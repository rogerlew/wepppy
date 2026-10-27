import json
import math
import os
import threading
import sys
import urllib.request
import urllib.error
from uuid import uuid4

import redis
import rq
from rq import Queue
from rq_dashboard.app import create_app
from werkzeug.serving import make_server

socket = '/tmp/rq212-redis/redis.sock'
guard = redis.Redis(unix_socket_path=socket, db=0)
assert guard.get('batch-boundary-test-server') == b'disposable'
connection = redis.Redis(unix_socket_path=socket, db=5)
name = 'rq212-dashboard-' + str(uuid4())
queue = Queue(name, connection=connection)
parent = queue.enqueue(math.sqrt, 4, job_id=name + '-parent')
child = queue.enqueue(math.sqrt, 9, depends_on=parent, job_id=name + '-child')
os.environ['RQ_DASHBOARD_REDIS_URL'] = 'unix://' + socket + '?db=5'
os.environ['RQ_DASHBOARD_URL_PREFIX'] = '/rq-dashboard'
app = create_app()
server = make_server('127.0.0.1', 0, app)
thread = threading.Thread(target=server.serve_forever)
thread.start()
try:
    url = 'http://127.0.0.1:%d/rq-dashboard/0/data/job/%s.json' % (server.server_port, child.id)
    try:
        with urllib.request.urlopen(url) as response:
            payload = json.load(response)
            status = response.status
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, {'error': exc.reason}
    print(json.dumps({'rq':rq.__version__, 'http_status':status, 'payload':payload}, sort_keys=True))
    assert status == 200
    assert payload['id'] == child.id
    assert payload['status'] == 'deferred'
    assert payload['depends_on'] == [parent.id]
    assert payload['depends_on_status'] == ['active']
    if '--orphan' in sys.argv:
        from rq.executions import Execution
        orphan = queue.create_job(math.sqrt, args=(16,), job_id=name + '-orphan')
        orphan.save()
        pipeline = connection.pipeline()
        execution = Execution.create(orphan, ttl=60, pipeline=pipeline)
        pipeline.execute()
        connection.delete(orphan.key)
        try:
            empty_url = 'http://127.0.0.1:%d/rq-dashboard/queue/%s/started/empty' % (server.server_port, queue.name)
            try:
                with urllib.request.urlopen(urllib.request.Request(empty_url, data=b'', method='POST')) as response:
                    empty_payload = json.load(response)
                    empty_status = response.status
            except urllib.error.HTTPError as exc:
                empty_status, empty_payload = exc.code, {'error': exc.reason}
            remaining = connection.zcard(queue.started_job_registry.key)
            print(json.dumps({'rq':rq.__version__, 'orphan_http_status':empty_status,
                              'payload':empty_payload, 'remaining_started':remaining}, sort_keys=True))
            assert empty_status == 200
            assert remaining == 0
        finally:
            execution.delete(job=orphan, pipeline=connection)
            connection.delete(orphan.execution_registry.key)
finally:
    server.shutdown()
    thread.join()
    child.delete()
    parent.delete()
    queue.delete(delete_jobs=False)
    connection.close()
