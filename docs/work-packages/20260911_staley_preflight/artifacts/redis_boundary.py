"""Disposable real Redis/NoDb projection check; run in the dev web container."""
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow
from wepppy.nodb.mods.postfire_debris_flow.preflight import notify
from wepppy.nodb.redis_prep import RedisPrep

with TemporaryDirectory(prefix='pfdf-preflight-') as wd:
    obj = PostfireDebrisFlow(wd, 'disturbed9002_wbt.cfg')
    prep = RedisPrep.getInstance(wd)
    key = 'timestamps:run_postfire_debris_flow'
    try:
        notify(wd)
        assert prep.redis.hget(prep.run_id, key) is None
        def publish(state):
            state['active_dnbr'] = {'id': 'a'*32, 'snapshot': {}, 'artifacts': {}}
            state['last_successful_run'] = {
                'id': 'b'*32, 'snapshot': {'dnbr': 'a'*32, 'frequency': 'cli'},
                'completed_at': '2026-09-11T02:34:06+00:00', 'artifacts': {}, 'partial': True,
            }
        obj.change(publish)
        expected = str(int(datetime.fromisoformat('2026-09-11T02:34:06+00:00').timestamp()))
        assert prep.redis.hget(prep.run_id, key) == expected
        assert json.loads(Path(prep.dump_filepath).read_text())[key] == expected
        prep.redis.delete(prep.run_id)
        prep = RedisPrep.getInstance(wd)
        assert prep.redis.hget(prep.run_id, key) == expected
        obj.change(lambda state: state['active_dnbr'].update(id='c'*32))
        assert prep.redis.hget(prep.run_id, key) is None
        assert key not in json.loads(Path(prep.dump_filepath).read_text())
        prep.redis.delete(prep.run_id)
        prep = RedisPrep.getInstance(wd)
        assert prep.redis.hget(prep.run_id, key) is None
        print('PASS real NoDb publication, Redis lock/pipeline, original timestamp, replacement, dump restoration')
    finally:
        prep.redis.delete(prep.run_id)
