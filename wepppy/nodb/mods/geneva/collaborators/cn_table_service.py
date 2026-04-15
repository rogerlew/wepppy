from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from wepppy.nodb.mods.geneva.errors import GenevaValidationError

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


GENEVA_CN_TABLE_SCHEMA_VERSION = 1
CN_TABLE_RELPATH = "data/cn_table.csv"
CN_TABLE_CONTRACT_PATH = "geneva/data/cn_table.csv"
CN_TABLE_AUDIT_RELPATH = "data/cn_table_audit.jsonl"

_CN_TABLE_REQUIRED_COLUMNS: tuple[str, ...] = (
    "nlcd_class",
    "nlcd_label",
    "hsg",
    "burn_severity",
    "hydrophobic",
    "cn_arc_ii",
    "antecedent_condition_source",
    "source",
    "notes",
)

_CN_TABLE_KEY_COLUMNS: tuple[str, ...] = (
    "nlcd_class",
    "hsg",
    "burn_severity",
    "hydrophobic",
)

_ALLOWED_ANTECEDENT_SOURCES = {
    "arc_ii_seed",
    "user_override",
}


class GenevaCnTableService:
    """Manage run-scoped Geneva CN-table lifecycle and optimistic edits."""

    def __init__(self, *, seed_path: Path | None = None) -> None:
        self._seed_path = seed_path or (
            Path(__file__).resolve().parents[1] / "data" / "geneva_cn_table_us_v1_seed.csv"
        )

    def ensure_initialized(self, geneva: "Geneva", *, reason: str = "init") -> dict[str, Any]:
        table_path = self._table_path(geneva)
        if not table_path.exists():
            before = self._snapshot_for_path(table_path)
            rows = self._load_seed_rows()
            self._atomic_write_rows(table_path, _CN_TABLE_REQUIRED_COLUMNS, rows)
            after = self._snapshot_for_path(table_path)
            self._emit_audit(
                geneva,
                event="cn_table.seed",
                before=before,
                after=after,
                details={
                    "reason": reason,
                    "seed_path": str(self._seed_path),
                    "seed_sha256": self._seed_sha256(),
                    "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
                    "rows": len(rows),
                },
            )
            return self._with_aliases(after)

        fieldnames, rows = self._read_rows(table_path)
        normalized_rows, changed, migration_details = self._normalize_existing_rows(
            fieldnames,
            rows,
        )

        if changed:
            before = self._snapshot_for_path(table_path)
            self._atomic_write_rows(table_path, _CN_TABLE_REQUIRED_COLUMNS, normalized_rows)
            after = self._snapshot_for_path(table_path)
            self._emit_audit(
                geneva,
                event="cn_table.schema_migrate",
                before=before,
                after=after,
                details={
                    "reason": reason,
                    "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
                    **migration_details,
                },
            )
            return self._with_aliases(after)

        return self._with_aliases(self._snapshot_for_path(table_path))

    def reset(self, geneva: "Geneva", *, reason: str = "manual") -> dict[str, Any]:
        table_path = self._table_path(geneva)
        before = self._snapshot_for_path(table_path)
        rows = self._load_seed_rows()
        self._atomic_write_rows(table_path, _CN_TABLE_REQUIRED_COLUMNS, rows)
        after = self._snapshot_for_path(table_path)
        self._emit_audit(
            geneva,
            event="cn_table.reset",
            before=before,
            after=after,
            details={
                "reason": reason,
                "seed_path": str(self._seed_path),
                "seed_sha256": self._seed_sha256(),
                "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
                "rows": len(rows),
            },
        )
        return self._with_aliases(after)

    def meta(self, geneva: "Geneva") -> dict[str, Any]:
        self.ensure_initialized(geneva, reason="meta")
        return self._with_aliases(self._snapshot_for_path(self._table_path(geneva)))

    def snapshot(self, geneva: "Geneva") -> dict[str, Any]:
        self.ensure_initialized(geneva, reason="snapshot")
        table_path = self._table_path(geneva)
        fieldnames, rows = self._read_rows(table_path)
        normalized_rows, _, _ = self._normalize_existing_rows(fieldnames, rows)
        meta = self._with_aliases(self._snapshot_for_path(table_path))

        csv_text = table_path.read_text(encoding="utf-8")
        return {
            "path": CN_TABLE_CONTRACT_PATH,
            "meta": {
                "sha256": meta.get("sha256"),
                "rows": meta.get("rows"),
                "columns": meta.get("columns"),
                "schema_version": meta.get("schema_version"),
            },
            "rows": normalized_rows,
            "csv_text": csv_text,
            "lookup_sha256": meta.get("sha256"),
            "rows_count": meta.get("rows"),
            "columns_count": meta.get("columns"),
            "schema_version": meta.get("schema_version"),
        }

    def modify(
        self,
        geneva: "Geneva",
        rows: list[Any],
        *,
        if_match_sha256: str | None,
    ) -> dict[str, Any]:
        if if_match_sha256 is None or not str(if_match_sha256).strip():
            raise GenevaValidationError(
                "if_match_sha256 is required",
                code="PRECONDITION_REQUIRED",
                details="if_match_sha256 is required",
                status_code=428,
            )

        self.ensure_initialized(geneva, reason="modify")
        table_path = self._table_path(geneva)
        current = self._snapshot_for_path(table_path)
        current_sha = current.get("sha256")
        expected_sha = str(if_match_sha256).strip()

        if not isinstance(current_sha, str) or not current_sha:
            raise GenevaValidationError(
                "Unable to verify current Geneva CN-table version. Reload and retry.",
                code="LOOKUP_VERSION_UNAVAILABLE",
                details={"path": CN_TABLE_CONTRACT_PATH},
                status_code=409,
            )

        if current_sha != expected_sha:
            raise GenevaValidationError(
                "Stale Geneva CN table. Reload current data before saving.",
                code="STALE_LOOKUP",
                details={
                    "expected_sha256": expected_sha,
                    "current_sha256": current_sha,
                    "path": CN_TABLE_CONTRACT_PATH,
                },
                status_code=409,
            )

        fieldnames, existing_rows = self._read_rows(table_path)
        normalized_existing_rows, _, _ = self._normalize_existing_rows(fieldnames, existing_rows)
        normalized_rows = self._normalize_payload_rows(rows, normalized_existing_rows)

        before = self._snapshot_for_path(table_path)
        self._atomic_write_rows(table_path, _CN_TABLE_REQUIRED_COLUMNS, normalized_rows)
        after = self._snapshot_for_path(table_path)
        self._emit_audit(
            geneva,
            event="cn_table.write",
            before=before,
            after=after,
            details={
                "incoming_rows": len(normalized_rows),
                "existing_rows": len(normalized_existing_rows),
                "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
            },
        )

        return {
            "path": CN_TABLE_CONTRACT_PATH,
            "before": self._with_aliases(before),
            "after": self._with_aliases(after),
            "sha256": after.get("sha256"),
            "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
        }

    def _table_path(self, geneva: "Geneva") -> Path:
        return geneva.artifact_io.resolve_path(geneva.wd, CN_TABLE_RELPATH)

    def _audit_path(self, geneva: "Geneva") -> Path:
        return geneva.artifact_io.resolve_path(geneva.wd, CN_TABLE_AUDIT_RELPATH)

    def _seed_sha256(self) -> str:
        digest = hashlib.sha256()
        with open(self._seed_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_seed_rows(self) -> list[dict[str, str]]:
        fieldnames, rows = self._read_rows(self._seed_path)
        normalized_rows, _changed, _details = self._normalize_existing_rows(fieldnames, rows)
        return normalized_rows

    def _read_rows(self, path: Path) -> tuple[list[str], list[dict[str, str]]]:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = [str(name).strip() for name in (reader.fieldnames or []) if str(name).strip()]
            rows = [{k: self._stringify(v) for k, v in row.items()} for row in reader]
        if not fieldnames:
            raise GenevaValidationError(
                "Geneva CN table is missing a header row.",
                code="invalid_cn_table_schema",
                details={"path": CN_TABLE_CONTRACT_PATH},
                status_code=409,
            )
        return fieldnames, rows

    def _normalize_existing_rows(
        self,
        fieldnames: Sequence[str],
        rows: Sequence[Mapping[str, Any]],
    ) -> tuple[list[dict[str, str]], bool, dict[str, Any]]:
        expected_columns = list(_CN_TABLE_REQUIRED_COLUMNS)
        incoming_columns = [str(column).strip() for column in fieldnames if str(column).strip()]
        missing = [column for column in expected_columns if column not in incoming_columns]
        extra = [column for column in incoming_columns if column not in expected_columns]

        migration_details: dict[str, Any] = {}
        changed = False

        if missing == ["antecedent_condition_source"] and not extra:
            incoming_columns.append("antecedent_condition_source")
            missing = []
            changed = True
            migration_details["added_columns"] = ["antecedent_condition_source"]
            migration_details["migration"] = "legacy_v0_to_v1"

        if missing or extra:
            raise GenevaValidationError(
                "Geneva CN table schema mismatch.",
                code="invalid_cn_table_schema",
                details={
                    "path": CN_TABLE_CONTRACT_PATH,
                    "expected_columns": expected_columns,
                    "found_columns": incoming_columns,
                    "missing_columns": missing,
                    "extra_columns": extra,
                },
                status_code=409,
            )

        normalized_rows: list[dict[str, str]] = []
        seen_keys: set[tuple[str, str, str, str]] = set()
        for index, row in enumerate(rows, start=1):
            normalized = {
                column: self._stringify(row.get(column, ""))
                for column in incoming_columns
            }

            antecedent = normalized.get("antecedent_condition_source", "").strip()
            if not antecedent:
                antecedent = "arc_ii_seed"
                normalized["antecedent_condition_source"] = antecedent
                changed = True

            if antecedent not in _ALLOWED_ANTECEDENT_SOURCES:
                raise GenevaValidationError(
                    "Geneva CN table has unsupported antecedent_condition_source value.",
                    code="invalid_cn_table_schema",
                    details={
                        "path": CN_TABLE_CONTRACT_PATH,
                        "row_index": index,
                        "column": "antecedent_condition_source",
                        "value": antecedent,
                        "allowed": sorted(_ALLOWED_ANTECEDENT_SOURCES),
                    },
                    status_code=409,
                )

            canonical_row = {
                column: self._stringify(normalized.get(column, ""))
                for column in expected_columns
            }
            key = self._row_key(canonical_row, index=index)
            if key in seen_keys:
                raise GenevaValidationError(
                    "Geneva CN table contains duplicate row keys.",
                    code="invalid_cn_table_schema",
                    details={
                        "path": CN_TABLE_CONTRACT_PATH,
                        "row_index": index,
                        "row_key": "/".join(key),
                    },
                    status_code=409,
                )
            seen_keys.add(key)

            if any(canonical_row[column] != normalized.get(column, "") for column in expected_columns):
                changed = True
            normalized_rows.append(canonical_row)

        if incoming_columns != expected_columns:
            changed = True

        if rows:
            migration_details.setdefault("row_count", len(rows))
        migration_details.setdefault("normalized_columns", list(expected_columns))

        return normalized_rows, changed, migration_details

    def _normalize_payload_rows(
        self,
        rows: list[Any],
        existing_rows: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if not isinstance(rows, list) or not rows:
            raise GenevaValidationError(
                "rows payload must be a non-empty list",
                code="invalid_rows_payload",
                details="rows payload must be a non-empty list",
                status_code=400,
            )

        normalized_rows: list[dict[str, str]] = []
        seen_keys: set[tuple[str, str, str, str]] = set()

        for index, row in enumerate(rows, start=1):
            normalized = self._normalize_payload_row(row, index=index)
            key = self._row_key(normalized, index=index)
            if key in seen_keys:
                raise GenevaValidationError(
                    "rows payload contains duplicate key values",
                    code="invalid_rows_payload",
                    details={
                        "row_index": index,
                        "row_key": "/".join(key),
                    },
                    status_code=400,
                )
            seen_keys.add(key)
            normalized_rows.append(normalized)

        existing_keys = {self._row_key(row, index=index) for index, row in enumerate(existing_rows, start=1)}
        incoming_keys = {self._row_key(row, index=index) for index, row in enumerate(normalized_rows, start=1)}
        missing_keys = existing_keys - incoming_keys
        if missing_keys:
            preview = sorted("/".join(key) for key in missing_keys)
            raise GenevaValidationError(
                "rows payload is missing existing CN table rows; refresh and retry",
                code="missing_cn_table_rows",
                details={
                    "missing_keys": preview[:10],
                    "missing_count": len(missing_keys),
                },
                status_code=400,
            )

        return normalized_rows

    def _normalize_payload_row(self, row: Any, *, index: int) -> dict[str, str]:
        if isinstance(row, dict):
            normalized = {
                column: self._stringify(row.get(column, ""))
                for column in _CN_TABLE_REQUIRED_COLUMNS
            }
        elif isinstance(row, (list, tuple)):
            if len(row) != len(_CN_TABLE_REQUIRED_COLUMNS):
                raise GenevaValidationError(
                    "row column count does not match Geneva CN-table schema",
                    code="invalid_rows_payload",
                    details={
                        "row_index": index,
                        "expected_columns": len(_CN_TABLE_REQUIRED_COLUMNS),
                        "received_columns": len(row),
                    },
                    status_code=400,
                )
            normalized = {
                column: self._stringify(value)
                for column, value in zip(_CN_TABLE_REQUIRED_COLUMNS, row)
            }
        else:
            raise GenevaValidationError(
                "each row must be a list/tuple or mapping",
                code="invalid_rows_payload",
                details={"row_index": index},
                status_code=400,
            )

        antecedent = normalized.get("antecedent_condition_source", "").strip()
        if not antecedent:
            normalized["antecedent_condition_source"] = "user_override"
            antecedent = "user_override"

        if antecedent not in _ALLOWED_ANTECEDENT_SOURCES:
            raise GenevaValidationError(
                "antecedent_condition_source must be arc_ii_seed or user_override",
                code="invalid_rows_payload",
                details={
                    "row_index": index,
                    "column": "antecedent_condition_source",
                    "value": antecedent,
                    "allowed": sorted(_ALLOWED_ANTECEDENT_SOURCES),
                },
                status_code=400,
            )

        self._row_key(normalized, index=index)
        return normalized

    def _row_key(self, row: Mapping[str, Any], *, index: int) -> tuple[str, str, str, str]:
        key_values: list[str] = []
        for column in _CN_TABLE_KEY_COLUMNS:
            value = self._stringify(row.get(column, "")).strip()
            if not value:
                raise GenevaValidationError(
                    "CN table row is missing key column values",
                    code="invalid_rows_payload",
                    details={"row_index": index, "column": column},
                    status_code=400,
                )
            key_values.append(value)
        return tuple(key_values)  # type: ignore[return-value]

    def _snapshot_for_path(self, path: Path) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "path": CN_TABLE_CONTRACT_PATH,
            "exists": path.exists(),
            "schema_version": GENEVA_CN_TABLE_SCHEMA_VERSION,
        }

        if not path.exists():
            snapshot.update(
                {
                    "sha256": None,
                    "rows": 0,
                    "columns": len(_CN_TABLE_REQUIRED_COLUMNS),
                }
            )
            return snapshot

        stat = path.stat()
        snapshot.update(
            {
                "size_bytes": stat.st_size,
                "mtime_epoch": stat.st_mtime,
                "sha256": self._sha256_for_path(path),
            }
        )

        fieldnames, rows = self._read_rows(path)
        snapshot.update(
            {
                "rows": len(rows),
                "columns": len(fieldnames),
            }
        )
        return snapshot

    def _sha256_for_path(self, path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _emit_audit(
        self,
        geneva: "Geneva",
        *,
        event: str,
        before: Mapping[str, Any] | None,
        after: Mapping[str, Any] | None,
        details: Mapping[str, Any] | None,
    ) -> None:
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "lookup_path": CN_TABLE_CONTRACT_PATH,
            "before": before,
            "after": after,
            "details": dict(details or {}),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        audit_path = self._audit_path(geneva)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")

    def _atomic_write_rows(
        self,
        path: Path,
        fieldnames: Sequence[str],
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        os.close(fd)
        try:
            with open(tmp_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            column: self._stringify(row.get(column, ""))
                            for column in fieldnames
                        }
                    )
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _with_aliases(self, meta: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(meta)
        payload.setdefault("lookup_sha256", payload.get("sha256"))
        payload.setdefault("rows_count", payload.get("rows"))
        payload.setdefault("columns_count", payload.get("columns"))
        return payload

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        return str(value)


__all__ = [
    "CN_TABLE_CONTRACT_PATH",
    "CN_TABLE_RELPATH",
    "GENEVA_CN_TABLE_SCHEMA_VERSION",
    "GenevaCnTableService",
]
