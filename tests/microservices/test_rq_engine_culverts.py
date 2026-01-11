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

    monkeypatch.setattr(culvert_routes, "_enqueue_culvert_batch_job", fake_enqueue)

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
    assert not (batch_root / "topo" / "flovec.tif").exists()
    assert not (batch_root / "topo" / "netful.tif").exists()


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


def test_culvert_ingest_invalid_point_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    def mutate_points(name: str, data: bytes) -> bytes:
        if name != "culverts/culvert_points.geojson":
            return data
        payload = json.loads(data.decode("utf-8"))
        features = payload.get("features", [])
        if features:
            features[0]["properties"]["Point_ID"] = "../escape"
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
    assert any(error["code"] == "invalid_point_id" for error in payload["errors"])


def test_culvert_ingest_duplicate_point_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    def mutate_points(name: str, data: bytes) -> bytes:
        if name != "culverts/culvert_points.geojson":
            return data
        payload = json.loads(data.decode("utf-8"))
        features = payload.get("features", [])
        if len(features) > 1:
            first_id = features[0]["properties"].get("Point_ID")
            features[1]["properties"]["Point_ID"] = first_id
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
    assert any(error["code"] == "duplicate_point_id" for error in payload["errors"])


def test_culvert_ingest_invalid_metadata_schema_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    def mutate_metadata(name: str, data: bytes) -> bytes:
        if name != "metadata.json":
            return data
        payload = json.loads(data.decode("utf-8"))
        payload["schema_version"] = "bad-metadata-schema"
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
    assert any(error["code"] == "invalid_schema_version" for error in payload["errors"])


def test_culvert_ingest_invalid_model_params_schema_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    def mutate_model_params(name: str, data: bytes) -> bytes:
        if name != "model-parameters.json":
            return data
        payload = json.loads(data.decode("utf-8"))
        payload["schema_version"] = "bad-model-params-schema"
        return json.dumps(payload).encode("utf-8")

    bad_zip = _rewrite_payload_zip(tmp_path, mutate_model_params)

    with bad_zip.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
            )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert any(error["code"] == "invalid_schema_version" for error in payload["errors"])


def test_culvert_ingest_zip_sha256_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    with PAYLOAD_ZIP.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
                data={"zip_sha256": "deadbeef"},
            )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert any(error["code"] == "zip_sha256_mismatch" for error in payload["errors"])


def test_culvert_ingest_total_bytes_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    total_bytes = PAYLOAD_ZIP.stat().st_size

    with PAYLOAD_ZIP.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
                data={"total_bytes": str(total_bytes + 1)},
            )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert any(error["code"] == "total_bytes_mismatch" for error in payload["errors"])


def test_culvert_ingest_invalid_zip_member_path_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    bad_zip = _rewrite_payload_zip_with_member(
        tmp_path, "../escape.txt", b"nope"
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
    assert any(
        error["code"] == "invalid_member_path" for error in payload["errors"]
    )


def test_culvert_ingest_raster_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    rasterio = pytest.importorskip("rasterio")
    import numpy as np

    with zipfile.ZipFile(PAYLOAD_ZIP) as src:
        streams_bytes = src.read("topo/streams.tif")

    with rasterio.io.MemoryFile(streams_bytes) as mem:
        with mem.open() as src:
            crs = src.crs
            transform = src.transform
            width = src.width + 1
            height = src.height + 1

    data = np.ones((height, width), dtype=np.uint8)
    with rasterio.io.MemoryFile() as mem:
        with mem.open(
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=data.dtype,
            crs=crs,
            transform=transform,
            nodata=0,
        ) as dst:
            dst.write(data, 1)
        mismatched_streams = mem.read()

    bad_zip = _rewrite_payload_zip(
        tmp_path,
        lambda name, data: mismatched_streams
        if name == "topo/streams.tif"
        else data,
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
    assert any(error["code"] == "raster_mismatch" for error in payload["errors"])


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


def _rewrite_payload_zip_with_member(
    tmp_path: Path, member_name: str, payload: bytes
) -> Path:
    dest = tmp_path / "payload.zip"
    with zipfile.ZipFile(PAYLOAD_ZIP) as src, zipfile.ZipFile(dest, "w") as dst:
        for info in src.infolist():
            if info.is_dir():
                continue
            data = src.read(info.filename)
            dst.writestr(info, data)
        dst.writestr(member_name, payload)
    return dest
