#!/usr/bin/env python3
"""Small-file NFS microbench helpers (metadata-heavy).

This intentionally benchmarks "lots of little files" (create/stat/read/unlink),
which tends to correlate with UI lag when run trees are NFS-backed.

Run phases separately so host-side tools (e.g., nfsiostat) can be wrapped
around each phase for per-op latency capture.
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchConfig:
    root: Path
    files: int
    file_size: int
    seed: int


def _file_paths(cfg: BenchConfig) -> list[Path]:
    return [cfg.root / f"f{i:05d}.bin" for i in range(cfg.files)]


def _time_call(fn, *args, **kwargs) -> float:
    start = time.perf_counter()
    fn(*args, **kwargs)
    return time.perf_counter() - start


def phase_write(cfg: BenchConfig) -> None:
    cfg.root.mkdir(parents=True, exist_ok=True)
    payload = b"x" * cfg.file_size
    for p in _file_paths(cfg):
        with open(p, "wb", buffering=0) as fp:
            fp.write(payload)


def phase_listdir(cfg: BenchConfig) -> int:
    # Return count to discourage accidental optimization.
    return len(os.listdir(cfg.root))


def phase_stat_seq(cfg: BenchConfig) -> int:
    total = 0
    for p in _file_paths(cfg):
        total += os.stat(p).st_size
    return total


def phase_read(cfg: BenchConfig) -> int:
    paths = _file_paths(cfg)
    rnd = random.Random(cfg.seed)
    rnd.shuffle(paths)
    total = 0
    for p in paths:
        with open(p, "rb", buffering=0) as fp:
            total += len(fp.read())
    return total


def phase_delete(cfg: BenchConfig) -> None:
    shutil.rmtree(cfg.root)


def phase_concurrent_stat(cfg: BenchConfig, *, threads: int, repeats: int) -> None:
    paths = _file_paths(cfg)

    def _one_round() -> float:
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=threads) as ex:
            # os.stat releases the GIL; this can actually drive concurrency.
            list(ex.map(os.stat, paths, chunksize=256))
        return time.perf_counter() - start

    for i in range(repeats):
        dt = _one_round()
        ops_s = cfg.files / dt if dt else float("inf")
        print(
            f"concurrent_stat repeat={i+1}/{repeats} threads={threads} "
            f"seconds={dt:.6f} ops_s={ops_s:.1f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Small-file metadata microbench phases.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", required=True, help="Benchmark directory (created/removed).")
        p.add_argument("--files", type=int, default=2000)
        p.add_argument("--file-size", type=int, default=4096)
        p.add_argument("--seed", type=int, default=12345, help="Shuffle seed for read phase.")

    p_write = sub.add_parser("write", help="Create+write all files.")
    add_common(p_write)

    p_list = sub.add_parser("listdir", help="List the directory once.")
    add_common(p_list)
    p_list.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the operation N times (useful to stretch interval tools like nfsiostat).",
    )

    p_stat = sub.add_parser("stat-seq", help="Sequential stat() across all files.")
    add_common(p_stat)
    p_stat.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the operation N times (useful to stretch interval tools like nfsiostat).",
    )

    p_read = sub.add_parser("read", help="Read all files (shuffled order).")
    add_common(p_read)

    p_del = sub.add_parser("delete", help="Delete the benchmark directory tree.")
    add_common(p_del)

    p_cstat = sub.add_parser("concurrent-stat", help="Concurrent stat() across all files.")
    add_common(p_cstat)
    p_cstat.add_argument("--threads", type=int, required=True)
    p_cstat.add_argument("--repeats", type=int, default=3)

    args = parser.parse_args()
    cfg = BenchConfig(
        root=Path(args.root),
        files=int(args.files),
        file_size=int(args.file_size),
        seed=int(args.seed),
    )

    if args.cmd == "write":
        dt = _time_call(phase_write, cfg)
        print(f"write seconds={dt:.6f} files={cfg.files} file_size={cfg.file_size}")
        return 0
    if args.cmd == "listdir":
        start = time.perf_counter()
        n = 0
        for _ in range(int(args.repeat)):
            n = phase_listdir(cfg)
        dt = time.perf_counter() - start
        print(f"listdir seconds={dt:.6f} entries={n} repeat={int(args.repeat)}")
        return 0
    if args.cmd == "stat-seq":
        start = time.perf_counter()
        total = 0
        for _ in range(int(args.repeat)):
            total = phase_stat_seq(cfg)
        dt = time.perf_counter() - start
        # Report per-file ops/s, across all repeats.
        ops_s = (cfg.files * int(args.repeat)) / dt if dt else float("inf")
        print(
            f"stat_seq seconds={dt:.6f} ops_s={ops_s:.1f} "
            f"total_bytes={total} repeat={int(args.repeat)}"
        )
        return 0
    if args.cmd == "read":
        start = time.perf_counter()
        total = phase_read(cfg)
        dt = time.perf_counter() - start
        mib = total / (1024 * 1024)
        mib_s = mib / dt if dt else float("inf")
        print(f"read seconds={dt:.6f} mib_s={mib_s:.3f} total_bytes={total}")
        return 0
    if args.cmd == "delete":
        dt = _time_call(phase_delete, cfg)
        print(f"delete seconds={dt:.6f}")
        return 0
    if args.cmd == "concurrent-stat":
        phase_concurrent_stat(cfg, threads=int(args.threads), repeats=int(args.repeats))
        return 0

    raise AssertionError(f"Unhandled cmd: {args.cmd}")


if __name__ == "__main__":
    sys.exit(main())
