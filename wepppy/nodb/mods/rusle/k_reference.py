"""Reference-harness helpers for benchmark K sampling."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from os.path import exists as _exists
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform


REFERENCE_MODES: tuple[str, ...] = (
    "gnatsgo_kffact",
    "gnatsgo_kwfact",
    "gssurgo_kffact",
    "gssurgo_kwfact",
)

DEFAULT_REFERENCE_MODE_PRECEDENCE: tuple[str, ...] = (
    "gssurgo_kffact",
    "gnatsgo_kffact",
    "gssurgo_kwfact",
    "gnatsgo_kwfact",
)


__all__ = [
    "REFERENCE_MODES",
    "DEFAULT_REFERENCE_MODE_PRECEDENCE",
    "ReferencePoint",
    "ReferenceSample",
    "validate_reference_mode",
    "resolve_reference_mode",
    "sample_points_from_raster",
    "sample_reference_k_points",
    "run_reference_harness",
    "write_reference_samples_json",
]


@dataclass(frozen=True)
class ReferencePoint:
    point_id: str
    x: float
    y: float


@dataclass(frozen=True)
class ReferenceSample:
    point_id: str
    x: float
    y: float
    value: float | None
    is_nodata: bool
    mode: str


def validate_reference_mode(mode: str) -> str:
    token = str(mode).strip().lower()
    if token not in REFERENCE_MODES:
        raise ValueError(f"Unsupported reference mode '{mode}'. Expected one of: {REFERENCE_MODES}")
    return token


def resolve_reference_mode(
    reference_paths: Mapping[str, str],
    *,
    precedence: Sequence[str] = DEFAULT_REFERENCE_MODE_PRECEDENCE,
) -> tuple[str, str]:
    """Return the first existing reference mode path based on precedence."""
    normalized: dict[str, str] = {str(k).strip().lower(): str(v) for k, v in reference_paths.items()}
    for mode in precedence:
        candidate = normalized.get(mode)
        if candidate and _exists(candidate):
            return mode, candidate
    raise FileNotFoundError(
        "No benchmark raster found for configured precedence. "
        f"Checked modes: {tuple(precedence)}"
    )


def _normalize_points(points: Iterable[ReferencePoint | Mapping[str, Any] | Sequence[Any]]) -> list[ReferencePoint]:
    normalized: list[ReferencePoint] = []
    for idx, point in enumerate(points):
        if isinstance(point, ReferencePoint):
            normalized.append(point)
            continue

        if isinstance(point, Mapping):
            point_id = str(point.get("point_id", f"point_{idx}"))
            x = float(point["x"])
            y = float(point["y"])
            normalized.append(ReferencePoint(point_id=point_id, x=x, y=y))
            continue

        if isinstance(point, Sequence) and len(point) >= 2:
            x = float(point[0])
            y = float(point[1])
            point_id = str(point[2]) if len(point) > 2 else f"point_{idx}"
            normalized.append(ReferencePoint(point_id=point_id, x=x, y=y))
            continue

        raise TypeError(f"Unsupported point format at index {idx}: {type(point).__name__}")

    if not normalized:
        raise ValueError("Reference harness requires at least one point.")
    return normalized


def sample_points_from_raster(
    raster_path: str,
    points: Iterable[ReferencePoint | Mapping[str, Any] | Sequence[Any]],
    *,
    mode: str,
    point_crs: str = "EPSG:4326",
) -> list[ReferenceSample]:
    """Sample raster values at point locations and return normalized records."""
    if not _exists(raster_path):
        raise FileNotFoundError(f"Reference raster does not exist: {raster_path}")

    mode_token = str(mode).strip().lower()
    normalized_points = _normalize_points(points)

    with rasterio.open(raster_path) as dataset:
        if dataset.count < 1:
            raise ValueError(f"Raster has no bands: {raster_path}")

        coords_x = [point.x for point in normalized_points]
        coords_y = [point.y for point in normalized_points]

        if point_crs and dataset.crs and str(dataset.crs).upper() != str(point_crs).upper():
            tx_x, tx_y = rio_transform(point_crs, dataset.crs, coords_x, coords_y)
        else:
            tx_x, tx_y = coords_x, coords_y

        values = list(dataset.sample(zip(tx_x, tx_y), indexes=1))

        nodata_value = dataset.nodata
        samples: list[ReferenceSample] = []
        for point, sampled in zip(normalized_points, values):
            value = float(sampled[0]) if len(sampled) else np.nan
            is_nodata = False
            if not np.isfinite(value):
                is_nodata = True
            elif nodata_value is not None and np.isclose(value, float(nodata_value), equal_nan=True):
                is_nodata = True

            samples.append(
                ReferenceSample(
                    point_id=point.point_id,
                    x=point.x,
                    y=point.y,
                    value=None if is_nodata else value,
                    is_nodata=is_nodata,
                    mode=mode_token,
                )
            )

    return samples


def sample_reference_k_points(
    *,
    mode: str,
    reference_raster: str,
    points: Iterable[ReferencePoint | Mapping[str, Any] | Sequence[Any]],
    point_crs: str = "EPSG:4326",
) -> list[ReferenceSample]:
    """Sample one benchmark K raster mode at reference points."""
    mode_token = validate_reference_mode(mode)
    return sample_points_from_raster(reference_raster, points, mode=mode_token, point_crs=point_crs)


def run_reference_harness(
    *,
    reference_paths: Mapping[str, str],
    points: Iterable[ReferencePoint | Mapping[str, Any] | Sequence[Any]],
    point_crs: str = "EPSG:4326",
    precedence: Sequence[str] = DEFAULT_REFERENCE_MODE_PRECEDENCE,
) -> dict[str, Any]:
    """Resolve the benchmark mode and sample point values."""
    mode, raster_path = resolve_reference_mode(reference_paths, precedence=precedence)
    samples = sample_reference_k_points(
        mode=mode,
        reference_raster=raster_path,
        points=points,
        point_crs=point_crs,
    )
    return {
        "mode": mode,
        "raster_path": raster_path,
        "point_crs": point_crs,
        "samples": [asdict(sample) for sample in samples],
    }


def write_reference_samples_json(path: str, payload: Mapping[str, Any]) -> None:
    """Write the harness output payload to JSON."""
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
