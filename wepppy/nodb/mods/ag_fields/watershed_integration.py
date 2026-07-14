"""Isolated Concept 2 watershed integration for AgFields.

The collaborator in this module owns the expensive raster, PASS, and WEPP work.
The :class:`AgFields` controller remains the persisted public facade and holds its
NoDb lock only while changing additive state.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Sequence

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import gdal

from wepp_runner.wepp_runner import (
    make_hillslope_run,
    make_watershed_omni_contrasts_run,
    get_linux_wepp_bin_opts,
    run_hillslope,
    run_watershed,
    wepp_bin_dir,
)
from wepppy.nodb.core.wepp import BaseflowOpts
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.wepp.interchange import (
    generate_interchange_documentation,
    run_totalwatsed3,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
)

if TYPE_CHECKING:
    from .ag_fields import AgFields


SCHEMA_VERSION = "1.0"
ALGORITHM = "ag_fields_v1"
SEMANTIC_CONTRACT = "ag_fields_pass_semantics_v1"
ADR = "ADR-0018"
PASS_FAMILY = "legacy_ascii"
LIMITATION = (
    "Field water and sediment are injected at the parent outlet; downslope "
    "buffer, trapping, and runon effects are not represented."
)
METRICS = (
    "runvol_m3",
    "sbrunv_m3",
    "drrunv_m3",
    "gwbfv_m3",
    "gwdsv_m3",
    "tdet_kg",
    "tdep_kg",
    "sediment_class_1_kg",
    "sediment_class_2_kg",
    "sediment_class_3_kg",
    "sediment_class_4_kg",
    "sediment_class_5_kg",
)
UPSTREAM_TASKS = (
    TaskEnum.abstract_watershed,
    TaskEnum.build_landuse,
    TaskEnum.build_soils,
    TaskEnum.build_climate,
    TaskEnum.run_wepp_hillslopes,
    TaskEnum.run_ag_fields,
)
_BASE_FIELDS = (
    ("schema_version", pa.string()),
    ("algorithm", pa.string()),
    ("semantic_contract", pa.string()),
    ("adr", pa.string()),
)


class AgFieldsWatershedIntegrationError(RuntimeError):
    """Raised when an integration contract cannot be proved."""


@dataclass(frozen=True)
class SourcePlan:
    source_id: str
    source_kind: str
    represented_area_m2: float
    pass_path: Path
    field_id: int | None = None
    sub_field_id: int | None = None


@dataclass(frozen=True)
class ParentPlan:
    parent_topaz_id: int
    parent_wepp_id: int
    parent_raster_area_m2: float
    retained_field_area_m2: float
    background_area_m2: float
    sources: tuple[SourcePlan, ...]

    @property
    def affected(self) -> bool:
        return self.retained_field_area_m2 > 0.0

    @property
    def full_coverage(self) -> bool:
        return self.affected and self.background_area_m2 == 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class _AtomicParquetWriter:
    def __init__(self, path: Path, schema: pa.Schema) -> None:
        self.path = path
        self.schema = schema
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        os.close(fd)
        self.temporary = Path(temporary_name)
        self.writer = pq.ParquetWriter(self.temporary, schema, compression="snappy")

    def write(self, rows: Sequence[Mapping[str, Any]]) -> None:
        if rows:
            self.writer.write_table(pa.Table.from_pylist(list(rows), schema=self.schema))

    def complete(self) -> None:
        self.writer.close()
        os.replace(self.temporary, self.path)

    def abort(self) -> None:
        self.writer.close()
        if self.temporary.exists():
            self.temporary.unlink()


def _source_schema() -> pa.Schema:
    fields = list(_BASE_FIELDS)
    fields.extend(
        [
            ("parent_topaz_id", pa.int64()),
            ("parent_wepp_id", pa.int64()),
            ("source_id", pa.string()),
            ("source_kind", pa.string()),
            ("field_id", pa.int64()),
            ("sub_field_id", pa.int64()),
            ("source_pass_relpath", pa.string()),
            ("source_climate_token", pa.string()),
            ("source_climate_sha256", pa.string()),
            ("target_climate_token", pa.string()),
            ("target_climate_sha256", pa.string()),
            ("parent_raster_area_m2", pa.float64()),
            ("retained_field_area_m2", pa.float64()),
            ("background_area_m2", pa.float64()),
            ("represented_area_m2", pa.float64()),
            ("modeled_area_m2", pa.float64()),
            ("scale", pa.float64()),
            ("coverage_ratio", pa.float64()),
            ("area_residual_m2", pa.float64()),
            ("calendar_valid", pa.bool_()),
            ("climate_valid", pa.bool_()),
            ("row_count", pa.int64()),
            ("status", pa.string()),
            ("rejection_reason", pa.string()),
        ]
    )
    fields.extend((f"raw_{metric}", pa.float64()) for metric in METRICS)
    fields.extend((f"weighted_{metric}", pa.float64()) for metric in METRICS)
    return _artifact_schema(fields)


def _event_schema() -> pa.Schema:
    fields = list(_BASE_FIELDS)
    fields.extend(
        [
            ("parent_topaz_id", pa.int64()),
            ("parent_wepp_id", pa.int64()),
            ("year", pa.int64()),
            ("julian", pa.int64()),
            ("event", pa.string()),
        ]
    )
    for prefix in ("weighted_input", "reparsed_output", "residual", "budget"):
        fields.extend((f"{prefix}_{metric}", pa.float64()) for metric in METRICS)
    return _artifact_schema(fields)


def _run_schema() -> pa.Schema:
    fields = list(_BASE_FIELDS)
    fields.extend(
        [
            ("parent_topaz_id", pa.int64()),
            ("parent_wepp_id", pa.int64()),
            ("target_area_m2", pa.float64()),
            ("serialized_target_area_m2", pa.float64()),
            ("target_area_residual_m2", pa.float64()),
            ("target_area_budget_m2", pa.float64()),
        ]
    )
    for prefix in (
        "weighted_input",
        "reparsed_output",
        "residual",
        "budget",
        "max_abs_event_residual",
        "max_event_budget_ratio",
    ):
        fields.extend((f"{prefix}_{metric}", pa.float64()) for metric in METRICS)
    return _artifact_schema(fields)


def _base_row() -> dict[str, str]:
    return {
        "schema_version": SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "semantic_contract": SEMANTIC_CONTRACT,
        "adr": ADR,
    }


def _artifact_schema(fields: Sequence[tuple[str, pa.DataType]]) -> pa.Schema:
    return pa.schema(
        fields,
        metadata={
            b"schema_version": SCHEMA_VERSION.encode("ascii"),
            b"algorithm": ALGORITHM.encode("ascii"),
            b"semantic_contract": SEMANTIC_CONTRACT.encode("ascii"),
            b"adr": ADR.encode("ascii"),
        },
    )


class AgFieldsWatershedIntegrator:
    """Execute one isolated AgFields Concept 2 watershed integration."""

    def __init__(
        self,
        controller: AgFields,
        *,
        max_workers: int | None = None,
        phase_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.controller = controller
        self.wd = Path(controller.wd).resolve()
        self.root = Path(controller.ag_field_watershed_root)
        self.runs_dir = Path(controller.ag_field_watershed_runs_dir)
        self.output_dir = Path(controller.ag_field_watershed_output_dir)
        self.manifest_dir = Path(controller.ag_field_watershed_manifest_dir)
        self.background_pass_dir = self.manifest_dir / "materialized_parent_pass"
        self.parent_runs_dir = self.wd / "wepp" / "runs"
        self.subfield_runs_dir = Path(controller.ag_field_wepp_runs_dir)
        self.subfield_output_dir = Path(controller.ag_field_wepp_output_dir)
        self.max_workers = self._normalize_workers(max_workers)
        self.phase_callback = phase_callback
        self.phase = "not_started"
        self.started_at = _utc_now()
        self.plans: tuple[ParentPlan, ...] = ()
        self.source_signature: str | None = None
        self._climate_hashes: dict[Path, str] = {}

    @staticmethod
    def _normalize_workers(value: int | None) -> int:
        cpu_count = os.cpu_count() or 1
        if value is None:
            return max(1, min(cpu_count, 16))
        if int(value) < 1:
            raise ValueError("max_workers must be at least 1")
        return min(int(value), max(cpu_count, 16))

    def _set_phase(self, phase: str) -> None:
        self.phase = phase
        if self.phase_callback is not None:
            self.phase_callback(phase)

    def run(self) -> dict[str, Any]:
        """Run all integration phases and return the durable terminal summary."""
        try:
            self._set_phase("preflight")
            self._preflight()
            self._set_phase("area_planning")
            self.plans = self._build_area_plan()
            self.source_signature = self._build_source_signature()
            self._set_phase("parent_materialization")
            self._reset_isolated_tree()
            self._materialize_parents()
            self._set_phase("source_validation")
            source_rows = self._prepare_source_rows()
            self._write_source_plan(source_rows)
            self._set_phase("pass_combination")
            self._combine_affected_parents(source_rows)
            self._set_phase("watershed_rerun")
            self._run_watershed()
            self._set_phase("interchange")
            required_resources = self._regenerate_interchange()
            self._set_phase("finalize")
            summary = self._success_summary(required_resources)
            self._write_manifest_readme(summary)
            _atomic_json(self.manifest_dir / "integration_summary.json", summary)
            return summary
        except Exception as exc:  # broad-except: terminal collaborator boundary records failed phase
            self._write_failure_summary(exc)
            public_message = self._public_error_message(exc)
            if public_message != str(exc):
                raise AgFieldsWatershedIntegrationError(public_message) from exc
            raise

    def _public_error_message(self, exc: Exception) -> str:
        message = str(exc).replace(str(self.wd), "<run>")
        application_root = Path(__file__).resolve().parents[4]
        return message.replace(str(application_root), "<application>")

    def _preflight(self) -> None:
        climate = self.controller.climate_instance
        if bool(getattr(climate, "is_single_storm", False)):
            raise AgFieldsWatershedIntegrationError(
                "AgFields watershed integration v1 requires a continuous observed climate."
            )
        self.controller._observed_year_bounds()
        parent_wepp_bin = self.controller.wepp_instance.wepp_bin
        if parent_wepp_bin is not None and parent_wepp_bin not in get_linux_wepp_bin_opts():
            raise AgFieldsWatershedIntegrationError(
                f"Parent WEPP executable is not an installed option: {parent_wepp_bin}"
            )
        if not Path(self.controller.subfields_parquet_path).is_file():
            raise FileNotFoundError(self.controller.subfields_parquet_path)
        for raster_path in (Path(self.controller.watershed_instance.subwta), Path(self.controller.sub_fields_map)):
            self._require_regular_file(raster_path, root=self.wd)

        translator = self.controller.watershed_instance.translator_factory()
        parent_ids = tuple(int(value) for value in translator.iter_wepp_sub_ids())
        if not parent_ids:
            raise AgFieldsWatershedIntegrationError("Watershed translator has no parent hillslopes.")

        subfields = self.controller.subfields_parquet
        required_columns = {"field_id", "topaz_id", "wepp_id", "sub_field_id"}
        missing_columns = sorted(required_columns.difference(subfields.columns))
        if missing_columns:
            raise AgFieldsWatershedIntegrationError(
                f"Sub-field parquet is missing required columns: {', '.join(missing_columns)}"
            )
        sub_field_ids = [int(value) for value in subfields["sub_field_id"].tolist()]
        if len(sub_field_ids) != len(set(sub_field_ids)):
            raise AgFieldsWatershedIntegrationError("Sub-field parquet contains duplicate sub_field_id values.")

        for row in subfields.itertuples(index=False):
            topaz_id = int(row.topaz_id)
            wepp_id = int(row.wepp_id)
            translated = translator.wepp(top=topaz_id)
            if translated is None or int(translated) != wepp_id:
                raise AgFieldsWatershedIntegrationError(
                    f"Sub-field {int(row.sub_field_id)} maps to inconsistent parent ids."
                )
            self._require_regular_file(
                self.subfield_output_dir / f"H{int(row.sub_field_id)}.pass.dat",
                root=self.wd,
            )

        for wepp_id in parent_ids:
            for suffix in ("cli", "man", "slp", "sol"):
                self._require_regular_file(self.parent_runs_dir / f"p{wepp_id}.{suffix}", root=self.wd)
            with (self.parent_runs_dir / f"p{wepp_id}.slp").open(encoding="utf-8") as stream:
                lines = [line.strip() for line in stream if line.strip()]
            if len(lines) < 2 or lines[1] != "1":
                raise AgFieldsWatershedIntegrationError(
                    f"Parent hillslope {wepp_id} is not a supported single-OFE slope."
                )

        for name in ("pw0.chn", "pw0.cli", "pw0.man", "pw0.slp", "pw0.sol", "pw0.str"):
            self._require_regular_file(self.parent_runs_dir / name, root=self.wd)

    @staticmethod
    def _require_regular_file(path: Path, *, root: Path) -> None:
        if path.is_symlink():
            raise AgFieldsWatershedIntegrationError(f"Symlink input is not allowed: {path.name}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise AgFieldsWatershedIntegrationError(
                f"Input path escapes the run root: {path.name}"
            ) from exc
        if not resolved.is_file():
            raise FileNotFoundError(path)

    @staticmethod
    def _open_raster(path: Path) -> tuple[Any, np.ndarray]:
        dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
        if dataset is None:
            raise AgFieldsWatershedIntegrationError(f"Unable to open raster: {path.name}")
        band = dataset.GetRasterBand(1)
        array = band.ReadAsArray()
        if array is None:
            raise AgFieldsWatershedIntegrationError(f"Unable to read raster: {path.name}")
        return dataset, np.asarray(array)

    def _build_area_plan(self) -> tuple[ParentPlan, ...]:
        parent_ds, parent_map = self._open_raster(Path(self.controller.watershed_instance.subwta))
        field_ds, field_map = self._open_raster(Path(self.controller.sub_fields_map))
        if (parent_ds.RasterXSize, parent_ds.RasterYSize) != (field_ds.RasterXSize, field_ds.RasterYSize):
            raise AgFieldsWatershedIntegrationError("Parent and sub-field rasters have different shapes.")
        if not np.allclose(parent_ds.GetGeoTransform(), field_ds.GetGeoTransform(), rtol=0.0, atol=1e-9):
            raise AgFieldsWatershedIntegrationError("Parent and sub-field rasters have different transforms.")
        if parent_ds.GetProjection() != field_ds.GetProjection():
            raise AgFieldsWatershedIntegrationError("Parent and sub-field rasters have different projections.")

        gt = parent_ds.GetGeoTransform()
        cell_area = abs(float(gt[1]) * float(gt[5]) - float(gt[2]) * float(gt[4]))
        if not math.isfinite(cell_area) or cell_area <= 0.0:
            raise AgFieldsWatershedIntegrationError("Aligned rasters have an invalid cell area.")

        translator = self.controller.watershed_instance.translator_factory()
        subfields = self.controller.subfields_parquet
        metadata: dict[int, tuple[int, int, int]] = {}
        for row in subfields.itertuples(index=False):
            sub_field_id = int(row.sub_field_id)
            metadata[sub_field_id] = (int(row.field_id), int(row.topaz_id), int(row.wepp_id))

        raster_sub_ids = {int(value) for value in np.unique(field_map) if int(value) > 0}
        expected_sub_ids = set(metadata)
        if raster_sub_ids != expected_sub_ids:
            missing = sorted(expected_sub_ids.difference(raster_sub_ids))[:10]
            unknown = sorted(raster_sub_ids.difference(expected_sub_ids))[:10]
            raise AgFieldsWatershedIntegrationError(
                f"Sub-field raster inventory mismatch; missing={missing}, unknown={unknown}."
            )

        sources_by_parent: dict[int, list[SourcePlan]] = {}
        for sub_field_id, (field_id, expected_topaz_id, wepp_id) in metadata.items():
            mask = field_map == sub_field_id
            owners = {int(value) for value in np.unique(parent_map[mask])}
            if owners != {expected_topaz_id}:
                raise AgFieldsWatershedIntegrationError(
                    f"Sub-field {sub_field_id} crosses or mismatches parent ownership: {sorted(owners)}."
                )
            represented_area = float(np.count_nonzero(mask)) * cell_area
            if represented_area <= 0.0:
                raise AgFieldsWatershedIntegrationError(f"Sub-field {sub_field_id} has no raster area.")
            sources_by_parent.setdefault(wepp_id, []).append(
                SourcePlan(
                    source_id=f"sub_field:{sub_field_id}",
                    source_kind="sub_field",
                    represented_area_m2=represented_area,
                    pass_path=self.subfield_output_dir / f"H{sub_field_id}.pass.dat",
                    field_id=field_id,
                    sub_field_id=sub_field_id,
                )
            )

        plans: list[ParentPlan] = []
        for wepp_id in translator.iter_wepp_sub_ids():
            parent_wepp_id = int(wepp_id)
            topaz = translator.top(wepp=parent_wepp_id)
            if topaz is None:
                raise AgFieldsWatershedIntegrationError(
                    f"Translator cannot resolve parent WEPP id {parent_wepp_id}."
                )
            parent_topaz_id = int(topaz)
            parent_area = float(np.count_nonzero(parent_map == parent_topaz_id)) * cell_area
            if parent_area <= 0.0:
                raise AgFieldsWatershedIntegrationError(
                    f"Parent hillslope {parent_wepp_id} has no raster area."
                )
            sub_sources = sorted(
                sources_by_parent.get(parent_wepp_id, []), key=lambda source: int(source.sub_field_id or 0)
            )
            retained_area = math.fsum(source.represented_area_m2 for source in sub_sources)
            background_area = parent_area - retained_area
            budget = 64.0 * np.finfo(np.float64).eps * max(parent_area, retained_area, 1.0)
            if background_area < -budget:
                raise AgFieldsWatershedIntegrationError(
                    f"Parent {parent_wepp_id} is overcovered by {-background_area:.6f} m2."
                )
            if abs(background_area) <= budget:
                background_area = 0.0
            background = SourcePlan(
                source_id=f"background:{parent_wepp_id}",
                source_kind="background",
                represented_area_m2=background_area,
                pass_path=self.background_pass_dir / f"H{parent_wepp_id}.pass.dat",
            )
            plans.append(
                ParentPlan(
                    parent_topaz_id=parent_topaz_id,
                    parent_wepp_id=parent_wepp_id,
                    parent_raster_area_m2=parent_area,
                    retained_field_area_m2=retained_area,
                    background_area_m2=background_area,
                    sources=tuple([background, *sub_sources]),
                )
            )
        return tuple(plans)

    def _build_source_signature(self) -> str:
        digest = hashlib.sha256()
        state = {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "semantic_contract": SEMANTIC_CONTRACT,
            "adr": ADR,
            "subfields_source_signature": getattr(self.controller, "_subfields_source_signature", None),
            "wepp_source_signature": getattr(self.controller, "_wepp_source_signature", None),
            "calendar": self.controller._observed_year_bounds(),
            "parent_wepp_bin": self.controller.wepp_instance.wepp_bin,
            "ag_fields_wepp_bin": self.controller.wepp_bin,
            "parent_wepp_executable": self._executable_identity(
                self.controller.wepp_instance.wepp_bin, hill=False
            ),
            "ag_fields_wepp_executable": self._executable_identity(
                self.controller.wepp_bin, hill=True
            ),
            "weighted_kernel_sha256": self._weighted_kernel_sha256(),
        }
        digest.update(json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        inventory = [
            Path(self.controller.subfields_parquet_path),
            Path(self.controller.watershed_instance.subwta),
            Path(self.controller.sub_fields_map),
        ]
        for plan in self.plans:
            for suffix in ("cli", "man", "slp", "sol"):
                inventory.append(self.parent_runs_dir / f"p{plan.parent_wepp_id}.{suffix}")
            inventory.extend(source.pass_path for source in plan.sources if source.source_kind == "sub_field")
        inventory.extend(self._parent_auxiliary_inputs())
        for path in sorted(inventory, key=lambda candidate: candidate.as_posix()):
            relative = path.resolve().relative_to(self.wd).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(_sha256(path).encode("ascii"))
        return digest.hexdigest()

    def _reset_isolated_tree(self) -> None:
        expected = self.wd / "wepp" / "ag_fields" / "watershed"
        if self.root.absolute() != expected.absolute():
            raise AgFieldsWatershedIntegrationError("Isolated watershed root does not match the fixed run path.")
        if any(path.is_symlink() for path in (expected.parent.parent, expected.parent, expected)):
            raise AgFieldsWatershedIntegrationError(
                "Refusing to reset through a symlinked watershed path."
            )
        if self.root.exists():
            shutil.rmtree(self.root)
        self.runs_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)
        self.manifest_dir.mkdir(parents=True)

    def _copy_input(self, source: Path, target: Path) -> None:
        self._require_regular_file(source, root=self.wd)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def _parent_auxiliary_inputs(self) -> tuple[Path, ...]:
        inputs = []
        for source in sorted(self.parent_runs_dir.iterdir(), key=lambda path: path.name):
            if not source.is_file() or source.is_symlink():
                continue
            if source.name.startswith("p") and len(source.name) > 1 and source.name[1].isdigit():
                continue
            if source.name in {"pw0.run", "pw0.err"}:
                continue
            inputs.append(source)
        return tuple(inputs)

    def _materialize_parents(self) -> None:
        parent_ids = [plan.parent_wepp_id for plan in self.plans]
        for wepp_id in parent_ids:
            for suffix in ("cli", "man", "slp", "sol"):
                self._copy_input(
                    self.parent_runs_dir / f"p{wepp_id}.{suffix}",
                    self.runs_dir / f"p{wepp_id}.{suffix}",
                )
        for source in self._parent_auxiliary_inputs():
            self._copy_input(source, self.runs_dir / source.name)

        years = int(self.controller.climate_instance.input_years)
        parent_wepp_bin = self.controller.wepp_instance.wepp_bin

        def materialize(wepp_id: int) -> None:
            make_hillslope_run(
                wepp_id,
                years,
                str(self.runs_dir),
                reveg=False,
                pass_family=PASS_FAMILY,
                wepp_bin=parent_wepp_bin,
            )
            run_hillslope(wepp_id, str(self.runs_dir), wepp_bin=parent_wepp_bin)

        self._run_parallel(parent_ids, materialize, label="parent hillslope")
        present = {int(path.name[1:-9]) for path in self.output_dir.glob("H*.pass.dat")}
        expected = set(parent_ids)
        if present != expected:
            raise AgFieldsWatershedIntegrationError(
                f"Parent PASS materialization mismatch; missing={sorted(expected - present)[:10]}, "
                f"unexpected={sorted(present - expected)[:10]}."
            )
        self.background_pass_dir.mkdir(parents=True)
        for plan in self.plans:
            background = plan.sources[0]
            if background.source_kind != "background":
                raise AgFieldsWatershedIntegrationError(
                    f"Parent {plan.parent_wepp_id} source plan does not start with background."
                )
            os.link(
                self.output_dir / f"H{plan.parent_wepp_id}.pass.dat",
                background.pass_path,
            )

    def _run_parallel(self, identifiers: Sequence[int], operation: Callable[[int], None], *, label: str) -> None:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures: dict[Future[None], int] = {
                pool.submit(operation, identifier): identifier for identifier in identifiers
            }
            pending = set(futures)
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    identifier = futures[future]
                    try:
                        future.result()
                    except Exception as exc:  # broad-except: concurrent subprocess task boundary
                        for remaining in pending:
                            remaining.cancel()
                        raise AgFieldsWatershedIntegrationError(
                            f"Failed to materialize {label} {identifier}: {exc}"
                        ) from exc

    @staticmethod
    def _read_pass_header(path: Path) -> tuple[str, float]:
        with path.open(encoding="utf-8") as stream:
            lines = [stream.readline() for _ in range(5)]
        if any(line == "" for line in lines):
            raise AgFieldsWatershedIntegrationError(f"PASS header is incomplete: {path.name}")
        try:
            modeled_area = float(lines[2].strip())
        except ValueError as exc:
            raise AgFieldsWatershedIntegrationError(f"PASS header area is invalid: {path.name}") from exc
        if not math.isfinite(modeled_area) or modeled_area <= 0.0:
            raise AgFieldsWatershedIntegrationError(f"PASS header area is not positive: {path.name}")
        return lines[0].strip(), modeled_area

    def _resolve_source_climate(self, token: str, *, runs_dir: Path) -> Path:
        if not token or "\n" in token or "\r" in token:
            raise AgFieldsWatershedIntegrationError("PASS climate token is empty or multiline.")
        token_path = Path(token)
        if token_path.is_absolute():
            raise AgFieldsWatershedIntegrationError("Absolute PASS climate tokens are not allowed.")
        candidate = runs_dir / token_path
        self._require_regular_file(candidate, root=self.wd)
        return candidate.resolve()

    def _climate_hash(self, path: Path) -> str:
        resolved = path.resolve()
        if resolved not in self._climate_hashes:
            self._climate_hashes[resolved] = _sha256(resolved)
        return self._climate_hashes[resolved]

    def _prepare_source_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for plan in self.plans:
            target_climate = self.runs_dir / f"p{plan.parent_wepp_id}.cli"
            target_sha = self._climate_hash(target_climate)
            target_token = f"../runs/p{plan.parent_wepp_id}.cli"
            for source in plan.sources:
                token, modeled_area = self._read_pass_header(source.pass_path)
                source_runs = self.runs_dir if source.source_kind == "background" else self.subfield_runs_dir
                source_climate = self._resolve_source_climate(token, runs_dir=source_runs)
                source_sha = self._climate_hash(source_climate)
                if source_sha != target_sha:
                    raise AgFieldsWatershedIntegrationError(
                        f"Climate content differs for parent {plan.parent_wepp_id}, source {source.source_id}."
                    )
                area_residual = (
                    plan.background_area_m2
                    + math.fsum(item.represented_area_m2 for item in plan.sources if item.source_kind == "sub_field")
                    - plan.parent_raster_area_m2
                )
                row: dict[str, Any] = {
                    **_base_row(),
                    "parent_topaz_id": plan.parent_topaz_id,
                    "parent_wepp_id": plan.parent_wepp_id,
                    "source_id": source.source_id,
                    "source_kind": source.source_kind,
                    "field_id": source.field_id,
                    "sub_field_id": source.sub_field_id,
                    "source_pass_relpath": source.pass_path.resolve().relative_to(self.wd).as_posix(),
                    "source_climate_token": token,
                    "source_climate_sha256": source_sha,
                    "target_climate_token": target_token,
                    "target_climate_sha256": target_sha,
                    "parent_raster_area_m2": plan.parent_raster_area_m2,
                    "retained_field_area_m2": plan.retained_field_area_m2,
                    "background_area_m2": plan.background_area_m2,
                    "represented_area_m2": source.represented_area_m2,
                    "modeled_area_m2": modeled_area,
                    "scale": source.represented_area_m2 / modeled_area,
                    "coverage_ratio": plan.retained_field_area_m2 / plan.parent_raster_area_m2,
                    "area_residual_m2": area_residual,
                    "calendar_valid": True,
                    "climate_valid": True,
                    "row_count": None,
                    "status": "planned" if plan.affected else "materialized",
                    "rejection_reason": None,
                }
                for metric in METRICS:
                    row[f"raw_{metric}"] = None
                    row[f"weighted_{metric}"] = None
                rows.append(row)
        return rows

    def _write_source_plan(self, rows: Sequence[Mapping[str, Any]]) -> None:
        table = pa.Table.from_pylist(list(rows), schema=_source_schema())
        target = self.manifest_dir / "pass_sources.parquet"
        fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            pq.write_table(table, temporary, compression="snappy")
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _combine_affected_parents(self, source_rows: list[dict[str, Any]]) -> None:
        try:
            from wepppyo3.wepp_interchange import combine_weighted_hillslope_pass_files
        except ImportError as exc:
            raise AgFieldsWatershedIntegrationError(
                "The installed wepppyo3 release lacks combine_weighted_hillslope_pass_files."
            ) from exc

        source_index = {(row["parent_wepp_id"], row["source_id"]): row for row in source_rows}
        rows_by_parent: dict[int, list[dict[str, Any]]] = {}
        for row in source_rows:
            rows_by_parent.setdefault(int(row["parent_wepp_id"]), []).append(row)
        source_writer = _AtomicParquetWriter(self.manifest_dir / "pass_sources.parquet", _source_schema())
        event_writer = _AtomicParquetWriter(
            self.manifest_dir / "pass_event_closure.parquet", _event_schema()
        )
        run_writer = _AtomicParquetWriter(self.manifest_dir / "pass_run_closure.parquet", _run_schema())
        try:
            for plan in self.plans:
                if plan.affected:
                    sources = [
                        (source.source_id, str(source.pass_path), source.represented_area_m2)
                        for source in plan.sources
                    ]
                    diagnostics = combine_weighted_hillslope_pass_files(
                        sources,
                        str(self.output_dir / f"H{plan.parent_wepp_id}.pass.dat"),
                        plan.parent_raster_area_m2,
                        f"../runs/p{plan.parent_wepp_id}.cli",
                        strategy=ALGORITHM,
                    )
                    if diagnostics.get("algorithm") != ALGORITHM or diagnostics.get("semantic_contract") != SEMANTIC_CONTRACT:
                        raise AgFieldsWatershedIntegrationError(
                            f"Native diagnostic contract mismatch for parent {plan.parent_wepp_id}."
                        )
                    for diagnostic in diagnostics["sources"]:
                        row = source_index[(plan.parent_wepp_id, diagnostic["source_id"])]
                        row["modeled_area_m2"] = float(diagnostic["modeled_area_m2"])
                        row["scale"] = float(diagnostic["scale"])
                        row["row_count"] = int(diagnostic["row_count"])
                        row["status"] = "combined"
                        for metric in METRICS:
                            row[f"raw_{metric}"] = float(diagnostic["raw_totals"][metric])
                            row[f"weighted_{metric}"] = float(diagnostic["weighted_totals"][metric])
                    event_writer.write(self._event_rows(plan, diagnostics["events"]))
                    run_writer.write([self._run_row(plan, diagnostics)])
                source_writer.write(rows_by_parent[plan.parent_wepp_id])
            source_writer.complete()
            event_writer.complete()
            run_writer.complete()
        except Exception:  # broad-except: abort all three atomic Parquet writers together
            source_writer.abort()
            event_writer.abort()
            run_writer.abort()
            raise

    @staticmethod
    def _event_rows(plan: ParentPlan, diagnostics: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for diagnostic in diagnostics:
            row: dict[str, Any] = {
                **_base_row(),
                "parent_topaz_id": plan.parent_topaz_id,
                "parent_wepp_id": plan.parent_wepp_id,
                "year": int(diagnostic["year"]),
                "julian": int(diagnostic["julian"]),
                "event": str(diagnostic["event"]),
            }
            for source_key, prefix in (
                ("weighted_input", "weighted_input"),
                ("reparsed_output", "reparsed_output"),
                ("residuals", "residual"),
                ("budgets", "budget"),
            ):
                for metric in METRICS:
                    row[f"{prefix}_{metric}"] = float(diagnostic[source_key][metric])
            rows.append(row)
        return rows

    @staticmethod
    def _run_row(plan: ParentPlan, diagnostics: Mapping[str, Any]) -> dict[str, Any]:
        closure = diagnostics["run_closure"]
        row: dict[str, Any] = {
            **_base_row(),
            "parent_topaz_id": plan.parent_topaz_id,
            "parent_wepp_id": plan.parent_wepp_id,
            "target_area_m2": float(diagnostics["target_area_m2"]),
            "serialized_target_area_m2": float(diagnostics["serialized_target_area_m2"]),
            "target_area_residual_m2": float(diagnostics["target_area_residual_m2"]),
            "target_area_budget_m2": float(diagnostics["target_area_budget_m2"]),
        }
        for source_key, prefix in (
            ("weighted_input", "weighted_input"),
            ("reparsed_output", "reparsed_output"),
            ("residuals", "residual"),
            ("budgets", "budget"),
            ("max_abs_event_residuals", "max_abs_event_residual"),
            ("max_event_budget_ratios", "max_event_budget_ratio"),
        ):
            for metric in METRICS:
                row[f"{prefix}_{metric}"] = float(closure[source_key][metric])
        return row

    def _run_watershed(self) -> None:
        parent_ids = [plan.parent_wepp_id for plan in self.plans]
        wepp_paths = [os.path.join("..", "output", f"H{wepp_id}") for wepp_id in parent_ids]
        make_watershed_omni_contrasts_run(
            int(self.controller.climate_instance.input_years),
            wepp_paths,
            str(self.runs_dir),
            output_options={"chnwb": True, "soil_pw0": True},
            pass_family=PASS_FAMILY,
            wepp_bin=self.controller.wepp_instance.wepp_bin,
        )
        run_watershed(
            str(self.runs_dir),
            wepp_bin=self.controller.wepp_instance.wepp_bin,
        )

    def _regenerate_interchange(self) -> list[str]:
        climate = self.controller.climate_instance
        start_year_raw = getattr(climate, "calendar_start_year", None)
        start_year = int(start_year_raw) if start_year_raw not in (None, "") else None
        interchange_dir = run_wepp_hillslope_interchange(
            self.output_dir,
            pass_family=PASS_FAMILY,
            start_year=start_year,
            run_loss_interchange=True,
            run_soil_interchange=any(self.output_dir.glob("H*.soil.dat")),
            run_wat_interchange=True,
            delete_after_interchange=False,
        )
        baseflow_opts = getattr(self.controller.wepp_instance, "baseflow_opts", None) or BaseflowOpts()
        run_totalwatsed3(interchange_dir, baseflow_opts=baseflow_opts)
        run_wepp_watershed_interchange(
            self.output_dir,
            pass_family=PASS_FAMILY,
            start_year=start_year,
            run_chan_out_interchange=(self.output_dir / "chan.out").exists(),
            run_soil_interchange=(self.output_dir / "soil_pw0.txt").exists(),
            run_chnwb_interchange=(self.output_dir / "chnwb.txt").exists(),
            delete_after_interchange=False,
        )
        generate_interchange_documentation(interchange_dir)
        required = [
            "H.pass.parquet",
            "H.wat.parquet",
            "ebe_pw0.parquet",
            "loss_pw0.out.parquet",
            "loss_pw0.hill.parquet",
            "loss_pw0.chn.parquet",
            "totalwatsed3.parquet",
            "README.md",
        ]
        if (self.output_dir / "chnwb.txt").exists():
            required.append("chnwb.parquet")
        missing = [name for name in required if not (interchange_dir / name).exists()]
        if missing:
            raise AgFieldsWatershedIntegrationError(
                f"Isolated interchange is missing required resources: {', '.join(missing)}"
            )
        return [(interchange_dir / name).resolve().relative_to(self.wd).as_posix() for name in required]

    def _executable_identity(self, configured: str | None, *, hill: bool) -> dict[str, Any]:
        name = str(configured or "latest")
        suffix = "_hill" if hill else ""
        candidate = Path(wepp_bin_dir) / f"{name}{suffix}"
        if not candidate.exists() and configured is None:
            candidate = Path(wepp_bin_dir) / f"wepp{suffix}"
        return {
            "configured": configured,
            "role": "hillslope" if hill else "watershed",
            "sha256": _sha256(candidate.resolve()) if candidate.exists() else None,
        }

    @staticmethod
    def _weighted_kernel_sha256() -> str:
        from wepppyo3.wepp_interchange import wepp_interchange_rust

        return _sha256(Path(wepp_interchange_rust.__file__).resolve())

    def _success_summary(self, required_resources: Sequence[str]) -> dict[str, Any]:
        pass_count = len(list(self.output_dir.glob("H*.pass.dat")))
        prep = RedisPrep.tryGetInstance(str(self.wd))
        upstream_timestamps = {
            str(task): prep[str(task)] if prep is not None else None for task in UPSTREAM_TASKS
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "semantic_contract": SEMANTIC_CONTRACT,
            "adr": ADR,
            "status": "completed",
            "source_signature": self.source_signature,
            "stage4_source_signature": getattr(self.controller, "_wepp_source_signature", None),
            "upstream_timestamps": upstream_timestamps,
            "started_at": self.started_at,
            "completed_at": _utc_now(),
            "run_root": self.root.resolve().relative_to(self.wd).as_posix(),
            "pass_family": PASS_FAMILY,
            "parent_wepp_bin": self._executable_identity(self.controller.wepp_instance.wepp_bin, hill=False),
            "ag_fields_wepp_bin": self._executable_identity(self.controller.wepp_bin, hill=True),
            "parent_count": len(self.plans),
            "affected_parent_count": sum(plan.affected for plan in self.plans),
            "sub_field_source_count": sum(len(plan.sources) - 1 for plan in self.plans),
            "full_coverage_parent_count": sum(plan.full_coverage for plan in self.plans),
            "pass_count": pass_count,
            "required_resources": list(required_resources),
            "warnings": [LIMITATION],
            "manifest_paths": {
                name: (self.manifest_dir / name).resolve().relative_to(self.wd).as_posix()
                for name in (
                    "pass_sources.parquet",
                    "pass_event_closure.parquet",
                    "pass_run_closure.parquet",
                    "integration_summary.json",
                    "README.md",
                )
            },
            "failure": None,
        }

    def _write_failure_summary(self, exc: Exception) -> None:
        expected = self.wd / "wepp" / "ag_fields" / "watershed"
        if self.root.absolute() != expected.absolute() or any(
            path.is_symlink() for path in (expected.parent.parent, expected.parent, expected)
        ):
            return
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            "semantic_contract": SEMANTIC_CONTRACT,
            "adr": ADR,
            "status": "failed",
            "source_signature": self.source_signature,
            "stage4_source_signature": getattr(self.controller, "_wepp_source_signature", None),
            "upstream_timestamps": {},
            "started_at": self.started_at,
            "completed_at": _utc_now(),
            "run_root": self.root.absolute().relative_to(self.wd).as_posix(),
            "pass_family": PASS_FAMILY,
            "parent_wepp_bin": self._executable_identity(self.controller.wepp_instance.wepp_bin, hill=False),
            "ag_fields_wepp_bin": self._executable_identity(self.controller.wepp_bin, hill=True),
            "parent_count": len(self.plans),
            "affected_parent_count": sum(plan.affected for plan in self.plans),
            "sub_field_source_count": sum(len(plan.sources) - 1 for plan in self.plans),
            "full_coverage_parent_count": sum(plan.full_coverage for plan in self.plans),
            "pass_count": len(list(self.output_dir.glob("H*.pass.dat"))),
            "required_resources": [],
            "warnings": [LIMITATION],
            "manifest_paths": {},
            "failure": {
                "phase": self.phase,
                "type": type(exc).__name__,
                "message": self._public_error_message(exc),
            },
        }
        _atomic_json(self.manifest_dir / "integration_summary.json", summary)

    def _write_manifest_readme(self, summary: Mapping[str, Any]) -> None:
        metrics = ", ".join(f"`{metric}`" for metric in METRICS)
        text = f"""# AgFields Integrated Watershed Evaluation Bundle

This directory records the versioned source and conservation evidence for the
isolated AgFields Concept 2 watershed run.

> **Scientific limitation:** {LIMITATION}

Scientific qualification is pending Mariana Dobre's review. These artifacts prove
engineering accounting and executable integration; they do not establish that the
outlet-injection approximation is scientifically acceptable for another use.

## Artifact contract

- Schema version: `{SCHEMA_VERSION}`
- Algorithm: `{ALGORITHM}`
- Semantic contract: `{SEMANTIC_CONTRACT}`
- Decision: `{ADR}`
- PASS family: `{PASS_FAMILY}`
- Parents: {summary['parent_count']}
- Affected parents: {summary['affected_parent_count']}
- Independent sub-field sources: {summary['sub_field_source_count']}

`pass_sources.parquet` records raster areas, scales, climate proof, and source
full-run totals. The hard-linked `materialized_parent_pass/` inventory preserves
the exact parent background PASS inputs used by the combiner without duplicating
their file data. `pass_event_closure.parquet` records serialized event closure.
`pass_run_closure.parquet` records full-run closure and maximum event ratios.
`integration_summary.json` records executable identities and required outputs.

The conserved metric suffixes, in order, are {metrics}. Water suffixes ending in
`_m3` are cubic metres; sediment suffixes ending in `_kg` are kilograms.

`pass_sources.parquet` columns, in exact order, are the four contract identifiers;
`parent_topaz_id`, `parent_wepp_id`, `source_id`, `source_kind`, `field_id`,
`sub_field_id`; `source_pass_relpath`, `source_climate_token`,
`source_climate_sha256`, `target_climate_token`, `target_climate_sha256`;
`parent_raster_area_m2`, `retained_field_area_m2`, `background_area_m2`,
`represented_area_m2`, `modeled_area_m2`, `scale`, `coverage_ratio`,
`area_residual_m2`; `calendar_valid`, `climate_valid`, `row_count`, `status`,
`rejection_reason`; then `raw_<metric>` and `weighted_<metric>` for every suffix.

`pass_event_closure.parquet` starts with the four contract identifiers,
`parent_topaz_id`, `parent_wepp_id`, `year`, `julian`, and `event`, followed by
`weighted_input_<metric>`, `reparsed_output_<metric>`, `residual_<metric>`, and
`budget_<metric>` groups. `pass_run_closure.parquet` starts with the four contract
identifiers, parent ids, target/serialized area and their residual/budget, followed
by those four metric groups plus `max_abs_event_residual_<metric>` and
`max_event_budget_ratio_<metric>`. Every Parquet schema repeats the four contract
identifiers in file metadata.

All paths stored in these artifacts are relative to the project run root. Baseline
results remain under `wepp/output`; independent field results remain under
`wepp/ag_fields/output`; the integrated results are under
`wepp/ag_fields/watershed/output`.
"""
        _atomic_text(self.manifest_dir / "README.md", text)


__all__ = [
    "ADR",
    "ALGORITHM",
    "LIMITATION",
    "METRICS",
    "PASS_FAMILY",
    "SCHEMA_VERSION",
    "SEMANTIC_CONTRACT",
    "AgFieldsWatershedIntegrationError",
    "AgFieldsWatershedIntegrator",
    "ParentPlan",
    "SourcePlan",
]
