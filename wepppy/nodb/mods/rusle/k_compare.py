"""Sanity comparison helpers for POLARIS K estimators vs benchmark values."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping

import numpy as np


__all__ = [
    "ComparisonThresholds",
    "compare_k_modes_to_reference",
    "write_comparison_summary_json",
]


@dataclass(frozen=True)
class ComparisonThresholds:
    abs_error_warn: float = 0.10
    rel_error_warn: float = 0.35


def _finite_value(value: Any) -> float | None:
    if value is None:
        return None
    candidate = float(value)
    if not np.isfinite(candidate):
        return None
    return candidate


def _build_value_map(samples: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for sample in samples:
        if bool(sample.get("is_nodata", False)):
            continue
        point_id = str(sample["point_id"])
        value = _finite_value(sample.get("value"))
        if value is None:
            continue
        values[point_id] = value
    return values


def _metrics(model: np.ndarray, reference: np.ndarray) -> dict[str, float | None]:
    if model.size == 0:
        return {
            "count": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "pearson_r": None,
        }

    errors = model - reference
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    bias = float(np.mean(errors))

    if model.size < 2:
        pearson_r = None
    else:
        reference_std = float(np.std(reference))
        model_std = float(np.std(model))
        if np.isclose(reference_std, 0.0) or np.isclose(model_std, 0.0):
            pearson_r = None
        else:
            pearson_r = float(np.corrcoef(reference, model)[0, 1])

    return {
        "count": int(model.size),
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "pearson_r": pearson_r,
    }


def _compare_mode(
    *,
    mode_name: str,
    mode_values: Mapping[str, float],
    reference_values: Mapping[str, float],
    thresholds: ComparisonThresholds,
) -> dict[str, Any]:
    common_ids = sorted(set(reference_values).intersection(mode_values))

    reference = np.asarray([reference_values[point_id] for point_id in common_ids], dtype=np.float64)
    model = np.asarray([mode_values[point_id] for point_id in common_ids], dtype=np.float64)

    metrics = _metrics(model, reference)

    per_point: list[dict[str, Any]] = []
    flagged: list[str] = []
    for point_id in common_ids:
        ref = reference_values[point_id]
        mod = mode_values[point_id]
        abs_error = abs(mod - ref)
        rel_error = abs_error / max(abs(ref), 1.0e-9)
        is_flagged = abs_error > thresholds.abs_error_warn or rel_error > thresholds.rel_error_warn
        if is_flagged:
            flagged.append(point_id)

        per_point.append(
            {
                "point_id": point_id,
                "mode": mode_name,
                "reference": ref,
                "model": mod,
                "abs_error": abs_error,
                "rel_error": rel_error,
                "flagged": is_flagged,
            }
        )

    return {
        "metrics": metrics,
        "flagged_point_ids": flagged,
        "per_point": per_point,
    }


def compare_k_modes_to_reference(
    *,
    reference_samples: Iterable[Mapping[str, Any]],
    nomograph_samples: Iterable[Mapping[str, Any]],
    epic_samples: Iterable[Mapping[str, Any]],
    thresholds: ComparisonThresholds = ComparisonThresholds(),
) -> dict[str, Any]:
    """Compare POLARIS K estimator samples against reference samples."""
    reference_values = _build_value_map(reference_samples)
    nomograph_values = _build_value_map(nomograph_samples)
    epic_values = _build_value_map(epic_samples)

    nomograph_result = _compare_mode(
        mode_name="polaris_nomograph",
        mode_values=nomograph_values,
        reference_values=reference_values,
        thresholds=thresholds,
    )
    epic_result = _compare_mode(
        mode_name="polaris_epic",
        mode_values=epic_values,
        reference_values=reference_values,
        thresholds=thresholds,
    )

    return {
        "thresholds": {
            "abs_error_warn": thresholds.abs_error_warn,
            "rel_error_warn": thresholds.rel_error_warn,
        },
        "reference_point_count": len(reference_values),
        "modes": {
            "polaris_nomograph": nomograph_result,
            "polaris_epic": epic_result,
        },
    }


def write_comparison_summary_json(path: str, payload: Mapping[str, Any]) -> None:
    """Write comparison summary payload to JSON."""
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
