from __future__ import annotations

import hashlib
import json
import asyncio
import tempfile
import signal
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from wepppy.microservices.shape_converter.cleanup import RequestScratchLayout
from wepppy.microservices.shape_converter.convert import (
    convert_uploaded_archive,
    probe_geoparquet_parser_runtime,
)
from wepppy.microservices.shape_converter.errors import ShapeConverterError
import wepppy.microservices.shape_converter.convert as convert_module


FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "work-packages"
    / "20261116_vector_upload_normalization"
    / "artifacts"
    / "red_fixtures"
)


def layout(root: Path) -> RequestScratchLayout:
    root.mkdir(mode=0o700)
    output = root / "output"
    output.mkdir()
    return RequestScratchLayout(
        request_dir=root,
        upload_archive_path=root / "upload.bin",
        extraction_root=root / "extracted",
        output_root=output,
    )


def upload(data: bytes, filename: str) -> UploadFile:
    stream = tempfile.SpooledTemporaryFile(max_size=len(data) + 1)
    stream.write(data)
    stream.seek(0)
    return UploadFile(stream, filename=filename)


@pytest.fixture
def direct_blocking_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run(function, /, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return function(*args, **kwargs)

    monkeypatch.setattr(convert_module, "_run_blocking_phase", run)
    monkeypatch.setattr(
        convert_module,
        "read_parser_provenance",
        lambda _path: {
            "binary_name": "geoparquet_parser_cli",
            "binary_version": "geoparquet_parser_cli 0.0.0",
            "binary_sha256": "1" * 64,
            "cargo_lock_sha256": "2" * 64,
            "source_revision": "3" * 40,
        },
    )


def test_geoparquet_normalizes_with_source_and_canonical_provenance(
    tmp_path: Path, direct_blocking_phase: None
) -> None:
    source = (FIXTURES / "polygon-1.1.0-snappy.parquet").read_bytes()
    converted = asyncio.run(
        convert_uploaded_archive(
            archive=upload(source, "watershed.parquet"),
            scratch=layout(tmp_path / "request"),
            request_id="request-1",
            output_format="geojson",
            target_crs="wgs84",
        )
    )
    payload = json.loads(converted.content)
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    assert payload["features"][0]["geometry"]["type"] == "Polygon"
    assert converted.metadata["source_size"] == len(source)
    assert converted.metadata["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert converted.metadata["canonical_size"] == len(converted.content)
    assert converted.metadata["canonical_sha256"] == hashlib.sha256(converted.content).hexdigest()
    assert converted.metadata["source_format"] == "geoparquet"
    assert converted.metadata["parser_provenance"]["binary_name"] == "geoparquet_parser_cli"


def test_hostile_geoparquet_rejects_without_published_output(
    tmp_path: Path, direct_blocking_phase: None
) -> None:
    source = (FIXTURES / "page-declared-expansion.parquet").read_bytes()
    scratch = layout(tmp_path / "request")
    with pytest.raises(ShapeConverterError) as captured:
        asyncio.run(
            convert_uploaded_archive(
                archive=upload(source, "hostile.geoparquet"),
                scratch=scratch,
                request_id="request-2",
                output_format="geojson",
                target_crs="wgs84",
            )
        )
    assert captured.value.code == "vector_limit_exceeded"
    assert not list(scratch.output_root.iterdir())


def test_projected_geoparquet_uses_best_offline_operation(
    tmp_path: Path, direct_blocking_phase: None
) -> None:
    source = (FIXTURES / "projected-crs-control.parquet").read_bytes()
    converted = asyncio.run(
        convert_uploaded_archive(
            archive=upload(source, "projected.parquet"),
            scratch=layout(tmp_path / "request"),
            request_id="request-projected",
            output_format="geojson",
            target_crs="wgs84",
        )
    )
    coordinate = json.loads(converted.content)["features"][0]["geometry"]["coordinates"]
    assert coordinate == pytest.approx([-116.0, 44.0], abs=1e-8)
    assert converted.metadata["detected_crs"]["authority"] == "EPSG:32611"


def test_geoparquet_rejects_when_best_offline_grid_is_unavailable(
    tmp_path: Path, direct_blocking_phase: None
) -> None:
    source = (FIXTURES / "missing-grid-crs.parquet").read_bytes()
    with pytest.raises(ShapeConverterError) as captured:
        asyncio.run(
            convert_uploaded_archive(
                archive=upload(source, "missing-grid.parquet"),
                scratch=layout(tmp_path / "request"),
                request_id="request-missing-grid",
                output_format="geojson",
                target_crs="wgs84",
            )
        )
    assert captured.value.code == "vector_crs_invalid"


def test_geoparquet_runtime_canary_executes_real_parser(tmp_path: Path) -> None:
    assert asyncio.run(probe_geoparquet_parser_runtime(tmp_path)) == (True, None)


def test_geoparquet_worker_uses_fixed_argv_minimal_env_and_new_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class Process:
        returncode = 0
        pid = 11001

        async def wait(self) -> int:
            return 0

    async def execute(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["args"] = args
        captured.update(kwargs)
        return Process()

    monkeypatch.setattr(convert_module.asyncio, "create_subprocess_exec", execute)
    asyncio.run(
        convert_module._run_geoparquet_parser_worker(
            input_path=tmp_path / "input.parquet",
            output_path=tmp_path / "output.json",
            scratch=SimpleNamespace(request_dir=tmp_path),
        )
    )
    args = captured["args"]
    assert isinstance(args, tuple)
    assert args[0] == str(convert_module._geoparquet_parser_cli_path())
    assert "--input-path" in args and "--output-path" in args
    assert captured["env"] == {"LC_ALL": "C", "LANG": "C"}
    assert captured["cwd"] == tmp_path.as_posix()
    assert captured["start_new_session"] is True
    assert captured["stdout"] == subprocess.DEVNULL
    assert captured["stderr"] == subprocess.DEVNULL


def test_geoparquet_worker_timeout_drains_process_group_and_removes_partial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    signals: list[int] = []
    output = tmp_path / "output.json"
    output.write_text("partial")

    class Process:
        returncode = None
        pid = 11002

        async def wait(self) -> int:
            if signal.SIGKILL in signals:
                self.returncode = -signal.SIGKILL
                return self.returncode
            await asyncio.sleep(10)
            return 0

    async def execute(*_args, **_kwargs):
        return Process()

    monkeypatch.setattr(convert_module.asyncio, "create_subprocess_exec", execute)
    monkeypatch.setattr(convert_module, "_PARSER_SUBPROCESS_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(convert_module, "_PARSER_SUBPROCESS_KILL_GRACE_SECONDS", 0.01)
    monkeypatch.setattr(convert_module.os, "killpg", lambda _pid, value: signals.append(value))
    monkeypatch.setattr(
        convert_module,
        "_process_group_exists",
        lambda _pid: signal.SIGKILL not in signals,
    )
    with pytest.raises(ShapeConverterError) as captured:
        asyncio.run(
            convert_module._run_geoparquet_parser_worker(
                input_path=tmp_path / "input.parquet",
                output_path=output,
                scratch=SimpleNamespace(request_dir=tmp_path),
            )
        )
    assert captured.value.code == "request_timeout"
    assert signal.SIGTERM in signals and signal.SIGKILL in signals
    assert not output.exists()


def _parser_payload(*, coordinates: list[float], bounds: list[float]) -> dict[str, object]:
    return {
        "schema": "geoparquet-parser-v1",
        "properties": [{"name": "control"}],
        "geometries": [{"type": "Point", "coordinates": coordinates}],
        "feature_count": 1,
        "geometry_types": ["Point Z" if len(coordinates) == 3 else "Point"],
        "source_bounds": bounds,
        "source_crs": "OGC:CRS84",
        "geoparquet_version": "1.1.0",
    }


def test_geoparquet_ipc_reconciles_observed_bounds_and_accepts_3d() -> None:
    loaded = convert_module._loaded_geoparquet_from_payload(
        _parser_payload(coordinates=[1.0, 2.0, 3.0], bounds=[1.0, 2.0, 1.0, 2.0])
    )
    assert loaded.source_bounds == (1.0, 2.0, 1.0, 2.0)
    with pytest.raises(ShapeConverterError) as captured:
        convert_module._loaded_geoparquet_from_payload(
            _parser_payload(coordinates=[1.0, 2.0], bounds=[0.0, 0.0, 0.0, 0.0])
        )
    assert captured.value.code == "vector_converter_unavailable"


def test_geoparquet_ipc_rejects_exponent_overflow(tmp_path: Path) -> None:
    payload = _parser_payload(coordinates=[1.0, 2.0], bounds=[1.0, 2.0, 1.0, 2.0])
    raw = json.dumps(payload).replace("1.0, 2.0", "1e400, 2.0", 1)
    path = tmp_path / "payload.json"
    path.write_text(raw)
    with pytest.raises(ShapeConverterError) as captured:
        convert_module._read_geoparquet_payload(payload_path=path)
    assert captured.value.code == "vector_converter_unavailable"


@pytest.mark.parametrize("coordinate", [10**400, True])
def test_geoparquet_ipc_rejects_nonfinite_or_nonnumeric_coordinate(coordinate: object) -> None:
    payload = _parser_payload(coordinates=[1.0, 2.0], bounds=[1.0, 2.0, 1.0, 2.0])
    payload["geometries"][0]["coordinates"][0] = coordinate  # type: ignore[index]
    with pytest.raises(ShapeConverterError) as captured:
        convert_module._loaded_geoparquet_from_payload(payload)
    assert captured.value.code == "vector_converter_unavailable"
    assert captured.value.status_code == 503


def test_geoparquet_ipc_rejects_deep_coordinate_tree() -> None:
    payload = _parser_payload(coordinates=[1.0, 2.0], bounds=[1.0, 2.0, 1.0, 2.0])
    coordinates: object = [1.0, 2.0]
    for _ in range(18):
        coordinates = [coordinates]
    payload["geometries"][0]["coordinates"] = coordinates  # type: ignore[index]
    with pytest.raises(ShapeConverterError) as captured:
        convert_module._loaded_geoparquet_from_payload(payload)
    assert captured.value.code == "vector_converter_unavailable"
    assert captured.value.status_code == 503


@pytest.mark.parametrize(
    ("returncode", "code", "status_code"),
    [
        (1, "invalid_vector", 400),
        (2, "vector_converter_unavailable", 503),
        (3, "vector_converter_unavailable", 503),
        (4, "vector_limit_exceeded", 413),
        (-signal.SIGXCPU, "request_timeout", 408),
        (-signal.SIGXFSZ, "vector_limit_exceeded", 413),
        (-signal.SIGKILL, "vector_converter_unavailable", 503),
    ],
)
def test_geoparquet_worker_maps_exit_statuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncode: int,
    code: str,
    status_code: int,
) -> None:
    class Process:
        pid = 11003

        def __init__(self) -> None:
            self.returncode = returncode

        async def wait(self) -> int:
            return self.returncode

    async def execute(*_args, **_kwargs):
        return Process()

    output = tmp_path / "output.json"
    output.write_text("partial")
    monkeypatch.setattr(convert_module.asyncio, "create_subprocess_exec", execute)
    with pytest.raises(ShapeConverterError) as captured:
        asyncio.run(
            convert_module._run_geoparquet_parser_worker(
                input_path=tmp_path / "input.parquet",
                output_path=output,
                scratch=SimpleNamespace(request_dir=tmp_path),
            )
        )
    assert captured.value.code == code
    assert captured.value.status_code == status_code
    assert not output.exists()
