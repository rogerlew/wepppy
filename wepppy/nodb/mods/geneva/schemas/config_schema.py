from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

GENEVA_CONFIG_SCHEMA_VERSION = 1

_ALLOWED_LAMBDA_MODES = {"0.20", "0.05"}
_ALLOWED_UH_METHODS = {"scs_triangular", "scs_curvilinear"}
_ALLOWED_UNRESOLVED_POLICIES = {"error", "assume_d"}


@dataclass(frozen=True)
class GenevaConfig:
    schema_version: int = GENEVA_CONFIG_SCHEMA_VERSION
    enabled: bool = False
    lambda_mode: str = "0.20"
    uh_method: str = "scs_triangular"
    default_hsg_code: int | None = None
    unresolved_hsg_policy: str = "error"
    strict_burn_nodata: bool = False
    allow_cross_hsg_merge: bool = False
    hydrophobic_forest_high: bool = True
    hydrophobic_forest_moderate: bool = False
    hydrophobic_shrub_high: bool = True
    hydrophobic_shrub_moderate: bool = False
    min_hru_area_ha: float = 2.0

    def validate(self) -> None:
        if self.schema_version != GENEVA_CONFIG_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must equal {GENEVA_CONFIG_SCHEMA_VERSION}"
            )

        if self.lambda_mode not in _ALLOWED_LAMBDA_MODES:
            raise ValueError("lambda_mode must be one of 0.20 or 0.05")

        if self.uh_method not in _ALLOWED_UH_METHODS:
            raise ValueError("uh_method must be one of scs_triangular or scs_curvilinear")

        if self.unresolved_hsg_policy not in _ALLOWED_UNRESOLVED_POLICIES:
            raise ValueError("unresolved_hsg_policy must be one of error or assume_d")

        if self.default_hsg_code is not None and self.default_hsg_code not in {1, 2, 3, 4}:
            raise ValueError("default_hsg_code must be one of 1,2,3,4 when provided")

        if self.min_hru_area_ha < 2.0:
            raise ValueError("min_hru_area_ha must be >= 2.0")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "lambda_mode": self.lambda_mode,
            "uh_method": self.uh_method,
            "default_hsg_code": self.default_hsg_code,
            "unresolved_hsg_policy": self.unresolved_hsg_policy,
            "strict_burn_nodata": self.strict_burn_nodata,
            "allow_cross_hsg_merge": self.allow_cross_hsg_merge,
            "hydrophobic_forest_high": self.hydrophobic_forest_high,
            "hydrophobic_forest_moderate": self.hydrophobic_forest_moderate,
            "hydrophobic_shrub_high": self.hydrophobic_shrub_high,
            "hydrophobic_shrub_moderate": self.hydrophobic_shrub_moderate,
            "min_hru_area_ha": self.min_hru_area_ha,
        }


def default_geneva_config() -> GenevaConfig:
    config = GenevaConfig()
    config.validate()
    return config


def config_from_mapping(payload: Mapping[str, Any]) -> GenevaConfig:
    data = default_geneva_config().to_payload()
    for key in data:
        if key in payload:
            data[key] = payload[key]

    config = GenevaConfig(
        schema_version=int(data["schema_version"]),
        enabled=_coerce_bool(data["enabled"], field="enabled"),
        lambda_mode=str(data["lambda_mode"]),
        uh_method=str(data["uh_method"]),
        default_hsg_code=_coerce_optional_hsg_code(data.get("default_hsg_code")),
        unresolved_hsg_policy=str(data["unresolved_hsg_policy"]),
        strict_burn_nodata=_coerce_bool(
            data["strict_burn_nodata"],
            field="strict_burn_nodata",
        ),
        allow_cross_hsg_merge=_coerce_bool(
            data["allow_cross_hsg_merge"],
            field="allow_cross_hsg_merge",
        ),
        hydrophobic_forest_high=_coerce_bool(
            data["hydrophobic_forest_high"],
            field="hydrophobic_forest_high",
        ),
        hydrophobic_forest_moderate=_coerce_bool(
            data["hydrophobic_forest_moderate"],
            field="hydrophobic_forest_moderate",
        ),
        hydrophobic_shrub_high=_coerce_bool(
            data["hydrophobic_shrub_high"],
            field="hydrophobic_shrub_high",
        ),
        hydrophobic_shrub_moderate=_coerce_bool(
            data["hydrophobic_shrub_moderate"],
            field="hydrophobic_shrub_moderate",
        ),
        min_hru_area_ha=_coerce_float(data["min_hru_area_ha"], field="min_hru_area_ha"),
    )
    config.validate()
    return config


def merge_config(current: Mapping[str, Any], updates: Mapping[str, Any]) -> GenevaConfig:
    merged = dict(current)
    merged.update(dict(updates))
    return config_from_mapping(merged)


def _coerce_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} must be boolean")


def _coerce_optional_hsg_code(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("default_hsg_code must be one of 1,2,3,4 when provided")
    if isinstance(value, int):
        return value
    raise ValueError("default_hsg_code must be an integer when provided")


def _coerce_float(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


__all__ = [
    "GENEVA_CONFIG_SCHEMA_VERSION",
    "GenevaConfig",
    "config_from_mapping",
    "default_geneva_config",
    "merge_config",
]
