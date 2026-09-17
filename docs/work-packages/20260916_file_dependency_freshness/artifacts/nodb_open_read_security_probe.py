"""Review-only proof of atomic replacement between actual descriptor stats."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from wepppy.nodb import _read_retry as retry


def run():
    with tempfile.TemporaryDirectory(prefix="nodb-open-read-security-") as directory:
        path, replacement = Path(directory)/"state", Path(directory)/"replacement"
        real_open = open
        for iteration in range(1000):
            path.write_text("old Unicode: café\n")
            replacement.write_text("new Unicode: 東京\n")
            evidence = {}

            class ReplacingReader:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    self.stream.close()

                def fileno(self):
                    return self.stream.fileno()

                def read(self):
                    # read_text_snapshot has already captured its first fstat.
                    before = os.fstat(self.stream.fileno())
                    os.replace(replacement, path)
                    contents = self.stream.read()
                    after = os.fstat(self.stream.fileno())
                    evidence.update(ctime_changed=before.st_ctime_ns != after.st_ctime_ns,
                                    link_counts=[before.st_nlink, after.st_nlink],
                                    old_inode=before.st_ino)
                    return contents

            def wrap(*args, **kwargs):
                return ReplacingReader(real_open(*args, **kwargs))

            with patch.object(retry, "open", wrap, create=True):
                contents, version = retry.read_text_snapshot(str(path))
            assert contents == "old Unicode: café\n"
            assert version.st_ino == evidence["old_inode"]
            assert path.read_text() == "new Unicode: 東京\n"
            if evidence["ctime_changed"]:
                evidence.update(iteration=iteration, old_payload_and_old_version_preserved=True)
                print(json.dumps(evidence, indent=2))
                return
        raise AssertionError("Probe did not observe a ctime transition in bounded iterations")


if __name__ == "__main__":
    run()
