"""Physical runoff and outlet lateral at the real daily-loader boundary."""
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange.hill_wat_interchange import SCHEMA, load_hill_wat_dataframe

pytestmark = pytest.mark.unit


def write_wat(root: Path, **changes):
    data = {field.name: [0, 0, 0] for field in SCHEMA}
    data.update(wepp_id=[1]*3, ofe_id=[1,2,2], OFE=[1,2,2], year=[2000]*3,
                water_year=[2000]*3, sim_day_index=[1,1,2],julian=[1,1,2],
                month=[1]*3,day_of_month=[1,1,2],Area=[250.,750.,750.],
                P=[10.,10.,12.],Q=[4.,8.,.5],QOFE=[4.,10.6666667,.6666667],
                latqcc=[4.,6.,2.],Ep=[1.,4.,2.],Es=[.5,1.,1.],Er=[.5,1.,1.],Dp=[4.,8.,2.])
    data.update(changes)
    path=root/'interchange/H.wat.parquet';path.parent.mkdir(exist_ok=True)
    pq.write_table(pa.table(data,schema=SCHEMA),path)


def test_physical_outlet_and_missing_upstream_use_full_area(tmp_path):
    write_wat(tmp_path)
    daily=load_hill_wat_dataframe(tmp_path,1)
    np.testing.assert_allclose(daily.Q,[8.,.5])
    np.testing.assert_allclose(daily.latqcc,[4.5,1.5])
    np.testing.assert_allclose(daily.P,[10.,12.])
    np.testing.assert_allclose(daily.Ep+daily.Es+daily.Er,[5.,4.])
    np.testing.assert_allclose(daily.Dp,[7.,2.])
    raw=load_hill_wat_dataframe(tmp_path,1,collapse=None)
    assert raw.Q.tolist()==[4.,8.,.5]


def test_missing_terminal_is_not_promoted(tmp_path):
    write_wat(tmp_path,ofe_id=[1,2,1],OFE=[1,2,1],Area=[250.,750.,250.])
    with pytest.raises(ValueError,match='terminal'):
        load_hill_wat_dataframe(tmp_path,1)


@pytest.mark.parametrize('bad',[None,float('nan'),float('inf')])
def test_unavailable_terminal_is_not_zero(tmp_path,bad):
    write_wat(tmp_path,Q=[4.,bad,.5])
    with pytest.raises(ValueError,match='terminal'):
        load_hill_wat_dataframe(tmp_path,1)


def test_local_null_semantics_preserved(tmp_path):
    write_wat(tmp_path,Dp=[None,8.,None],Es=[float('nan'),1.,1.])
    daily=load_hill_wat_dataframe(tmp_path,1)
    assert daily.Dp.iloc[0]==6.
    assert np.isnan(daily.Dp.iloc[1])
    assert np.isnan(daily.Es.iloc[0])


def test_daily_digest_precedes_queries_and_is_shared_across_hills(tmp_path, monkeypatch):
    from wepppy.wepp.interchange import hill_wat_interchange as module
    import hashlib
    write_wat(tmp_path)
    path = tmp_path/'interchange/H.wat.parquet'
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    cache = {}
    signature = module._wat_source_signature(path)
    monkeypatch.setattr(module, '_wat_source_signature', lambda source: signature)
    first = load_hill_wat_dataframe(tmp_path, 1, _source_fingerprint_cache=cache)
    second = load_hill_wat_dataframe(tmp_path, 1, _source_fingerprint_cache=cache)
    assert first.attrs['water_source_sha256'] == second.attrs['water_source_sha256'] == original
    assert cache['digest'] == original
    # Changing a source after loading cannot change the fingerprint on its frame.
    write_wat(tmp_path, Q=[4.,9.,.5])
    assert first.attrs['water_source_sha256'] == original
    updated = hashlib.sha256(path.read_bytes()).hexdigest()
    assert updated != original
    # Even indistinguishable metadata cannot poison a fresh batch or direct load.
    for kwargs in ({}, {'_source_fingerprint_cache': {}}):
        regenerated = load_hill_wat_dataframe(tmp_path, 1, **kwargs)
        assert regenerated.Q.iloc[0] == 9.
        assert regenerated.attrs['water_source_sha256'] == updated


def test_digest_is_captured_before_source_queries(tmp_path, monkeypatch):
    import hashlib
    from wepppy.wepp.interchange import hill_wat_interchange as module
    write_wat(tmp_path)
    path = tmp_path/'interchange/H.wat.parquet'
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    signature = module._wat_source_signature(path)
    aliases = module._resolve_column_aliases
    def replace_after_fingerprinting(source):
        write_wat(tmp_path, Q=[4.,9.,.5])
        return aliases(source)
    # Deliberately emulate a filesystem signature collision during loading.
    monkeypatch.setattr(module, '_wat_source_signature', lambda source: signature)
    monkeypatch.setattr(module, '_resolve_column_aliases', replace_after_fingerprinting)
    frame = module.load_hill_wat_dataframe(tmp_path, 1, collapse='daily')
    assert frame.Q.iloc[0] == 9.
    assert frame.attrs['water_source_sha256'] == before
    assert frame.attrs['water_source_sha256'] != hashlib.sha256(path.read_bytes()).hexdigest()
