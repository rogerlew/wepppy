#!/usr/bin/env python3
"""Read-only metadata and full-read probe for WA-117 interchange inputs."""

import argparse
import json
import os
import random
import resource
import time
from pathlib import Path

FAMILIES = ("pass", "ebe", "element", "loss", "soil", "wat")


def timed(name, operation):
    before = resource.getrusage(resource.RUSAGE_SELF)
    started = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_SELF)
    return {"phase": name, "wall_seconds": elapsed,
            "user_seconds": after.ru_utime - before.ru_utime,
            "system_seconds": after.ru_stime - before.ru_stime, **result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--label", required=True)
    parser.add_argument("--read-repeats", type=int, default=2)
    parser.add_argument("--chunk-mib", type=int, default=1)
    args = parser.parse_args()
    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"missing root: {root}")
    report = {"schema_version": 1, "label": args.label, "root": str(root),
              "hostname": os.uname().nodename, "started_epoch": time.time(),
              "families": {}, "phases": []}
    paths = []
    for family in FAMILIES:
        found = sorted(root.glob(f"H*.{family}.dat"))
        report["families"][family] = {"files": len(found)}
        paths.extend(found)
    report["files"] = len(paths)

    def do_stat():
        sizes = {family: 0 for family in FAMILIES}
        for path in paths:
            sizes[path.name.rsplit(".", 2)[1]] += path.stat().st_size
        return {"files": len(paths), "bytes": sum(sizes.values()),
                "family_bytes": sizes}

    report["phases"].append(timed("stat_all", do_stat))
    report["phases"].append(timed("open_close_all", lambda: (
        [path.open("rb").close() for path in paths] and {"files": len(paths)})))
    chunk = args.chunk_mib * 1024 * 1024
    for repeat in range(1, args.read_repeats + 1):
        ordered = list(paths)
        random.Random(117 + repeat).shuffle(ordered)

        def do_read():
            total = 0
            for path in ordered:
                with path.open("rb", buffering=0) as stream:
                    while data := stream.read(chunk):
                        total += len(data)
            return {"files": len(ordered), "bytes": total}

        report["phases"].append(timed(f"read_all_{repeat}", do_read))
    report["ended_epoch"] = time.time()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
