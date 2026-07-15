"""Faithful Concept 1 AgFields watershed integration collaborator."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from wepp_runner.wepp_runner import (
    get_linux_wepp_bin_opts,
    make_hillslope_run,
    run_hillslope,
)
from wepppy.nodb.redis_prep import RedisPrep

from .concept1_inputs import synthesize_concept1_parent_inputs
from .concept1_planner import run_planning_census
from .watershed_integration import (
    PASS_FAMILY,
    UPSTREAM_TASKS,
    AgFieldsWatershedIntegrationError,
    AgFieldsWatershedIntegrator,
    _atomic_json,
    _atomic_text,
    _sha256,
    _utc_now,
)

if TYPE_CHECKING:
    from .ag_fields import AgFields


SCHEMA_VERSION = "1.0"
ALGORITHM = "ag_fields_concept_1_v1"
ADR = "ADR-0019"
LIMITATION = (
    "Field placement is reduced from a two-dimensional mosaic to ordered "
    "one-dimensional OFEs; fit diagnostics require separate science evaluation."
)
_NONFINITE_TOKEN_RE = re.compile(
    rb"(?<![A-Za-z0-9_])[+-]?(?:nan|inf(?:inity)?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
# Legacy PASS headers serialize area as .xxxxxE+xx. Half an output unit is at
# most 5e-5 of the represented value when the normalized mantissa is near 0.1.
PASS_HEADER_RELATIVE_AREA_BUDGET = 5.0e-5


def _routing_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("algorithm", pa.string()),
            ("adr", pa.string()),
            ("parent_topaz_id", pa.int64()),
            ("parent_wepp_id", pa.int64()),
            ("routing_branch", pa.string()),
            ("plan_family", pa.string()),
            ("ofe_count", pa.int64()),
            ("referenced_yearly_scenario_count", pa.int64()),
            ("target_area_m2", pa.float64()),
            ("serialized_target_area_m2", pa.float64()),
            ("pass_header_area_m2", pa.float64()),
            ("pass_area_residual_m2", pa.float64()),
            ("pass_area_budget_m2", pa.float64()),
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


class AgFieldsConcept1Integrator(AgFieldsWatershedIntegrator):
    """Plan, execute, and route the Concept 1 replacement-parent scheme."""

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
        self.planning_summary: dict[str, Any] | None = None
        self.routing_rows: list[dict[str, Any]] = []

    def _integration_root(self) -> Path:
        return self.wd / "wepp" / "ag_fields" / "watershed" / "concept-1"

    def _watershed_wepp_bin(self) -> str | None:
        return self.controller.wepp_bin

    @property
    def _slope_dir(self) -> Path:
        return self.wd / "watershed" / "slope_files" / "hillslopes"

    def run(self) -> dict[str, Any]:
        """Produce a complete isolated Concept 1 watershed result."""
        try:
            self._set_phase("preflight")
            self._preflight()
            self._preflight_concept1()
            self._set_phase("workspace_reset")
            self._reset_isolated_tree()
            self._set_phase("ofe_planning")
            self.planning_summary = self._plan()
            self.plans = self._build_area_plan()
            self.source_signature = self._build_concept1_source_signature()
            self._set_phase("parent_execution")
            self.routing_rows = self._materialize_and_run_parents()
            self._write_parent_routing(self.routing_rows)
            self._set_phase("watershed_rerun")
            self._run_watershed()
            self._set_phase("interchange")
            required_resources = self._regenerate_interchange()
            self._set_phase("finalize")
            summary = self._concept1_success_summary(required_resources)
            self._write_concept1_readme(summary)
            _atomic_json(self.manifest_dir / "integration_summary.json", summary)
            self._publish_isolated_tree()
            return summary
        except Exception as exc:  # broad-except: terminal collaborator boundary
            if self._attempt_root is not None:
                self._write_concept1_failure_summary(exc)
                self._preserve_failed_attempt()
            public_message = self._public_error_message(exc)
            if public_message != str(exc):
                raise AgFieldsWatershedIntegrationError(public_message) from exc
            raise

    def _preflight_concept1(self) -> None:
        discha = self.controller.watershed_instance.discha
        if discha is None:
            raise AgFieldsWatershedIntegrationError(
                "Concept 1 requires a distance-to-channel raster."
            )
        for path in (Path(discha), self._slope_dir):
            if not path.exists() or path.is_symlink():
                raise FileNotFoundError(path)
            path.resolve().relative_to(self.wd)
        scheme_binary = self.controller.wepp_bin
        if scheme_binary is None or scheme_binary not in get_linux_wepp_bin_opts():
            raise AgFieldsWatershedIntegrationError(
                "Concept 1 requires an installed AgFields WEPP executable family."
            )

    def _plan(self) -> dict[str, Any]:
        discha = self.controller.watershed_instance.discha
        assert discha is not None
        return run_planning_census(
            subwta_path=Path(self.controller.watershed_instance.subwta),
            discha_path=Path(discha),
            subfield_map_path=Path(self.controller.sub_fields_map),
            fields_parquet_path=Path(self.controller.subfields_parquet_path),
            slope_dir=self._slope_dir,
            output_dir=self.manifest_dir,
        )

    def _build_concept1_source_signature(self) -> str:
        digest = hashlib.sha256()
        state = {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "adr": ADR,
            "calendar": self.controller._observed_year_bounds(),
            "parent_wepp_bin": self.controller.wepp_instance.wepp_bin,
            "ag_fields_wepp_bin": self.controller.wepp_bin,
            "parent_wepp_executable": self._executable_identity(
                self.controller.wepp_instance.wepp_bin,
                hill=False,
            ),
            "ag_fields_wepp_executable": self._executable_identity(
                self.controller.wepp_bin,
                hill=True,
            ),
        }
        digest.update(json.dumps(state, sort_keys=True).encode("utf-8"))
        inventory = [
            Path(self.controller.subfields_parquet_path),
            Path(self.controller.watershed_instance.subwta),
            Path(self.controller.watershed_instance.discha),
            Path(self.controller.sub_fields_map),
            self.manifest_dir / "ofe_plan.parquet",
            self.manifest_dir / "parent_summary.parquet",
        ]
        plan_rows = pq.read_table(self.manifest_dir / "ofe_plan.parquet").to_pylist()
        for row in plan_rows:
            parent_id = int(row["parent_wepp_id"])
            if row["source_kind"] == "background":
                inventory.append(self.parent_runs_dir / f"p{parent_id}.man")
            else:
                inventory.append(
                    self.subfield_runs_dir / f"p{int(row['sub_field_id'])}.man"
                )
        for plan in self.plans:
            for suffix in ("cli", "man", "slp", "sol"):
                inventory.append(
                    self.parent_runs_dir / f"p{plan.parent_wepp_id}.{suffix}"
                )
        inventory.extend(self._parent_auxiliary_inputs())
        for path in sorted(set(inventory), key=lambda item: item.as_posix()):
            relative = self._published_relpath(path)
            digest.update(relative.encode("utf-8"))
            digest.update(_sha256(path).encode("ascii"))
        return digest.hexdigest()

    def _copy_parent_inputs(self) -> None:
        for plan in self.plans:
            for suffix in ("cli", "man", "slp", "sol"):
                self._copy_input(
                    self.parent_runs_dir / f"p{plan.parent_wepp_id}.{suffix}",
                    self.runs_dir / f"p{plan.parent_wepp_id}.{suffix}",
                )
        for source in self._parent_auxiliary_inputs():
            self._copy_input(source, self.runs_dir / source.name)

    def _materialize_and_run_parents(self) -> list[dict[str, Any]]:
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
        for parent_wepp_id in sorted(grouped):
            summary = summaries[parent_wepp_id]
            synthesis[parent_wepp_id] = synthesize_concept1_parent_inputs(
                parent_wepp_id=parent_wepp_id,
                ofe_rows=grouped[parent_wepp_id],
                parent_runs_dir=self.parent_runs_dir,
                subfield_runs_dir=self.subfield_runs_dir,
                target_runs_dir=self.runs_dir,
                target_width_m=float(summary["residual_width_m"]),
            )

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

        parent_ids = [plan.parent_wepp_id for plan in self.plans]
        self._run_parallel(parent_ids, execute, label="Concept 1 parent hillslope")
        present = {int(path.name[1:-9]) for path in self.output_dir.glob("H*.pass.dat")}
        if present != set(parent_ids):
            raise AgFieldsWatershedIntegrationError(
                "Concept 1 parent PASS inventory does not match the watershed."
            )

        topaz_by_wepp = {plan.parent_wepp_id: plan.parent_topaz_id for plan in self.plans}
        rows: list[dict[str, Any]] = []
        for parent_wepp_id in parent_ids:
            pass_path = self.output_dir / f"H{parent_wepp_id}.pass.dat"
            _, pass_area = self._read_pass_header(pass_path)
            if self._pass_has_nonfinite(pass_path):
                raise AgFieldsWatershedIntegrationError(
                    f"Concept 1 parent {parent_wepp_id} produced non-finite PASS data."
                )
            generated = synthesis.get(parent_wepp_id)
            if generated is None:
                rows.append(
                    self._routing_row(
                        parent_topaz_id=topaz_by_wepp[parent_wepp_id],
                        parent_wepp_id=parent_wepp_id,
                        pass_path=pass_path,
                        pass_area=pass_area,
                    )
                )
                continue
            serialized_area = float(generated["serialized_target_area_m2"])
            residual = pass_area - serialized_area
            budget = PASS_HEADER_RELATIVE_AREA_BUDGET * max(
                pass_area,
                serialized_area,
                1.0,
            )
            if abs(residual) > budget:
                raise AgFieldsWatershedIntegrationError(
                    f"Concept 1 parent {parent_wepp_id} PASS area differs from "
                    "the serialized slope area."
                )
            plan_family = str(grouped[parent_wepp_id][0]["plan_family"])
            rows.append(
                self._routing_row(
                    parent_topaz_id=topaz_by_wepp[parent_wepp_id],
                    parent_wepp_id=parent_wepp_id,
                    pass_path=pass_path,
                    pass_area=pass_area,
                    plan_family=plan_family,
                    generated=generated,
                    residual=residual,
                    budget=budget,
                )
            )
        return rows

    @staticmethod
    def _pass_has_nonfinite(path: Path) -> bool:
        with path.open("rb") as stream:
            return any(_NONFINITE_TOKEN_RE.search(line) for line in stream)

    @staticmethod
    def _routing_row(
        *,
        parent_topaz_id: int,
        parent_wepp_id: int,
        pass_path: Path,
        pass_area: float,
        plan_family: str | None = None,
        generated: Mapping[str, Any] | None = None,
        residual: float = 0.0,
        budget: float = 0.0,
    ) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "adr": ADR,
            "parent_topaz_id": parent_topaz_id,
            "parent_wepp_id": parent_wepp_id,
            "routing_branch": "concept_1" if generated is not None else "baseline",
            "plan_family": plan_family,
            "ofe_count": int(generated["ofe_count"]) if generated else 1,
            "referenced_yearly_scenario_count": (
                int(generated["referenced_yearly_scenario_count"])
                if generated
                else None
            ),
            "target_area_m2": float(generated["target_area_m2"]) if generated else None,
            "serialized_target_area_m2": (
                float(generated["serialized_target_area_m2"]) if generated else None
            ),
            "pass_header_area_m2": pass_area,
            "pass_area_residual_m2": residual if generated else None,
            "pass_area_budget_m2": budget if generated else None,
            "pass_sha256": _sha256(pass_path),
            "status": "completed",
            "rejection_reason": None,
        }

    def _write_parent_routing(self, rows: Sequence[Mapping[str, Any]]) -> None:
        table = pa.Table.from_pylist(list(rows), schema=_routing_schema())
        target = self.manifest_dir / "parent_routing.parquet"
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            dir=target.parent,
        )
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            pq.write_table(table, temporary, compression="snappy")
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _concept1_success_summary(
        self,
        required_resources: Sequence[str],
    ) -> dict[str, Any]:
        affected = sum(row["routing_branch"] == "concept_1" for row in self.routing_rows)
        prep = RedisPrep.tryGetInstance(str(self.wd))
        upstream_timestamps = {
            str(task): prep[str(task)] if prep is not None else None
            for task in UPSTREAM_TASKS
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "adr": ADR,
            "scheme": "concept_1",
            "scheme_slug": "concept-1",
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
            "parent_count": len(self.routing_rows),
            "affected_parent_count": affected,
            "untouched_parent_count": len(self.routing_rows) - affected,
            "pass_count": len(list(self.output_dir.glob("H*.pass.dat"))),
            "required_resources": list(required_resources),
            "warnings": [LIMITATION],
            "manifest_paths": {
                name: (self.root / "manifest" / name).relative_to(self.wd).as_posix()
                for name in (
                    "ofe_plan.parquet",
                    "parent_candidates.parquet",
                    "parent_summary.parquet",
                    "parent_routing.parquet",
                    "planning_summary.json",
                    "integration_summary.json",
                    "README.md",
                )
            },
            "failure": None,
        }

    def _write_concept1_failure_summary(self, exc: Exception) -> None:
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
                "scheme": "concept_1",
                "scheme_slug": "concept-1",
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

    def _write_concept1_readme(self, summary: Mapping[str, Any]) -> None:
        text = f"""# AgFields Concept 1 Watershed Result

This directory records the field-aware OFE routing result for scheme
`concept_1` (`concept-1`).

> **Scientific limitation:** {LIMITATION}

The result contains {summary['parent_count']} parent hillslopes, including
{summary['affected_parent_count']} field-aware replacements. `ofe_plan.parquet`
is the accepted geospatial-to-input boundary; `parent_routing.parquet` records
the executed PASS identity and serialized-area check for every parent.
"""
        _atomic_text(self.manifest_dir / "README.md", text)


__all__ = ["AgFieldsConcept1Integrator"]
