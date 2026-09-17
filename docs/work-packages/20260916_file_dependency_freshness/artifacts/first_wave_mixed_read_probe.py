"""Bounded multi-chunk read probe; real files and stat values, controlled writer.

The hash-update hook overwrites the entire 2 MiB file after the first 1 MiB read.
An undetected read would contain old prefix + new suffix, a hybrid generation.
"""
import json
import tempfile
from pathlib import Path

from wepppy.nodb.mods.postfire_debris_flow import production as p


def main():
    real_sha256 = p.hashlib.sha256
    chunk = 1024 * 1024
    old, new = b"A" * (2 * chunk), b"B" * (2 * chunk)
    expected = {
        name: real_sha256(data).hexdigest()
        for name, data in (("old", old), ("new", new), ("mixed", old[:chunk] + new[chunk:]))
    }
    results = []
    for parent in ("/tmp", "/workdir/wepppy"):
        detected = returned = 0
        sample = None
        with tempfile.TemporaryDirectory(prefix="freshness-mixed-probe-", dir=parent) as directory:
            path = Path(directory) / "source"
            for attempt in range(150):
                path.write_bytes(old)
                version = p._file_version(path.stat())

                def changing_hash():
                    checksum = real_sha256()

                    class ChangingHash:
                        blocks = 0

                        def update(self, block):
                            checksum.update(block)
                            self.blocks += 1
                            if self.blocks == 1:
                                path.write_bytes(new)

                        def hexdigest(self):
                            return checksum.hexdigest()

                    return ChangingHash()

                p.hashlib.sha256 = changing_hash
                try:
                    actual = p.cached_digest(path, local=True)
                except p.WorkflowError:
                    detected += 1
                else:
                    returned += 1
                    sample = {
                        "attempt": attempt,
                        "version_equal": version == p._file_version(path.stat()),
                        "result": actual,
                        "is_mixed": actual == expected["mixed"],
                        "matches_current": actual == expected["new"],
                    }
                    if sample["is_mixed"]:
                        break
                finally:
                    p.hashlib.sha256 = real_sha256
        results.append({"parent": parent, "detected": detected, "returned": returned, "sample": sample})
    print(json.dumps({"expected": expected, "results": results}, indent=2))


if __name__ == "__main__":
    main()
