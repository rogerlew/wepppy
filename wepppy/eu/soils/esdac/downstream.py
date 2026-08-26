"""Validation of serialized EU soils after disturbed transformations.

The ESDAC builder validates the base profile before it is written. Disturbed
soil generation then parses that file, applies lookup replacements, and
serializes a new versioned ``.sol``. This module validates the artifact after
that round trip so the downstream transformation cannot quietly reintroduce
non-finite values, invalid horizons, or missing disturbed metadata.
"""

from __future__ import annotations

import json
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


class ESDACSoilQualityReportError(RuntimeError):
    """Raised when an ESDAC runtime quality report cannot identify a soil."""

    def __init__(
        self,
        report_path: str | Path,
        *,
        code: str,
        topaz_id: str | int | None = None,
        detail: str | None = None,
    ) -> None:
        self.report_path = str(report_path)
        self.code = code
        self.topaz_id = topaz_id
        self.detail = detail
        location = f" for TopoAZ {topaz_id!r}" if topaz_id is not None else ""
        suffix = f": {detail}" if detail else ""
        super().__init__(
            f"ESDAC soil quality report error{location}: {code}"
            f" ({self.report_path}){suffix}"
        )


class ESDACDisturbedSoilBuildError(RuntimeError):
    """Raised when a generated EU disturbed artifact fails its quality gate."""

    def __init__(
        self,
        result: SoilQualityResult,
        *,
        artifact_path: str | Path,
        quality_report_path: str | Path,
    ) -> None:
        self.result = result
        self.artifact_path = str(artifact_path)
        self.quality_report_path = str(quality_report_path)
        context = result.context
        codes = ", ".join(result.reason_codes) or "unknown_quality_failure"
        super().__init__(
            f"EU disturbed soil rejected at ({context.longitude}, {context.latitude})"
            f" for TopoAZ {context.topaz_id!r}: {codes}"
        )


def _report_number(
    value: object,
    *,
    report_path: str | Path,
    topaz_id: str | int | None,
    field: str,
) -> float:
    number = _number(value)
    if number is None:
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.nonfinite_context",
            topaz_id=topaz_id,
            detail=field,
        )
    return number


def _quality_result_from_report_entry(
    entry: object,
    *,
    report_path: str | Path,
) -> SoilQualityResult:
    if not isinstance(entry, Mapping):
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.profile_malformed",
        )

    topaz_id = entry.get("topaz_id")
    if topaz_id is None or isinstance(topaz_id, (dict, list, tuple)):
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.topaz_id_missing",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )

    outcome = entry.get("outcome")
    if outcome not in {"valid", "degraded", "rejected"}:
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.outcome_invalid",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )

    soil_key = entry.get("soil_key")
    if soil_key is not None and not isinstance(soil_key, str):
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.soil_key_invalid",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )
    if outcome in {"valid", "degraded"} and not soil_key:
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.soil_key_missing",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )

    if "diagnostics" not in entry:
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.diagnostics_malformed",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )
    diagnostics_payload = entry["diagnostics"]
    if (
        isinstance(diagnostics_payload, (str, bytes))
        or not isinstance(diagnostics_payload, Sequence)
    ):
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.diagnostics_malformed",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )

    diagnostics: list[SoilQualityDiagnostic] = []
    for diagnostic_payload in diagnostics_payload:
        if not isinstance(diagnostic_payload, Mapping):
            raise ESDACSoilQualityReportError(
                report_path,
                code="source.quality_report.diagnostic_malformed",
                topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
            )
        code = diagnostic_payload.get("code")
        field = diagnostic_payload.get("field")
        severity = diagnostic_payload.get("severity")
        if (
            not isinstance(code, str)
            or not isinstance(field, str)
            or severity not in {"warning", "error"}
        ):
            raise ESDACSoilQualityReportError(
                report_path,
                code="source.quality_report.diagnostic_invalid",
                topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
            )
        exception_type = diagnostic_payload.get("exception_type")
        if exception_type is not None and not isinstance(exception_type, str):
            raise ESDACSoilQualityReportError(
                report_path,
                code="source.quality_report.diagnostic_invalid",
                topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
            )
        diagnostics.append(
            SoilQualityDiagnostic(
                code,
                field,
                severity,
                raw_value=diagnostic_payload.get("raw_value"),
                exception_type=exception_type,
            )
        )

    context = SoilQualityContext(
        longitude=_report_number(
            entry.get("longitude"),
            report_path=report_path,
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
            field="longitude",
        ),
        latitude=_report_number(
            entry.get("latitude"),
            report_path=report_path,
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
            field="latitude",
        ),
        topaz_id=topaz_id,
    )
    result = SoilQualityResult(context, outcome, tuple(diagnostics), soil_key)
    if result.outcome == "valid" and result.diagnostics:
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.outcome_mismatch",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )
    if result.outcome == "degraded" and (
        not result.diagnostics
        or any(diagnostic.severity == "error" for diagnostic in result.diagnostics)
    ):
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.outcome_mismatch",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )
    if result.outcome == "rejected" and not any(
        diagnostic.severity == "error" for diagnostic in result.diagnostics
    ):
        raise ESDACSoilQualityReportError(
            report_path,
            code="source.quality_report.outcome_mismatch",
            topaz_id=topaz_id if isinstance(topaz_id, (str, int)) else None,
        )
    return result


def load_soil_quality_report(
    report_path: str | Path,
) -> dict[str, SoilQualityResult]:
    """Load and validate the additive Phase 4 ESDAC quality report."""
    path = Path(report_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.missing",
        ) from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.unreadable",
            detail=type(exc).__name__,
        ) from exc

    if (
        not isinstance(payload, Mapping)
        or isinstance(payload.get("schema_version"), bool)
        or payload.get("schema_version") != 1
    ):
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.schema_invalid",
        )
    if payload.get("batch_outcome") != "accepted":
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.batch_not_accepted",
        )
    profiles = payload.get("profiles")
    if (
        isinstance(profiles, (str, bytes))
        or not isinstance(profiles, Sequence)
    ):
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.profiles_missing",
        )

    results: dict[str, SoilQualityResult] = {}
    for entry in profiles:
        result = _quality_result_from_report_entry(entry, report_path=path)
        key = str(result.context.topaz_id)
        if key in results:
            raise ESDACSoilQualityReportError(
                path,
                code="source.quality_report.duplicate_topaz_id",
                topaz_id=result.context.topaz_id,
            )
        results[key] = result

    accepted_count = payload.get("accepted_count")
    rejected_count = payload.get("rejected_count")
    if (
        isinstance(accepted_count, bool)
        or not isinstance(accepted_count, int)
        or accepted_count < 0
        or isinstance(rejected_count, bool)
        or not isinstance(rejected_count, int)
        or rejected_count < 0
    ):
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.counts_invalid",
        )
    actual_accepted = sum(result.accepted for result in results.values())
    actual_rejected = sum(result.outcome == "rejected" for result in results.values())
    if accepted_count != actual_accepted or rejected_count != actual_rejected:
        raise ESDACSoilQualityReportError(
            path,
            code="source.quality_report.counts_mismatch",
        )
    return results


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
