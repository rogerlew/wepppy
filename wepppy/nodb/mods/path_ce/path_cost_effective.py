"""Cost-effective mitigation path optimizer.

This module provides the ``PathCostEffective`` NoDb controller which ranks
post-fire mitigation treatments (mulch, seeding, road upgrades) by cost and
sediment reduction benefit. The workflow loads treatment parameters from Parquet
summaries, runs the linear programming solver, and writes an interchange bundle
so downstream UI panels and WEPP runs stay in sync.

It relies on helper utilities in ``data_loader`` and ``path_ce_solver`` for
Parquet ingestion and pulp-based optimization respectively.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange.schema_utils import pa_field
from wepppy.nodb.base import NoDbBase, nodb_setter

from .data_loader import (
    PathCEDataError,
    SolverInputs,
    TreatmentOption,
    load_solver_inputs,
)
from .path_ce_solver import (
    PathCESolverError,
    SolverResult,
    run_path_cost_effective_solver,
)

__all__ = ["PathCostEffective"]

LOGGER = logging.getLogger(__name__)

DEFAULT_TREATMENT_OPTIONS: List[Dict[str, Any]] = [
    {
        "label": "Mulch 0.5 tons/acre",
        "scenario": "mulch_15_sbs_map",
        "quantity": 0.5,
        "unit_cost": 0.0,
        "fixed_cost": 0.0,
    },
    {
        "label": "Mulch 1.0 tons/acre",
        "scenario": "mulch_30_sbs_map",
        "quantity": 1.0,
        "unit_cost": 0.0,
        "fixed_cost": 0.0,
    },
    {
        "label": "Mulch 2.0 tons/acre",
        "scenario": "mulch_60_sbs_map",
        "quantity": 2.0,
        "unit_cost": 0.0,
        "fixed_cost": 0.0,
    },
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "post_fire_scenario": "sbs_map",
    "undisturbed_scenario": "undisturbed",
    "sdyd_threshold": 0.0,
    "sddc_threshold": 0.0,
    "slope_range": [None, None],
    "severity_filter": None,
    "treatment_options": DEFAULT_TREATMENT_OPTIONS,
}


def _normalize_config(value: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(DEFAULT_CONFIG)
    incoming = dict(value or {})
    normalized.update({k: v for k, v in incoming.items() if k in normalized})

    normalized["treatment_options"] = _normalize_treatment_options(
        incoming.get("treatment_options", normalized["treatment_options"])
    )

    return normalized


def _normalize_treatment_options(options: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not options:
        options = DEFAULT_TREATMENT_OPTIONS

    for option in options:
        if not isinstance(option, Mapping):
            continue
        label = str(option.get("label") or option.get("name") or "")
        scenario = option.get("scenario")
        if not label or not scenario:
            continue
        normalized.append(
            {
                "label": label,
                "scenario": str(scenario),
                "quantity": float(option.get("quantity", 0.0) or 0.0),
                "unit_cost": float(option.get("unit_cost", 0.0) or 0.0),
                "fixed_cost": float(option.get("fixed_cost", 0.0) or 0.0),
            }
        )
    if not normalized:
        normalized = DEFAULT_TREATMENT_OPTIONS
    return normalized


def _hydrate_treatment_options(config: Mapping[str, Any]) -> List[TreatmentOption]:
    options = config.get("treatment_options", [])
    hydrated: List[TreatmentOption] = []
    for option in options:
        hydrated.append(
            TreatmentOption(
                label=str(option["label"]),
                scenario=str(option["scenario"]),
                quantity=float(option.get("quantity", 0.0) or 0.0),
                unit_cost=float(option.get("unit_cost", 0.0) or 0.0),
                fixed_cost=float(option.get("fixed_cost", 0.0) or 0.0),
            )
        )
    return hydrated


def _coerce_slope_range(config: Mapping[str, Any]) -> Optional[Tuple[Optional[float], Optional[float]]]:
    slope_range = config.get("slope_range")
    if not slope_range:
        return None
    if not isinstance(slope_range, Sequence) or len(slope_range) != 2:
        return None
    min_slope = slope_range[0]
    max_slope = slope_range[1]
    min_value = float(min_slope) if min_slope is not None else None
    max_value = float(max_slope) if max_slope is not None else None
    if min_value is None and max_value is None:
        return None
    return (min_value, max_value)


def _prepare_severity_filter(config: Mapping[str, Any]) -> Optional[List[str]]:
    severity = config.get("severity_filter")
    if severity is None:
        return None
    if isinstance(severity, str):
        return [severity]
    try:
        return [str(item) for item in severity if item is not None]
    except TypeError:
        return None


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


class PathCostEffective(NoDbBase):
    """
    NoDb controller for the PATH cost-effective optimization model.

    The controller coordinates configuration, tracks solver status, and
    persists intermediate and final outputs under ``<wd>/path`` so other
    services (RQ workers, Flask routes, client controllers) can consume
    results without re-running the optimization.
    """

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
            if not hasattr(self, "_path_dir"):
                self._path_dir = str(self._ensure_path_dir())
            else:
                self._ensure_path_dir()

            if not hasattr(self, "_config"):
                self._config = _normalize_config({})

            if not hasattr(self, "_results"):
                self._results: Dict[str, Any] = {}

            if not hasattr(self, "_status"):
                self._status: str = "idle"

            if not hasattr(self, "_status_message"):
                self._status_message: str = "Waiting for configuration."

            if not hasattr(self, "_progress"):
                self._progress: float = 0.0

    # ------------------------------------------------------------------
    # Paths & directories
    # ------------------------------------------------------------------
    def _ensure_path_dir(self) -> Path:
        path_dir = Path(self.wd) / "path"
        path_dir.mkdir(parents=True, exist_ok=True)
        return path_dir

    @property
    def path_dir(self) -> Path:
        """Working directory used to stage solver artifacts."""
        return Path(self._path_dir)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @property
    def config(self) -> Dict[str, Any]:
        """Return a shallow copy of the current configuration payload."""
        return dict(self._config)

    @config.setter  # type: ignore[override]
    @nodb_setter
    def config(self, value: Mapping[str, Any]) -> None:
        self._config = _normalize_config(value)
        self._status = "configured"
        self._status_message = "Configuration updated."
        self._progress = 0.0

    # ------------------------------------------------------------------
    # Results & status management
    # ------------------------------------------------------------------
    @property
    def results(self) -> Dict[str, Any]:
        """Return the most recent solver results (if any)."""
        return dict(self._results)

    def clear_results(self) -> None:
        """Reset stored results and progress markers."""
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
        """
        Update solver status fields in a single locked operation.

        Parameters
        ----------
        status:
            High-level state indicator (e.g., ``running``, ``completed``).
        message:
            Optional human-readable detail describing the state change.
        progress:
            Optional progress fraction between ``0.0`` and ``1.0``.
        """
        with self.locked():
            self._status = status
            if message is not None:
                self._status_message = message
            if progress is not None:
                self._progress = max(0.0, min(1.0, progress))

    def store_results(self, results: Mapping[str, Any]) -> None:
        """Persist solver results and mark the controller as completed."""
        with self.locked():
            self._results = dict(results)
            self._status = "completed"
            self._status_message = "Solver run complete."
            self._progress = 1.0

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
    # Execution
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        """Execute the PATH cost-effective workflow."""
        config = self.config
        treatment_options = _hydrate_treatment_options(config)

        try:
            self.set_status("running", message="Loading PATH inputs", progress=0.1)
            solver_inputs = load_solver_inputs(
                self.wd,
                post_fire_scenario=str(config.get("post_fire_scenario", "sbs_map")),
                undisturbed_scenario=config.get("undisturbed_scenario"),
                treatment_options=treatment_options,
            )
        except PathCEDataError as exc:
            self.set_status("failed", message=str(exc))
            raise

        slope_range = _coerce_slope_range(config)
        severity_filter = _prepare_severity_filter(config)
        sdyd_threshold = float(config.get("sdyd_threshold", 0.0) or 0.0)
        sddc_threshold = float(config.get("sddc_threshold", 0.0) or 0.0)

        try:
            self.set_status("running", message="Running optimization model", progress=0.55)
            solver_result = run_path_cost_effective_solver(
                data=solver_inputs.data,
                treatments=solver_inputs.treatments,
                treatment_cost=solver_inputs.treatment_costs,
                treatment_quantity=solver_inputs.treatment_quantities,
                fixed_cost=solver_inputs.fixed_costs,
                sdyd_threshold=sdyd_threshold,
                sddc_threshold=sddc_threshold,
                slope_range=slope_range,
                severity_filter=severity_filter,
                logger=self.logger,
            )
        except PathCESolverError as exc:
            self.set_status("failed", message=str(exc))
            raise

        try:
            self.set_status("running", message="Persisting solver outputs", progress=0.85)
            artifact_paths = self._persist_solver_outputs(solver_inputs, solver_result)
        except Exception as exc:  # pragma: no cover - filesystem errors
            self.set_status("failed", message=f"Failed to persist solver outputs: {exc}")
            raise

        payload = {
            "status": solver_result.status,
            "used_secondary": solver_result.used_secondary,
            "selected_hillslopes": solver_result.selected_hillslopes,
            "treatment_hillslopes": solver_result.treatment_hillslopes,
            "total_cost": solver_result.total_cost,
            "total_fixed_cost": solver_result.total_fixed_cost,
            "total_sddc_reduction": solver_result.total_sddc_reduction,
            "final_sddc": solver_result.final_sddc,
            "analysis_artifact": artifact_paths["analysis"],
            "sdyd_artifact": artifact_paths["sdyd"],
            "untreatable_artifact": artifact_paths["untreatable"],
            "config_snapshot": config,
        }

        self.store_results(payload)
        return payload

    def _persist_solver_outputs(self, inputs: SolverInputs, result: SolverResult) -> Dict[str, str]:
        """Serialize solver inputs/results to parquet."""
        analysis_path = self.path_dir / "analysis_frame.parquet"
        sdyd_path = self.path_dir / "hillslope_sdyd.parquet"
        untreatable_path = self.path_dir / "untreatable_hillslopes.parquet"

        pq.write_table(_dataframe_to_table(inputs.data), analysis_path)
        pq.write_table(_dataframe_to_table(result.hillslopes_sdyd), sdyd_path)
        pq.write_table(_dataframe_to_table(result.untreatable_sdyd), untreatable_path)

        return {
            "analysis": str(analysis_path.relative_to(self.wd)),
            "sdyd": str(sdyd_path.relative_to(self.wd)),
            "untreatable": str(untreatable_path.relative_to(self.wd)),
        }
