import os
from pathlib import Path
import pytest
from wepppy.nodb.core.soils import Soils

pytestmark = pytest.mark.integration


def test_json_cache_selection_persists_and_clear_keeps_legacy(tmp_path, monkeypatch, caplog):
    socket_path = os.environ.get('SOIL_PROVENANCE_TEST_REDIS_SOCKET')
    if not socket_path:
        pytest.skip('Requires an explicitly selected disposable Redis socket')
    import redis
    client = redis.StrictRedis(unix_socket_path=socket_path, decode_responses=True)
    client.ping()
    monkeypatch.setattr('wepppy.nodb.base.redis_lock_client', client)
    from wepppy.soils.ssurgo.source import SoilDataSourceError
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)
    wd = tmp_path / 'run'
    wd.mkdir()
    soils = Soils(str(wd), 'disturbed9002.cfg')
    legacy = Path(soils.ssurgo_cache_db_path)
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_bytes(b'legacy sentinel')
    soils.configure_soil_data_source(endpoint='http://localhost:18080/Tabular/post.rest', profile='wepppy-json-v1', release='r1')
    loaded = Soils.getInstance(str(wd), ignore_lock=True)
    assert loaded.soil_data_source['release'] == 'r1'
    selected = Path(loaded.ssurgo_cache_db_path)
    assert selected != legacy
    selected.write_bytes(b'new cache')
    loaded._clear_project_surgo_cache()
    assert not selected.exists() and legacy.read_bytes() == b'legacy sentinel'
    with pytest.raises(SoilDataSourceError):
        loaded.configure_soil_data_source(endpoint='http://user:secret@localhost/Tabular/post.rest', profile='wepppy-json-v1', release='r2')
    assert 'user:secret' not in caplog.text
    assert Soils.getInstance(str(wd), ignore_lock=True).soil_data_source['release'] == 'r1'
    loaded.configure_soil_data_source()
    assert loaded.ssurgo_cache_db_path == str(legacy)
