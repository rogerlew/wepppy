"""Omni-artifact precondition validation for PATH-CE (D3 / ADR-0023).

The user provisions Omni scenarios and outlet contrasts before running
PATH-CE; nothing here provisions anything. Validation confirms the run
directory carries every artifact the pipeline consumes and that coverage
matches the configured treatments, producing actionable "run Omni X"
errors otherwise.

Coverage semantics (see 2026-07-20_validation_run_austere.md): each
configured treatment scenario must appear among *completed* contrasts —
psv contrast ids absent from ``contrasts.out.parquet`` are legitimate
(``landuse_unchanged`` skips), so ids are never cross-checked against the
psv. WGS geojson availability is a warning, not an error: it blocks the
HTML report (Phase 3), not the solve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd
import pyarrow as pa

__all__ = [
    "OUTLET_SEDIMENT_KEY",
    "PathCEPreconditionError",
    "PreconditionReport",
    "validate_preconditions",
]

OUTLET_SEDIMENT_KEY = "Avg. Ann. sediment discharge from outlet"

HILLSLOPE_SUMMARIES = "omni/scenarios.hillslope_summaries.parquet"
CONTRASTS_OUT = "omni/contrasts.out.parquet"
SCENARIOS_OUT = "omni/scenarios.out.parquet"
CONTRAST_GROUPS_PSV = "omni/contrast_id_definitions.psv"
HILLSLOPE_CHAR = "watershed/hillslopes.parquet"

_GEOJSON_SEARCH_DIRS = ("dem/wbt", "dem/topaz", "dem/taudem")


class PathCEPreconditionError(RuntimeError):
    """Raised when required Omni artifacts are missing or under-provisioned."""

    def __init__(self, report: "PreconditionReport") -> None:
        super().__init__("; ".join(report.errors) or "PATH-CE preconditions not met")
        self.report = report


@dataclass
class PreconditionReport:
    ok: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    mode: Optional[str] = None  # "grouped" | "cumulative"
    contrast_groups_path: Optional[str] = None  # psv relpath when mode == grouped
    subcatchments_geojson: Optional[str] = None
    channels_geojson: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "mode": self.mode,
            "contrast_groups_path": self.contrast_groups_path,
            "subcatchments_geojson": self.subcatchments_geojson,
            "channels_geojson": self.channels_geojson,
        }


def _contrast_scenarios(contrasts: pd.DataFrame) -> pd.Series:
    if "contrast_scenario" in contrasts.columns:
        return contrasts["contrast_scenario"].astype(str)
    if "contrast" in contrasts.columns:
        return contrasts["contrast"].astype(str).str.split("to__").str[-1]
    return pd.Series([], dtype=str)


def _read_artifact(path: Path, relpath: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Read a parquet artifact defensively; malformed files become report errors."""
    try:
        return pd.read_parquet(path), None
    except (OSError, ValueError, KeyError, pa.lib.ArrowException) as exc:
        return None, f"{relpath} is unreadable ({exc.__class__.__name__}: {exc}) — regenerate it."


def validate_preconditions(
    wd: str,
    treatments: Sequence[Mapping[str, Any]],
    baseline_scenario: str = "sbs_map",
    undisturbed_scenario: str = "undisturbed",
) -> PreconditionReport:
    """Validate run artifacts against the configured treatment set.

    ``treatments`` follows the presets vector contract (needs ``scenario``
    and ``label`` keys). Returns a report; never raises — callers decide
    whether errors are fatal (see :class:`PathCEPreconditionError`).
    """
    base = Path(wd)
    report = PreconditionReport()
    treatment_scenarios = [str(t["scenario"]) for t in treatments]

    def _err(msg: str) -> None:
        report.errors.append(msg)
        report.ok = False

    # -- hillslope scenario summaries -----------------------------------
    hs_path = base / HILLSLOPE_SUMMARIES
    if not hs_path.exists():
        _err(
            f"{HILLSLOPE_SUMMARIES} not found — run Omni scenarios "
            f"(undisturbed + mulch treatments) before PATH-CE."
        )
    else:
        summaries, read_err = _read_artifact(hs_path, HILLSLOPE_SUMMARIES)
        if read_err:
            _err(read_err)
        elif "scenario" not in summaries.columns:
            _err(f"{HILLSLOPE_SUMMARIES} has no 'scenario' column — re-run Omni scenarios.")
        else:
            scenarios = set(summaries["scenario"].astype(str))
            for needed, what in (
                (baseline_scenario, "baseline"),
                (undisturbed_scenario, "reference"),
            ):
                if needed not in scenarios:
                    _err(
                        f"Omni scenario summaries are missing the {what} scenario "
                        f"{needed!r} — re-run Omni scenarios."
                    )
            missing = [s for s in treatment_scenarios if s not in scenarios]
            if missing:
                _err(
                    f"Omni scenario summaries are missing treatment scenario(s) {missing} — "
                    f"add them to Omni and run Omni scenarios."
                )

    # -- outlet contrasts (structurally required for the Sddc constraint) --
    co_path = base / CONTRASTS_OUT
    if not co_path.exists():
        _err(
            f"{CONTRASTS_OUT} not found — run Omni contrasts (treatment vs control) "
            f"before PATH-CE; outlet contrasts are required for the sediment-discharge constraint."
        )
    else:
        contrasts, read_err = _read_artifact(co_path, CONTRASTS_OUT)
        if read_err:
            _err(read_err)
            contrasts = None
        if contrasts is not None:
            if "contrast_id" not in contrasts.columns:
                _err(f"{CONTRASTS_OUT} has no 'contrast_id' column — re-run Omni contrasts.")
            # Contrasts must target the treatment AND control against the
            # post-fire baseline; a treatment-vs-undisturbed contrast would
            # produce scientifically wrong Sddc reductions downstream.
            if "control_scenario" in contrasts.columns:
                baseline_mask = contrasts["control_scenario"].astype(str).eq(baseline_scenario)
                eligible = contrasts.loc[baseline_mask]
                off_baseline = contrasts.loc[~baseline_mask]
                if len(off_baseline):
                    off_scen = sorted(set(_contrast_scenarios(off_baseline)) & set(treatment_scenarios))
                    if off_scen:
                        report.warnings.append(
                            f"Some contrasts for {off_scen} use a non-{baseline_scenario!r} control "
                            f"scenario and are ignored for coverage."
                        )
            else:
                eligible = contrasts
            scen = _contrast_scenarios(eligible)
            covered = set(scen)
            missing = [s for s in treatment_scenarios if s not in covered]
            if missing:
                _err(
                    f"Omni contrasts have no completed {baseline_scenario!r}-control contrasts for "
                    f"treatment scenario(s) {missing} — run Omni contrasts for each configured "
                    f"treatment. (Contrasts skipped as landuse_unchanged do not count against "
                    f"coverage when at least one contrast per treatment completed.)"
                )
            if "key" in contrasts.columns:
                keyed = eligible.loc[eligible["key"].astype(str).eq(OUTLET_SEDIMENT_KEY)]
                keyed_scen = set(_contrast_scenarios(keyed))
                unkeyed = [s for s in treatment_scenarios if s in covered and s not in keyed_scen]
                if unkeyed:
                    _err(
                        f"Omni contrasts for {unkeyed} lack the {OUTLET_SEDIMENT_KEY!r} key — "
                        f"re-run Omni contrasts with outlet summaries enabled."
                    )
            else:
                _err(f"{CONTRASTS_OUT} has no 'key' column — re-run Omni contrasts.")

            # -- schema mode ------------------------------------------------
            psv_path = base / CONTRAST_GROUPS_PSV
            if psv_path.exists():
                report.mode = "grouped"
                report.contrast_groups_path = CONTRAST_GROUPS_PSV
            elif "contrast_topaz_id" in contrasts.columns:
                report.mode = "cumulative"
            else:
                _err(
                    f"Cannot determine contrast schema: no {CONTRAST_GROUPS_PSV} and no "
                    f"'contrast_topaz_id' column in {CONTRASTS_OUT} — re-run Omni contrasts "
                    f"(current Omni writes the contrast group definitions file)."
                )

    # -- outlet scenario totals -----------------------------------------
    so_path = base / SCENARIOS_OUT
    if not so_path.exists():
        _err(f"{SCENARIOS_OUT} not found — run Omni scenarios before PATH-CE.")
    else:
        totals, read_err = _read_artifact(so_path, SCENARIOS_OUT)
        if read_err:
            _err(read_err)
        elif not {"key", "value", "scenario"}.issubset(totals.columns):
            _err(f"{SCENARIOS_OUT} lacks key/value/scenario columns — re-run Omni scenarios.")
        else:
            sbs_keys = set(
                totals.loc[totals["scenario"].astype(str).eq(baseline_scenario), "key"].astype(str)
            )
            if OUTLET_SEDIMENT_KEY not in sbs_keys:
                report.warnings.append(
                    f"{SCENARIOS_OUT} has no {OUTLET_SEDIMENT_KEY!r} row for "
                    f"{baseline_scenario!r}; the post-fire outlet scalar will fall back to "
                    f"contrast control values."
                )

    # -- hillslope characteristics --------------------------------------
    char_path = base / HILLSLOPE_CHAR
    if not char_path.exists():
        _err(f"{HILLSLOPE_CHAR} not found — build the watershed before PATH-CE.")
    else:
        char, read_err = _read_artifact(char_path, HILLSLOPE_CHAR)
        if read_err:
            _err(read_err)
        else:
            char_cols = set(char.columns)
            has_id = bool({"topaz_id", "TopazID", "Topaz ID"} & char_cols)
            missing_cols = [c for c in ("centroid_lon", "centroid_lat") if c not in char_cols]
            if not has_id:
                missing_cols.insert(0, "topaz_id")
            if missing_cols:
                _err(
                    f"{HILLSLOPE_CHAR} lacks required columns {missing_cols} — "
                    f"re-run watershed abstraction."
                )

    # -- WGS geojsons (report-stage; warning only) ----------------------
    for attr, name in (
        ("subcatchments_geojson", "subcatchments.WGS.geojson"),
        ("channels_geojson", "channels.WGS.geojson"),
    ):
        for d in _GEOJSON_SEARCH_DIRS:
            candidate = base / d / name
            if candidate.exists():
                setattr(report, attr, f"{d}/{name}")
                break
        else:
            report.warnings.append(
                f"{name} not found under {_GEOJSON_SEARCH_DIRS} — the interactive HTML "
                f"report map will be unavailable until the watershed WGS exports exist."
            )

    return report
