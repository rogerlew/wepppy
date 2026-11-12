"""Untrusted image files remain data throughout independent inventory."""
import hashlib
import io
import tarfile

import pytest

from tools.security.archive_inventory import inventory_archive

pytestmark = pytest.mark.unit
LOCK = 'workdir/wepppy/wepppy/weppcloud/static-src/package-lock.json'
SCIENCE = b'CLIGEN station text\n'
ELF = b'\x7fELF\x02\x01' + b'\0' * 10 + b'\x03\0' + b'\0' * 46


def write_archive(tmp_path, extras=(), omit=()):
    rows = [('data/station.par', SCIENCE), (LOCK, b'{}'),
            ('var/lib/dpkg/status', b'Package: sample\nStatus: install ok installed\nVersion: 1.0\n\n'),
            ('opt/venv/lib/python3.12/site-packages/sample-1.0.dist-info/METADATA', b'Name: sample\nVersion: 1.0\n'),
            ('usr/lib/libsample.so', ELF)]
    path = tmp_path / 'filesystem.tar'
    with tarfile.open(path, 'w') as stream:
        for name, data in [r for r in rows if r[0] not in omit] + list(extras):
            member = tarfile.TarInfo(name)
            if isinstance(data, bytes):
                member.size = len(data)
                stream.addfile(member, io.BytesIO(data))
            else:
                member.type, member.linkname = data
                stream.addfile(member)
    return path


def collect(path):
    return inventory_archive(path, {'exclude': ['/data/*.par']},
        [{'path': '/data/station.par', 'size': len(SCIENCE),
          'sha256': hashlib.sha256(SCIENCE).hexdigest()}], 'sha256:' + 'a' * 64)


def test_data_only_inventory_does_not_execute_candidate_startup(tmp_path):
    sentinel = tmp_path / 'executed'
    hostile = f'from pathlib import Path; Path({str(sentinel)!r}).write_text("executed")'.encode()
    path = write_archive(tmp_path, [('opt/venv/lib/python3.12/site-packages/sitecustomize.py', hostile),
                                    ('opt/venv/bin/python', hostile)])
    result = collect(path)
    assert not sentinel.exists()
    assert result['scientific_files_verified'] == 1
    assert result['python'][0]['name'] == 'sample'
    assert result['deb'][0]['version'] == '1.0'
    assert result['native_files'] == [{'path': '/usr/lib/libsample.so', 'sha256': hashlib.sha256(ELF).hexdigest()}]
    assert not (tmp_path / 'opt').exists()


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'data/../escape', 'data\\escape'])
def test_unsafe_member_paths_fail_without_extraction(tmp_path, name):
    with pytest.raises(ValueError, match='unsafe'):
        collect(write_archive(tmp_path, [(name, b'payload')]))


def test_duplicate_member_rejected(tmp_path):
    with pytest.raises(ValueError, match='duplicate'):
        collect(write_archive(tmp_path, [('usr/lib/libsample.so', b'changed')]))


@pytest.mark.parametrize('entry', [(tarfile.DIRTYPE, ''), (tarfile.SYMTYPE, 'elsewhere'), b'PK\x03\x04hidden'])
def test_hidden_scientific_entry_rejected(tmp_path, entry):
    with pytest.raises(ValueError, match='extra or nonregular'):
        collect(write_archive(tmp_path, [('data/.hidden.par', entry)]))


def test_changed_scientific_bytes_rejected(tmp_path):
    with pytest.raises(ValueError, match='requalification'):
        collect(write_archive(tmp_path, [('data/station.par', b'changed')], omit=['data/station.par']))


def test_missing_scientific_file_rejected(tmp_path):
    with pytest.raises(ValueError, match='match set'):
        collect(write_archive(tmp_path, omit=['data/station.par']))


def test_symlink_scientific_parent_rejected(tmp_path):
    with pytest.raises(ValueError, match='symlink'):
        collect(write_archive(tmp_path, [('data', (tarfile.SYMTYPE, 'outside'))]))


def test_native_hardlink_aliases_resolve_forward_and_chained(tmp_path):
    entries = [('alias-first', (tarfile.LNKTYPE, 'alias-second')),
               ('alias-second', (tarfile.LNKTYPE, 'usr/lib/libsample.so'))]
    result = collect(write_archive(tmp_path, entries))
    assert {r['path'] for r in result['native_files']} == {'/usr/lib/libsample.so', '/alias-first', '/alias-second'}
    assert {r['sha256'] for r in result['native_files']} == {hashlib.sha256(ELF).hexdigest()}


@pytest.mark.parametrize('entries', [[('alias', (tarfile.LNKTYPE, 'missing'))],
    [('a', (tarfile.LNKTYPE, 'b')), ('b', (tarfile.LNKTYPE, 'a'))],
    [('alias', (tarfile.LNKTYPE, 'symbolic')), ('symbolic', (tarfile.SYMTYPE, 'usr/lib/libsample.so'))]])
def test_missing_cyclic_or_nonregular_hardlink_target_rejected(tmp_path, entries):
    with pytest.raises(ValueError, match='hardlink'):
        collect(write_archive(tmp_path, entries))


def test_relocatable_object_is_not_an_executable(tmp_path):
    relocatable = ELF[:16] + b'\x01\0' + ELF[18:]
    result = collect(write_archive(tmp_path, [('usr/lib/object.o', relocatable)]))
    assert len(result['native_files']) == 1


def test_held_package_remains_in_direct_inventory(tmp_path):
    status = b'Package: held\nStatus: hold ok installed\nVersion: 2.0\n\n'
    result = collect(write_archive(tmp_path, [('var/lib/dpkg/status', status)], omit=['var/lib/dpkg/status']))
    assert result['deb'] == [{'name': 'held', 'version': '2.0', 'path': '/var/lib/dpkg/status'}]


@pytest.mark.parametrize('entry', [(tarfile.SYMTYPE, 'other'), (tarfile.DIRTYPE, '')])
def test_nonregular_python_metadata_cannot_disappear(tmp_path, entry):
    with pytest.raises(ValueError, match='nonregular package metadata'):
        collect(write_archive(tmp_path, [('opt/venv/lib/python3.12/site-packages/linked.dist-info/METADATA', entry)]))


@pytest.mark.parametrize('metadata', [b'Name: first\nName: second\nVersion: 1.0\n',
    b'Name: first\nVersion: 1.0\nVersion: 2.0\n', b'Name: \nVersion: 1.0\n',
    b'Name: first\nVersion: 1.0\nbroken header\n'])
def test_ambiguous_or_malformed_python_identity_rejected(tmp_path, metadata):
    with pytest.raises(ValueError, match='package metadata'):
        collect(write_archive(tmp_path, [('other.dist-info/METADATA', metadata)]))


@pytest.mark.parametrize('status', ['install reinstreq installed', 'hold ok unpacked',
                                   'install ok installed\nStatus: install ok installed'])
def test_ambiguous_or_partial_debian_state_rejected(tmp_path, status):
    raw = f'Package: partial\nStatus: {status}\nVersion: 1.0\n\n'.encode()
    with pytest.raises(ValueError):
        collect(write_archive(tmp_path, [('var/lib/dpkg/status', raw)], omit=['var/lib/dpkg/status']))


@pytest.mark.parametrize('suffix', ['.dist-info', '.egg-info'])
def test_linked_metadata_root_cannot_hide_distribution(tmp_path, suffix):
    with pytest.raises(ValueError, match='metadata root'):
        collect(write_archive(tmp_path, [('linked' + suffix, (tarfile.SYMTYPE, 'records/linked')),
            ('records/linked/METADATA', b'Name: linked\nVersion: 2.0\n')]))


def test_legacy_single_file_egg_info_is_inventoried(tmp_path):
    result = collect(write_archive(tmp_path, [('legacy.egg-info', b'Name: legacy\nVersion: 2.0\n')]))
    assert {'name': 'legacy', 'version': '2.0', 'path': '/legacy.egg-info'} in result['python']


def test_python_metadata_hardlinks_preserve_each_alias_identity(tmp_path):
    target = 'opt/venv/lib/python3.12/site-packages/sample-1.0.dist-info/METADATA'
    result = collect(write_archive(tmp_path, [
        ('cache/second.dist-info/METADATA', (tarfile.LNKTYPE, 'cache/first.dist-info/METADATA')),
        ('cache/first.dist-info/METADATA', (tarfile.LNKTYPE, target))]))
    assert {r['path'] for r in result['python']} == {'/'+target, '/cache/first.dist-info/METADATA', '/cache/second.dist-info/METADATA'}
    assert all(r['name'] == 'sample' and r['version'] == '1.0' for r in result['python'])


def test_python_metadata_hardlink_to_nonmetadata_is_not_omitted(tmp_path):
    with pytest.raises(ValueError, match='lacks qualified identity'):
        collect(write_archive(tmp_path, [('cache/unknown.dist-info/METADATA', (tarfile.LNKTYPE, LOCK))]))
