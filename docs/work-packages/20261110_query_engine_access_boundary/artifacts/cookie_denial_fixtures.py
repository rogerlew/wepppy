"""Controlled forest fixtures for the admitted-page/query-denial follow-up."""
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from wepppy.weppcloud.app import app, db, User, Run, runs_users, user_datastore
from wepppy.nodb.core import Ron, Wepp
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.weppcloud.utils.helpers import get_wd, redis_wd_cache_client, get_batch_root_dir
from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard, invalidate_catalog_incarnation

manifest = Path('/workdir/wepppy/docker/secrets/qe-cookie-denial-followup.json')
with app.app_context():
    if '--cleanup' in sys.argv:
        import redis
        from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
        sessions = redis.Redis(**redis_connection_kwargs(RedisDB.SESSION))
        data = json.loads(manifest.read_text())
        assert data['ordinary'].startswith('qe-cookie-denial-')
        assert data['group'].startswith('qe-cookie-denial-')
        for runid in (data['ordinary'], data['batch']):
            wd = Path(get_wd(runid, prefer_active=False, read_only=True))
            expected = (Path('/wc1/runs/qe') / runid if runid == data['ordinary'] else
                        Path(get_batch_root_dir()) / data['group'] / 'runs/child')
            assert wd == expected
            if wd.exists():
                clear_nodb_file_cache(runid, wd_override=wd)
                with catalog_lifecycle_guard(wd):
                    invalidate_catalog_incarnation(wd)
                    shutil.rmtree(wd)
            if redis_wd_cache_client is not None:
                redis_wd_cache_client.delete(runid)
            keys = list(sessions.scan_iter(match=f'auth:session:run:{runid}:*'))
            if keys:
                sessions.delete(*keys)
            row = Run.query.filter_by(runid=runid).one_or_none()
            if row:
                db.session.execute(runs_users.delete().where(runs_users.c.run_id == row.id))
                db.session.delete(row)
            db.session.commit()
        shutil.rmtree(Path(get_batch_root_dir()) / data['group'])
        manifest.unlink()
        print('Removed ordinary and Batch fixtures, row/associations, caches, markers and manifest')
    else:
        assert not manifest.exists()
        import pyarrow as pa
        import pyarrow.parquet as pq
        nonce = uuid.uuid4().hex[:10]
        data = {'ordinary': 'qe-cookie-denial-' + nonce, 'group': 'qe-cookie-denial-' + nonce,
                'config': 'disturbed9002'}
        data['batch'] = 'batch;;' + data['group'] + ';;child'
        with os.fdopen(os.open(manifest, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as stream:
            json.dump(data, stream)
        (Path(get_batch_root_dir()) / data['group'] / '_base').mkdir(parents=True, exist_ok=False)
        for runid in (data['ordinary'], data['batch']):
            wd = Path(get_wd(runid, prefer_active=False, read_only=True))
            wd.mkdir(parents=True, exist_ok=False)
            group_args = {'run_group': 'batch', 'group_name': data['group']} if runid == data['batch'] else {}
            ron = Ron(str(wd), 'disturbed9002.cfg', **group_args)
            ron.set_map([-117.1, 46.6, -117.0, 46.7], [-117.05, 46.65], 12)
            Wepp.getInstance(str(wd))
            (wd / 'data').mkdir()
            pq.write_table(pa.table({'value': [3, 7]}), wd / 'data/sample.parquet')
        user_datastore.create_run(data['ordinary'], data['config'],
                                 User.query.filter_by(email='dev-agent@example.com').one())
        print('Created one ordinary private run and one private Batch base/child')
