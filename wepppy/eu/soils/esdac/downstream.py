"""Validation of serialized EU soils after disturbed transformations.

The ESDAC builder validates the base profile before it is written. Disturbed
soil generation then parses that file, applies lookup replacements, and
serializes a new versioned ``.sol``. This module validates the artifact after
that round trip so the downstream transformation cannot quietly reintroduce
non-finite values, invalid horizons, or missing disturbed metadata.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path
from typing import Any

from wepppy.wepp.soils.utils import WeppSoilUtil

from .quality import (
    SoilQualityContext,
    SoilQualityDiagnostic,
    SoilQualityResult,
    merge_quality_results,
)


_HORIZON_FIELDS: tuple[str, ...] = (
    "bd",
    "ksat",
    "fc",
    "wp",
    "sand",
    "clay",
    "orgmat",
    "cec",
    "rfg",
)


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _result(
    context: SoilQualityContext,
    diagnostics: Sequence[SoilQualityDiagnostic],
) -> SoilQualityResult:
    diagnostics_tuple = tuple(diagnostics)
    if any(diagnostic.severity == "error" for diagnostic in diagnostics_tuple):
        outcome = "rejected"
    elif diagnostics_tuple:
        outcome = "degraded"
    else:
        outcome = "valid"
    return SoilQualityResult(context, outcome, diagnostics_tuple)


def _finite_diagnostic(
    diagnostics: list[SoilQualityDiagnostic],
    *,
    field: str,
    value: object,
    code: str,
) -> float | None:
    number = _number(value)
    if number is None:
        diagnostics.append(
            SoilQualityDiagnostic(code, field, "error", raw_value=value)
        )
    return number


def _validate_ofe(
    diagnostics: list[SoilQualityDiagnostic],
    ofe: Mapping[str, Any],
    *,
    ofe_index: int,
    expected_luse: str | None,
    expected_stext: str | None,
    supports_anisotropy: bool,
) -> None:
    prefix = f"ofes[{ofe_index}]"

    for field in ("ki", "kr", "shcrit", "sat"):
        value = _finite_diagnostic(
            diagnostics,
            field=f"{prefix}.{field}",
            value=ofe.get(field),
            code="disturbed.ofe.nonfinite_value",
        )
        if field == "sat" and value is not None and not 0 <= value <= 1:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "disturbed.ofe.saturation_out_of_range",
                    f"{prefix}.sat",
                    "error",
                    raw_value=ofe.get(field),
                )
            )

    if expected_luse is not None and ofe.get("luse") != expected_luse:
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.metadata.luse_mismatch",
                f"{prefix}.luse",
                "error",
                raw_value=ofe.get("luse"),
            )
        )
    if expected_stext is not None and ofe.get("stext") != expected_stext:
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.metadata.stext_mismatch",
                f"{prefix}.stext",
                "error",
                raw_value=ofe.get("stext"),
            )
        )

    horizons = ofe.get("horizons")
    if (
        isinstance(horizons, (str, bytes))
        or not isinstance(horizons, Sequence)
        or not horizons
    ):
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.horizon.missing",
                f"{prefix}.horizons",
                "error",
                raw_value=horizons,
            )
        )
        return

    nsl = _number(ofe.get("nsl"))
    if nsl is None:
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.ofe.horizon_count_nonfinite",
                f"{prefix}.nsl",
                "error",
                raw_value=ofe.get("nsl"),
            )
        )
    elif int(nsl) != len(horizons):
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.horizon.count_mismatch",
                f"{prefix}.nsl",
                "error",
                raw_value=(ofe.get("nsl"), len(horizons)),
            )
        )

    previous_depth: float | None = None
    for horizon_index, raw_horizon in enumerate(horizons):
        field_prefix = f"{prefix}.horizons[{horizon_index}]"
        if not isinstance(raw_horizon, Mapping):
            diagnostics.append(
                SoilQualityDiagnostic(
                    "disturbed.horizon.malformed",
                    field_prefix,
                    "error",
                    raw_value=raw_horizon,
                )
            )
            continue

        depth = _finite_diagnostic(
            diagnostics,
            field=f"{field_prefix}.solthk",
            value=raw_horizon.get("solthk"),
            code="disturbed.horizon.depth_nonfinite",
        )
        if depth is not None:
            if depth <= 0:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.horizon.depth_nonpositive",
                        f"{field_prefix}.solthk",
                        "error",
                        raw_value=raw_horizon.get("solthk"),
                    )
                )
            if previous_depth is not None and depth <= previous_depth:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.horizon.depth_order",
                        f"{field_prefix}.solthk",
                        "error",
                        raw_value=(previous_depth, depth),
                    )
                )
            previous_depth = depth

        for field in _HORIZON_FIELDS:
            value = _finite_diagnostic(
                diagnostics,
                field=f"{field_prefix}.{field}",
                value=raw_horizon.get(field),
                code="disturbed.horizon.nonfinite_value",
            )
            if value is None:
                continue
            if field == "bd" and value <= 0:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.horizon.bulk_density_nonpositive",
                        f"{field_prefix}.bd",
                        "error",
                        raw_value=raw_horizon.get(field),
                    )
                )
            elif field == "ksat" and value <= 0:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.horizon.ksat_nonpositive",
                        f"{field_prefix}.ksat",
                        "error",
                        raw_value=raw_horizon.get(field),
                    )
                )
            elif field in {"sand", "clay"} and not 0 <= value <= 100:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.horizon.texture_out_of_range",
                        f"{field_prefix}.{field}",
                        "error",
                        raw_value=raw_horizon.get(field),
                    )
                )
            elif field in {"fc", "wp"} and not 0 <= value <= 1:
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.horizon.water_content_range",
                        f"{field_prefix}.{field}",
                        "error",
                        raw_value=raw_horizon.get(field),
                    )
                )

        if supports_anisotropy:
            _finite_diagnostic(
                diagnostics,
                field=f"{field_prefix}.anisotropy",
                value=raw_horizon.get("anisotropy"),
                code="disturbed.horizon.nonfinite_value",
            )

        wp = _number(raw_horizon.get("wp"))
        fc = _number(raw_horizon.get("fc"))
        if wp is not None and fc is not None and wp <= fc and 0 <= wp <= 1 and 0 <= fc <= 1:
            continue
        if wp is not None and fc is not None:
            diagnostics.append(
                SoilQualityDiagnostic(
                    "disturbed.horizon.water_content_order",
                    f"{field_prefix}.water_content",
                    "error",
                    raw_value=(wp, fc),
                )
            )

    restrictive = ofe.get("res_lyr")
    if restrictive is not None and isinstance(restrictive, Mapping):
        _finite_diagnostic(
            diagnostics,
            field=f"{prefix}.res_lyr.kslast",
            value=restrictive.get("kslast"),
            code="disturbed.restrictive_layer.nonfinite_value",
        )


def validate_disturbed_soil_artifact(
    soil_path: str | Path,
    *,
    context: SoilQualityContext,
    expected_datver: int | float | None = None,
    expected_luse: str | None = None,
    expected_stext: str | None = None,
    base_quality: SoilQualityResult | None = None,
) -> SoilQualityResult:
    """Validate a disturbed ``.sol`` after writing and reparsing it.

    ``base_quality`` is optional so existing callers can adopt the validator
    incrementally. When supplied, its diagnostics are merged into the
    downstream result. A rejected base is returned immediately with an
    additional explicit diagnostic; no missing artifact is converted into a
    generic disturbed soil result.
    """
    if base_quality is not None and base_quality.context != context:
        return _result(
            context,
            base_quality.diagnostics
            + (
                SoilQualityDiagnostic(
                    "disturbed.base.context_mismatch",
                    "base_quality.context",
                    "error",
                    raw_value={
                        "longitude": base_quality.context.longitude,
                        "latitude": base_quality.context.latitude,
                        "topaz_id": base_quality.context.topaz_id,
                    },
                ),
            ),
        )

    if base_quality is not None and not base_quality.accepted:
        return merge_quality_results(
            base_quality,
            _result(
                context,
                (
                    SoilQualityDiagnostic(
                        "disturbed.base.rejected",
                        "base_quality",
                        "error",
                    ),
                ),
            ),
        )

    path = Path(soil_path)
    try:
        soil = WeppSoilUtil(str(path))
    except Exception as exc:  # broad-except: parser boundary translates heterogeneous syntax errors
        downstream = _result(
            context,
            (
                SoilQualityDiagnostic(
                    "disturbed.artifact.parse_error",
                    str(path),
                    "error",
                    exception_type=type(exc).__name__,
                ),
            ),
        )
        return merge_quality_results(base_quality, downstream) if base_quality else downstream

    diagnostics: list[SoilQualityDiagnostic] = []
    actual_datver = _number(soil.obj.get("datver"))
    if actual_datver is None:
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.artifact.version_nonfinite",
                "datver",
                "error",
                raw_value=soil.obj.get("datver"),
            )
        )
    elif expected_datver is not None and actual_datver != float(expected_datver):
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.metadata.version_mismatch",
                "datver",
                "error",
                raw_value=soil.obj.get("datver"),
            )
        )

    ofes = soil.obj.get("ofes")
    if (
        isinstance(ofes, (str, bytes))
        or not isinstance(ofes, Sequence)
        or not ofes
    ):
        diagnostics.append(
            SoilQualityDiagnostic(
                "disturbed.ofe.missing",
                "ofes",
                "error",
                raw_value=ofes,
            )
        )
    else:
        supports_anisotropy = actual_datver is not None and actual_datver >= 7778
        for index, raw_ofe in enumerate(ofes):
            if not isinstance(raw_ofe, Mapping):
                diagnostics.append(
                    SoilQualityDiagnostic(
                        "disturbed.ofe.malformed",
                        f"ofes[{index}]",
                        "error",
                        raw_value=raw_ofe,
                    )
                )
                continue
            _validate_ofe(
                diagnostics,
                raw_ofe,
                ofe_index=index,
                expected_luse=expected_luse,
                expected_stext=expected_stext,
                supports_anisotropy=supports_anisotropy,
            )

    downstream = _result(context, diagnostics)
    return merge_quality_results(base_quality, downstream) if base_quality else downstream
