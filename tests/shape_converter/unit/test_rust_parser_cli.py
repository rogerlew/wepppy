from __future__ import annotations

import importlib
import json
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.shape_converter.helpers.archive_builder import (
    build_minimal_line_dataset,
    build_minimal_point_dataset,
    build_minimal_polygon_dataset,
)
from wepppy.microservices.shape_converter.errors import ShapeConverterError
from wepppy.microservices.shape_converter.parser_provenance import (
    validate_parser_executable,
)


convert = importlib.import_module("wepppy.microservices.shape_converter.convert")
pytestmark = [pytest.mark.unit, pytest.mark.microservice]
_CRATE_ROOT = (
    Path(__file__).resolve().parents[3]
    / "wepppy"
    / "microservices"
    / "shape_converter"
    / "rust"
    / "shape_parser_cli"
)


def _write_dataset(root: Path, entries: dict[str, bytes]) -> Path:
    for name, content in entries.items():
        (root / name).write_bytes(content)
    return root / next(name for name in entries if name.endswith(".shp"))


def _run_cli(
    root: Path,
    shp_path: Path,
    output_path: Path,
    **limits: int,
) -> subprocess.CompletedProcess[str]:
    configured = {
        "max-payload-bytes": 1_000_000,
        "max-input-bytes": 1_000_000,
        "max-features": 100,
        "max-vertices-per-feature": 100,
        "max-memory-bytes": 536_870_912,
        "max-cpu-seconds": 60,
        "max-open-files": 32,
    }
    configured.update(limits)
    command = [
        str(convert._parser_cli_path()),
        "--request-root",
        str(root),
        "--shp-path",
        str(shp_path),
        "--output-path",
        str(output_path),
    ]
    for name, value in configured.items():
        command.extend((f"--{name}", str(value)))
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _two_point_dataset() -> dict[str, bytes]:
    entries = build_minimal_point_dataset(prefix="points")
    shp = bytearray(entries["points.shp"])
    record = bytes(shp[100:])
    struct.pack_into(">i", record := bytearray(record), 0, 2)
    shp.extend(record)
    struct.pack_into(">i", shp, 24, len(shp) // 2)

    shx = bytearray(entries["points.shx"])
    content_words = struct.unpack_from(">i", shx, 104)[0]
    shx.extend(struct.pack(">2i", 50 + 4 + content_words, content_words))
    struct.pack_into(">i", shx, 24, len(shx) // 2)

    dbf = bytearray(entries["points.dbf"])
    struct.pack_into("<I", dbf, 4, 2)
    header_length = struct.unpack_from("<H", dbf, 8)[0]
    record_length = struct.unpack_from("<H", dbf, 10)[0]
    first_record = dbf[header_length : header_length + record_length]
    dbf[header_length + record_length : header_length + record_length] = first_record
    return {"points.shp": bytes(shp), "points.shx": bytes(shx), "points.dbf": bytes(dbf)}


@pytest.mark.parametrize(
    ("entries", "expected_type", "expected_name", "expected_bounds"),
    [
        (build_minimal_point_dataset(), "Point", "demo", [10.0, 20.0, 10.0, 20.0]),
        (build_minimal_line_dataset(), "LineString", "line", [10.0, 20.0, 12.0, 21.0]),
        (
            build_minimal_polygon_dataset(
                ring=[
                    (10.0, 20.0),
                    (10.0, 21.0),
                    (11.0, 21.0),
                    (11.0, 20.0),
                    (10.0, 20.0),
                ]
            ),
            "Polygon",
            "poly",
            [10.0, 20.0, 11.0, 21.0],
        ),
    ],
)
def test_rust_cli_parses_valid_geometry_families(
    tmp_path: Path,
    entries: dict[str, bytes],
    expected_type: str,
    expected_name: str,
    expected_bounds: list[float],
) -> None:
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    convert._run_parser_worker(
        shp_path=shp_path,
        output_path=output_path,
        scratch=SimpleNamespace(request_dir=tmp_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["properties"] == [{"NAME": expected_name}]
    assert payload["geometries"][0]["type"] == expected_type
    assert payload["source_bounds"] == expected_bounds


def test_rust_cli_rejects_disguised_non_shapefile(tmp_path: Path) -> None:
    (tmp_path / "disguised.shp").write_text(
        '{"type":"FeatureCollection","features":[]}', encoding="utf-8"
    )
    (tmp_path / "disguised.shx").write_bytes(b"not-an-index")
    (tmp_path / "disguised.dbf").write_bytes(b"not-a-dbf")

    with pytest.raises(ShapeConverterError) as error:
        convert._run_parser_worker(
            shp_path=tmp_path / "disguised.shp",
            output_path=tmp_path / "payload.json",
            scratch=SimpleNamespace(request_dir=tmp_path),
        )

    assert error.value.code == "invalid_shapefile"


def test_rust_cli_accepts_numeric_utf8_cpg_label(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="encoded")
    dbf = bytearray(entries["encoded.dbf"])
    header_length = struct.unpack_from("<H", dbf, 8)[0]
    dbf[header_length : header_length + 11] = b" caf\xc3\xa9     "
    entries["encoded.dbf"] = bytes(dbf)
    entries["encoded.cpg"] = b"65001"
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path)

    assert result.returncode == 0, result.stderr
    assert json.loads(output_path.read_text(encoding="utf-8"))["properties"] == [
        {"NAME": "café"}
    ]


def test_rust_cli_enforces_vertex_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shp_path = _write_dataset(tmp_path, build_minimal_line_dataset())
    monkeypatch.setattr(convert, "_MAX_VERTICES_PER_FEATURE", 1)

    with pytest.raises(ShapeConverterError) as error:
        convert._run_parser_worker(
            shp_path=shp_path,
            output_path=tmp_path / "payload.json",
            scratch=SimpleNamespace(request_dir=tmp_path),
        )

    assert error.value.code == "archive_quota_exceeded"
    assert "vertex_limit_exceeded" in error.value.details


@pytest.mark.parametrize(
    ("limits", "expected_exit"),
    [
        ({"max-input-bytes": 1}, 1),
        ({"max-payload-bytes": 32}, 3),
        ({"max-open-files": 3}, 1),
    ],
)
def test_rust_cli_resource_limits_fail_without_publishing_output(
    tmp_path: Path,
    limits: dict[str, int],
    expected_exit: int | None,
) -> None:
    shp_path = _write_dataset(tmp_path, build_minimal_point_dataset())
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path, **limits)

    assert result.returncode != 0
    if expected_exit is not None:
        assert result.returncode == expected_exit
    assert not output_path.exists()
    assert not list(tmp_path.glob("payload.tmp.*"))


def test_rust_cli_feature_limit_has_dedicated_exit_and_no_output(tmp_path: Path) -> None:
    shp_path = _write_dataset(tmp_path, _two_point_dataset())
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path, **{"max-features": 1})

    assert result.returncode == 4
    assert not output_path.exists()


def test_rust_cli_rejects_bounded_malformed_binary_corpus(tmp_path: Path) -> None:
    base = build_minimal_point_dataset(prefix="sample_point")

    def mutate_file_code(entries: dict[str, bytearray]) -> None:
        struct.pack_into(">I", entries["sample_point.shp"], 0, 0)

    def mutate_shp_length(entries: dict[str, bytearray]) -> None:
        struct.pack_into(">I", entries["sample_point.shp"], 24, 0x7FFFFFFF)

    def mutate_shx_count(entries: dict[str, bytearray]) -> None:
        entries["sample_point.shx"].extend(struct.pack(">2I", 64, 10))
        struct.pack_into(">I", entries["sample_point.shx"], 24, 58)

    def mutate_dbf_count(entries: dict[str, bytearray]) -> None:
        struct.pack_into("<I", entries["sample_point.dbf"], 4, 2)

    def mutate_dbf_record_length(entries: dict[str, bytearray]) -> None:
        struct.pack_into("<H", entries["sample_point.dbf"], 10, 1)

    def mutate_nonfinite_bounds(entries: dict[str, bytearray]) -> None:
        struct.pack_into("<d", entries["sample_point.shp"], 36, float("nan"))

    mutations = (
        mutate_file_code,
        mutate_shp_length,
        mutate_shx_count,
        mutate_dbf_count,
        mutate_dbf_record_length,
        mutate_nonfinite_bounds,
    )
    for index, mutation in enumerate(mutations):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        entries = {name: bytearray(content) for name, content in base.items()}
        mutation(entries)
        shp_path = _write_dataset(
            case_root,
            {name: bytes(content) for name, content in entries.items()},
        )
        output_path = case_root / "payload.json"

        result = _run_cli(case_root, shp_path, output_path)

        assert result.returncode != 0, mutation.__name__
        assert not output_path.exists(), mutation.__name__


def test_rust_cli_command_receives_every_resource_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_command: list[str] = []

    class Process:
        pid = 123
        returncode = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            return "", ""

    def fake_popen(command, **_kwargs):  # noqa: ANN001
        captured_command.extend(command)
        return Process()

    monkeypatch.setattr(convert.subprocess, "Popen", fake_popen)
    convert._run_parser_worker(
        shp_path=tmp_path / "sample.shp",
        output_path=tmp_path / "payload.json",
        scratch=SimpleNamespace(request_dir=tmp_path),
    )

    for flag in (
        "--request-root",
        "--max-payload-bytes",
        "--max-input-bytes",
        "--max-features",
        "--max-vertices-per-feature",
        "--max-memory-bytes",
        "--max-cpu-seconds",
        "--max-open-files",
    ):
        assert flag in captured_command


def test_executable_provenance_sidecar_binds_binary_and_rejects_tampering(
    tmp_path: Path,
) -> None:
    source_binary = convert._parser_cli_path()
    binary = tmp_path / "shape_parser_cli"
    binary.write_bytes(source_binary.read_bytes())
    binary.chmod(0o755)
    sidecar = tmp_path / "shape_parser_cli.json"
    generator = _CRATE_ROOT / "tools" / "generate_provenance.py"
    validator = _CRATE_ROOT / "tools" / "validate_provenance.py"
    rustc = tmp_path / "rustc"
    rustc.write_text("#!/bin/sh\necho 'rustc 1.92.0 test'\n", encoding="utf-8")
    rustc.chmod(0o755)

    generated = subprocess.run(
        [
            sys.executable,
            str(generator),
            "--binary",
            str(binary),
            "--source-root",
            str(_CRATE_ROOT),
            "--output",
            str(sidecar),
            "--source-revision",
            "test-revision",
            "--release-label",
            "test-release",
            "--built-utc",
            "2026-11-14T00:00:00Z",
            "--rustc",
            str(rustc),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert generated.returncode == 0, generated.stderr
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["schema"] == "shape-parser-binary-provenance-v1"
    assert payload["binary"]["version"] == "shape_parser_cli 0.1.0"
    assert payload["source"]["revision"] == "test-revision"
    assert payload["source"]["files"]

    valid = subprocess.run(
        [sys.executable, str(validator), "--binary", str(binary), "--sidecar", str(sidecar)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert valid.returncode == 0, valid.stderr
    assert validate_parser_executable(binary) == (True, None)

    binary.write_bytes(binary.read_bytes() + b"tampered")
    invalid = subprocess.run(
        [sys.executable, str(validator), "--binary", str(binary), "--sidecar", str(sidecar)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid.returncode != 0
    assert "mismatch" in invalid.stderr
    assert validate_parser_executable(binary) == (False, "parser_provenance_contract_invalid")
