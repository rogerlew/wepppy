#!/usr/bin/env python3
"""Inventory gNATSGO MUKEY coverage and summarize SSURGO build diagnostics.

This is a research-only tool for the SSURGO intelligent-fallback study.  Its
inventory and summary commands operate locally.  The explicit ``cohort``
command reads source data through the existing SSURGO client and builds WEPP
soils solely to write diagnostics; it never changes a run's soil assignments.
"""

from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import tempfile
from typing import Any, Iterator, Mapping, Sequence


DIAGNOSTIC_SCHEMA_VERSION = 1
DIAGNOSTIC_RECORD_TYPE = "mukey_build"
VALID_OUTCOMES = frozenset(
    {"valid", "residual_invalid", "worker_failed", "data_access_failed"}
)
SAMPLING_FRAMES = frozenset({"area_weighted", "uniform_mukey"})
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


def _inventory_pixel_counts(inventory: Mapping[str, Any]) -> dict[str, int]:
    """Return normalized positive MUKEY pixel counts from a complete inventory."""
    if inventory.get("record_type") != "mukey_raster_inventory":
        raise ValueError("Expected a mukey_raster_inventory document")
    if not inventory.get("complete"):
        raise ValueError("Cohort sampling requires a complete raster inventory")
    raw_counts = inventory.get("mukey_pixel_counts")
    if not isinstance(raw_counts, Mapping):
        raise ValueError("Raster inventory has no mukey_pixel_counts mapping")
    counts = {_normalize_mukey(mukey): int(count) for mukey, count in raw_counts.items()}
    if not counts or any(count <= 0 for count in counts.values()):
        raise ValueError("Raster inventory must contain positive MUKEY pixel counts")
    return counts


def cohort_targets(
    inventory: Mapping[str, Any], *, sampling_frame: str, draw_count: int, seed: int
) -> dict[str, int]:
    """Select deterministic MUKEY targets, returning MUKEY-to-draw multiplicity."""
    if sampling_frame not in SAMPLING_FRAMES:
        raise ValueError(f"Unsupported sampling frame: {sampling_frame!r}")
    if draw_count < 1:
        raise ValueError("draw_count must be at least 1")
    pixel_counts = _inventory_pixel_counts(inventory)
    mukeys = sorted(pixel_counts, key=int)
    generator = random.Random(seed)

    if sampling_frame == "uniform_mukey":
        if draw_count > len(mukeys):
            raise ValueError("draw_count exceeds the number of distinct MUKEYs")
        return {mukey: 1 for mukey in sorted(generator.sample(mukeys, draw_count), key=int)}

    total_pixels = sum(pixel_counts.values())
    draw_positions = sorted(generator.randrange(total_pixels) for _ in range(draw_count))
    targets: Counter[str] = Counter()
    draw_index = 0
    cumulative = 0
    for mukey in mukeys:
        cumulative += pixel_counts[mukey]
        while draw_index < draw_count and draw_positions[draw_index] < cumulative:
            targets[mukey] += 1
            draw_index += 1
    if draw_index != draw_count:  # Defensive guard against inventory arithmetic drift.
        raise RuntimeError("Unable to resolve every area-weighted draw to a MUKEY")
    return dict(sorted(targets.items(), key=lambda item: int(item[0])))


def _classify_raw_value(field: str, value: object) -> str:
    """Classify source attributes without applying converter defaults."""
    if value is None or value == "":
        return "missing"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "non_numeric"
    if not math.isfinite(numeric):
        return "non_finite"
    if field in {"sandtotal_r", "claytotal_r", "cec7_r"} and numeric <= 0.0:
        return "nonphysical"
    return "present"


def _raw_horizon_profile(layers: Sequence[Mapping[str, Any]]) -> tuple[dict[str, int], dict[str, bool]]:
    """Summarize raw source completeness and feature availability by field."""
    fields = (
        "hzdepb_r",
        "sandtotal_r",
        "claytotal_r",
        "om_r",
        "cec7_r",
        "sandvf_r",
        "ksat_r",
        "dbthirdbar_r",
    )
    completeness: dict[str, int] = {}
    retained: dict[str, bool] = {}
    for field in fields:
        states = Counter(_classify_raw_value(field, layer.get(field)) for layer in layers)
        completeness.update(
            {f"{field}:{state}": count for state, count in sorted(states.items()) if state != "present"}
        )
        retained[field] = bool(states.get("present"))
    return completeness, retained


def _failure_evidence(
    collection: Any, mukey: int, *, emitted_wepp_layer_count: int | None
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect source-row evidence for one MUKEY without changing its build."""
    components = collection.get_components(mukey)
    layers = [layer for component in components for layer in collection.get_layers(component["cokey"])]
    raw_completeness, retained_features = _raw_horizon_profile(layers)
    eligible_components = sum(
        1
        for component in components
        if not str(component.get("compname") or "").lower().startswith(("urban", "water"))
    )
    post_default_valid = 0
    required = ("hzdepb_r", "sandtotal_r", "claytotal_r", "om_r", "cec7_r", "sandvf_r")
    for layer in layers:
        if all(_classify_raw_value(field, layer.get(field)) == "present" for field in required):
            post_default_valid += 1
    restrictive_layer_state: str | None = None
    if components:
        restrictions = [collection.get_reskind(component["cokey"]) for component in components]
        restrictive_layer_state = "present" if any(value not in (None, "N/A") for value in restrictions) else "absent"
    return (
        {
            "component_count": len(components),
            "eligible_component_count": eligible_components,
            "horizon_count": len(layers),
            "post_default_valid_horizon_count": post_default_valid,
            "emitted_wepp_layer_count": emitted_wepp_layer_count,
            "restrictive_layer_state": restrictive_layer_state,
        },
        raw_completeness,
        retained_features,
    )


def _residual_reason_codes(
    evidence: Mapping[str, Any], raw_completeness: Mapping[str, int]
) -> list[str]:
    """Return nonexclusive, source-grounded reasons for a residual invalid build."""
    reasons: list[str] = []
    if evidence["component_count"] == 0:
        reasons.append("no_components")
    if evidence["horizon_count"] == 0:
        reasons.append("no_horizons")
    if evidence["eligible_component_count"] == 0 and evidence["component_count"]:
        reasons.append("no_eligible_component")
    if evidence["post_default_valid_horizon_count"] == 0 and evidence["horizon_count"]:
        reasons.append("no_valid_horizons")
    if evidence["emitted_wepp_layer_count"] == 0 and evidence["component_count"]:
        reasons.append("zero_wepp_layers")
    for field_state, count in raw_completeness.items():
        if count and field_state.endswith(":missing"):
            reasons.append(f"missing_{field_state.removesuffix(':missing')}")
    return sorted(set(reasons or ["residual_invalid_unclassified"]))


def _build_configuration(
    *, source_accessed_at: str, batch_size: int, max_workers: int
) -> dict[str, Any]:
    return {
        "converter": "SurgoSoilCollection.makeWeppSoils",
        "initial_sat": 0.75,
        "ksflag": True,
        "horizon_defaults": {
            "sandtotal_r": 66.8,
            "claytotal_r": 7.0,
            "om_r": 7.0,
            "cec7_r": 11.3,
            "sandvf_r": 10.0,
            "smr": 55.5,
        },
        "batch_size": batch_size,
        "max_workers": max_workers,
        "source_accessed_at": source_accessed_at,
    }


def _base_record(
    *, cohort_id: str, raster_source: str, mukey: str, sampling_frame: str,
    sample_draw_count: int, build_configuration: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "record_type": DIAGNOSTIC_RECORD_TYPE,
        "cohort_id": cohort_id,
        "raster_source": raster_source,
        "mukey": mukey,
        "sampling_frame": sampling_frame,
        "sample_draw_count": sample_draw_count,
        "build_configuration": dict(build_configuration),
        "repair_provenance": [],
    }


def _data_access_failure_record(
    *, cohort_id: str, raster_source: str, mukey: str, sampling_frame: str,
    sample_draw_count: int, build_configuration: Mapping[str, Any], exception: BaseException,
) -> dict[str, Any]:
    record = _base_record(
        cohort_id=cohort_id, raster_source=raster_source, mukey=mukey,
        sampling_frame=sampling_frame, sample_draw_count=sample_draw_count,
        build_configuration=build_configuration,
    )
    record.update(
        {
            "outcome": "data_access_failed",
            "reason_codes": ["ssurgo_data_access_failed"],
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
            "source_access_exception": {
                "type": type(exception).__name__,
                "message": str(exception),
            },
        }
    )
    return record


def _records_for_batch(
    *, mukeys: Sequence[str], target_draws: Mapping[str, int], cohort_id: str,
    raster_source: str, sampling_frame: str, build_configuration: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build and diagnose one source-data batch using the production converter."""
    from wepppy.soils.ssurgo.ssurgo import (
        SurgoCollectionWorkerViewFactory,
        SurgoSoilCollection,
        WeppSoil,
    )

    numeric_mukeys = [int(mukey) for mukey in mukeys]
    # This is a deliberate external-service boundary: the SSURGO client can
    # surface transport, XML, or SQLite errors, all of which mean no soil data
    # was observed rather than a soil-quality failure.
    try:
        collection = SurgoSoilCollection(numeric_mukeys)
        collection.makeWeppSoils(
            initial_sat=0.75,
            horizon_defaults=OrderedDict(build_configuration["horizon_defaults"].items()),
            ksflag=True,
            max_workers=int(build_configuration["max_workers"]),
        )
    except Exception as exc:  # See deliberate source-data boundary above.
        return [
            _data_access_failure_record(
                cohort_id=cohort_id, raster_source=raster_source, mukey=mukey,
                sampling_frame=sampling_frame, sample_draw_count=target_draws[mukey],
                build_configuration=build_configuration, exception=exc,
            )
            for mukey in mukeys
        ]

    factory = SurgoCollectionWorkerViewFactory(conn=collection.conn)
    worker_view = factory.build(set(numeric_mukeys), collection.source_data)
    records: list[dict[str, Any]] = []
    for mukey_text, mukey in zip(mukeys, numeric_mukeys):
        soil = collection.weppSoils.get(mukey)
        invalid_soil = collection.invalidSoils.get(mukey)
        emitted_layers = None if soil is None else soil.num_layers
        evidence, raw_completeness, retained_features = _failure_evidence(
            collection, mukey, emitted_wepp_layer_count=emitted_layers
        )
        record = _base_record(
            cohort_id=cohort_id, raster_source=raster_source, mukey=mukey_text,
            sampling_frame=sampling_frame, sample_draw_count=target_draws[mukey_text],
            build_configuration=build_configuration,
        )
        record["failure_evidence"] = evidence
        record["raw_data_completeness"] = raw_completeness
        record["retained_comparison_features"] = retained_features
        if soil is not None:
            record.update({"outcome": "valid", "reason_codes": []})
        elif invalid_soil is not None:
            record.update(
                {
                    "outcome": "residual_invalid",
                    "reason_codes": _residual_reason_codes(evidence, raw_completeness),
                }
            )
        else:
            try:
                WeppSoil(
                    worker_view, mukey, initial_sat=0.75,
                    horizon_defaults=OrderedDict(build_configuration["horizon_defaults"].items()),
                    ksflag=True,
                )
            except Exception as exc:  # Converter replay preserves worker error evidence.
                reasons = ["worker_failed"]
                if "texture fractions" in str(exc).lower():
                    reasons.append("nonphysical_texture_balance")
                record["worker_exception"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            else:
                reasons = ["worker_failed", "worker_replay_inconsistent"]
            record.update({"outcome": "worker_failed", "reason_codes": reasons})
        records.append(record)
    return records


def _write_jsonl_atomic(path: Path | str, records: Sequence[Mapping[str, Any]]) -> None:
    """Write validated, MUKEY-sorted records atomically for safe batch resume."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    normalized = [
        _validate_diagnostic_record(record, line_number=index)
        for index, record in enumerate(records, start=1)
    ]
    normalized.sort(key=lambda record: int(record["mukey"]))
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, delete=False
    ) as stream:
        temporary_path = Path(stream.name)
        for record in normalized:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    os.replace(temporary_path, destination)


def summarize_cohort_records(
    records: Sequence[Mapping[str, Any]], *, cohort_id: str, sampling_frame: str,
    draw_count: int, seed: int, inventory: Mapping[str, Any], batch_size: int,
    max_workers: int,
) -> dict[str, Any]:
    """Summarize a sampled cohort by draw multiplicity, not just unique MUKEYs."""
    if sampling_frame not in SAMPLING_FRAMES:
        raise ValueError(f"Unsupported sampling frame: {sampling_frame!r}")
    outcomes: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for index, record in enumerate(records, start=1):
        normalized = _validate_diagnostic_record(record, line_number=index)
        if normalized["cohort_id"] != cohort_id:
            raise ValueError("Cohort summary received a record from another cohort")
        multiplicity = normalized.get("sample_draw_count")
        if not isinstance(multiplicity, int) or multiplicity < 1:
            raise ValueError("Cohort record has no positive sample_draw_count")
        outcomes[normalized["outcome"]] += multiplicity
        for reason in normalized["reason_codes"]:
            reasons[reason] += multiplicity
    observed_draw_count = sum(outcomes.values())
    if observed_draw_count != draw_count:
        raise ValueError(
            f"Cohort draw count mismatch: expected {draw_count}, observed {observed_draw_count}"
        )
    soil_unbuildable = outcomes["residual_invalid"] + outcomes["worker_failed"]
    soil_observed = draw_count - outcomes["data_access_failed"]
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "record_type": "mukey_build_cohort_summary",
        "cohort_id": cohort_id,
        "sampling_frame": sampling_frame,
        "draw_count": draw_count,
        "unique_mukey_count": len(records),
        "seed": seed,
        "batch_size": batch_size,
        "max_workers": max_workers,
        "raster_path": inventory.get("raster_path"),
        "inventory_valid_pixel_count": inventory.get("valid_pixel_count"),
        "outcome_draw_counts": {outcome: outcomes[outcome] for outcome in sorted(VALID_OUTCOMES)},
        "outcome_draw_rates": {
            outcome: outcomes[outcome] / draw_count for outcome in sorted(VALID_OUTCOMES)
        },
        "soil_unbuildable_draw_count": soil_unbuildable,
        "soil_unbuildable_rate": soil_unbuildable / soil_observed if soil_observed else None,
        "soil_observed_draw_count": soil_observed,
        "data_access_draw_count": outcomes["data_access_failed"],
        "reason_draw_counts": dict(sorted(reasons.items())),
        "complete": True,
    }


def run_cohort(
    *, inventory: Mapping[str, Any], output: Path | str, summary_output: Path | str,
    cohort_id: str, sampling_frame: str, draw_count: int, seed: int, batch_size: int,
    max_workers: int,
) -> dict[str, Any]:
    """Run or resume a deterministic research cohort, persisting every batch."""
    if batch_size < 1 or max_workers < 1:
        raise ValueError("batch_size and max_workers must be at least 1")
    targets = cohort_targets(
        inventory, sampling_frame=sampling_frame, draw_count=draw_count, seed=seed
    )
    output_path = Path(output)
    existing_by_mukey: dict[str, dict[str, Any]] = {}
    if output_path.is_file():
        for record in read_diagnostic_records(output_path):
            mukey = record["mukey"]
            if record["cohort_id"] != cohort_id or mukey not in targets:
                raise ValueError("Existing cohort output does not match requested cohort targets")
            if record.get("sampling_frame") != sampling_frame:
                raise ValueError("Existing cohort output has a different sampling frame")
            if record.get("sample_draw_count") != targets[mukey]:
                raise ValueError("Existing cohort output has different draw multiplicities")
            if mukey in existing_by_mukey:
                raise ValueError(f"Existing cohort output has duplicate MUKEY {mukey}")
            existing_by_mukey[mukey] = record

    source_accessed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    configuration = _build_configuration(
        source_accessed_at=source_accessed_at, batch_size=batch_size, max_workers=max_workers
    )
    pending = [
        mukey for mukey in targets
        if mukey not in existing_by_mukey or existing_by_mukey[mukey]["outcome"] == "data_access_failed"
    ]
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        batch_records = _records_for_batch(
            mukeys=batch, target_draws=targets, cohort_id=cohort_id,
            raster_source=str(inventory["raster_path"]), sampling_frame=sampling_frame,
            build_configuration=configuration,
        )
        for record in batch_records:
            existing_by_mukey[record["mukey"]] = record
        _write_jsonl_atomic(output_path, list(existing_by_mukey.values()))
        if any(record["outcome"] == "data_access_failed" for record in batch_records):
            raise RuntimeError(
                "SSURGO source-data access failed; persisted the batch for evidence. "
                "Rerun the same command to retry only those records."
            )

    records = [existing_by_mukey[mukey] for mukey in sorted(targets, key=int)]
    summary = summarize_cohort_records(
        records, cohort_id=cohort_id, sampling_frame=sampling_frame, draw_count=draw_count,
        seed=seed, inventory=inventory, batch_size=batch_size, max_workers=max_workers,
    )
    summary["source_completed_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary["records_path"] = str(output_path.resolve())
    _write_json(summary_output, summary)
    return summary


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

    cohort = subparsers.add_parser(
        "cohort",
        help="run or resume a research-only SSURGO conversion cohort",
    )
    cohort.add_argument("--inventory", required=True, type=Path)
    cohort.add_argument("--output", required=True, type=Path)
    cohort.add_argument("--summary-output", required=True, type=Path)
    cohort.add_argument("--cohort-id", required=True)
    cohort.add_argument("--sampling-frame", required=True, choices=sorted(SAMPLING_FRAMES))
    cohort.add_argument("--draw-count", required=True, type=int)
    cohort.add_argument("--seed", required=True, type=int)
    cohort.add_argument("--batch-size", type=int, default=128)
    cohort.add_argument("--max-workers", type=int, default=8)

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
    elif args.command == "cohort":
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        run_cohort(
            inventory=inventory,
            output=args.output,
            summary_output=args.summary_output,
            cohort_id=args.cohort_id,
            sampling_frame=args.sampling_frame,
            draw_count=args.draw_count,
            seed=args.seed,
            batch_size=args.batch_size,
            max_workers=args.max_workers,
        )
    elif args.command == "template":
        _write_json(args.output, diagnostic_record_template())
    else:  # argparse makes this unreachable; retain an explicit boundary for callers.
        raise RuntimeError(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
