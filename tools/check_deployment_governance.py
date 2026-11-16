#!/usr/bin/env python3
"""Require clean protected source and exact-source CI evidence before deployment."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from check_security_baseline import GateError, PROTECTED, git, publication


def check(root: Path, repository: str) -> dict:
    candidate = git(root, "rev-parse", "HEAD").decode().strip()
    # --untracked-files=all also rejects newly introduced protected source that
    # has not participated in the accepted commit's governance check.
    dirty = git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", *PROTECTED)
    if dirty:
        raise GateError("Protected deployment source differs from the accepted commit; commit and integrate it first")
    return publication(repository, candidate, os.environ.get("GH_TOKEN", ""), 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        # This entry point belongs to this repository; a configurable repository
        # would permit borrowing another repository's successful check.
        print(json.dumps(check(args.root, "rogerlew/wepppy"), sort_keys=True))
        return 0
    except (GateError, OSError, ValueError, KeyError) as error:
        print(f"DEPLOY_GOVERNANCE_FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
