"""RedisPrep file boundary; caller holds the project lifecycle guard."""
from __future__ import annotations

import json
import math
import os
import stat
from uuid import uuid4


class RedisPrepSnapshotError(RuntimeError):
    """A snapshot operation failed, with its cross-store commit stage retained."""

    def __init__(self, message: str, *, published: bool | None = False, live_committed: bool | None = False):
        super().__init__(message)
        self.published = published
        self.live_committed = live_committed


def validate_snapshot(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError('RedisPrep snapshot must contain an object')
    for key, value in payload.items():
        if (not isinstance(key, str) or isinstance(value, bool)
                or not isinstance(value, (str, int, float))
                or isinstance(value, float) and not math.isfinite(value)):
            raise ValueError('RedisPrep snapshot fields must be Redis-compatible scalars')
    return {k: v for k, v in payload.items() if not k.startswith('locked:')}


def read_snapshot(directory_fd: int) -> dict:
    fd = os.open('redisprep.dump', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, encoding='utf-8') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('RedisPrep snapshot must be a regular file')
        return validate_snapshot(json.load(stream))


def publish_snapshot(directory_fd: int, payload: dict, *, target_mode: int | None = None) -> None:
    """Replace complete bytes, preserving access; never roll back after replace."""
    encoded = json.dumps(validate_snapshot(payload), allow_nan=False).encode('utf-8')
    original = None
    attributes = {}
    try:
        source = os.open('redisprep.dump', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    except FileNotFoundError:
        pass
    else:
        try:
            original = os.fstat(source)
            if not stat.S_ISREG(original.st_mode):
                raise ValueError('RedisPrep snapshot must be a regular file')
            attributes = {name: os.getxattr(source, name) for name in os.listxattr(source)}
        finally:
            os.close(source)
    name = '.redisprep.dump.' + uuid4().hex + '.tmp'
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                 0o600 if original else 0o666, dir_fd=directory_fd)
    published = False
    replace_attempted = False
    try:
        try:
            if original is not None:
                current = os.fstat(fd)
                if (current.st_uid, current.st_gid) != (original.st_uid, original.st_gid):
                    os.fchown(fd, original.st_uid, original.st_gid)
                for attr in set(os.listxattr(fd)) - attributes.keys():
                    os.removexattr(fd, attr)
                for attr, value in attributes.items():
                    os.setxattr(fd, attr, value)
                os.fchmod(fd, stat.S_IMODE(original.st_mode))
                if {attr: os.getxattr(fd, attr) for attr in os.listxattr(fd)} != attributes:
                    raise PermissionError('Cannot preserve RedisPrep snapshot access attributes')
            if target_mode is not None:
                os.fchmod(fd, target_mode)
            written = 0
            while written < len(encoded):
                count = os.write(fd, encoded[written:])
                if count <= 0:
                    raise OSError('Short write while persisting RedisPrep snapshot')
                written += count
            os.fsync(fd)
        finally:
            os.close(fd)
        replace_attempted = True
        os.replace(name, 'redisprep.dump', src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        published = True
        os.fsync(directory_fd)
    except OSError as exc:
        raise RedisPrepSnapshotError(
            'RedisPrep snapshot published; directory durability uncertain' if published
            else ('RedisPrep snapshot replacement outcome uncertain; inspect destination'
                  if replace_attempted else 'RedisPrep snapshot not published; prior snapshot retained'),
            published=True if published else (None if replace_attempted else False),
        ) from exc
    finally:
        try:
            os.unlink(name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise RedisPrepSnapshotError(
                'RedisPrep staging cleanup failed' + (' after publication' if published else ' before publication'),
                published=True if published else (None if replace_attempted else False),
            ) from exc
