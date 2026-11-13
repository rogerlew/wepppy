"""Kernel-owned NFS metadata must be preserved without redundant writes."""
import errno
import json
import os
import stat

import pytest

from wepppy.nodb import _redis_prep_snapshot as snapshots


def nfs_attributes(monkeypatch, source_inode, *, mismatched_label=False):
    user_values = {source_inode: b'original-user-value'}

    def attributes(fd):
        info = os.fstat(fd)
        label = b'other' if mismatched_label and info.st_ino != source_inode else b'nfs-label'
        result = {'system.nfs4_acl': str(stat.S_IMODE(info.st_mode)).encode(),
                  'security.selinux': label}
        if info.st_ino in user_values:
            result['user.project'] = user_values[info.st_ino]
        return result

    def set_attribute(fd, name, value):
        if name != 'user.project':
            raise OSError(errno.EOPNOTSUPP, 'Kernel-owned attribute cannot be set')
        user_values[os.fstat(fd).st_ino] = value

    monkeypatch.setattr(snapshots.os, 'listxattr', lambda fd: list(attributes(fd)))
    monkeypatch.setattr(snapshots.os, 'getxattr', lambda fd, name: attributes(fd)[name])
    monkeypatch.setattr(snapshots.os, 'setxattr', set_attribute)
    return attributes


def test_preserves_inherited_nfs_acl_label_and_changed_user_attribute(tmp_path, monkeypatch):
    path = tmp_path / 'redisprep.dump'
    path.write_text('{"generation":1}')
    path.chmod(0o640)
    attributes = nfs_attributes(monkeypatch, path.stat().st_ino)
    fd = os.open(tmp_path, os.O_RDONLY)
    try:
        snapshots.publish_snapshot(fd, {'generation': 2})
    finally:
        os.close(fd)
    assert json.loads(path.read_text()) == {'generation': 2}
    with path.open() as stream:
        assert attributes(stream.fileno()) == {
            'system.nfs4_acl': b'416', 'security.selinux': b'nfs-label',
            'user.project': b'original-user-value'}
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert not list(tmp_path.glob('.redisprep.dump.*.tmp'))


def test_unpreservable_changed_system_attribute_retains_original(tmp_path, monkeypatch):
    path = tmp_path / 'redisprep.dump'
    original = '{"generation":1}'
    path.write_text(original)
    path.chmod(0o640)
    inode = path.stat().st_ino
    nfs_attributes(monkeypatch, inode, mismatched_label=True)
    fd = os.open(tmp_path, os.O_RDONLY)
    try:
        with pytest.raises(snapshots.RedisPrepSnapshotError) as caught:
            snapshots.publish_snapshot(fd, {'generation': 2})
        assert caught.value.published is False
        assert caught.value.__cause__.errno == errno.EOPNOTSUPP
    finally:
        os.close(fd)
    assert path.stat().st_ino == inode and path.read_text() == original
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert not list(tmp_path.glob('.redisprep.dump.*.tmp'))
