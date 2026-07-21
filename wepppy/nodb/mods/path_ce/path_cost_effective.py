"""PATH Cost-Effective NoDb controller (v2).

Coordinates the vendored PATH-CE pipeline for a run directory: validates
user-provisioned Omni artifacts (no auto-provisioning — D3/ADR-0023),
prepares the parquet-native model frame, runs the faithful solver behind
the wepppy seam (acre cost basis, label alignment), runs the threshold
sweep with cache reuse, and persists artifacts under ``<wd>/path/`` for
the report pipeline and UI.

Stage methods (``validate``, ``prepare_data``, ``solve``, ``run_sweep``)
are individually callable; ``run()`` orchestrates them and accepts a
status callback so the RQ task can stream stage transitions without
duplicating orchestration.

Config schema (serialized in ``path_ce.nodb``; $/acre per D4):

- ``sdyd_threshold`` (tons/acre), ``sddc_threshold`` (tons)
- ``slope_range``: ``[min_deg|null, max_deg|null]``
- ``severity_filter``: null or subset of High/Moderate/Low (grouped-mode
  caveat in ADR-0023 §5)
- ``treatments``: list of ``{label, scenario, unit_cost, quantity,
  fixed_cost}`` vectors (presets contract)

The HTML report always renders (skipped with a recorded reason only when the
WGS geojson exports are missing).
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except ImportError:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

from wepppy.wepp.interchange.schema_utils import pa_field
from wepppy.nodb.base import NoDbBase, nodb_setter

from .data_prep import prepare_ce_and_plot_data
from .path_ce_solver import (
    ACRES_PER_HECTARE,
    PathCESolverError,
    SolverResult,
    prepare_solver_inputs,
    run_path_cost_effective_solver,
)
from .preconditions import (
    CONTRASTS_OUT,
    HILLSLOPE_CHAR,
    HILLSLOPE_SUMMARIES,
    SCENARIOS_OUT,
    PathCEPreconditionError,
    PreconditionReport,
    validate_preconditions,
)
from .presets import default_treatments, normalize_treatment, solver_vectors
from .report_service import PathCEReportError, render_report
from .threshold_sweep import all_thresholds, find_threshold_ranges

__all__ = ["PathCostEffective"]

LOGGER = logging.getLogger(__name__)

SEVERITY_CLASSES = ("High", "Moderate", "Low")

PREP_PREFIX = "path_ce"
PREPARED_FRAME = f"{PREP_PREFIX}_final_data.parquet"
SELECTION_TABLE = "selection.parquet"
SDYD_TABLE = "hillslope_sdyd.parquet"
UNTREATABLE_TABLE = "untreatable.parquet"
UNTREATABLE_INCREASE_TABLE = "untreatable_increase.parquet"
SWEEP_TABLE = "sweep.parquet"
SWEEP_MANIFEST = "sweep_manifest.json"


def _default_config() -> Dict[str, Any]:
    return {
        "sdyd_threshold": 15.0,
        "sddc_threshold": 0.0,
        "slope_range": [None, None],
        "severity_filter": None,
        "treatments": default_treatments(),
    }


def _normalize_slope_range(value: Any) -> List[Optional[float]]:
    if value in (None, "", []):
        return [None, None]
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
        raise ValueError(f"slope_range must be a [min, max] pair, got {value!r}")
    out: List[Optional[float]] = []
    for bound in value:
        if bound in (None, ""):
            out.append(None)
            continue
        bound = float(bound)
        if not math.isfinite(bound):
            raise ValueError(f"slope_range bounds must be finite, got {bound!r}")
        out.append(bound)
    if out[0] is not None and out[1] is not None and out[0] > out[1]:
        raise ValueError(f"slope_range min exceeds max: {out}")
    return out


def _normalize_severity_filter(value: Any) -> Optional[List[str]]:
    if value in (None, "", []):
        return None
    if isinstance(value, str):
        value = [value]
    out = [str(item).strip().title() for item in value if item not in (None, "")]
    invalid = [s for s in out if s not in SEVERITY_CLASSES]
    if invalid:
        raise ValueError(
            f"severity_filter accepts {list(SEVERITY_CLASSES)}, got {invalid}"
        )
    return out or None


def _normalize_threshold(name: str, value: Any, default: float) -> float:
    if value in (None, ""):
        return default
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number, got {value!r}")
    return value


def _normalize_config(value: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    incoming = dict(value or {})
    defaults = _default_config()

    raw_treatments = incoming.get("treatments")
    if raw_treatments is None:
        treatments = defaults["treatments"]
    elif not raw_treatments:
        raise ValueError("treatments must contain at least one treatment vector")
    else:
        treatments = [normalize_treatment(t) for t in raw_treatments]
        labels = [t["label"] for t in treatments]
        if len(set(labels)) != len(labels):
            raise ValueError(f"treatment labels must be unique, got {labels}")

    return {
        "sdyd_threshold": _normalize_threshold(
            "sdyd_threshold", incoming.get("sdyd_threshold"), defaults["sdyd_threshold"]
        ),
        "sddc_threshold": _normalize_threshold(
            "sddc_threshold", incoming.get("sddc_threshold"), defaults["sddc_threshold"]
        ),
        "slope_range": _normalize_slope_range(incoming.get("slope_range")),
        "severity_filter": _normalize_severity_filter(incoming.get("severity_filter")),
        "treatments": treatments,
    }


def _solver_slope_range(config: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    lo, hi = config.get("slope_range") or [None, None]
    if lo is None and hi is None:
        return None
    return (lo if lo is not None else -math.inf, hi if hi is not None else math.inf)


def _dtype_to_arrow(dtype: Any) -> pa.DataType:
    if pd.api.types.is_integer_dtype(dtype):
        return pa.int64()
    if pd.api.types.is_float_dtype(dtype):
        return pa.float64()
    if pd.api.types.is_bool_dtype(dtype):
        return pa.bool_()
    return pa.string()


def _dataframe_to_table(df: pd.DataFrame) -> pa.Table:
    fields = [pa_field(str(column), _dtype_to_arrow(dtype)) for column, dtype in df.dtypes.items()]
    schema = pa.schema(fields)
    return pa.Table.from_pandas(df, schema=schema, preserve_index=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PathCostEffective(NoDbBase):
    """NoDb controller for the PATH cost-effective optimization pipeline."""

    __name__ = "PathCostEffective"
    filename = "path_ce.nodb"

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._path_dir = str(self._ensure_path_dir())

            if not isinstance(getattr(self, "_config", None), Mapping):
                self._config = _normalize_config({})
            else:
                # pre-v2 configs (mulch_costs/treatment_options) are replaced
                # wholesale — no backward compatibility (package brief).
                try:
                    self._config = _normalize_config(self._config)
                except (ValueError, TypeError):
                    self._config = _normalize_config({})

            if not hasattr(self, "_results"):
                self._results: Dict[str, Any] = {}
            if not hasattr(self, "_precondition_errors"):
                self._precondition_errors: List[str] = []
            if not hasattr(self, "_status"):
                self._status: str = "idle"
            if not hasattr(self, "_status_message"):
                self._status_message: str = "Waiting for configuration."
            if not hasattr(self, "_progress"):
                self._progress: float = 0.0

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    def _ensure_path_dir(self) -> Path:
        path_dir = Path(self.wd) / "path"
        path_dir.mkdir(parents=True, exist_ok=True)
        return path_dir

    @property
    def path_dir(self) -> Path:
        return Path(self._path_dir)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @property
    def config(self) -> Dict[str, Any]:
        current = _normalize_config(self._config if isinstance(self._config, Mapping) else {})
        return current

    @config.setter  # type: ignore[override]
    @nodb_setter
    def config(self, value: Mapping[str, Any]) -> None:
        self._config = _normalize_config(value)
        self._status = "configured"
        self._status_message = "Configuration updated."
        self._progress = 0.0

    # ------------------------------------------------------------------
    # Status / results
    # ------------------------------------------------------------------
    @property
    def results(self) -> Dict[str, Any]:
        return copy.deepcopy(self._results)

    def clear_results(self) -> None:
        with self.locked():
            self._results = {}
            self._status = "idle"
            self._status_message = "Results cleared."
            self._progress = 0.0

    def set_status(
        self,
        status: str,
        *,
        message: Optional[str] = None,
        progress: Optional[float] = None,
    ) -> None:
        with self.locked():
            self._status = status
            if message is not None:
                self._status_message = message
            if progress is not None:
                self._progress = max(0.0, min(1.0, progress))

    def store_results(self, results: Mapping[str, Any]) -> None:
        with self.locked():
            self._results = copy.deepcopy(dict(results))
            self._status = "completed"
            self._status_message = "PATH-CE run complete."
            self._progress = 1.0

    @property
    def precondition_errors(self) -> List[str]:
        """Structured Omni-provisioning failures from the last run attempt."""
        return list(getattr(self, "_precondition_errors", []))

    def _set_precondition_errors(self, errors: Sequence[str]) -> None:
        with self.locked():
            self._precondition_errors = [str(e) for e in errors]

    @property
    def status(self) -> str:
        return self._status

    @property
    def status_message(self) -> str:
        return self._status_message

    @property
    def progress(self) -> float:
        return self._progress

    # ------------------------------------------------------------------
    # Stage 1: precondition validation (D3 — no provisioning)
    # ------------------------------------------------------------------
    def validate(self, config: Optional[Mapping[str, Any]] = None) -> PreconditionReport:
        """Validate user-provisioned Omni artifacts against the configured treatments."""
        if config is None:
            config = self.config
        return validate_preconditions(self.wd, config["treatments"])

    # ------------------------------------------------------------------
    # Stage 2: data preparation (parquet-native, vendored pipeline)
    # ------------------------------------------------------------------
    def prepare_data(self, report: Optional[PreconditionReport] = None) -> pd.DataFrame:
        """Build the model frame from run artifacts; persists the four prep tables."""
        if report is None:
            report = self.validate()
        if not report.ok:
            raise PathCEPreconditionError(report)

        wd = Path(self.wd)
        contrast_groups = (
            str(wd / report.contrast_groups_path) if report.contrast_groups_path else None
        )
        _, _, _, final_df = prepare_ce_and_plot_data(
            hillslopes=pd.read_parquet(wd / HILLSLOPE_SUMMARIES),
            contrasts=pd.read_parquet(wd / CONTRASTS_OUT),
            hillslope_char=pd.read_parquet(wd / HILLSLOPE_CHAR),
            contrast_groups=contrast_groups,
            outlet_totals=pd.read_parquet(wd / SCENARIOS_OUT),
            write_outputs=True,
            output_dir=str(self.path_dir),
            output_prefix=PREP_PREFIX,
        )
        return final_df

    # ------------------------------------------------------------------
    # Stage 3: solve
    # ------------------------------------------------------------------
    def solve(
        self, final_df: pd.DataFrame, config: Optional[Mapping[str, Any]] = None
    ) -> SolverResult:
        """Run the seam-wrapped solver and persist selection/sdyd/untreatable tables."""
        if config is None:
            config = self.config
        labels, unit_costs, quantities, fixed_costs = solver_vectors(config["treatments"])

        result = run_path_cost_effective_solver(
            final_df,
            labels,
            unit_costs,
            quantities,
            fixed_costs,
            sdyd_threshold=config["sdyd_threshold"],
            sddc_threshold=config["sddc_threshold"],
            slope_range=_solver_slope_range(config),
            bs_threshold=config["severity_filter"],
        )
        self._persist_solver_outputs(final_df, result, config)
        return result

    def _persist_solver_outputs(
        self,
        final_df: pd.DataFrame,
        result: SolverResult,
        config: Mapping[str, Any],
    ) -> None:
        treatment_by_label = {t["label"]: t for t in config["treatments"]}
        area_map = (
            pd.to_numeric(final_df.set_index(result.id_col)[result.area_col], errors="coerce")
            * ACRES_PER_HECTARE
        ).to_dict()

        rows: List[Dict[str, Any]] = []
        for label, ids in zip(result.treatments, result.treatment_hillslopes):
            vector = treatment_by_label[label]
            for site_id in ids:
                area_ac = float(area_map.get(site_id, float("nan")))
                rows.append(
                    {
                        result.id_col: int(site_id),
                        "treatment": label,
                        "scenario": vector["scenario"],
                        "area_ac": area_ac,
                        "unit_cost": vector["unit_cost"],
                        "quantity": vector["quantity"],
                        "cost": area_ac * vector["unit_cost"] * vector["quantity"],
                    }
                )
        selection = pd.DataFrame(
            rows,
            columns=[result.id_col, "treatment", "scenario", "area_ac", "unit_cost", "quantity", "cost"],
        )

        pq.write_table(_dataframe_to_table(selection), self.path_dir / SELECTION_TABLE)
        sdyd_df = result.sdyd_df.copy()
        sdyd_df["final_Sdyd"] = pd.to_numeric(sdyd_df["final_Sdyd"], errors="coerce")
        pq.write_table(_dataframe_to_table(sdyd_df), self.path_dir / SDYD_TABLE)
        pq.write_table(
            _dataframe_to_table(result.untreatable_sdyd), self.path_dir / UNTREATABLE_TABLE
        )
        increase_ids = (
            result.untreatable_sdyd_increase[[result.id_col]].copy()
            if len(result.untreatable_sdyd_increase)
            else pd.DataFrame({result.id_col: pd.Series(dtype="int64")})
        )
        pq.write_table(
            _dataframe_to_table(increase_ids), self.path_dir / UNTREATABLE_INCREASE_TABLE
        )

    # ------------------------------------------------------------------
    # Stage 4: threshold sweep (always-on, cache-keyed — D5)
    # ------------------------------------------------------------------
    def _sweep_cache_key(self, config: Mapping[str, Any]) -> str:
        payload = {
            "sweep_schema": 2,  # bump when the flattened column set changes
            "treatments": config["treatments"],
            "slope_range": config["slope_range"],
            "severity_filter": config["severity_filter"],
            "sdyd_anchor": int(config["sdyd_threshold"]),
            "sddc_anchor": int(config["sddc_threshold"]),
            "frame_sha256": _sha256_file(self.path_dir / PREPARED_FRAME),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def run_sweep(
        self, final_df: pd.DataFrame, config: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run (or reuse) the threshold sweep; persists sweep table + manifest."""
        if config is None:
            config = self.config
        cache_key = self._sweep_cache_key(config)
        manifest_path = self.path_dir / SWEEP_MANIFEST
        sweep_path = self.path_dir / SWEEP_TABLE

        if manifest_path.exists() and sweep_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except (ValueError, OSError):
                manifest = {}
            if manifest.get("cache_key") == cache_key:
                manifest["reused"] = True
                return manifest

        labels, unit_costs, quantities, fixed_costs = solver_vectors(config["treatments"])
        frame, labels, unit_costs, quantities, fixed_costs, id_col, area_col = (
            prepare_solver_inputs(final_df, labels, unit_costs, quantities, fixed_costs)
        )

        sddc_range, sdyd_range, _, _ = find_threshold_ranges(
            frame, labels, unit_costs, quantities, fixed_costs
        )
        results_df = all_thresholds(
            frame,
            labels,
            unit_costs,
            quantities,
            fixed_costs,
            sdyd_threshold_range=sdyd_range,
            sddc_threshold_range=sddc_range,
            sdyd_threshold=int(config["sdyd_threshold"]),
            sddc_threshold=int(config["sddc_threshold"]),
            slope_range=_solver_slope_range(config),
            bs_threshold=config["severity_filter"],
            id_col=id_col,
            area_col=area_col,
        )

        flat = results_df[
            [
                "sdyd_threshold",
                "sddc_threshold",
                "model_primary_status",
                "total_Sddc_reduction",
                "final_Sddc",
                "total_cost",
                "total_fixed_cost",
            ]
        ].copy()
        flat["model_primary_status"] = pd.to_numeric(
            flat["model_primary_status"], errors="coerce"
        )

        def _ids(value) -> str:
            if value is None:
                return "[]"
            return json.dumps([int(v) for v in value])

        flat["selected_hillslopes"] = [
            _ids(v) for v in results_df["selected_hillslopes"]
        ]
        flat["treatment_hillslopes"] = [
            json.dumps([[int(i) for i in t] for t in v]) if v is not None else "[]"
            for v in results_df["treatment_hillslopes"]
        ]
        flat["untreatable_ids"] = [
            _ids(df[id_col].tolist()) if df is not None and len(df) else "[]"
            for df in results_df["untreatable_sdyd"]
        ]
        # the report's interactive map derives per-slider untreatable sets from
        # the full [id, final_sdyd] pairs and styles the increase class separately
        flat["hillslopes_sdyd"] = [
            json.dumps([[int(i), float(v)] for i, v in pairs]) if pairs is not None else "[]"
            for pairs in results_df["hillslopes_sdyd"]
        ]
        flat["untreatable_sdyd_increase"] = [
            _ids(df[id_col].tolist()) if df is not None and len(df) else "[]"
            for df in results_df["untreatable_sdyd_increase"]
        ]

        if "error" in results_df.columns:
            errors = results_df["error"].fillna("")
        else:
            errors = pd.Series([""] * len(results_df))
        flat["error"] = errors.astype(str)
        n_errors = int((flat["error"] != "").sum())
        if n_errors == len(flat) and len(flat) > 0:
            first = flat.loc[flat["error"] != "", "error"].iloc[0]
            raise PathCESolverError(
                f"Threshold sweep failed on every cell ({n_errors}/{len(flat)}); first error: {first}"
            )

        pq.write_table(_dataframe_to_table(flat), sweep_path)
        manifest = {
            "cache_key": cache_key,
            "treatments": labels,
            "sdyd_threshold_range": list(sdyd_range),
            "sddc_threshold_range": list(sddc_range),
            "n_cells": int(len(flat)),
            "n_errors": n_errors,
            "reused": False,
        }
        manifest_path.write_text(json.dumps(manifest, indent=1))
        return manifest

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def run(
        self, status_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Execute validate → prepare → solve → sweep and persist results."""
        emit = status_callback or (lambda message: None)
        # one immutable snapshot threads through every stage so a mid-run
        # config POST cannot mix treatment sets between stages
        config = self.config

        try:
            emit("Validating Omni artifact preconditions")
            self.set_status("running", message="Validating Omni artifact preconditions", progress=0.05)
            self._set_precondition_errors([])
            report = self.validate(config)
            if not report.ok:
                self._set_precondition_errors(report.errors)
                raise PathCEPreconditionError(report)
            for warning in report.warnings:
                emit(f"WARNING {warning}")

            emit("Preparing PATH model frame from Omni artifacts")
            self.set_status("running", message="Preparing PATH model frame", progress=0.2)
            final_df = self.prepare_data(report)

            emit("Running cost-effective site selection")
            self.set_status("running", message="Running cost-effective site selection", progress=0.45)
            solver_result = self.solve(final_df, config)

            emit("Running threshold sweep")
            self.set_status("running", message="Running threshold sweep", progress=0.6)
            sweep_manifest = self.run_sweep(final_df, config)

            report_relpath: Optional[str] = None
            report_skipped: Optional[str] = None
            if report.subcatchments_geojson is None:
                report_skipped = (
                    "subcatchments.WGS.geojson not found — report rendering skipped "
                    "(see precondition warnings)."
                )
                emit(f"WARNING {report_skipped}")
            else:
                emit("Rendering HTML report (Quarto)")
                self.set_status("running", message="Rendering HTML report", progress=0.85)
                report_relpath = render_report(
                    self.wd,
                    config,
                    self._artifact_relpaths(),
                    report.subcatchments_geojson,
                    report.channels_geojson,
                )
        except (PathCEPreconditionError, PathCESolverError, PathCEReportError, ValueError) as exc:
            self.set_status("failed", message=str(exc))
            raise
        except Exception as exc:
            self.set_status("failed", message=f"PATH-CE run failed: {exc}")
            raise

        payload = {
            "primary_status": solver_result.primary_status,
            "used_secondary": solver_result.used_secondary,
            "schema_mode": report.mode,
            "id_col": solver_result.id_col,
            "treatments": solver_result.treatments,
            "selected_hillslopes": [int(i) for i in solver_result.selected_hillslopes],
            "treatment_hillslopes": [
                [int(i) for i in ids] for ids in solver_result.treatment_hillslopes
            ],
            "total_cost": solver_result.total_cost,
            "total_fixed_cost": solver_result.total_fixed_cost,
            "total_sddc_reduction": solver_result.total_sddc_reduction,
            "final_sddc": solver_result.final_sddc,
            "n_untreatable": int(len(solver_result.untreatable_sdyd)),
            "n_untreatable_increase": int(len(solver_result.untreatable_sdyd_increase)),
            "precondition_warnings": list(report.warnings),
            "sweep": {
                "sdyd_threshold_range": sweep_manifest.get("sdyd_threshold_range"),
                "sddc_threshold_range": sweep_manifest.get("sddc_threshold_range"),
                "n_cells": sweep_manifest.get("n_cells"),
                "n_errors": sweep_manifest.get("n_errors", 0),
                "reused": sweep_manifest.get("reused", False),
            },
            "report": {
                "html": report_relpath,
                "skipped_reason": report_skipped,
            },
            "artifacts": self._artifact_relpaths(),
            "config_snapshot": config,
        }

        self.store_results(payload)
        self._refresh_catalog()
        return payload

    def _artifact_relpaths(self) -> Dict[str, str]:
        rel = self.path_dir.name
        return {
            "prepared_frame": f"{rel}/{PREPARED_FRAME}",
            "hillslope_agg": f"{rel}/{PREP_PREFIX}_hillslope_agg.parquet",
            "outlet_agg": f"{rel}/{PREP_PREFIX}_outlet_agg.parquet",
            "char_agg": f"{rel}/{PREP_PREFIX}_char_agg.parquet",
            "selection": f"{rel}/{SELECTION_TABLE}",
            "sdyd": f"{rel}/{SDYD_TABLE}",
            "untreatable": f"{rel}/{UNTREATABLE_TABLE}",
            "untreatable_increase": f"{rel}/{UNTREATABLE_INCREASE_TABLE}",
            "sweep": f"{rel}/{SWEEP_TABLE}",
            "sweep_manifest": f"{rel}/{SWEEP_MANIFEST}",
        }

    def _refresh_catalog(self) -> None:
        if _update_catalog_entry is None:
            return
        try:
            relative_dir = str(self.path_dir.relative_to(self.wd))
        except ValueError:
            relative_dir = self.path_dir.name
        try:
            _update_catalog_entry(self.wd, relative_dir)
        except Exception:  # pragma: no cover - best effort
            LOGGER.warning(
                "Failed to refresh catalog for PATH CE artifacts in %s", self.wd, exc_info=True
            )
