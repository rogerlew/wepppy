"""Pure quality validation and diagnostics for ESDAC soil profiles.

The validators remain independent of the ESDAC builder while Phase 4 wires
their result contract into source sampling, horizon derivation, and worker
aggregation under ADR-0043.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from numbers import Integral, Real
from typing import Literal


QualityOutcome = Literal["valid", "degraded", "rejected"]
DiagnosticSeverity = Literal["warning", "error"]

_MISSING = object()


def _json_safe(value: object) -> object:
    """Keep diagnostic evidence serializable, including non-finite floats."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if isfinite(number) else str(number)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            item = item_method()
        except (AttributeError, TypeError, ValueError):
            pass
        else:
            if item is not value:
                return _json_safe(item)
    return value

_CEC_ALIASES: dict[str, tuple[str, ...]] = {
    "cec_top": ("cec_top", "cectop"),
    "cec_sub": ("cec_sub", "cecsub"),
}

_REQUIRED_CATEGORICAL: tuple[str, ...] = (
    "textdepchg",
    "il",
    "cec_top",
    "cec_sub",
)

_OPTIONAL_CATEGORICAL = ("fao90lev1", "usedom", "dgh", "dimp", "dr")

# Existing ESDAC class representatives (mm), shared by admission and writer.
_il_short_to_depth_mm = {'0': None, '1': 1500, '2': 1150, '3': 600, '4': 400}
_texdepchg_short_to_depth_mm = {
    '0': None, '1': 300, '2': 500, '3': 700, '4': 1000, '5': 1200, '6': 400, '7': 900,
}


def _uses_subsoil(esdb: Mapping[str, object]) -> bool:
    """Unknown depths remain subject to required-data validation, never guessed."""
    values = []
    for field, mapping in (("textdepchg", _texdepchg_short_to_depth_mm),
                           ("il", _il_short_to_depth_mm)):
        value = esdb.get(field)
        if not isinstance(value, (list, tuple)) or len(value) < 2 or not isinstance(value[1], str):
            return True
        depth = mapping.get(value[1])
        if depth is None:
            return True
        values.append(depth)
    return values[1] > values[0]


_STU_FIELDS: tuple[str, ...] = ("CLAY", "SAND", "SILT", "OC", "BD", "GRAVEL")

_HORIZON_FIELDS: dict[str, tuple[str, ...]] = {
    "bd": ("bd",),
    "ks": ("ks",),
    "anisotropy": ("anisotropy", "anisotrophy"),
    "field_capacity": ("field_capacity", "field_cap"),
    "wilting_point": ("wilting_point", "wilt_pt"),
    "sand": ("sand",),
    "clay": ("clay",),
    "silt": ("silt", "vfs"),
    "om": ("om",),
    "cec": ("cec",),
    "smr": ("smr", "gravel"),
    "interrill": ("interrill",),
    "rill": ("rill",),
    "shear": ("shear",),
}


@dataclass(frozen=True, slots=True)
class SoilQualityContext:
    """Location identity carried with every quality result."""

    longitude: float
    latitude: float
    topaz_id: int | str | None = None


@dataclass(frozen=True, slots=True)
class SoilQualityDiagnostic:
    """Stable reason code plus source evidence for one quality finding."""

    code: str
    field: str
    severity: DiagnosticSeverity
    raw_value: object = None
    exception_type: str | None = None


@dataclass(frozen=True, slots=True)
class SoilQualityResult:
    """Pure per-location quality result used by the Phase 3 contract."""

    context: SoilQualityContext
    outcome: QualityOutcome
    diagnostics: tuple[SoilQualityDiagnostic, ...] = ()
    soil_key: str | None = None

    @property
    def accepted(self) -> bool:
        """Return whether the profile may produce model input."""
        return self.outcome in {"valid", "degraded"}

    @property
    def reason_codes(self) -> tuple[str, ...]:
        """Return unique reason codes in first-seen order."""
        return tuple(dict.fromkeys(diagnostic.code for diagnostic in self.diagnostics))

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe quality report entry."""
        return {
            "outcome": self.outcome,
            "longitude": _json_safe(self.context.longitude),
            "latitude": _json_safe(self.context.latitude),
            "topaz_id": _json_safe(self.context.topaz_id),
            "soil_key": self.soil_key,
            "reason_codes": list(self.reason_codes),
            "diagnostics": [
                {
                    "code": diagnostic.code,
                    "field": diagnostic.field,
                    "severity": diagnostic.severity,
                    "raw_value": _json_safe(diagnostic.raw_value),
                    "exception_type": diagnostic.exception_type,
                }
                for diagnostic in self.diagnostics
            ],
        }


class ESDACSoilBuildError(RuntimeError):
    """Expected, location-specific rejection from one ESDAC soil build."""

    def __init__(self, result: SoilQualityResult) -> None:
        self.result = result
        codes = ", ".join(result.reason_codes) or "unknown_quality_failure"
        context = result.context
        super().__init__(
            f"EU soil rejected at ({context.longitude}, {context.latitude})"
            f" for TopoAZ {context.topaz_id!r}: {codes}"
        )


def _result(
    context: SoilQualityContext,
    diagnostics: Sequence[SoilQualityDiagnostic],
    *,
    soil_key: str | None = None,
) -> SoilQualityResult:
    diagnostics_tuple = tuple(diagnostics)
    if any(diagnostic.severity == "error" for diagnostic in diagnostics_tuple):
        outcome: QualityOutcome = "rejected"
    elif diagnostics_tuple:
        outcome = "degraded"
    else:
        outcome = "valid"
    return SoilQualityResult(context, outcome, diagnostics_tuple, soil_key)


def merge_quality_results(*results: SoilQualityResult) -> SoilQualityResult:
    """Combine source, horizon, and Ksat findings for one location."""
    if not results:
        raise ValueError("at least one quality result is required")
    context = results[0].context
    if any(result.context != context for result in results[1:]):
        raise ValueError("quality result contexts must match")
    diagnostics = tuple(
        diagnostic for result in results for diagnostic in result.diagnostics
    )
    return _result(context, diagnostics, soil_key=results[0].soil_key)


def rejected_quality_result(
    context: SoilQualityContext,
    *,
    code: str,
    field: str,
    exception: BaseException | None = None,
    raw_value: object = None,
) -> SoilQualityResult:
    """Create a rejected result while preserving a narrow exception class."""
    return _result(
        context,
        (
            SoilQualityDiagnostic(
                code=code,
                field=field,
                severity="error",
                raw_value=raw_value,
                exception_type=type(exception).__name__ if exception else None,
            ),
        ),
    )


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _source_value(source: Mapping[str, object], aliases: Sequence[str]) -> object:
    for alias in aliases:
        if alias in source:
            return source[alias]
    return _MISSING


def _categorical_short(
    source: Mapping[str, object],
    field: str,
    diagnostics: list[SoilQualityDiagnostic],
) -> str | None:
    aliases = _CEC_ALIASES.get(field, (field,))
    value = _source_value(source, aliases)
    if value is _MISSING:
        diagnostics.append(
            SoilQualityDiagnostic(
                "source.categorical.missing", field, "error", raw_value=None
            )
        )
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) < 2:
        diagnostics.append(
            SoilQualityDiagnostic(
                "source.categorical.malformed", field, "error", raw_value=value
            )
        )
        return None
    short = value[1]
    if short is None or str(short).strip() in {"", "None"}:
        diagnostics.append(
            SoilQualityDiagnostic(
                "source.categorical.empty", field, "error", raw_value=value
            )
        )
        return None
    return str(short)


def _optional_metadata(
    source: Mapping[str, object],
    field: str,
    diagnostics: list[SoilQualityDiagnostic],
) -> tuple[str, str, str]:
    """Retain every usable metadata component; never discard a known class."""
    value = _source_value(source, _CEC_ALIASES.get(field, (field,)))
    fallback = "0" if field == "usedom" else "unknown"

    def warn(code: str) -> None:
        diagnostics.append(SoilQualityDiagnostic(
            code, field, "warning", raw_value=None if value is _MISSING else value,
        ))

    if value is _MISSING:
        warn("source.categorical.missing")
        return "", fallback, "No information"
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) < 2:
        warn("source.categorical.malformed")
        return "", fallback, "No information"
    pixel = value[0]
    if not isinstance(pixel, (str, Real)) or str(pixel).strip() in {"", "None"}:
        warn("source.categorical.pixel_missing")
        pixel = ""
    short = value[1]
    if short is None or (isinstance(short, str) and short.strip() in {"", "None"}):
        warn("source.categorical.empty")
        short = fallback
    elif not isinstance(short, str):
        warn("source.categorical.malformed")
        short = fallback
    description = value[2] if len(value) > 2 else None
    if not isinstance(description, str) or description.strip() in {"", "None"}:
        warn("source.categorical.description_missing")
        description = "No information"
    return str(pixel), short, description


def validate_esdac_source_profile(
    context: SoilQualityContext,
    *,
    esdb: Mapping[str, object],
    stu: Mapping[str, object],
) -> SoilQualityResult:
    """Validate categorical ESDAC and continuous STU source payloads."""
    diagnostics: list[SoilQualityDiagnostic] = []

    categorical: dict[str, str | None] = {}
    use_subsoil = _uses_subsoil(esdb)
    for field in _REQUIRED_CATEGORICAL:
        if field == "cec_sub" and not use_subsoil:
            continue
        categorical[field] = _categorical_short(esdb, field, diagnostics)
        if categorical[field] is not None:
            _optional_metadata(esdb, field, diagnostics)

    for field in (("cec_top", "cec_sub") if use_subsoil else ("cec_top",)):
        value = categorical[field]
        if value is not None and value not in {"H", "M", "L"}:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "source.categorical.unsupported",
                    field,
                    "error",
                    raw_value=value,
                )
            )

    for field in ("textdepchg", "il"):
        if categorical[field] == "0":
            diagnostics.append(
                SoilQualityDiagnostic(
                    f"source.{field}.no_information",
                    field,
                    "error",
                    raw_value=categorical[field],
                )
            )
        elif categorical[field] is not None:
            mapping = _texdepchg_short_to_depth_mm if field == "textdepchg" else _il_short_to_depth_mm
            if categorical[field] not in mapping:
                diagnostics.append(SoilQualityDiagnostic(
                    f"source.{field}.unsupported", field, "error",
                    raw_value=categorical[field],
                ))

    optional_fields = _OPTIONAL_CATEGORICAL + (() if use_subsoil else ("cec_sub",))
    for field in optional_fields:
        categorical[field] = _optional_metadata(esdb, field, diagnostics)[1]

    usedom = categorical["usedom"]
    if usedom is None or usedom == "0":
        diagnostics.append(
            SoilQualityDiagnostic(
                "source.usedom.no_information",
                "usedom",
                "warning",
                raw_value=None if usedom is None else usedom,
            )
        )

    if not use_subsoil:
        diagnostics.append(SoilQualityDiagnostic(
            "source.profile.single_horizon", "horizons", "warning",
            raw_value=[_texdepchg_short_to_depth_mm[categorical["textdepchg"]],
                       _il_short_to_depth_mm[categorical["il"]]],
        ))

    for layer in (("T", "S") if use_subsoil else ("T",)):
        texture: dict[str, float] = {}
        for field in _STU_FIELDS:
            source_field = f"STU_EU_{layer}_{field}"
            raw_value = stu.get(source_field, _MISSING)
            value = _finite_number(raw_value)
            if raw_value is _MISSING or value is None:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "source.stu.nonfinite_value",
                        source_field,
                        "error",
                        raw_value=None if raw_value is _MISSING else raw_value,
                    )
                )
                continue
            texture[field] = value

            if field in {"CLAY", "SAND", "SILT", "GRAVEL"} and not 0 <= value <= 100:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "source.stu.out_of_range",
                        source_field,
                        "error",
                        raw_value=raw_value,
                    )
                )
            elif field == "BD" and value <= 0:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "source.stu.bulk_density_nonpositive",
                        source_field,
                        "error",
                        raw_value=raw_value,
                    )
                )
            elif field == "OC" and value < 0:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "source.stu.organic_matter_negative",
                        source_field,
                        "error",
                        raw_value=raw_value,
                    )
                )

        texture_fields = ("CLAY", "SAND", "SILT")
        if all(field in texture for field in texture_fields):
            texture_sum = sum(texture[field] for field in texture_fields)
            if all(texture[field] == 0 for field in texture_fields):
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "source.stu.mandatory_profile_empty",
                        f"STU_EU_{layer}_CLAY/SAND/SILT",
                        "error",
                        raw_value=texture_sum,
                    )
                )
            elif abs(texture_sum - 100.0) > 1.0:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "source.stu.texture_balance",
                        f"STU_EU_{layer}_CLAY/SAND/SILT",
                        "error",
                        raw_value=texture_sum,
                    )
                )

    return _result(context, diagnostics)


def validate_horizon_depths(
    context: SoilQualityContext,
    depths: Sequence[object] | None,
) -> SoilQualityResult:
    """Validate positive, strictly increasing cumulative horizon depths."""
    diagnostics: list[SoilQualityDiagnostic] = []
    if depths is None or isinstance(depths, (str, bytes)) or not isinstance(depths, Sequence):
        return rejected_quality_result(
            context,
            code="horizon.depth_missing",
            field="horizons",
            raw_value=depths,
        )

    numeric_depths: list[float] = []
    for index, raw_depth in enumerate(depths):
        depth = _finite_number(raw_depth)
        if depth is None:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "horizon.depth_nonfinite",
                    f"horizons[{index}].depth",
                    "error",
                    raw_value=raw_depth,
                )
            )
        elif depth <= 0:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "horizon.depth_nonpositive",
                    f"horizons[{index}].depth",
                    "error",
                    raw_value=raw_depth,
                )
            )
        else:
            numeric_depths.append(depth)

    for index, (previous, current) in enumerate(zip(numeric_depths, numeric_depths[1:]), 1):
        if current <= previous:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "horizon.depth_order",
                    f"horizons[{index}].depth",
                    "error",
                    raw_value=(previous, current),
                )
            )

    return _result(context, diagnostics)


def _horizon_value(horizon: Mapping[str, object], aliases: Sequence[str]) -> object:
    for alias in aliases:
        if alias in horizon:
            return horizon[alias]
    return _MISSING


def validate_horizon_profile(
    context: SoilQualityContext,
    horizons: Sequence[Mapping[str, object]],
) -> SoilQualityResult:
    """Validate values that the ESDAC builder will serialize for WEPP."""
    if not horizons:
        return rejected_quality_result(
            context,
            code="horizon.depth_missing",
            field="horizons",
        )

    diagnostics: list[SoilQualityDiagnostic] = []
    depths = [horizon.get("depth", _MISSING) for horizon in horizons]
    diagnostics.extend(validate_horizon_depths(context, depths).diagnostics)

    numeric_values: list[dict[str, float]] = []
    for index, horizon in enumerate(horizons):
        values: dict[str, float] = {}
        for field, aliases in _HORIZON_FIELDS.items():
            raw_value = _horizon_value(horizon, aliases)
            value = _finite_number(raw_value)
            if raw_value is _MISSING or value is None:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "output.nonfinite_value",
                        f"horizons[{index}].{field}",
                        "error",
                        raw_value=None if raw_value is _MISSING else raw_value,
                    )
                )
            else:
                values[field] = value
        numeric_values.append(values)

        wp = values.get("wilting_point")
        fc = values.get("field_capacity")
        if wp is not None and fc is not None:
            if not 0 <= wp <= 1 or not 0 <= fc <= 1:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "output.water_content_range",
                        f"horizons[{index}].water_content",
                        "error",
                        raw_value=(wp, fc),
                    )
                )
            elif wp > fc:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "output.water_content_order",
                        f"horizons[{index}].water_content",
                        "error",
                        raw_value=(wp, fc),
                    )
                )

    return _result(context, diagnostics)


def _ksat_value(raw_value: object) -> object:
    if isinstance(raw_value, (str, bytes)) or not isinstance(raw_value, Sequence):
        return raw_value
    if len(raw_value) >= 2:
        return raw_value[1]
    return raw_value


def validate_ksat_profile(
    context: SoilQualityContext,
    values: Mapping[str, object] | Sequence[object] | None,
) -> SoilQualityResult:
    """Validate raw or depth-keyed SoilHydroGrids Ksat values."""
    if values is None:
        return rejected_quality_result(
            context,
            code="source.hydrogrids.all_missing",
            field="hydrogrids",
        )

    raw_values = list(values.values()) if isinstance(values, Mapping) else list(values)
    if not raw_values:
        return rejected_quality_result(
            context,
            code="source.hydrogrids.all_missing",
            field="hydrogrids",
        )

    diagnostics: list[SoilQualityDiagnostic] = []
    missing_count = 0
    valid_count = 0
    for index, raw_value in enumerate(raw_values):
        value = _ksat_value(raw_value)
        if value is None:
            missing_count += 1
            continue
        number = _finite_number(value)
        if number is None:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "source.hydrogrids.nonfinite",
                    f"hydrogrids[{index}]",
                    "error",
                    raw_value=value,
                )
            )
        elif number <= 0:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "source.hydrogrids.nonpositive",
                    f"hydrogrids[{index}]",
                    "error",
                    raw_value=value,
                )
            )
        else:
            valid_count += 1

    if valid_count == 0 and missing_count == len(raw_values):
        diagnostics.append(
            SoilQualityDiagnostic(
                "source.hydrogrids.all_missing",
                "hydrogrids",
                "error",
            )
        )
    elif missing_count:
        diagnostics.append(
            SoilQualityDiagnostic(
                "source.hydrogrids.partial_missing",
                "hydrogrids",
                "warning",
                raw_value=missing_count,
            )
        )

    return _result(context, diagnostics)
