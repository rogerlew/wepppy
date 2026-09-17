"""Disposable actual-LRU and access checks; clock injection only for admission."""
import errno
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from wepppy.all_your_base import file_digest as digest
from wepppy.nodb.config_builder.registry import RegistryError, _executable_sha256


def main():
    records = {"uid": os.getuid(), "gid": os.getgid()}
    digest._observed_at.cache_clear()
    digest._digest.cache_clear()
    with TemporaryDirectory(prefix="shared-digest-security-") as temporary:
        root = Path(temporary)
        path = root / "input"
        path.write_bytes(b"actual target bytes")
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        clock = [0]
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
                result = self.stream.read(count)
                reads.append(len(result))
                return result
        def monitored_open(path, *args, **kwargs):
            return Reader(real_open(path, *args, **kwargs))
        with patch.object(digest, "monotonic_ns", lambda: clock[0]):
            assert digest.sha256_file(path) == expected
            assert digest._digest.cache_info().currsize == 0
            clock[0] = 1_000_000_001
            assert digest.sha256_file(path) == expected
            assert digest._digest.cache_info().currsize == 1
            for index in range(512):
                other = root / f"other-{index}"
                other.write_bytes(bytes([index % 256]))
                digest.sha256_file(other)
            assert digest._observed_at.cache_info().currsize == 512
            assert digest._digest.cache_info().currsize == 1
            clock[0] += 1
            with patch.object(Path, "open", monitored_open):
                assert digest.sha256_file(path) == expected
                assert sum(reads) == path.stat().st_size
                reads.clear()
                clock[0] += 1_000_000_001
                assert digest.sha256_file(path) == expected
                assert sum(reads) == path.stat().st_size
                reads.clear()
                assert digest.sha256_file(path) == expected
                assert reads == []
            records["actual_observation_eviction_forces_fresh_admission"] = True
            records["settled_content_bytes_read"] = sum(reads)
            alias = root / "alias"
            alias.symlink_to(path)
            assert digest.sha256_file(alias) == expected
            records["allowed_symlink_digest"] = True
            path.chmod(0o700)
            assert _executable_sha256(str(path), "fixture", "watershed") == expected
            path.chmod(0o600)
            try:
                _executable_sha256(str(path), "fixture", "watershed")
            except RegistryError as error:
                assert "unusable" in str(error)
                records["execute_access_loss_rejected"] = True
            else:
                raise AssertionError("execute access loss accepted")
            path.chmod(0)
            try:
                digest.sha256_file(path)
            except PermissionError as error:
                assert error.errno == errno.EACCES
                records["actual_read_access_loss_rejected"] = True
            else:
                records["actual_read_access_loss_rejected"] = False
                assert os.geteuid() == 0, "read denial unexpectedly bypassed"
            finally:
                path.chmod(0o600)
        records["observation_cache_size"] = digest._observed_at.cache_info().currsize
        records["digest_cache_size"] = digest._digest.cache_info().currsize
        assert records["observation_cache_size"] <= 512
        assert records["digest_cache_size"] <= 512
    print(json.dumps(records, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
