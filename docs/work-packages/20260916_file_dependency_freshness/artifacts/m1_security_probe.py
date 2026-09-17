"""Disposable discovery probe; does not change runtime code or named runs.

Run: wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/m1_security_probe.py
The subclass replaces decoding only to schedule an actual filesystem replace
after read_text has returned. Both NoDb hydration methods remain unmodified.
"""
import json
import os
from pathlib import Path
import tempfile

from wepppy.nodb import base


class Probe(base.NoDbBase):
    filename = "probe.nodb"
    replacement = None

    def _init_logging(self):
        pass

    @classmethod
    def _decode_jsonpickle(cls, text):
        value = json.loads(text)
        if cls.replacement is not None:
            source, target = cls.replacement
            os.replace(source, target)
            cls.replacement = None
        instance = cls.__new__(cls)
        instance.wd = value["wd"]
        instance.value = value["value"]
        return instance


def run():
    # Isolate the probe from every Redis read/write; no lock or dump is invoked.
    base.redis_nodb_cache_client = None
    results = []
    with tempfile.TemporaryDirectory(prefix="freshness-security-") as directory:
        root = Path(directory)
        (root / "READONLY").touch()  # Skip version migration in detached loader.
        target = root / Probe.filename
        replacement = root / "replacement.nodb"
        for loader in ("hydrate", "detached"):
            target.write_text(json.dumps({"wd": directory, "value": "A"}))
            replacement.write_text(json.dumps({"wd": directory, "value": "B"}))
            # Ensure this probe does not depend on timestamp resolution.
            changed_ns = target.stat().st_mtime_ns + 2_000_000_000
            os.utime(replacement, ns=(changed_ns, changed_ns))
            Probe.replacement = (replacement, target)
            if loader == "hydrate":
                observed = Probe._hydrate_instance(directory, False, False, True, use_redis_cache=False)
            else:
                observed = Probe.load_detached(directory)
            matches, _ = Probe._cache_instance_matches_file_signature(instance=observed, filepath=str(target))
            results.append({"loader": loader, "loaded_value": observed.value,
                            "disk_value": json.loads(target.read_text())["value"],
                            "stale_payload_matches_current_signature": matches})
    print(json.dumps(results, indent=2))
    assert all(item["loaded_value"] == "A" and item["disk_value"] == "B"
               and item["stale_payload_matches_current_signature"] for item in results)


if __name__ == "__main__":
    run()
