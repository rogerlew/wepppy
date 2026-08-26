#!/usr/bin/env python3
"""Fail when Git LFS pointer files remain in a checkout or build tree."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable


LFS_POINTER_HEADER = b"version https://git-lfs.github.com/spec/v1\n"


def is_lfs_pointer(path: Path) -> bool:
    """Return whether *path* begins with the canonical Git LFS pointer header."""
    try:
        with path.open("rb") as stream:
            return stream.read(len(LFS_POINTER_HEADER)) == LFS_POINTER_HEADER
    except (OSError, PermissionError):
        return False


def tracked_lfs_paths(repository: Path) -> list[Path]:
    """Return paths tracked by Git LFS at the repository's current revision."""
    result = subprocess.run(
        ["git", "lfs", "ls-files", "--name-only"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return [repository / line for line in result.stdout.splitlines() if line]


def scanned_paths(root: Path, excluded_names: set[str]) -> Iterable[Path]:
    """Yield regular files below *root*, pruning excluded directory names."""
    for directory, directory_names, file_names in os.walk(root):
        directory_names[:] = [name for name in directory_names if name not in excluded_names]
        base = Path(directory)
        for name in file_names:
            path = base / name
            if path.is_file() and not path.is_symlink():
                yield path


def verify(paths: Iterable[Path]) -> tuple[int, list[Path]]:
    """Return the number checked and any paths that remain LFS pointers."""
    checked = 0
    pointers: list[Path] = []
    for path in paths:
        checked += 1
        if not path.is_file():
            pointers.append(path)
        elif is_lfs_pointer(path):
            pointers.append(path)
    return checked, pointers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--tracked",
        action="store_true",
        help="verify every path reported by git lfs ls-files",
    )
    mode.add_argument(
        "--scan-root",
        type=Path,
        help="scan a copied source or image tree without requiring Git metadata",
    )
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
        help="repository used by --tracked (default: current directory)",
    )
    parser.add_argument(
        "--exclude-name",
        action="append",
        default=[".git"],
        help="directory name pruned by --scan-root (repeatable; default: .git)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = args.repository.resolve()
    if args.tracked:
        paths = tracked_lfs_paths(repository)
        display_root = repository
        mode = "tracked Git LFS files"
    else:
        display_root = args.scan_root.resolve()
        paths = scanned_paths(display_root, set(args.exclude_name))
        mode = "files in copied tree"

    checked, pointers = verify(paths)
    if pointers:
        print(
            f"ERROR: {len(pointers)} unmaterialized or missing Git LFS file(s) "
            f"found among {checked} {mode}:",
            file=sys.stderr,
        )
        for path in pointers:
            try:
                rendered = path.relative_to(display_root)
            except ValueError:
                rendered = path
            print(f"- {rendered}", file=sys.stderr)
        return 1

    print(f"Git LFS verification passed: {checked} {mode} are materialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
