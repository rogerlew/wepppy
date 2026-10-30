"""DM-01 durable state, real lifecycle serialization and native soil policy."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
import shutil
import zipfile

import pytest

from wepppy.nodb.core.ron import Ron
from wepppy.nodb.core.wepp import Wepp
from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard

pytestmark = pytest.mark.integration


def make_ron(path):
    path.mkdir(exist_ok=True)
    return Ron(str(path), 'canada-wbt-mofe.cfg', initialize_components=False)


def test_missing_false_and_enable_refreshes_unrelated_durable_state(tmp_path):
    ron = make_ron(tmp_path)
    original = (tmp_path / 'ron.nodb').read_bytes()
    assert ron.developer_mode is False
    assert (tmp_path / 'ron.nodb').read_bytes() == original
    fresh = Ron._hydrate_instance(str(tmp_path), False, False, False, use_redis_cache=False)
    fresh.name = 'Keep this concurrent update'
    ron.enable_developer_mode()
    ron.enable_developer_mode()
    loaded = Ron.load_detached(str(tmp_path))
    assert loaded.developer_mode is True
    assert loaded.name == 'Keep this concurrent update'
    with pytest.raises(AttributeError):
        ron.developer_mode = False


@pytest.mark.parametrize('value', [None, 'true', 'false', 0, 1, [], {}])
def test_malformed_persisted_mode_does_not_activate(tmp_path, value):
    ron = make_ron(tmp_path)
    with ron.locked():
        ron._developer_mode = value
    original = (tmp_path / 'ron.nodb').read_bytes()
    with pytest.raises(ValueError, match='expected a boolean'):
        ron.enable_developer_mode()
    assert (tmp_path / 'ron.nodb').read_bytes() == original


def test_activation_waits_for_real_capture_guard(tmp_path):
    ron = make_ron(tmp_path / 'source')
    entered = Event()
    def activate():
        entered.set()
        ron.enable_developer_mode()
    # The actual same guard used by fork/archive spans both member copies.
    with ThreadPoolExecutor(max_workers=1) as pool:
        with catalog_lifecycle_guard(ron.wd):
            future = pool.submit(activate)
            assert entered.wait(2)
            assert not future.done()
            clone = tmp_path / 'clone'
            clone.mkdir()
            shutil.copy2(Path(ron.wd) / 'ron.nodb', clone / 'ron.nodb')
            assert Ron.load_detached(str(clone)).developer_mode is False
        future.result(timeout=10)
    with catalog_lifecycle_guard(ron.wd):
        with zipfile.ZipFile(tmp_path / 'snapshot.zip', 'w') as archive:
            archive.write(Path(ron.wd) / 'ron.nodb', 'ron.nodb')
    with zipfile.ZipFile(tmp_path / 'snapshot.zip') as archive:
        archive.extractall(clone)
    assert Ron.load_detached(str(clone)).developer_mode is True


def test_project_policy_drives_saved_and_prepared_anisotropy(tmp_path, monkeypatch):
    from tests.nodb.test_soil_anisotropy import _soil_source, _mofe_files
    from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
    from wepppy.wepp.soils.utils import WeppSoilUtil
    ron = make_ron(tmp_path)
    monkeypatch.setattr(Wepp, 'clean', lambda self: None)
    wepp = Wepp(str(tmp_path), 'canada-wbt-mofe.cfg')
    with wepp.locked():
        wepp._multi_ofe = True
        wepp._run_wepp_ui = True
    with pytest.raises(ValueError):
        wepp.parse_inputs({'soil_anisotropy_upper': 101, 'soil_anisotropy_lower': 11, 'developer_mode': True})
    assert ron.developer_mode is False
    ron.enable_developer_mode()
    wepp.parse_inputs({'soil_anisotropy_upper': 101, 'soil_anisotropy_lower': 11})
    loaded = Wepp.load_detached(str(tmp_path))
    assert (loaded.soil_anisotropy_upper, loaded.soil_anisotropy_lower) == (101, 11)
    before = (tmp_path / 'wepp.nodb').read_bytes()
    for invalid in [True, False, float('inf'), float('nan'), 0, -1]:
        with pytest.raises(ValueError):
            wepp.parse_inputs({'soil_anisotropy_upper': invalid})
        assert (tmp_path / 'wepp.nodb').read_bytes() == before
    source = _soil_source(tmp_path)
    _mofe_files(tmp_path)
    source_bytes = source.read_bytes()
    runs = tmp_path / 'wepp/runs'
    runs.mkdir(parents=True, exist_ok=True)
    prep_multi_ofe_hillslope(('101', 1, str(tmp_path), str(runs), 1, .02, .4,
        False, 300, False, 500, False, 1000, None, False, False, (101, 11), True))
    prepared = WeppSoilUtil(str(runs / 'p1.sol'))
    assert [[h['solthk'] for h in ofe['horizons']] for ofe in prepared.obj['ofes']] == [[100, 200, 500, 800]] * 2
    assert [[h['anisotropy'] for h in ofe['horizons']] for ofe in prepared.obj['ofes']] == [[101, 101, 101, 11]] * 2
    assert source.read_bytes() == source_bytes
