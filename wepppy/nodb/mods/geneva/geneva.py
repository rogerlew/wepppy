from __future__ import annotations

from typing import Any, Mapping

import time

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.geneva.collaborators import (
    GenevaArtifactIO,
    GenevaBatchRunService,
    GenevaCnTableService,
    GenevaConfigService,
    GenevaFrequencyPanelService,
    GenevaHruEventMeasureService,
    GenevaHruMapGeometryService,
    GenevaHruPreparationService,
    GenevaHsgAssignmentService,
    GenevaKernelGateway,
    GenevaReportPayloadService,
    GenevaResultsService,
)
from wepppy.nodb.mods.geneva.errors import GenevaNoDbError, GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import (
    empty_progress_payload,
    validate_lifecycle_state,
)

__all__ = [
    "Geneva",
    "GenevaNoDbError",
]


_GENEVA_ARTIFACT_IO = GenevaArtifactIO()
_GENEVA_CONFIG_SERVICE = GenevaConfigService()
_GENEVA_CN_TABLE_SERVICE = GenevaCnTableService()
_GENEVA_HSG_ASSIGNMENT_SERVICE = GenevaHsgAssignmentService()
_GENEVA_KERNEL_GATEWAY = GenevaKernelGateway()
_GENEVA_HRU_PREPARATION_SERVICE = GenevaHruPreparationService()
_GENEVA_FREQUENCY_PANEL_SERVICE = GenevaFrequencyPanelService()
_GENEVA_BATCH_RUN_SERVICE = GenevaBatchRunService()
_GENEVA_HRU_EVENT_MEASURE_SERVICE = GenevaHruEventMeasureService()
_GENEVA_HRU_MAP_GEOMETRY_SERVICE = GenevaHruMapGeometryService()
_GENEVA_RESULTS_SERVICE = GenevaResultsService()
_GENEVA_REPORT_PAYLOAD_SERVICE = GenevaReportPayloadService()


class Geneva(NoDbBase):
    """NoDb facade for Geneva orchestration with collaborator services."""

    __name__ = "Geneva"
    filename = "geneva.nodb"

    def __init__(
        self,
        wd: str,
        cfg_fn: str = "0.cfg",
        run_group: str | None = None,
        group_name: str | None = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._enabled = bool(getattr(self, "_enabled", False))
            self._status = self._normalize_status(getattr(self, "_status", "idle"))
            self._status_message = str(getattr(self, "_status_message", "Waiting for configuration."))
            self._progress = dict(getattr(self, "_progress", {}) or empty_progress_payload())
            self._active_job_id = getattr(self, "_active_job_id", None)
            self._last_job_id = getattr(self, "_last_job_id", None)

            self._input_refs = dict(getattr(self, "_input_refs", {}) or {})
            self._storm_batch = dict(getattr(self, "_storm_batch", {}) or {})
            self._hru_summary = dict(getattr(self, "_hru_summary", {}) or {})
            self._run_summary = dict(getattr(self, "_run_summary", {}) or {})
            self._warnings = list(getattr(self, "_warnings", []) or [])
            self._errors = list(getattr(self, "_errors", []) or [])
            self._timestamps = dict(getattr(self, "_timestamps", {}) or {})
            self._config_user_modified = bool(getattr(self, "_config_user_modified", False))

            self.config_service.initialize_config(self)
            self._config["enabled"] = bool(self._enabled)
            self._apply_default_enabled_state_locked()
            self.artifact_io.root_dir(self.wd)
            self.cn_table_service.ensure_initialized(self, reason="init")

    @property
    def artifact_io(self) -> GenevaArtifactIO:
        return _GENEVA_ARTIFACT_IO

    @property
    def config_service(self) -> GenevaConfigService:
        return _GENEVA_CONFIG_SERVICE

    @property
    def cn_table_service(self) -> GenevaCnTableService:
        return _GENEVA_CN_TABLE_SERVICE

    @property
    def hsg_assignment_service(self) -> GenevaHsgAssignmentService:
        return _GENEVA_HSG_ASSIGNMENT_SERVICE

    @property
    def kernel_gateway(self) -> GenevaKernelGateway:
        return _GENEVA_KERNEL_GATEWAY

    @property
    def hru_preparation_service(self) -> GenevaHruPreparationService:
        return _GENEVA_HRU_PREPARATION_SERVICE

    @property
    def frequency_panel_service(self) -> GenevaFrequencyPanelService:
        return _GENEVA_FREQUENCY_PANEL_SERVICE

    @property
    def batch_run_service(self) -> GenevaBatchRunService:
        return _GENEVA_BATCH_RUN_SERVICE

    @property
    def hru_event_measure_service(self) -> GenevaHruEventMeasureService:
        return _GENEVA_HRU_EVENT_MEASURE_SERVICE

    @property
    def hru_map_geometry_service(self) -> GenevaHruMapGeometryService:
        return _GENEVA_HRU_MAP_GEOMETRY_SERVICE

    @property
    def results_service(self) -> GenevaResultsService:
        return _GENEVA_RESULTS_SERVICE

    @property
    def report_payload_service(self) -> GenevaReportPayloadService:
        return _GENEVA_REPORT_PAYLOAD_SERVICE

    @property
    def enabled(self) -> bool:
        return bool(self._enabled)

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        requested = bool(enabled)
        if requested:
            self.hsg_assignment_service.enforce_wbt_backend(self)
            self.hsg_assignment_service.enforce_supported_domain(self)
            self.artifact_io.root_dir(self.wd)

        with self.locked():
            effective_enabled = True
            self._enabled = effective_enabled
            self._config["enabled"] = effective_enabled
            self._timestamps["enabled"] = int(time.time())
            if requested:
                self._status_message = "Geneva enabled."
            else:
                self._status_message = "Geneva enablement follows mod membership."

        return {
            "enabled": effective_enabled,
            "status": self._status,
        }

    def get_config(self) -> dict[str, Any]:
        payload = self.config_service.get_config(self)
        payload["enabled"] = self.enabled
        return payload

    def update_config(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        updates = dict(payload)
        updates.pop("enabled", None)
        try:
            with self.locked():
                before = dict(self._config)
                updated = self.config_service.update_config(self, updates)
                updated["enabled"] = self.enabled
                self._config["enabled"] = self.enabled
                self._config_user_modified = True
                if before != updated:
                    self._status_message = "Configuration updated."
                    if self._status in {"prepared", "running", "completed", "completed_with_gaps", "failed"}:
                        self._clear_runtime_state_locked()
        except ValueError as exc:
            raise GenevaValidationError(
                str(exc),
                code="invalid_input",
                details=str(exc),
                status_code=400,
            ) from exc
        return updated

    def prepare_hrus(
        self,
        *,
        force_rebuild: bool = False,
        input_refs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_enabled()
        self.hsg_assignment_service.enforce_wbt_backend(self)
        self.hsg_assignment_service.enforce_supported_domain(self)

        with self.locked():
            self._status = "running"
            self._status_message = "Preparing Geneva HRUs..."
            self._progress = empty_progress_payload()
            self._errors = []
            self._timestamps["running"] = int(time.time())

        try:
            summary = self.hru_preparation_service.prepare_hrus(
                self,
                force_rebuild=force_rebuild,
                input_refs=input_refs,
            )
        except GenevaNoDbError as exc:
            self._record_failure(exc)
            raise

        with self.locked():
            self._input_refs = dict(summary.get("input_refs", {}) or {})
            self._hru_summary = dict(summary)
            self._warnings = list(summary.get("warnings", []) or [])
            self._errors = []
            self._status = "prepared"
            self._status_message = "Geneva HRU preparation completed."
            self._progress = empty_progress_payload()
            self._timestamps["prepared"] = int(time.time())

        return summary

    def build_frequency_panel(
        self,
        *,
        durations_minutes: list[int] | tuple[int, ...] | None = None,
        ari_years: list[int] | tuple[int, ...] | None = None,
        rebuild: bool = False,
        sources: Mapping[str, str | None] | None = None,
        distribution_type: str = "neh4_type_b",
    ) -> dict[str, Any]:
        self._require_enabled()
        self.hsg_assignment_service.enforce_wbt_backend(self)
        self.hsg_assignment_service.enforce_supported_domain(self)

        try:
            panel = self.frequency_panel_service.build_frequency_panel(
                self,
                durations_minutes=durations_minutes,
                ari_years=ari_years,
                rebuild=rebuild,
                sources=sources,
                distribution_type=distribution_type,
            )
        except GenevaNoDbError as exc:
            self._record_failure(exc)
            raise

        with self.locked():
            previous_distribution = str(
                (
                    (self._storm_batch.get("frequency_panel", {}) or {})
                    if isinstance(self._storm_batch, dict)
                    else {}
                ).get("distribution_type")
                or ""
            )
            next_distribution = str(panel.get("distribution_type") or "neh4_type_b")
            if (
                previous_distribution
                and previous_distribution != next_distribution
            ):
                self._run_summary = {}
                self._errors = []
                if self._status in {"completed", "completed_with_gaps", "failed"}:
                    self._status = "prepared"
                    self._progress = empty_progress_payload()

            self._storm_batch = {
                "frequency_panel": {
                    "datasource_ids": list(panel.get("datasource_ids", []) or []),
                    "durations_minutes": list(panel.get("durations_minutes", []) or []),
                    "ari_years": list(panel.get("ari_years", []) or []),
                    "distribution_type": next_distribution,
                }
            }
            self._warnings = list(panel.get("warnings", []) or [])
            self._errors = []
            if self._status == "idle":
                self._status = "prepared"
            self._status_message = "Frequency panel ready."
            self._timestamps["prepared"] = int(time.time())

        return panel

    def run_batch(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._require_enabled()
        self.hsg_assignment_service.enforce_wbt_backend(self)
        self.hsg_assignment_service.enforce_supported_domain(self)

        with self.locked():
            self._status = "running"
            self._status_message = "Running Geneva storm batch..."
            self._errors = []
            self._timestamps["running"] = int(time.time())

        try:
            batch_result = self.batch_run_service.run_batch(self, payload)
            run_summary = self.results_service.summarize_batch_run(self, batch_result)
        except GenevaNoDbError as exc:
            self._record_failure(exc)
            raise

        progress = self.results_service.progress_for_batch(
            completed=int(run_summary.get("storm_count_completed", 0) or 0),
            total=int(run_summary.get("storm_count_total", 0) or 0),
        )
        terminal_status = self._normalize_status(str(run_summary.get("status", "failed")))

        with self.locked():
            self._run_summary = dict(run_summary)
            self._warnings = list(run_summary.get("warnings", []) or [])
            self._errors = list(run_summary.get("errors", []) or [])
            self._status = terminal_status
            self._status_message = self._status_message_for_terminal_state(terminal_status)
            self._progress = progress
            self._timestamps[terminal_status] = int(time.time())

        return run_summary

    def status_payload(self) -> dict[str, Any]:
        return self.results_service.build_status_payload(self)

    def results_payload(self) -> dict[str, Any]:
        return self.results_service.build_results_payload(self)

    def state_payload(self) -> dict[str, Any]:
        return self.results_service.build_state_payload(self)

    def frequency_panel_payload(self) -> dict[str, Any]:
        return self.frequency_panel_service.get_frequency_panel(self)

    def query_summary_payload(
        self,
        *,
        datasource_id: str = "all",
        ari_years: list[int] | tuple[int, ...] | None = None,
        measure: str = "peak_discharge",
        selected_storm_id: str | None = None,
    ) -> dict[str, Any]:
        return self.report_payload_service.build_summary_payload(
            self,
            datasource_id=datasource_id,
            ari_years=ari_years,
            measure=measure,
            selected_storm_id=selected_storm_id,
        )

    def query_hru_map_rows_payload(
        self,
        *,
        storm_id: str,
        measure_id: str,
        include_schema: bool = True,
        limit: int | None = None,
    ) -> dict[str, Any]:
        return self.hru_event_measure_service.query_rows(
            self,
            storm_id=storm_id,
            measure_id=measure_id,
            include_schema=include_schema,
            limit=limit,
        )

    def query_hru_map_features_payload(self) -> dict[str, Any]:
        return self.hru_map_geometry_service.query_feature_collection(self)

    def assert_task_guardrails(self) -> None:
        self._require_enabled()
        self.hsg_assignment_service.enforce_wbt_backend(self)
        self.hsg_assignment_service.enforce_supported_domain(self)

    def mark_job_queued(self, job_id: str, *, status_message: str) -> None:
        now = int(time.time())
        with self.locked():
            self._active_job_id = job_id
            self._last_job_id = job_id
            self._status = "running"
            self._status_message = status_message
            self._progress = empty_progress_payload()
            self._timestamps["running"] = now

    def mark_job_started(self, job_id: str, *, status_message: str) -> None:
        now = int(time.time())
        with self.locked():
            self._active_job_id = job_id
            self._last_job_id = job_id
            self._status = "running"
            self._status_message = status_message
            self._timestamps["running"] = now

    def mark_job_finished(self, job_id: str) -> None:
        with self.locked():
            if self._active_job_id == job_id:
                self._active_job_id = None
            self._last_job_id = job_id
            self._timestamps["last_job_finished"] = int(time.time())

    def cn_table_meta(self) -> dict[str, Any]:
        with self.locked():
            return self.cn_table_service.meta(self)

    def cn_table_snapshot(self) -> dict[str, Any]:
        with self.locked():
            return self.cn_table_service.snapshot(self)

    def modify_cn_table(
        self,
        rows: list[Any],
        *,
        if_match_sha256: str | None,
    ) -> dict[str, Any]:
        with self.locked():
            return self.cn_table_service.modify(
                self,
                rows,
                if_match_sha256=if_match_sha256,
            )

    def reset_cn_table(self, *, reason: str = "manual") -> dict[str, Any]:
        with self.locked():
            return self.cn_table_service.reset(self, reason=reason)

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise GenevaValidationError(
                "Geneva mod is disabled.",
                code="mod_disabled",
                details="Enable Geneva before running this action.",
            )

    def _apply_default_enabled_state_locked(self) -> None:
        """Geneva enablement follows mod membership; keep active whenever mod is present."""
        if self._enabled:
            self._config["enabled"] = True
            return

        self._enabled = True
        self._config["enabled"] = True
        self._status_message = "Geneva enabled."
        if "enabled" not in self._timestamps:
            self._timestamps["enabled"] = int(time.time())

    def _record_failure(self, error: GenevaNoDbError) -> None:
        payload = error.to_error_payload()["error"]
        with self.locked():
            self._status = "failed"
            self._status_message = payload["message"]
            self._errors = [payload]
            self._timestamps["failed"] = int(time.time())

    def _clear_runtime_state_locked(self) -> None:
        self._status = "idle"
        self._progress = empty_progress_payload()
        self._active_job_id = None
        self._input_refs = {}
        self._storm_batch = {}
        self._hru_summary = {}
        self._run_summary = {}
        self._warnings = []
        self._errors = []

    def _normalize_status(self, raw: Any) -> str:
        try:
            return validate_lifecycle_state(str(raw))
        except ValueError:
            return "idle"

    def _status_message_for_terminal_state(self, status: str) -> str:
        if status == "completed":
            return "Geneva batch completed."
        if status == "completed_with_gaps":
            return "Geneva batch completed with unavailable storms."
        if status == "failed":
            return "Geneva batch failed."
        return "Geneva batch updated."
