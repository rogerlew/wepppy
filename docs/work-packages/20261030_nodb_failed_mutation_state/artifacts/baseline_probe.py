"""Discovery probe: asserts the existing defect, not the desired contract."""
import pytest
import wepppy.nodb.base as base
from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub


def test_failed_mutation_contaminates_reused_controller(tmp_path, monkeypatch):
    monkeypatch.setattr(base, 'redis_lock_client', _RedisStub())
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    controller = _DummyNoDb(str(tmp_path))
    with controller.locked():
        controller.value = 'A'
        controller.nested = {'items': ['A']}
    held = _DummyNoDb.getInstance(str(tmp_path))
    with pytest.raises(ValueError, match='domain failure'):
        with held.locked():
            held.value = 'B'
            held.nested['items'].append('B')
            raise ValueError('domain failure')
    assert _DummyNoDb.load_detached(str(tmp_path)).value == 'A'
    assert _DummyNoDb.getInstance(str(tmp_path)) is held
    assert held.value == 'B'
    with held.locked():
        held.unrelated = 'C'
    durable = _DummyNoDb.load_detached(str(tmp_path))
    assert durable.value == 'B'
    assert durable.nested == {'items': ['A', 'B']}
    print('CONFIRMED: disk A after failure; held/cache B; unrelated save persists B + C')


def test_real_soils_missing_ssurgo_contaminates_later_save(tmp_path, monkeypatch):
    from wepppy.nodb.core import Ron, Soils, Watershed
    monkeypatch.setattr(base, 'redis_lock_client', _RedisStub())
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    wd = str(tmp_path)
    config = 'canada-wbt-mofe.cfg'
    Ron(wd, config, initialize_components=False)
    Watershed(wd, config)
    Soils(wd, config)
    held = Soils.getInstance(wd)
    with held.locked():
        held._initial_sat = 0.2
    with pytest.raises(FileNotFoundError, match='not found'):
        held._build_gridded(initial_sat=0.9, retrieve_gridded_ssurgo=False)
    assert Soils.load_detached(wd).initial_sat == 0.2
    assert held.initial_sat == 0.9
    with held.locked():
        held.probe_unrelated = 'C'
    assert Soils.load_detached(wd).initial_sat == 0.9
    print('CONFIRMED REAL SOILS: missing SSURGO rejects build; later save persists rejected initial_sat=0.9')
