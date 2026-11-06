"""One bounded heartbeat exchange in the existing worker; never enqueue work."""
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import signal
import sys
import time

import redis
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs


def read(path):
    return json.loads(path.read_text())


def finite_time(value, now, maximum_age=60):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not -5 <= now - value <= maximum_age:
        raise ValueError('Missing, stale or future heartbeat')


def probe(root, expected_manifest_digest):
    started_monotonic = time.monotonic()
    if (os.getuid(), os.getgid()) != (1002, 130) or os.getenv('EXTERNAL_HOST') != 'wepp.cloud':
        raise ValueError('Wrong worker identity/environment')
    if not root.is_absolute() or root.resolve() != root or root.stat().st_mode & 0o077:
        raise ValueError('Evidence directory must be private and canonical')
    manifest = read(root / 'manifest.json')
    actual_digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if actual_digest != expected_manifest_digest or manifest['absolute_deadline'] != 1794127194.157908:
        raise ValueError('Supervisor/collector manifest differs')
    worker = next(item for item in manifest['host_runtime_images']['wepp1'] if item['service'] == 'rq-worker')
    if socket.gethostname() != worker['id'][:12]:
        raise ValueError('Worker container changed')
    now = time.time()
    if now >= manifest['absolute_deadline']:
        raise ValueError('Original deadline reached')
    kwargs = redis_connection_kwargs(RedisDB.RQ)
    kwargs.update(socket_connect_timeout=5, socket_timeout=5)
    connection = redis.Redis(**kwargs)
    pause_key = 'query-catalog:batch-admission:v1:paused'
    owner = manifest['pause_owner'].encode()
    pause = connection.get(pause_key)
    if (root / 'stop.json').exists():
        raise ValueError('Collector stopped')
    if (root / 'completed.json').exists():
        completed = read(root / 'completed.json')
        activation = read(root / 'activation.json')
        target = read(root / 'target-cycle.json')
        proof = read(root / 'artifact-acceptance.json')
        if (pause or completed['cycle'] != target['cycle'] or proof['cycle'] != target['cycle']
                or target['cycle'] == activation['baseline_cycle']
                or target['started_at'] < activation['started_at']
                or not isinstance(completed['time'], (int, float))
                or not math.isfinite(completed['time'])
                or not activation['started_at'] <= completed['time'] <= manifest['absolute_deadline']
                or completed.get('artifact_proof') != proof
                or proof.get('artifacts_verified') is not True
                or proof.get('pending_age_coverage_accepted') is not True):
            raise ValueError('Completion evidence is not coherent')
        return {'state': 'completed', 'checked_at': now, 'cycle': target['cycle']}
    marker = root / 'observer-start.json'
    if not marker.exists():
        if pause != owner:
            raise ValueError('Startup has no owned admission pause')
        return {'state': 'starting', 'checked_at': now}
    start = read(marker)
    pid = start['pid']
    if type(pid) is not int or pid <= 1:
        raise ValueError('Invalid collector PID')
    command = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
    if str(root / 'observe_general_catalog.py').encode() not in command or str(root).encode() not in command:
        raise ValueError('Collector PID identity changed')
    previous = root / 'parent-heartbeat.json'
    old = None
    if previous.exists():
        old = read(previous)
        finite_time(old['time'], now, maximum_age=45)
        if (old['nonce'] != manifest['supervision_nonce'] or old['observer_pid'] != pid
                or old['worker_hostname'] != socket.gethostname()):
            raise ValueError('Parent heartbeat identity mismatch')
    heartbeat = root / 'heartbeat.json'
    if heartbeat.exists():
        beat = read(heartbeat)
        finite_time(beat['time'], now)
        if beat['pid'] != pid or type(beat['samples']) is not int or beat['samples'] < 1:
            raise ValueError('Collector heartbeat identity/progress invalid')
        if (root / 'activation.json').exists() and pause:
            raise ValueError('Admission was paused after activation')
    else:
        finite_time(start['started_at'], now)
        if pause != owner:
            raise ValueError('Collector startup lost its owned pause')
        beat = {'samples': 0, 'time': start['started_at']}
    checked_at = time.time()
    if time.monotonic() - started_monotonic >= 10 or checked_at >= manifest['absolute_deadline']:
        raise ValueError('Probe duration or observation deadline exceeded')
    if old is not None:
        finite_time(old['time'], checked_at, maximum_age=45)
    finite_time(beat['time'], checked_at)
    receipt = {'nonce': manifest['supervision_nonce'], 'observer_pid': pid,
               'worker_hostname': socket.gethostname(), 'time': checked_at}
    temporary = root / 'parent-heartbeat.tmp'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(receipt, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, previous)
    return {'state': 'running' if beat['samples'] else 'starting', 'checked_at': time.time(),
            'observer_pid': pid, 'samples': beat['samples'], 'heartbeat_time': beat['time']}


if __name__ == '__main__':
    def expired(signum, frame):
        raise RuntimeError('Supervision probe deadline exceeded')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(10)
    try:
        print(json.dumps(probe(Path(sys.argv[1]), sys.argv[2])))
    finally:
        signal.alarm(0)
