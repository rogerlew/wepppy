"""Verified ordinary-file hashes; callers retain path and access authority.

See docs/schemas/file-dependency-freshness-contract.md. This follows ordinary
symlinks and is not a replacement for a caller's required no-follow opener.
"""
from functools import lru_cache
import errno
import hashlib
import os
from pathlib import Path
import stat
from time import monotonic_ns

__all__ = ["sha256_file"]


def _version(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@lru_cache(maxsize=512)
def _observed_at(path, version):
    return monotonic_ns()


@lru_cache(maxsize=512)
def _digest(path, version, observation):
    # observation distinguishes a new admission after observation-cache eviction.
    checksum = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or _version(before) != version:
            raise OSError(errno.ESTALE, "File changed while opening", path)
        while block := stream.read(min(1024 * 1024, version[2] - size + 1)):
            size += len(block)
            if size > version[2]:
                raise OSError(errno.ESTALE, "File grew while hashing", path)
            checksum.update(block)
        if (size != version[2] or _version(os.fstat(stream.fileno())) != version
                or _version(Path(path).stat()) != version):
            raise OSError(errno.ESTALE, "File changed while hashing", path)
    return checksum.hexdigest()


def sha256_file(path: str | Path, *, use_cache: bool = True) -> str:
    """Hash a regular file with access/read checks and guarded bounded reuse.

    Changed versions remain uncached for one monotonic second. Settled reuse
    requires coherent filesystem metadata; see the cache-admission ADR.
    """
    path = Path(path).absolute()
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        version = _version(info)
        if not stat.S_ISREG(info.st_mode):
            raise OSError(errno.EINVAL, "Expected a regular file", str(path))
        if _version(path.stat()) != version:
            raise OSError(errno.ESTALE, "File changed while opening", str(path))
        observation = _observed_at(str(path), version) if use_cache else None
        if not use_cache or monotonic_ns() - observation < 1_000_000_000:
            checksum = _digest.__wrapped__(str(path), version, observation)
        else:
            checksum = _digest(str(path), version, observation)
        if (_version(os.fstat(stream.fileno())) != version
                or _version(path.stat()) != version):
            raise OSError(errno.ESTALE, "File changed while hashing", str(path))
    return checksum
