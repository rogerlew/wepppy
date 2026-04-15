from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.schemas import (
    build_progress_payload,
    empty_progress_payload,
    validate_lifecycle_state,
)

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


class GenevaResultsService:
    """Aggregate Geneva run outputs and build API payload views."""

    def summarize_batch_run(
        self,
        geneva: "Geneva",
        batch_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        storm_results = list(batch_result.get("storm_results", []) or [])
        unavailable_cells = list(batch_result.get("unavailable_cells", []) or [])

        completed = [entry for entry in storm_results if entry.get("status") == "completed"]
        failed = [entry for entry in storm_results if entry.get("status") == "failed"]

        storm_count_total = len(storm_results) + len(unavailable_cells)
        storm_count_completed = len(completed)
        storm_count_failed = len(failed)
        storm_count_unavailable = len(unavailable_cells)

        warnings = []
        for entry in completed:
            for warning in entry.get("warnings", []) or []:
                warnings.append(warning)
        for cell in unavailable_cells:
            warnings.append(
                {
                    "code": str(cell.get("reason_code") or "source_missing"),
                    "storm_id": str(cell.get("storm_id", "")),
                }
            )

        errors = [
            {
                "storm_id": str(entry.get("storm_id", "")),
                "message": str(entry.get("error", "unknown error")),
            }
            for entry in failed
        ]

        status = "completed"
        if storm_count_failed > 0:
            status = "failed"
        elif storm_count_unavailable > 0:
            status = "completed_with_gaps"

        run_summary = {
            "batch_id": batch_result.get("batch_id"),
            "datasource_ids": sorted(
                {
                    str(cell.get("datasource_id"))
                    for cell in list(batch_result.get("available_cells", [])) + unavailable_cells
                    if cell.get("datasource_id")
                }
            ),
            "storm_count_total": storm_count_total,
            "storm_count_completed": storm_count_completed,
            "storm_count_failed": storm_count_failed,
            "storm_count_unavailable": storm_count_unavailable,
            "failed_storm_ids": [str(item.get("storm_id", "")) for item in failed],
            "warnings": warnings,
            "errors": errors,
            "artifacts": {
                "batch_summary_relpath": "geneva/batch_summary.json",
                "frequency_panel_relpath": "geneva/frequency_panel.json",
                "storm_inputs_relpath": f"geneva/{batch_result.get('storm_inputs_relpath', 'storm_inputs.json')}",
            },
            "status": status,
        }

        geneva.artifact_io.write_json(geneva.wd, "batch_summary.json", run_summary)
        return run_summary

    def build_status_payload(self, geneva: "Geneva") -> dict[str, Any]:
        progress = dict(getattr(geneva, "_progress", {}) or {})
        if not progress:
            progress = empty_progress_payload()

        return {
            "status": validate_lifecycle_state(str(getattr(geneva, "_status", "idle"))),
            "status_message": str(getattr(geneva, "_status_message", "")),
            "progress": progress,
            "active_job_id": getattr(geneva, "_active_job_id", None),
            "last_job_id": getattr(geneva, "_last_job_id", None),
        }

    def build_results_payload(self, geneva: "Geneva") -> dict[str, Any]:
        return {
            "status": validate_lifecycle_state(str(getattr(geneva, "_status", "idle"))),
            "last_prepare_summary": dict(getattr(geneva, "_hru_summary", {}) or {}),
            "last_run_summary": dict(getattr(geneva, "_run_summary", {}) or {}),
            "warnings": list(getattr(geneva, "_warnings", []) or []),
            "errors": list(getattr(geneva, "_errors", []) or []),
        }

    def progress_for_batch(self, *, completed: int, total: int) -> dict[str, Any]:
        return build_progress_payload(completed=completed, total=total, unit="storms")


__all__ = ["GenevaResultsService"]
