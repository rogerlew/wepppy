#!/usr/bin/env python3
"""Validate and summarize generated AgFields routing-scheme result trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import pyarrow.parquet as pq


SCHEMES: dict[str, dict[str, object]] = {
    "concept_1": {
        "slug": "concept-1",
        "description": (
            "Field-aware hillslope routing routes represented fields through "
            "downstream overland flow elements."
        ),
        "manifests": (
            "ofe_plan.parquet",
            "parent_candidates.parquet",
            "parent_summary.parquet",
            "parent_routing.parquet",
            "planning_summary.json",
            "integration_summary.json",
            "README.md",
        ),
    },
    "concept_2": {
        "slug": "concept-2",
        "description": (
            "Direct sub-field outlet injection preserves independent sub-field "
            "results without buffer routing."
        ),
        "manifests": (
            "pass_sources.parquet",
            "pass_event_closure.parquet",
            "pass_run_closure.parquet",
            "integration_summary.json",
            "README.md",
        ),
    },
    "hybrid": {
        "slug": "hybrid",
        "description": (
            "Connectivity-aware mixed routing injects channel-connected sub-fields "
            "and routes the others through overland flow elements."
        ),
        "manifests": (
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
        ),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_metrics(root: Path) -> tuple[int, int]:
    file_count = 0
    size_bytes = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        for entry in os.scandir(directory):
            path = Path(entry.path)
            if entry.is_symlink():
                raise RuntimeError(f"Scheme tree contains a symlink: {path}")
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                file_count += 1
                size_bytes += entry.stat(follow_symlinks=False).st_size
            else:
                raise RuntimeError(f"Unsupported scheme-tree entry: {path}")
    return file_count, size_bytes


def _counter(values: Iterable[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _finite(values: Iterable[object]) -> list[float]:
    result: list[float] = []
    for value in values:
        if value is None:
            continue
        number = float(value)
        if math.isfinite(number):
            result.append(number)
    return result


def _max_abs(values: Iterable[object]) -> float | None:
    finite = _finite(values)
    return max((abs(value) for value in finite), default=None)


def _min(values: Iterable[object]) -> float | None:
    finite = _finite(values)
    return min(finite, default=None)


def _max(values: Iterable[object]) -> float | None:
    finite = _finite(values)
    return max(finite, default=None)


def _parquet_rows(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows


def _read_columns(path: Path, requested: Iterable[str]) -> dict[str, list[object]]:
    schema_names = set(pq.read_schema(path).names)
    columns = [name for name in requested if name in schema_names]
    if not columns:
        return {}
    table = pq.read_table(path, columns=columns)
    return {name: table[name].to_pylist() for name in columns}


def _parent_routing_metrics(path: Path) -> dict[str, object]:
    columns = _read_columns(
        path,
        (
            "parent_wepp_id",
            "routing_branch",
            "status",
            "rejection_reason",
            "area_closure_residual_m2",
            "pass_area_residual_m2",
            "residual_pass_area_residual_m2",
        ),
    )
    result: dict[str, object] = {
        "row_count": _parquet_rows(path),
        "distinct_parent_count": len(set(columns.get("parent_wepp_id", []))),
        "routing_branch_counts": _counter(columns.get("routing_branch", [])),
        "status_counts": _counter(columns.get("status", [])),
        "rejection_count": sum(value is not None for value in columns.get("rejection_reason", [])),
    }
    for name in (
        "area_closure_residual_m2",
        "pass_area_residual_m2",
        "residual_pass_area_residual_m2",
    ):
        if name in columns:
            result[f"max_abs_{name}"] = _max_abs(columns[name])
    return result


def _ofe_metrics(path: Path) -> dict[str, object]:
    columns = _read_columns(
        path,
        (
            "parent_wepp_id",
            "routing_branch",
            "fit_status",
            "classification_agreement",
            "signed_area_error_m2",
        ),
    )
    return {
        "row_count": _parquet_rows(path),
        "distinct_parent_count": len(set(columns.get("parent_wepp_id", []))),
        "routing_branch_counts": _counter(columns.get("routing_branch", [])),
        "fit_status_counts": _counter(columns.get("fit_status", [])),
        "minimum_classification_agreement": _min(columns.get("classification_agreement", [])),
        "max_abs_signed_area_error_m2": _max_abs(columns.get("signed_area_error_m2", [])),
    }


def _source_metrics(path: Path) -> dict[str, object]:
    columns = _read_columns(
        path,
        (
            "parent_wepp_id",
            "source_kind",
            "status",
            "area_residual_m2",
            "calendar_valid",
            "climate_valid",
        ),
    )
    return {
        "row_count": _parquet_rows(path),
        "distinct_parent_count": len(set(columns.get("parent_wepp_id", []))),
        "source_kind_counts": _counter(columns.get("source_kind", [])),
        "status_counts": _counter(columns.get("status", [])),
        "max_abs_area_residual_m2": _max_abs(columns.get("area_residual_m2", [])),
        "invalid_calendar_count": sum(value is not True for value in columns.get("calendar_valid", [])),
        "invalid_climate_count": sum(value is not True for value in columns.get("climate_valid", [])),
    }


def _run_closure_metrics(path: Path) -> dict[str, object]:
    schema_names = pq.read_schema(path).names
    selected = [
        name
        for name in schema_names
        if name == "target_area_residual_m2"
        or name.startswith("residual_")
        or name.startswith("max_abs_event_residual_")
        or name.startswith("max_event_budget_ratio_")
    ]
    columns = _read_columns(path, selected)
    maxima = {
        name: (_max(columns[name]) if name.startswith("max_event_budget_ratio_") else _max_abs(columns[name]))
        for name in selected
    }
    return {"row_count": _parquet_rows(path), "column_maxima": maxima}


def _subfield_metrics(path: Path) -> dict[str, object]:
    columns = _read_columns(
        path,
        (
            "sub_field_id",
            "channel_connected",
            "routing_branch",
            "direct_channel_outlet_cells",
        ),
    )
    connected = columns.get("channel_connected", [])
    branches = columns.get("routing_branch", [])
    mismatch_count = sum(
        (branch == "concept_2") != bool(is_connected)
        for is_connected, branch in zip(connected, branches)
    )
    return {
        "row_count": _parquet_rows(path),
        "distinct_sub_field_count": len(set(columns.get("sub_field_id", []))),
        "channel_connected_counts": _counter(connected),
        "routing_branch_counts": _counter(branches),
        "classifier_branch_mismatch_count": mismatch_count,
        "direct_channel_outlet_cell_count": sum(
            int(value or 0) for value in columns.get("direct_channel_outlet_cells", [])
        ),
    }


def _calendar_inventory(runs_dir: Path) -> dict[str, object]:
    paths = sorted(runs_dir.glob("p*.cli"), key=lambda path: path.name)
    digest = hashlib.sha256()
    for path in paths:
        file_sha = _sha256(path)
        digest.update(f"{path.name}\0{path.stat().st_size}\0{file_sha}\n".encode())
    return {"file_count": len(paths), "inventory_sha256": digest.hexdigest()}


def _require_below(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    if not resolved.is_file() or path.is_symlink():
        raise FileNotFoundError(path)
    return resolved


def _scheme_summary(run_root: Path, scheme: str, contract: Mapping[str, object]) -> dict[str, object]:
    slug = str(contract["slug"])
    root = run_root / "wepp" / "ag_fields" / "watershed" / slug
    if not root.is_dir() or root.is_symlink():
        raise FileNotFoundError(root)
    manifest = root / "manifest"
    expected_manifests = tuple(str(name) for name in contract["manifests"])
    for name in expected_manifests:
        _require_below(manifest / name, root)

    with (manifest / "integration_summary.json").open(encoding="utf-8") as stream:
        summary = json.load(stream)
    if summary.get("status") != "completed":
        raise RuntimeError(f"{scheme} is not completed")
    if summary.get("scheme") != scheme or summary.get("scheme_slug") != slug:
        raise RuntimeError(f"{scheme} summary identity does not match its fixed root")

    missing_required_resources = []
    for relative in summary.get("required_resources", []):
        try:
            _require_below(run_root / str(relative), root)
        except (FileNotFoundError, ValueError):
            missing_required_resources.append(str(relative))
    missing_manifest_paths = []
    for relative in summary.get("manifest_paths", {}).values():
        try:
            _require_below(run_root / str(relative), root)
        except (FileNotFoundError, ValueError):
            missing_manifest_paths.append(str(relative))

    file_count, size_bytes = _tree_metrics(root)
    parquets = {
        path.name: _parquet_rows(path)
        for path in sorted(manifest.glob("*.parquet"), key=lambda path: path.name)
    }
    result: dict[str, object] = {
        "scheme": scheme,
        "scheme_slug": slug,
        "description": str(contract["description"]),
        "algorithm": summary.get("algorithm"),
        "source_signature": summary.get("source_signature"),
        "stage4_source_signature": summary.get("stage4_source_signature"),
        "started_at": summary.get("started_at"),
        "completed_at": summary.get("completed_at"),
        "parent_count": summary.get("parent_count"),
        "pass_count": summary.get("pass_count"),
        "parent_wepp_bin": summary.get("parent_wepp_bin"),
        "ag_fields_wepp_bin": summary.get("ag_fields_wepp_bin"),
        "scientific_limitations": summary.get("warnings", []),
        "tree_file_count": file_count,
        "tree_size_bytes": size_bytes,
        "manifest_parquet_row_counts": parquets,
        "required_resource_count": len(summary.get("required_resources", [])),
        "missing_required_resources": missing_required_resources,
        "missing_manifest_paths": missing_manifest_paths,
        "calendar_inventory": _calendar_inventory(root / "runs"),
    }
    if (manifest / "parent_routing.parquet").is_file():
        result["parent_routing"] = _parent_routing_metrics(manifest / "parent_routing.parquet")
    if (manifest / "ofe_plan.parquet").is_file():
        result["ofe_plan"] = _ofe_metrics(manifest / "ofe_plan.parquet")
    if (manifest / "pass_sources.parquet").is_file():
        result["pass_sources"] = _source_metrics(manifest / "pass_sources.parquet")
    if (manifest / "pass_event_closure.parquet").is_file():
        result["pass_event_closure"] = {
            "row_count": _parquet_rows(manifest / "pass_event_closure.parquet")
        }
    if (manifest / "pass_run_closure.parquet").is_file():
        result["pass_run_closure"] = _run_closure_metrics(
            manifest / "pass_run_closure.parquet"
        )
    if (manifest / "subfield_routing.parquet").is_file():
        result["subfield_routing"] = _subfield_metrics(manifest / "subfield_routing.parquet")
    return result


def summarize(run_root: Path) -> dict[str, object]:
    resolved_root = run_root.resolve()
    schemes = {
        name: _scheme_summary(resolved_root, name, contract)
        for name, contract in SCHEMES.items()
    }
    stage4_signatures = {
        str(item["stage4_source_signature"]) for item in schemes.values()
    }
    calendar_digests = {
        str(item["calendar_inventory"]["inventory_sha256"])
        for item in schemes.values()
    }
    errors = []
    if len(stage4_signatures) != 1 or stage4_signatures == {"None"}:
        errors.append("stage4 source signatures are missing or differ across schemes")
    if len(calendar_digests) != 1:
        errors.append("parent climate inventories differ across schemes")
    for name, item in schemes.items():
        if item["missing_required_resources"]:
            errors.append(f"{name} is missing required resources")
        if item["missing_manifest_paths"]:
            errors.append(f"{name} is missing summary-declared manifest paths")
        subfields = item.get("subfield_routing")
        if isinstance(subfields, Mapping) and subfields.get("classifier_branch_mismatch_count"):
            errors.append(f"{name} disagrees with its persisted connectivity classifier")
    return {
        "schema_version": "1.0",
        "runid": resolved_root.name,
        "valid": not errors,
        "errors": errors,
        "common_stage4_source_signature": next(iter(stage4_signatures), None),
        "common_calendar_inventory_sha256": next(iter(calendar_digests), None),
        "schemes": schemes,
    }


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(args.run_root)
    if args.output is not None:
        _atomic_json(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
