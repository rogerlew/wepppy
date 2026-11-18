#!/usr/bin/env python3
"""Audit or recover stale vector-upload retention reservations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wepppy.microservices.vector_upload_normalization import reconcile_retention


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit stale vector upload evidence; pass --apply to terminalize and reconcile it.",
    )
    parser.add_argument("--filesystem-root", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--rebuild-ledger",
        action="store_true",
        help="Audit retained receipts and, with --apply, rebuild Redis committed-byte totals.",
    )
    parser.add_argument("--stale-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.stale_seconds < 60:
        parser.error("--stale-seconds must be at least 60")
    report = reconcile_retention(
        args.filesystem_root,
        apply=args.apply,
        stale_seconds=args.stale_seconds,
        rebuild_ledger=args.rebuild_ledger,
    )
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
