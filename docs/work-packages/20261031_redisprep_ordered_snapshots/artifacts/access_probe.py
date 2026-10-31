"""Run sequentially in existing web/worker/archive/browser containers, no jobs."""
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('role')
parser.add_argument('socket')
parser.add_argument('root')
args = parser.parse_args()
root = Path(args.root)
wd = root / 'access-project'
if args.role == 'weppcloud':
    wd.mkdir(parents=True)
os.environ['QUERY_CATALOG_ROOTS_JSON'] = json.dumps([
    {'path': str(root), 'namespace': 'rps-isolated-access', 'layout': 'flat',
     'coordination': str(root.parent / 'access-locks')}])
if args.role != 'browse':
    import redis
    from wepppy.nodb import redis_prep
    client = redis.StrictRedis(unix_socket_path=args.socket, db=0, decode_responses=True)
    assert client.get('batch-boundary-test-server') == 'disposable'
    redis_prep.redis_client = lambda *a, **k: client
    prep = redis_prep.RedisPrep.getInstance(str(wd))
    if args.role == 'weppcloud':
        prep.set_rq_job_id('access', 'retained-receipt')
        (wd / 'redisprep.dump').chmod(0o640)
    else:
        assert prep.get_rq_job_id('access') == 'retained-receipt'
        prep.update_metadata({f'timestamps:{args.role}': 42})
    client.close()
payload = json.loads((wd / 'redisprep.dump').read_text())
assert payload['rq:access'] == 'retained-receipt'
info = (wd / 'redisprep.dump').stat()
assert (info.st_uid, info.st_gid, info.st_mode & 0o777) == (1000, 993, 0o640)
print(json.dumps({'role': args.role, 'uid': os.getuid(), 'gid': os.getgid(),
                  'file_uid': info.st_uid, 'file_gid': info.st_gid, 'mode': oct(info.st_mode & 0o777),
                  'fields': sorted(payload)}))
