from __future__ import annotations

import io
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from wepppy.microservices.vector_upload_normalization import (
    RedisRetentionLedger,
    RetentionActor,
    VectorUploadError,
    prepare_vector_upload,
    validate_feature_collection_geometries,
)

pytestmark = pytest.mark.unit


@dataclass
class _Reservation:
    reservation_id: str = "reservation-test"
    committed: int | None = None
    released: bool = False

    def commit(self, exact_bytes: int) -> None:
        self.committed = exact_bytes

    def release_prewrite(self) -> None:
        self.released = True


class _Ledger:
    def __init__(self) -> None:
        self.reservation = _Reservation()
        self.calls: list[dict[str, Any]] = []

    def reserve(self, **kwargs: Any) -> _Reservation:
        self.calls.append(kwargs)
        return self.reservation


class _Lease:
    def __init__(self) -> None:
        self.owned = True

    def assert_owned(self) -> None:
        if not self.owned:
            raise AssertionError("lease lost")

    def release(self) -> None:
        self.owned = False


def _polygon_payload() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"field_id": 1},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
                },
            }
        ],
    }


def _prepare_kwargs(tmp_path: Path, ledger: _Ledger) -> dict[str, object]:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    attempts = project / "vector_upload_attempts"
    return {
        "endpoint_max_bytes": 1024 * 1024,
        "attempt_root": attempts,
        "evidence_roots": (attempts,),
        "filesystem_root": tmp_path,
        "project_key": "run:test",
        "workflow": "test",
        "project_identity": "test-run",
        "actor": RetentionActor("human", 7),
        "validator": lambda _path, payload: validate_feature_collection_geometries(payload, ("Polygon", "MultiPolygon")),
        "ledger": ledger,
        "scope_lease_factory": lambda _key: _Lease(),
    }


def test_direct_geojson_retains_original_and_accepts_readback(tmp_path: Path) -> None:
    original = json.dumps(_polygon_payload(), separators=(",", ":")).encode()
    ledger = _Ledger()
    prepared = prepare_vector_upload(
        raw_filename="My Fields.geojson",
        stream=io.BytesIO(original),
        **_prepare_kwargs(tmp_path, ledger),
    )
    original_path = next((prepared.attempt_dir / "original").iterdir())
    assert original_path.name == "My_Fields.geojson.upload"
    assert original_path.read_bytes() == original
    assert stat_mode(original_path) == 0o600
    assert stat_mode(prepared.attempt_dir) == 0o700

    canonical = tmp_path / "project" / "accepted.geojson"
    result = prepared.publish(
        mutation=lambda candidate: shutil.copy2(candidate, canonical) or {"ok": True},
        canonical_path=canonical,
        canonical_relative_path="accepted.geojson",
    )
    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    assert result == canonical
    assert receipt["status"] == "accepted"
    assert receipt["source_sha256"] == sha256(original)
    assert receipt["canonical_sha256"] == sha256(original)
    assert receipt["actor"] == {"kind": "human", "user_id": 7}
    assert not prepared.candidate_path.exists()
    assert ledger.reservation.committed == sum(
        path.stat().st_size for path in prepared.attempt_dir.rglob("*") if path.is_file()
    )


def test_failed_workflow_validation_quarantines_complete_original_and_candidate(tmp_path: Path) -> None:
    payload = _polygon_payload()
    payload["features"][0]["geometry"] = {"type": "Point", "coordinates": [0.0, 0.0]}  # type: ignore[index]
    original = json.dumps(payload).encode()
    ledger = _Ledger()
    with pytest.raises(VectorUploadError, match="geometry must be") as raised:
        prepare_vector_upload(
            raw_filename="wrong.geojson",
            stream=io.BytesIO(original),
            **_prepare_kwargs(tmp_path, ledger),
        )
    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.status_code == 400
    assert receipt["status"] == "rejected"
    assert receipt["outcome"] == "quarantined"
    assert receipt["source_sha256"] == sha256(original)
    assert (attempt / "candidate.geojson").read_bytes() == original
    assert ledger.reservation.committed is not None


def test_oversize_records_no_original_hash_or_partial(tmp_path: Path) -> None:
    ledger = _Ledger()
    kwargs = _prepare_kwargs(tmp_path, ledger)
    kwargs["endpoint_max_bytes"] = 8
    with pytest.raises(VectorUploadError) as raised:
        prepare_vector_upload(
            raw_filename="large.geojson",
            stream=io.BytesIO(b"{" + b"x" * 20),
            **kwargs,
        )
    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.status_code == 413
    assert receipt["outcome"] == "oversize_not_retained"
    assert receipt["source_complete"] is False
    assert "source_sha256" not in receipt
    assert not list((attempt / "original").iterdir())


def test_binary_converter_digest_is_reconciled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = b"PAR1bounded-fixturePAR1"
    canonical = json.dumps(_polygon_payload(), separators=(",", ":")).encode()

    class Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "request_id": "converter-request",
                "geojson": _polygon_payload(),
                "metadata": {
                    "source_size": len(source),
                    "source_sha256": sha256(source),
                    "canonical_size": len(canonical),
                    "canonical_sha256": sha256(canonical),
                    "parser_provenance": {
                        "binary_name": "geoparquet_parser_cli",
                        "binary_version": "0.0.0",
                        "binary_sha256": "1" * 64,
                        "cargo_lock_sha256": "2" * 64,
                        "source_revision": "3" * 40,
                    },
                },
            }

    monkeypatch.setattr(
        "wepppy.microservices.vector_upload_normalization.requests.post",
        lambda *_args, **_kwargs: Response(),
    )
    ledger = _Ledger()
    prepared = prepare_vector_upload(
        raw_filename="fields.parquet",
        stream=io.BytesIO(source),
        converter_url="http://shape-converter/v1/convert",
        **_prepare_kwargs(tmp_path, ledger),
    )
    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    assert receipt["status"] == "prepared"
    assert receipt["converter_request_id"] == "converter-request"
    assert receipt["parser_provenance"]["binary_name"] == "geoparquet_parser_cli"
    prepared.reject("test_cleanup")


def test_converter_source_digest_mismatch_is_quarantined(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = b"PAR1bounded-fixturePAR1"

    class Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "request_id": "converter-request",
                "geojson": _polygon_payload(),
                "metadata": {
                    "source_size": len(source),
                    "source_sha256": "0" * 64,
                    "canonical_size": 1,
                    "canonical_sha256": "0" * 64,
                },
            }

    monkeypatch.setattr(
        "wepppy.microservices.vector_upload_normalization.requests.post",
        lambda *_args, **_kwargs: Response(),
    )
    ledger = _Ledger()
    with pytest.raises(VectorUploadError) as raised:
        prepare_vector_upload(
            raw_filename="fields.parquet",
            stream=io.BytesIO(source),
            converter_url="http://shape-converter/v1/convert",
            **_prepare_kwargs(tmp_path, ledger),
        )
    attempt = next((tmp_path / "project" / "vector_upload_attempts").iterdir())
    receipt = json.loads((attempt / "normalization.json").read_text())
    assert raised.value.code == "vector_source_integrity_error"
    assert receipt["status"] == "rejected"
    assert receipt["outcome"] == "quarantined"
    assert receipt["source_sha256"] == sha256(source)


def test_default_ledger_fails_closed_without_filesystem_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", raising=False)
    monkeypatch.delenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", raising=False)
    with pytest.raises(VectorUploadError) as raised:
        RedisRetentionLedger().reserve(
            project_key="run:test",
            actor=RetentionActor("human", 7),
            worst_case_bytes=1024,
            filesystem_root=tmp_path,
        )
    assert raised.value.code == "vector_retention_quota_exceeded"
    assert raised.value.status_code == 507


def sha256(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777
