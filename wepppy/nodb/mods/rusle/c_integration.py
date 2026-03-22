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

from .c_formula import compute_c_from_fg_pct, compute_fg_from_bare_ground_pct
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

        fg = np.asarray(compute_fg_from_bare_ground_pct(band_data["bare_ground"]), dtype=np.float64)
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
                "fg": "clamp(100 - bare_ground_pct, 0, 100)",
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
                c[mask] = row.resolved_c()
                lookup_keys_used.add((family, canonicalize_sbs_class(sbs_class)))
            continue

        row = resolve_lookup_row(lookup, family, "unburned")
        c[family_mask] = row.resolved_c()
        lookup_keys_used.add((family, "unburned"))

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
            "fg": "lookup ground_cover -> percent -> exp(-0.04 * fg)",
            "c": "exp(-0.04 * fg)",
            "b": 0.04,
        },
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
