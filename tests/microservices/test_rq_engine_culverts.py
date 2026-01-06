import json
import zipfile
from pathlib import Path
from typing import Callable, Optional

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import culvert_routes


pytestmark = pytest.mark.microservice

PAYLOAD_ZIP = Path(
    "tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip"
)


def test_culvert_ingest_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    seen = {}

    def fake_enqueue(batch_uuid: str) -> str:
        seen["uuid"] = batch_uuid
        return "job-123"

    def fake_generate_batch_topo(dem: Path, streams: Path, flovec: Path, netful: Path) -> None:
        assert dem.exists()
        assert streams.exists()
        flovec.write_bytes(b"")
        netful.write_bytes(b"")

    monkeypatch.setattr(culvert_routes, "_enqueue_culvert_batch_job", fake_enqueue)
    monkeypatch.setattr(culvert_routes, "_generate_batch_topo", fake_generate_batch_topo)

    with PAYLOAD_ZIP.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"
    assert payload["status_url"] == "/rq-engine/api/jobstatus/job-123"
    assert payload["culvert_batch_uuid"] == seen["uuid"]

    batch_root = culverts_root / payload["culvert_batch_uuid"]
    metadata_path = batch_root / "batch_metadata.json"
    assert metadata_path.is_file()
    metadata = json.loads(metadata_path.read_text())
    assert metadata["culvert_batch_uuid"] == payload["culvert_batch_uuid"]
    assert "created_at" in metadata


def test_culvert_ingest_missing_files_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    bad_zip = _rewrite_payload_zip(
        tmp_path,
        lambda name, data: None if name == "topo/streams.tif" else data,
    )

    with bad_zip.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
            )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert any(error["code"] == "missing_file" for error in payload["errors"])


def test_culvert_ingest_crs_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    def mutate_metadata(name: str, data: bytes) -> bytes:
        if name != "metadata.json":
            return data
        payload = json.loads(data.decode("utf-8"))
        payload["crs"]["proj4"] = "+proj=longlat +datum=WGS84 +no_defs"
        return json.dumps(payload).encode("utf-8")

    bad_zip = _rewrite_payload_zip(tmp_path, mutate_metadata)

    with bad_zip.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
            )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert any(error["code"] == "crs_mismatch" for error in payload["errors"])


def test_culvert_ingest_missing_point_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    def mutate_points(name: str, data: bytes) -> bytes:
        if name != "culverts/culvert_points.geojson":
            return data
        payload = json.loads(data.decode("utf-8"))
        for feature in payload.get("features", []):
            if isinstance(feature.get("properties"), dict):
                feature["properties"].pop("Point_ID", None)
        return json.dumps(payload).encode("utf-8")

    bad_zip = _rewrite_payload_zip(tmp_path, mutate_points)

    with bad_zip.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
            )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert any(error["code"] == "missing_point_id" for error in payload["errors"])


def _rewrite_payload_zip(
    tmp_path: Path, mutate: Callable[[str, bytes], Optional[bytes]]
) -> Path:
    dest = tmp_path / "payload.zip"
    with zipfile.ZipFile(PAYLOAD_ZIP) as src, zipfile.ZipFile(dest, "w") as dst:
        for info in src.infolist():
            if info.is_dir():
                continue
            data = src.read(info.filename)
            data = mutate(info.filename, data)
            if data is None:
                continue
            dst.writestr(info, data)
    return dest
