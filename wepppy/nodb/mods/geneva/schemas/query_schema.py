from __future__ import annotations

from typing import Any, Mapping, Sequence

GENEVA_DATASOURCE_IDS: tuple[str, ...] = ("cligen_freq", "noaa14_pds")
DEFAULT_GENEVA_DISTRIBUTION_ID = "neh4_type_b"
GENEVA_DISTRIBUTION_IDS: tuple[str, ...] = (
    DEFAULT_GENEVA_DISTRIBUTION_ID,
    "uniform",
    "type_i",
    "type_ia",
    "type_ii",
    "type_iii",
)
GENEVA_MEASURE_IDS: tuple[str, ...] = ("peak_discharge", "runoff_depth", "runoff_volume")
GENEVA_HRU_MAP_MEASURE_IDS: tuple[str, ...] = ("runoff_depth", "runoff_volume")
GENEVA_AVAILABILITY_IDS: tuple[str, ...] = ("available", "unavailable")
GENEVA_UNAVAILABLE_REASON_CODES: tuple[str, ...] = (
    "duration_unavailable",
    "ari_unavailable",
    "source_missing",
)


def validate_datasource_id(value: str) -> str:
    normalized = str(value).strip()
    if normalized not in GENEVA_DATASOURCE_IDS:
        raise ValueError(
            f"datasource_id must be one of: {', '.join(GENEVA_DATASOURCE_IDS)}"
        )
    return normalized


def validate_measure_id(value: str) -> str:
    normalized = str(value).strip()
    if normalized not in GENEVA_MEASURE_IDS:
        raise ValueError(
            f"measure must be one of: {', '.join(GENEVA_MEASURE_IDS)}"
        )
    return normalized


def validate_hru_map_measure_id(value: str) -> str:
    normalized = str(value).strip()
    if normalized not in GENEVA_HRU_MAP_MEASURE_IDS:
        raise ValueError(
            f"measure_id must be one of: {', '.join(GENEVA_HRU_MAP_MEASURE_IDS)}"
        )
    return normalized


def validate_distribution_type(value: str | None) -> str:
    normalized = str(value or DEFAULT_GENEVA_DISTRIBUTION_ID).strip()
    if not normalized:
        normalized = DEFAULT_GENEVA_DISTRIBUTION_ID
    if normalized not in GENEVA_DISTRIBUTION_IDS:
        raise ValueError(
            f"distribution_type must be one of: {', '.join(GENEVA_DISTRIBUTION_IDS)}"
        )
    return normalized


def normalize_frequency_panel_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    schema_version = int(
        payload.get("schema_version")
        or payload.get("kernel_schema_version")
        or 1
    )
    distribution_type = validate_distribution_type(payload.get("distribution_type"))

    datasource_ids = _normalize_datasource_ids(payload.get("datasource_ids"))
    durations_minutes = _normalize_positive_int_list(
        payload.get("durations_minutes"),
        field="durations_minutes",
    )
    ari_years = _normalize_positive_int_list(
        payload.get("ari_years"),
        field="ari_years",
    )

    raw_cells = payload.get("cells")
    if not isinstance(raw_cells, list):
        raise ValueError("cells must be a list")

    cells: list[dict[str, Any]] = []
    for raw in raw_cells:
        if not isinstance(raw, Mapping):
            raise ValueError("cells entries must be objects")

        datasource_id = validate_datasource_id(raw.get("datasource_id", ""))
        availability = str(raw.get("availability") or "").strip()
        if availability not in GENEVA_AVAILABILITY_IDS:
            raise ValueError(
                f"availability must be one of: {', '.join(GENEVA_AVAILABILITY_IDS)}"
            )

        reason_value = raw.get("reason_code")
        reason_code = _normalize_reason_code(reason_value)
        if availability == "available":
            if reason_code is not None:
                raise ValueError("reason_code must be null when availability=available")
        elif reason_code not in GENEVA_UNAVAILABLE_REASON_CODES:
            raise ValueError(
                "reason_code must be one of duration_unavailable, ari_unavailable, source_missing "
                "when availability=unavailable"
            )

        depth_mm = _normalize_optional_float(raw.get("depth_mm"), field="depth_mm")
        intensity_mm_per_hr = _normalize_optional_float(
            raw.get("intensity_mm_per_hr"),
            field="intensity_mm_per_hr",
        )

        if availability == "available" and (depth_mm is None or intensity_mm_per_hr is None):
            raise ValueError("available cells must include depth_mm and intensity_mm_per_hr")
        if availability == "available" and (
            depth_mm is not None and depth_mm <= 0.0
            or intensity_mm_per_hr is not None and intensity_mm_per_hr <= 0.0
        ):
            raise ValueError(
                "available cells must include positive depth_mm and intensity_mm_per_hr"
            )

        cell_distribution = validate_distribution_type(raw.get("distribution_type") or distribution_type)

        cells.append(
            {
                "storm_id": str(raw.get("storm_id", "")).strip(),
                "datasource_id": datasource_id,
                "duration_minutes": _normalize_positive_int(raw.get("duration_minutes"), field="duration_minutes"),
                "ari_years": _normalize_positive_int(raw.get("ari_years"), field="ari_years"),
                "depth_mm": depth_mm,
                "intensity_mm_per_hr": intensity_mm_per_hr,
                "distribution_type": cell_distribution,
                "availability": availability,
                "reason_code": reason_code,
            }
        )

    cells.sort(
        key=lambda row: (
            row["datasource_id"],
            row["duration_minutes"],
            row["ari_years"],
            row["storm_id"],
        )
    )

    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        warnings = []

    return {
        "schema_version": schema_version,
        "datasource_ids": datasource_ids,
        "durations_minutes": durations_minutes,
        "ari_years": ari_years,
        "distribution_type": distribution_type,
        "cells": cells,
        "warnings": warnings,
    }


def _normalize_datasource_ids(value: Any) -> list[str]:
    if value in (None, ""):
        return list(GENEVA_DATASOURCE_IDS)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("datasource_ids must be a list")
    normalized = [validate_datasource_id(item) for item in value]
    seen: set[str] = set()
    deduped: list[str] = []
    for item in normalized:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _normalize_positive_int_list(value: Any, *, field: str) -> list[int]:
    if value in (None, ""):
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{field} must be a list")
    return [_normalize_positive_int(item, field=field) for item in value]


def _normalize_positive_int(value: Any, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} values must be integers") from exc
    if parsed <= 0:
        raise ValueError(f"{field} values must be positive")
    return parsed


def _normalize_optional_float(value: Any, *, field: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric when provided") from exc


def _normalize_reason_code(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text == "null":
        raise ValueError('reason_code must be null, not string "null"')
    return text


__all__ = [
    "GENEVA_DATASOURCE_IDS",
    "DEFAULT_GENEVA_DISTRIBUTION_ID",
    "GENEVA_DISTRIBUTION_IDS",
    "GENEVA_MEASURE_IDS",
    "GENEVA_HRU_MAP_MEASURE_IDS",
    "GENEVA_AVAILABILITY_IDS",
    "GENEVA_UNAVAILABLE_REASON_CODES",
    "validate_datasource_id",
    "validate_distribution_type",
    "validate_measure_id",
    "validate_hru_map_measure_id",
    "normalize_frequency_panel_payload",
]
