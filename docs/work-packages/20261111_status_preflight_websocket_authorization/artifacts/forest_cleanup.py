"""Operator-only cleanup of the exact disposable browser receipt identities."""
import json
import sys
from pathlib import Path

from redis import Redis
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.project_rq import delete_run_rq
from wepppy.weppcloud.app import app
from wepppy.weppcloud.utils.helpers import get_wd, get_user_models, get_run_owners_lazy

runs = json.loads(sys.stdin.read())
assert 0 < len(runs) <= 2
receipt = []
with app.app_context():
    Run, User, datastore = get_user_models()
    for run in runs:
        runid = run['runid']
        assert run['config'] == '0' and ';' not in runid and '/' not in runid
        owners = get_run_owners_lazy(runid)
        assert owners and all(owner.email == 'dev-agent@example.com' for owner in owners)
        wd = get_wd(runid, prefer_active=False)
        delete_run_rq(runid, wd, delete_files=True)
        assert not Path(wd).exists()
        assert Run.query.filter(Run.runid == runid).first() is None
        with Redis(**redis_connection_kwargs(RedisDB.SESSION)) as conn:
            keys = list(conn.scan_iter(match=f'auth:session:run:{runid}:*'))
            if keys:
                conn.delete(*keys)
        with Redis(**redis_connection_kwargs(RedisDB.LOCK)) as conn:
            conn.delete(runid)
        receipt.append({'runid':runid,'directory_removed':True,'ownership_removed':True,'stream_markers_removed':len(keys)})
print(json.dumps(receipt))
