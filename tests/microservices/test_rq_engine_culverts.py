import json
import zipfile
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import culvert_routes
from wepppy.weppcloud.utils import auth_tokens


pytestmark = pytest.mark.microservice

PAYLOAD_ZIP = Path(
    "tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip"
)


def _issue_culvert_token(
    monkeypatch: pytest.MonkeyPatch, *, scopes: list[str] | None = None
) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "culvert-tester",
        scopes=scopes or ["culvert:batch:submit"],
        audience="rq-engine",
        extra_claims={"jti": "test-jti"},
    )
    return payload["token"]


def _auth_headers(
    monkeypatch: pytest.MonkeyPatch, *, scopes: list[str] | None = None
) -> dict[str, str]:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    token = _issue_culvert_token(monkeypatch, scopes=scopes)
    return {"Authorization": f"Bearer {token}"}

def assert_validation_error(payload: dict[str, Any], code: str) -> None:
    assert payload["error"]["code"] == "validation_error"
    assert any(error["code"] == code for error in payload["errors"])


def test_culvert_ingest_requires_auth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/culverts-wepp-batch/")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"


def test_culvert_ingest_rejects_missing_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch, scopes=["runs:read"])

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/culverts-wepp-batch/", headers=auth_headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


def test_culvert_ingest_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)
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
                headers=auth_headers,
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"
    assert payload["status_url"] == "/rq-engine/api/jobstatus/job-123"
    assert payload["culvert_batch_uuid"] == seen["uuid"]
    assert isinstance(payload.get("browse_token"), str)

    browse_claims = auth_tokens.decode_token(payload["browse_token"], audience="rq-engine")
    assert browse_claims.get("token_class") == "service"
    assert payload["culvert_batch_uuid"] in (browse_claims.get("runs") or [])

    batch_root = culverts_root / payload["culvert_batch_uuid"]
    metadata_path = batch_root / "batch_metadata.json"
    assert metadata_path.is_file()
    metadata = json.loads(metadata_path.read_text())
    assert metadata["culvert_batch_uuid"] == payload["culvert_batch_uuid"]
    assert "created_at" in metadata
    runner = CulvertsRunner.getInstance(str(batch_root))
    assert runner.rq_job_ids.get("run_culvert_batch_rq") == "job-123"
    assert not (batch_root / "topo" / "flovec.tif").exists()
    assert not (batch_root / "topo" / "netful.tif").exists()


def test_culvert_retry_success_returns_browse_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch, scopes=["culvert:batch:retry"])
    batch_uuid = "culvert-retry-1234"
    point_id = "42"

    batch_root = culverts_root / batch_uuid
    watersheds_path = batch_root / "culverts" / "watersheds.geojson"
    watersheds_path.parent.mkdir(parents=True, exist_ok=True)
    watersheds_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"Point_ID": point_id},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [[0, 0], [1, 0], [1, 1], [0, 0]],
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    seen: dict[str, str] = {}

    def fake_enqueue(batch: str, point: str) -> str:
        seen["batch_uuid"] = batch
        seen["point_id"] = point
        return "job-456"

    monkeypatch.setattr(culvert_routes, "_enqueue_culvert_run_job", fake_enqueue)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-456"
    assert payload["culvert_batch_uuid"] == batch_uuid
    assert payload["point_id"] == point_id
    assert payload["status_url"] == "/rq-engine/api/jobstatus/job-456"
    assert isinstance(payload.get("browse_token"), str)
    assert isinstance(payload.get("browse_token_expires_at"), int)

    browse_claims = auth_tokens.decode_token(payload["browse_token"], audience="rq-engine")
    assert browse_claims.get("token_class") == "service"
    assert batch_uuid in (browse_claims.get("runs") or [])
    assert "culverts" in {str(g).strip().lower() for g in (browse_claims.get("service_groups") or [])}
    assert payload["browse_token_expires_at"] == browse_claims.get("exp")
    assert seen == {"batch_uuid": batch_uuid, "point_id": point_id}


def test_culvert_ingest_missing_files_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)
    bad_zip = _rewrite_payload_zip(
        tmp_path,
        lambda name, data: None if name == "topo/streams.tif" else data,
    )

    with bad_zip.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "missing_file")


def test_culvert_ingest_crs_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "crs_mismatch")


def test_culvert_ingest_missing_point_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "missing_point_id")


def test_culvert_ingest_invalid_point_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "invalid_point_id")


def test_culvert_ingest_duplicate_point_id_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "duplicate_point_id")


def test_culvert_ingest_invalid_metadata_schema_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "invalid_schema_version")


def test_culvert_ingest_invalid_model_params_schema_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "invalid_schema_version")


def test_culvert_ingest_zip_sha256_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

    with PAYLOAD_ZIP.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
                data={"zip_sha256": "deadbeef"},
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "zip_sha256_mismatch")


def test_culvert_ingest_total_bytes_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)
    total_bytes = PAYLOAD_ZIP.stat().st_size

    with PAYLOAD_ZIP.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
                data={"total_bytes": str(total_bytes + 1)},
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "total_bytes_mismatch")


def test_culvert_ingest_invalid_zip_member_path_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)
    bad_zip = _rewrite_payload_zip_with_member(
        tmp_path, "../escape.txt", b"nope"
    )

    with bad_zip.open("rb") as handle:
        with TestClient(rq_engine.app) as client:
            response = client.post(
                "/api/culverts-wepp-batch/",
                files={"payload.zip": ("payload.zip", handle, "application/zip")},
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "invalid_member_path")


def test_culvert_ingest_raster_mismatch_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))
    auth_headers = _auth_headers(monkeypatch)

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
                headers=auth_headers,
            )

    assert response.status_code == 400
    payload = response.json()
    assert_validation_error(payload, "raster_mismatch")


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
