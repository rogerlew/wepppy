from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from wepppy.mcp.base import mcp_tool, validate_run_scope
from wepppy.weppcloud.utils.helpers import get_wd

MAX_FILE_BYTES = 1_000_000  # 1 MB default cap for agent reads


def _run_root(runid: str) -> Path:
    path = Path(get_wd(runid))
    if not path.exists():
        raise FileNotFoundError(f"Run directory not found for {runid}")
    return path


def _sample_names(paths: Iterable[Path], limit: int = 5) -> list[str]:
    names: list[str] = []
    for path in paths:
        names.append(path.name)
        if len(names) >= limit:
            break
    return names


def _describe_climate(root: Path) -> Dict[str, Any]:
    climate_dir = root / "climate"
    if not climate_dir.exists():
        return {}
    cli_files = sorted(climate_dir.glob("*.cli"))
    observed_dir = climate_dir / "observed"
    monthlies = observed_dir.glob("*.txt") if observed_dir.exists() else []
    return {
        "type": "hillslope_climate",
        "count": len(cli_files),
        "pattern": "*.cli",
        "sample_files": _sample_names(cli_files),
        "has_monthlies": any(monthlies),
    }


def _describe_wepp(root: Path) -> Dict[str, Any]:
    wepp_output = root / "wepp" / "output"
    if not wepp_output.exists():
        return {}
    hillslopes = sorted(wepp_output.glob("H*.hill.txt"))
    channels = sorted(wepp_output.glob("C*.channel.txt"))
    daily = list(wepp_output.glob("*.daily.txt"))
    return {
        "hillslope_count": len(hillslopes),
        "channel_count": len(channels),
        "has_daily_output": bool(daily),
        "sample_files": _sample_names(list(hillslopes) + list(channels)),
    }


def _describe_reports(root: Path) -> Dict[str, Any]:
    reports_dir = root / "reports"
    if not reports_dir.exists():
        return {}
    drafts = sorted(reports_dir.glob("*.md"))
    return {
        "count": len(drafts),
        "ids": [draft.stem for draft in drafts],
        "status": "draft" if drafts else "none",
    }


def _describe_watershed(root: Path) -> Dict[str, Any]:
    watershed_dir = root / "watershed"
    if not watershed_dir.exists():
        return {}
    method = "peridot" if (watershed_dir / "peridot_slopes.parquet").exists() else "topaz"
    subcatchments = list(watershed_dir.glob("subcatchments*.json"))
    return {
        "delineation_method": method,
        "subcatchment_count": len(subcatchments),
    }


def _describe_landuse(root: Path) -> Dict[str, Any]:
    landuse_dir = root / "landuse"
    if not landuse_dir.exists():
        return {}
    return {
        "has_burns": (landuse_dir / "fire_date.txt").exists(),
    }


def _describe_soils(root: Path) -> Dict[str, Any]:
    soils_dir = root / "soils"
    if not soils_dir.exists():
        return {}
    return {}


@mcp_tool()
def describe_run_contents(
    runid: str, category: Optional[str] = None, _jwt_claims: Mapping[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Return lightweight metadata about a run directory.
    """

    if _jwt_claims is None:
        raise PermissionError("Missing JWT claims for run validation")
    validate_run_scope(runid, _jwt_claims)

    root = _run_root(runid)
    category_normalized = category.lower() if category else None
    payload: Dict[str, Any] = {}

    if category_normalized in (None, "climate"):
        data = _describe_climate(root)
        if data:
            payload["climate"] = data

    if category_normalized in (None, "wepp"):
        data = _describe_wepp(root)
        if data:
            payload["wepp"] = data

    if category_normalized in (None, "reports"):
        data = _describe_reports(root)
        if data:
            payload["reports"] = data

    if category_normalized in (None, "watershed"):
        data = _describe_watershed(root)
        if data:
            payload["watershed"] = data

    if category_normalized in (None, "landuse"):
        data = _describe_landuse(root)
        if data:
            payload["landuse"] = data

    if category_normalized in (None, "soils"):
        data = _describe_soils(root)
        if data:
            payload["soils"] = data

    return payload


def _normalize_relative_path(path: str) -> Path:
    sanitized = path.lstrip("/\\")
    return Path(sanitized)


@mcp_tool()
def read_run_file(
    runid: str, path: str, *, encoding: str = "utf-8", _jwt_claims: Mapping[str, Any] | None = None
) -> str:
    """
    Read a small text file from the run directory.
    """

    if _jwt_claims is None:
        raise PermissionError("Missing JWT claims for run validation")
    validate_run_scope(runid, _jwt_claims)

    root = _run_root(runid).resolve()
    relative = _normalize_relative_path(path)
    candidate = (root / relative).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError("Path traversal detected") from exc

    if not candidate.exists():
        raise FileNotFoundError(f"{relative} does not exist in run {runid}")
    if not candidate.is_file():
        raise IsADirectoryError(f"{relative} is not a file")

    if candidate.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(
            f"{relative} is larger than the {MAX_FILE_BYTES} byte safety limit"
        )

    return candidate.read_text(encoding=encoding, errors="ignore")
