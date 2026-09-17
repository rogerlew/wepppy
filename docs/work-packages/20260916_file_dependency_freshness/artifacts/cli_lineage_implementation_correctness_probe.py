"""Independent actual-file probes of CLI lineage implementation boundaries."""
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pandas as pd
import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from tests.nodb.test_cli_parquet_lineage import selected, change, proof
from wepppy.climates import cli_parquet
from wepppy.climates.cligen import ClimateFile
from wepppy.nodb.mods.postfire_debris_flow import production
from wepppy.wepp.interchange._utils import _ensure_cli_parquet


@pytest.mark.parametrize('content', [True, False])
def test_footer_replacement_rejects_generation_mismatch(owner_project, monkeypatch, content):
    root, _ = owner_project
    output = root / 'climate/wepp_cli.parquet'
    replacement = output.with_name('replacement.parquet')
    replacement.write_bytes(output.read_bytes())
    reader = cli_parquet._read_proof
    def replace_after_metadata(stream, limit):
        result = reader(stream, limit)
        os.replace(replacement, output)
        return result
    monkeypatch.setattr(cli_parquet, '_read_proof', replace_after_metadata)
    with pytest.raises(production.WorkflowError) as raised:
        production.sources(root, content=content)
    assert raised.value.code == 'changed_source'
    print('FOOTER_REPLACEMENT', json.dumps({'content': content, 'code': raised.value.code}))


def test_committed_output_survives_status_failure(owner_project, monkeypatch):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    change(source)
    status = cli_parquet._CliParquetAttempt._status
    def fail_after_commit(self, state, error=None):
        if state == 'complete':
            raise OSError(28, 'independent postcommit diagnostic failure')
        return status(self, state, error)
    monkeypatch.setattr(cli_parquet._CliParquetAttempt, '_status', fail_after_commit)
    assert owner._export_cli_parquet() == output
    assert float(pd.read_parquet(output).iloc[0]['prcp']) == 8.
    assert production.sources(root)[2]['climate']
    records = [json.loads(path.read_text()) for path in root.glob('climate_artifacts/cli_parquet/attempts/*/status.json')]
    assert any(record['status'] == 'ready_to_publish' for record in records)
    print('POSTCOMMIT_DIAGNOSTIC', json.dumps({'committed_return': True, 'current': True}))


def test_overlap_retains_complete_generations(owner_project, monkeypatch):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    change(source)
    status = cli_parquet._CliParquetAttempt._status
    barrier = Barrier(2, timeout=20)
    def overlap(self, state, error=None):
        status(self, state, error)
        if state == 'ready_to_publish':
            barrier.wait()
    monkeypatch.setattr(cli_parquet._CliParquetAttempt, '_status', overlap)
    before = set(root.glob('climate_artifacts/cli_parquet/attempts/*'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: owner._export_cli_parquet(), range(2)))
    after = set(root.glob('climate_artifacts/cli_parquet/attempts/*'))
    assert results == [output, output]
    assert len(after - before) == 2
    assert all(json.loads((path / 'status.json').read_text())['status'] == 'complete' for path in after - before)
    assert float(pd.read_parquet(output).iloc[0]['prcp']) == 8.
    assert proof(output)['source_sha256'] == cli_parquet.sha256_file(source, use_cache=False)
    print('OVERLAP', json.dumps({'attempts': 2, 'complete_rows_and_proof': True}))


def test_interchange_disappearing_hint_rejects_candidate(owner_project, monkeypatch):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    output.unlink()
    fallback = source.with_name('fallback.cli')
    fallback.write_bytes(source.read_bytes())
    parser = ClimateFile.as_dataframe
    def remove_hint(self, *args, **kwargs):
        frame = parser(self, *args, **kwargs)
        source.unlink()
        return frame
    monkeypatch.setattr(ClimateFile, 'as_dataframe', remove_hint)
    assert _ensure_cli_parquet(output.parent, cli_file_hint=source.name) is None
    assert not output.exists()
    print('HINT_REMOVAL', json.dumps({'candidate_rejected': True, 'fallback_remains': fallback.exists()}))
