#!/usr/bin/env python3
"""Require catalog-readable dates on every numbered Architecture Decision Record."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from wepppy.weppcloud.usersum_docs.adr_catalog import read_adr, resolve_adr


def check_dates(repo_root: Path) -> int:
    directory = repo_root / 'docs' / 'adrs'
    if directory.is_symlink() or not directory.is_dir():
        print(f'ERROR: {directory}: expected a regular ADR directory.', file=sys.stderr)
        return 1

    checked = 0
    failed = 0
    for candidate in sorted(directory.iterdir()):
        path = resolve_adr(repo_root, candidate.name)
        if path is None:
            continue
        checked += 1
        try:
            record = read_adr(path)
        except (OSError, UnicodeError) as exc:
            # CLI diagnostic boundary: report each unreadable source and fail the gate.
            print(f'ERROR: {path}: cannot read ADR: {exc}', file=sys.stderr)
            failed += 1
            continue
        if record.recorded_date is None:
            print(
                f'ERROR: {path}: missing or invalid recorded date. Add a valid '
                'Date: YYYY-MM-DD before the first section heading; use the original '
                'decision date. Review dates and dates only in prose do not qualify.',
                file=sys.stderr,
            )
            failed += 1

    if checked == 0:
        print(f'ERROR: {directory}: no numbered ADR files found.', file=sys.stderr)
        return 1
    if failed:
        print(f'ADR date check failed: {failed} of {checked} ADRs need attention.', file=sys.stderr)
        return 1
    print(f'ADR date check passed: {checked} ADRs have valid recorded dates.')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    try:
        return check_dates(args.repo_root.resolve())
    except OSError as exc:
        # Filesystem enumeration errors must not turn into a successful empty scan.
        print(f'ERROR: cannot inspect {args.repo_root / "docs/adrs"}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
