"""Real filesystem proof that ns-valued ctime may collide across rapid writes.

Run with wctl exec weppcloud python <this path>. Only disposable files change.
No mocked metadata, clocks, file opens, or hash implementation are used.
"""
import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path

from wepppy.nodb.mods.postfire_debris_flow import production as p


def main():
    answer = []
    for parent in ("/tmp", "/workdir/wepppy", "/wc1/runs"):
        with tempfile.TemporaryDirectory(prefix="freshness-ctime-probe-", dir=parent) as directory:
            source = Path(directory) / "source"
            collisions = stale = 0
            sample = None
            for iteration in range(1000):
                source.write_bytes(b"before")
                p.cached_digest(source, local=True)
                before = source.stat()
                source.write_bytes(b"AFTER!")
                os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
                after = source.stat()
                if p._file_version(before) == p._file_version(after):
                    collisions += 1
                    actual = p.cached_digest(source, local=True)
                    expected = sha256(source.read_bytes()).hexdigest()
                    if actual != expected:
                        stale += 1
                        sample = {
                            "iteration": iteration,
                            "version": p._file_version(before),
                            "actual_digest": actual,
                            "expected_digest": expected,
                        }
                        break
            answer.append({
                "filesystem_parent": parent,
                "identical_versions": collisions,
                "stale_cache_hits": stale,
                "sample": sample,
            })
    print(json.dumps(answer, indent=2))


if __name__ == "__main__":
    main()
