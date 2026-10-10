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
