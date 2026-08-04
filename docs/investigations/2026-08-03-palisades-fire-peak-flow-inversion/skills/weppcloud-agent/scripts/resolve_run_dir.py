#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _env_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value)


def resolve_batch_run_root(batch_root: Path, batch_name: str, runid: str) -> Path | None:
    batch_dir = batch_root / batch_name
    if not batch_dir.is_dir():
        return None
    if runid == "_base":
        return batch_dir / "_base"
    return batch_dir / "runs" / runid


def resolve_run_root(
    runid: str,
    *,
    primary_run_root: Path,
    partitioned_run_root: Path,
    batch_root: Path,
) -> Path | None:
    if ";;" in runid:
        tokens = runid.split(";;")
        if len(tokens) == 3 and tokens[0] == "batch":
            return resolve_batch_run_root(batch_root, tokens[1], tokens[2])
        return None

    primary_path = primary_run_root / runid
    if primary_path.is_dir():
        return primary_path

    prefix = runid[:2] if len(runid) >= 2 else runid
    partitioned_path = partitioned_run_root / prefix / runid
    if partitioned_path.is_dir():
        return partitioned_path

    return None


def resolve_run_dir(
    runid: str,
    *,
    config: str | None,
    pup: str | None,
    primary_run_root: Path,
    partitioned_run_root: Path,
    batch_root: Path,
) -> Path | None:
    root = resolve_run_root(
        runid,
        primary_run_root=primary_run_root,
        partitioned_run_root=partitioned_run_root,
        batch_root=batch_root,
    )
    if root is None:
        return None

    if pup:
        pups_root = root / "_pups"
        if not pups_root.is_dir():
            return None
        candidate = (pups_root / pup).resolve()
        pups_root_norm = pups_root.resolve()
        if not (candidate == pups_root_norm or str(candidate).startswith(str(pups_root_norm) + os.sep)):
            return None
        if candidate.is_dir():
            return candidate
        return None

    if config:
        candidate = root / config
        if candidate.is_dir():
            return candidate

    if root.is_dir():
        return root
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a WEPPcloud run directory (runid + optional config/pup) using the same root heuristics as WEPPcloudR.",
    )
    parser.add_argument("runid", help="Run identifier (folder name). Batch form: batch;;<batch_name>;;<runid>.")
    parser.add_argument("--config", help="Config directory under the run root (optional).")
    parser.add_argument("--pup", help="Pup directory under <run_root>/_pups/<pup> (optional).")
    parser.add_argument(
        "--primary-run-root",
        default=os.environ.get("PRIMARY_RUN_ROOT", "/geodata/weppcloud_runs"),
        help="Primary run root (default: env PRIMARY_RUN_ROOT or /geodata/weppcloud_runs).",
    )
    parser.add_argument(
        "--partitioned-run-root",
        default=os.environ.get("PARTITIONED_RUN_ROOT", "/wc1/runs"),
        help="Partitioned run root (default: env PARTITIONED_RUN_ROOT or /wc1/runs).",
    )
    parser.add_argument(
        "--batch-root",
        default=os.environ.get("BATCH_ROOT", "/wc1/batch"),
        help="Batch root (default: env BATCH_ROOT or /wc1/batch).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    primary_run_root = Path(args.primary_run_root)
    partitioned_run_root = Path(args.partitioned_run_root)
    batch_root = Path(args.batch_root)

    run_root = resolve_run_root(
        args.runid,
        primary_run_root=primary_run_root,
        partitioned_run_root=partitioned_run_root,
        batch_root=batch_root,
    )
    run_dir = resolve_run_dir(
        args.runid,
        config=args.config,
        pup=args.pup,
        primary_run_root=primary_run_root,
        partitioned_run_root=partitioned_run_root,
        batch_root=batch_root,
    )

    if args.json:
        payload = {
            "runid": args.runid,
            "config": args.config,
            "pup": args.pup,
            "primary_run_root": str(primary_run_root),
            "partitioned_run_root": str(partitioned_run_root),
            "batch_root": str(batch_root),
            "run_root": str(run_root) if run_root else None,
            "run_dir": str(run_dir) if run_dir else None,
            "run_root_exists": bool(run_root and run_root.is_dir()),
            "run_dir_exists": bool(run_dir and run_dir.is_dir()),
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0 if run_dir else 2

    if run_root:
        sys.stdout.write(f"run_root: {run_root}\n")
    else:
        sys.stdout.write("run_root: (not found)\n")

    if run_dir:
        sys.stdout.write(f"run_dir:  {run_dir}\n")
        return 0

    sys.stdout.write("run_dir:  (not found)\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
