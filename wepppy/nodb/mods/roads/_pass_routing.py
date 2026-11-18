"""Roads PASS climate identity and isolated native workspace assembly."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable, Optional


def _safe_link_or_copy(src: str, dst: str) -> str:
    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists() or dst_path.is_symlink():
        dst_path.unlink()

    try:
        os.symlink(src_path, dst_path)
        return "symlink"
    except OSError:
        shutil.copy2(src_path, dst_path)
        return "copy"


def _read_pass_header_climate_line(pass_path: Path) -> str:
    from wepppy.wepp.interchange.pass_metadata import pass_metadata_offset

    with pass_path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline()
        if pass_metadata_offset(first_line):
            first_line = handle.readline()
    if not first_line:
        raise ValueError(f"{pass_path}: PASS file missing climate-file token on line 1")
    return first_line.rstrip("\r\n")


def _rewrite_pass_header_climate_line(pass_path: Path, climate_line: str) -> None:
    from wepppy.wepp.interchange.pass_metadata import pass_metadata_offset

    with pass_path.open(encoding="utf-8", newline="") as stream:
        lines = stream.readlines()
    if not lines:
        raise ValueError(f"{pass_path}: PASS file missing climate-file token on line 1")
    offset = pass_metadata_offset(lines[0])
    if len(lines) <= offset:
        raise ValueError(f"{pass_path}: PASS file missing climate-file token")
    newline = "\n"
    if lines[offset].endswith("\r\n"):
        newline = "\r\n"
    elif lines[offset].endswith("\n"):
        newline = "\n"
    lines[offset] = f"{climate_line}{newline}"
    with pass_path.open("w", encoding="utf-8", newline="") as stream:
        stream.writelines(lines)


def _resolve_pass_header_climate_path(pass_path: Path, climate_token: str) -> Optional[Path]:
    token = climate_token.strip()
    if not token:
        return None
    runs_dir = pass_path.parent.parent / "runs"
    climate_path = runs_dir / token
    if not climate_path.exists():
        return None
    try:
        return climate_path.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None


def _normalize_road_pass_header_climate_tokens(
    self,
    *,
    base_pass_path: Path,
    road_pass_paths: Iterable[Path],
) -> None:
    base_climate_line = self._read_pass_header_climate_line(base_pass_path)
    base_climate_token = base_climate_line.strip()
    if not base_climate_token:
        raise ValueError(
            f"{base_pass_path}: PASS header climate-file token is empty; cannot combine roads PASS data"
        )

    base_climate_path = self._resolve_pass_header_climate_path(base_pass_path, base_climate_token)
    if base_climate_path is None:
        raise ValueError(
            f"{base_pass_path}: PASS header climate-file token '{base_climate_token}' does not resolve under runs/"
        )

    for road_pass_path in road_pass_paths:
        source_climate_line = self._read_pass_header_climate_line(road_pass_path)
        source_climate_token = source_climate_line.strip()
        if source_climate_token == base_climate_token:
            continue

        source_climate_path = self._resolve_pass_header_climate_path(
            road_pass_path, source_climate_token
        )
        if source_climate_path is None or source_climate_path != base_climate_path:
            raise ValueError(
                f"{road_pass_path}: PASS header climate-file token mismatch could not be normalized "
                f"(base={base_climate_token} source={source_climate_token} "
                f"base_cli={base_climate_path} source_cli={source_climate_path})"
            )

        self._rewrite_pass_header_climate_line(road_pass_path, base_climate_line)
        self._append_roads_log(
            "run",
            "normalized_road_pass_climate_token",
            {
                "base_pass_relpath": os.path.relpath(base_pass_path, self.wd),
                "road_pass_relpath": os.path.relpath(road_pass_path, self.wd),
                "base_climate_token": base_climate_token,
                "source_climate_token": source_climate_token,
            },
        )


def _combine_target_hillslope_pass(
    self,
    *,
    base_pass_path: str,
    road_pass_paths: Iterable[str],
    output_pass_path: str,
    strategy: str = "phase1",
) -> None:
    from wepppyo3.wepp_interchange import combine_hillslope_pass_files

    base_path = Path(base_pass_path)
    road_paths = [Path(path) for path in road_pass_paths]
    if road_paths:
        self._normalize_road_pass_header_climate_tokens(
            base_pass_path=base_path,
            road_pass_paths=road_paths,
        )

    combine_hillslope_pass_files(
        base_pass=str(base_path),
        road_passes=[str(path) for path in road_paths],
        out_pass=str(output_pass_path),
        strategy=str(strategy),
    )


def _prepare_roads_runs_workspace(self) -> None:
    baseline_runs_dir = Path(self.wepp_instance.runs_dir)
    if not baseline_runs_dir.exists():
        raise FileNotFoundError(f"Missing baseline WEPP runs directory: {baseline_runs_dir}")

    runs_dir = Path(self.roads_runs_dir)
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    for entry in baseline_runs_dir.iterdir():
        # Native watershed rewrites tc_out.txt; never link baseline diagnostics.
        if entry.name in {"pw0.run", "pw0.err", "tc_out.txt"}:
            continue
        dst = runs_dir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dst)
        else:
            self._safe_link_or_copy(str(entry), str(dst))


def _prepare_roads_output_workspace(self) -> None:
    output_dir = Path(self.roads_output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
