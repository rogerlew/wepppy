"""Prune run directories to a minimal skeleton footprint."""

from __future__ import annotations

import glob
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable

__all__ = [
    "RUN_SKELETON_ALLOWLIST",
    "RUN_SKELETON_DENYLIST",
    "skeletonize_run",
]

RUN_SKELETON_ALLOWLIST: tuple[str, ...] = (
    "*.log",
    "*.vrt",
    "climate.nodb",
    "disturbed.nodb",
    "landuse.nodb",
    "nodb.version",
    "soils.nodb",
    "redisprep.dump",
    "ron.nodb",
    "run_metadata.json",
    "unitizer.nodb",
    "watershed.nodb",
    "wepp.nodb",
    "climate/*",
    "dem/wbt/*.geojson",
    "disturbed/disturbed_land_soil_lookup.csv",
    # Canonical directory parquet locations.
    "landuse/landuse.parquet",
    "soils/soils.parquet",
    "climate/wepp_cli.parquet",
    "climate/wepp_cli_pds_mean_metric.csv",
    "watershed/channels.parquet",
    "watershed/hillslopes.parquet",
    "watershed/flowpaths.parquet",
    "watershed/network.txt",
    "watershed/structure.json",
    "watershed/structure.pkl",
    "wepp/output/interchange",
)
RUN_SKELETON_DENYLIST: tuple[str, ...] = (
    "wepp/output/interchange/H.pass.parquet",
)


def skeletonize_run(
    run_wd: str | Path,
    allowlist: Iterable[str] = RUN_SKELETON_ALLOWLIST,
    denylist: Iterable[str] = RUN_SKELETON_DENYLIST,
) -> None:
    run_path = Path(run_wd).resolve()
    if not run_path.is_dir():
        raise FileNotFoundError(f"Run directory does not exist: {run_path}")

    git_dir = run_path / ".git"
    gitignore_path = run_path / ".gitignore"
    if git_dir.exists():
        raise RuntimeError(
            "Refusing to skeletonize inside an existing git repo: "
            f"{run_path}"
        )
    if gitignore_path.exists():
        raise RuntimeError(
            "Refusing to overwrite existing .gitignore: "
            f"{gitignore_path}"
        )

    gitignore_path.write_text(
        "\n".join(_build_gitignore(run_path, allowlist, denylist)) + "\n",
        encoding="utf-8",
    )

    try:
        subprocess.run(["git", "init", "-q"], cwd=run_path, check=True)
        subprocess.run(
            ["git", "-c", "core.excludesFile=/dev/null", "clean", "-d", "-f", "-X"],
            cwd=run_path,
            check=True,
        )
    finally:
        if git_dir.exists():
            shutil.rmtree(git_dir)
        if gitignore_path.exists():
            gitignore_path.unlink()


def _normalize_pattern(pattern: str) -> str:
    return pattern.strip().lstrip("/")


def _build_gitignore(
    run_path: Path,
    allowlist: Iterable[str],
    denylist: Iterable[str],
) -> list[str]:
    lines = ["*", ".*", "!.gitignore", "!.git/"]
    seen = set(lines)

    def add(line: str) -> None:
        if line in seen:
            return
        lines.append(line)
        seen.add(line)

    for raw_pattern in allowlist:
        pattern = _normalize_pattern(raw_pattern)
        if not pattern:
            continue

        _add_parent_dirs(pattern, add)
        add(f"!{pattern}")

        if _should_keep_dir(run_path, pattern):
            dir_pattern = pattern.rstrip("/")
            add(f"!{dir_pattern}/")
            add(f"!{dir_pattern}/**")

    for raw_pattern in denylist:
        pattern = _normalize_pattern(raw_pattern)
        if not pattern:
            continue
        lines.append(pattern)

    return lines


def _add_parent_dirs(pattern: str, add: Callable[[str], None]) -> None:
    parts = pattern.split("/")
    if len(parts) <= 1:
        return
    parents: list[str] = []
    for part in parts[:-1]:
        if glob.has_magic(part):
            break
        parents.append(part)
        add(f"!{'/'.join(parents)}/")


def _should_keep_dir(run_path: Path, pattern: str) -> bool:
    if glob.has_magic(pattern):
        return False
    if pattern.endswith("/"):
        return True
    if pattern.endswith("/*") or pattern.endswith("/**"):
        return False
    target = run_path / pattern
    return target.is_dir()
