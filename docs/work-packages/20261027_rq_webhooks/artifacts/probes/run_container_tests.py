"""Run wctl container tests against a disposable host Redis Unix socket.

Container image has redis-py but no redis-server binary. The repository bind mount
provides the socket; no shared Redis is accessed. Pass pytest arguments after this
script. Host Python requires redis-py (use .venv/bin/python).
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time

import redis

root = Path(__file__).resolve().parents[5]
with tempfile.TemporaryDirectory(prefix='webhook-', dir=root / '.pytest_cache') as folder:
    Path(folder).chmod(0o777)
    socket = Path(folder) / 'redis.sock'
    server = subprocess.Popen(['redis-server', '--port', '0', '--unixsocket', str(socket),
                               '--unixsocketperm', '777', '--save', '', '--appendonly', 'no'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = redis.Redis(unix_socket_path=str(socket))
    try:
        for _ in range(100):
            try:
                if client.ping():
                    break
            except redis.ConnectionError:
                time.sleep(.02)
        else:
            raise RuntimeError('Disposable Redis failed to start')
        client.set('batch-boundary-test-server', 'disposable')
        container_socket = '/workdir/wepppy/' + str(socket.relative_to(root))
        probe_env = []
        for name in ('RQ_WEBHOOK_PROFILE_HOOKS', 'RQ_WEBHOOK_PROBE_TRANSITIONS'):
            if name in os.environ:
                probe_env.extend(['-e', name + '=' + os.environ[name]])
        result = subprocess.run(['wctl', 'exec', '-T', '-e', 'RQ212_TEST_REDIS_SOCKET=' + container_socket,
                                 '-e', 'BATCH_BOUNDARY_TEST_REDIS_SOCKET=' + container_socket,
                                 '-e', 'PYTHONPATH=/workdir/wepppy', *probe_env, 'weppcloud',
                                 '/opt/venv/bin/python', '-m', 'pytest', *sys.argv[1:]], cwd=root)
    finally:
        client.close()
        server.terminate()
        server.wait(timeout=5)
sys.exit(result.returncode)
