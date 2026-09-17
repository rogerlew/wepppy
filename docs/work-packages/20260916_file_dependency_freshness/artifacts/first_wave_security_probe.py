"""Read-only implementation review probes using disposable real files."""
import asyncio
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from wepppy.microservices.rq_engine import postfire_debris_flow_routes as routes
from wepppy.nodb.mods.postfire_debris_flow import production as p, rainfall_io as io


def run():
    with tempfile.TemporaryDirectory(prefix="freshness-security-download-") as folder:
        root = Path(folder)
        identity = "a" * 32
        results = p.directory(root, identity) / "results"
        results.mkdir(parents=True)
        target = results / "manifest.json"
        target.write_bytes(b"accepted")
        accepted = {"id": identity, "artifacts": {
            str(target.relative_to(root)): p.signature(root, target, strong=True)}}
        open_local = io.open_local
        evidence = {"initial_bytes": target.stat().st_size, "limit_bytes": io.MAX_TEXT,
                    "read_bytes": 0}

        class CountingReader:
            def __init__(self, stream):
                self.stream = stream

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def readinto(self, buffer):
                count = self.stream.readinto(buffer)
                evidence["read_bytes"] += count
                return count

            def read(self, size=-1):
                value = self.stream.read(size)
                evidence["read_bytes"] += len(value)
                return value

        def admit_then_grow(path, limit):
            stream = open_local(path, limit)
            # Model concurrent growth immediately after real descriptor admission.
            with target.open("ab") as outgoing:
                outgoing.write(b"x" * (limit + 1024))
            return CountingReader(stream)

        with patch.object(routes, "context", return_value=folder), \
                patch.object(p, "state_at", return_value={"last_successful_run": accepted}), \
                patch.object(io, "open_local", side_effect=admit_then_grow):
            response = asyncio.run(routes.download("test", "config", identity, "manifest.json", None))
        evidence["response_status"] = response.status_code
        evidence["read_exceeded_limit"] = evidence["read_bytes"] > io.MAX_TEXT
        print(json.dumps(evidence, indent=2))

        target = root / "digest-source"
        target.write_bytes(b"accepted")
        original_open = Path.open
        evidence = {"kind": "cached_digest_growth", "initial_bytes": 8,
                    "read_bytes": 0, "grew": False}

        class GrowingReader:
            def __init__(self, stream):
                self.stream = stream

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def read(self, size=-1):
                if not evidence["grew"]:
                    evidence["grew"] = True
                    with original_open(target, "ab") as outgoing:
                        outgoing.write(b"x" * (3 * 1024 * 1024))
                block = self.stream.read(size)
                evidence["read_bytes"] += len(block)
                return block

        def wrap_read(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return GrowingReader(stream) if path == target and args == ("rb",) else stream

        with patch.object(Path, "open", wrap_read):
            try:
                p.cached_digest(target)
            except p.WorkflowError as error:
                evidence["error_code"] = error.code
        print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    run()
