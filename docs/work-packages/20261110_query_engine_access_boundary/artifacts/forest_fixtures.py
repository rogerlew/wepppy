"""Disposable forest fixtures; run inside the existing weppcloud container."""
import json
import shutil
import sys
import uuid
from pathlib import Path
from wepppy.weppcloud.app import app, db, User, Run, runs_users, user_datastore
from wepppy.nodb.core import Ron, Wepp
from wepppy.weppcloud.utils.helpers import get_wd, redis_wd_cache_client
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard, invalidate_catalog_incarnation

manifest = Path('/workdir/wepppy/docker/secrets/qe-boundary-fixtures.json')
with app.app_context():
    if '--cleanup' in sys.argv:
        data = json.loads(manifest.read_text())
        import redis
        from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
        sessions = redis.Redis(**redis_connection_kwargs(RedisDB.SESSION))
        for runid in data['runs']:
            assert runid.startswith(data['prefix']) and data['prefix'].startswith('qe-boundary-')
            path = Path(get_wd(runid, prefer_active=False, read_only=True))
            assert path == Path('/wc1/runs/qe') / runid
            row = Run.query.filter_by(runid=runid).one_or_none()
            if row:
                db.session.execute(runs_users.delete().where(runs_users.c.run_id == row.id))
                db.session.delete(row)
            if path.exists():
                clear_nodb_file_cache(runid, wd_override=path)
                if redis_wd_cache_client is not None:
                    redis_wd_cache_client.delete(runid)
                with catalog_lifecycle_guard(path):
                    invalidate_catalog_incarnation(path)
                    shutil.rmtree(path)
            keys = list(sessions.scan_iter(match=f'auth:session:run:{runid}:*'))
            if keys:
                sessions.delete(*keys)
            db.session.commit()

        manifest.unlink()
        print('Cleaned fixture run rows, ownership associations and directories:', len(data['runs']))
    else:
        assert not manifest.exists(), 'Existing fixture manifest requires cleanup first'
        import pyarrow as pa
        import pyarrow.parquet as pq
        user = User.query.filter_by(email='dev-agent@example.com').one()
        data = {'prefix': 'qe-boundary-' + uuid.uuid4().hex[:10] + '-', 'runs': [], 'config': 'disturbed9002'}
        for index in range(101):
            runid = data['prefix'] + str(index).zfill(3)
            wd = Path(get_wd(runid, prefer_active=False, read_only=True))
            wd.mkdir(parents=True, exist_ok=False)
            data['runs'].append(runid)
            manifest.write_text(json.dumps(data))
            ron = Ron(str(wd), 'disturbed9002.cfg')
            ron.set_map([-117.1, 46.6, -117.0, 46.7], [-117.05, 46.65], 12)
            Wepp.getInstance(str(wd))
            (wd/'data').mkdir()
            pq.write_table(pa.table({'value': [3, 7]}), wd/'data/sample.parquet')
            user_datastore.create_run(runid, data['config'], user)
            if index == 100:
                (wd/'PUBLIC').touch()
        print('Created synthetic private/public fixtures:', 100, 1)
