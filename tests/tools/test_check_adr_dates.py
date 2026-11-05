from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHECKER = _REPO_ROOT / 'tools' / 'check_adr_dates.py'


def run_checker(repo_root, *, cwd=None):
    # An isolated interpreter proves this CI command needs no installed app or PYTHONPATH.
    return subprocess.run(
        [sys.executable, '-I', str(_CHECKER), '--repo-root', str(repo_root)],
        cwd=cwd, capture_output=True, text=True, check=False,
    )


@pytest.fixture()
def adr_dir(tmp_path):
    directory = tmp_path / 'docs' / 'adrs'
    directory.mkdir(parents=True)
    return directory


@pytest.mark.parametrize('metadata', [
    'Date: 2024-02-29',
    '**Date**: 2026-11-05',
    '**Date:** 2026-11-05',
    '- Date: 2026-11-05',
    'Status: Accepted. Date: 2026-11-05 UTC',
    'Date: 2026-11-04 Pacific / 2026-11-05 UTC',
])
def test_checker_accepts_catalog_date_formats(adr_dir, metadata):
    (adr_dir / 'ADR-0001-valid.md').write_text('# Decision\n\n' + metadata + '\n')
    result = run_checker(adr_dir.parents[1], cwd=adr_dir)
    assert result.returncode == 0, result.stderr
    assert '1 ADR' in result.stdout


@pytest.mark.parametrize('metadata', [
    '',
    'Date: YYYY-MM-DD',
    'Date: 2025-02-29',
    'Date: 2026-13-01',
    'Review Date: 2026-11-05',
    'Status: Accepted. Review Date: 2026-11-05',
    'Status: Accepted 2026-11-05',
    '## Provenance\nDate: 2026-11-05',
    '```\nDate: 2026-11-05\n```',
    'Date: invalid\nDate: 2026-11-05',
])
def test_checker_rejects_missing_or_invalid_recorded_dates(adr_dir, metadata):
    (adr_dir / 'ADR-0001-bad.md').write_text('# Decision\n\n' + metadata + '\n')
    (adr_dir / 'ADR-0002-good.md').write_text('# Good\nDate: 2026-11-05\n')
    result = run_checker(adr_dir.parents[1])
    assert result.returncode == 1
    assert 'ADR-0001-bad.md' in result.stderr
    assert 'Date: YYYY-MM-DD' in result.stderr
    assert 'ADR-0002-good.md' not in result.stderr


def test_checker_rejects_unfilled_template_but_excludes_authoring_files(adr_dir):
    template = (_REPO_ROOT / 'docs/adrs/ADR-template.md').read_text()
    (adr_dir / 'ADR-template.md').write_text(template)
    (adr_dir / 'README.md').write_text('# Authoring guide\n')
    record = adr_dir / 'ADR-0001-example.md'
    record.write_text(template)
    assert run_checker(adr_dir.parents[1]).returncode == 1
    record.write_text(template.replace('Date: YYYY-MM-DD  ', 'Date: 2026-11-05  ', 1))
    result = run_checker(adr_dir.parents[1])
    assert result.returncode == 0, result.stderr
    assert '1 ADR' in result.stdout


def test_checker_reports_each_bad_file_and_invalid_encoding(adr_dir):
    (adr_dir / 'ADR-0001-missing.md').write_text('# Missing\n')
    (adr_dir / 'ADR-0001-invalid.md').write_bytes(b'\xff')
    result = run_checker(adr_dir.parents[1])
    assert result.returncode == 1
    assert 'ADR-0001-missing.md' in result.stderr
    assert 'ADR-0001-invalid.md' in result.stderr


@pytest.mark.parametrize('state', ['missing', 'empty', 'symlink'])
def test_checker_rejects_absent_adr_source_tree(tmp_path, state):
    root = tmp_path / 'docs/adrs'
    root.parent.mkdir()
    if state == 'empty':
        root.mkdir()
    elif state == 'symlink':
        target = tmp_path / 'elsewhere'
        target.mkdir()
        (target / 'ADR-0001-present.md').write_text('# Existing\nDate: 2026-11-05\n')
        root.symlink_to(target, target_is_directory=True)
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert 'docs/adrs' in result.stderr


def test_repository_adrs_have_explicit_valid_dates():
    result = run_checker(_REPO_ROOT)
    assert result.returncode == 0, result.stderr
