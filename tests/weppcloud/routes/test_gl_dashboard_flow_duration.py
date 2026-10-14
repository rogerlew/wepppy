"""Direct filesystem ownership tests: no mocked safety boundary."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.weppcloud.routes import gl_dashboard_flow_duration as fdc

pytestmark = pytest.mark.routes


def source(root, name='totalwatsed3'):
    path = root / f'wepp/output/interchange/{name}.parquet'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def catalog(owner, source_path, **updates):
    path = owner / '_query_engine/catalog.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {'root': str(owner), 'files': [{'path': str(source_path.relative_to(owner))}]}
    data.update(updates)
    path.write_text(json.dumps(data))


def test_missing_catalog_allows_owned_source_but_mismatched_root_and_entry_fail(tmp_path):
    path = source(tmp_path)
    relative = str(path.relative_to(tmp_path))
    assert fdc._source_status(tmp_path, relative)['available']
    catalog(tmp_path, path)
    assert fdc._source_status(tmp_path, relative)['available']
    catalog(tmp_path, path, root=str(tmp_path.parent))
    assert not fdc._source_status(tmp_path, relative)['available']
    catalog(tmp_path, path, files=[{'path': relative, 'fs_path': '/tmp/another.parquet'}])
    assert not fdc._source_status(tmp_path, relative)['available']


def test_daily_source_and_catalog_symlinks_cannot_escape(tmp_path):
    child = tmp_path / 'child'; child.mkdir()
    parent_file = source(tmp_path)
    child_file = source(child); child_file.unlink(); child_file.symlink_to(parent_file)
    assert not fdc._source_status(child, str(child_file.relative_to(child)))['available']
    child_file.unlink(); child_file.touch()
    catalog(tmp_path, parent_file)
    (child / '_query_engine').symlink_to(tmp_path / '_query_engine', target_is_directory=True)
    assert not fdc._source_status(child, str(child_file.relative_to(child)))['available']


@pytest.mark.parametrize('target', ['base', 'sibling'])
def test_scenario_directory_alias_is_rejected(tmp_path, target):
    source(tmp_path)
    sibling = tmp_path / 'sibling'; sibling.mkdir(); source(sibling)
    (tmp_path / 'alias').symlink_to(tmp_path if target == 'base' else sibling, target_is_directory=True)
    result = fdc.flow_duration_context(str(tmp_path), [{'path': 'alias'}], 'baseline')
    assert not result['scenarios']['alias']['hillslope']['available']


def test_shared_parent_topology_allowed_but_external_topology_rejected(tmp_path, monkeypatch):
    base = tmp_path / 'base'; base.mkdir()
    child = base / 'child'; child.mkdir()
    topology = base / 'watershed'; topology.mkdir()
    (topology / 'network.txt').write_text('24|34,44\n34|0\n44|0\n')
    (child / 'watershed').symlink_to(topology, target_is_directory=True)
    translator = SimpleNamespace(chn_ids=['chn_24', 'chn_34', 'chn_44'],
                                 chn_enum=lambda top: {24: 3}[top], wepp=lambda top: {24: 8}[top])
    watershed = SimpleNamespace(outlet_top_id=None, translator_factory=lambda: translator)
    monkeypatch.setattr(fdc.Watershed, 'getInstance', lambda _root: watershed)
    assert fdc._outlet_ids(child, base) == {'channelId': 3, 'elementId': 8}
    (child / 'watershed').unlink()
    outside = tmp_path / 'outside'; outside.mkdir(); (outside / 'network.txt').write_text('24|34,44')
    (child / 'watershed').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='outside this project'):
        fdc._outlet_ids(child, base)


def test_roads_is_explicitly_unavailable(tmp_path):
    result = fdc.flow_duration_context(str(tmp_path), None, 'roads')
    assert result['scenarios'] == {}
    assert 'baseline output scope' in result['reason']


def test_external_nodb_is_rejected_before_deserialization(tmp_path, monkeypatch):
    base = tmp_path / 'project'; base.mkdir()
    outside = tmp_path / 'outside.nodb'; outside.write_text('{}')
    (base / 'watershed.nodb').symlink_to(outside)
    def must_not_load(_root):
        pytest.fail('External NoDb must not be deserialized')
    monkeypatch.setattr(fdc.Watershed, 'getInstance', must_not_load)
    with pytest.raises(ValueError, match='outside this project'):
        fdc._outlet_ids(base, base)


def test_malformed_topology_parquet_does_not_break_dashboard(tmp_path, monkeypatch):
    from wepppy.nodb.core.watershed_mixins import WatershedOperationsMixin
    source(tmp_path, 'chanwb')
    topology = tmp_path / 'watershed'; topology.mkdir()
    (topology / 'hillslopes.parquet').write_text('not parquet')
    (topology / 'channels.parquet').write_text('not parquet')
    watershed = SimpleNamespace(wd=str(tmp_path), _subs_summary=None, _chns_summary=None, outlet_top_id=None)
    watershed.translator_factory = lambda: WatershedOperationsMixin.translator_factory(watershed)
    monkeypatch.setattr(fdc.Watershed, 'getInstance', lambda _root: watershed)
    result = fdc.flow_duration_context(str(tmp_path), None, 'baseline')
    assert not result['scenarios']['']['outlet']['available']


@pytest.mark.parametrize('query_run_is_child', [False, True])
def test_standalone_omni_child_uses_parent_topology_and_own_daily_source(tmp_path, monkeypatch, query_run_is_child):
    child = tmp_path / '_pups/omni/scenarios/undisturbed'; child.mkdir(parents=True)
    source(child, 'chanwb')
    topology = tmp_path / 'watershed'; topology.mkdir()
    (topology / 'network.txt').write_text('24|34\n34|0\n')
    (child / 'watershed').symlink_to(topology, target_is_directory=True)
    (tmp_path / 'watershed.nodb').write_text('{}')
    (child / 'watershed.nodb').symlink_to(tmp_path / 'watershed.nodb')
    translator = SimpleNamespace(chn_ids=['chn_24', 'chn_34'], chn_enum=lambda top: 2, wepp=lambda top: 6)
    monkeypatch.setattr(fdc.Watershed, 'getInstance', lambda _root: SimpleNamespace(outlet_top_id=None, translator_factory=lambda: translator))
    result = fdc.flow_duration_context(str(child), None, 'baseline', query_run_is_child=query_run_is_child)
    assert result['scenarios']['']['outlet'] == {'available': True, 'channelId': 2, 'elementId': 6}
    assert result['queryScenarioPath'] == ('' if query_run_is_child else '_pups/omni/scenarios/undisturbed')


def observed_source(root, text=None, area=86400000):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = root / 'observed/observed.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text is not None else
                    'Date,Year,Month,Day,Julian,Streamflow (mm)\n'
                    '2000-01-01,2000,1,1,0,4\n'
                    '2000-01-02,2000,1,2,1,\n')
    area_path = source(root)
    pq.write_table(pa.table({'Area': [area]}), area_path)
    return path, area_path


def test_observed_reads_normalized_upload_without_model_fit_or_catalog(tmp_path):
    csv_path, area_path = observed_source(tmp_path)
    originals = [p.read_bytes() for p in (csv_path, area_path)]
    data = fdc.flow_duration_context(str(tmp_path), None, 'baseline')['observed']
    assert data['present'] and data['available']
    assert data['records'] == [
        {'year': '2000', 'month': '1', 'day': '1', 'julian': 1, 'flow': '4', 'area': '86400000.0'},
        {'year': '2000', 'month': '1', 'day': '2', 'julian': 2, 'flow': None, 'area': '86400000.0'},
    ]
    assert [p.read_bytes() for p in (csv_path, area_path)] == originals
    assert not (tmp_path / 'observed.nodb').exists()


@pytest.mark.parametrize('text,reason', [
    ('', 'columns'),
    ('Year,Month,Day,Julian,Sediment\n2000,1,1,0,2\n', 'columns'),
    ('Year,Month,Day,Julian,Streamflow (mm)\n', 'daily records'),
    ('Year,Month,Day,Julian,Streamflow (mm)\n2000,1,1,0\n', 'row'),
    ('Year,Month,Day,Julian,Streamflow (mm)\n2000,1,1,0,2,extra\n', 'row'),
    ('Year,Month,Day,Julian,Streamflow (mm)\n2000,1,1,bad,2\n', 'Julian'),
    ('Year,Month,Day,Julian,Streamflow (mm),Streamflow (mm)\n2000,1,1,0,2,3\n', 'columns'),
])
def test_invalid_observed_is_unavailable_without_breaking_model_sources(tmp_path, text, reason):
    observed_source(tmp_path, text)
    data = fdc.flow_duration_context(str(tmp_path), None, 'baseline')
    assert data['scenarios']['']['hillslope']['available']
    assert data['observed']['present'] and not data['observed']['available']
    assert reason in data['observed']['reason']
    assert 'records' not in data['observed']


@pytest.mark.parametrize('area', [0, -1, float('nan'), float('inf'), None, [1, 2], {'value': 1}, True])
def test_observed_invalid_area_is_explicit(tmp_path, area):
    observed_source(tmp_path, area=area)
    context = fdc.flow_duration_context(str(tmp_path), None, 'baseline')
    assert context['scenarios']['']['hillslope']['available']
    data = context['observed']
    assert not data['available']
    assert 'area' in data['reason']


def test_observed_missing_and_roads_have_no_records(tmp_path):
    assert fdc._observed_status(tmp_path) == {'present': False, 'available': False}
    observed_source(tmp_path)
    assert 'observed' not in fdc.flow_duration_context(str(tmp_path), None, 'roads')


@pytest.mark.parametrize('which', ['csv', 'area'])
def test_observed_rejects_escaping_files(tmp_path, which):
    project = tmp_path / 'project'; project.mkdir()
    paths = observed_source(project)
    target = paths[0 if which == 'csv' else 1]
    outside = tmp_path / target.name
    target.rename(outside)
    target.symlink_to(outside)
    data = fdc._observed_status(project)
    assert data['present'] and not data['available']
    assert 'records' not in data


def test_observed_canonical_child_uses_project_upload_and_area(tmp_path):
    observed_source(tmp_path)
    child = tmp_path / '_pups/omni/scenarios/undisturbed'
    child.mkdir(parents=True)
    observed_source(child, area=42)
    result = fdc.flow_duration_context(str(child), None, 'baseline')
    assert result['observed']['records'][0]['area'] == '86400000.0'
    ordinary_child = tmp_path / 'ordinary'; ordinary_child.mkdir()
    assert not fdc.flow_duration_context(str(ordinary_child), None, 'baseline')['observed']['present']


def test_observed_byte_and_row_limits_never_return_partial_data(tmp_path, monkeypatch):
    path, _ = observed_source(tmp_path)
    monkeypatch.setattr(fdc, 'OBSERVED_MAX_BYTES', len(path.read_bytes()))
    monkeypatch.setattr(fdc, 'OBSERVED_MAX_ROWS', 2)
    assert fdc._observed_status(tmp_path)['available']
    path.write_text(path.read_text() + '\n')
    result = fdc._observed_status(tmp_path)
    assert not result['available'] and '16 MiB' in result['reason']
    assert 'records' not in result
    monkeypatch.setattr(fdc, 'OBSERVED_MAX_BYTES', 1024)
    monkeypatch.setattr(fdc, 'OBSERVED_MAX_ROWS', 1)
    result = fdc._observed_status(tmp_path)
    assert not result['available'] and '100,000' in result['reason']
    assert 'records' not in result


def test_observed_preserves_nonfinite_and_malformed_flow_for_graph_validation(tmp_path):
    observed_source(tmp_path, 'Year,Month,Day,Julian,Streamflow (mm)\n2000,1,1,0,Infinity\n')
    assert fdc._observed_status(tmp_path)['records'][0]['flow'] == 'Infinity'


def test_observed_numeric_string_area_is_converted_before_maximum(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    _, area_path = observed_source(tmp_path)
    pq.write_table(pa.table({'Area': ['9', '100']}), area_path)
    data = fdc.flow_duration_context(str(tmp_path), None, 'baseline')
    assert data['observed']['records'][0]['area'] == '100.0'
    assert data['scenarios']['']['hillslope']['available']


def test_missing_observed_conversion_source_and_bad_encoding_are_isolated(tmp_path):
    csv_path, area_path = observed_source(tmp_path)
    area_path.unlink()
    result = fdc._observed_status(tmp_path)
    assert result['present'] and not result['available']
    assert 'records' not in result
    csv_path.write_bytes(b'\xff\xfe')
    result = fdc._observed_status(tmp_path)
    assert result['present'] and not result['available']
    assert 'records' not in result
