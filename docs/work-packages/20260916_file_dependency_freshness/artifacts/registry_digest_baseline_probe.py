"""Actual executable identity helper under rapid real-file rewrites; no execution."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from wepppy.nodb.config_builder.registry import _executable_sha256

with TemporaryDirectory(prefix='registry-digest-') as work:
    path = Path(work) / 'fixture'
    path.write_bytes(b'A' * 1024)
    path.chmod(0o700)
    original = path.stat()
    stale = 0
    same_version = 0
    for i in range(1000):
        first = bytes([65 + i % 2]) * 1024
        second = bytes([66 - i % 2]) * 1024
        path.write_bytes(first)
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        _executable_sha256(str(path), 'fixture', 'watershed')
        before = path.stat()
        path.write_bytes(second)
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        after = path.stat()
        same_version += (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        observed = _executable_sha256(str(path), 'fixture', 'watershed')
        stale += observed != hashlib.sha256(second).hexdigest()
    print(json.dumps({'iterations': 1000, 'same_version_rewrites': same_version,
                      'stale_digests': stale, 'filesystem': '/tmp in canonical container'}, indent=2))
