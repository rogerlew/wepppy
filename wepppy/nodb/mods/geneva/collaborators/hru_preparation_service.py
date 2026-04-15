from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaKernelError

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva

_HRU_TABLE_COLUMNS = [
    "hru_id",
    "area_m2",
    "area_ac",
    "area_fraction",
    "landuse_class",
    "hsg_group",
    "burn_severity_class",
    "hydrophobic_class",
    "is_water",
    "cn_arc_ii",
    "cn_lambda_020",
    "cn_lambda_005",
    "antecedent_condition_source",
    "cn_source",
    "hsg_source",
    "collapsed_from_hru_ids",
    "warnings",
]


class GenevaHruPreparationService:
    """Orchestrate HRU preparation kernel calls and artifact persistence."""

    def prepare_hrus(
        self,
        geneva: "Geneva",
        *,
        force_rebuild: bool = False,
        input_refs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        artifact_io = geneva.artifact_io
        if not force_rebuild and artifact_io.exists(geneva.wd, "hru_prepare_summary.json"):
            return artifact_io.read_json(geneva.wd, "hru_prepare_summary.json")

        resolved_refs = geneva.hsg_assignment_service.resolve_prepare_input_refs(
            geneva,
            overrides=input_refs,
        )
        config = dict(geneva._config)
        default_hsg_code, default_hsg_derivation = geneva.hsg_assignment_service.resolve_default_hsg(config)

        payload: dict[str, Any] = {
            "kernel_schema_version": 1,
            "bound_tif": resolved_refs["bound_tif"],
            "landuse_tif": resolved_refs["landuse_tif"],
            "hydgrpdcd_tif": resolved_refs["hydgrpdcd_tif"],
            "default_hsg_code": default_hsg_code,
            "default_hsg_derivation": default_hsg_derivation,
            "unresolved_hsg_policy": config["unresolved_hsg_policy"],
            "strict_burn_nodata": bool(config["strict_burn_nodata"]),
            "allow_cross_hsg_merge": bool(config["allow_cross_hsg_merge"]),
            "min_hru_area_ha": float(config["min_hru_area_ha"]),
            "hydrophobic_forest_high": bool(config["hydrophobic_forest_high"]),
            "hydrophobic_forest_moderate": bool(config["hydrophobic_forest_moderate"]),
            "hydrophobic_shrub_high": bool(config["hydrophobic_shrub_high"]),
            "hydrophobic_shrub_moderate": bool(config["hydrophobic_shrub_moderate"]),
        }
        if "burn_severity_tif" in resolved_refs:
            payload["burn_severity_tif"] = resolved_refs["burn_severity_tif"]

        response = geneva.kernel_gateway.call_json_api("geneva_prepare_hrus", payload)

        hru_rows = response.get("hru_rows")
        if not isinstance(hru_rows, list) or not hru_rows:
            raise GenevaKernelError(
                "geneva_prepare_hrus returned no HRU rows.",
                code="contract_violation",
                details={"response_keys": sorted(response.keys())},
            )

        diagnostics = response.get("diagnostics")
        if not isinstance(diagnostics, dict):
            raise GenevaKernelError(
                "geneva_prepare_hrus returned invalid diagnostics payload.",
                code="contract_violation",
            )

        warnings = response.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = []

        hru_table_relpath = artifact_io.write_records_parquet(
            geneva.wd,
            "hru_table.parquet",
            hru_rows,
            columns=_HRU_TABLE_COLUMNS,
        )

        summary: dict[str, Any] = {
            "status": "ok",
            "phase": "prepare_hrus",
            "hru_count": len(hru_rows),
            "hru_area_total_m2": float(diagnostics.get("hru_area_total_m2", 0.0) or 0.0),
            "hru_area_total_acres": float(diagnostics.get("hru_area_total_m2", 0.0) or 0.0)
            * 0.0002471053814671653,
            "hsg_provenance_counts": diagnostics.get("hsg_provenance_counts", {}),
            "warnings": warnings,
            "input_refs": resolved_refs,
            "artifacts": {
                "hru_table_relpath": hru_table_relpath,
                "hru_prepare_summary_relpath": "hru_prepare_summary.json",
            },
        }
        artifact_io.write_json(geneva.wd, "hru_prepare_summary.json", summary)
        return summary


__all__ = ["GenevaHruPreparationService"]
