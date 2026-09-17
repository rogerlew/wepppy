"""Independent disposable CLI artifact-path and reader-generation probes."""
import json
import os
from pathlib import Path
import stat

import pyarrow.parquet as pq
import pytest

from tests.nodb.test_climate_artifact_export_service import _write_minimal_cli
from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from wepppy.climates import cli_parquet
from wepppy.nodb.mods.postfire_debris_flow import production
from wepppy.wepp.interchange._utils import _ensure_cli_parquet

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('component', ['climate_artifacts', 'cli_parquet', 'attempts'])
def test_characterize_redirected_new_artifact_subtree(tmp_path, component):
    root = tmp_path / 'run'
    source_dir = root / 'climate'
    source_dir.mkdir(parents=True)
    _write_minimal_cli(source_dir / 'selected.cli')
    outside = tmp_path / 'outside-run'
    outside.mkdir()
    segments = ['climate_artifacts', 'cli_parquet', 'attempts']
    index = segments.index(component)
    link = root.joinpath(*segments[:index + 1])
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    output = _ensure_cli_parquet(source_dir, cli_file_hint='selected.cli')
    leaked = list(outside.rglob('source.cli'))
    print('ARTIFACT_REDIRECTION ' + json.dumps({'component': component,
          'export_succeeded': output is not None, 'outside_snapshots': len(leaked)}))
    assert output is not None and len(leaked) == 1
    assert leaked[0].read_bytes() == (source_dir / 'selected.cli').read_bytes()
    assert stat.S_IMODE(leaked[0].parent.stat().st_mode) == 0o700


@pytest.mark.parametrize('content', [False, True])
def test_readiness_rejects_observable_parquet_replacement(owner_project, monkeypatch, content):
    root, _ = owner_project
    output = root / 'climate/wepp_cli.parquet'
    replacement = root / 'other-generation.parquet'
    table = pq.read_table(output)
    metadata = dict(table.schema.metadata)
    metadata.pop(b'wepppy_cli_source')
    pq.write_table(table.replace_schema_metadata(metadata), replacement)
    read_proof = cli_parquet._read_proof
    def proof_then_replace(stream, max_text):
        result = read_proof(stream, max_text)
        os.replace(replacement, output)
        return result
    monkeypatch.setattr(cli_parquet, '_read_proof', proof_then_replace)
    with pytest.raises(production.WorkflowError, match='Climate changed'):
        production.sources(root, content=content)


def test_oversize_footer_refused_before_arrow_decoding(tmp_path, monkeypatch):
    path = tmp_path / 'oversize.parquet'
    limit = 1024 * 1024
    path.write_bytes(b'PAR1' + b'x' * (limit + 1) + (limit + 1).to_bytes(4, 'little') + b'PAR1')
    def forbidden(*args, **kwargs):
        raise AssertionError('Arrow must not decode an oversized footer')
    monkeypatch.setattr(cli_parquet.pq, 'ParquetFile', forbidden)
    with path.open('rb') as stream:
        with pytest.raises(ValueError, match='oversized'):
            cli_parquet._read_proof(stream, limit)


@pytest.mark.parametrize('key', ['active_cli', 'cli'])
def test_real_read_denial_cannot_be_ready(owner_project, key):
    assert os.getuid() != 0
    root, _ = owner_project
    state = production.sources(root)
    target = state[3][key]
    mode = stat.S_IMODE(target.stat().st_mode)
    target.chmod(0)
    try:
        with pytest.raises(PermissionError):
            production.sources(root, content=False)
    finally:
        target.chmod(mode)
