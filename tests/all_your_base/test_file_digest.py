import errno
import hashlib
import os
from pathlib import Path

import pytest
from wepppy.all_your_base import file_digest as digest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolated_digest_cache():
    digest._observed_at.cache_clear()
    digest._digest.cache_clear()
    yield
    digest._observed_at.cache_clear()
    digest._digest.cache_clear()


def test_rapid_real_rewrites_do_not_reuse_old_bytes(tmp_path):
    path = tmp_path / 'input'
    path.write_bytes(b'A' * 1024)
    before = path.stat()
    for i in range(100):
        content = bytes([65 + i % 2]) * 1024
        path.write_bytes(content)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        assert digest.sha256_file(path) == hashlib.sha256(content).hexdigest()


def test_settled_cache_opens_but_does_not_read_and_eviction_rehashes(tmp_path, monkeypatch):
    path = tmp_path / 'input'
    path.write_bytes(b'content')
    clock = [0]
    monkeypatch.setattr(digest, 'monotonic_ns', lambda: clock[0])
    expected = digest.sha256_file(path)
    assert digest._digest.cache_info().currsize == 0
    clock[0] = 1_000_000_001
    assert digest.sha256_file(path) == expected
    real_open = Path.open
    reads = []
    opens = []
    class Reader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self, count):
            reads.append(count)
            return self.stream.read(count)
    def observed_open(path, *args, **kwargs):
        opens.append(path)
        return Reader(real_open(path, *args, **kwargs))
    monkeypatch.setattr(Path, 'open', observed_open)
    assert digest.sha256_file(path) == expected
    assert len(opens) == 1 and not reads
    digest._observed_at.cache_clear()
    clock[0] += 1
    digest.sha256_file(path)
    assert reads
    reads.clear()
    clock[0] += 1_000_000_001
    digest.sha256_file(path)
    assert reads  # Surviving old digest cannot satisfy a new observation generation.
    reads.clear()
    digest.sha256_file(path, use_cache=False)
    assert reads
    denied = PermissionError(errno.EACCES, 'denied', str(path))
    def fail_open(*args, **kwargs):
        raise denied
    monkeypatch.setattr(Path, 'open', fail_open)
    with pytest.raises(PermissionError) as caught:
        digest.sha256_file(path)
    assert caught.value is denied


@pytest.mark.parametrize('change', ['grow', 'truncate', 'replace'])
def test_observable_read_drift_is_not_cached(tmp_path, monkeypatch, change):
    path = tmp_path / 'input'
    path.write_bytes(b'AAAA')
    replacement = tmp_path / 'replacement'
    replacement.write_bytes(b'BBBB')
    real_open = Path.open
    reads = []
    class Reader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self, count):
            reads.append(count)
            data = self.stream.read(count)
            if len(reads) == 1:
                if change == 'replace':
                    os.replace(replacement, path)
                else:
                    with real_open(path, 'ab' if change == 'grow' else 'wb') as writer:
                        writer.write(b'XX')
            return data
    monkeypatch.setattr(Path, 'open', lambda path, *args, **kwargs: Reader(real_open(path, *args, **kwargs)))
    with pytest.raises(OSError) as caught:
        digest.sha256_file(path)
    assert caught.value.errno == errno.ESTALE
    assert reads == [5, 1]
    assert digest._digest.cache_info().currsize == 0


def test_empty_missing_and_metadata_only_operations(tmp_path):
    path = tmp_path / 'input'
    with pytest.raises(FileNotFoundError):
        digest.sha256_file(path)
    path.touch()
    expected = hashlib.sha256(b'').hexdigest()
    assert digest.sha256_file(path) == expected
    os.link(path, tmp_path / 'alias')
    path.chmod(0o600)
    os.utime(path, None)
    assert digest.sha256_file(path) == expected
    replacement = tmp_path / 'replacement'
    replacement.touch()
    os.replace(replacement, path)
    assert digest.sha256_file(path) == expected
    alias = tmp_path / 'symbolic'
    alias.symlink_to(path)
    assert digest.sha256_file(alias) == expected
    path.write_bytes(b'new bytes')
    assert digest.sha256_file(alias) == hashlib.sha256(b'new bytes').hexdigest()


def test_interleaved_paths_keep_both_caches_bounded(tmp_path, monkeypatch):
    clock = [0]
    monkeypatch.setattr(digest, 'monotonic_ns', lambda: clock[0])
    paths = []
    for i in range(600):
        path = tmp_path / f'project-{i % 2}-input-{i}'
        content = str(i).encode()
        path.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert digest.sha256_file(path) == expected
        clock[0] += 1_000_000_001
        assert digest.sha256_file(path) == expected
        paths.append((path, expected))
    assert digest._observed_at.cache_info().currsize == 512
    assert digest._digest.cache_info().currsize == 512
    for path, expected in paths[:10] + paths[-10:]:
        assert digest.sha256_file(path) == expected
