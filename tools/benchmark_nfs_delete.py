#!/usr/bin/env python3
"""Benchmark delete latency for large directory trees.

This script creates a directory tree with many small files, then measures how
long it takes to delete the tree. Use it to compare /geodata (NFS) versus a
local filesystem like /ssd1 or /tmp.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BenchResult:
    root: Path
    files: int
    dirs: int
    bytes_written: int
    create_seconds: float
    delete_seconds: float
    rewrite_seconds: float
    flush_seconds: float


def _iter_dirs(root: Path, width: int, depth: int) -> Iterable[Path]:
    yield root
    if depth <= 0:
        return
    for d in range(width):
        child = root / f"d{d}"
        yield child
        yield from _iter_dirs(child, width, depth - 1)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _populate_tree(
    root: Path,
    files_per_dir: int,
    file_size: int,
    dir_width: int,
    dir_depth: int,
    *,
    fsync_files: bool,
    fsync_dirs: bool,
) -> int:
    total_bytes = 0
    payload = b"x" * file_size
    dirs: list[Path] = []
    for dpath in _iter_dirs(root, dir_width, dir_depth):
        dpath.mkdir(parents=True, exist_ok=True)
        dirs.append(dpath)
        for i in range(files_per_dir):
            fpath = dpath / f"f{i}.bin"
            with open(fpath, "wb") as fp:
                fp.write(payload)
                if fsync_files:
                    fp.flush()
                    os.fsync(fp.fileno())
            total_bytes += file_size
    if fsync_dirs:
        for dpath in dirs:
            _fsync_dir(dpath)
    return total_bytes


def _count_tree(root: Path) -> tuple[int, int]:
    dirs = 0
    files = 0
    for _, dirnames, filenames in os.walk(root):
        dirs += len(dirnames)
        files += len(filenames)
    return files, dirs


def _time_call(fn, *args, **kwargs) -> float:
    start = time.perf_counter()
    fn(*args, **kwargs)
    return time.perf_counter() - start


def run_benchmark(
    root: Path,
    *,
    files_per_dir: int,
    file_size: int,
    dir_width: int,
    dir_depth: int,
    fsync_files: bool,
    fsync_dirs: bool,
    sync_after_rewrite: bool,
    keep: bool,
) -> BenchResult:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    create_seconds = _time_call(
        _populate_tree,
        root,
        files_per_dir,
        file_size,
        dir_width,
        dir_depth,
        fsync_files=False,
        fsync_dirs=False,
    )
    files, dirs = _count_tree(root)

    delete_seconds = _time_call(shutil.rmtree, root)
    root.mkdir(parents=True, exist_ok=True)

    rewrite_seconds = _time_call(
        _populate_tree,
        root,
        files_per_dir,
        file_size,
        dir_width,
        dir_depth,
        fsync_files=fsync_files,
        fsync_dirs=fsync_dirs,
    )
    flush_seconds = 0.0
    if sync_after_rewrite:
        flush_seconds = _time_call(os.sync)

    if keep:
        shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
    else:
        shutil.rmtree(root)

    return BenchResult(
        root=root,
        files=files,
        dirs=dirs,
        bytes_written=files * file_size,
        create_seconds=create_seconds,
        delete_seconds=delete_seconds,
        rewrite_seconds=rewrite_seconds,
        flush_seconds=flush_seconds,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark delete latency for directory trees."
    )
    parser.add_argument(
        "roots",
        nargs="+",
        help="One or more root directories to benchmark (will be created/removed).",
    )
    parser.add_argument("--files-per-dir", type=int, default=100)
    parser.add_argument("--file-size", type=int, default=4096)
    parser.add_argument("--dir-width", type=int, default=5)
    parser.add_argument("--dir-depth", type=int, default=2)
    parser.add_argument("--fsync-files", action="store_true", help="fsync each file after write.")
    parser.add_argument("--fsync-dirs", action="store_true", help="fsync each directory after write.")
    parser.add_argument("--sync", action="store_true", help="call os.sync after rewrite.")
    parser.add_argument("--keep", action="store_true", help="Recreate empty root after delete.")
    args = parser.parse_args()

    results: list[BenchResult] = []
    for root_str in args.roots:
        root = Path(root_str).resolve()
        results.append(
            run_benchmark(
                root,
                files_per_dir=args.files_per_dir,
                file_size=args.file_size,
                dir_width=args.dir_width,
                dir_depth=args.dir_depth,
                fsync_files=args.fsync_files,
                fsync_dirs=args.fsync_dirs,
                sync_after_rewrite=args.sync,
                keep=args.keep,
            )
        )

    print("delete_benchmark_results")
    for result in results:
        mb = result.bytes_written / (1024 * 1024)
        print(
            f"- root={result.root} files={result.files} dirs={result.dirs} "
            f"size_mb={mb:.2f} create_s={result.create_seconds:.3f} "
            f"delete_s={result.delete_seconds:.3f} "
            f"rewrite_s={result.rewrite_seconds:.3f} "
            f"sync_s={result.flush_seconds:.3f}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
