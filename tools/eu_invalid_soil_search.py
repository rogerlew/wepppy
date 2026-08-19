"""Generate reproducible coordinate manifests for EU invalid-soil searches.

The generated manifest is intentionally only a sampling frame. Source
screening and full ESDAC builds are separate steps so a large search does not
silently change production soil-building behavior.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
import random
from pathlib import Path
from typing import Any

DEFAULT_ANCHOR_ATTRIBUTE = "fao90lev1"
DEFAULT_SEED = 20260819
DEFAULT_STRATA = (20, 20)

ESDB_SCREEN_ATTRIBUTES = (
    "fao90lev1",
    "usedom",
    "textdepchg",
    "il",
    "cec_top",
    "cec_sub",
    "dgh",
    "dimp",
    "dr",
)
STU_SCREEN_ATTRIBUTES = (
    "STU_EU_T_CLAY",
    "STU_EU_S_CLAY",
    "STU_EU_T_SAND",
    "STU_EU_S_SAND",
    "STU_EU_T_SILT",
    "STU_EU_S_SILT",
    "STU_EU_T_OC",
    "STU_EU_S_OC",
    "STU_EU_T_BD",
    "STU_EU_S_BD",
    "STU_EU_T_GRAVEL",
    "STU_EU_S_GRAVEL",
)
HYDRO_SCREEN_DATASET = "KS"
HYDRO_SCREEN_DEPTHS = ("sl1", "sl2", "sl3", "sl4", "sl5", "sl6", "sl7")


def _sample_pixel_indices(
    width: int,
    height: int,
    sample_count: int,
    *,
    seed: int,
    strata: tuple[int, int] = DEFAULT_STRATA,
    valid_cells_by_stratum: dict[int, list[tuple[int, int]]] | None = None,
) -> list[tuple[int, int]]:
    """Return deterministic, unique pixel indices distributed across strata."""
    if width < 1 or height < 1:
        raise ValueError(f"Raster dimensions must be positive, got {width}x{height}.")
    if sample_count < 1:
        raise ValueError(f"sample_count must be positive, got {sample_count}.")
    if sample_count > width * height:
        raise ValueError(
            f"Cannot draw {sample_count} unique pixels from {width * height} cells."
        )

    strata_rows, strata_cols = strata
    if not (1 <= strata_rows <= height and 1 <= strata_cols <= width):
        raise ValueError(
            f"Strata {strata_rows}x{strata_cols} do not fit raster {width}x{height}."
        )

    rng = random.Random(seed)
    all_stratum_indices = range(strata_rows * strata_cols)
    if valid_cells_by_stratum is None:
        sample_stratum_indices = list(all_stratum_indices)
    else:
        sample_stratum_indices = [
            stratum_index
            for stratum_index in all_stratum_indices
            if valid_cells_by_stratum.get(stratum_index)
        ]
        if not sample_stratum_indices:
            raise ValueError("No valid cells are available in any sampling stratum.")
        valid_cell_count = sum(
            len(valid_cells_by_stratum[stratum_index])
            for stratum_index in sample_stratum_indices
        )
        if sample_count > valid_cell_count:
            raise ValueError(
                f"Cannot draw {sample_count} unique valid pixels from "
                f"{valid_cell_count} cells."
            )

    stratum_count = len(sample_stratum_indices)
    if valid_cells_by_stratum is None:
        base_count, remainder = divmod(sample_count, stratum_count)
        draw_counts = {
            stratum_index: base_count + (sample_stratum_index < remainder)
            for sample_stratum_index, stratum_index in enumerate(sample_stratum_indices)
        }
    else:
        # Allocate one cell per non-empty stratum in repeated passes. This keeps
        # the sample spatially broad while allowing edge strata to have fewer
        # valid cells than the nominal even allocation.
        draw_counts = {stratum_index: 0 for stratum_index in sample_stratum_indices}
        remaining = sample_count
        while remaining:
            progressed = False
            for stratum_index in sample_stratum_indices:
                if draw_counts[stratum_index] >= len(
                    valid_cells_by_stratum[stratum_index]
                ):
                    continue
                draw_counts[stratum_index] += 1
                remaining -= 1
                progressed = True
                if not remaining:
                    break
            if not progressed:
                raise ValueError("Unable to allocate the requested valid pixels.")

    samples: list[tuple[int, int]] = []

    for sample_stratum_index, stratum_index in enumerate(sample_stratum_indices):
        row_stratum, col_stratum = divmod(stratum_index, strata_cols)
        row_start = (row_stratum * height) // strata_rows
        row_stop = ((row_stratum + 1) * height) // strata_rows
        col_start = (col_stratum * width) // strata_cols
        col_stop = ((col_stratum + 1) * width) // strata_cols
        if valid_cells_by_stratum is None:
            cells = [
                (row, col)
                for row in range(row_start, row_stop)
                for col in range(col_start, col_stop)
            ]
        else:
            cells = valid_cells_by_stratum.get(stratum_index, [])
        draw_count = draw_counts[stratum_index]
        if draw_count > len(cells):
            raise ValueError(
                f"Stratum {stratum_index} has {len(cells)} cells but needs {draw_count}."
            )
        samples.extend(rng.sample(cells, draw_count))

    return samples


def _manifest_path(output: Path) -> Path:
    return output if output.suffix.lower() == ".json" else output / "manifest.json"


def build_manifest(
    *,
    sample_count: int,
    seed: int,
    output: Path,
    anchor_attribute: str = DEFAULT_ANCHOR_ATTRIBUTE,
    strata: tuple[int, int] = DEFAULT_STRATA,
    force: bool = False,
) -> Path:
    """Build a coordinate manifest from the installed ESDAC anchor raster."""
    from wepppy.all_your_base.geo import RasterDatasetInterpolator
    from wepppy.eu.soils.esdac import ESDAC

    esdac = ESDAC()
    try:
        anchor_path = esdac.catalog[anchor_attribute]
    except KeyError as exc:
        raise FileNotFoundError(
            f"ESDAC anchor raster {anchor_attribute!r} is not catalogued. "
            "Install the matching ESDAC rasters before running this search."
        ) from exc

    raster = RasterDatasetInterpolator(anchor_path)
    import numpy as np

    anchor_array = raster.band[0].ReadAsArray()
    nodata = raster.no_data_values[0]
    valid_mask = np.isfinite(anchor_array)
    if nodata is not None:
        valid_mask &= anchor_array != nodata

    strata_rows, strata_cols = strata
    valid_cells_by_stratum: dict[int, list[tuple[int, int]]] = {}
    for stratum_index in range(strata_rows * strata_cols):
        row_stratum, col_stratum = divmod(stratum_index, strata_cols)
        row_start = (row_stratum * raster.height) // strata_rows
        row_stop = ((row_stratum + 1) * raster.height) // strata_rows
        col_start = (col_stratum * raster.width) // strata_cols
        col_stop = ((col_stratum + 1) * raster.width) // strata_cols
        rows, cols = np.where(valid_mask[row_start:row_stop, col_start:col_stop])
        valid_cells_by_stratum[stratum_index] = [
            (int(row + row_start), int(col + col_start))
            for row, col in zip(rows, cols)
        ]

    pixel_indices = _sample_pixel_indices(
        raster.width,
        raster.height,
        sample_count,
        seed=seed,
        strata=strata,
        valid_cells_by_stratum=valid_cells_by_stratum,
    )

    samples: list[dict[str, Any]] = []
    for sample_id, (row, col) in enumerate(pixel_indices):
        easting, northing = raster.get_geo_coord(col + 0.5, row + 0.5)
        lng, lat = raster.proj2wgs_transformer.transform(easting, northing)
        samples.append(
            {
                "sample_id": sample_id,
                "row": row,
                "col": col,
                "lng": float(lng),
                "lat": float(lat),
            }
        )

    manifest = {
        "schema_version": 1,
        "campaign": "eu-invalid-soil-search",
        "sampling": {
            "seed": seed,
            "sample_count": sample_count,
            "strata": {"rows": strata[0], "cols": strata[1]},
            "unique_pixels": True,
            "valid_anchor_pixels_only": True,
        },
        "source": {
            "anchor_attribute": anchor_attribute,
            "anchor_raster": str(anchor_path),
            "width": raster.width,
            "height": raster.height,
            "nodata": nodata,
            "valid_anchor_pixels": int(valid_mask.sum()),
            "projection": raster.wkt_text,
            "geotransform": list(raster.transform),
        },
        "samples": samples,
    }

    manifest_path = _manifest_path(output)
    if manifest_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {manifest_path}; pass --force to replace it."
        )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


class _CachedRasterSampler:
    """Sample the same source fields as the builder without reopening rasters."""

    def __init__(self, esdac: Any) -> None:
        from wepppy.all_your_base.geo import RasterDatasetInterpolator
        from wepppy.eu.soils.esdac.esdac import _attr_fmt

        self._attr_fmt = _attr_fmt
        self._esdac = esdac
        self._categorical = {
            attr: RasterDatasetInterpolator(esdac.catalog[_attr_fmt(attr)])
            for attr in ESDB_SCREEN_ATTRIBUTES
        }
        self._continuous = {
            attr: RasterDatasetInterpolator(esdac.derived_db_catalog[attr])
            for attr in STU_SCREEN_ATTRIBUTES
        }
        self._hydro = {
            depth: RasterDatasetInterpolator(
                esdac_hydro_path(dataset=HYDRO_SCREEN_DATASET, depth=depth)
            )
            for depth in HYDRO_SCREEN_DEPTHS
        }

    @staticmethod
    def _cell_value(raster: Any, row: int, col: int) -> Any:
        if not (0 <= row < raster.height and 0 <= col < raster.width):
            return None
        value = raster.band[0].ReadAsArray(col, row, 1, 1)
        if value is None:
            return None
        scalar = value[0, 0]
        nodata = raster.no_data_values[0]
        if nodata is not None and scalar == nodata:
            return None
        return scalar

    def _pixel_for(
        self,
        raster: Any,
        row: int,
        col: int,
        lng: float,
        lat: float,
    ) -> tuple[int, int]:
        anchor = self._categorical[ESDB_SCREEN_ATTRIBUTES[0]]
        if (
            raster.width == anchor.width
            and raster.height == anchor.height
            and raster.transform == anchor.transform
        ):
            return row, col
        px, py = raster.get_px_coord_from_lnglat(lng, lat)
        return int(round(py)), int(round(px))

    def categorical_values(
        self,
        row: int,
        col: int,
        lng: float,
        lat: float,
    ) -> dict[str, dict[str, str | None]]:
        from wepppy.eu.soils.esdac.legends import get_legend

        values: dict[str, dict[str, str | None]] = {}
        for attr, raster in self._categorical.items():
            normalized = self._attr_fmt(attr)
            px_row, px_col = self._pixel_for(raster, row, col, lng, lat)
            value = self._cell_value(raster, px_row, px_col)
            if value is None:
                values[attr] = {"px": None, "short": None, "long": None}
                continue
            px = str(int(value))
            short = self._esdac.rats[normalized][px]
            long = get_legend(normalized)["table"].get(short, "None")
            values[attr] = {"px": px, "short": short, "long": str(long)}
        return values

    def continuous_values(
        self,
        row: int,
        col: int,
        lng: float,
        lat: float,
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {}
        for attr, raster in self._continuous.items():
            px_row, px_col = self._pixel_for(raster, row, col, lng, lat)
            value = self._cell_value(raster, px_row, px_col)
            values[attr] = None if value is None else float(value)
        return values

    def hydro_values(
        self,
        row: int,
        col: int,
        lng: float,
        lat: float,
    ) -> dict[str, float | None]:
        values: dict[str, float | None] = {}
        for depth, raster in self._hydro.items():
            px_row, px_col = self._pixel_for(raster, row, col, lng, lat)
            value = self._cell_value(raster, px_row, px_col)
            values[depth] = None if value is None else float(value)
        return values


def esdac_hydro_path(*, dataset: str, depth: str) -> str:
    from wepppy.eu.soils.eusoilhydrogrids.eusoilhydrogrids import SoilHydroGrids

    return SoilHydroGrids.get_fn(dataset, depth)


def _screen_source(
    sampler: _CachedRasterSampler,
    sample: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Capture raw builder inputs and mark suspicious values for full builds."""
    row = sample["row"]
    col = sample["col"]
    source: dict[str, Any] = {"esdb": {}, "stu": {}, "hydrogrids": {}}
    issues: list[str] = []

    try:
        source["esdb"] = sampler.categorical_values(row, col, sample["lng"], sample["lat"])
    except (KeyError, TypeError, ValueError, OverflowError, RuntimeError) as exc:
        for attr in ESDB_SCREEN_ATTRIBUTES:
            source["esdb"][attr] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            issues.append(f"esdb.{attr}.read_error")

    for attr in ESDB_SCREEN_ATTRIBUTES:
        value = source["esdb"][attr]
        if "error_type" in value:
            continue
        if value["px"] is None or value["short"] in {"0", "9"}:
            issues.append(f"esdb.{attr}.no_information")
        if attr in {"cec_top", "cec_sub"} and value["short"] not in {
            "H",
            "M",
            "L",
        }:
            issues.append(f"esdb.{attr}.invalid_class")
        if attr in {"textdepchg", "il"} and value["short"] == "0":
            issues.append(f"esdb.{attr}.missing_depth_class")
    try:
        source["stu"] = sampler.continuous_values(row, col, sample["lng"], sample["lat"])
    except (KeyError, TypeError, ValueError, OverflowError, RuntimeError) as exc:
        for attr in STU_SCREEN_ATTRIBUTES:
            source["stu"][attr] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            issues.append(f"stu.{attr}.read_error")

    for attr in STU_SCREEN_ATTRIBUTES:
        value = source["stu"][attr]
        if isinstance(value, dict):
            continue
        if value is None:
            issues.append(f"stu.{attr}.missing")
        elif not math.isfinite(value):
            issues.append(f"stu.{attr}.nonfinite")
        elif value == 0:
            issues.append(f"stu.{attr}.zero_observed")
        elif value < 0:
            issues.append(f"stu.{attr}.negative")
    top_texture = [source["stu"].get(f"STU_EU_T_{name}") for name in ("CLAY", "SAND", "SILT")]
    sub_texture = [source["stu"].get(f"STU_EU_S_{name}") for name in ("CLAY", "SAND", "SILT")]
    for horizon_name, texture in (("top", top_texture), ("sub", sub_texture)):
        if all(isinstance(value, (int, float)) and math.isfinite(value) for value in texture):
            if not 99 <= sum(texture) <= 101:
                issues.append(f"stu.{horizon_name}.texture_balance")

    try:
        source["hydrogrids"] = sampler.hydro_values(
            row, col, sample["lng"], sample["lat"]
        )
    except (KeyError, TypeError, ValueError, OverflowError, RuntimeError) as exc:
        for depth in HYDRO_SCREEN_DEPTHS:
            source["hydrogrids"][depth] = {
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            issues.append(f"hydrogrids.{depth}.read_error")

    for depth in HYDRO_SCREEN_DEPTHS:
        value = source["hydrogrids"][depth]
        if isinstance(value, dict):
            continue
        if value is None:
            issues.append(f"hydrogrids.{depth}.missing")
        elif not math.isfinite(value):
            issues.append(f"hydrogrids.{depth}.nonfinite")
        elif value == 0:
            issues.append(f"hydrogrids.{depth}.zero_observed")
        elif value < 0:
            issues.append(f"hydrogrids.{depth}.negative")
    if source["hydrogrids"] and all(
        source["hydrogrids"].get(depth) is None for depth in HYDRO_SCREEN_DEPTHS
    ):
        issues.append("hydrogrids.profile.all_missing")

    return source, sorted(set(issues))


def _inspect_sol(path: Path) -> list[str]:
    """Check generated horizon rows for finite, positive, ordered depths."""
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        tokens = line.split()
        if len(tokens) != 11:
            continue
        try:
            values = [float(token) for token in tokens]
        except ValueError:
            continue
        if all(math.isfinite(value) for value in values):
            rows.append(values)

    issues: list[str] = []
    depths = [row[0] for row in rows]
    if not rows:
        issues.append("sol.no_horizon_rows")
    elif any(depth <= 0 for depth in depths):
        issues.append("sol.nonpositive_horizon_depth")
    elif any(next_depth <= depth for depth, next_depth in zip(depths, depths[1:])):
        issues.append("sol.horizon_depth_order")
    return issues


def _horizon_payload(horizon: Any) -> dict[str, Any]:
    """Capture stable Horizon fields without depending on its broken serializer."""
    fields = (
        "clay",
        "sand",
        "silt",
        "om",
        "bd",
        "gravel",
        "depth",
        "conductivity",
        "anisotropy",
        "interrill",
        "rill",
        "shear",
        "ks",
        "field_capacity",
    )
    payload: dict[str, Any] = {}
    for field in fields:
        try:
            value = getattr(horizon, field)
        except (AttributeError, ValueError):
            payload[field] = None
            continue
        payload[field] = None if value is None else float(value)
    return payload


def _build_record(record: dict[str, Any], build_root: Path) -> tuple[int, dict[str, Any]]:
    """Build one targeted case; this is an intentional diagnostic boundary."""
    from wepppy.eu.soils.esdac import ESDAC

    case_dir = build_root / f"sample-{record['sample_id']:06d}"
    case_dir.mkdir(parents=True, exist_ok=True)
    try:
        key, horizon, description = ESDAC().build_wepp_soil(
            record["lng"], record["lat"], str(case_dir)
        )
        sol_path = case_dir / f"{key}.sol"
        return record["sample_id"], {
            "status": "built",
            "key": key,
            "description": description,
            "sol_path": str(sol_path),
            "horizon": _horizon_payload(horizon),
            "output_issues": _inspect_sol(sol_path),
        }
    except Exception as exc:  # retain arbitrary builder failures as evidence
        return record["sample_id"], {
            "status": "exception",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def screen_manifest(
    manifest_path: Path,
    output: Path,
    *,
    control_count: int = 20,
    build_workers: int = 8,
) -> Path:
    """Screen a manifest, then build suspicious samples and valid controls."""
    from wepppy.eu.soils.esdac import ESDAC

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    esdac = ESDAC()
    sampler = _CachedRasterSampler(esdac)
    records: list[dict[str, Any]] = []
    for sample in manifest["samples"]:
        source, issues = _screen_source(sampler, sample)
        records.append(
            {
                **sample,
                "source": source,
                "screen_issues": issues,
                "screen_status": "suspicious" if issues else "control_candidate",
            }
        )

    controls = [record for record in records if not record["screen_issues"]][:control_count]
    targets = [record for record in records if record["screen_issues"]]
    target_ids = {record["sample_id"] for record in targets}
    target_ids.update(record["sample_id"] for record in controls)
    build_root = output / "builds"
    build_root.mkdir(parents=True, exist_ok=True)

    targets = [record for record in records if record["sample_id"] in target_ids]
    if build_workers < 0:
        raise ValueError(f"build_workers must be nonnegative, got {build_workers}.")
    if build_workers:
        with ProcessPoolExecutor(max_workers=build_workers) as executor:
            futures = [
                executor.submit(_build_record, record, build_root) for record in targets
            ]
            results = [future.result() for future in futures]
    else:
        results = []
    records_by_id = {record["sample_id"]: record for record in records}
    for sample_id, builder in results:
        records_by_id[sample_id]["builder"] = builder

    output.mkdir(parents=True, exist_ok=True)
    screen_path = output / "screen.json"
    summary = {
        "sample_count": len(records),
        "suspicious_count": len(targets),
        "control_count": len(controls),
        "built_count": sum(
            record.get("builder", {}).get("status") == "built" for record in records
        ),
        "builder_exception_count": sum(
            record.get("builder", {}).get("status") == "exception" for record in records
        ),
        "output_issue_count": sum(
            bool(record.get("builder", {}).get("output_issues")) for record in records
        ),
    }
    screen = {
        "schema_version": 1,
        "campaign": manifest["campaign"],
        "manifest": str(manifest_path),
        "sampling_mode": "recorded_raster_cell_indices",
        "summary": summary,
        "records": records,
    }
    screen_path.write_text(
        json.dumps(screen, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return screen_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--screen-manifest", type=Path)
    mode.add_argument("--pilot", type=int, help="Generate a pilot manifest.")
    mode.add_argument("--samples", type=int, help="Generate a full manifest.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--anchor-attribute", default=DEFAULT_ANCHOR_ATTRIBUTE)
    parser.add_argument("--strata-rows", type=int, default=DEFAULT_STRATA[0])
    parser.add_argument("--strata-cols", type=int, default=DEFAULT_STRATA[1])
    parser.add_argument("--controls", type=int, default=20)
    parser.add_argument("--build-workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.screen_manifest is not None:
        screen_path = screen_manifest(
            args.screen_manifest,
            args.output,
            control_count=args.controls,
            build_workers=args.build_workers,
        )
        print(f"Wrote source screen and targeted builds to {screen_path}")
        return 0

    sample_count = args.pilot if args.pilot is not None else args.samples
    assert sample_count is not None
    manifest_path = build_manifest(
        sample_count=sample_count,
        seed=args.seed,
        output=args.output,
        anchor_attribute=args.anchor_attribute,
        strata=(args.strata_rows, args.strata_cols),
        force=args.force,
    )
    print(f"Wrote {sample_count} samples to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
