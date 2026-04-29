from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.collaborators.cn_table_service import CN_TABLE_CONTRACT_PATH
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

_FLOAT_TOLERANCE = 1e-9
_TABLE_CN_SOURCE = "geneva_cn_table_csv_v1"
_TABLE_FALLBACK_CN_SOURCE = "geneva_proxy_cn_v1_fallback_missing_row"
_TABLE_FALLBACK_WARNING = "cn_table_missing_exact_row"
_HRU_MAP_RELPATH = "hru_map.tif"
_HRU_MAP_LEGEND_RELPATH = "hru_map_legend.json"


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
        cn_runtime_lookup = geneva.cn_table_service.runtime_lookup(geneva)
        cn_lookup_meta = dict(cn_runtime_lookup.get("meta", {}) or {})
        if not force_rebuild and artifact_io.exists(geneva.wd, "hru_prepare_summary.json"):
            cached_summary = artifact_io.read_json(geneva.wd, "hru_prepare_summary.json")
            if self._is_cached_summary_current(
                artifact_io=artifact_io,
                geneva=geneva,
                cached_summary=cached_summary,
                cn_lookup_meta=cn_lookup_meta,
            ):
                return cached_summary

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
            "hru_map_output_tif": str(artifact_io.resolve_path(geneva.wd, _HRU_MAP_RELPATH)),
            "hru_map_legend_output_json": str(
                artifact_io.resolve_path(geneva.wd, _HRU_MAP_LEGEND_RELPATH)
            ),
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

        hru_rows = self._apply_runtime_cn_table(
            hru_rows,
            cn_lookup=cn_runtime_lookup.get("lookup", {}),
        )
        fallback_hru_count = sum(
            1 for row in hru_rows if row.get("cn_source") == _TABLE_FALLBACK_CN_SOURCE
        )

        hru_table_relpath = artifact_io.write_records_parquet(
            geneva.wd,
            "hru_table.parquet",
            hru_rows,
            columns=_HRU_TABLE_COLUMNS,
        )
        map_summary = self._resolve_kernel_hru_map_summary(
            response=response,
            artifact_io=artifact_io,
            geneva=geneva,
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
            "cn_table": {
                "path": CN_TABLE_CONTRACT_PATH,
                "lookup_sha256": cn_lookup_meta.get("lookup_sha256"),
                "runtime_source": _TABLE_CN_SOURCE,
                "fallback_source": _TABLE_FALLBACK_CN_SOURCE,
                "fallback_hru_count": fallback_hru_count,
            },
            "artifacts": {
                "hru_table_relpath": hru_table_relpath,
                "hru_prepare_summary_relpath": "hru_prepare_summary.json",
                "cn_table_relpath": CN_TABLE_CONTRACT_PATH,
                "hru_map_relpath": map_summary["hru_map_relpath"],
                "hru_map_legend_relpath": map_summary["hru_map_legend_relpath"],
            },
            "hru_map": map_summary["hru_map"],
        }
        artifact_io.write_json(geneva.wd, "hru_prepare_summary.json", summary)
        return summary

    def _is_cached_summary_current(
        self,
        *,
        artifact_io: Any,
        geneva: "Geneva",
        cached_summary: Mapping[str, Any],
        cn_lookup_meta: Mapping[str, Any],
    ) -> bool:
        if not artifact_io.exists(geneva.wd, "hru_table.parquet"):
            return False
        if not artifact_io.exists(geneva.wd, _HRU_MAP_RELPATH):
            return False
        if not artifact_io.exists(geneva.wd, _HRU_MAP_LEGEND_RELPATH):
            return False

        cached_cn = cached_summary.get("cn_table")
        if not isinstance(cached_cn, Mapping):
            return False
        cached_artifacts = cached_summary.get("artifacts")
        if not isinstance(cached_artifacts, Mapping):
            return False
        if cached_artifacts.get("hru_map_relpath") != _HRU_MAP_RELPATH:
            return False
        if cached_artifacts.get("hru_map_legend_relpath") != _HRU_MAP_LEGEND_RELPATH:
            return False

        cached_sha = cached_cn.get("lookup_sha256")
        current_sha = cn_lookup_meta.get("lookup_sha256")
        return isinstance(cached_sha, str) and cached_sha == current_sha

    def _apply_runtime_cn_table(
        self,
        hru_rows: list[Any],
        *,
        cn_lookup: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        resolved_rows: list[dict[str, Any]] = []
        for index, row in enumerate(hru_rows, start=1):
            if not isinstance(row, Mapping):
                raise GenevaKernelError(
                    "geneva_prepare_hrus returned invalid HRU row payload.",
                    code="contract_violation",
                    details={"row_index": index},
                )

            resolved = dict(row)
            key = self._row_lookup_key(resolved, index=index)
            lookup_row = cn_lookup.get(key)

            if lookup_row is None:
                resolved["cn_source"] = _TABLE_FALLBACK_CN_SOURCE
                resolved["warnings"] = self._append_warning(
                    resolved.get("warnings"),
                    _TABLE_FALLBACK_WARNING,
                )
                resolved_rows.append(resolved)
                continue

            cn_arc_ii = float(lookup_row["cn_arc_ii"])
            resolved["cn_arc_ii"] = cn_arc_ii
            resolved["cn_lambda_020"] = cn_arc_ii
            resolved["cn_lambda_005"] = self._derive_cn_lambda_005(cn_arc_ii)
            resolved["antecedent_condition_source"] = lookup_row["antecedent_condition_source"]
            resolved["cn_source"] = _TABLE_CN_SOURCE
            resolved_rows.append(resolved)

        return resolved_rows

    def _row_lookup_key(self, row: Mapping[str, Any], *, index: int) -> tuple[str, str, str, str]:
        try:
            landuse_class = str(int(row["landuse_class"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise GenevaKernelError(
                "geneva_prepare_hrus returned invalid landuse_class in HRU row.",
                code="contract_violation",
                details={"row_index": index},
            ) from exc

        try:
            hsg_group = str(row["hsg_group"]).strip()
            burn_severity = str(row["burn_severity_class"]).strip()
            hydrophobic_class = self._bool_to_cn_key(row["hydrophobic_class"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GenevaKernelError(
                "geneva_prepare_hrus returned invalid HRU lookup dimensions.",
                code="contract_violation",
                details={"row_index": index},
            ) from exc

        if not hsg_group or not burn_severity:
            raise GenevaKernelError(
                "geneva_prepare_hrus returned blank HRU lookup dimensions.",
                code="contract_violation",
                details={"row_index": index},
            )
        return (landuse_class, hsg_group, burn_severity, hydrophobic_class)

    def _bool_to_cn_key(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"

        text = str(value).strip().lower()
        if text in {"true", "false"}:
            return text
        raise ValueError(f"Unsupported hydrophobic_class value: {value!r}")

    def _append_warning(self, warnings: Any, warning: str) -> list[Any]:
        warning_list = list(warnings) if isinstance(warnings, list) else []
        if warning not in warning_list:
            warning_list.append(warning)
        return warning_list

    def _derive_cn_lambda_005(self, cn_arc_ii: float) -> float:
        if cn_arc_ii >= (100.0 - _FLOAT_TOLERANCE):
            return 100.0
        if cn_arc_ii > 98.5:
            return min(max(cn_arc_ii, 0.0), 100.0)

        term = (100.0 / cn_arc_ii) - 1.0
        denominator = (1.879 * (term**1.15)) + 1.0
        return min(max(100.0 / denominator, 0.0), 100.0)

    def _resolve_kernel_hru_map_summary(
        self,
        *,
        response: Mapping[str, Any],
        artifact_io: Any,
        geneva: "Geneva",
    ) -> dict[str, Any]:
        kernel_summary = response.get("hru_map")
        if not isinstance(kernel_summary, Mapping):
            raise GenevaKernelError(
                "geneva_prepare_hrus returned invalid hru_map payload.",
                code="contract_violation",
            )

        if not artifact_io.exists(geneva.wd, _HRU_MAP_RELPATH):
            raise GenevaKernelError(
                "geneva_prepare_hrus did not materialize hru_map.tif.",
                code="contract_violation",
            )
        if not artifact_io.exists(geneva.wd, _HRU_MAP_LEGEND_RELPATH):
            raise GenevaKernelError(
                "geneva_prepare_hrus did not materialize hru_map_legend.json.",
                code="contract_violation",
            )

        unresolved_samples = kernel_summary.get("unresolved_component_samples", [])
        if not isinstance(unresolved_samples, list):
            unresolved_samples = []
        normalized_unresolved_samples = [
            str(sample).strip()
            for sample in unresolved_samples
            if str(sample).strip()
        ]

        return {
            "hru_map_relpath": _HRU_MAP_RELPATH,
            "hru_map_legend_relpath": _HRU_MAP_LEGEND_RELPATH,
            "hru_map": {
                "nodata_value": int(kernel_summary.get("nodata_value", 0) or 0),
                "hru_value_count": int(kernel_summary.get("hru_value_count", 0) or 0),
                "fallback_id_match_count": int(
                    kernel_summary.get("fallback_id_match_count", 0) or 0
                ),
                "mapping_status": str(kernel_summary.get("mapping_status", "complete") or "complete"),
                "active_cell_count": int(kernel_summary.get("active_cell_count", 0) or 0),
                "mapped_cell_count": int(kernel_summary.get("mapped_cell_count", 0) or 0),
                "unmapped_cell_count": int(kernel_summary.get("unmapped_cell_count", 0) or 0),
                "unresolved_component_count": int(
                    kernel_summary.get("unresolved_component_count", 0) or 0
                ),
                "unresolved_component_samples": normalized_unresolved_samples,
            },
        }


__all__ = ["GenevaHruPreparationService"]
