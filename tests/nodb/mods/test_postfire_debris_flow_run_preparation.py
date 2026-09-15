"""Unit coverage for the narrow first-run snapshot delta and local-only states."""
from copy import deepcopy

import pytest

from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io, source_acquisition
from wepppy.nodb.mods.postfire_debris_flow.run_preparation import _project_inputs, prepare_for_run
from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import META

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('metadata',[{}, {'schema_version':1},
    {'schema_version':1,'primary':None,'fallback':None}])
def test_valid_empty_legacy_pointer_never_acquires(tmp_path,monkeypatch,metadata):
    pointer = tmp_path/META
    pointer.parent.mkdir(parents=True)
    io.write_json(pointer,metadata)
    def forbidden(*args): pytest.fail('Existing empty metadata must not acquire')
    monkeypatch.setattr(source_acquisition,'acquire_sources',forbidden)
    paths,expected = {},{}
    assert prepare_for_run(tmp_path,'unused',expected,paths) == (paths,expected)


@pytest.mark.parametrize('state',['zero_bytes','invalid_schema','dangling_link','populated_empty'])
def test_malformed_pointer_never_acquires(tmp_path,monkeypatch,state):
    pointer = tmp_path/META
    pointer.parent.mkdir(parents=True)
    if state == 'dangling_link': pointer.symlink_to(tmp_path/'missing')
    elif state == 'zero_bytes': pointer.write_bytes(b'')
    elif state == 'invalid_schema': io.write_json(pointer,{'schema_version':2})
    else: io.write_json(pointer,{'schema_version':1,'primary':{}})
    def forbidden(*args): pytest.fail('Malformed metadata must not acquire')
    monkeypatch.setattr(source_acquisition,'acquire_sources',forbidden)
    with pytest.raises(io.RainfallError): prepare_for_run(tmp_path,'unused',{}, {})


def test_snapshot_delta_excludes_only_prepared_assets(tmp_path):
    raw = str(tmp_path/'soils/ssurgo_tabular_cache.sqlite')
    pointer = str(tmp_path/META)
    snapshot = {'files':{'sbs':['original']},'selections':{'model':'M3','soil_inputs':{
        'dependencies':{pointer:None,raw:[1]},'cache_state':{'wal':[1]},'prepared_sha256':{}}}}
    prepared = deepcopy(snapshot)
    inventory = prepared['selections']['soil_inputs']
    inventory['dependencies'][pointer] = [2]
    inventory['dependencies'][str(tmp_path/'postfire_debris_flow/source_preparation/id/native.tif')] = [3]
    inventory['prepared_sha256'] = {pointer:'hash'}
    assert _project_inputs(tmp_path,prepared) == _project_inputs(tmp_path,snapshot)
    assert snapshot['selections']['soil_inputs']['dependencies'][pointer] is None
    for change in ('raw','wal','sbs','other_module_file'):
        changed = deepcopy(prepared)
        inv = changed['selections']['soil_inputs']
        if change == 'raw': inv['dependencies'][raw] = [99]
        elif change == 'wal': inv['cache_state']['wal'] = [99]
        elif change == 'sbs': changed['files']['sbs'] = ['new']
        else: inv['dependencies'][str(tmp_path/'postfire_debris_flow/unrelated')] = [99]
        assert _project_inputs(tmp_path,changed) != _project_inputs(tmp_path,snapshot)
