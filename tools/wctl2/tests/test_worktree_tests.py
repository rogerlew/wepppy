from __future__ import annotations

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app
from tools.wctl2.commands import worktree_tests as command
from tools.wctl2 import test_runtime as runtime

pytestmark = pytest.mark.unit


def git_repo(path):
    subprocess.run(['git', 'init', '-q', str(path)], check=True)
    (path / '.gitignore').write_text('.wctl-test-runs/\n')
    (path / 'example.py').write_text('value = 1\n')
    subprocess.run(['git', '-C', str(path), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(path), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    return path


def test_missing_bind_source_does_not_create_directories(tmp_path):
    with pytest.raises(FileNotFoundError):
        command.bind(tmp_path / 'missing', '/target')
    assert not (tmp_path / 'missing').exists()


def test_mount_path_injection_rejected(tmp_path):
    path = tmp_path / 'bad,readonly=false'
    path.mkdir()
    with pytest.raises(ValueError, match='commas'):
        command.bind(path, '/target')


@pytest.mark.parametrize("command_name", ["run-pytest", "run-pytest-worktree"])
def test_worktree_cli_runs_oneoff_with_nonce_and_preserves_pytest_args(temp_project, monkeypatch, command_name):
    git_repo(temp_project)
    calls = []
    monkeypatch.setenv("GIT_DIR", "/nonexistent/foreign-checkout")
    monkeypatch.setenv("WCTL_TEST_CONTEXT", "preserved")
    def run(context, args, check):
        assert context.environment["WCTL_TEST_CONTEXT"] == "preserved"
        calls.append(args)
        assert list(temp_project.glob('.wctl-checkout-*'))
        return SimpleNamespace(returncode=7)
    monkeypatch.setattr(command, 'run_compose', run)
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), command_name,
        '--checkout', str(temp_project), '--profile', 'python', '--', 'tools/wctl2/tests', '-k', 'one or two'])
    assert result.exit_code == 7, result.output
    assert calls[0][:7] == ['run', '--rm', '--no-deps', '--pull', 'never', '-T', '--volume']
    assert 'one or two' in calls[0][-1]
    assert '.wctl-checkout-' in calls[0][-1]
    assert not list(temp_project.glob('.wctl-checkout-*'))
    assert ':ro' in ' '.join(calls[0])


@pytest.mark.parametrize("selection", [None, "tests", "./tests", "tests/", "tests/../tests", "."])
def test_full_suite_cannot_select_python_only_profile(temp_project, monkeypatch, selection):
    monkeypatch.setattr(command, 'run_compose', lambda *a, **kw: pytest.fail('must not run'))
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), 'run-pytest-worktree', '--profile', 'python'] + ([] if selection is None else ['--', selection]))
    assert result.exit_code == 2
    assert 'Full-suite' in result.output


def test_preflight_collects_all_missing_prerequisites(monkeypatch, tmp_path):
    def missing(*args):
        raise ValueError('missing prerequisite')
    for name in ('controller_check', 'browser_check', 'parser_check', 'database_check'):
        monkeypatch.setattr(runtime, name, missing)
    checks = runtime.preflight(tmp_path, 'broad', False)
    assert [row['name'] for row in checks] == ['controllers', 'browser', 'shape_parser_cli', 'geoparquet_parser_cli', 'database']
    assert all(not row['ready'] for row in checks)


def test_manifest_detects_dirty_untracked_deleted_and_symlink_changes(tmp_path):
    git_repo(tmp_path)
    before = runtime.source_manifest(tmp_path)
    (tmp_path / 'example.py').unlink()
    (tmp_path / 'new.py').write_text('new')
    (tmp_path / 'link.py').symlink_to('new.py')
    (tmp_path / '.wctl-test-runs').mkdir()
    (tmp_path / '.wctl-test-runs/receipt.json').write_text('{}')
    after = runtime.source_manifest(tmp_path)
    assert runtime.source_changes(before, after) == ['example.py', 'link.py', 'new.py']


def test_failed_preflight_never_starts_pytest_and_preserves_receipt(tmp_path, monkeypatch):
    git_repo(tmp_path)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    monkeypatch.setattr(runtime, 'preflight', lambda *a: [{'name': 'database', 'ready': False, 'detail': 'schema missing'}])
    report = tmp_path / '.wctl-test-runs/r/receipt.json'
    assert runtime.main(['--receipt', str(report), '--', 'tests']) == 2
    data = json.loads(report.read_text())
    assert data['tests_started'] is False
    assert data['status'] == 'not_ready'
    with pytest.raises(FileExistsError):
        runtime.main(['--receipt', str(report)])


def test_preflight_cannot_silently_modify_source(tmp_path, monkeypatch):
    git_repo(tmp_path)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    def prepare(*args):
        (tmp_path / 'example.py').write_text('changed')
        return []
    monkeypatch.setattr(runtime, 'preflight', prepare)
    report = tmp_path / '.wctl-test-runs/r/receipt.json'
    assert runtime.main(['--receipt', str(report)]) == 3
    data = json.loads(report.read_text())
    assert not data['tests_started']
    assert data['source_changes'] == ['example.py']
    assert (tmp_path / 'example.py').read_text() == 'changed'


def test_pytest_source_mutation_overrides_success_and_uses_short_temp(tmp_path, monkeypatch):
    git_repo(tmp_path)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    monkeypatch.setattr(runtime, 'preflight', lambda *a: [])
    real_run = subprocess.run
    def run(args, **kwargs):
        if args[1:3] == ['-m', 'pytest']:
            assert args[-2] == '--basetemp'
            assert len(args[-1]) < 30
            (tmp_path / 'example.py').write_text('test side effect')
            return SimpleNamespace(returncode=0)
        return real_run(args, **kwargs)
    monkeypatch.setattr(runtime.subprocess, 'run', run)
    report = tmp_path / '.wctl-test-runs/r/receipt.json'
    assert runtime.main(['--receipt', str(report), '--', 'tools/test.py']) == 3
    assert json.loads(report.read_text())['pytest_exitstatus'] == 0


def test_user_basetemp_override_is_rejected(tmp_path):
    with pytest.raises(SystemExit) as error:
        runtime.main(['--receipt', str(tmp_path / 'out.json'), '--', 'tests', '--basetemp=/unsafe'])
    assert error.value.code == 2
    assert not (tmp_path / 'out.json').exists()


def make_node_root(path, version='1.0'):
    (path / 'node_modules').mkdir(parents=True)
    (path / 'package.json').write_text('{}')
    lock = {'packages': {'node_modules/example': {'version': version, 'integrity': 'abc'}}}
    for name in ('package-lock.json', 'node_modules/.package-lock.json'):
        (path / name).write_text(json.dumps(lock))


def test_node_provider_lock_mismatch_rejected(tmp_path):
    candidate, provider = tmp_path / 'candidate', tmp_path / 'provider'
    make_node_root(candidate)
    make_node_root(provider, '2.0')
    with pytest.raises(ValueError, match='differs from candidate'):
        runtime.node_lock_check(candidate, provider)


def test_node_installed_dependency_drift_rejected(tmp_path):
    make_node_root(tmp_path)
    (tmp_path / 'node_modules/.package-lock.json').write_text(json.dumps({'packages': {'node_modules/example': {'version': '2.0'}}}))
    with pytest.raises(ValueError, match='Installed Node dependency'):
        runtime.node_lock_check(tmp_path, tmp_path)


def test_missing_database_column_and_table_reported():
    table = SimpleNamespace(name='user', fullname='user', schema=None, columns=[SimpleNamespace(name='account_kind')])
    metadata = SimpleNamespace(sorted_tables=[table])
    inspector = SimpleNamespace(has_table=lambda *a, **kw: True, get_columns=lambda *a, **kw: [{'name': 'id'}])
    assert runtime.missing_columns(metadata, inspector) == {'user': ['account_kind']}
    inspector.has_table = lambda *a, **kw: False
    assert runtime.missing_columns(metadata, inspector) == {'user': ['account_kind']}


def test_parser_sources_require_full_inventory_and_matching_bytes(tmp_path):
    (tmp_path / 'src').mkdir()
    rows = []
    for name in ('Cargo.toml', 'Cargo.lock', 'src/main.rs'):
        path = tmp_path / name
        path.write_text(name)
        rows.append({'path': name, 'size_bytes': path.stat().st_size, 'sha256': runtime.digest(path)})
    runtime.validate_parser_sources(tmp_path, rows)
    (tmp_path / 'src/main.rs').write_text('changed')
    with pytest.raises(ValueError, match='does not match candidate'):
        runtime.validate_parser_sources(tmp_path, rows)
    (tmp_path / 'src/added.rs').write_text('new source')
    with pytest.raises(ValueError, match='inventory differs'):
        runtime.validate_parser_sources(tmp_path, rows)


def test_runtime_mutation_cannot_report_success(tmp_path, monkeypatch):
    git_repo(tmp_path)
    artifact = tmp_path / 'parser-binary'
    artifact.write_text('original')
    original = runtime.digest(artifact)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    monkeypatch.setattr(runtime, 'preflight', lambda *a: [{'name': 'parser', 'ready': True, 'identity': {'files': {str(artifact): original}}}])
    real_run = subprocess.run
    def run(args, **kwargs):
        if args[1:3] == ['-m', 'pytest']:
            artifact.write_text('mutated')
            return SimpleNamespace(returncode=0)
        return real_run(args, **kwargs)
    monkeypatch.setattr(runtime.subprocess, 'run', run)
    report = tmp_path / '.wctl-test-runs/r/receipt.json'
    assert runtime.main(['--receipt', str(report), '--', 'tools/test.py']) == 3
    assert json.loads(report.read_text())['status'] == 'runtime_changed'


def test_interrupted_pytest_retains_truthful_running_receipt(tmp_path, monkeypatch):
    git_repo(tmp_path)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    monkeypatch.setattr(runtime, 'preflight', lambda *a: [])
    real_run = subprocess.run
    def run(args, **kwargs):
        if args[1:3] == ['-m', 'pytest']:
            raise KeyboardInterrupt
        return real_run(args, **kwargs)
    monkeypatch.setattr(runtime.subprocess, 'run', run)
    report = tmp_path / '.wctl-test-runs/r/receipt.json'
    with pytest.raises(KeyboardInterrupt):
        runtime.main(['--receipt', str(report), '--', 'tools/test.py'])
    data = json.loads(report.read_text())
    assert data['status'] == 'running'
    assert data['tests_started'] is True
    assert 'pytest_exitstatus' not in data


def test_compose_project_does_not_override_default_caller_checkout(temp_project, tmp_path, monkeypatch):
    candidate = tmp_path / 'candidate'
    candidate.mkdir()
    git_repo(candidate)
    (candidate / 'tools/wctl2').mkdir(parents=True)
    (candidate / 'tools/wctl2/__main__.py').touch()
    (candidate / 'docker').mkdir()
    (candidate / 'docker/defaults.env').touch()
    monkeypatch.setenv('WCTL_CALLER_CWD', str(candidate))
    def run(context, args, check):
        assert context.project_dir == temp_project
        assert f'{candidate}:/workdir/wepppy' in args
        assert list(candidate.glob('.wctl-checkout-*'))
        assert not list(temp_project.glob('.wctl-checkout-*'))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(command, 'run_compose', run)
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), 'run-pytest-worktree',
                                     '--profile', 'python', '--', 'tools/wctl2/tests'])
    assert result.exit_code == 0, result.output
