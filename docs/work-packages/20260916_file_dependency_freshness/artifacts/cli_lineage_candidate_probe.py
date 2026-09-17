"""Disposable publication feasibility only; not a production implementation."""
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pyarrow.parquet as pq
import pytest

from tests.nodb.test_climate_artifact_export_service import _write_minimal_cli
from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService

pytestmark = pytest.mark.integration


def create(root):
    cli_dir = root / 'climate'
    cli_dir.mkdir()
    _write_minimal_cli(cli_dir / 'selected.cli')
    climate = SimpleNamespace(wd=str(root), cli_dir=str(cli_dir), cli_fn='selected.cli',
                              logger=logging.getLogger('cli-candidate-discovery'))
    return ClimateArtifactExportService().export_cli_parquet(climate)


def test_open_file_candidate_retains_native_failure_and_old_output(tmp_path, monkeypatch):
    output = create(tmp_path)
    previous = output.read_bytes()
    table = pq.read_table(output)
    candidate = tmp_path / 'failed-candidate.parquet'
    def fail_write(self, table, row_group_size=None):
        raise OSError(28, 'controlled native writer ENOSPC')
    monkeypatch.setattr(pq.ParquetWriter, 'write_table', fail_write)
    with candidate.open('xb') as stream:
        with pytest.raises(OSError, match='ENOSPC'):
            pq.write_table(table, stream)
    assert candidate.is_file() and candidate.stat().st_size > 0
    assert output.read_bytes() == previous
    print('FILE_HANDLE_CANDIDATE ' + json.dumps({'retained_bytes': candidate.stat().st_size,
          'old_canonical_unchanged': True}))


def test_single_descriptor_embedded_proof_and_rows_survive_atomic_replace(tmp_path):
    output = create(tmp_path)
    table = pq.read_table(output)
    old_meta = dict(table.schema.metadata or {})
    old_meta[b'wepppy_cli_source'] = b'{"observation":"old-discovery-only"}'
    pq.write_table(table.replace_schema_metadata(old_meta), output)
    frame = table.to_pandas()
    frame.loc[0, 'prcp'] = 8.
    new_table = type(table).from_pandas(frame, preserve_index=False)
    new_meta = dict(new_table.schema.metadata or {})
    new_meta[b'wepppy_cli_source'] = b'{"observation":"new-discovery-only"}'
    candidate = tmp_path / 'candidate.parquet'
    pq.write_table(new_table.replace_schema_metadata(new_meta), candidate)
    with output.open('rb') as stream:
        opened_reader = pq.ParquetFile(stream)
        os.replace(candidate, output)
        old_rows = opened_reader.read().to_pandas()
        old_proof = opened_reader.schema_arrow.metadata[b'wepppy_cli_source']
    assert old_rows.iloc[0]['prcp'] == 4
    assert old_proof == old_meta[b'wepppy_cli_source']
    assert pd.read_parquet(output).iloc[0]['prcp'] == 8
    assert pq.read_metadata(output).metadata[b'wepppy_cli_source'] == new_meta[b'wepppy_cli_source']
    print('ATOMIC_GENERATIONS ' + json.dumps({'opened_old_rows_and_proof_agree': True,
          'new_path_rows_and_proof_agree': True}))
