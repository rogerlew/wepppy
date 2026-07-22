#!/usr/bin/env python3
"""Inventory gNATSGO MUKEY coverage and summarize SSURGO build diagnostics.

This is an offline research scaffold for the SSURGO intelligent-fallback study.
It does not call Soil Data Access, build WEPP soils, or change a run's soil
assignments. A future collector writes one ``mukey_build`` JSON object per line
after a SSURGO build; this tool combines those records with a streamed raster
inventory to quantify the coverage of valid and residual-invalid MUKEYs.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


DIAGNOSTIC_SCHEMA_VERSION = 1
DIAGNOSTIC_RECORD_TYPE = "mukey_build"
VALID_OUTCOMES = frozenset({"valid", "residual_invalid", "worker_failed"})
REQUIRED_DIAGNOSTIC_FIELDS = (
    "schema_version",
    "record_type",
    "cohort_id",
    "raster_source",
    "mukey",
    "outcome",
    "reason_codes",
    "build_configuration",
    "failure_evidence",
    "raw_data_completeness",
    "retained_comparison_features",
    "repair_provenance",
)
REQUIRED_FAILURE_EVIDENCE_FIELDS = (
    "component_count",
    "eligible_component_count",
    "horizon_count",
    "post_default_valid_horizon_count",
    "emitted_wepp_layer_count",
    "restrictive_layer_state",
)


def _normalize_mukey(value: object) -> str:
    """Return a canonical positive integer MUKEY string."""
    if isinstance(value, bool):
        raise ValueError("MUKEY must be an integer, not a boolean")
    try:
        mukey = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid MUKEY: {value!r}") from exc
    if mukey <= 0:
        raise ValueError(f"MUKEY must be positive: {mukey}")
    return str(mukey)


def _validate_diagnostic_record(record: Mapping[str, Any], *, line_number: int) -> dict[str, Any]:
    """Validate and normalize one version-1 MUKEY diagnostic record."""
    missing = [field for field in REQUIRED_DIAGNOSTIC_FIELDS if field not in record]
    if missing:
        raise ValueError(f"Diagnostic line {line_number} is missing fields: {', '.join(missing)}")
    if record["schema_version"] != DIAGNOSTIC_SCHEMA_VERSION:
        raise ValueError(
            f"Diagnostic line {line_number} has unsupported schema version: "
            f"{record['schema_version']!r}"
        )
    if record["record_type"] != DIAGNOSTIC_RECORD_TYPE:
        raise ValueError(
            f"Diagnostic line {line_number} must have record_type "
            f"{DIAGNOSTIC_RECORD_TYPE!r}"
        )
    if not isinstance(record["cohort_id"], str) or not record["cohort_id"].strip():
        raise ValueError(f"Diagnostic line {line_number} has an empty cohort_id")
    if not isinstance(record["raster_source"], str) or not record["raster_source"].strip():
        raise ValueError(f"Diagnostic line {line_number} has an empty raster_source")
    outcome = record["outcome"]
    if outcome not in VALID_OUTCOMES:
        raise ValueError(
            f"Diagnostic line {line_number} has unsupported outcome {outcome!r}; "
            f"expected one of {sorted(VALID_OUTCOMES)}"
        )
    reason_codes = record["reason_codes"]
    if not isinstance(reason_codes, list) or any(
        not isinstance(code, str) or not code for code in reason_codes
    ):
        raise ValueError(f"Diagnostic line {line_number} has invalid reason_codes")
    if outcome != "valid" and not reason_codes:
        raise ValueError(f"Diagnostic line {line_number} needs a reason code for {outcome}")
    for field in (
        "build_configuration",
        "failure_evidence",
        "raw_data_completeness",
        "retained_comparison_features",
    ):
        if not isinstance(record[field], Mapping):
            raise ValueError(f"Diagnostic line {line_number} has invalid {field}")
    missing_evidence = [
        field for field in REQUIRED_FAILURE_EVIDENCE_FIELDS if field not in record["failure_evidence"]
    ]
    if missing_evidence:
        raise ValueError(
            f"Diagnostic line {line_number} has incomplete failure_evidence: "
            f"{', '.join(missing_evidence)}"
        )
    if not isinstance(record["repair_provenance"], list):
        raise ValueError(f"Diagnostic line {line_number} has invalid repair_provenance")

    normalized = dict(record)
    normalized["mukey"] = _normalize_mukey(record["mukey"])
    normalized["reason_codes"] = sorted(set(reason_codes))
    return normalized


def diagnostic_record_template() -> dict[str, Any]:
    """Return the version-1 JSONL contract for one future build diagnostic."""
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "record_type": DIAGNOSTIC_RECORD_TYPE,
        "cohort_id": "replace-with-immutable-cohort-id",
        "raster_source": "replace-with-raster-version-or-path",
        "mukey": "replace-with-positive-mukey",
        "outcome": "residual_invalid",
        "reason_codes": ["replace-with-reason-code"],
        "build_configuration": {},
        "failure_evidence": {
            "component_count": None,
            "eligible_component_count": None,
            "horizon_count": None,
            "post_default_valid_horizon_count": None,
            "emitted_wepp_layer_count": None,
            "restrictive_layer_state": None,
        },
        "raw_data_completeness": {},
        "retained_comparison_features": {},
        "repair_provenance": [],
    }


def read_diagnostic_records(path: Path | str) -> Iterator[dict[str, Any]]:
    """Yield validated JSONL diagnostic records from *path*."""
    source = Path(path)
    with source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on diagnostic line {line_number}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"Diagnostic line {line_number} must be a JSON object")
            yield _validate_diagnostic_record(raw, line_number=line_number)


def inventory_mukey_raster(
    raster_path: Path | str,
    *,
    max_windows: int | None = None,
) -> dict[str, Any]:
    """Stream a MUKEY raster and return deterministic pixel-frequency metadata.

    ``max_windows`` is only a smoke-test aid. Its output is explicitly marked
    incomplete and must not be used for study frequencies or area estimates.
    """
    if max_windows is not None and max_windows < 1:
        raise ValueError("max_windows must be at least 1")

    import numpy as np
    import rasterio

    path = Path(raster_path).resolve()
    counts: Counter[int] = Counter()
    windows_read = 0
    with rasterio.open(path) as dataset:
        if dataset.count != 1:
            raise ValueError(f"Expected one raster band, found {dataset.count}: {path}")
        nodata = dataset.nodata
        vat_path = path.with_suffix(path.suffix + ".vat.dbf")
        inventory_method = "raster_blocks"
        if max_windows is None and vat_path.is_file():
            from osgeo import ogr

            source = ogr.Open(str(vat_path), 0)
            if source is None:
                raise RuntimeError(f"Unable to open raster attribute table: {vat_path}")
            layer = source.GetLayer(0)
            field_names = {
                layer.GetLayerDefn().GetFieldDefn(index).GetName().lower(): index
                for index in range(layer.GetLayerDefn().GetFieldCount())
            }
            if "mukey" not in field_names or "count" not in field_names:
                raise ValueError(f"Raster attribute table lacks mukey/count fields: {vat_path}")
            for feature in layer:
                mukey = int(feature.GetFieldAsInteger64(field_names["mukey"]))
                pixel_count = int(feature.GetFieldAsDouble(field_names["count"]))
                if mukey > 0 and pixel_count > 0:
                    counts[mukey] += pixel_count
            source = None
            inventory_method = "raster_attribute_table"
        else:
            for _, window in dataset.block_windows(1):
                values = dataset.read(1, window=window, masked=True)
                valid = values.compressed()
                if valid.size:
                    mukeys, pixel_counts = np.unique(valid, return_counts=True)
                    counts.update(
                        {
                            int(mukey): int(pixel_count)
                            for mukey, pixel_count in zip(mukeys.tolist(), pixel_counts.tolist())
                            if int(mukey) > 0
                        }
                    )
                windows_read += 1
                if max_windows is not None and windows_read >= max_windows:
                    break

        transform = dataset.transform
        pixel_area_m2 = abs(transform.a * transform.e - transform.b * transform.d)
        summary = {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "record_type": "mukey_raster_inventory",
            "raster_path": str(path),
            "driver": dataset.driver,
            "crs": str(dataset.crs),
            "width": dataset.width,
            "height": dataset.height,
            "dtype": dataset.dtypes[0],
            "nodata": nodata,
            "block_shape": list(dataset.block_shapes[0]),
            "pixel_area_m2": pixel_area_m2,
            "windows_read": windows_read,
            "inventory_method": inventory_method,
            "raster_attribute_table_path": str(vat_path) if vat_path.is_file() else None,
            "complete": max_windows is None,
            "valid_pixel_count": sum(counts.values()),
            "distinct_mukey_count": len(counts),
            "mukey_pixel_counts": {str(mukey): counts[mukey] for mukey in sorted(counts)},
        }
    return summary


def summarize_diagnostics(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize validated records without assigning any soil replacement."""
    outcomes: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    duplicate_keys: Counter[tuple[str, str, str]] = Counter()

    for index, record in enumerate(records, start=1):
        normalized = _validate_diagnostic_record(record, line_number=index)
        outcomes[normalized["outcome"]] += 1
        by_source[normalized["raster_source"]][normalized["outcome"]] += 1
        duplicate_keys[
            (normalized["cohort_id"], normalized["raster_source"], normalized["mukey"])
        ] += 1
        for reason in normalized["reason_codes"]:
            reasons[reason] += 1

    duplicates = [
        {"cohort_id": cohort, "raster_source": source, "mukey": mukey, "record_count": count}
        for (cohort, source, mukey), count in sorted(duplicate_keys.items())
        if count > 1
    ]
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "record_type": "mukey_build_diagnostic_summary",
        "record_count": sum(outcomes.values()),
        "outcome_counts": {outcome: outcomes[outcome] for outcome in sorted(VALID_OUTCOMES)},
        "reason_code_counts": dict(sorted(reasons.items())),
        "outcome_counts_by_raster_source": {
            source: {outcome: counts[outcome] for outcome in sorted(VALID_OUTCOMES)}
            for source, counts in sorted(by_source.items())
        },
        "duplicate_mukey_records": duplicates,
    }


def summarize_raster_coverage(
    inventory: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Join one complete raster inventory to one diagnostic cohort by MUKEY.

    A diagnostic record is expected once per MUKEY for the selected cohort and
    raster source. Duplicate records are rejected because their build outcomes
    cannot be weighted unambiguously.
    """
    if inventory.get("record_type") != "mukey_raster_inventory":
        raise ValueError("Expected a mukey_raster_inventory document")
    if not inventory.get("complete"):
        raise ValueError("Coverage summaries require a complete raster inventory")
    raw_counts = inventory.get("mukey_pixel_counts")
    if not isinstance(raw_counts, Mapping):
        raise ValueError("Raster inventory has no mukey_pixel_counts mapping")
    pixel_counts = {_normalize_mukey(mukey): int(count) for mukey, count in raw_counts.items()}

    outcomes_by_mukey: dict[str, str] = {}
    cohorts: set[str] = set()
    raster_sources: set[str] = set()
    for index, record in enumerate(records, start=1):
        normalized = _validate_diagnostic_record(record, line_number=index)
        mukey = normalized["mukey"]
        if mukey in outcomes_by_mukey:
            raise ValueError(f"Duplicate diagnostic record for MUKEY {mukey}")
        outcomes_by_mukey[mukey] = normalized["outcome"]
        cohorts.add(normalized["cohort_id"])
        raster_sources.add(normalized["raster_source"])
    if len(cohorts) > 1:
        raise ValueError("Coverage summaries require one diagnostic cohort")
    if len(raster_sources) > 1:
        raise ValueError("Coverage summaries require one diagnostic raster_source")

    outcome_pixels: Counter[str] = Counter()
    outcome_mukeys: Counter[str] = Counter()
    unobserved_pixel_count = 0
    for mukey, pixel_count in pixel_counts.items():
        outcome = outcomes_by_mukey.get(mukey)
        if outcome is None:
            unobserved_pixel_count += pixel_count
            continue
        outcome_mukeys[outcome] += 1
        outcome_pixels[outcome] += pixel_count

    total_pixels = sum(pixel_counts.values())
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "record_type": "mukey_raster_coverage_summary",
        "raster_path": inventory.get("raster_path"),
        "cohort_id": next(iter(cohorts), None),
        "raster_source": next(iter(raster_sources), None),
        "pixel_area_m2": inventory.get("pixel_area_m2"),
        "valid_pixel_count": total_pixels,
        "observed_pixel_count": total_pixels - unobserved_pixel_count,
        "unobserved_pixel_count": unobserved_pixel_count,
        "outcome_mukey_counts": {
            outcome: outcome_mukeys[outcome] for outcome in sorted(VALID_OUTCOMES)
        },
        "outcome_pixel_counts": {
            outcome: outcome_pixels[outcome] for outcome in sorted(VALID_OUTCOMES)
        },
    }


def _write_json(path: Path | str, document: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="stream a MUKEY raster into a frequency inventory")
    inventory.add_argument("--raster", required=True, type=Path)
    inventory.add_argument("--output", required=True, type=Path)
    inventory.add_argument(
        "--max-windows",
        type=int,
        help="smoke-test limit; the resulting inventory is incomplete",
    )

    diagnostics = subparsers.add_parser("diagnostics", help="summarize MUKEY build diagnostic JSONL")
    diagnostics.add_argument("--input", required=True, type=Path)
    diagnostics.add_argument("--output", required=True, type=Path)

    coverage = subparsers.add_parser("coverage", help="join complete raster inventory and diagnostic JSONL")
    coverage.add_argument("--inventory", required=True, type=Path)
    coverage.add_argument("--diagnostics", required=True, type=Path)
    coverage.add_argument("--output", required=True, type=Path)

    template = subparsers.add_parser("template", help="write the version-1 diagnostic record template")
    template.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "inventory":
        _write_json(args.output, inventory_mukey_raster(args.raster, max_windows=args.max_windows))
    elif args.command == "diagnostics":
        _write_json(args.output, summarize_diagnostics(list(read_diagnostic_records(args.input))))
    elif args.command == "coverage":
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        _write_json(
            args.output,
            summarize_raster_coverage(inventory, list(read_diagnostic_records(args.diagnostics))),
        )
    elif args.command == "template":
        _write_json(args.output, diagnostic_record_template())
    else:  # argparse makes this unreachable; retain an explicit boundary for callers.
        raise RuntimeError(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
