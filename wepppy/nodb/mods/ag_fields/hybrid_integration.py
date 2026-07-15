"""Connectivity-aware mixed AgFields watershed integration collaborator."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.topo.peridot.peridot_runner import (
    get_subfield_channel_connectivity_bin,
)

from .concept1_inputs import synthesize_concept1_parent_inputs
from .concept1_integration import (
    PASS_HEADER_RELATIVE_AREA_BUDGET,
    AgFieldsConcept1Integrator,
)
from .concept1_planner import run_planning_census
from .watershed_integration import (
    PASS_FAMILY,
    UPSTREAM_TASKS,
    AgFieldsWatershedIntegrationError,
    ParentPlan,
    SourcePlan,
    _atomic_json,
    _atomic_text,
    _sha256,
    _utc_now,
)

if TYPE_CHECKING:
    from .ag_fields import AgFields


SCHEMA_VERSION = "1.0"
ALGORITHM = "ag_fields_hybrid_v1"
ADR = "ADR-0019"
LIMITATION = (
    "Channel-connected fields use direct outlet injection; all other fields and "
    "background are reduced to a one-dimensional residual OFE profile."
)


def _subfield_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("algorithm", pa.string()),
            ("adr", pa.string()),
            ("field_id", pa.int64()),
            ("sub_field_id", pa.int64()),
            ("parent_topaz_id", pa.int64()),
            ("parent_wepp_id", pa.int64()),
            ("channel_connected", pa.bool_()),
            ("direct_channel_outlet_cells", pa.int64()),
            ("routing_branch", pa.string()),
            ("peridot_version", pa.string()),
            ("definition", pa.string()),
            ("channel_detection", pa.string()),
            ("sub_field_map_sha256", pa.string()),
            ("subwta_sha256", pa.string()),
            ("wbt_flovec_sha256", pa.string()),
            ("channel_mask_sha256", pa.string()),
        ],
        metadata={
            b"schema_version": SCHEMA_VERSION.encode("ascii"),
            b"algorithm": ALGORITHM.encode("ascii"),
            b"adr": ADR.encode("ascii"),
        },
    )


def _parent_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("algorithm", pa.string()),
            ("adr", pa.string()),
            ("parent_topaz_id", pa.int64()),
            ("parent_wepp_id", pa.int64()),
            ("routing_branch", pa.string()),
            ("connected_subfield_count", pa.int64()),
            ("residual_area_m2", pa.float64()),
            ("connected_area_m2", pa.float64()),
            ("target_area_m2", pa.float64()),
            ("area_closure_residual_m2", pa.float64()),
            ("serialized_residual_area_m2", pa.float64()),
            ("residual_pass_header_area_m2", pa.float64()),
            ("residual_pass_area_residual_m2", pa.float64()),
            ("residual_pass_area_budget_m2", pa.float64()),
            ("pass_sha256", pa.string()),
            ("status", pa.string()),
            ("rejection_reason", pa.string()),
        ],
        metadata={
            b"schema_version": SCHEMA_VERSION.encode("ascii"),
            b"algorithm": ALGORITHM.encode("ascii"),
            b"adr": ADR.encode("ascii"),
        },
    )


def _atomic_parquet(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    schema: pa.Schema,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        table = pa.Table.from_pylist(list(rows), schema=schema)
        pq.write_table(table, temporary, compression="snappy")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class AgFieldsHybridIntegrator(AgFieldsConcept1Integrator):
    """Route connected sub-fields by Concept 2 and all residual area by Concept 1."""

    def __init__(
        self,
        controller: AgFields,
        *,
        max_workers: int | None = None,
        phase_callback=None,
    ) -> None:
        super().__init__(
            controller,
            max_workers=max_workers,
            phase_callback=phase_callback,
        )
        self.connectivity_payload: dict[str, Any] | None = None
        self.parent_routing_rows: list[dict[str, Any]] = []
        self.residual_pass_diagnostics: dict[int, dict[str, float | None]] = {}

    def _integration_root(self) -> Path:
        return self.wd / "wepp" / "ag_fields" / "watershed" / "hybrid"

    @property
    def _connectivity_summary_path(self) -> Path:
        return self.manifest_dir / "connectivity_summary.json"

    @property
    def _connectivity_detail_path(self) -> Path:
        return self.manifest_dir / "connectivity_detail.json"

    def run(self) -> dict[str, Any]:
        """Produce one complete isolated connectivity-aware hybrid result."""
        try:
            self._set_phase("preflight")
            self._preflight()
            self._preflight_concept1()
            self._set_phase("workspace_reset")
            self._reset_isolated_tree()
            self._set_phase("connectivity")
            self.connectivity_payload = self._run_connectivity_classifier()
            self._write_subfield_routing(self.connectivity_payload)
            self._set_phase("ofe_planning")
            self.planning_summary = self._plan_hybrid()
            baseline_plans = self._build_area_plan()
            self.plans = baseline_plans
            self.source_signature = self._build_hybrid_source_signature()
            self._set_phase("parent_execution")
            self.plans = self._materialize_hybrid_parents(baseline_plans)
            source_rows = self._prepare_source_rows()
            self._write_source_plan(source_rows)
            self._set_phase("pass_combination")
            self._combine_affected_parents(source_rows)
            self.parent_routing_rows = self._build_parent_routing_rows()
            _atomic_parquet(
                self.manifest_dir / "parent_routing.parquet",
                self.parent_routing_rows,
                _parent_schema(),
            )
            self._set_phase("watershed_rerun")
            self._run_watershed()
            self._set_phase("interchange")
            required_resources = self._regenerate_interchange()
            self._set_phase("finalize")
            summary = self._hybrid_success_summary(required_resources)
            self._write_hybrid_readme(summary)
            _atomic_json(self.manifest_dir / "integration_summary.json", summary)
            self._publish_isolated_tree()
            return summary
        except Exception as exc:  # broad-except: terminal collaborator boundary
            if self._attempt_root is not None:
                self._write_hybrid_failure_summary(exc)
                self._preserve_failed_attempt()
            public_message = self._public_error_message(exc)
            if public_message != str(exc):
                raise AgFieldsWatershedIntegrationError(public_message) from exc
            raise

    def _connectivity_resources(self) -> dict[str, Path | None]:
        watershed = self.controller.watershed_instance
        channel_mask_raw = getattr(watershed, "netful", None)
        return {
            "sub_field_map": Path(self.controller.sub_fields_map),
            "subwta": Path(watershed.subwta),
            "wbt_flovec": Path(watershed.wbt_wd) / "flovec.tif",
            "channel_mask": Path(channel_mask_raw) if channel_mask_raw else None,
        }

    def _run_connectivity_classifier(self) -> dict[str, Any]:
        resources = self._connectivity_resources()
        for path in resources.values():
            if path is not None:
                self._require_regular_file(path, root=self.wd)
        command = [
            get_subfield_channel_connectivity_bin(),
            "--sub-field-map",
            str(resources["sub_field_map"]),
            "--subwta",
            str(resources["subwta"]),
            "--wbt-flovec",
            str(resources["wbt_flovec"]),
            "--out-json",
            str(self._connectivity_summary_path),
            "--out-subfields-json",
            str(self._connectivity_detail_path),
        ]
        channel_mask = resources["channel_mask"]
        if channel_mask is not None:
            command.extend(("--channel-mask", str(channel_mask)))
        completed = subprocess.run(
            command,
            cwd=self.wd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-2000:]
            raise AgFieldsWatershedIntegrationError(
                f"Peridot connectivity classifier failed: {detail}"
            )
        payload = json.loads(self._connectivity_detail_path.read_text(encoding="utf-8"))
        rows = payload.get("subfields")
        metrics = payload.get("metrics")
        if payload.get("schema_version") != 1 or not isinstance(rows, list):
            raise AgFieldsWatershedIntegrationError(
                "Peridot connectivity detail has an unsupported schema."
            )
        if not isinstance(metrics, dict) or metrics.get("subfields_total") != len(rows):
            raise AgFieldsWatershedIntegrationError(
                "Peridot connectivity detail count does not match its metrics."
            )
        return payload

    def _write_subfield_routing(self, payload: Mapping[str, Any]) -> None:
        detail = {int(row["subfield_id"]): row for row in payload["subfields"]}
        if len(detail) != len(payload["subfields"]):
            raise AgFieldsWatershedIntegrationError(
                "Peridot connectivity detail contains duplicate sub-field ids."
            )
        fields = self.controller.subfields_parquet
        expected = {int(value) for value in fields["sub_field_id"].tolist()}
        if set(detail) != expected:
            raise AgFieldsWatershedIntegrationError(
                "Peridot connectivity detail does not match retained sub-fields."
            )
        resources = self._connectivity_resources()
        identities = {
            name: _sha256(path) if path is not None else None
            for name, path in resources.items()
        }
        rows = []
        for field in fields.sort_values("sub_field_id").itertuples(index=False):
            sub_field_id = int(field.sub_field_id)
            connectivity = detail[sub_field_id]
            connected = bool(connectivity["channel_connected"])
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "algorithm": ALGORITHM,
                    "adr": ADR,
                    "field_id": int(field.field_id),
                    "sub_field_id": sub_field_id,
                    "parent_topaz_id": int(field.topaz_id),
                    "parent_wepp_id": int(field.wepp_id),
                    "channel_connected": connected,
                    "direct_channel_outlet_cells": int(
                        connectivity["direct_channel_outlet_cells"]
                    ),
                    "routing_branch": "concept_2" if connected else "concept_1",
                    "peridot_version": payload.get("peridot_version"),
                    "definition": payload.get("definition"),
                    "channel_detection": payload.get("channel_detection"),
                    "sub_field_map_sha256": identities["sub_field_map"],
                    "subwta_sha256": identities["subwta"],
                    "wbt_flovec_sha256": identities["wbt_flovec"],
                    "channel_mask_sha256": identities["channel_mask"],
                }
            )
        _atomic_parquet(
            self.manifest_dir / "subfield_routing.parquet",
            rows,
            _subfield_schema(),
        )

    def _plan_hybrid(self) -> dict[str, Any]:
        discha = self.controller.watershed_instance.discha
        assert discha is not None
        return run_planning_census(
            subwta_path=Path(self.controller.watershed_instance.subwta),
            discha_path=Path(discha),
            subfield_map_path=Path(self.controller.sub_fields_map),
            fields_parquet_path=Path(self.controller.subfields_parquet_path),
            slope_dir=self._slope_dir,
            output_dir=self.manifest_dir,
            connectivity_detail_path=self._connectivity_detail_path,
        )

    def _build_hybrid_source_signature(self) -> str:
        digest = hashlib.sha256()
        digest.update(self._build_concept1_source_signature().encode("ascii"))
        digest.update(_sha256(self._connectivity_detail_path).encode("ascii"))
        binary = Path(get_subfield_channel_connectivity_bin())
        digest.update(_sha256(binary).encode("ascii"))
        return digest.hexdigest()

    def _materialize_hybrid_parents(
        self,
        baseline_plans: Sequence[ParentPlan],
    ) -> tuple[ParentPlan, ...]:
        self._copy_parent_inputs()
        plan_rows = pq.read_table(self.manifest_dir / "ofe_plan.parquet").to_pylist()
        summary_rows = pq.read_table(
            self.manifest_dir / "parent_summary.parquet"
        ).to_pylist()
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in plan_rows:
            grouped[int(row["parent_wepp_id"])].append(row)
        summaries = {int(row["parent_wepp_id"]): row for row in summary_rows}
        synthesis: dict[int, dict[str, Any]] = {}
        for parent_wepp_id, rows in grouped.items():
            summary = summaries[parent_wepp_id]
            synthesis[parent_wepp_id] = synthesize_concept1_parent_inputs(
                parent_wepp_id=parent_wepp_id,
                ofe_rows=rows,
                parent_runs_dir=self.parent_runs_dir,
                subfield_runs_dir=self.subfield_runs_dir,
                target_runs_dir=self.runs_dir,
                target_width_m=float(summary["residual_width_m"]),
            )

        branches = {
            parent_wepp_id: str(row["routing_branch"])
            for parent_wepp_id, row in summaries.items()
        }
        run_ids = [
            plan.parent_wepp_id
            for plan in baseline_plans
            if branches.get(plan.parent_wepp_id) != "pure_concept_2"
        ]
        years = int(self.controller.climate_instance.input_years)
        wepp_bin = self.controller.wepp_bin

        def execute(parent_wepp_id: int) -> None:
            make_hillslope_run(
                parent_wepp_id,
                years,
                str(self.runs_dir),
                reveg=False,
                pass_family=PASS_FAMILY,
                wepp_bin=wepp_bin,
            )
            run_hillslope(parent_wepp_id, str(self.runs_dir), wepp_bin=wepp_bin)

        self._run_parallel(run_ids, execute, label="hybrid residual parent")
        present = {
            int(path.name[1:-9]) for path in self.output_dir.glob("H*.pass.dat")
        }
        if present != set(run_ids):
            raise AgFieldsWatershedIntegrationError(
                "Hybrid residual PASS inventory does not match the execution plan."
            )
        self.residual_pass_diagnostics = {
            parent_wepp_id: self._validate_residual_pass(
                parent_wepp_id,
                self.output_dir / f"H{parent_wepp_id}.pass.dat",
                synthesis.get(parent_wepp_id),
            )
            for parent_wepp_id in run_ids
        }
        self.background_pass_dir.mkdir(parents=True)
        for parent_wepp_id, branch in branches.items():
            if branch == "mixed":
                os.replace(
                    self.output_dir / f"H{parent_wepp_id}.pass.dat",
                    self.background_pass_dir / f"H{parent_wepp_id}.pass.dat",
                )
        return self._build_hybrid_plans(baseline_plans, summaries)

    @classmethod
    def _validate_residual_pass(
        cls,
        parent_wepp_id: int,
        pass_path: Path,
        generated: Mapping[str, Any] | None,
    ) -> dict[str, float | None]:
        _, pass_area = cls._read_pass_header(pass_path)
        if cls._pass_has_nonfinite(pass_path):
            raise AgFieldsWatershedIntegrationError(
                f"Hybrid residual parent {parent_wepp_id} produced non-finite PASS data."
            )
        if generated is None:
            return {
                "serialized_residual_area_m2": None,
                "residual_pass_header_area_m2": pass_area,
                "residual_pass_area_residual_m2": None,
                "residual_pass_area_budget_m2": None,
            }
        serialized_area = float(generated["serialized_target_area_m2"])
        residual = pass_area - serialized_area
        budget = PASS_HEADER_RELATIVE_AREA_BUDGET * max(
            pass_area,
            serialized_area,
            1.0,
        )
        if abs(residual) > budget:
            raise AgFieldsWatershedIntegrationError(
                f"Hybrid residual parent {parent_wepp_id} PASS area differs from "
                "the serialized slope area."
            )
        return {
            "serialized_residual_area_m2": serialized_area,
            "residual_pass_header_area_m2": pass_area,
            "residual_pass_area_residual_m2": residual,
            "residual_pass_area_budget_m2": budget,
        }

    def _connected_ids(self) -> set[int]:
        assert self.connectivity_payload is not None
        return {
            int(row["subfield_id"])
            for row in self.connectivity_payload["subfields"]
            if bool(row["channel_connected"])
        }

    def _build_hybrid_plans(
        self,
        baseline_plans: Sequence[ParentPlan],
        summaries: Mapping[int, Mapping[str, Any]],
    ) -> tuple[ParentPlan, ...]:
        connected_ids = self._connected_ids()
        hybrid_plans = []
        for baseline in baseline_plans:
            summary = summaries.get(baseline.parent_wepp_id)
            residual_area = (
                float(summary["residual_area_m2"])
                if summary is not None
                else baseline.parent_raster_area_m2
            )
            connected_sources = tuple(
                source
                for source in baseline.sources
                if source.sub_field_id in connected_ids
            )
            connected_area = math.fsum(
                source.represented_area_m2 for source in connected_sources
            )
            if summary is not None and not math.isclose(
                connected_area,
                float(summary["connected_area_m2"]),
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise AgFieldsWatershedIntegrationError(
                    f"Hybrid connected area differs for parent {baseline.parent_wepp_id}."
                )
            residual = ()
            if residual_area > 0.0:
                branch = str(summary["routing_branch"]) if summary else "untouched"
                pass_dir = (
                    self.background_pass_dir if branch == "mixed" else self.output_dir
                )
                residual = (
                    SourcePlan(
                        source_id=f"concept_1_residual:{baseline.parent_wepp_id}",
                        source_kind="background",
                        represented_area_m2=residual_area,
                        pass_path=pass_dir / f"H{baseline.parent_wepp_id}.pass.dat",
                    ),
                )
            area_residual = (
                baseline.parent_raster_area_m2 - residual_area - connected_area
            )
            if abs(area_residual) > 1e-9:
                raise AgFieldsWatershedIntegrationError(
                    f"Hybrid source area does not close for parent {baseline.parent_wepp_id}."
                )
            hybrid_plans.append(
                ParentPlan(
                    parent_topaz_id=baseline.parent_topaz_id,
                    parent_wepp_id=baseline.parent_wepp_id,
                    parent_raster_area_m2=baseline.parent_raster_area_m2,
                    retained_field_area_m2=connected_area,
                    background_area_m2=residual_area,
                    sources=(*residual, *connected_sources),
                )
            )
        return tuple(hybrid_plans)

    def _build_parent_routing_rows(self) -> list[dict[str, Any]]:
        summaries = {
            int(row["parent_wepp_id"]): row
            for row in pq.read_table(
                self.manifest_dir / "parent_summary.parquet"
            ).to_pylist()
        }
        rows = []
        for plan in self.plans:
            summary = summaries.get(plan.parent_wepp_id)
            branch = str(summary["routing_branch"]) if summary else "untouched"
            residual_area = plan.background_area_m2
            connected_area = plan.retained_field_area_m2
            pass_path = self.output_dir / f"H{plan.parent_wepp_id}.pass.dat"
            residual_diagnostics = self.residual_pass_diagnostics.get(
                plan.parent_wepp_id,
                {},
            )
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "algorithm": ALGORITHM,
                    "adr": ADR,
                    "parent_topaz_id": plan.parent_topaz_id,
                    "parent_wepp_id": plan.parent_wepp_id,
                    "routing_branch": branch,
                    "connected_subfield_count": sum(
                        source.sub_field_id is not None for source in plan.sources
                    ),
                    "residual_area_m2": residual_area,
                    "connected_area_m2": connected_area,
                    "target_area_m2": plan.parent_raster_area_m2,
                    "area_closure_residual_m2": (
                        plan.parent_raster_area_m2
                        - residual_area
                        - connected_area
                    ),
                    "serialized_residual_area_m2": residual_diagnostics.get(
                        "serialized_residual_area_m2"
                    ),
                    "residual_pass_header_area_m2": residual_diagnostics.get(
                        "residual_pass_header_area_m2"
                    ),
                    "residual_pass_area_residual_m2": residual_diagnostics.get(
                        "residual_pass_area_residual_m2"
                    ),
                    "residual_pass_area_budget_m2": residual_diagnostics.get(
                        "residual_pass_area_budget_m2"
                    ),
                    "pass_sha256": _sha256(pass_path),
                    "status": "completed",
                    "rejection_reason": None,
                }
            )
        return rows

    def _hybrid_success_summary(
        self,
        required_resources: Sequence[str],
    ) -> dict[str, Any]:
        branch_counts: dict[str, int] = defaultdict(int)
        for row in self.parent_routing_rows:
            branch_counts[str(row["routing_branch"])] += 1
        prep = RedisPrep.tryGetInstance(str(self.wd))
        upstream_timestamps = {
            str(task): prep[str(task)] if prep is not None else None
            for task in UPSTREAM_TASKS
        }
        assert self.connectivity_payload is not None
        return {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "adr": ADR,
            "scheme": "hybrid",
            "scheme_slug": "hybrid",
            "status": "completed",
            "source_signature": self.source_signature,
            "stage4_source_signature": getattr(
                self.controller,
                "_wepp_source_signature",
                None,
            ),
            "upstream_timestamps": upstream_timestamps,
            "started_at": self.started_at,
            "completed_at": _utc_now(),
            "run_root": self.root.relative_to(self.wd).as_posix(),
            "pass_family": PASS_FAMILY,
            "parent_wepp_bin": self._executable_identity(
                self._watershed_wepp_bin(),
                hill=False,
            ),
            "ag_fields_wepp_bin": self._executable_identity(
                self.controller.wepp_bin,
                hill=True,
            ),
            "parent_count": len(self.plans),
            "branch_counts": dict(sorted(branch_counts.items())),
            "sub_field_counts": self.connectivity_payload["metrics"],
            "pass_count": len(list(self.output_dir.glob("H*.pass.dat"))),
            "required_resources": list(required_resources),
            "warnings": [LIMITATION],
            "manifest_paths": {
                name: (self.root / "manifest" / name).relative_to(self.wd).as_posix()
                for name in (
                    "connectivity_summary.json",
                    "connectivity_detail.json",
                    "subfield_routing.parquet",
                    "ofe_plan.parquet",
                    "parent_summary.parquet",
                    "parent_routing.parquet",
                    "pass_sources.parquet",
                    "pass_event_closure.parquet",
                    "pass_run_closure.parquet",
                    "integration_summary.json",
                    "README.md",
                )
            },
            "failure": None,
        }

    def _write_hybrid_failure_summary(self, exc: Exception) -> None:
        try:
            self._validate_integration_root()
        except AgFieldsWatershedIntegrationError:
            return
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        _atomic_json(
            self.manifest_dir / "integration_summary.json",
            {
                "schema_version": SCHEMA_VERSION,
                "algorithm": ALGORITHM,
                "adr": ADR,
                "scheme": "hybrid",
                "scheme_slug": "hybrid",
                "status": "failed",
                "source_signature": self.source_signature,
                "started_at": self.started_at,
                "completed_at": _utc_now(),
                "run_root": self.root.relative_to(self.wd).as_posix(),
                "failure": {
                    "phase": self.phase,
                    "type": type(exc).__name__,
                    "message": self._public_error_message(exc),
                },
            },
        )

    def _write_hybrid_readme(self, summary: Mapping[str, Any]) -> None:
        text = f"""# AgFields Hybrid Watershed Result

This directory records connectivity-aware mixed routing for scheme `hybrid`.

> **Scientific limitation:** {LIMITATION}

The result contains {summary['parent_count']} parents. `subfield_routing.parquet`
records the exact Peridot branch for every retained sub-field;
`parent_routing.parquet` records pure Concept 1, pure Concept 2, mixed, and
untouched compositions. Weighted connected-source closure uses ADR-0018.
"""
        _atomic_text(self.manifest_dir / "README.md", text)


__all__ = ["AgFieldsHybridIntegrator"]
