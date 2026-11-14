"""Fail before Docker when the external build identity is incomplete or wrong."""
from argparse import Namespace
import hashlib
import json
import os
import stat
import sys

import pytest

from tools.security.collect_image_evidence import (
    Collector,
    NODE_IMAGE,
    SCANNER_IMAGE,
    container,
    mount,
    sha,
    copy_regular,
)
from tools.security.import_dependency_evidence import EvidenceError
from tools.security.collect_image_evidence import analysis_diagnostic, QUALIFIED_WARNINGS

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('tool', ['syft', 'grype'])
def test_qualified_warning_is_exact_and_tool_scoped(tool):
    warning = QUALIFIED_WARNINGS[tool]
    assert not analysis_diagnostic(tool, '[0002]  ' + warning, qualified_scope=True)
    assert not analysis_diagnostic(tool, warning, qualified_scope=True)
    assert analysis_diagnostic(tool, warning, qualified_scope=False)
    assert analysis_diagnostic(tool, warning + ' extra failure', qualified_scope=True)
    assert analysis_diagnostic(tool, 'ERROR something failed; ' + warning, qualified_scope=True)
    assert analysis_diagnostic('other', warning, qualified_scope=True)
    assert analysis_diagnostic(tool, warning.replace('WARN', 'ERROR', 1), qualified_scope=True)


def test_other_diagnostics_remain_blocking():
    assert not analysis_diagnostic('grype', '[0000] INFO loaded database')
    assert analysis_diagnostic('grype', '[0001] WARN partial input')
    assert analysis_diagnostic('syft', 'FATAL parser failed')


@pytest.mark.parametrize('mutation', ['image', 'revision', 'dirty', 'failed', 'boolean_exit', 'lock', 'hash'])
def test_bad_build_binding_never_starts_docker(tmp_path, monkeypatch, mutation):
    lock = tmp_path / 'lock.json'
    lock.write_text('{}')
    build = {'image_id': 'sha256:' + 'a' * 64, 'source_revision': 'b' * 40,
             'source_clean': True, 'exit_status': 0,
             'static_build_lock_sha256': hashlib.sha256(lock.read_bytes()).hexdigest()}
    if mutation == 'image':
        build['image_id'] = 'sha256:' + 'c' * 64
    elif mutation == 'revision':
        build['source_revision'] = 'c' * 40
    elif mutation == 'dirty':
        build['source_clean'] = False
    elif mutation == 'failed':
        build['exit_status'] = 1
    elif mutation == 'boolean_exit':
        build['exit_status'] = False
    elif mutation == 'lock':
        build['static_build_lock_sha256'] = '0' * 64
    receipt = tmp_path / 'build.json'
    receipt.write_text(json.dumps(build))
    args = Namespace(image_id='sha256:'+'a'*64, source_revision='b'*40,
                     build_receipt=receipt, lock=lock,
                     build_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
    if mutation == 'hash':
        args.build_receipt_sha256 = '0' * 64
    collector = Collector(tmp_path / 'output')
    monkeypatch.setattr(collector, 'run', lambda *a, **kw: pytest.fail('started command before rejecting receipt'))
    with pytest.raises(EvidenceError):
        collector.collect(args)
    assert not (collector.output / 'bundle').exists()


def test_failed_command_retains_private_receipt_without_bundle(tmp_path):
    collector = Collector(tmp_path / 'output')
    with pytest.raises(EvidenceError, match='failed'):
        collector.run('synthetic', [sys.executable, '-c', 'print("failure"); raise SystemExit(7)'])
    receipt = json.loads((collector.output / 'synthetic-command.json').read_text())
    assert receipt['exit_status'] == 7
    assert stat.S_IMODE(collector.output.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in collector.output.iterdir())
    assert not (collector.output / 'bundle').exists()


def test_scanner_container_confinement():
    start, end = container('sha256:'+'a'*64, '/syft')
    assert '--read-only' in start and '--network' in start
    assert start[start.index('--network') + 1] == 'none'
    assert start[start.index('--cap-drop') + 1] == 'ALL'
    assert start[start.index('--user') + 1] == f'{os.getuid()}:{os.getgid()}'
    assert 'no-new-privileges' in start and not any('docker.sock' in arg for arg in start + end)
    assert mount('/private/image.tar', '/image.tar')[-1].endswith(',readonly')
    with pytest.raises(EvidenceError):
        mount('/private/evil,readonly=false', '/image.tar')


def test_scanner_carrier_is_source_addressable_and_has_no_implicit_volume():
    assert SCANNER_IMAGE == NODE_IMAGE
    assert SCANNER_IMAGE.startswith('docker.io/library/node:20-alpine@sha256:')
    start, _ = container(SCANNER_IMAGE, '/syft')
    assert '/data:ro,nosuid,nodev,noexec,size=1m' not in start


@pytest.mark.parametrize('kind', ['symlink', 'fifo'])
def test_report_read_rejects_nonregular_output(tmp_path, kind):
    source = tmp_path / 'report'
    if kind == 'symlink':
        outside = tmp_path / 'outside'
        outside.write_text('must not copy')
        source.symlink_to(outside)
    else:
        os.mkfifo(source)
    with pytest.raises((OSError, EvidenceError)):
        sha(source)
    with pytest.raises((OSError, EvidenceError)):
        copy_regular(source, tmp_path / 'retained')
    assert not (tmp_path / 'retained').exists()
