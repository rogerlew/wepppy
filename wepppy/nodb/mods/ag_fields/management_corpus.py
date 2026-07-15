"""Inventory synthesized AgFields management graphs from an explicit OFE plan.

This command is intentionally independent of a WEPPcloud run controller.  It
materializes and reparses the complete deduplicated management corpus so a WEPP
hillslope capacity can be selected from evidence rather than from the current
20-scenario production ceiling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.management import read_management
from wepppy.wepp.management.managements import Management
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth

from .concept1_inputs import _coerce_subfield_id, _validated_rows


SCHEMA_VERSION = "1.0"
ALGORITHM = "ag_fields_management_corpus_v1"

__all__ = [
    "ALGORITHM",
    "SCHEMA_VERSION",
    "ManagementCorpusError",
    "run_management_corpus",
]


class ManagementCorpusError(RuntimeError):
    """Raised when an OFE plan cannot produce a complete management corpus."""


_METRIC_FIELDS = (
    "ofe_count",
    "plant_scenarios",
    "operation_scenarios",
    "initial_scenarios",
    "surface_scenarios",
    "contour_scenarios",
    "drainage_scenarios",
    "yearly_scenarios",
    "rotation_count",
    "max_rotation_years",
    "max_crops_per_ofe_year",
    "perennial_cut_entries",
    "perennial_graze_entries",
    "rangeland_graze_entries",
    "max_nested_cut_or_graze_cycles",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    _atomic_bytes(path, payload)


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_parquet(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    schema: pa.Schema,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        table = pa.Table.from_pylist(list(rows), schema=schema)
        pq.write_table(table, temporary, compression="snappy")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _schema(fields: Sequence[tuple[str, pa.DataType]]) -> pa.Schema:
    return pa.schema(
        fields,
        metadata={
            b"schema_version": SCHEMA_VERSION.encode("ascii"),
            b"algorithm": ALGORITHM.encode("ascii"),
        },
    )


def _corpus_schema() -> pa.Schema:
    fields: list[tuple[str, pa.DataType]] = [
        ("schema_version", pa.string()),
        ("algorithm", pa.string()),
        ("parent_wepp_id", pa.int64()),
        ("source_management_count", pa.int64()),
        ("unique_source_management_count", pa.int64()),
    ]
    fields.extend((metric, pa.int64()) for metric in _METRIC_FIELDS)
    fields.extend(
        [
            ("source_manifest_sha256", pa.string()),
            ("generated_relpath", pa.string()),
            ("generated_sha256", pa.string()),
            ("serialization_reparsed", pa.bool_()),
        ]
    )
    return _schema(fields)


def _source_schema() -> pa.Schema:
    return _schema(
        [
            ("schema_version", pa.string()),
            ("algorithm", pa.string()),
            ("parent_wepp_id", pa.int64()),
            ("ofe_id", pa.int64()),
            ("source_kind", pa.string()),
            ("sub_field_id", pa.int64()),
            ("source_path", pa.string()),
            ("source_sha256", pa.string()),
        ]
    )


def _read_plan(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ManagementCorpusError(f"OFE plan does not exist: {path}")
    table = pq.read_table(path)
    required = {
        "parent_wepp_id",
        "ofe_id",
        "normalized_start",
        "normalized_end",
        "source_kind",
        "sub_field_id",
    }
    missing = sorted(required - set(table.column_names))
    if missing:
        raise ManagementCorpusError(
            f"OFE plan is missing required columns: {missing}"
        )
    rows = table.to_pylist()
    if not rows:
        raise ManagementCorpusError("OFE plan contains no rows.")
    return rows


def _source_path(
    row: Mapping[str, Any],
    *,
    parent_wepp_id: int,
    parent_runs_dir: Path,
    subfield_runs_dir: Path,
) -> tuple[Path, int | None]:
    if row["source_kind"] == "background":
        return parent_runs_dir / f"p{parent_wepp_id}.man", None
    sub_field_id = _coerce_subfield_id(row)
    return subfield_runs_dir / f"p{sub_field_id}.man", sub_field_id


def _nested_cycle_metrics(management: Management) -> dict[str, int]:
    perennial_cut_entries = 0
    perennial_graze_entries = 0
    rangeland_graze_entries = 0
    max_nested_cycles = 0

    for yearly in management.years:
        data = yearly.data
        perennial = getattr(data, "perennial", None)
        if perennial not in (None, ""):
            ncut = getattr(perennial, "ncut", 0)
            if isinstance(ncut, int):
                perennial_cut_entries += ncut
                max_nested_cycles = max(max_nested_cycles, ncut)
            ncycle = getattr(perennial, "ncycle", 0)
            if isinstance(ncycle, int):
                perennial_graze_entries += ncycle
                max_nested_cycles = max(max_nested_cycles, ncycle)

        graze = getattr(data, "graze", None)
        graze_loops = getattr(graze, "loops", None)
        if graze_loops is not None:
            cycle_count = len(graze_loops)
            rangeland_graze_entries += cycle_count
            max_nested_cycles = max(max_nested_cycles, cycle_count)

    return {
        "perennial_cut_entries": perennial_cut_entries,
        "perennial_graze_entries": perennial_graze_entries,
        "rangeland_graze_entries": rangeland_graze_entries,
        "max_nested_cut_or_graze_cycles": max_nested_cycles,
    }


def _management_metrics(management: Management) -> dict[str, int]:
    rotation_years = [rotation.nyears for rotation in management.man.loops]
    crop_counts = [
        ofe.nycrop
        for rotation in management.man.loops
        for year in rotation.years
        for ofe in year
    ]
    metrics = {
        "ofe_count": int(management.nofe or 0),
        "plant_scenarios": management.ncrop,
        "operation_scenarios": management.nop,
        "initial_scenarios": management.nini,
        "surface_scenarios": management.nseq,
        "contour_scenarios": management.ncnt,
        "drainage_scenarios": management.ndrain,
        "yearly_scenarios": management.nscen,
        "rotation_count": management.man.nrots,
        "max_rotation_years": max(rotation_years, default=0),
        "max_crops_per_ofe_year": max(crop_counts, default=0),
    }
    metrics.update(_nested_cycle_metrics(management))
    return metrics


def _render_reparse_replace(
    *,
    synth: ManagementMultipleOfeSynth,
    destination: Path,
) -> tuple[Management, str]:
    rendered = synth.render(enforce_yearly_scenario_limit=False)
    payload = rendered.encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        reparsed = read_management(str(temporary))
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return reparsed, _sha256_bytes(payload)


def _distribution(rows: Sequence[Mapping[str, Any]], metric: str) -> dict[str, int]:
    counts = Counter(int(row[metric]) for row in rows)
    return {str(value): counts[value] for value in sorted(counts)}


def _maximum(rows: Sequence[Mapping[str, Any]], metric: str) -> dict[str, Any]:
    value = max(int(row[metric]) for row in rows)
    parent_ids = sorted(
        int(row["parent_wepp_id"])
        for row in rows
        if int(row[metric]) == value
    )
    retained_ids = parent_ids[:25]
    return {
        "value": value,
        "parent_count": len(parent_ids),
        "parent_wepp_ids": retained_ids,
        "parent_wepp_ids_truncated": len(retained_ids) != len(parent_ids),
    }


def _process_parent(
    request: tuple[
        int,
        list[dict[str, Any]],
        Path,
        Path,
        Path,
    ],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    (
        parent_wepp_id,
        plan_rows,
        parent_runs_dir,
        subfield_runs_dir,
        output_dir,
    ) = request
    ordered = _validated_rows(plan_rows, parent_wepp_id=parent_wepp_id)
    management_cache: dict[Path, Management] = {}
    hash_cache: dict[Path, str] = {}
    stack: list[Management] = []
    parent_source_rows: list[dict[str, Any]] = []

    for row in ordered:
        path, sub_field_id = _source_path(
            row,
            parent_wepp_id=parent_wepp_id,
            parent_runs_dir=parent_runs_dir,
            subfield_runs_dir=subfield_runs_dir,
        )
        if not path.is_file():
            raise ManagementCorpusError(
                f"Parent {parent_wepp_id} OFE {int(row['ofe_id'])} management "
                f"does not exist: {path}"
            )
        resolved_path = path.resolve()
        if resolved_path not in management_cache:
            management_cache[resolved_path] = read_management(str(resolved_path))
            hash_cache[resolved_path] = _sha256(resolved_path)
        stack.append(management_cache[resolved_path])
        parent_source_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "algorithm": ALGORITHM,
                "parent_wepp_id": parent_wepp_id,
                "ofe_id": int(row["ofe_id"]),
                "source_kind": str(row["source_kind"]),
                "sub_field_id": sub_field_id,
                "source_path": str(resolved_path),
                "source_sha256": hash_cache[resolved_path],
            }
        )

    synth = ManagementMultipleOfeSynth(
        stack=stack,
        deduplicate_scenarios=True,
    )
    generated_relpath = Path("managements") / f"p{parent_wepp_id}.man"
    reparsed, generated_sha256 = _render_reparse_replace(
        synth=synth,
        destination=output_dir / generated_relpath,
    )
    metrics = _management_metrics(reparsed)
    if metrics["ofe_count"] != len(ordered):
        raise ManagementCorpusError(
            f"Parent {parent_wepp_id} reparsed with {metrics['ofe_count']} OFEs; "
            f"the plan contains {len(ordered)}."
        )
    source_manifest_sha256 = _sha256_bytes(
        _canonical_json_bytes(parent_source_rows)
    )
    corpus_row = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "parent_wepp_id": parent_wepp_id,
        "source_management_count": len(stack),
        "unique_source_management_count": len(management_cache),
        **metrics,
        "source_manifest_sha256": source_manifest_sha256,
        "generated_relpath": generated_relpath.as_posix(),
        "generated_sha256": generated_sha256,
        "serialization_reparsed": True,
    }
    return corpus_row, parent_source_rows


def run_management_corpus(
    *,
    ofe_plan_path: Path,
    parent_runs_dir: Path,
    subfield_runs_dir: Path,
    output_dir: Path,
    workers: int = 1,
) -> dict[str, Any]:
    """Materialize, reparse, and inventory every parent in an OFE plan."""
    started = time.monotonic()
    if not parent_runs_dir.is_dir():
        raise ManagementCorpusError(
            f"Parent runs directory does not exist: {parent_runs_dir}"
        )
    if not subfield_runs_dir.is_dir():
        raise ManagementCorpusError(
            f"Sub-field runs directory does not exist: {subfield_runs_dir}"
        )
    if workers < 1:
        raise ManagementCorpusError("workers must be at least 1.")

    plan_rows = _read_plan(ofe_plan_path)
    rows_by_parent: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        rows_by_parent[int(row["parent_wepp_id"])].append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    requests = [
        (
            parent_wepp_id,
            rows_by_parent[parent_wepp_id],
            parent_runs_dir,
            subfield_runs_dir,
            output_dir,
        )
        for parent_wepp_id in sorted(rows_by_parent)
    ]
    if workers == 1:
        results = [_process_parent(request) for request in requests]
    else:
        with ProcessPoolExecutor(max_workers=min(workers, len(requests))) as executor:
            results = list(executor.map(_process_parent, requests))

    corpus_rows = [row for row, _source_rows in results]
    source_rows = [
        source_row
        for _corpus_row, parent_source_rows in results
        for source_row in parent_source_rows
    ]

    _atomic_parquet(
        output_dir / "management_corpus.parquet",
        corpus_rows,
        _corpus_schema(),
    )
    _atomic_parquet(
        output_dir / "management_sources.parquet",
        source_rows,
        _source_schema(),
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "inputs": {
            "ofe_plan": {
                "path": str(ofe_plan_path.resolve()),
                "sha256": _sha256(ofe_plan_path),
            },
            "parent_runs": str(parent_runs_dir.resolve()),
            "subfield_runs": str(subfield_runs_dir.resolve()),
        },
        "counts": {
            "parents": len(corpus_rows),
            "plan_rows": len(plan_rows),
            "unique_source_managements": len(
                {row["source_path"] for row in source_rows}
            ),
            "serialized_and_reparsed": sum(
                bool(row["serialization_reparsed"]) for row in corpus_rows
            ),
        },
        "workers": workers,
        "maxima": {
            metric: _maximum(corpus_rows, metric) for metric in _METRIC_FIELDS
        },
        "distributions": {
            metric: _distribution(corpus_rows, metric) for metric in _METRIC_FIELDS
        },
        "artifacts": {
            "corpus": "management_corpus.parquet",
            "sources": "management_sources.parquet",
            "managements": "managements/",
        },
        "elapsed_seconds": time.monotonic() - started,
    }
    _atomic_json(output_dir / "management_corpus_summary.json", summary)
    return summary


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ofe-plan", required=True, type=Path)
    parser.add_argument("--parent-runs", required=True, type=Path)
    parser.add_argument("--subfield-runs", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="Independent parent-management processes (default: up to 8).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_management_corpus(
        ofe_plan_path=args.ofe_plan,
        parent_runs_dir=args.parent_runs,
        subfield_runs_dir=args.subfield_runs,
        output_dir=args.output_dir,
        workers=args.workers,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
