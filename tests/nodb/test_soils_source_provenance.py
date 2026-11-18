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
    selection_path = Path(str(selected) + '.selection.json')
    selection_path.write_text('{}')
    loaded._clear_project_surgo_cache()
    assert not selected.exists() and legacy.read_bytes() == b'legacy sentinel'
    assert not selection_path.exists()
    with pytest.raises(SoilDataSourceError):
        loaded.configure_soil_data_source(endpoint='http://user:secret@localhost/Tabular/post.rest', profile='wepppy-json-v1', release='r2')
    assert 'user:secret' not in caplog.text
    assert Soils.getInstance(str(wd), ignore_lock=True).soil_data_source['release'] == 'r1'
    loaded.configure_soil_data_source()
    assert loaded.ssurgo_cache_db_path == str(legacy)


def test_mirror_deployment_default_persists_policy_and_explicit_override(tmp_path, monkeypatch):
    socket_path = os.environ.get('SOIL_PROVENANCE_TEST_REDIS_SOCKET')
    if not socket_path:
        pytest.skip('Requires an explicitly selected disposable Redis socket')
    import redis
    client = redis.StrictRedis(unix_socket_path=socket_path, decode_responses=True)
    client.ping()
    monkeypatch.setattr('wepppy.nodb.base.redis_lock_client', client)
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)
    monkeypatch.setenv('SOIL_DATA_MODE', 'mirror-first')
    monkeypatch.setenv('SOIL_DATA_ENDPOINT', 'http://soil-api:8080/Tabular/post.rest')
    monkeypatch.setenv('SOIL_DATA_RELEASE', 'r1')
    wd = tmp_path / 'run'; wd.mkdir()
    soils = Soils(str(wd), 'disturbed9002.cfg')
    assert soils.soil_data_policy == 'mirror-first'
    monkeypatch.setenv('SOIL_DATA_RELEASE', 'r2')
    loaded = Soils.getInstance(str(wd), ignore_lock=True)
    assert loaded.soil_data_source['release'] == 'r1'
    assert loaded._soil_data_source_kwargs()['fallback_to_sda'] is True
    loaded.configure_soil_data_source()
    loaded = Soils.getInstance(str(wd), ignore_lock=True)
    assert loaded.soil_data_policy == 'explicit'
    assert loaded.soil_data_source['profile'] == 'legacy-xml'


@pytest.mark.parametrize('profile', ['legacy-xml', 'wepppy-json-v1'])
def test_legacy_hydration_respects_explicit_config(tmp_path, monkeypatch, profile):
    socket_path = os.environ.get('SOIL_PROVENANCE_TEST_REDIS_SOCKET')
    if not socket_path:
        pytest.skip('Requires an explicitly selected disposable Redis socket')
    import redis
    client = redis.StrictRedis(unix_socket_path=socket_path, decode_responses=True)
    client.ping()
    monkeypatch.setattr('wepppy.nodb.base.redis_lock_client', client)
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)
    monkeypatch.setenv('SOIL_DATA_MODE', 'invalid-deployment-setting')
    config = '0.cfg?soils:soil_data_profile=' + profile
    if profile == 'wepppy-json-v1':
        config += '&soils:soil_data_endpoint=http://localhost:18080/Tabular/post.rest&soils:soil_data_release=explicit-r1'
    wd = tmp_path / 'run'; wd.mkdir()
    soils = Soils(str(wd), config)
    expected = soils.soil_data_source
    with soils.locked():
        del soils._soil_data_source
        del soils._soil_data_policy
    loaded = Soils.getInstance(str(wd), ignore_lock=True)
    assert loaded.soil_data_source == expected
    assert loaded.soil_data_policy == 'explicit'
