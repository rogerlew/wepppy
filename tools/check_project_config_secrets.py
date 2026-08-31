#!/usr/bin/env python3
"""Reject secret-bearing or runtime-host-bound project configuration artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wepppy.project_config_sanitization import scan_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("wepppy/nodb/configs")],
        help="Config source, project directory, manifest, or ZIP/tar archive",
    )
    args = parser.parse_args()

    violations = [violation for path in args.paths for violation in scan_path(path)]
    for violation in violations:
        print(violation.describe())
    if violations:
        print(f"project-config sanitization failed: {len(violations)} violation(s)")
        return 1
    print(f"project-config sanitization passed: {len(args.paths)} path(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
