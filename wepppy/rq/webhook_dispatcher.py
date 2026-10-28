"""Independent webhook evaluation/delivery and sanitized operator inspection.

No RQ computation queue is consumed. Explicit external arming is required; a
restored Redis enabled flag alone never starts dispatch.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
import time
from uuid import uuid4

import redis
from redis.exceptions import WatchError

from . import webhook_policy as policy
from .webhook_http import deliver
from .webhook_tracking import WebhookStore, bounded_root

LOG = logging.getLogger(__name__)

_CLAIM = """
if ARGV[7] ~= '' and string.match(redis.call('INFO','server'), 'run_id:(%w+)') ~= ARGV[7] then return '' end
local raw = redis.call('HGET', KEYS[1], 'data')
if not raw then return '' end
local root = cjson.decode(raw)
if root.state ~= 'delivery_pending' then return '' end
local now = tonumber(ARGV[1])
local due = tonumber(redis.call('ZSCORE', KEYS[4], root.job_id) or '0')
if due > now then return '' end
if now >= root.event_at + tonumber(ARGV[3]) then return 'exhausted' end
if root.claim and root.claim.until_at > now then return '' end
if root.attempts >= tonumber(ARGV[4]) then return 'exhausted' end
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
local owner = redis.call('GET', KEYS[3])
if owner then return '' end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[5]) then return '' end
root.attempts = root.attempts + 1
root.claim = {token=ARGV[2], until_at=now+tonumber(ARGV[6])}
root.audit = root.audit or {}
table.insert(root.audit, {attempt=root.attempts, started_at=now, result='interrupted'})
if string.len(cjson.encode(root)) > tonumber(redis.call('HGET',KEYS[1],'bytes')) then return 'exhausted' end
redis.call('HSET', KEYS[1], 'data', cjson.encode(root))
redis.call('ZADD', KEYS[2], root.claim.until_at, ARGV[2])
redis.call('SET', KEYS[3], ARGV[2], 'EX', ARGV[6])
redis.call('ZADD', KEYS[4], root.claim.until_at, root.job_id)
return cjson.encode(root)
"""


def claim(store: WebhookStore, root_id: str, now: float, *, redis_run_id: str | None = None) -> dict | None:
    root = store.read(root_id)
    if not root:
        return None
    result = store.connection.eval(_CLAIM, 4, store.root_key(root_id), store.prefix + 'claims',
                                   store.prefix + 'claim:' + root['principal'], store.due_key,
                                   now, str(uuid4()), policy.DELIVERY_SECONDS, policy.ATTEMPTS,
                                   policy.CONCURRENCY, policy.LEASE_SECONDS, redis_run_id or '')
    if result == b'exhausted' or result == 'exhausted':
        store.finish(root_id, 'exhausted', now=now)
        return None
    return json.loads(result) if result else None


def record_attempt(store: WebhookStore, claimed: dict, result: dict, now: float) -> bool:
    key = store.root_key(claimed['job_id'])
    token = claimed['claim']['token']
    with store.connection.pipeline() as pipe:
        try:
            pipe.watch(key)
            raw = pipe.hget(key, 'data')
            if not raw:
                return False
            root = json.loads(raw)
            if root.get('claim', {}).get('token') != token or root['state'] != 'delivery_pending':
                return False
            # Persist only known safe values, never a response/error string.
            status = result.get('status')
            error = result.get('error')
            errors = {'unsafe_destination', 'connection', 'tls', 'dns', 'timeout', 'sender', 'response_headers'}
            audit = root['audit'][-1]
            audit.update(finished_at=now, result='http' if isinstance(status, int) else (error if error in errors else 'sender'))
            if isinstance(status, int) and 100 <= status <= 599:
                audit['http_status'] = status
            acknowledged = isinstance(status, int) and 200 <= status < 300
            transient = error in {'connection', 'timeout'} or (error == 'dns' and result.get('transient') is True) or status in policy.RETRY_STATUSES
            terminal = acknowledged or not transient or root['attempts'] >= policy.ATTEMPTS or now >= root['event_at'] + policy.DELIVERY_SECONDS
            root.pop('claim', None)
            delay = policy.RETRY_DELAYS[min(root['attempts'] - 1, len(policy.RETRY_DELAYS) - 1)]
            if isinstance(result.get('retry_after'), int):
                delay = max(delay, min(policy.RETRY_AFTER_MAX, max(0, result['retry_after'])))
            due = min(now + delay, root['event_at'] + policy.DELIVERY_SECONDS)
            if terminal:
                member_bytes = int(pipe.hget(key, 'member_bytes') or 0)
                principal_key = pipe.hget(key, 'principal_key')
                root['state'] = 'delivered' if acknowledged else 'exhausted'
                root['closed_at'] = now
                root.pop('url', None)
                due = now + policy.AUDIT_SECONDS
            raw = bounded_root(root, int(pipe.hget(key, 'bytes')))
            pipe.multi()
            pipe.hset(key, 'data', raw)
            if terminal:
                pipe.hset(key, 'member_bytes', 0)
                pipe.hincrby(key, 'revision', 1)
                pipe.hincrby(principal_key, 'pending', -1)
                pipe.hincrby(store.global_key, 'pending', -1)
                pipe.hincrby(principal_key, 'bytes', -member_bytes)
                pipe.hincrby(store.global_key, 'bytes', -member_bytes)
                pipe.unlink(store.members_key(root['job_id']))
            pipe.zrem(store.prefix + 'claims', token)
            # Owner compare prevents stale completion releasing a newer claim.
            pipe.eval("if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0",
                      1, store.prefix + 'claim:' + root['principal'], token)
            pipe.zadd(store.due_key, {root['job_id']: due})
            pipe.execute()
        except WatchError:
            return False
    return True


def attempt(store: WebhookStore, claimed: dict, redis_run_id: str | None = None) -> None:
    if redis_run_id and store.connection.info('server').get('run_id') != redis_run_id:
        return  # Leave the persisted interrupted attempt for explicit rearming.
    remaining = claimed['event_at'] + policy.DELIVERY_SECONDS - time.time()
    result = deliver(claimed['url'], claimed['event'], claimed['event_id'], seconds=min(policy.ATTEMPT_SECONDS, remaining))
    record_attempt(store, claimed, result, time.time())


def inspect(store: WebhookStore, root_id: str) -> dict | None:
    root = store.read(root_id)
    if root is None:
        return None
    allowed = {'job_id', 'principal', 'operation', 'host', 'destination_id', 'state', 'created_at',
               'closed_at', 'event_id', 'event_at', 'attempts', 'audit', 'publication'}
    return {key: value for key, value in root.items() if key in allowed}


def run(store: WebhookStore, *, dispatch: bool = False, once: bool = False,
        redis_run_id: str | None = None) -> None:
    if dispatch and (not redis_run_id or store.connection.info('server').get('run_id') != redis_run_id):
        raise ValueError('Dispatch requires explicit arming for the current Redis process identity.')
    futures = set()
    evaluations = {}
    last_principal = None
    with ThreadPoolExecutor(max_workers=policy.CONCURRENCY, thread_name_prefix='webhook') as executor:
        try:
            while True:
                now = time.time()
                if dispatch and store.connection.info('server').get('run_id') != redis_run_id:
                    dispatch = False
                    LOG.error('Redis process identity changed; dispatch disabled pending operator recovery')
                for future in list(futures):
                    if future.done():
                        try:
                            future.result()
                        except (redis.RedisError, OSError, ValueError):
                            LOG.error('Webhook attempt bookkeeping unavailable; fenced recovery pending')
                        futures.remove(future)
                ids = store.connection.zrangebyscore(store.due_key, '-inf', now, start=0, num=policy.PAGE_SIZE)
                candidates = {}
                for raw_id in ids:
                    root_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
                    if root_id in evaluations:
                        continue
                    root = store.read(root_id)
                    if root is None:
                        store.connection.zrem(store.due_key, root_id)
                        continue
                    candidates.setdefault(root['principal'], []).append((root_id, root))
                principals = sorted(candidates)
                if last_principal in principals:
                    split = principals.index(last_principal) + 1
                    principals = principals[split:] + principals[:split]
                active_principals = {entry[0] for entry in evaluations.values()}
                for principal in principals:
                    # Rotate one due root per principal before revisiting backlog.
                    root_id, root = candidates[principal][0]
                    state = root['state']
                    if state == 'delivery_pending':
                        if now >= root['event_at'] + policy.DELIVERY_SECONDS:
                            store.finish(root_id, 'exhausted', now=now)
                        elif dispatch and len(futures) < policy.CONCURRENCY:
                            claimed = claim(store, root_id, now, redis_run_id=redis_run_id)
                            if claimed:
                                futures.add(executor.submit(attempt, store, claimed, redis_run_id))
                            else:
                                store.connection.zadd(store.due_key, {root_id: now + policy.RECONCILE_SECONDS}, gt=True)
                        elif not dispatch:
                            store.connection.zadd(store.due_key, {root_id: min(now + policy.RECONCILE_SECONDS, root['event_at'] + policy.DELIVERY_SECONDS)}, gt=True)
                        else:
                            store.connection.zadd(store.due_key, {root_id: now + policy.RECONCILE_SECONDS}, gt=True)
                    elif state in {'delivered', 'exhausted', 'outcome_unavailable', 'admission_unavailable'}:
                        if not store.expire(root_id, now):
                            # Repair stale due indexes after older schedulers or
                            # interrupted recovery; an unexpired terminal root
                            # must not starve its principal's pending deliveries.
                            store.connection.zadd(store.due_key, {
                                root_id: max(now + policy.RECONCILE_SECONDS,
                                             root['closed_at'] + policy.AUDIT_SECONDS)
                            }, gt=True)
                    elif len(evaluations) < policy.CONCURRENCY and principal not in active_principals:
                        evaluations[root_id] = (principal, store.evaluation_steps(root_id, now=now))
                        active_principals.add(principal)
                        store.connection.zadd(store.due_key, {root_id: now + policy.RECONCILE_SECONDS}, gt=True)
                    else:
                        store.connection.zadd(store.due_key, {root_id: now + policy.RECONCILE_SECONDS}, gt=True)
                    # Roots skipped behind the selected representative must not
                    # pin the first candidate page and starve later principals.
                    if len(candidates[principal]) > 1:
                        store.connection.zadd(store.due_key, {
                            key: now + policy.RECONCILE_SECONDS for key, _ in candidates[principal][1:]
                        }, gt=True)
                    last_principal = principal
                # One scheduler budget shared across roots, not a full slice
                # per root. Rotate after every bounded generator step so a large
                # graph cannot consume consecutive slices ahead of other roots.
                deadline = time.monotonic() + policy.SLICE_SECONDS
                while evaluations and time.monotonic() < deadline:
                    root_id = next(iter(evaluations))
                    principal, steps = evaluations.pop(root_id)
                    evaluations[root_id] = (principal, steps)
                    try:
                        next(steps)
                    except StopIteration as done:
                        del evaluations[root_id]
                        if done.value != 'delivery_pending':
                            store.connection.zadd(store.due_key, {root_id: time.time() + policy.RECONCILE_SECONDS}, gt=True)
                if once and not evaluations:
                    break
                time.sleep(policy.SLICE_SECONDS)
        finally:
            for _, steps in evaluations.values():
                steps.close()  # Release WATCH connections on shutdown/interruption.


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', required=True)
    parser.add_argument('--dispatch', action='store_true', default=os.getenv('RQ_WEBHOOK_DISPATCH') == 'enabled', help='Explicit external arm; omit for restored/copied stores')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--redis-run-id', default=os.getenv('RQ_WEBHOOK_REDIS_RUN_ID'), help='Operator-reviewed Redis process identity; mandatory with --dispatch')
    parser.add_argument('--inspect', metavar='JOB_ID')
    args = parser.parse_args()
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        store = WebhookStore(connection, args.environment)
        if args.inspect:
            print(json.dumps(inspect(store, args.inspect)))
        else:
            run(store, dispatch=args.dispatch, once=args.once, redis_run_id=args.redis_run_id)


if __name__ == '__main__':
    main()
