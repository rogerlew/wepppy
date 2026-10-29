"""Real worker transitions with production dispatcher and a hung TLS receiver."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from uuid import uuid4

import redis
from rq import Queue, Worker
from tests.rq.webhook_tasks import transition_batch
from wepppy.rq.webhook_hooks import admission, install
from wepppy.rq.webhook_tracking import WebhookStore
from wepppy.rq.webhook_settlement import Member

connection = redis.Redis(host='redis', db=9)
store = WebhookStore(connection, 'disposable-workflow-acceptance')
queue = Queue('webhook-performance-' + str(uuid4()), connection=connection)
install()
evidence = {'uid': os.getuid(), 'gid': os.getgid(), 'conditions':
            '1000 actual worker transitions; tracked group with 80 hung TLS events and four 5000-member evaluation roots'}
workers = Worker.all(connection=connection)
evidence['worker_counts'] = {name: sum(name in worker.queue_names() for worker in workers)
                             for name in ('default', 'batch')}
assert evidence['worker_counts'] == {'default': 6, 'batch': 4}
assert all(worker.get_state() != 'busy' for worker in workers), 'Model computation must be idle before timing'
backlog = []
synthetic_jobs = []
count = int(os.getenv('RQ_WEBHOOK_PROBE_TRANSITIONS', '1000'))
profile = os.getenv('RQ_WEBHOOK_PROFILE_HOOKS')


def reserve(principal):
    identifier = str(uuid4())
    _, root = store.reserve(principal=principal, key=identifier, digest=identifier,
        operation='run-wepp', resource={'type': 'run', 'id': 'disposable-performance'},
        url='https://webhook.test/hang', job_id=identifier)
    return root

def publish(root, members):
    with connection.pipeline() as pipe:
        for member in members:
            pipe.hset('rq:job:' + member.job_id, 'status', member.status)
            synthetic_jobs.append(member.job_id)
            store.record_member(member, pipeline=pipe)
        store.published(root['job_id'], {'job_id': root['job_id']}, pipeline=pipe)
        pipe.execute()

try:
    for enabled in (False, True):
        if enabled:
            for index in range(80):
                root = reserve('backlog-' + str(index % 4))
                backlog.append(root['job_id'])
                publish(root, [Member(root['job_id'], root['job_id'], None, 'finished',
                                      producer_closed=True, changed_at=time.time())])
                assert store.evaluate(root['job_id']) == 'delivery_pending'
            for index in range(4):
                root = reserve('evaluation-' + str(index))
                backlog.append(root['job_id'])
                members = [Member(root['job_id'], root['job_id'], None, 'finished', producer_closed=True)]
                members += [Member(str(uuid4()), root['job_id'], root['job_id'], 'started') for _ in range(4999)]
                publish(root, members)
            deadline = time.monotonic() + 60
            while sum(bool(store.read(key).get('claim')) for key in backlog[:80]) < 4:
                assert time.monotonic() < deadline, 'Disposable dispatcher did not start four hung sends'
                time.sleep(.1)
            evidence['initial_active_senders'] = 4
            root = reserve('measured-transitions')
            backlog.append(root['job_id'])
            with connection.pipeline() as pipe:
                with admission(root['job_id'], store.environment):
                    queue.enqueue_call(transition_batch, args=(count + 1,), job_id=root['job_id'], pipeline=pipe)
                store.published(root['job_id'], {'job_id': root['job_id']}, pipeline=pipe)
                pipe.execute()
        else:
            queue.enqueue_call(transition_batch, args=(count + 1,))
        command_counts = connection.info("commandstats")
        redis_cpu = connection.info('cpu')
        started = time.monotonic()
        with Path('/acceptance/backlog-worker-' + str(enabled) + '.log').open('w') as log:
            command = (['/opt/venv/bin/python', 'docs/work-packages/20261027_rq_webhooks/artifacts/probes/profile_worker.py', queue.name]
                       if profile else ['/opt/venv/bin/rq', 'worker', '--burst', '--url',
                       'redis://redis:6379/9', '--worker-class', 'wepppy.rq.WepppyRqWorker', queue.name])
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            assert process.wait(timeout=600) == 0
        samples = [float(v) for v in connection.lrange(queue.name + ':transition-samples', 0, -1)]
        assert len(samples) == count + 1
        intervals = [b-a for a,b in zip(samples, samples[1:])]
        evidence['tracked' if enabled else 'baseline'] = {
            'first_sample_at': samples[0], 'last_sample_at': samples[-1],
            'transitions': len(intervals), 'p95_seconds': statistics.quantiles(intervals, n=100)[94],
            'median_seconds': statistics.median(intervals), 'elapsed_seconds': time.monotonic()-started,
            'intervals_seconds': intervals,
            'redis_cpu_seconds': {key: value - redis_cpu.get(key, 0)
                                  for key, value in connection.info('cpu').items()},
            'redis_command_usec': {key: value['usec'] - command_counts.get(key, {}).get('usec', 0)
                                  for key, value in connection.info('commandstats').items()},
            'redis_calls': {key: value['calls'] - command_counts.get(key, {}).get('calls', 0)
                            for key, value in connection.info('commandstats').items()}}
        if profile:
            timings = {}
            for line in Path('/acceptance/backlog-worker-' + str(enabled) + '.log').read_text().splitlines():
                if line.startswith('WEBHOOK_TIMING '):
                    value = json.loads(line.removeprefix('WEBHOOK_TIMING '))
                    timings.setdefault(value['hook'], []).append(value['seconds'])
            evidence['tracked' if enabled else 'baseline']['hook_timings'] = {
                key: {'mean': statistics.mean(values), 'max': max(values), 'count': len(values)}
                for key, values in timings.items()}
        connection.delete(queue.name + ':transition-samples')
    delta = evidence['tracked']['p95_seconds'] - evidence['baseline']['p95_seconds']
    evidence.update(delta_seconds=delta, relative_delta=delta/evidence['baseline']['p95_seconds'],
                    threshold_pass=delta <= .05 and delta <= .05*evidence['baseline']['p95_seconds'])
    evidence['backlog_audits'] = [{'job_id': key, 'state': store.read(key)['state'],
        'due': connection.zscore(store.due_key, key), 'event_id': store.read(key).get('event_id'),
        'attempts': store.read(key).get('attempts', 0),
        'audit': store.read(key).get('audit', [])} for key in backlog[:80]]
    event_ids = {item['event_id'] for item in evidence['backlog_audits']}
    evidence['hung_receiver_observations'] = [
        {'event_id': row['event_id'], 'received_at': row['received_at']}
        for line in Path('/evidence/workflow_receiver.jsonl').read_text().splitlines()
        if (row := json.loads(line))['event_id'] in event_ids
        and samples[0] <= row['received_at'] <= samples[-1]]
    evidence['sender_load_verified'] = len(evidence['hung_receiver_observations']) >= 4
finally:
    for root_id in backlog:
        store.finish(root_id, 'exhausted')
    if synthetic_jobs:
        connection.unlink(*['rq:job:' + key for key in synthetic_jobs])
    Path('/evidence/' + ('backlog_diagnostic.json' if profile else 'backlog_performance.json')).write_text(json.dumps(evidence, indent=2)+'\n')
assert evidence['sender_load_verified'], 'Hung receiver overlap was not demonstrated'
assert evidence['threshold_pass'], 'Approved overhead threshold exceeded; retained evidence'
print('Backlog transition overhead met both approved limits.')
