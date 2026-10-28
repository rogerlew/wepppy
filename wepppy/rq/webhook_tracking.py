"""Bounded Redis receipts for RQ-WH-01, separate from RQ job/result retention.

Receipts use this environment's namespace; first publication also seeds a dedicated
RQ generation field in the same transaction. Hooks use bounded construction and
never evaluate a graph. Raw URLs remain in restricted root intents.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import time
from uuid import uuid4

from redis.exceptions import WatchError

from . import webhook_policy as policy
from .webhook_http import destination
from .webhook_settlement import Member, evaluation_steps


def encode(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _text(value):
    return value.decode() if isinstance(value, bytes) else value


def bounded_root(root: dict, ceiling: int) -> str:
    raw = encode(root)
    if len(raw.encode('utf-8')) > ceiling:
        raise ValueError('Webhook receipt exceeds its reserved envelope.')
    return raw


class AdmissionError(RuntimeError):
    def __init__(self, code: str, status: int, job_id: str | None = None, *, publication: str = 'unknown'):
        super().__init__(code)
        self.code, self.status, self.job_id = code, status, job_id
        self.publication = publication if publication == 'not_published' else 'unknown'


_RESERVE = """
if ARGV[9] ~= '' and string.match(redis.call('INFO', 'server'), 'run_id:(%w+)') ~= ARGV[9] then return {'instance', ''} end
local existing = redis.call('GET', KEYS[1])
if existing then
 local key = ARGV[10] .. existing
 local raw = redis.call('HGET', key, 'data')
 if raw then
  local root = cjson.decode(raw); local candidate = cjson.decode(ARGV[2])
  if root.state == 'admission_retryable' and root.digest == candidate.digest then
   if tonumber(ARGV[3]) >= root.created_at + tonumber(ARGV[11]) then return {'expired', existing} end
   root.state = 'admission_pending'
   redis.call('HSET', key, 'data', cjson.encode(root))
   redis.call('HINCRBY', key, 'revision', 1)
   return {'resumed', existing}
  end
 end
 return {'existing', existing}
end
local pn = tonumber(redis.call('HGET', KEYS[4], 'pending') or '0')
local gn = tonumber(redis.call('HGET', KEYS[3], 'pending') or '0')
local pb = tonumber(redis.call('HGET', KEYS[4], 'bytes') or '0')
local gb = tonumber(redis.call('HGET', KEYS[3], 'bytes') or '0')
local size = string.len(ARGV[2]) + tonumber(ARGV[4])
if pn >= tonumber(ARGV[5]) or pb + size > tonumber(ARGV[7]) then return {'principal', ''} end
if gn >= tonumber(ARGV[6]) or gb + size > tonumber(ARGV[8]) then return {'global', ''} end
redis.call('SET', KEYS[1], ARGV[1])
redis.call('HSET', KEYS[2], 'data', ARGV[2], 'revision', 0, 'bytes', size,
 'member_bytes', 0, 'edges', 0, 'principal_key', KEYS[4], 'idem_key', KEYS[1])
redis.call('HINCRBY', KEYS[3], 'pending', 1)
redis.call('HINCRBY', KEYS[4], 'pending', 1)
redis.call('HINCRBY', KEYS[3], 'bytes', size)
redis.call('HINCRBY', KEYS[4], 'bytes', size)
redis.call('ZADD', KEYS[5], ARGV[3], ARGV[1])
return {'created', ARGV[1]}
"""

_MEMBER = """
local raw = redis.call('HGET', KEYS[1], 'data')
if not raw then return 0 end
local root = cjson.decode(raw)
if root.state ~= 'tracking' and root.state ~= 'admission_pending' then return 0 end
local member = cjson.decode(ARGV[2])
if member.root_id ~= root.job_id then return 0 end
local oldraw = redis.call('HGET', KEYS[2], ARGV[1])
local old = oldraw and cjson.decode(oldraw) or nil
if old and old.parent_id ~= member.parent_id then
 redis.call('HSET', KEYS[1], 'incomplete', 'binding'); return 0
end
if old and old.published and not member.published then
 redis.call('HSET', KEYS[1], 'incomplete', 'republication')
 redis.call('HINCRBY', KEYS[1], 'revision', 1); return 0
end
if ARGV[8] == 'start' then
 if not old or member.execution_id == cjson.null then return 0 end
 local actual = redis.call('HGET', KEYS[5], ARGV[9])
 if actual == member.execution_id and old.execution_id == member.execution_id
  and old.executions and old.executions[member.execution_id] ~= nil then return 1 end
 local previous = redis.call('HGET', KEYS[5], ARGV[10]) or ''
 local retained = old.execution_id ~= cjson.null and old.execution_id or ARGV[11]
 if actual ~= member.execution_id or previous ~= retained then
  redis.call('HSET', KEYS[1], 'incomplete', 'generation_gap')
  redis.call('HINCRBY', KEYS[1], 'revision', 1); return 0
 end
 old.executions = old.executions or {}
 if old.executions[member.execution_id] ~= nil then return 1 end
 old.executions[member.execution_id] = false
 old.execution_id = member.execution_id; old.status = 'started'
 old.returned = false; old.producer_closed = false
 old.changed_at = member.changed_at; member = old
elseif ARGV[8] == 'returned' or ARGV[8] == 'closed' or ARGV[8] == 'exited' then
 if not old or member.execution_id == cjson.null or not old.executions
  or old.executions[member.execution_id] == nil then return 0 end
 if ARGV[8] == 'closed' or ARGV[8] == 'exited' then
  if ARGV[8] == 'closed' and not old.executions[member.execution_id] then return 0 end
  if ARGV[8] == 'exited' and old.execution_id == member.execution_id then
   old.returned = true; old.status = member.status
  end
  old.executions[member.execution_id] = nil
 else
  old.executions[member.execution_id] = true
  if old.execution_id == member.execution_id then
   old.status = member.status; old.returned = true
  end
 end
 old.producer_closed = next(old.executions) == nil
 old.changed_at = member.changed_at; member = old
elseif ARGV[8] == 'state' and old then
 if member.execution_id ~= cjson.null and member.execution_id ~= old.execution_id then
  -- A registered older overlapping producer may still save its own job state.
  -- Ignore that stale state without losing its independently tracked exit.
  if old.executions and old.executions[member.execution_id] ~= nil then return 1 end
  redis.call('HSET', KEYS[1], 'incomplete', 'generation_gap')
  redis.call('HINCRBY', KEYS[1], 'revision', 1); return 0
 end
 member.producer_closed = old.producer_closed
 member.returned = old.returned; member.executions = old.executions
 if member.execution_id == cjson.null then member.execution_id = old.execution_id end
 if member.status == 'started' and next(member.executions or {}) == nil then
  redis.call('HSET', KEYS[1], 'incomplete', 'uninstrumented_execution')
  member.producer_closed = false
 end
end
ARGV[2] = cjson.encode(member)
local oldedges = old and #old.dependencies or 0
local edges = tonumber(redis.call('HGET', KEYS[1], 'edges') or '0') + #member.dependencies - oldedges
local delta = string.len(ARGV[2]) - (oldraw and string.len(oldraw) or 0)
local principal = redis.call('HGET', KEYS[1], 'principal_key')
if (not old and redis.call('HLEN', KEYS[2]) >= tonumber(ARGV[3])) or edges > tonumber(ARGV[4])
 or tonumber(redis.call('HGET', KEYS[3], 'bytes') or '0') + delta > tonumber(ARGV[5])
 or tonumber(redis.call('HGET', principal, 'bytes') or '0') + delta > tonumber(ARGV[6]) then
 redis.call('HSET', KEYS[1], 'incomplete', 'capacity');
 redis.call('HINCRBY', KEYS[1], 'revision', 1); return 0
end
if member.published and (not old or not old.published) then
 -- Seed once in the first publication transaction. Recreated job hashes must
 -- not regain initial-generation proof after TTL deletion and lost receipts.
 redis.call('HSETNX', KEYS[5], ARGV[9], ARGV[11])
end
redis.call('HSET', KEYS[2], ARGV[1], ARGV[2])
redis.call('HSET', KEYS[1], 'edges', edges)
redis.call('HINCRBY', KEYS[1], 'member_bytes', delta)
redis.call('HINCRBY', KEYS[3], 'bytes', delta)
redis.call('HINCRBY', principal, 'bytes', delta)
redis.call('HINCRBY', KEYS[1], 'revision', 1)
-- Preserve the evaluator's reconciliation deadline. Waking on every child
-- transition repeatedly traverses active graphs and contends with computation.
redis.call('ZADD', KEYS[4], 'NX', ARGV[7], root.job_id)
return 1
"""

# Atomic event creation validates the revision used to evaluate all member receipts.
_EVENT = """
if redis.call('HGET', KEYS[1], 'revision') ~= ARGV[1] or redis.call('HEXISTS', KEYS[1], 'incomplete') == 1 then return 0 end
local raw = redis.call('HGET', KEYS[1], 'data')
if not raw then return 0 end
local root = cjson.decode(raw)
if root.state ~= 'tracking' then return 0 end
root.state = 'delivery_pending'; root.event = ARGV[2]; root.event_id = ARGV[3]
root.event_at = tonumber(ARGV[4]); root.attempts = 0
if string.len(cjson.encode(root)) > tonumber(redis.call('HGET', KEYS[1], 'bytes')) then
 redis.call('HSET', KEYS[1], 'incomplete', 'envelope_capacity'); return 0 end
redis.call('HSET', KEYS[1], 'data', cjson.encode(root))
redis.call('HINCRBY', KEYS[1], 'revision', 1)
redis.call('ZADD', KEYS[2], ARGV[4], root.job_id)
return 1
"""


class WebhookStore:
    def __init__(self, connection, environment: str):
        if not environment or len(environment) > 128:
            raise ValueError('A bounded webhook environment identity is required.')
        self.connection = connection
        self.environment = environment
        self.prefix = 'rq-webhook:v1:' + hashlib.sha256(environment.encode()).hexdigest()[:24] + ':'
        self.due_key = self.prefix + 'due'
        self.global_key = self.prefix + 'quota'

    def root_key(self, root_id: str) -> str:
        return self.prefix + 'root:' + root_id

    def members_key(self, root_id: str) -> str:
        return self.root_key(root_id) + ':members'

    def read(self, root_id: str) -> dict | None:
        raw = self.connection.hget(self.root_key(root_id), 'data')
        return json.loads(raw) if raw else None

    def reserve(self, *, principal: str, key: str, digest: str, operation: str,
                resource: dict, url: str, job_id: str, now: float | None = None,
                redis_run_id: str | None = None) -> tuple[bool, dict]:
        now = time.time() if now is None else now
        target = destination(url)
        principal_hash = hashlib.sha256(principal.encode()).hexdigest()
        idem = self.prefix + 'idem:' + hashlib.sha256(encode([principal, key]).encode()).hexdigest()
        data = {'job_id': job_id, 'principal': principal_hash, 'digest': digest,
                'operation': operation, 'resource': resource, 'url': target.url,
                'host': target.host, 'destination_id': str(uuid4()), 'environment': self.environment,
                'created_at': now, 'state': 'admission_pending', 'response': {}, 'publication': 'unknown'}
        result = self.connection.eval(_RESERVE, 5, idem, self.root_key(job_id), self.global_key,
                                      self.prefix + 'principal:' + principal_hash, self.due_key,
                                      job_id, encode(data), now, policy.EVENT_BYTES * 2,
                                      policy.PRINCIPAL_ROOTS, policy.GLOBAL_ROOTS,
                                      policy.PRINCIPAL_BYTES, policy.GLOBAL_BYTES, redis_run_id or '', self.prefix + 'root:', policy.TRACKING_SECONDS)
        status, root_id = map(_text, result)
        if status == 'expired':
            self.finish(root_id, 'admission_unavailable', now=now)
            stored = self.read(root_id) or {}
            raise AdmissionError('webhook_admission_unavailable', 410, root_id,
                                 publication=stored.get('publication', 'unknown'))
        if status == 'principal':
            raise AdmissionError('webhook_capacity_exceeded', 429)
        if status in {'global', 'instance'}:
            raise AdmissionError('webhook_unavailable', 503)
        stored = self.read(root_id)
        if stored is None:
            raise AdmissionError('webhook_admission_unknown', 503, root_id)
        if stored['digest'] != digest or stored['operation'] != operation:
            raise AdmissionError('webhook_idempotency_conflict', 409, root_id)
        if stored['state'] == 'admission_unavailable':
            raise AdmissionError('webhook_admission_unavailable', 410, root_id,
                                 publication=stored.get('publication', 'unknown'))
        return status in {'created', 'resumed'}, stored

    def prepublication_failed(self, root_id: str) -> None:
        script = """
        local raw = redis.call('HGET',KEYS[1],'data')
        if not raw then return 0 end
        local root = cjson.decode(raw)
        if root.state ~= 'admission_pending' then return 0 end
        root.state = 'admission_retryable'; root.publication = 'not_published'
        redis.call('HSET',KEYS[1],'data',cjson.encode(root))
        redis.call('HINCRBY',KEYS[1],'revision',1)
        return 1
        """
        self.connection.eval(script, 1, self.root_key(root_id))

    def record_member(self, member: Member, *, pipeline=None, mode: str = 'replace', deadline=None) -> bool:
        client = pipeline if pipeline is not None else self.connection
        if deadline is None:
            raw = encode(asdict(member))
        else:
            # Deep-copying a large dependency tuple already exceeds the hook
            # budget. Stream the immutable receipt and stop before publication.
            chunks = []
            encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True)
            for index, chunk in enumerate(encoder.iterencode(vars(member))):
                if index % policy.PAGE_SIZE == 0 and time.monotonic() >= deadline:
                    raise ValueError('Webhook receipt construction budget exhausted')
                chunks.append(chunk)
            raw = ''.join(chunks)
            if time.monotonic() >= deadline:
                raise ValueError('Webhook receipt construction budget exhausted')
        result = client.eval(_MEMBER, 5, self.root_key(member.root_id), self.members_key(member.root_id),
                             self.global_key, self.due_key, 'rq:job:' + member.job_id, member.job_id, raw,
                             policy.ROOT_MEMBERS, policy.ROOT_EDGES, policy.GLOBAL_BYTES,
                             policy.PRINCIPAL_BYTES, time.time(), mode,
                             policy.GENERATION_FIELD, policy.PREVIOUS_GENERATION_FIELD,
                             policy.UNSTARTED_GENERATION)
        return True if pipeline is not None and result is pipeline else bool(result)

    def member(self, root_id: str, job_id: str) -> Member | None:
        raw = self.connection.hget(self.members_key(root_id), job_id)
        if not raw:
            return None
        data = json.loads(raw)
        data['dependencies'] = tuple(data['dependencies'])
        return Member(**data)

    def published(self, root_id: str, response: dict, *, pipeline) -> None:
        # No credentials are admitted to persisted replay fields.
        allowed = {'job_id', 'culvert_batch_uuid', 'status_url', 'webhook'}
        if set(response) - allowed:
            raise ValueError('Credential-free webhook receipt required.')
        script = """
        local raw = redis.call('HGET', KEYS[1], 'data')
        if not raw then return 0 end
        local root = cjson.decode(raw)
        if root.state ~= 'admission_pending' then return 0 end
        local memberraw = redis.call('HGET', KEYS[2], root.job_id)
        local member = memberraw and cjson.decode(memberraw) or nil
        if not member or not member.published or member.root_id ~= root.job_id
         or member.parent_id ~= cjson.null
         or redis.call('HGET', KEYS[3], ARGV[2]) ~= ARGV[3] then
         -- API publication has no executing parent to poison. Preserve accepted
         -- computation, but never recover missing initial proof by reseeding a
         -- later recreated job after all first-attempt receipts were lost.
         redis.call('HSET', KEYS[1], 'incomplete', 'initial_publication')
        end
        root.state = 'tracking'; root.publication = 'published'; root.response = cjson.decode(ARGV[1])
        if string.len(cjson.encode(root)) > tonumber(redis.call('HGET', KEYS[1], 'bytes')) then return 0 end
        redis.call('HSET', KEYS[1], 'data', cjson.encode(root))
        redis.call('HINCRBY', KEYS[1], 'revision', 1)
        return 1
        """
        pipeline.eval(script, 3, self.root_key(root_id), self.members_key(root_id),
                      'rq:job:' + root_id, encode(response), policy.GENERATION_FIELD,
                      policy.UNSTARTED_GENERATION)

    def incomplete(self, root_id: str, reason: str) -> None:
        with self.connection.pipeline() as pipe:
            pipe.hset(self.root_key(root_id), 'incomplete', reason)
            pipe.hincrby(self.root_key(root_id), 'revision', 1)
            pipe.execute()

    def snapshot_pages(self, root_id: str):
        """Yield small pages; caller can time-slice between them without locks."""
        cursor = 0
        while True:
            cursor, fields = self.connection.hscan(self.members_key(root_id), cursor=cursor, count=policy.PAGE_SIZE)
            yield fields
            if not cursor:
                break

    def evaluation_steps(self, root_id: str, *, now: float | None = None):
        now = time.time() if now is None else now
        root_key = self.root_key(root_id)
        # WATCH is an optimistic version check, not a computation lock. The
        # dispatcher holds at most CONCURRENCY evaluators/connections at once.
        with self.connection.pipeline() as guard:
            guard.watch(root_key)
            header = guard.hgetall(root_key)
            if not header:
                return 'missing'
            header = {_text(k): _text(v) for k, v in header.items()}
            root = json.loads(header['data'])
            if root['state'] not in {'tracking', 'admission_pending', 'admission_retryable'}:
                return root['state']
            if now >= root['created_at'] + policy.TRACKING_SECONDS:
                guard.reset()
                self.finish(root_id, 'admission_unavailable' if root['state'] != 'tracking' else 'outcome_unavailable', now=now)
                return 'outcome_unavailable'
            if root['state'] != 'tracking':
                self.connection.zadd(self.due_key, {root_id: now + policy.RECONCILE_SECONDS}, gt=True)
                return 'waiting'
            if 'incomplete' in header:
                return 'unknown'
            members = {}
            for page in self.snapshot_pages(root_id):
                keys = [_text(key) for key in page]
                for key in keys:
                    raw = page.get(key, page.get(key.encode()))
                    data = json.loads(raw)
                    data['dependencies'] = tuple(data['dependencies'])
                    members[key] = Member(**data)
                if any(not members[key].published for key in keys):
                    return 'unknown'
                # An active receipt cannot contribute to a terminal event. Stop
                # this observation before accumulating WATCH keys for large live
                # graphs. No outcome is inferred; reconciliation will retry.
                if any(member.published and member.status in policy.TERMINAL | {'created', 'queued', 'started', 'scheduled', 'deferred'}
                       and (member.retry_pending or not member.producer_closed or member.release_pending
                            or member.status in {'created', 'queued', 'started', 'scheduled'})
                       for member in (members[key] for key in keys)):
                    return 'waiting'
                if keys:
                    # Preserve the early actual-job fence for every page that
                    # could contribute to settlement. In particular, a complete
                    # retry/requeue ABA during evaluation must invalidate WATCH
                    # even when every notification receipt for that attempt fails.
                    guard.watch(*['rq:job:' + key for key in keys])
                    with self.connection.pipeline(transaction=False) as reads:
                        for key in keys:
                            reads.hmget('rq:job:' + key, 'status', policy.GENERATION_FIELD)
                        statuses = reads.execute()
                    for key, (actual, generation) in zip(keys, statuses):
                        # The ordinary pre-fork RQ write advances generation even
                        # if all optional tracking receipts fail. Old Job.save
                        # mappings cannot overwrite this dedicated hash field.
                        # A missing hash cannot rule out an entirely missed rerun.
                        if (actual is None or _text(actual) != members[key].status
                                or (_text(generation) if generation is not None else None)
                                != (members[key].execution_id or policy.UNSTARTED_GENERATION)):
                            return 'unknown'
                yield None
            external = yield from self.external_steps(guard, members)
            result = yield from evaluation_steps(root_id, members, external,
                                                 incomplete='incomplete' in header)
            if result.state != 'settled':
                self.connection.zadd(self.due_key, {root_id: now + policy.RECONCILE_SECONDS}, gt=True)
                return result.state
            stamp = lambda value: datetime.fromtimestamp(value, timezone.utc).isoformat().replace('+00:00', 'Z')
            event_id = str(uuid4())
            event = encode({'schema_version': 1, 'event_id': event_id, 'event': 'operation.completed',
                            'job_id': root_id, 'operation': root['operation'], 'resource': root['resource'],
                            'execution_status': result.execution_status, 'settled_at': stamp(result.settled_at),
                            'observed_at': stamp(now)})
            if len(event.encode()) > policy.EVENT_BYTES:
                guard.reset()
                self.finish(root_id, 'outcome_unavailable', now=now)
                return 'outcome_unavailable'
            guard.multi()
            guard.eval(_EVENT, 2, root_key, self.due_key, header['revision'], event, event_id, now)
            try:
                committed = guard.execute()[0]
            except WatchError:
                return 'conflict'
            return 'delivery_pending' if committed else 'conflict'

    def external_steps(self, guard, members):
        """Verify foreign prerequisites without adopting their hierarchy.

        RQ metadata only locates a receipt. The durable server-owned member and
        its root revision authorize the observation; absent/expired or incomplete
        receipts remain unknown. WATCH fences both that receipt and actual RQ
        state against retry/requeue through this operation's event commit.
        """
        from rq.job import Job
        from .webhook_hooks import binding

        dependencies = set()
        for member in members.values():
            for index, key in enumerate(member.dependencies):
                if key not in members:
                    dependencies.add(key)
                if index % policy.PAGE_SIZE == 0:
                    yield None
        external = {}
        keys = list(dependencies)
        for offset in range(0, len(keys), policy.PAGE_SIZE):
            page = keys[offset:offset + policy.PAGE_SIZE]
            guard.watch(*['rq:job:' + key for key in page])
            jobs = Job.fetch_many(page, connection=self.connection)
            for job in jobs:
                yield None
                if job is None:
                    continue
                info = binding(job)
                if info is None or info['environment'] != self.environment:
                    continue
                foreign_root = self.root_key(info['root'])
                guard.watch(foreign_root)
                root_data, incomplete = guard.hmget(foreign_root, 'data', 'incomplete')
                if root_data is None or incomplete is not None:
                    continue
                raw = guard.hget(self.members_key(info['root']), job.id)
                if raw is None:
                    continue
                data = json.loads(raw)
                data['dependencies'] = tuple(data['dependencies'])
                member = Member(**data)
                actual = job.get_status(refresh=False)
                generation = guard.hget(job.key, policy.GENERATION_FIELD)
                if (member.job_id == job.id and member.root_id == info['root']
                        and member.parent_id == info['parent']
                        and member.status == getattr(actual, 'value', actual)
                        and (member.execution_id or policy.UNSTARTED_GENERATION)
                        == (_text(generation) if generation is not None else None)):
                    external[job.id] = member
            yield None
        return external

    def evaluate(self, root_id: str, *, now: float | None = None) -> str:
        steps = self.evaluation_steps(root_id, now=now)
        while True:
            try:
                next(steps)
            except StopIteration as done:
                return done.value

    def finish(self, root_id: str, state: str, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        key = self.root_key(root_id)
        with self.connection.pipeline() as pipe:
            try:
                pipe.watch(key)
                raw = pipe.hget(key, 'data')
                if not raw:
                    return False
                root = json.loads(raw)
                if root['state'] in {'delivered', 'exhausted', 'outcome_unavailable', 'admission_unavailable'}:
                    return False
                principal = _text(pipe.hget(key, 'principal_key'))
                member_bytes = int(pipe.hget(key, 'member_bytes') or 0)
                root.pop('url', None)
                root['state'], root['closed_at'] = state, now
                root.pop('claim', None)
                raw = bounded_root(root, int(pipe.hget(key, 'bytes')))
                pipe.multi()
                pipe.hset(key, mapping={'data': raw, 'member_bytes': 0})
                pipe.hincrby(key, 'revision', 1)
                pipe.hincrby(principal, 'pending', -1)
                pipe.hincrby(self.global_key, 'pending', -1)
                pipe.hincrby(principal, 'bytes', -member_bytes)
                pipe.hincrby(self.global_key, 'bytes', -member_bytes)
                pipe.unlink(self.members_key(root_id))
                pipe.zadd(self.due_key, {root_id: now + policy.AUDIT_SECONDS})
                pipe.execute()
                return True
            except WatchError:
                return False

    def expire(self, root_id: str, now: float) -> bool:
        key = self.root_key(root_id)
        with self.connection.pipeline() as pipe:
            try:
                pipe.watch(key)
                raw = pipe.hget(key, 'data')
                if not raw:
                    return False
                root = json.loads(raw)
                if not root.get('closed_at') or now < root['closed_at'] + policy.AUDIT_SECONDS:
                    return False
                principal = _text(pipe.hget(key, 'principal_key'))
                idem = _text(pipe.hget(key, 'idem_key'))
                size = int(pipe.hget(key, 'bytes'))
                pipe.multi()
                pipe.hincrby(principal, 'bytes', -size)
                pipe.eval("if tonumber(redis.call('HGET',KEYS[1],'bytes') or '0') == 0 and tonumber(redis.call('HGET',KEYS[1],'pending') or '0') == 0 then return redis.call('DEL',KEYS[1]) end return 0", 1, principal)
                pipe.hincrby(self.global_key, 'bytes', -size)
                pipe.delete(key, idem)
                pipe.zrem(self.due_key, root_id)
                pipe.execute()
                return True
            except WatchError:
                return False
