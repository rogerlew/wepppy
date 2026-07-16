"""Failure-atomic native interchange for AgFields sub-field WEPP outputs."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import pyarrow as pa
import pyarrow.parquet as pq

from ._rust_interchange import (
    call_wepppyo3_interchange,
    require_wepppyo3_interchange,
    version_args,
)
from .hill_ebe_interchange import SCHEMA as EBE_SCHEMA
from .hill_element_interchange import SCHEMA as ELEMENT_SCHEMA
from .hill_loss_interchange import SCHEMA as LOSS_SCHEMA
from .hill_pass_interchange import PASS_FAMILY_LEGACY_ASCII, SCHEMA as PASS_SCHEMA
from .hill_soil_interchange import SCHEMA as SOIL_SCHEMA
from .hill_wat_interchange import SCHEMA as WAT_SCHEMA
from .versioning import INTERCHANGE_VERSION, MANIFEST_FILENAME


LOGGER = logging.getLogger(__name__)

DATASET_KIND: Final = "ag_fields_hillslope"
AG_FIELDS_SCHEMA_VERSION: Final = 1

_FAMILY_CONTRACTS: Final = {
    "pass": (
        re.compile(r"^H([1-9][0-9]*)\.pass\.dat$"),
        "H*.pass.dat",
        "H.pass.parquet",
        "ag_fields_hillslope_pass_files_to_parquet",
        PASS_SCHEMA,
    ),
    "ebe": (
        re.compile(r"^H([1-9][0-9]*)\.ebe\.dat$"),
        "H*.ebe.dat",
        "H.ebe.parquet",
        "ag_fields_hillslope_ebe_files_to_parquet",
        EBE_SCHEMA,
    ),
    "element": (
        re.compile(r"^H([1-9][0-9]*)\.element\.dat$"),
        "H*.element.dat",
        "H.element.parquet",
        "ag_fields_hillslope_element_files_to_parquet",
        ELEMENT_SCHEMA,
    ),
    "loss": (
        re.compile(r"^H([1-9][0-9]*)\.loss\.dat$"),
        "H*.loss.dat",
        "H.loss.parquet",
        "ag_fields_hillslope_loss_files_to_parquet",
        LOSS_SCHEMA,
    ),
    "soil": (
        re.compile(r"^H([1-9][0-9]*)\.soil\.dat$"),
        "H*.soil.dat",
        "H.soil.parquet",
        "ag_fields_hillslope_soil_files_to_parquet",
        SOIL_SCHEMA,
    ),
    "wat": (
        re.compile(r"^H([1-9][0-9]*)\.wat\.dat$"),
        "H*.wat.dat",
        "H.wat.parquet",
        "ag_fields_hillslope_wat_files_to_parquet",
        WAT_SCHEMA,
    ),
}

_REQUIRED_NATIVE_SYMBOLS: Final = tuple(
    contract[3] for contract in _FAMILY_CONTRACTS.values()
)

__all__ = [
    "AG_FIELDS_SCHEMA_VERSION",
    "DATASET_KIND",
    "run_wepp_ag_fields_interchange",
]


def _identity_mapping(subfields_parquet_path: Path) -> dict[int, int]:
    if not subfields_parquet_path.is_file():
        raise FileNotFoundError(subfields_parquet_path)

    schema = pq.read_schema(subfields_parquet_path)
    required = ("field_id", "sub_field_id")
    missing = [name for name in required if name not in schema.names]
    if missing:
        raise ValueError(
            f"AgFields sub-field mapping is missing required column(s): {', '.join(missing)}"
        )
    for name in required:
        if not pa.types.is_integer(schema.field(name).type):
            raise TypeError(f"AgFields mapping column {name!r} must be an integer")

    table = pq.read_table(subfields_parquet_path, columns=list(required))
    field_ids = table.column("field_id")
    sub_field_ids = table.column("sub_field_id")
    if field_ids.null_count or sub_field_ids.null_count:
        raise ValueError("AgFields mapping identity columns must not contain nulls")

    mapping: dict[int, int] = {}
    i32_max = 2**31 - 1
    for field_value, sub_field_value in zip(
        field_ids.to_pylist(), sub_field_ids.to_pylist(), strict=True
    ):
        field_id = int(field_value)
        sub_field_id = int(sub_field_value)
        if not 0 < field_id <= i32_max:
            raise ValueError(f"field_id must be in the positive int32 range: {field_id}")
        if not 0 < sub_field_id <= i32_max:
            raise ValueError(
                f"sub_field_id must be in the positive int32 range: {sub_field_id}"
            )
        if sub_field_id in mapping:
            raise ValueError(f"Duplicate sub_field_id in AgFields mapping: {sub_field_id}")
        mapping[sub_field_id] = field_id

    if not mapping:
        raise ValueError("AgFields sub-field mapping must contain at least one row")
    return mapping


def _family_sources(
    output_dir: Path,
    mapping: dict[int, int],
) -> dict[str, list[tuple[str, int, int]]]:
    expected_ids = set(mapping)
    all_sources: dict[str, list[tuple[str, int, int]]] = {}
    family_ids: dict[str, set[int]] = {}

    for family, (pattern, glob_pattern, _target, _symbol, _schema) in _FAMILY_CONTRACTS.items():
        paths_by_id: dict[int, Path] = {}
        malformed: list[str] = []
        for path in output_dir.glob(glob_pattern):
            match = pattern.fullmatch(path.name)
            if match is None:
                malformed.append(path.name)
                continue
            sub_field_id = int(match.group(1))
            if sub_field_id in paths_by_id:
                raise ValueError(
                    f"Duplicate {family} source for sub_field_id={sub_field_id}"
                )
            paths_by_id[sub_field_id] = path
        if malformed:
            raise ValueError(
                f"Malformed AgFields {family} source name(s): {', '.join(sorted(malformed))}"
            )

        actual_ids = set(paths_by_id)
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        if missing or extra:
            raise FileNotFoundError(
                f"AgFields {family} source ids do not match fields.parquet; "
                f"missing={missing[:10]} extra={extra[:10]}"
            )
        family_ids[family] = actual_ids
        all_sources[family] = [
            (str(paths_by_id[sub_field_id]), mapping[sub_field_id], sub_field_id)
            for sub_field_id in sorted(expected_ids)
        ]

    first_family = next(iter(family_ids))
    first_ids = family_ids[first_family]
    mismatched = [family for family, ids in family_ids.items() if ids != first_ids]
    if mismatched:
        raise ValueError(
            "AgFields raw report families do not contain identical sub_field_id sets: "
            + ", ".join(mismatched)
        )
    return all_sources


def _expected_schema(ordinary_schema: pa.Schema) -> pa.Schema:
    metadata = dict(ordinary_schema.metadata or {})
    metadata[b"dataset_kind"] = DATASET_KIND.encode()
    metadata[b"ag_fields_schema_version"] = str(AG_FIELDS_SCHEMA_VERSION).encode()
    return pa.schema(
        [
            pa.field("field_id", pa.int32(), nullable=False),
            pa.field("sub_field_id", pa.int32(), nullable=False),
            *list(ordinary_schema)[1:],
        ],
        metadata=metadata,
    )


def _expected_zero_row_ids(
    family: str,
    sources: list[tuple[str, int, int]],
) -> set[int]:
    """Classify evidence-backed header-only EBE reports without parsing values."""
    if family != "ebe":
        return set()

    zero_row_ids: set[int] = set()
    for source_path, _field_id, sub_field_id in sources:
        line_count = 0
        has_scientific_row = False
        with Path(source_path).open(encoding="ascii") as stream:
            for line_count, line in enumerate(stream, start=1):
                if line_count > 3 and line.strip():
                    has_scientific_row = True
                    break
        if line_count < 3:
            raise ValueError(
                f"AgFields EBE source has an incomplete header: {source_path}"
            )
        if not has_scientific_row:
            zero_row_ids.add(sub_field_id)
    return zero_row_ids


def _validate_output(
    path: Path,
    ordinary_schema: pa.Schema,
    expected_mapping: dict[int, int],
    expected_zero_row_ids: set[int],
) -> dict[str, object]:
    parquet_file = pq.ParquetFile(path)
    schema = parquet_file.schema_arrow
    expected_schema = _expected_schema(ordinary_schema)
    if schema.names != expected_schema.names:
        raise ValueError(
            f"Unexpected AgFields schema fields for {path.name}: {schema.names}"
        )
    if list(schema) != list(expected_schema):
        raise TypeError(f"Unexpected AgFields schema fields for {path.name}")
    if "wepp_id" in schema.names or "topaz_id" in schema.names:
        raise ValueError(f"AgFields output {path.name} contains a false hillslope identity")
    if schema.field("field_id").nullable or schema.field("sub_field_id").nullable:
        raise ValueError(f"AgFields output {path.name} identity fields must be non-nullable")

    metadata = schema.metadata or {}
    if metadata != expected_schema.metadata:
        raise ValueError(f"AgFields output {path.name} has unexpected schema metadata")

    field_index = schema.get_field_index("field_id")
    sub_field_index = schema.get_field_index("sub_field_id")
    ordered_pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for row_group_index in range(parquet_file.metadata.num_row_groups):
        row_group = parquet_file.metadata.row_group(row_group_index)
        if row_group.num_rows == 0:
            raise ValueError(f"AgFields output {path.name} contains an empty row group")
        field_stats = row_group.column(field_index).statistics
        sub_field_stats = row_group.column(sub_field_index).statistics
        if (
            field_stats is None
            or sub_field_stats is None
            or not field_stats.has_min_max
            or not sub_field_stats.has_min_max
        ):
            raise ValueError(f"AgFields output {path.name} lacks identity statistics")
        if field_stats.null_count or sub_field_stats.null_count:
            raise ValueError(f"AgFields output {path.name} contains null identity values")
        if field_stats.min != field_stats.max or sub_field_stats.min != sub_field_stats.max:
            raise ValueError(
                f"AgFields output {path.name} mixes identities within one source row group"
            )
        pair = (int(field_stats.min), int(sub_field_stats.min))
        expected_field_id = expected_mapping.get(pair[1])
        if expected_field_id != pair[0]:
            raise ValueError(
                f"AgFields output {path.name} contains an unexpected identity pair {pair}"
            )
        if pair in seen:
            raise ValueError(f"AgFields output {path.name} repeats identity pair {pair}")
        seen.add(pair)
        ordered_pairs.append(pair)

    expected_pairs = {
        (field_id, sub_field_id)
        for sub_field_id, field_id in expected_mapping.items()
    }
    extra = sorted(seen - expected_pairs)
    if extra:
        raise ValueError(
            f"AgFields output {path.name} contains unexpected identity pairs: {extra[:10]}"
        )
    missing = expected_pairs - seen
    expected_missing = {
        (expected_mapping[sub_field_id], sub_field_id)
        for sub_field_id in expected_zero_row_ids
    }
    if missing != expected_missing:
        raise ValueError(
            f"AgFields output {path.name} has unexplained missing identity pairs; "
            f"missing={sorted(missing)[:10]} "
            f"expected_zero_rows={sorted(expected_missing)[:10]}"
        )
    if ordered_pairs != sorted(ordered_pairs, key=lambda pair: pair[1]):
        raise ValueError(
            f"AgFields output {path.name} row groups are not in numeric sub_field_id order"
        )
    if parquet_file.metadata.num_row_groups != len(ordered_pairs):
        raise ValueError(
            f"AgFields output {path.name} must contain one row group per "
            "row-bearing source"
        )
    return {
        "rows": parquet_file.metadata.num_rows,
        "row_groups": parquet_file.metadata.num_row_groups,
        "size_bytes": path.stat().st_size,
        "identity_count": len(seen),
        "source_count": len(expected_mapping),
        "zero_row_source_count": len(expected_zero_row_ids),
        "zero_row_sub_field_ids": sorted(expected_zero_row_ids),
    }


def _write_manifest(
    stage_dir: Path,
    summaries: dict[str, dict[str, object]],
    *,
    source_mapping_sha256: str,
) -> Path:
    payload = {
        **INTERCHANGE_VERSION.to_dict(),
        "dataset_kind": DATASET_KIND,
        "ag_fields_schema_version": AG_FIELDS_SCHEMA_VERSION,
        "source_mapping_sha256": source_mapping_sha256,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "files": summaries,
    }
    path = stage_dir / MANIFEST_FILENAME
    temporary = stage_dir / f".{MANIFEST_FILENAME}.tmp"
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)
    return path


def _publish_stage(stage_dir: Path, final_dir: Path) -> None:
    if final_dir.exists() and not final_dir.is_dir():
        raise NotADirectoryError(final_dir)
    if not final_dir.exists():
        os.replace(stage_dir, final_dir)
        if not _manifest_is_current(final_dir):
            shutil.rmtree(final_dir)
            raise RuntimeError(f"Published AgFields bundle failed validation: {final_dir}")
        return

    backup_dir = final_dir.parent / f".{final_dir.name}.backup-{uuid.uuid4().hex}"
    os.replace(final_dir, backup_dir)
    try:
        os.replace(stage_dir, final_dir)
    except OSError as publish_error:
        try:
            os.replace(backup_dir, final_dir)
        except OSError as restore_error:
            raise RuntimeError(
                f"Failed to publish {stage_dir} and restore prior bundle {backup_dir}"
            ) from restore_error
        raise publish_error
    if not _manifest_is_current(final_dir):
        try:
            shutil.rmtree(final_dir)
            os.replace(backup_dir, final_dir)
        except OSError as restore_error:
            raise RuntimeError(
                f"Published bundle validation failed and prior bundle could not be restored: {backup_dir}"
            ) from restore_error
        raise RuntimeError(f"Published AgFields bundle failed validation: {final_dir}")
    shutil.rmtree(backup_dir)


def _remove_stage(stage_dir: Path) -> None:
    """Remove an NFS-backed failed stage, retrying transient ENOTEMPTY races."""
    for attempt in range(5):
        try:
            shutil.rmtree(stage_dir)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            if exc.errno != errno.ENOTEMPTY or attempt == 4:
                raise
            time.sleep(0.1 * (attempt + 1))


def _manifest_is_current(
    interchange_dir: Path,
    *,
    subfields_parquet_path: Path | None = None,
    deep: bool = False,
) -> bool:
    manifest_path = interchange_dir / MANIFEST_FILENAME
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    if not isinstance(payload, dict):
        return False
    if payload.get("dataset_kind") != DATASET_KIND:
        return False
    if payload.get("ag_fields_schema_version") != AG_FIELDS_SCHEMA_VERSION:
        return False
    if payload.get("major") != INTERCHANGE_VERSION.major:
        return False
    source_mapping_sha256 = payload.get("source_mapping_sha256")
    if not isinstance(source_mapping_sha256, str) or len(source_mapping_sha256) != 64:
        return False
    mapping_row_count: int | None = None
    if subfields_parquet_path is not None:
        try:
            if (
                not subfields_parquet_path.is_file()
                or _sha256(subfields_parquet_path) != source_mapping_sha256
            ):
                return False
            mapping_row_count = pq.ParquetFile(
                subfields_parquet_path
            ).metadata.num_rows
        except (OSError, pa.ArrowException):
            return False
    files = payload.get("files")
    if not isinstance(files, dict) or set(files) != set(_FAMILY_CONTRACTS):
        return False
    for family, contract in _FAMILY_CONTRACTS.items():
        summary = files.get(family)
        if not isinstance(summary, dict):
            return False
        integer_fields = (
            "rows",
            "row_groups",
            "size_bytes",
            "identity_count",
            "source_count",
            "zero_row_source_count",
        )
        if any(
            type(summary.get(field)) is not int or summary[field] < 0
            for field in integer_fields
        ):
            return False
        source_count = summary["source_count"]
        identity_count = summary["identity_count"]
        zero_row_source_count = summary["zero_row_source_count"]
        zero_row_ids = summary.get("zero_row_sub_field_ids")
        if (
            source_count < 1
            or identity_count + zero_row_source_count != source_count
            or summary["row_groups"] != identity_count
            or not isinstance(zero_row_ids, list)
            or (family != "ebe" and zero_row_source_count != 0)
            or len(zero_row_ids) != zero_row_source_count
            or any(type(value) is not int or value < 1 for value in zero_row_ids)
            or len(set(zero_row_ids)) != len(zero_row_ids)
            or (mapping_row_count is not None and source_count != mapping_row_count)
        ):
            return False

        target_path = interchange_dir / contract[2]
        try:
            if (
                not target_path.is_file()
                or target_path.stat().st_size != summary["size_bytes"]
            ):
                return False
        except OSError:
            return False
        if not deep:
            continue
        try:
            parquet_file = pq.ParquetFile(target_path)
        except (OSError, pa.ArrowException):
            return False
        schema = parquet_file.schema_arrow
        expected_schema = _expected_schema(contract[4])
        metadata = schema.metadata or {}
        if (
            schema.names != expected_schema.names
            or list(schema) != list(expected_schema)
            or metadata != expected_schema.metadata
            or parquet_file.metadata.num_rows != summary["rows"]
            or parquet_file.metadata.num_row_groups != summary["row_groups"]
        ):
            return False
    return True


def _is_wepp_ag_fields_interchange_complete(
    wepp_output_dir: Path | str,
    subfields_parquet_path: Path | str | None = None,
    *,
    deep: bool = False,
) -> bool:
    """Return whether a last-written AgFields manifest describes six present outputs."""
    mapping_path = (
        Path(subfields_parquet_path) if subfields_parquet_path is not None else None
    )
    return _manifest_is_current(
        Path(wepp_output_dir) / "interchange",
        subfields_parquet_path=mapping_path,
        deep=deep,
    )


def _existing_cli_calendar_path(output_dir: Path) -> Path | None:
    """Return an already-materialized calendar without mutating climate assets."""
    for candidate in (output_dir, *output_dir.parents):
        path = candidate / "climate" / "wepp_cli.parquet"
        if path.is_file():
            pq.ParquetFile(path)
            return path
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_wepp_ag_fields_interchange(
    wepp_output_dir: Path | str,
    subfields_parquet_path: Path | str,
    *,
    start_year: int | None = None,
) -> Path:
    """Convert all six AgFields raw families and publish one complete bundle."""
    output_dir = Path(wepp_output_dir)
    if not output_dir.is_dir():
        raise FileNotFoundError(output_dir)
    mapping_path = Path(subfields_parquet_path)
    source_mapping_sha256 = _sha256(mapping_path)
    mapping = _identity_mapping(mapping_path)
    if _sha256(mapping_path) != source_mapping_sha256:
        raise RuntimeError("AgFields sub-field mapping changed while it was being read")
    sources = _family_sources(output_dir, mapping)

    if isinstance(start_year, bool):
        raise TypeError("start_year must be an integer year or None")
    normalized_start_year = int(start_year) if start_year is not None else None

    require_wepppyo3_interchange(
        "AgFields hillslope aggregate preflight", *_REQUIRED_NATIVE_SYMBOLS
    )
    final_dir = output_dir / "interchange"
    stage_dir = output_dir / f".interchange.stage-{uuid.uuid4().hex}"
    lock_fd = os.open(output_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        stage_dir.mkdir(parents=False, exist_ok=False)

        major, minor = version_args()
        cli_calendar_path = _existing_cli_calendar_path(output_dir)
        cli_calendar = str(cli_calendar_path) if cli_calendar_path else None
        summaries: dict[str, dict[str, object]] = {}
        try:
            for family, (_pattern, _glob, target_name, symbol, ordinary_schema) in _FAMILY_CONTRACTS.items():
                target_path = stage_dir / target_name
                kwargs: dict[str, object] = {"compression": "snappy"}
                if family in {"pass", "ebe", "soil", "wat"}:
                    kwargs["cli_calendar_path"] = cli_calendar
                if family == "pass":
                    kwargs["pass_family"] = PASS_FAMILY_LEGACY_ASCII
                if family in {"ebe", "element", "soil"}:
                    kwargs["start_year"] = normalized_start_year
                call_wepppyo3_interchange(
                    f"AgFields hillslope {family.upper()}",
                    symbol,
                    sources[family],
                    str(target_path),
                    major,
                    minor,
                    **kwargs,
                )
                summaries[family] = _validate_output(
                    target_path,
                    ordinary_schema,
                    mapping,
                    _expected_zero_row_ids(family, sources[family]),
                )

            if _sha256(mapping_path) != source_mapping_sha256:
                raise RuntimeError(
                    "AgFields sub-field mapping changed during interchange conversion"
                )
            _write_manifest(
                stage_dir,
                summaries,
                source_mapping_sha256=source_mapping_sha256,
            )
            _publish_stage(stage_dir, final_dir)
        finally:
            if stage_dir.exists():
                try:
                    _remove_stage(stage_dir)
                except OSError:
                    LOGGER.warning(
                        "Failed to remove AgFields interchange stage %s",
                        stage_dir,
                        exc_info=True,
                    )
    finally:
        os.close(lock_fd)

    return final_dir
