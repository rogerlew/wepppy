"""RUSLE C-factor integration for `observed_rap` and `scenario_sbs`."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
import shutil
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

from wepppy.all_your_base.geo import raster_stacker
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.query_engine.activate import update_catalog_entry
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path

from .c_formula import compute_c_from_fg_pct, compute_observed_rap_fg_pct
from .c_lookup import (
    BASE_DISTURBED_CLASS_RASTER_CODES,
    BURNABLE_FAMILIES,
    DEFAULT_LOOKUP_PATH,
    DISTURBED_CLASS_RASTER_NODATA,
    MASKED_FAMILY_NAMES,
    RusleCLookupRow,
    canonicalize_sbs_class,
    disturbed_family_from_nlcd_class,
    load_rusle_c_lookup,
    resolve_lookup_row,
)
from .c_manifest import update_c_manifest


DEFAULT_DISTURBED_MAPPING_PATH = str(
    Path(__file__).resolve().parents[3] / "wepp" / "management" / "data" / "disturbed.json"
)

RAP_COVER_BAND_INDICES: dict[str, int] = {
    "annual_forb_and_grass": 1,
    "bare_ground": 2,
    "litter": 3,
    "perennial_forb_and_grass": 4,
    "shrub": 5,
    "tree": 6,
}

SBS_VALUE_TO_CLASS: dict[int, str] = {
    0: "unburned",
    1: "low",
    2: "moderate",
    3: "high",
}

COSURFFRAGS_PARQUET_COLUMN_CANDIDATES: tuple[str, ...] = (
    "cosurffrags_cover_pct",
    "surface_rock_cover_pct",
    "surface_rock_cover_percent",
    "sfragcov",
)

CFVO_TOP_LAYER_CANDIDATES: tuple[str, ...] = (
    "polaris/cfvo_mean_0_5.tif",
    "soils/cfvo_0-5cm_Q0.5.tif",
)

try:
    import duckdb
except ModuleNotFoundError:  # pragma: no cover - optional dependency boundary
    duckdb = None


__all__ = ["RusleCResult", "run_rusle_c_factor"]


@dataclass(frozen=True)
class RusleCResult:
    c: str
    manifest: str
    fg: str | None
    disturbed_class: str | None
    sbs_4class: str | None
    lookup_copy: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative_path(base: str, path: str) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def _dem_profile(path: str) -> dict[str, Any]:
    if not _exists(path):
        raise FileNotFoundError(f"DEM path does not exist: {path}")
    with rasterio.open(path) as dataset:
        return dict(dataset.profile)


def _aligned_band(path: str, dem_profile: dict[str, Any], *, band_index: int = 1) -> np.ndarray:
    if not _exists(path):
        raise FileNotFoundError(f"Required raster path does not exist: {path}")

    height = int(dem_profile["height"])
    width = int(dem_profile["width"])
    destination = np.full((height, width), np.nan, dtype=np.float64)

    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, band_index),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=dem_profile["transform"],
            dst_crs=dem_profile["crs"],
            dst_nodata=np.nan,
            resampling=Resampling.nearest,
        )

    return destination


def _mask_rap_cover_values(data: np.ndarray) -> np.ndarray:
    masked = np.asarray(data, dtype=np.float64).copy()
    # Keep >100 values so the locked `fg = clamp(100 - bare_ground_pct, 0, 100)`
    # contract can handle them; only obvious nodata/sentinel values are masked.
    invalid = ~np.isfinite(masked) | (masked < 0.0) | (masked >= 65535.0)
    masked[invalid] = np.nan
    return masked


def _coerce_rock_fraction_value(value: Any, *, field_name: str) -> float | str:
    if isinstance(value, str):
        token = value.strip().lower()
        if token == "auto":
            return "auto"
        if token == "":
            raise ValueError(f"{field_name} must be numeric in [0,1] or 'auto'")
        try:
            parsed = float(token)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be numeric in [0,1] or 'auto'") from exc
    else:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be numeric in [0,1] or 'auto'") from exc

    if not np.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{field_name} must be within [0, 1]")
    return float(parsed)


def _coerce_rock_fraction_of_rap_bare(value: Any) -> float | str:
    return _coerce_rock_fraction_value(value, field_name="rock_fraction_of_rap_bare")


def _coerce_rock_fraction_of_sbs_bare(value: Any) -> float | str:
    return _coerce_rock_fraction_value(value, field_name="rock_fraction_of_sbs_bare")


def _mean_bare_rap_0_1(*, bare_ground_pct: np.ndarray, valid_mask: np.ndarray) -> float:
    finite = valid_mask & np.isfinite(bare_ground_pct)
    if not np.any(finite):
        return 0.0
    bare_0_1 = np.clip(bare_ground_pct[finite] / 100.0, 0.0, 1.0)
    if bare_0_1.size == 0:
        return 0.0
    return float(np.nanmean(bare_0_1))


def _mean_lookup_bare_0_1(*, bare_lookup_0_1: np.ndarray, valid_mask: np.ndarray) -> float:
    finite = valid_mask & np.isfinite(bare_lookup_0_1)
    if not np.any(finite):
        return 0.0
    bare_0_1 = np.clip(bare_lookup_0_1[finite], 0.0, 1.0)
    if bare_0_1.size == 0:
        return 0.0
    return float(np.nanmean(bare_0_1))


def _load_cosurffrags_surface_proxy_from_soils_parquet(wd: str) -> tuple[float | None, dict[str, Any]]:
    soils_parquet = pick_existing_parquet_path(wd, "soils/soils.parquet")
    if soils_parquet is None:
        return None, {"status": "unavailable", "reason": "missing_soils_parquet"}
    if duckdb is None:
        return None, {"status": "unavailable", "reason": "duckdb_unavailable"}

    selected_column: str | None = None
    try:
        with duckdb.connect() as con:
            schema = con.execute("SELECT * FROM read_parquet(?) LIMIT 0", [str(soils_parquet)])
            column_names = {desc[0] for desc in schema.description}

            for candidate in COSURFFRAGS_PARQUET_COLUMN_CANDIDATES:
                if candidate in column_names:
                    selected_column = candidate
                    break

            if selected_column is None:
                return None, {
                    "status": "unavailable",
                    "reason": "missing_cosurffrags_columns",
                    "available_columns": sorted(column_names),
                    "expected_columns": list(COSURFFRAGS_PARQUET_COLUMN_CANDIDATES),
                }

            column_expr = f'"{selected_column}"'
            if "area" in column_names:
                rows = con.execute(
                    f"SELECT {column_expr}, area FROM read_parquet(?) WHERE {column_expr} IS NOT NULL",
                    [str(soils_parquet)],
                ).fetchall()
                weighted_rows = [
                    (float(cover_pct), float(area))
                    for cover_pct, area in rows
                    if cover_pct is not None
                    and area is not None
                    and np.isfinite(float(cover_pct))
                    and np.isfinite(float(area))
                    and float(area) > 0.0
                ]
                if not weighted_rows:
                    return None, {
                        "status": "unavailable",
                        "reason": "cosurffrags_no_weighted_rows",
                        "column": selected_column,
                    }
                total_area = float(sum(area for _value, area in weighted_rows))
                if total_area <= 0.0:
                    return None, {
                        "status": "unavailable",
                        "reason": "cosurffrags_nonpositive_total_area",
                        "column": selected_column,
                    }
                cover_pct = float(sum(value * area for value, area in weighted_rows) / total_area)
                row_count = len(weighted_rows)
                aggregation = "area_weighted_mean"
            else:
                rows = con.execute(
                    f"SELECT {column_expr} FROM read_parquet(?) WHERE {column_expr} IS NOT NULL",
                    [str(soils_parquet)],
                ).fetchall()
                values = [
                    float(cover_pct)
                    for (cover_pct,) in rows
                    if cover_pct is not None and np.isfinite(float(cover_pct))
                ]
                if not values:
                    return None, {
                        "status": "unavailable",
                        "reason": "cosurffrags_no_finite_rows",
                        "column": selected_column,
                    }
                cover_pct = float(np.mean(values))
                row_count = len(values)
                aggregation = "mean"
    except Exception as exc:
        return None, {
            "status": "unavailable",
            "reason": "cosurffrags_query_failed",
            "error": str(exc),
        }

    surface_proxy_0_1 = float(np.clip(cover_pct / 100.0, 0.0, 1.0))
    return surface_proxy_0_1, {
        "status": "available",
        "source_kind": "soils_parquet_cosurffrags",
        "column": selected_column,
        "aggregation": aggregation,
        "cover_pct": cover_pct,
        "row_count": int(row_count),
        "surface_rock_cover_proxy_0_1": surface_proxy_0_1,
    }


def _load_cfvo_surface_proxy_from_raster(
    *,
    wd: str,
    dem_profile: dict[str, Any],
    valid_mask: np.ndarray,
) -> tuple[float | None, dict[str, Any]]:
    for relpath in CFVO_TOP_LAYER_CANDIDATES:
        raster_path = _join(wd, relpath)
        if not _exists(raster_path):
            continue
        try:
            aligned = _aligned_band(raster_path, dem_profile)
        except (OSError, rasterio.errors.RasterioError) as exc:
            return None, {
                "status": "unavailable",
                "reason": "cfvo_read_failed",
                "path": raster_path,
                "error": str(exc),
            }

        finite = valid_mask & np.isfinite(aligned)
        if not np.any(finite):
            continue

        cfvo_values = np.asarray(aligned[finite], dtype=np.float64)
        raw_max = float(np.nanmax(cfvo_values))
        scale_divisor = 10.0 if raw_max > 100.0 else 1.0
        cfvo_volpct = np.clip(cfvo_values / scale_divisor, 0.0, 100.0)
        cfvo_0_5cm_volpct = float(np.nanmean(cfvo_volpct))
        surface_proxy_0_1 = float(np.clip(cfvo_0_5cm_volpct / 100.0, 0.0, 1.0))
        return surface_proxy_0_1, {
            "status": "available",
            "source_kind": "cfvo_top_horizon",
            "path": raster_path,
            "cfvo_0_5cm_volpct": cfvo_0_5cm_volpct,
            "scale_divisor": scale_divisor,
            "surface_rock_cover_proxy_0_1": surface_proxy_0_1,
            "sample_cells": int(np.count_nonzero(finite)),
        }

    return None, {
        "status": "unavailable",
        "reason": "missing_cfvo_top_horizon_raster",
        "expected_paths": [_join(wd, relpath) for relpath in CFVO_TOP_LAYER_CANDIDATES],
    }


def _resolve_rock_fraction_auto(
    *,
    wd: str,
    dem_profile: dict[str, Any],
    valid_mask: np.ndarray,
    bare_ground_pct: np.ndarray,
) -> dict[str, Any]:
    bare_rap_mean_0_1 = _mean_bare_rap_0_1(bare_ground_pct=bare_ground_pct, valid_mask=valid_mask)
    cosurffrags_proxy_0_1, cosurffrags_report = _load_cosurffrags_surface_proxy_from_soils_parquet(wd)
    cfvo_proxy_0_1: float | None = None
    cfvo_report: dict[str, Any] | None = None

    if cosurffrags_proxy_0_1 is not None:
        source = "auto:cosurffrags"
        surface_proxy_0_1 = float(cosurffrags_proxy_0_1)
    else:
        cfvo_proxy_0_1, cfvo_report = _load_cfvo_surface_proxy_from_raster(
            wd=wd,
            dem_profile=dem_profile,
            valid_mask=valid_mask,
        )
        if cfvo_proxy_0_1 is not None:
            source = "auto:cfvo"
            surface_proxy_0_1 = float(cfvo_proxy_0_1)
        else:
            source = "auto:fallback_0"
            surface_proxy_0_1 = 0.0

    if bare_rap_mean_0_1 > 0.0:
        effective_fraction = float(np.clip(surface_proxy_0_1 / bare_rap_mean_0_1, 0.0, 1.0))
    else:
        effective_fraction = 0.0

    report: dict[str, Any] = {
        "requested": "auto",
        "effective": effective_fraction,
        "source": source,
        "surface_rock_cover_proxy_0_1": float(surface_proxy_0_1),
        "bare_rap_mean_0_1": float(bare_rap_mean_0_1),
        "normalization": "clamp(surface_rock_cover_proxy_0_1 / bare_rap_mean_0_1, 0, 1) when bare_rap_mean_0_1 > 0 else 0",
        "sources": {"cosurffrags": cosurffrags_report},
    }
    if cfvo_report is not None:
        report["sources"]["cfvo"] = cfvo_report
    if source == "auto:fallback_0":
        report["fallback_reason"] = (
            "No cosurffrags surface proxy or cfvo top-horizon proxy available for this run."
        )
    return report


def _resolve_rock_fraction_auto_for_scenario_sbs(
    *,
    wd: str,
    dem_profile: dict[str, Any],
    valid_mask: np.ndarray,
    bare_lookup_0_1: np.ndarray,
) -> dict[str, Any]:
    bare_lookup_mean_0_1 = _mean_lookup_bare_0_1(bare_lookup_0_1=bare_lookup_0_1, valid_mask=valid_mask)
    cosurffrags_proxy_0_1, cosurffrags_report = _load_cosurffrags_surface_proxy_from_soils_parquet(wd)
    cfvo_proxy_0_1: float | None = None
    cfvo_report: dict[str, Any] | None = None

    if cosurffrags_proxy_0_1 is not None:
        source = "auto:cosurffrags"
        surface_proxy_0_1 = float(cosurffrags_proxy_0_1)
    else:
        cfvo_proxy_0_1, cfvo_report = _load_cfvo_surface_proxy_from_raster(
            wd=wd,
            dem_profile=dem_profile,
            valid_mask=valid_mask,
        )
        if cfvo_proxy_0_1 is not None:
            source = "auto:cfvo"
            surface_proxy_0_1 = float(cfvo_proxy_0_1)
        else:
            source = "auto:fallback_0"
            surface_proxy_0_1 = 0.0

    if bare_lookup_mean_0_1 > 0.0:
        effective_fraction = float(np.clip(surface_proxy_0_1 / bare_lookup_mean_0_1, 0.0, 1.0))
    else:
        effective_fraction = 0.0

    report: dict[str, Any] = {
        "requested": "auto",
        "effective": effective_fraction,
        "source": source,
        "surface_rock_cover_proxy_0_1": float(surface_proxy_0_1),
        "bare_lookup_mean_0_1": float(bare_lookup_mean_0_1),
        "normalization": "clamp(surface_rock_cover_proxy_0_1 / bare_lookup_mean_0_1, 0, 1) when bare_lookup_mean_0_1 > 0 else 0",
        "sources": {"cosurffrags": cosurffrags_report},
    }
    if cfvo_report is not None:
        report["sources"]["cfvo"] = cfvo_report
    if source == "auto:fallback_0":
        report["fallback_reason"] = (
            "No cosurffrags surface proxy or cfvo top-horizon proxy available for this run."
        )
    return report


def _lookup_fg_pct_for_row(row: RusleCLookupRow) -> float:
    if row.ground_cover is not None:
        return float(np.clip(float(row.ground_cover) * 100.0, 0.0, 100.0))
    if row.c_override is not None:
        c_value = float(row.c_override)
        if not np.isfinite(c_value) or c_value <= 0.0:
            raise ValueError(
                "scenario_sbs lookup row requires finite positive c_override when ground_cover is absent: "
                f"disturbed_class={row.disturbed_class!r}, sbs_class={row.sbs_class!r}"
            )
        return float(np.clip(-np.log(c_value) / 0.04, 0.0, 100.0))
    raise ValueError(
        "scenario_sbs lookup row requires ground_cover or c_override: "
        f"disturbed_class={row.disturbed_class!r}, sbs_class={row.sbs_class!r}"
    )


def _write_float_raster(path: str, data: np.ndarray, profile: dict[str, Any], *, nodata: float = -9999.0) -> None:
    out_profile = dict(profile)
    out_profile.update(
        {
            "driver": "GTiff",
            "dtype": "float32",
            "count": 1,
            "nodata": nodata,
            "compress": "deflate",
        }
    )
    writable = np.where(np.isfinite(data), data, nodata).astype(np.float32)
    with rasterio.open(path, "w", **out_profile) as dataset:
        dataset.write(writable, 1)


def _write_uint8_raster(path: str, data: np.ndarray, profile: dict[str, Any], *, nodata: int) -> None:
    out_profile = dict(profile)
    out_profile.update(
        {
            "driver": "GTiff",
            "dtype": "uint8",
            "count": 1,
            "nodata": nodata,
            "compress": "deflate",
        }
    )
    with rasterio.open(path, "w", **out_profile) as dataset:
        dataset.write(data.astype(np.uint8), 1)


def _load_disturbed_mapping(path: str) -> dict[int, dict[str, Any]]:
    if not _exists(path):
        raise FileNotFoundError(f"Disturbed mapping file does not exist: {path}")
    with open(path, "r", encoding="utf-8") as stream:
        payload = json.load(stream)
    return {int(key): dict(value) for key, value in payload.items()}


def _build_disturbed_class_raster(
    landuse_aligned: np.ndarray,
    *,
    disturbed_mapping: dict[int, dict[str, Any]],
) -> tuple[np.ndarray, dict[str, int], dict[str, int], dict[str, str]]:
    valid = np.isfinite(landuse_aligned)
    rounded = np.zeros(landuse_aligned.shape, dtype=np.int32)
    rounded[valid] = np.rint(landuse_aligned[valid]).astype(np.int32)

    family_codes = dict(BASE_DISTURBED_CLASS_RASTER_CODES)
    next_code = max(family_codes.values()) + 1

    disturbed_class = np.full(
        landuse_aligned.shape,
        DISTURBED_CLASS_RASTER_NODATA,
        dtype=np.uint8,
    )
    family_counts: Counter[str] = Counter()
    nlcd_family_map: dict[str, str] = {}

    for nlcd_code in sorted(set(int(value) for value in rounded[valid])):
        if nlcd_code == 0:
            continue

        mapping_row = disturbed_mapping.get(nlcd_code)
        if mapping_row is None:
            raise ValueError(f"Landuse raster contains NLCD class {nlcd_code} missing from disturbed mapping")

        family = disturbed_family_from_nlcd_class(nlcd_code, mapping_row.get("DisturbedClass"))
        if family is None:
            continue

        if family not in family_codes:
            family_codes[family] = next_code
            next_code += 1
            if next_code > 255:
                raise ValueError("Too many disturbed-family raster codes for uint8 output")

        mask = rounded == nlcd_code
        disturbed_class[mask] = family_codes[family]
        family_counts[family] += int(np.count_nonzero(mask))
        nlcd_family_map[str(nlcd_code)] = family

    return disturbed_class, family_codes, dict(family_counts), nlcd_family_map


def _prepare_sbs_4class(
    *,
    sbs_path: str,
    dem_path: str,
    dem_profile: dict[str, Any],
    output_path: str,
    sbs_is_4class: bool,
) -> np.ndarray:
    if sbs_is_4class:
        aligned = _aligned_band(sbs_path, dem_profile)
        sbs_4class = np.full(aligned.shape, 255, dtype=np.uint8)
        valid = np.isfinite(aligned)
        rounded = np.rint(aligned[valid]).astype(np.int32)
        allowed = {0, 1, 2, 3, 255}
        invalid_values = sorted({int(value) for value in rounded if int(value) not in allowed})
        if invalid_values:
            raise ValueError(f"Expected SBS 4-class raster values in {sorted(allowed)}, got {invalid_values}")
        sbs_4class[valid] = rounded.astype(np.uint8)
        _write_uint8_raster(output_path, sbs_4class, dem_profile, nodata=255)
        return sbs_4class

    aligned_source_path = output_path.replace("sbs_4class.tif", "sbs_source_aligned.tif")
    raster_stacker(sbs_path, dem_path, aligned_source_path, resample="near")
    SoilBurnSeverityMap(aligned_source_path).export_4class_map(output_path)
    os.remove(aligned_source_path)

    with rasterio.open(output_path) as dataset:
        data = dataset.read(1).astype(np.uint8)

    return data


def _build_lookup_key_payload(lookup_keys_used: set[tuple[str, str]], lookup: dict[tuple[str, str], RusleCLookupRow]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for disturbed_class, sbs_class in sorted(lookup_keys_used):
        row = lookup[(disturbed_class, sbs_class)]
        payload.append(
            {
                "disturbed_class": disturbed_class,
                "sbs_class": sbs_class,
                "c_value": row.resolved_c(),
            }
        )
    return payload


def run_rusle_c_factor(
    wd: str,
    dem: str,
    *,
    c_mode: str,
    c_output_filename: str = "c.tif",
    rap: str | None = None,
    rock_fraction_of_rap_bare: float | str = "auto",
    rock_fraction_of_sbs_bare: float | str = "auto",
    landuse: str | None = None,
    sbs: str | None = None,
    sbs_is_4class: bool = False,
    disturbed_mapping_path: str = DEFAULT_DISTURBED_MAPPING_PATH,
    lookup_path: str = DEFAULT_LOOKUP_PATH,
) -> RusleCResult:
    """Compute a run-scoped RUSLE `C` factor artifact."""

    dem_profile = _dem_profile(dem)

    rusle_dir = _join(wd, "rusle")
    os.makedirs(rusle_dir, exist_ok=True)

    c_output_name = str(c_output_filename).strip()
    if not c_output_name:
        raise ValueError("c_output_filename must be a non-empty filename")
    c_path = _join(rusle_dir, c_output_name)
    fg_path = _join(rusle_dir, "c_fg.tif")
    disturbed_class_path = _join(rusle_dir, "disturbed_class.tif")
    sbs_4class_path = _join(rusle_dir, "sbs_4class.tif")
    lookup_copy_path = _join(rusle_dir, "c_lookup_used.csv")
    manifest_path = _join(rusle_dir, "manifest.json")

    if c_mode == "observed_rap":
        if rap is None:
            raise ValueError("rap path is required for c_mode='observed_rap'")

        band_data: dict[str, np.ndarray] = {}
        valid_mask = np.ones((int(dem_profile["height"]), int(dem_profile["width"])), dtype=bool)
        for band_name, band_index in RAP_COVER_BAND_INDICES.items():
            aligned = _aligned_band(rap, dem_profile, band_index=band_index)
            cleaned = _mask_rap_cover_values(aligned)
            band_data[band_name] = cleaned
            valid_mask &= np.isfinite(cleaned)

        requested_rock_fraction = _coerce_rock_fraction_of_rap_bare(rock_fraction_of_rap_bare)
        if requested_rock_fraction == "auto":
            rock_report = _resolve_rock_fraction_auto(
                wd=wd,
                dem_profile=dem_profile,
                valid_mask=valid_mask,
                bare_ground_pct=band_data["bare_ground"],
            )
            effective_rock_fraction = float(rock_report["effective"])
        else:
            effective_rock_fraction = float(requested_rock_fraction)
            rock_report = {
                "requested": float(requested_rock_fraction),
                "effective": float(effective_rock_fraction),
                "source": "user",
            }

        fg = np.asarray(
            compute_observed_rap_fg_pct(
                band_data["bare_ground"],
                rock_fraction_of_rap_bare=effective_rock_fraction,
            ),
            dtype=np.float64,
        )
        fg[~valid_mask] = np.nan
        c = np.asarray(compute_c_from_fg_pct(fg), dtype=np.float64)
        c[~valid_mask] = np.nan

        _write_float_raster(c_path, c, dem_profile)
        _write_float_raster(fg_path, fg, dem_profile)

        for path in (c_path, fg_path):
            update_catalog_entry(wd, _relative_path(wd, path))

        c_manifest = {
            "mode": "observed_rap",
            "formula": {
                "fg": "100 * (1 - bare_rap_0_1 * (1 - r_bare))",
                "bare_rap_0_1": "clamp(bare_ground_pct / 100, 0, 1)",
                "r_bare": "clamp(rock_fraction_of_rap_bare, 0, 1)",
                "c": "exp(-0.04 * fg)",
                "b": 0.04,
            },
            "neutral_terms": {
                "canopy": 1.0,
                "roughness": 1.0,
                "biomass": 1.0,
                "consolidation": 1.0,
            },
            "rap_band_indices": dict(RAP_COVER_BAND_INDICES),
            "rock_fraction_of_rap_bare": rock_report,
            "valid_mask_rule": "all_required_rap_cover_bands_finite_after_dem_alignment",
            "generated_utc": _utc_now_iso(),
            "source_paths": {"dem": dem, "rap": rap},
            "artifacts": asdict(
                RusleCResult(
                    c=c_path,
                    manifest=manifest_path,
                    fg=fg_path,
                    disturbed_class=None,
                    sbs_4class=None,
                    lookup_copy=None,
                )
            ),
        }
        update_c_manifest(manifest_path, c_manifest)
        update_catalog_entry(wd, _relative_path(wd, manifest_path))

        return RusleCResult(
            c=c_path,
            manifest=manifest_path,
            fg=fg_path,
            disturbed_class=None,
            sbs_4class=None,
            lookup_copy=None,
        )

    if c_mode != "scenario_sbs":
        raise ValueError(f"Unsupported RUSLE C mode: {c_mode!r}")

    if landuse is None:
        raise ValueError("landuse path is required for c_mode='scenario_sbs'")

    lookup = load_rusle_c_lookup(lookup_path)
    disturbed_mapping = _load_disturbed_mapping(disturbed_mapping_path)

    landuse_aligned = _aligned_band(landuse, dem_profile)
    disturbed_class, family_codes, family_counts, nlcd_family_map = _build_disturbed_class_raster(
        landuse_aligned,
        disturbed_mapping=disturbed_mapping,
    )
    _write_uint8_raster(
        disturbed_class_path,
        disturbed_class,
        dem_profile,
        nodata=DISTURBED_CLASS_RASTER_NODATA,
    )

    sbs_4class: np.ndarray | None = None
    if sbs is not None:
        sbs_4class = _prepare_sbs_4class(
            sbs_path=sbs,
            dem_path=dem,
            dem_profile=dem_profile,
            output_path=sbs_4class_path,
            sbs_is_4class=sbs_is_4class,
        )

    inverse_family_codes = {code: family for family, code in family_codes.items()}
    requested_sbs_rock_fraction = _coerce_rock_fraction_of_sbs_bare(rock_fraction_of_sbs_bare)
    bare_lookup_0_1 = np.full(landuse_aligned.shape, np.nan, dtype=np.float64)
    c = np.full(landuse_aligned.shape, np.nan, dtype=np.float64)
    lookup_keys_used: set[tuple[str, str]] = set()

    for code, family in sorted(inverse_family_codes.items()):
        if code == DISTURBED_CLASS_RASTER_NODATA:
            continue

        family_mask = disturbed_class == code
        if not np.any(family_mask):
            continue

        if family in MASKED_FAMILY_NAMES:
            continue

        if family in BURNABLE_FAMILIES and sbs_4class is not None:
            for sbs_value, sbs_class in SBS_VALUE_TO_CLASS.items():
                mask = family_mask & (sbs_4class == sbs_value)
                if not np.any(mask):
                    continue
                row = resolve_lookup_row(lookup, family, sbs_class)
                fg_lookup_pct = _lookup_fg_pct_for_row(row)
                bare_lookup_0_1[mask] = np.clip(1.0 - (fg_lookup_pct / 100.0), 0.0, 1.0)
                lookup_keys_used.add((family, canonicalize_sbs_class(sbs_class)))
            continue

        row = resolve_lookup_row(lookup, family, "unburned")
        fg_lookup_pct = _lookup_fg_pct_for_row(row)
        bare_lookup_0_1[family_mask] = np.clip(1.0 - (fg_lookup_pct / 100.0), 0.0, 1.0)
        lookup_keys_used.add((family, "unburned"))

    valid_lookup_mask = np.isfinite(bare_lookup_0_1)
    if requested_sbs_rock_fraction == "auto":
        sbs_rock_report = _resolve_rock_fraction_auto_for_scenario_sbs(
            wd=wd,
            dem_profile=dem_profile,
            valid_mask=valid_lookup_mask,
            bare_lookup_0_1=bare_lookup_0_1,
        )
        effective_sbs_rock_fraction = float(sbs_rock_report["effective"])
    else:
        effective_sbs_rock_fraction = float(requested_sbs_rock_fraction)
        sbs_rock_report = {
            "requested": float(requested_sbs_rock_fraction),
            "effective": float(effective_sbs_rock_fraction),
            "source": "user",
        }

    fg_effective_pct = np.full(landuse_aligned.shape, np.nan, dtype=np.float64)
    fg_effective_pct[valid_lookup_mask] = 100.0 * (
        1.0 - (bare_lookup_0_1[valid_lookup_mask] * (1.0 - effective_sbs_rock_fraction))
    )
    c[valid_lookup_mask] = np.asarray(compute_c_from_fg_pct(fg_effective_pct[valid_lookup_mask]), dtype=np.float64)

    shutil.copyfile(lookup_path, lookup_copy_path)
    _write_float_raster(c_path, c, dem_profile)

    catalog_paths = [c_path, disturbed_class_path, lookup_copy_path]
    if sbs_4class is not None:
        catalog_paths.append(sbs_4class_path)
    for path in catalog_paths:
        update_catalog_entry(wd, _relative_path(wd, path))

    if sbs_4class is None:
        sbs_counts: dict[str, int] = {}
    else:
        sbs_counts = dict(Counter(str(int(value)) for value in sbs_4class[np.where(sbs_4class != 255)]))
    c_manifest = {
        "mode": "scenario_sbs",
        "formula": {
            "fg_lookup_pct": "lookup ground_cover fraction * 100 (or inverse from c_override when ground_cover absent)",
            "bare_lookup_0_1": "clamp(1 - fg_lookup_pct / 100, 0, 1)",
            "r_sbs_bare": "clamp(rock_fraction_of_sbs_bare, 0, 1)",
            "fg_effective_pct": "100 * (1 - bare_lookup_0_1 * (1 - r_sbs_bare))",
            "c": "exp(-0.04 * fg_effective_pct)",
            "b": 0.04,
        },
        "rock_fraction_of_sbs_bare": sbs_rock_report,
        "burnable_families": list(BURNABLE_FAMILIES),
        "masked_families": sorted(MASKED_FAMILY_NAMES),
        "disturbed_class_codes": {family: int(code) for family, code in sorted(family_codes.items(), key=lambda item: item[1])},
        "disturbed_family_counts": family_counts,
        "sbs_counts": sbs_counts,
        "lookup_keys_used": _build_lookup_key_payload(lookup_keys_used, lookup),
        "source_paths": {
            "dem": dem,
            "landuse": landuse,
            "sbs": sbs,
            "disturbed_mapping": disturbed_mapping_path,
            "lookup": lookup_path,
        },
        "sbs_input_mode": (
            "classified_4class"
            if sbs_is_4class and sbs is not None
            else "normalized_from_source"
            if sbs is not None
            else "missing_use_unburned"
        ),
        "nlcd_family_map": nlcd_family_map,
        "generated_utc": _utc_now_iso(),
        "artifacts": asdict(
            RusleCResult(
                c=c_path,
                manifest=manifest_path,
                fg=None,
                disturbed_class=disturbed_class_path,
                sbs_4class=sbs_4class_path if sbs_4class is not None else None,
                lookup_copy=lookup_copy_path,
            )
        ),
    }
    update_c_manifest(manifest_path, c_manifest)
    update_catalog_entry(wd, _relative_path(wd, manifest_path))

    return RusleCResult(
        c=c_path,
        manifest=manifest_path,
        fg=None,
        disturbed_class=disturbed_class_path,
        sbs_4class=sbs_4class_path if sbs_4class is not None else None,
        lookup_copy=lookup_copy_path,
    )
