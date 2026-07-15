#!/usr/bin/env python3
"""Capture or compare protected AgFields routing-suite input trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pyarrow as pa
import pyarrow.parquet as pq


ROOTS = (
    ("baseline_runs", Path("wepp/runs")),
    ("baseline_output", Path("wepp/output")),
    ("ag_fields_inputs", Path("ag_fields")),
    ("ag_fields_runs", Path("wepp/ag_fields/runs")),
    ("ag_fields_output", Path("wepp/ag_fields/output")),
    ("legacy_concept2_runs", Path("wepp/ag_fields/watershed/runs")),
    ("legacy_concept2_output", Path("wepp/ag_fields/watershed/output")),
    ("legacy_concept2_manifest", Path("wepp/ag_fields/watershed/manifest")),
)
SCHEMA = pa.schema(
    [
        ("tree", pa.string()),
        ("relative_path", pa.string()),
        ("size_bytes", pa.int64()),
        ("sha256", pa.string()),
    ],
    metadata={b"purpose": b"ag_fields_routing_suite_protected_inventory_v1"},
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> Iterator[Path]:
    pending = [root]
    while pending:
        directory = pending.pop()
        entries = sorted(
            os.scandir(directory),
            key=lambda entry: entry.name,
            reverse=True,
        )
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                raise RuntimeError(f"Protected inventory contains a symlink: {path}")
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                yield path
            else:
                raise RuntimeError(f"Unsupported protected inventory entry: {path}")


def capture(run_root: Path, output: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    tree_counts: dict[str, int] = {}
    tree_bytes: dict[str, int] = {}
    inventory_digest = hashlib.sha256()
    for tree, relative_root in ROOTS:
        root = run_root / relative_root
        if not root.is_dir():
            raise FileNotFoundError(f"Missing protected tree: {relative_root}")
        tree_counts[tree] = 0
        tree_bytes[tree] = 0
        for path in _files(root):
            relative_path = path.relative_to(root).as_posix()
            size_bytes = path.stat().st_size
            sha256 = _sha256(path)
            rows.append(
                {
                    "tree": tree,
                    "relative_path": relative_path,
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                }
            )
            tree_counts[tree] += 1
            tree_bytes[tree] += size_bytes
            inventory_digest.update(
                f"{tree}\0{relative_path}\0{size_bytes}\0{sha256}\n".encode()
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        table = pa.Table.from_pylist(rows, schema=SCHEMA)
        pq.write_table(table, temporary, compression="zstd")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "schema_version": "1.0",
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runid": run_root.name,
        "roots": {tree: relative.as_posix() for tree, relative in ROOTS},
        "tree_file_counts": tree_counts,
        "tree_bytes": tree_bytes,
        "file_count": len(rows),
        "size_bytes": sum(tree_bytes.values()),
        "inventory_sha256": inventory_digest.hexdigest(),
    }


def compare(expected_path: Path, observed_path: Path) -> dict[str, object]:
    columns = ["tree", "relative_path", "size_bytes", "sha256"]
    expected = {
        (row["tree"], row["relative_path"]): (row["size_bytes"], row["sha256"])
        for row in pq.read_table(expected_path, columns=columns).to_pylist()
    }
    observed = {
        (row["tree"], row["relative_path"]): (row["size_bytes"], row["sha256"])
        for row in pq.read_table(observed_path, columns=columns).to_pylist()
    }
    missing = sorted(expected.keys() - observed.keys())
    added = sorted(observed.keys() - expected.keys())
    changed = sorted(
        key
        for key in expected.keys() & observed.keys()
        if expected[key] != observed[key]
    )
    return {
        "identical": not missing and not added and not changed,
        "expected_file_count": len(expected),
        "observed_file_count": len(observed),
        "missing_count": len(missing),
        "added_count": len(added),
        "changed_count": len(changed),
        "sample_missing": [f"{tree}/{path}" for tree, path in missing[:20]],
        "sample_added": [f"{tree}/{path}" for tree, path in added[:20]],
        "sample_changed": [f"{tree}/{path}" for tree, path in changed[:20]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("EXPECTED", "OBSERVED"),
    )
    args = parser.parse_args()
    if args.compare:
        result = compare(*args.compare)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["identical"] else 1
    if args.run_root is None or args.output is None:
        parser.error("--run-root and --output are required for capture")
    result = capture(args.run_root.resolve(), args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
