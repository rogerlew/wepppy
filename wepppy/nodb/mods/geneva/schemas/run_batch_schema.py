from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .query_schema import DEFAULT_GENEVA_DISTRIBUTION_ID, validate_datasource_id, validate_distribution_type

RUN_BATCH_SCHEMA_VERSION = 1
_ALLOWED_TIMING_METHODS = {"kirpich", "kent", "simas"}
_ALLOWED_LAMBDA_MODES = {"0.20", "0.05"}
_ALLOWED_UH_METHODS = {"scs_triangular", "scs_curvilinear"}


@dataclass(frozen=True)
class GenevaEventFilter:
    datasource_ids: tuple[str, ...] = ()
    durations_minutes: tuple[int, ...] = ()
    ari_years: tuple[int, ...] = ()


@dataclass(frozen=True)
class GenevaHyetographConfig:
    distribution_type: str = DEFAULT_GENEVA_DISTRIBUTION_ID
    time_step_minutes: float = 1.0


@dataclass(frozen=True)
class GenevaRunoffModelConfig:
    lambda_mode: str
    uh_method: str
    timing_method: str | None = None
    tc_hours: float | None = None


@dataclass(frozen=True)
class GenevaRunBatchRequest:
    schema_version: int
    batch_id: str | None
    event_filter: GenevaEventFilter
    hyetograph: GenevaHyetographConfig
    runoff_model: GenevaRunoffModelConfig


def parse_run_batch_request(
    payload: Mapping[str, Any],
    *,
    default_lambda_mode: str,
    default_uh_method: str,
) -> GenevaRunBatchRequest:
    schema_version = int(payload.get("schema_version", RUN_BATCH_SCHEMA_VERSION))
    if schema_version != RUN_BATCH_SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {RUN_BATCH_SCHEMA_VERSION}")

    event_filter_payload = payload.get("event_filter") or {}
    event_filter = GenevaEventFilter(
        datasource_ids=_coerce_str_tuple(event_filter_payload.get("datasource_ids")),
        durations_minutes=_coerce_int_tuple(event_filter_payload.get("durations_minutes")),
        ari_years=_coerce_int_tuple(event_filter_payload.get("ari_years")),
    )

    hyetograph_payload = payload.get("hyetograph") or {}
    hyetograph = GenevaHyetographConfig(
        distribution_type=validate_distribution_type(hyetograph_payload.get("distribution_type")),
        time_step_minutes=_coerce_float(
            hyetograph_payload.get("time_step_minutes", 1.0),
            field="hyetograph.time_step_minutes",
        ),
    )
    if hyetograph.time_step_minutes <= 0.0:
        raise ValueError("hyetograph.time_step_minutes must be > 0")

    runoff_payload = payload.get("runoff_model") or {}
    lambda_mode = str(runoff_payload.get("lambda_mode", default_lambda_mode))
    uh_method = str(runoff_payload.get("uh_method", default_uh_method))
    timing_method_raw = runoff_payload.get("timing_method")
    timing_method = str(timing_method_raw) if timing_method_raw not in (None, "") else None
    tc_hours_raw = runoff_payload.get("tc_hours")
    tc_hours = (
        _coerce_float(tc_hours_raw, field="runoff_model.tc_hours")
        if tc_hours_raw not in (None, "")
        else None
    )

    if lambda_mode not in _ALLOWED_LAMBDA_MODES:
        raise ValueError("runoff_model.lambda_mode must be one of 0.20 or 0.05")
    if uh_method not in _ALLOWED_UH_METHODS:
        raise ValueError(
            "runoff_model.uh_method must be one of scs_triangular or scs_curvilinear"
        )
    if timing_method is not None and timing_method not in _ALLOWED_TIMING_METHODS:
        raise ValueError(
            "runoff_model.timing_method must be one of kirpich, kent, simas"
        )

    if (timing_method is None and tc_hours is None) or (
        timing_method is not None and tc_hours is not None
    ):
        raise ValueError(
            "Exactly one of runoff_model.tc_hours or runoff_model.timing_method must be provided"
        )
    if tc_hours is not None and tc_hours <= 0.0:
        raise ValueError("runoff_model.tc_hours must be > 0")

    runoff_model = GenevaRunoffModelConfig(
        lambda_mode=lambda_mode,
        uh_method=uh_method,
        timing_method=timing_method,
        tc_hours=tc_hours,
    )

    batch_id_value = payload.get("batch_id")
    batch_id = None if batch_id_value in (None, "") else str(batch_id_value)

    return GenevaRunBatchRequest(
        schema_version=schema_version,
        batch_id=batch_id,
        event_filter=event_filter,
        hyetograph=hyetograph,
        runoff_model=runoff_model,
    )


def _coerce_int_tuple(value: Any) -> tuple[int, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("Expected list/tuple of integers")
    out: list[int] = []
    for item in value:
        try:
            parsed = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("Expected list/tuple of integers") from exc
        if parsed <= 0:
            raise ValueError("Integer selector values must be positive")
        out.append(parsed)
    return tuple(out)


def _coerce_str_tuple(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("Expected list/tuple of strings")
    out: list[str] = []
    for item in value:
        text = validate_datasource_id(str(item).strip())
        out.append(text)
    return tuple(out)


def _coerce_float(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


__all__ = [
    "RUN_BATCH_SCHEMA_VERSION",
    "GenevaEventFilter",
    "GenevaHyetographConfig",
    "GenevaRunoffModelConfig",
    "GenevaRunBatchRequest",
    "parse_run_batch_request",
]
