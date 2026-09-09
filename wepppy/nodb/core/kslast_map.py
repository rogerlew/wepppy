"""Project-grid kslast preparation shared by ordinary and MOFE soil prep.

Policy authority: docs/schemas/kslast-map-contract.md. This collaborator writes
artifacts under the soils maintenance lock and never persists NoDb state.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

import numpy as np
import rasterio

from wepppy.all_your_base.geo import raster_stacker
from wepppy.runtime_paths.thaw_freeze import maintenance_lock

__all__ = ["prepare_kslast_map", "kslast_provenance"]


def _sha256(path: str | Path) -> str:
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def kslast_provenance(source: str, record: dict[str, Any]) -> dict[str, Any]:
    return dict(map_fn=source, aggregation="project_cell_area_mean",
                map_value=record["mean"], valid_cell_count=record["valid_cell_count"],
                missing_cell_count=record["missing_cell_count"],
                default_fraction=record["default_fraction"])


def prepare_kslast_map(wepp: Any, hillslope_keys: Iterable[str | int]) -> dict[str, Any] | None:
    """Rebuild current map/summary before workers; no-map prep consumes neither."""
    source = wepp.kslast_map
    if source is None:
        return None
    default = wepp.kslast
    if default is not None and (not math.isfinite(default) or default <= 0):
        raise ValueError("Mapped kslast default must be finite and positive")
    expected = {str(int(key)) for key in hillslope_keys}
    soil_dir = Path(wepp.wd) / "soils"
    if not soil_dir.is_dir():
        raise FileNotFoundError("Mapped kslast prep requires a soils directory; archive-only roots are retired")
    soil_dir = soil_dir.resolve(strict=True)
    if not soil_dir.is_relative_to(Path(wepp.wd).resolve(strict=True)):
        raise ValueError("kslast soils directory escapes the run root")
    grid = wepp.watershed_instance.subwta
    from wepppyo3.raster_characteristics import identify_area_weighted_mean_single_raster_key

    with maintenance_lock(wepp.wd, "soils", purpose="wepp-prep-kslast-map"):
        with tempfile.TemporaryDirectory(prefix=".kslast-", dir=soil_dir) as staging:
            mapped = Path(staging) / "kslast.tif"
            source_hash, grid_hash = _sha256(source), _sha256(grid)
            raster_stacker(source, grid, mapped, dst_nodata=float("nan"), dst_dtype="float64")
            with rasterio.open(mapped, "r+") as dataset:
                values = dataset.read(1, masked=True)
                original_missing = np.ma.getmaskarray(values)
                nonfinite = ~np.isfinite(values.data) & ~original_missing
                nonpositive = (values.data <= 0) & ~original_missing & ~nonfinite
                missing = original_missing | nonfinite | nonpositive
                normalized = values.data.copy()
                normalized[missing] = -9999.0
                dataset.nodata = -9999.0
                dataset.write(normalized, 1)
                grid_metadata = dict(crs=dataset.crs.to_wkt(), transform=list(dataset.transform)[:6],
                                     width=dataset.width, height=dataset.height, nodata=-9999.0, dtype="float64")
            with rasterio.open(grid) as key_raster:
                keys = key_raster.read(1, masked=True).compressed()
                excluded = {int(key) for key in np.unique(keys) if str(int(key)) not in expected}
            excluded.add(0)
            records = identify_area_weighted_mean_single_raster_key(
                str(grid), str(mapped), ignore_keys=excluded, default_value=default,
            )
            if set(records) != expected:
                raise ValueError(f"kslast hillslope keys mismatch: missing={sorted(expected - set(records))[:10]}, unexpected={sorted(set(records) - expected)[:10]}")
            for record in records.values():
                record["default_fraction"] = record["missing_cell_count"] / record["total_cell_count"]
                if not math.isfinite(record["mean"]) or record["mean"] <= 0:
                    raise ValueError("kslast aggregation produced invalid conductivity")
            if source_hash != _sha256(source) or grid_hash != _sha256(grid):
                raise RuntimeError("kslast source/grid changed during preparation; retry with stable inputs")
            summary = dict(schema_version=1, source=dict(path=str(source), sha256=source_hash),
                           grid=dict(path=str(grid), sha256=grid_hash, **grid_metadata),
                           map_sha256=_sha256(mapped), resampling="nearest",
                           aggregation="project_cell_area_mean", units="mm/h", default_value=default,
                           normalization=dict(source_or_uncovered_missing=int(original_missing.sum()),
                                              nonfinite=int(nonfinite.sum()), nonpositive=int(nonpositive.sum())),
                           hillslopes=records)
            summary_path = Path(staging) / "kslast_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
            # Summary is the completion marker and binds the map hash. Readers
            # must check that hash; two independent filenames cannot swap together.
            os.replace(mapped, soil_dir / "kslast.tif")
            os.replace(summary_path, soil_dir / "kslast_summary.json")
    wepp.logger.info("kslast area means: %s hillslopes; %s use missing-area default (max fraction %.6f)",
                     len(records), sum(r["missing_cell_count"] > 0 for r in records.values()),
                     max((r["default_fraction"] for r in records.values()), default=0.0))
    return records
