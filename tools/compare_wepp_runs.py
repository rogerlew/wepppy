"""Compare WEPP run directories (runs/ and output/)."""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


def sha256(path: Path) -> str:
    """Hash a file without loading it all at once."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_sol(path: Path) -> str:
    """Hash a .sol file while ignoring comment lines that start with #."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for raw_line in handle:
            if raw_line.lstrip().startswith(b"#"):
                continue
            hasher.update(raw_line)
    return hasher.hexdigest()


def sha256_slp(path: Path) -> str:
    """Hash a .slp file while ignoring aspect for 2003.3/2023.3 formats."""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except UnicodeDecodeError:
        return sha256(path)

    if lines and lines[0].strip() in {"2003.3", "2023.3"} and len(lines) >= 3:
        parts = lines[2].split()
        if len(parts) >= 3:
            # Drop the aspect/azimuth field (3rd value) to avoid noisy diffs
            lines[2] = " ".join(parts[:2])
        normalized = "\n".join(lines).encode()
        return hashlib.sha256(normalized).hexdigest()

    return sha256(path)


def file_hash(path: Path) -> str:
    """Hash files with format-aware normalization."""
    if path.suffix.lower() == ".sol":
        return sha256_sol(path)
    if path.suffix.lower() == ".slp":
        return sha256_slp(path)
    return sha256(path)


def index_files(root: Path) -> Dict[str, Path]:
    """Build a relative-path index for all files under root."""
    return {
        str(path.relative_to(root)): path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() != ".err"
    }


@dataclass
class ComparisonResult:
    only_a: Tuple[str, ...]
    only_b: Tuple[str, ...]
    identical: Counter[str]
    different: Counter[str]
    differing_paths: Tuple[str, ...]
    differing_by_suffix: Dict[str, Tuple[str, ...]]


def compare_dirs(dir_a: Path, dir_b: Path) -> ComparisonResult:
    files_a = index_files(dir_a)
    files_b = index_files(dir_b)

    only_a = tuple(sorted(set(files_a) - set(files_b)))
    only_b = tuple(sorted(set(files_b) - set(files_a)))

    identical: Counter[str] = Counter()
    different: Counter[str] = Counter()
    differing_paths: list[str] = []
    differing_by_suffix: defaultdict[str, list[str]] = defaultdict(list)

    for rel in sorted(set(files_a) & set(files_b)):
        a_path, b_path = files_a[rel], files_b[rel]
        if file_hash(a_path) == file_hash(b_path):
            identical[a_path.suffix] += 1
        else:
            different[a_path.suffix] += 1
            differing_paths.append(rel)
            differing_by_suffix[a_path.suffix].append(rel)

    return ComparisonResult(
        only_a=only_a,
        only_b=only_b,
        identical=identical,
        different=different,
        differing_paths=tuple(differing_paths),
        differing_by_suffix={
            suffix: tuple(paths) for suffix, paths in differing_by_suffix.items()
        },
    )


def _print_counter(label: str, data: Counter[str]) -> None:
    print(f"{label}:")
    if not data:
        print("  (none)")
        return
    for suffix, count in sorted(data.items(), key=lambda kv: kv[0]):
        print(f"  {suffix or '<no-ext>'}: {count}")


def _print_different_with_files(
    data: Counter[str], grouped_paths: Dict[str, Tuple[str, ...]]
) -> None:
    print("Different by extension:")
    if not data:
        print("  (none)")
        return
    for suffix, count in sorted(data.items(), key=lambda kv: kv[0]):
        print(f"  {suffix or '<no-ext>'}: {count}")
        for rel in grouped_paths.get(suffix, ()):  # list every differing file
            print(f"    {rel}")


def run_comparison(base_a: Path, base_b: Path, subdir: str, sample: int) -> None:
    dir_a = base_a / "wepp" / subdir
    dir_b = base_b / "wepp" / subdir
    if not dir_a.is_dir() or not dir_b.is_dir():
        print(f"Skipping {subdir}: missing {dir_a} or {dir_b}")
        return

    print(f"\n=== Comparing {subdir}: {dir_a} vs {dir_b}")
    result = compare_dirs(dir_a, dir_b)

    print(f"Only in A ({len(result.only_a)}):")
    for rel in result.only_a[:sample]:
        print(f"  {rel}")
    if len(result.only_a) > sample:
        print(f"  ... ({len(result.only_a) - sample} more)")

    print(f"Only in B ({len(result.only_b)}):")
    for rel in result.only_b[:sample]:
        print(f"  {rel}")
    if len(result.only_b) > sample:
        print(f"  ... ({len(result.only_b) - sample} more)")

    _print_counter("Identical by extension", result.identical)
    _print_different_with_files(result.different, result.differing_by_suffix)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare WEPP run directories (runs/ and output/).",
    )
    parser.add_argument("run_a", type=Path, help="Path to first run root")
    parser.add_argument("run_b", type=Path, help="Path to second run root")
    parser.add_argument(
        "--subdir",
        action="append",
        default=["runs", "output"],
        help="wepp/<subdir> to compare (repeatable)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="How many entries to show for unique/differing lists",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_a: Path = args.run_a
    base_b: Path = args.run_b
    for subdir in args.subdir:
        run_comparison(base_a, base_b, subdir, args.sample)


if __name__ == "__main__":
    main()
