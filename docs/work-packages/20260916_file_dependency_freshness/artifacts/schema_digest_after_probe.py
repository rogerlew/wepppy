"""Actual output-discovery helper, real restored-time changes, no named mutations."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from wepppy.microservices.rq_engine.schema_defaults_routes import _sha256_file

with tempfile.TemporaryDirectory(prefix='schema-digest-') as work:
    path = Path(work) / 'export.zip'
    path.write_bytes(b'first export')
    before = path.stat()
    old = _sha256_file(path)
    path.write_bytes(b'other export')
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    current = _sha256_file(path)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps({'old': old, 'observed': current, 'expected': expected,
                      'equal_size': path.stat().st_size == before.st_size,
                      'same_mtime': path.stat().st_mtime_ns == before.st_mtime_ns,
                      'stale_digest': current == old != expected}, indent=2))
    assert current == expected != old
