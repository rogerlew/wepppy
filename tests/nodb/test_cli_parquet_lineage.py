"""Actual CLI/native Parquet provenance and publication boundaries."""
from __future__ import annotations

import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pandas as pd
import pyarrow.parquet as pq
import pytest

from wepppy.climates.cligen import ClimateFile
from wepppy.climates.cli_parquet import _CliParquetAttempt, _read_proof
from wepppy.nodb.core import Climate
from wepppy.nodb.mods.postfire_debris_flow import production
from wepppy.wepp.interchange._utils import _ensure_cli_parquet
from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from tests.nodb.test_climate_artifact_export_service import _write_minimal_cli

pytestmark = pytest.mark.integration


def selected(root):
    owner = Climate.getInstance(str(root))
    return owner, Path(owner.cli_dir) / owner.cli_fn


def change(path):
    before = path.stat()
    incoming = path.read_bytes()
    outgoing = incoming.replace(b'1980   4.0', b'1980   8.0')
    assert incoming != outgoing and len(incoming) == len(outgoing)
    path.write_bytes(outgoing)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))


def proof(path):
    with path.open('rb') as stream:
        return _read_proof(stream, 1024 * 1024)[0]


def test_content_and_metadata_readiness_including_locked_authority(owner_project):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    before = output.read_bytes()
    source.touch()
    os.link(source, source.with_suffix('.link'))
    source.chmod(0o640)
    for content in (True, False):
        assert production.sources(root, content=content)[2]['climate']
    assert output.read_bytes() == before
    change(source)
    for content in (True, False):
        assert not production.sources(root, content=content)[2]['climate']
    assert owner._export_cli_parquet() == output
    assert float(pd.read_parquet(output).iloc[0]['prcp']) == 8.
    assert production.sources(root)[2]['climate']


@pytest.mark.parametrize('operation', ['rewrite', 'selection', 'change_restore'])
def test_snapshot_and_owner_selection_races(owner_project, monkeypatch, operation):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    previous = output.read_bytes()
    original = source.read_bytes()
    alternate = source.with_name('alternate.cli')
    alternate.write_bytes(original)
    change(alternate)
    parse = ClimateFile.as_dataframe
    def mutate(self, *args, **kwargs):
        assert Path(self.cli_fn) != source
        if operation == 'change_restore':
            change(source)
        result = parse(self, *args, **kwargs)
        if operation == 'rewrite':
            change(source)
        elif operation == 'change_restore':
            source.write_bytes(original)
        else:
            # Persist through a distinct hydrated controller, not the object
            # retained by the exporter. Fresh owner resolution must observe it.
            independent = Climate.load_detached(str(root))
            with independent.locked():
                independent.cli_fn = alternate.name
        return result
    monkeypatch.setattr(ClimateFile, 'as_dataframe', mutate)
    result = owner._export_cli_parquet()
    if operation == 'change_restore':
        assert result == output
        assert float(pd.read_parquet(output).iloc[0]['prcp']) == 4.
    else:
        assert result is None
        assert output.read_bytes() == previous
        statuses = [json.loads(p.read_text()) for p in root.glob('climate_artifacts/cli_parquet/attempts/*/status.json')]
        assert any(s['status'] == 'failed' for s in statuses)


def test_native_failure_and_output_authorization_preserve_prior(owner_project, monkeypatch):
    assert os.geteuid() != 0
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    previous = output.read_bytes()
    change(source)
    with monkeypatch.context() as patch:
        def fail(self, table, row_group_size=None):
            raise OSError(28, 'controlled native writer ENOSPC')
        patch.setattr(pq.ParquetWriter, 'write_table', fail)
        assert owner._export_cli_parquet() is None
    assert output.read_bytes() == previous
    candidates = list(root.glob('climate_artifacts/cli_parquet/attempts/*/candidate.parquet'))
    assert any(p.stat().st_size > 0 for p in candidates)
    assert not production.sources(root)[2]['climate']
    output.chmod(0o444)
    try:
        assert owner._export_cli_parquet() is None
        assert output.read_bytes() == previous
    finally:
        output.chmod(0o640)
    assert owner._export_cli_parquet() == output
    assert output.stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize('raw', [None, b'null', b'{}', b'{"version":1,"version":1}'])
def test_legacy_and_malformed_proof_do_not_certify_new_execution(owner_project, raw):
    root, _ = owner_project
    output = root / 'climate/wepp_cli.parquet'
    table = pq.read_table(output)
    metadata = dict(table.schema.metadata)
    metadata.pop(b'wepppy_cli_source')
    if raw is not None:
        metadata[b'wepppy_cli_source'] = raw
    pq.write_table(table.replace_schema_metadata(metadata), output)
    assert not production.sources(root)[2]['climate']
    assert _ensure_cli_parquet(output.parent) == output
    assert pd.read_parquet(output).iloc[0]['prcp'] == 4.


@pytest.mark.parametrize('drift', [False, True])
def test_interchange_actual_producer_rechecks_its_fallback(tmp_path, monkeypatch, drift):
    cli_dir = tmp_path / 'climate'
    cli_dir.mkdir()
    source = cli_dir / 'z.cli'
    _write_minimal_cli(source)
    parse = ClimateFile.as_dataframe
    def parse_then_add(self, *args, **kwargs):
        result = parse(self, *args, **kwargs)
        if drift:
            earlier = cli_dir / 'a.cli'
            earlier.write_bytes(source.read_bytes())
            change(earlier)
        return result
    monkeypatch.setattr(ClimateFile, 'as_dataframe', parse_then_add)
    output = _ensure_cli_parquet(cli_dir)
    if drift:
        assert output is None
        assert not (cli_dir / 'wepp_cli.parquet').exists()
    else:
        assert proof(output)['producer'] == 'interchange'
        assert proof(output)['source'] == 'climate/z.cli'
        assert pd.read_parquet(output).iloc[0]['prcp'] == 4.


def test_source_output_links_and_snapshot_confidentiality(owner_project):
    root, _ = owner_project
    owner, source = selected(root)
    physical_source = root / 'external.cli'
    source.rename(physical_source)
    source.symlink_to(physical_source)
    output = root / 'climate/wepp_cli.parquet'
    physical_output = root / 'external.parquet'
    output.rename(physical_output)
    physical_output.chmod(0o640)
    output.symlink_to(physical_output)
    change(source)
    assert owner._export_cli_parquet() == output
    assert output.is_symlink() and source.is_symlink()
    assert physical_output.stat().st_mode & 0o777 == 0o640
    assert pd.read_parquet(output).iloc[0]['prcp'] == 8.
    for attempt in root.glob('climate_artifacts/cli_parquet/attempts/*'):
        assert attempt.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize('text,error', [('', IndexError), ('wrong-header', AssertionError)])
def test_original_uncaught_parser_errors_retain_evidence(owner_project, text, error):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    previous = output.read_bytes()
    if text:
        source.write_text(source.read_text().replace(' da mo year', ' xx mo year'))
    else:
        source.write_text('')
    with pytest.raises(error):
        owner._export_cli_parquet()
    assert output.read_bytes() == previous
    failed = [p.parent for p in root.glob('climate_artifacts/cli_parquet/attempts/*/status.json')
              if json.loads(p.read_text())['status'] == 'failed']
    assert len(failed) == 1
    assert (failed[0] / 'source.cli').read_bytes() == source.read_bytes()


def test_bounded_footer_and_proof_generation(owner_project):
    root, _ = owner_project
    owner, source = selected(root)
    output = root / 'climate/wepp_cli.parquet'
    with output.open('rb') as old:
        old_reader = pq.ParquetFile(old)
        old_proof = old_reader.schema_arrow.metadata[b'wepppy_cli_source']
        change(source)
        assert owner._export_cli_parquet() == output
        assert old_reader.read().to_pandas().iloc[0]['prcp'] == 4.
        assert old_reader.schema_arrow.metadata[b'wepppy_cli_source'] == old_proof
    assert pd.read_parquet(output).iloc[0]['prcp'] == 8.
    with output.open('r+b') as outgoing:
        outgoing.seek(-8, os.SEEK_END)
        outgoing.write((2 * 1024 * 1024).to_bytes(4, 'little'))
    assert not production.sources(root)[2]['climate']


def test_overlapping_atomic_generations_have_matching_source_proof(tmp_path, monkeypatch):
    root = tmp_path
    first = root / 'first.cli'
    second = root / 'second.cli'
    _write_minimal_cli(first)
    second.write_bytes(first.read_bytes())
    change(second)
    output = root / 'climate/wepp_cli.parquet'
    barrier = Barrier(2)
    original = _CliParquetAttempt._status
    def rendezvous(self, status, error=None):
        original(self, status, error)
        if status == 'ready_to_publish':
            barrier.wait(timeout=10)
    monkeypatch.setattr(_CliParquetAttempt, '_status', rendezvous)
    def write(source):
        with _CliParquetAttempt(root, source, output, 'interchange') as attempt:
            frame = ClimateFile(str(attempt.snapshot)).as_dataframe(calc_peak_intensities=True)
            attempt.publish(frame, lambda: source)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(write, [first, second]))
    accepted = proof(output)
    expected = 4. if accepted['source'] == 'first.cli' else 8.
    assert pd.read_parquet(output).iloc[0]['prcp'] == expected
    assert len(list(root.glob('climate_artifacts/cli_parquet/attempts/*/status.json'))) == 2


def test_cleanup_skeleton_archive_restore_keep_history(owner_project):
    import shutil
    import zipfile
    from types import SimpleNamespace
    from wepppy.nodb.core.climate_build_router import _clear_directory_preserving_symlink_mount
    from wepppy.nodb.skeletonize import skeletonize_run
    from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq
    from wepppy.nodb.project_config_update import project_config_lifecycle_guard

    root, _ = owner_project
    owner, source = selected(root)
    source.chmod(0o600)
    source.write_text('')
    with pytest.raises(IndexError):
        owner._export_cli_parquet()
    expected = {str(path.relative_to(root)): path.read_bytes()
                for path in (root / 'climate_artifacts').rglob('*') if path.is_file()}
    assert any(json.loads(value).get('status') == 'failed'
               for name, value in expected.items() if name.endswith('status.json'))
    _clear_directory_preserving_symlink_mount(str(root / 'climate'))
    assert all((root / name).read_bytes() == data for name, data in expected.items())
    skeletonize_run(root)
    assert all((root / name).read_bytes() == data for name, data in expected.items())
    runtime = ArchiveRuntime(
        get_current_job=lambda: SimpleNamespace(id='climate-archive-test'),
        get_wd=lambda runid: str(root), get_prep_from_runid=lambda runid: None,
        lock_statuses=lambda runid: {}, clear_nodb_file_cache=lambda runid: [],
        publish_status=lambda channel, message: None, disk_usage=shutil.disk_usage,
        zip_file_cls=zipfile.ZipFile, project_config_lifecycle_guard=project_config_lifecycle_guard,
        project_config_authority_wd=lambda runid: str(root),
    )
    archive_rq('climate-fixture', 'climate lineage history', runtime=runtime)
    archive = next((root / 'archives').glob('*.zip'))
    with zipfile.ZipFile(archive) as members:
        assert expected.keys() <= set(members.namelist())
        assert all(members.read(name) == data for name, data in expected.items())
    shutil.rmtree(root / 'climate_artifacts')
    restore_archive_rq('climate-fixture', archive.name, runtime=runtime)
    assert all((root / name).read_bytes() == data for name, data in expected.items())
    for name in expected:
        if name.endswith(('source.cli', 'status.json')):
            assert (root / name).stat().st_mode & 0o077 == 0


def test_attempt_subtree_symlink_cannot_redirect_snapshot(tmp_path):
    from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService
    import logging
    from types import SimpleNamespace
    source = tmp_path / 'source.cli'
    _write_minimal_cli(source)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'climate_artifacts').symlink_to(outside, target_is_directory=True)
    owner = SimpleNamespace(wd=str(tmp_path), cli_dir=str(tmp_path), cli_fn=source.name,
                            logger=logging.getLogger('cli-lineage-containment'))
    assert ClimateArtifactExportService().export_cli_parquet(owner) is None
    assert list(outside.iterdir()) == []


def test_postcommit_status_failure_keeps_success(owner_project, monkeypatch):
    root, _ = owner_project
    owner, source = selected(root)
    change(source)
    original = _CliParquetAttempt._status
    def fail_status(self, status, error=None):
        if status == 'complete':
            raise OSError('controlled status failure')
        return original(self, status, error)
    monkeypatch.setattr(_CliParquetAttempt, '_status', fail_status)
    output = owner._export_cli_parquet()
    assert output is not None
    assert pd.read_parquet(output).iloc[0]['prcp'] == 8.
    assert production.sources(root)[2]['climate']


def test_run_root_alias_preserves_portable_selected_identity(owner_project):
    root, _ = owner_project
    output = root / 'climate/wepp_cli.parquet'
    output.unlink()
    alias = root.with_name(root.name + '-alias')
    alias.symlink_to(root, target_is_directory=True)
    assert _ensure_cli_parquet(alias / 'climate') is not None
    assert proof(output)['source'] == 'climate/owner.cli'
    assert proof(output)['resolved_source'] == 'climate/owner.cli'
    assert production.sources(root)[2]['climate']


@pytest.mark.parametrize('content', [True, False])
def test_footer_replacement_rejects_inventory_generation_mismatch(owner_project, monkeypatch, content):
    from wepppy.climates import cli_parquet
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


def test_interchange_disappearing_hint_does_not_publish_fallback_proof(owner_project, monkeypatch):
    root, _ = owner_project
    _, source = selected(root)
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
    assert fallback.exists()


@pytest.mark.parametrize('content', [False, True])
def test_parent_replacement_hardlinks_cannot_keep_lineage_current(owner_project, monkeypatch, content):
    from wepppy.climates import cli_parquet
    root, _ = owner_project
    parent = root / 'climate'
    replacement = root / 'replacement-climate'
    replacement.mkdir()
    for item in parent.iterdir():
        if item.is_file():
            os.link(item, replacement / item.name)
    real = cli_parquet._read_proof
    def read_then_replace(stream, limit):
        result = real(stream, limit)
        parent.rename(root / 'former-climate')
        replacement.rename(parent)
        return result
    monkeypatch.setattr(cli_parquet, '_read_proof', read_then_replace)
    with pytest.raises(production.WorkflowError) as caught:
        production.sources(root, content=content)
    assert caught.value.code == 'changed_source'
