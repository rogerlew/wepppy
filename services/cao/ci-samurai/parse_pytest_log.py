#!/usr/bin/env python3
"""
Parse pytest text output and emit JSONL of failing tests.

Heuristics:
- Look for summary lines like:
  "FAILED tests/path/test_file.py::test_name - AssertionError: ..."
  "ERROR  tests/path/test_file.py::test_name - FileNotFoundError: ..."
- Deduplicate while preserving order.

Usage:
  python parse_pytest_log.py /path/to/triage_nodb.txt > failures.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable


# ANSI escape removal
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

# Matches pytest summary lines like:
#   FAILED tests/path/test_file.py::test_name - AssertionError: ...
#   ERROR  tests/path/test_file.py::test_name - FileNotFoundError: ...
SUMMARY_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+::\S+)(?:\s+-\s+(.*))?$")

# Matches in-line progress lines like:
#   tests/path/test_file.py::test_name FAILED
#   tests/path/test_file.py::test_name ERROR
PROGRESS_RE = re.compile(r"^(\S+::\S+)\s+(FAILED|ERROR)\b(?:\s+-\s+(.*))?$")

# Matches collection error lines in short test summary like:
#   ERROR services/cao/test/test_flow_service.py
#   ERROR wepppy/climates/cligen/tests/geojson_export_test.py - sqlite3.DatabaseE...
COLLECTION_ERROR_RE = re.compile(r"^ERROR\s+([^:]+\.py)(?:\s+-\s+(.*))?$")


def _strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def iter_failures(lines: Iterable[str]):
    seen = set()
    for raw in lines:
        line = _strip_ansi(raw.rstrip("\n"))
        
        # Try test failure/error with nodeid first
        m = SUMMARY_RE.match(line)
        if m:
            kind, nodeid, tail = m.groups()
        else:
            m2 = PROGRESS_RE.match(line)
            if m2:
                nodeid, kind, tail = m2.groups()
            else:
                # Try collection error (file-level)
                m3 = COLLECTION_ERROR_RE.match(line)
                if m3:
                    file_path, tail = m3.groups()
                    # Convert file path to synthetic nodeid for consistency
                    nodeid = f"{file_path}::collection_error"
                    kind = "ERROR"
                else:
                    continue
        
        if nodeid in seen:
            continue
        seen.add(nodeid)
        yield {
            "kind": kind.lower(),
            "test": nodeid,
            "error": (tail or "").strip(),
        }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: parse_pytest_log.py <logfile>", file=sys.stderr)
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"Log file not found: {p}", file=sys.stderr)
        return 2
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        for item in iter_failures(f):
            print(json.dumps(item, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
