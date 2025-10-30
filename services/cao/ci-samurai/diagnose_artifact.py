#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import os
import re
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple


SUMMARY_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+::\S+)(?:\s+-\s+(.*))?$")


def iter_failures(lines: Iterable[str]) -> List[Tuple[str, str, str]]:
    seen = set()
    out: List[Tuple[str, str, str]] = []
    for raw in lines:
        line = raw.rstrip("\n")
        m = SUMMARY_RE.match(line)
        if not m:
            continue
        kind, nodeid, tail = m.groups()
        if nodeid in seen:
            continue
        seen.add(nodeid)
        out.append((kind.lower(), nodeid, (tail or "").strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose a ci-samurai logs artifact (tgz or directory)")
    ap.add_argument("artifact", help="Path to ci-samurai-logs.tgz or extracted directory")
    args = ap.parse_args()

    path = Path(args.artifact)
    workdir: Path
    cleanup = False
    if path.is_dir():
        workdir = path
    else:
        tmp = Path(tempfile.mkdtemp(prefix="ci-samurai-logs-"))
        with tarfile.open(path, "r:gz") as tf:
            tf.extractall(tmp)
        workdir = tmp
        cleanup = True

    try:
        triages = list(workdir.rglob("triage_*.txt"))
        print(f"Found {len(triages)} triage files")
        for p in triages:
            print(f" - {p}")
        triage_nodb = next((p for p in triages if p.name == "triage_nodb.txt"), None)
        if triage_nodb and triage_nodb.exists():
            print(f"\ntriage_nodb.txt head (20 lines): {triage_nodb}")
            try:
                print("".join(triage_nodb.read_text(encoding="utf-8", errors="ignore").splitlines(True)[:20]))
            except Exception:
                pass
            fails = iter_failures(triage_nodb.read_text(encoding="utf-8", errors="ignore").splitlines())
            print(f"Parsed failures: {len(fails)}")
            for i, (kind, nodeid, msg) in enumerate(fails[:10], 1):
                print(f"  {i:02d}. {kind.upper()} {nodeid} - {msg}")
        else:
            print("No triage_nodb.txt found in artifact")

        first_fail = next(workdir.rglob("first_fail.txt"), None)
        if first_fail and first_fail.exists():
            print("\nfirst_fail.txt:")
            print(first_fail.read_text(encoding="utf-8", errors="ignore").strip())

        validate_first = next(workdir.rglob("validate_first.txt"), None)
        if validate_first and validate_first.exists():
            print("\nvalidate_first.txt tail (20 lines):")
            lines = validate_first.read_text(encoding="utf-8", errors="ignore").splitlines()
            print("\n".join(lines[-20:]))

        flake_loop = next(workdir.rglob("flake_loop.txt"), None)
        if flake_loop and flake_loop.exists():
            print("\nflake_loop.txt tail (40 lines):")
            lines = flake_loop.read_text(encoding="utf-8", errors="ignore").splitlines()
            print("\n".join(lines[-40:]))

    finally:
        if cleanup:
            try:
                # Best effort cleanup of extracted temp dir
                for root, dirs, files in os.walk(workdir, topdown=False):
                    for name in files:
                        Path(root, name).unlink(missing_ok=True)
                    for name in dirs:
                        Path(root, name).rmdir()
                workdir.rmdir()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

