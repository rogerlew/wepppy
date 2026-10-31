"""Bounded disposable benchmark; invoke with isolated Redis socket and scratch root."""
import argparse
import gc
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import types
from uuid import uuid4

import redis
from wepppy.nodb import redis_prep

parser = argparse.ArgumentParser()
parser.add_argument('socket')
parser.add_argument('scratch')
args = parser.parse_args()
root = Path(args.scratch) / ('bench-' + uuid4().hex)
root.mkdir(parents=True)
os.environ['QUERY_CATALOG_ROOTS_JSON'] = json.dumps([
    {'path': str(root), 'namespace': root.name, 'layout': 'flat',
     'coordination': str(root.parent / (root.name + '-locks'))}])
client = redis.StrictRedis(unix_socket_path=args.socket, db=0, decode_responses=True)
assert client.get('batch-boundary-test-server') == 'disposable'
baseline = types.ModuleType('redisprep_baseline')
source = subprocess.check_output(['git', 'show', '967627f4c:wepppy/nodb/redis_prep.py'], text=True)
exec(compile(source, 'redisprep_baseline.py', 'exec'), baseline.__dict__)
result = {'uid': os.getuid(), 'gid': os.getgid(), 'root': str(root), 'iterations': 100}
for label, module in [('baseline', baseline), ('candidate', redis_prep)]:
    module.redis_client = lambda *a, **k: client
    wd = root / (label + '-' + uuid4().hex)
    wd.mkdir()
    prep = module.RedisPrep.getInstance(str(wd))
    client.hset(prep.run_id, mapping={f'timestamps:field-{i}': str(i) for i in range(64)})
    prep.dump()
    timings = {}
    for operation, action in [('setter', lambda: prep.set_rq_job_id('work', 'accepted-job')),
                              ('startup', lambda: module.RedisPrep.getInstance(str(wd)))]:
        samples = []
        for _ in range(100):
            start = time.perf_counter()
            action()
            samples.append((time.perf_counter() - start) * 1000)
        timings[operation] = {'median_ms': statistics.median(samples), 'p95_ms': sorted(samples)[94]}
    gc.collect()
    before = len(list(Path('/proc/self/fd').iterdir()))
    for _ in range(1000):
        module.RedisPrep.getInstance(str(wd))
    gc.collect()
    timings['fd_delta_after_1000_wrappers'] = len(list(Path('/proc/self/fd').iterdir())) - before
    timings['snapshot_bytes'] = (wd / 'redisprep.dump').stat().st_size
    result[label] = timings
    client.delete(prep.run_id)
client.close()
print(json.dumps(result, indent=2))
