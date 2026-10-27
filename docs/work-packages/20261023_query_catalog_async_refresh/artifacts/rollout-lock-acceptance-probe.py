"""Bounded actual-guard canary, only the retained production scratch scope."""
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import socket
import sys
import threading
import time

ROOT = Path('/wc1/query-catalog-validation/20261026/async-preflight-1719')
WD = ROOT / 'runs/aa/aa-preflight'
role = sys.argv[1]
started = time.monotonic()
def emit(event, **fields):
    print(json.dumps(dict(event=event, role=role, epoch=time.time(), elapsed=time.monotonic()-started, **fields)), flush=True)
def deadline(_signum, _frame):
    raise TimeoutError('90-second process budget exceeded')
signal.signal(signal.SIGALRM, deadline)
signal.alarm(90)
os.environ['QUERY_CATALOG_ROOTS_JSON'] = json.dumps([dict(path=str(ROOT/'runs'), namespace='qcat-rollout-preflight-20261026', coordination=str(ROOT/'locks'), layout='sharded')])
os.environ['QUERY_CATALOG_REFRESH_ENABLED'] = 'false'
assert os.getuid() == 1002 and os.getgid() == 130
assert WD.is_dir()
cr = importlib.import_module('wepppy.query_engine.catalog_refresh')
locks = sorted((ROOT/'locks').glob('*.lock'))
assert len(locks) == 1, locks
lock = locks[0]
initial = lock.stat()
emit('identity', hostname=socket.gethostname(), uid=os.getuid(), gid=os.getgid(), groups=os.getgroups(), lock_path=str(lock), inode=initial.st_ino, mode=oct(initial.st_mode & 0o7777), source_sha256=hashlib.sha256(Path(cr.__file__).read_bytes()).hexdigest())
heartbeats = []
done = threading.Event()
def beat():
    while not done.wait(.1): heartbeats.append(time.monotonic())
thread = threading.Thread(target=beat, daemon=True)
thread.start()
original_lockf = fcntl.lockf
def timed_lockf(fd, operation, *args):
    t = time.monotonic()
    emit('lockf_enter', operation=operation)
    try:
        result = original_lockf(fd, operation, *args)
    except BaseException as exc:
        emit('lockf_error', operation=operation, seconds=time.monotonic()-t, error=repr(exc))
        raise
    emit('lockf_exit', operation=operation, seconds=time.monotonic()-t)
    return result
fcntl.lockf = timed_lockf
try:
    if role == 'publish':
        act = importlib.import_module('wepppy.query_engine.activate')
        emit('publication_start')
        t = time.monotonic()
        act.activate_query_engine(WD, run_interchange=False, force_refresh=True)
        cr.ensure_catalog_fresh(WD, required_paths=['probe.parquet'])
        catalog = json.loads((WD/'_query_engine/catalog.json').read_text())
        emit('publication_complete', seconds=time.monotonic()-t, catalog_sha256=hashlib.sha256((WD/'_query_engine/catalog.json').read_bytes()).hexdigest(), catalog=catalog)
    else:
        repeats = 3 if role == 'uncontended' else 1
        for repeat in range(repeats):
            t = time.monotonic()
            emit('guard_request', repeat=repeat)
            with cr.catalog_lifecycle_guard(WD):
                emit('acquired', repeat=repeat, wait_seconds=time.monotonic()-t)
                if role == 'holder': time.sleep(8)
                emit('release_start', repeat=repeat)
            emit('released', repeat=repeat)
    final = lock.stat()
    assert final.st_ino == initial.st_ino
    emit('success', inode_unchanged=True)
except BaseException as exc:
    emit('error', error=repr(exc))
    raise
finally:
    done.set()
    thread.join(timeout=1)
    gaps = [b-a for a,b in zip([started]+heartbeats, heartbeats+[time.monotonic()])]
    emit('heartbeat', samples=len(heartbeats), max_gap_seconds=max(gaps))
    signal.alarm(0)
