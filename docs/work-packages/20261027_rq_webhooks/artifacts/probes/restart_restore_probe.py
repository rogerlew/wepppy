"""Real persisted Redis restart across reservation/publication and dispatch arming."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace

import redis
from rq import Queue
from wepppy.rq.webhook_dispatcher import claim, run
from wepppy.rq.webhook_settlement import Member

repo = Path(__file__).resolve().parents[5]
import sys
if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(dir=repo/'.pytest_cache', prefix='webhook-restore-') as folder:
        Path(folder).chmod(0o777)
        socket = str(Path(folder)/'redis.sock')
        command = ['redis-server', '--port', '0', '--unixsocket', socket, '--unixsocketperm', '777', '--dir', folder, '--save', '', '--appendonly', 'no']
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = None
        try:
            remote = '/workdir/wepppy/' + str(Path(folder).relative_to(repo))
            client = subprocess.Popen(['wctl','exec','-T','-e','PYTHONPATH=/workdir/wepppy','weppcloud','/opt/venv/bin/python',str(Path(__file__).relative_to(repo)),remote])
            deadline = time.monotonic() + 60
            while not (Path(folder)/'ready').exists():
                if client.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Container reservation barrier failed')
                time.sleep(.05)
            redis.Redis(unix_socket_path=socket).save()
            process.terminate()
            process.wait(timeout=5)
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    if redis.Redis(unix_socket_path=socket).ping():
                        break
                except redis.RedisError:
                    time.sleep(.02)
            (Path(folder)/'restored').touch()
            assert client.wait(timeout=60) == 0
        finally:
            if client is not None and client.poll() is None:
                client.terminate()
                client.wait(timeout=5)
            process.terminate()
            process.wait(timeout=5)
    raise SystemExit(0)
from wepppy.microservices.rq_engine.webhooks import Submission, AdmissionError
folder = sys.argv[1]
socket = str(Path(folder)/'redis.sock')
connection = redis.Redis(unix_socket_path=socket)
try:
    identity = connection.info('server')['run_id']
    os.environ.update(RQ_WEBHOOK_ENVIRONMENT='disposable-restart', RQ_WEBHOOK_ADMISSION='enabled',
                      RQ_WEBHOOK_INSTRUMENTATION='rq-wh-01', RQ_WEBHOOK_REDIS_RUN_ID=identity)
    connection.sadd('rq:workers', 'rq:worker:fixture')
    connection.hset('rq:worker:fixture', mapping={'queues': 'default,batch',
        'webhook_configuration': json.dumps({'protocol': 'rq-wh-01', 'environment': 'disposable-restart'})})
    submission = Submission(connection, options=('https://example.com/unused', 'restart-intent-001'),
        claims={'iss': 'fixture', 'token_class': 'user'}, principal=SimpleNamespace(kind='human', user_id=1),
        operation='run-wepp', resource={'type': 'run', 'id': 'fixture'}, payload={})
    store = submission.store
    _, delivery = store.reserve(principal='fixture-delivery', key='delivery-intent-001', digest='fixture',
        operation='run-wepp', resource={'type': 'run', 'id': 'fixture'}, url='https://example.com/unused',
        job_id='fixture-delivery-root')
    with connection.pipeline() as pipe:
        store.record_member(Member(delivery['job_id'], delivery['job_id'], None, 'finished',
                                   producer_closed=True, changed_at=time.time()), pipeline=pipe)
        store.published(delivery['job_id'], {'job_id': delivery['job_id']}, pipeline=pipe)
        pipe.execute()
    assert store.evaluate(delivery['job_id']) == 'delivery_pending'
    (Path(folder)/'ready').touch()
    deadline = time.monotonic()+60
    while not (Path(folder)/'restored').exists():
        assert time.monotonic() < deadline
        time.sleep(.05)
    assert connection.info('server')['run_id'] != identity
    queue = Queue('default', connection=connection)
    try:
        submission.enqueue(queue, json.loads, args=('1',))
    except AdmissionError as exc:
        admission_code = exc.code
    else:
        raise AssertionError('Old reservation published after Redis restart')
    assert queue.count == 0 and not connection.exists('rq:job:' + submission.job_id)
    assert claim(store, delivery['job_id'], time.time(), redis_run_id=identity) is None
    try:
        run(store, dispatch=True, once=True, redis_run_id=identity)
    except ValueError:
        refused_old_arm = True
    else:
        refused_old_arm = False
    run(store, dispatch=False, once=True)
    assert store.read(delivery['job_id']).get('attempts', 0) == 0
    evidence = {'real_rdb_restore': True, 'redis_identity_changed': True,
                'publication_rejected': admission_code, 'published_jobs': queue.count,
                'stale_dispatch_arm_rejected': refused_old_arm, 'paused_restore_attempts': 0}
    assert refused_old_arm
    (repo/'docs/work-packages/20261027_rq_webhooks/artifacts/restart_restore_probe.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))
finally:
    connection.close()
