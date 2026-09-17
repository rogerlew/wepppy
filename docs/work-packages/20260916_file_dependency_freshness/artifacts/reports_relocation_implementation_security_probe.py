"""Actual C09 selection, lost-catalog history and unrelated-entry isolation."""
import json
import os
from pathlib import Path
import shutil
import stat

import pyarrow.parquet as pq
import pytest

from tests.wepp.reports.test_report_cache_freshness import run, _rewrite, _rows
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports import _cache_freshness as freshness


def test_missing_catalog_changed_complete_source_rebuilds_in_one_call(run):
    AverageAnnualsByLanduseReport(run)
    _rewrite(run / AverageAnnualsByLanduseReport._LOSS_DATASET, 'Runoff Volume', 900.)
    shutil.rmtree(run / '_query_engine')
    report = AverageAnnualsByLanduseReport(run)
    assert report.cache_status == 'built'
    assert _rows(report)[0]['Avg Runoff Depth (mm/yr)'] == 900.


def test_relocated_own_absolute_sources_use_new_root_and_keep_catalog_bytes(run, tmp_path):
    original = _rows(AverageAnnualsByLanduseReport(run))
    catalog_path = run / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog['files']:
        entry['fs_path'] = str(run / entry['path'])
    catalog_path.write_text(json.dumps(catalog))
    relocated = tmp_path / 'moved'
    shutil.copytree(run, relocated)
    catalog_before = (relocated / '_query_engine/catalog.json').read_bytes()
    _rewrite(relocated / AverageAnnualsByLanduseReport._LOSS_DATASET, 'Runoff Volume', 900.)
    report = AverageAnnualsByLanduseReport(relocated)
    assert _rows(report)[0]['Avg Runoff Depth (mm/yr)'] == 900.
    assert _rows(AverageAnnualsByLanduseReport(run)) == original
    assert (relocated / '_query_engine/catalog.json').read_bytes() == catalog_before
    proof = json.loads(pq.read_schema(relocated / 'wepp/reports/cache/average_annuals_by_landuse.parquet').metadata[freshness._METADATA_KEY])
    key = AverageAnnualsByLanduseReport._LOSS_DATASET
    assert proof['dependencies'][key] == freshness._observe_file(relocated, relocated / key)


def test_unrelated_parent_reference_does_not_block_standalone_report(run, tmp_path):
    expected = _rows(AverageAnnualsByLanduseReport(run))
    parent = tmp_path / 'old-parent'
    child = parent / '_pups/omni/scenarios/child'
    shutil.copytree(run, child)
    catalog_path = child / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    catalog['root'] = str(child)
    catalog['files'].append({'path': 'soils/soils.parquet', 'fs_path': str(parent / 'soils/soils.parquet'),
                             'extension': '.parquet', 'size_bytes': 0,
                             'modified': '2026-09-17', 'schema': None})
    catalog_path.write_text(json.dumps(catalog))
    standalone = tmp_path / 'standalone'
    shutil.copytree(child, standalone)
    before = (standalone / '_query_engine/catalog.json').read_bytes()
    report = AverageAnnualsByLanduseReport(standalone)
    assert report.cache_status == 'current' and _rows(report) == expected
    assert (standalone / '_query_engine/catalog.json').read_bytes() == before


def test_missing_catalog_cannot_authorize_forged_outside_history_path(run, tmp_path):
    AverageAnnualsByLanduseReport(run)
    cache = run / 'wepp/reports/cache/average_annuals_by_landuse.parquet'
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    proof = json.loads(metadata[freshness._METADATA_KEY])
    outside = tmp_path / 'outside.parquet'
    shutil.copyfile(run / AverageAnnualsByLanduseReport._LOSS_DATASET, outside)
    proof['dependencies'][AverageAnnualsByLanduseReport._LOSS_DATASET]['path'] = '../outside.parquet'
    metadata[freshness._METADATA_KEY] = json.dumps(proof).encode()
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    shutil.rmtree(run / '_query_engine')
    outside.chmod(0)
    try:
        with pytest.raises(ValueError, match='escapes allowed roots'):
            AverageAnnualsByLanduseReport(run)
    finally:
        outside.chmod(0o600)


def test_missing_catalog_redirected_history_still_checks_permission(run):
    assert os.getuid() != 0
    AverageAnnualsByLanduseReport(run)
    selected = run / 'selected-loss.parquet'
    shutil.copyfile(run / AverageAnnualsByLanduseReport._LOSS_DATASET, selected)
    catalog_path = run / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog['files']:
        if entry['path'] == AverageAnnualsByLanduseReport._LOSS_DATASET:
            entry['fs_path'] = str(selected)
    catalog_path.write_text(json.dumps(catalog))
    AverageAnnualsByLanduseReport(run)
    shutil.rmtree(run / '_query_engine')
    mode = stat.S_IMODE(selected.stat().st_mode)
    selected.chmod(0)
    try:
        with pytest.raises(PermissionError):
            AverageAnnualsByLanduseReport(run)
    finally:
        selected.chmod(mode)
