"""Artifact-level coverage for producer publication and catalog admission ordering."""
import json
import logging
from types import SimpleNamespace

import pandas as pd
import pytest

from wepppy.nodb.core.soils import Soils
from wepppy.query_engine import catalog_refresh

pytestmark = pytest.mark.unit


def _soils(wd):
    (wd / 'soils').mkdir(parents=True)
    return SimpleNamespace(
        wd=str(wd), soils_dir=str(wd / 'soils'), class_name='Soils',
        logger=logging.getLogger(__name__),
        _subs_summary_gen=lambda: {'11': {'mukey': '42', 'wepp_id': 1}},
        watershed_instance=SimpleNamespace(translator_factory=lambda: None),
    )


def test_managed_soils_publishes_artifact_and_receipt_before_queue(tmp_path, monkeypatch):
    root = tmp_path / 'runs'
    wd = root / 'ab' / 'ab-test'
    soils = _soils(wd)
    monkeypatch.setenv('QUERY_CATALOG_REFRESH_ENABLED', 'true')
    monkeypatch.setenv('QUERY_CATALOG_ROOTS_JSON', json.dumps([
        {'path': str(root), 'namespace': 'test:runs',
         'coordination': str(tmp_path / 'locks'), 'layout': 'sharded'}
    ]))
    admissions = []

    def enqueue(base, **kwargs):
        frame = pd.read_parquet(wd / 'soils/soils.parquet')
        assert frame['mukey'].tolist() == ['42']
        requests = catalog_refresh.pending_catalog_requests(base)
        assert [r['asset_path'] for r in requests] == ['soils/soils.parquet']
        assert not (wd / '_query_engine/catalog.json').exists()
        admissions.append(kwargs['scope'])
        return {'state': 'pending'}

    monkeypatch.setattr('wepppy.rq.query_catalog_rq.enqueue_catalog_refresh', enqueue)
    Soils.dump_soils_parquet(soils)
    assert len(admissions) == 1
    catalog_refresh.refresh_catalog(wd)
    catalog = json.loads((wd / '_query_engine/catalog.json').read_text())
    assert any(entry['path'] == 'soils/soils.parquet' for entry in catalog['files'])
    assert not catalog_refresh.pending_catalog_requests(wd)


def test_soils_durable_admission_failure_propagates_after_artifact(tmp_path, monkeypatch):
    soils = _soils(tmp_path / 'run')

    def fail_admission(*args):
        raise OSError('durable intent unavailable')

    monkeypatch.setattr('wepppy.nodb.core.soils.request_catalog_refresh', fail_admission)
    with pytest.raises(OSError, match='durable intent unavailable'):
        Soils.dump_soils_parquet(soils)
    assert pd.read_parquet(tmp_path / 'run/soils/soils.parquet')['mukey'].tolist() == ['42']


def test_standalone_soils_remains_synchronously_discoverable(tmp_path, monkeypatch):
    monkeypatch.delenv('QUERY_CATALOG_ROOTS_JSON', raising=False)
    soils = _soils(tmp_path / 'standalone')
    Soils.dump_soils_parquet(soils)
    catalog = json.loads((tmp_path / 'standalone/_query_engine/catalog.json').read_text())
    assert any(entry['path'] == 'soils/soils.parquet' for entry in catalog['files'])
    assert not catalog_refresh.pending_catalog_requests(soils.wd)
