#!/usr/bin/env python3
"""Verify and stage the pinned Gate 2.1 observer source for an isolated build."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "e4179702478561206d3024f00cacd57245d92e5b168862ac5cea801aa04538ad"


def instrument(source: str) -> str:
    """Return the already-instrumented source only when it is the pinned file."""
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    if source_hash != SOURCE_SHA256:
        raise ValueError(f"unexpected Gate 2.1 irs.for SHA-256: {source_hash}")
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    args.destination.write_text(instrument(args.source.read_text()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
