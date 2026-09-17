"""Disposable PF-R02 producer/readiness discovery; current-behavior assertions."""
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import stat
import time
from types import SimpleNamespace

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from tests.nodb.test_climate_artifact_export_service import _write_minimal_cli
from wepppy.climates.cligen import ClimateFile
from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService
from wepppy.nodb.mods.postfire_debris_flow import production
from wepppy.wepp.interchange._utils import _ensure_cli_parquet

pytestmark = pytest.mark.integration


def climate_at(root):
    cli_dir = root / 'climate'
    cli_dir.mkdir()
    _write_minimal_cli(cli_dir / 'selected.cli')
    return SimpleNamespace(wd=str(root), cli_dir=str(cli_dir), cli_fn='selected.cli',
                           logger=logging.getLogger('cli-lineage-discovery'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def change_precip(path):
    before = path.read_bytes()
    after = before.replace(b'1980   4.0  0.50', b'1980   8.0  0.50')
    assert before != after and len(before) == len(after)
    path.write_bytes(after)


def test_parse_failure_keeps_previous_output(tmp_path):
    climate = climate_at(tmp_path)
    service = ClimateArtifactExportService()
    output = service.export_cli_parquet(climate)
    previous = output.read_bytes()
    cli = Path(climate.cli_dir) / climate.cli_fn
    cli.write_text(cli.read_text().replace('1980   4.0  0.50', '1980   bad  0.50'))
    assert service.export_cli_parquet(climate) is None
    assert output.read_bytes() == previous
    print('PARSE_FAILURE ' + json.dumps({'prior_output_preserved': True}))


def test_native_writer_failure_truncates_previous_output(tmp_path, monkeypatch):
    climate = climate_at(tmp_path)
    service = ClimateArtifactExportService()
    output = service.export_cli_parquet(climate)
    previous = output.read_bytes()
    observed = {}
    def fail_write(self, table, row_group_size=None):
        # The real native writer constructor has already opened the destination.
        observed['size_at_write_table'] = output.stat().st_size
        raise OSError(28, 'controlled native writer ENOSPC')
    monkeypatch.setattr(pq.ParquetWriter, 'write_table', fail_write)
    assert service.export_cli_parquet(climate) is None
    assert output.read_bytes() != previous
    print('WRITE_FAILURE ' + json.dumps({**observed, 'prior_size': len(previous),
          'final_size': output.stat().st_size, 'prior_output_preserved': False}))


@pytest.mark.parametrize('operation', ['rewrite', 'selected_cli'])
def test_source_changes_after_real_parse_are_published(owner_project, monkeypatch, operation):
    from wepppy.nodb.core import Climate
    root, _ = owner_project
    climate = Climate.getInstance(str(root))
    source = Path(climate.cli_dir) / climate.cli_fn
    _write_minimal_cli(source)
    alternate = source.with_name('alternate.cli')
    _write_minimal_cli(alternate)
    change_precip(alternate)
    real_parse = ClimateFile.as_dataframe
    def parse_then_change(self, *args, **kwargs):
        result = real_parse(self, *args, **kwargs)
        if operation == 'rewrite':
            change_precip(source)
        else:
            with climate.locked():
                climate.cli_fn = alternate.name
        return result
    with monkeypatch.context() as patch:
        patch.setattr(ClimateFile, 'as_dataframe', parse_then_change)
        output = ClimateArtifactExportService().export_cli_parquet(climate)
    assert output is not None
    active = Path(climate.cli_dir) / climate.cli_fn
    source_value = float(ClimateFile(str(active)).as_dataframe().iloc[0]['prcp'])
    output_value = float(pd.read_parquet(output).iloc[0]['prcp'])
    ready = production.sources(root)[2]['climate']
    print('PARSE_RACE ' + json.dumps({'operation': operation, 'source_precip': source_value,
          'output_precip': output_value, 'ready': ready}))
    assert source_value == 8 and output_value == 4 and ready


def test_existing_output_symlink_and_mode_followed(tmp_path):
    climate = climate_at(tmp_path)
    service = ClimateArtifactExportService()
    output = service.export_cli_parquet(climate)
    target = tmp_path / 'existing-target.parquet'
    output.rename(target)
    target.chmod(0o640)
    output.symlink_to(target)
    source = Path(climate.cli_dir) / climate.cli_fn
    change_precip(source)
    assert service.export_cli_parquet(climate) == output
    assert output.is_symlink() and stat.S_IMODE(target.stat().st_mode) == 0o640
    assert float(pd.read_parquet(target).iloc[0]['prcp']) == 8
    print('DESTINATION ' + json.dumps({'symlink_preserved': True, 'target_mode': '0640'}))


def test_selected_source_symlink_supported(tmp_path):
    climate = climate_at(tmp_path)
    source = Path(climate.cli_dir) / climate.cli_fn
    target = tmp_path / 'external-selected.cli'
    source.rename(target)
    source.symlink_to(target)
    output = ClimateArtifactExportService().export_cli_parquet(climate)
    assert output is not None and source.is_symlink()
    assert float(pd.read_parquet(output).iloc[0]['prcp']) == 4
    print('SOURCE ' + json.dumps({'symlink_supported': True, 'resolved_outside_cli_dir': True}))


def test_denied_source_keeps_prior_output(tmp_path):
    assert os.getuid() != 0
    climate = climate_at(tmp_path)
    service = ClimateArtifactExportService()
    output = service.export_cli_parquet(climate)
    previous = output.read_bytes()
    source = Path(climate.cli_dir) / climate.cli_fn
    mode = stat.S_IMODE(source.stat().st_mode)
    source.chmod(0)
    try:
        with pytest.raises(PermissionError):
            source.read_bytes()
        assert service.export_cli_parquet(climate) is None
        assert output.read_bytes() == previous
    finally:
        source.chmod(mode)
    print('DENIED_SOURCE ' + json.dumps({'uid': os.getuid(), 'prior_output_preserved': True}))


@pytest.mark.parametrize('hint,expected', [(None, 4), ('z-selected.cli', 8)])
def test_interchange_materializer_is_another_producer(tmp_path, hint, expected):
    climate = climate_at(tmp_path)
    source = Path(climate.cli_dir) / climate.cli_fn
    source.rename(source.with_name('a-first.cli'))
    selected = source.with_name('z-selected.cli')
    _write_minimal_cli(selected)
    change_precip(selected)
    output = _ensure_cli_parquet(Path(climate.cli_dir), cli_file_hint=hint)
    assert output is not None
    metadata = pq.read_metadata(output).metadata
    value = float(pd.read_parquet(output).iloc[0]['prcp'])
    assert value == expected
    assert set(metadata) == {b'ARROW:schema', b'pandas'}
    print('INTERCHANGE ' + json.dumps({'hint': hint, 'precip': value,
          'metadata_keys': [key.decode() for key in metadata]}))


def test_real_fixture_export_metadata_and_copy_cost(tmp_path):
    climate = climate_at(tmp_path)
    source = Path(climate.cli_dir) / climate.cli_fn
    fixture = Path(__file__).resolve().parents[4] / 'tests/disturbed/data/test_climate.cli'
    shutil.copyfile(fixture, source)
    fixture_before = sha(fixture)
    begin = time.perf_counter()
    output = ClimateArtifactExportService().export_cli_parquet(climate)
    export_seconds = time.perf_counter() - begin
    assert output is not None
    begin = time.perf_counter()
    source_hash = sha(source)
    copy = tmp_path / 'source-snapshot.cli'
    shutil.copyfile(source, copy)
    assert sha(copy) == source_hash
    assert sha(source) == source_hash
    copy_hash_seconds = time.perf_counter() - begin
    table = pq.read_table(output)
    before = table.to_pandas()
    proof = {'version': 1, 'source': 'climate/selected.cli', 'source_sha256': source_hash,
             'exporter': 'discovery-only-not-authoritative'}
    metadata = dict(table.schema.metadata or {})
    metadata[b'wepppy_cli_source'] = json.dumps(proof).encode()
    candidate = tmp_path / 'metadata-candidate.parquet'
    begin = time.perf_counter()
    pq.write_table(table.replace_schema_metadata(metadata), candidate)
    metadata_write_seconds = time.perf_counter() - begin
    assert pq.read_table(candidate).to_pandas().equals(before)
    archived = tmp_path / 'archive-copy.parquet'
    shutil.copyfile(candidate, archived)
    with archived.open('rb') as stream:
        copied_table = pq.read_table(stream)
    assert copied_table.to_pandas().equals(before)
    assert copied_table.schema.metadata[b'wepppy_cli_source'] == metadata[b'wepppy_cli_source']
    assert sha(fixture) == fixture_before
    print('PERFORMANCE ' + json.dumps({'source_bytes': source.stat().st_size,
          'rows': table.num_rows, 'parquet_bytes': output.stat().st_size,
          'actual_export_seconds': export_seconds, 'copy_plus_three_sha_seconds': copy_hash_seconds,
          'separate_metadata_rewrite_seconds': metadata_write_seconds,
          'copied_embedded_proof_and_rows_coherent': True}))
