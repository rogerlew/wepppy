"""Disposable canonical restore authority and directory-mode observations."""
import builtins
import errno
import json
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace
import zipfile

import pytest

from wepppy.nodb.project_config_update import project_config_lifecycle_guard
from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq


RESULTS = {}


def record(name, value):
    RESULTS[name] = value
    Path(__file__).with_suffix('.json').write_text(json.dumps(RESULTS, indent=2) + '\n')
    print(json.dumps({name: value}))


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def runtime(run, messages):
    return ArchiveRuntime(
        get_current_job=lambda: SimpleNamespace(id='security-disposable'),
        get_wd=lambda runid: str(run), get_prep_from_runid=lambda runid: None,
        lock_statuses=lambda runid: {}, clear_nodb_file_cache=lambda runid: [],
        publish_status=lambda channel, message: messages.append(message),
        disk_usage=shutil.disk_usage, zip_file_cls=zipfile.ZipFile,
        project_config_lifecycle_guard=project_config_lifecycle_guard,
        project_config_authority_wd=lambda runid: str(run))


def directory(name, permissions, unix=True):
    info = zipfile.ZipInfo(name)
    info.create_system = 3 if unix else 0
    info.external_attr = (stat.S_IFDIR | permissions) << 16 | 0x10
    return info


def fixture_archive(run, entries):
    (run / 'archives').mkdir(exist_ok=True)
    archive = run / 'archives' / 'fixture.zip'
    with zipfile.ZipFile(archive, 'w') as target:
        for info, payload in entries:
            target.writestr(info, payload)
    return archive


@pytest.mark.parametrize('permissions', [0o000, 0o500, 0o750])
def test_private_ancestry_precedes_payload_and_final_modes_follow_children(tmp_path, monkeypatch, permissions):
    run = tmp_path / 'run'
    run.mkdir(mode=0o750)
    (run / 'old.txt').write_text('old')
    archive = fixture_archive(run, [
        ('private/child/payload.txt', b'private bytes'),
        (directory('private/child/', 0o400), b''),
        (directory('empty/', 0o711), b''),
        (directory('private/', permissions), b''),
        (directory('./', 0o000), b''),
    ])
    seen = []
    original = builtins.open

    def observing_open(file, mode_arg='r', *args, **kwargs):
        if str(file).endswith('/private/child/payload.txt') and mode_arg == 'wb':
            seen.append({'parent': mode(run / 'private'),
                         'child': mode(run / 'private/child'),
                         'root': mode(run)})
        return original(file, mode_arg, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', observing_open)
    messages = []
    restore_archive_rq('security-disposable', archive.name, runtime=runtime(run, messages))
    parent_final = mode(run / 'private')
    # Reopen only the disposable owner path after recording its restored mode.
    (run / 'private').chmod(0o700)
    child_final = mode(run / 'private/child')
    (run / 'private/child').chmod(0o700)
    result = {'uid': os.geteuid(), 'first_payload': seen,
              'parent_final': parent_final, 'child_final': child_final,
              'root_final': mode(run), 'empty_final': mode(run / 'empty'),
              'bytes': (run / 'private/child/payload.txt').read_text(),
              'completed': any('RESTORE_COMPLETE' in value for value in messages)}
    record(f'prepayload_{permissions:o}', result)
    assert seen == [{'parent': permissions | 0o700, 'child': 0o700, 'root': 0o750}]
    assert parent_final == permissions and child_final == 0o400
    assert result['root_final'] == 0o750 and result['empty_final'] == 0o711
    assert result['bytes'] == 'private bytes' and result['completed']


@pytest.mark.parametrize('conflict', [False, True])
def test_resolved_duplicate_directory_modes_are_validated_before_removal(tmp_path, conflict):
    run = tmp_path / 'run'
    run.mkdir()
    marker = run / 'prior.txt'
    marker.write_text('preserve on rejected inventory')
    archive = fixture_archive(run, [
        (directory('private/', 0o700), b''),
        (directory('./private/', 0o755 if conflict else 0o700), b''),
        ('private/data.txt', b'data'),
    ])
    messages = []
    if conflict:
        with pytest.raises(ValueError, match='Conflicting archive directory modes'):
            restore_archive_rq('security-disposable', archive.name, runtime=runtime(run, messages))
        assert marker.read_text() == 'preserve on rejected inventory'
        assert not (run / 'private').exists()
        assert not any('Removing ' in item for item in messages)
    else:
        restore_archive_rq('security-disposable', archive.name, runtime=runtime(run, messages))
        assert mode(run / 'private') == 0o700
        assert (run / 'private/data.txt').read_bytes() == b'data'
    record(f'duplicate_{conflict}', {'rejected': conflict, 'prior_present': marker.exists()})


def test_legacy_metadata_exclusions_and_directory_symlink_policy(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    control = tmp_path / 'umask-control'
    control.mkdir()
    archive = fixture_archive(run, [
        ('legacy/payload.txt', b'legacy'),
        (directory('nonunix/', 0o000, unix=False), b''),
        ('nonunix/payload.txt', b'nonunix'),
        ('archives/poison.txt', b'excluded'),
        ('.config-amendment.lock', b'excluded poison'),
        ('.config-amendment.pending.json', b'excluded'),
    ])
    untouched = run / 'archives/untouched.txt'
    untouched.write_text('keep')
    messages = []
    restore_archive_rq('security-disposable', archive.name, runtime=runtime(run, messages))
    assert mode(run / 'legacy') == mode(control)
    assert mode(run / 'nonunix') == mode(control)
    assert untouched.read_text() == 'keep'
    assert not (run / 'archives/poison.txt').exists()
    assert not (run / '.config-amendment.pending.json').exists()
    assert (run / '.config-amendment.lock').read_bytes() != b'excluded poison'
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'outside.txt').write_text('outside')
    (run / 'directory-alias').symlink_to(outside, target_is_directory=True)
    (run / 'ordinary-empty').mkdir(mode=0o750)
    archive_rq('security-disposable', None, runtime=runtime(run, messages))
    produced = next(path for path in (run / 'archives').glob('security-disposable.*.zip'))
    with zipfile.ZipFile(produced) as saved:
        names = saved.namelist()
        assert 'ordinary-empty/' in names
        assert not any(name.startswith('directory-alias') for name in names)
        assert not any(name.startswith('archives') for name in names)
        assert '.config-amendment.lock' not in names
    record('legacy_exclusions', {'legacy_mode': mode(run / 'legacy'),
                                'nonunix_mode': mode(run / 'nonunix'), 'new_members': names})


@pytest.mark.parametrize('final', [False, True])
def test_required_directory_mode_failure_is_explicit(tmp_path, monkeypatch, final):
    run = tmp_path / 'run'
    run.mkdir()
    archive = fixture_archive(run, [(directory('private/', 0o500), b''),
                                    ('private/payload.txt', b'data')])
    original = os.chmod
    messages = []

    def failing_chmod(path, permissions, *args, **kwargs):
        if Path(path) == run / 'private' and permissions == (0o500 if final else 0o700):
            raise OSError(errno.EIO, 'disposable required-mode failure')
        return original(path, permissions, *args, **kwargs)

    monkeypatch.setattr(os, 'chmod', failing_chmod)
    with pytest.raises(OSError, match='disposable required-mode failure'):
        restore_archive_rq('security-disposable', archive.name, runtime=runtime(run, messages))
    assert not any('RESTORE_COMPLETE' in item for item in messages)
    assert any('RESTORE_FAILED' in item for item in messages)
    assert archive.is_file()
    assert (run / 'private/payload.txt').exists() is final
    record(f'chmod_failure_{final}', {'archive_retained': True,
                                    'payload_created': (run / 'private/payload.txt').exists()})
