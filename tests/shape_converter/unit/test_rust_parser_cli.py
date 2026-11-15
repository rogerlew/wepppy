from __future__ import annotations

import asyncio
import importlib
import json
import signal
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
    build_multipatch_dataset,
    build_multipart_dataset,
    build_multipoint_dataset,
    build_repeated_point_dataset,
    build_shape_dataset,
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


def _dbf_bytes(
    fields: list[tuple[str, str, int, int, bytes]],
    *,
    language_driver: int = 0,
    deleted: bool = False,
) -> bytes:
    header_length = 32 + 32 * len(fields) + 1
    record_length = 1 + sum(field[2] for field in fields)
    header = bytearray(32)
    header[0] = 0x03
    struct.pack_into("<I", header, 4, 1)
    struct.pack_into("<H", header, 8, header_length)
    struct.pack_into("<H", header, 10, record_length)
    header[29] = language_driver
    descriptors = bytearray()
    record = bytearray(b"*" if deleted else b" ")
    for name, kind, length, decimal_count, value in fields:
        descriptor = bytearray(32)
        encoded_name = name.encode("ascii")[:10]
        descriptor[: len(encoded_name)] = encoded_name
        descriptor[11] = ord(kind)
        descriptor[16] = length
        descriptor[17] = decimal_count
        descriptors.extend(descriptor)
        record.extend(value[:length].ljust(length, b" "))
    return bytes(header + descriptors + b"\r" + record + b"\x1a")


def _parse_direct(tmp_path: Path, entries: dict[str, bytes]) -> dict:
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"
    result = _run_cli(tmp_path, shp_path, output_path)
    assert result.returncode == 0, result.stderr
    return json.loads(output_path.read_text(encoding="utf-8"))


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

    asyncio.run(
        convert._run_parser_worker(
            shp_path=shp_path,
            output_path=output_path,
            scratch=SimpleNamespace(request_dir=tmp_path),
        )
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["properties"] == [{"NAME": expected_name}]
    assert payload["geometries"][0]["type"] == expected_type
    assert payload["source_bounds"] == expected_bounds


@pytest.mark.parametrize(
    ("entries", "expected_type", "coordinate_depth"),
    [
        (build_multipoint_dataset(), "MultiPoint", 1),
        (build_multipoint_dataset(prefix="multipoint-m", shape_type=28), "MultiPoint", 1),
        (
            build_multipart_dataset(
                prefix="line-multipart",
                shape_type=3,
                parts=[[(0.0, 0.0), (1.0, 1.0)], [(2.0, 0.0), (3.0, 1.0)]],
            ),
            "MultiLineString",
            2,
        ),
        (
            build_multipart_dataset(
                prefix="line-m",
                shape_type=23,
                parts=[[(0.0, 0.0), (1.0, 1.0)]],
            ),
            "LineString",
            1,
        ),
        (
            build_multipart_dataset(
                prefix="polygon-m",
                shape_type=25,
                parts=[[
                    (0.0, 0.0),
                    (0.0, 1.0),
                    (1.0, 1.0),
                    (1.0, 0.0),
                    (0.0, 0.0),
                ]],
            ),
            "Polygon",
            2,
        ),
    ],
)
def test_rust_cli_parses_multipoint_m_and_multipart_families(
    tmp_path: Path,
    entries: dict[str, bytes],
    expected_type: str,
    coordinate_depth: int,
) -> None:
    payload = _parse_direct(tmp_path, entries)

    geometry = payload["geometries"][0]
    assert geometry["type"] == expected_type
    coordinates = geometry["coordinates"]
    for _ in range(coordinate_depth):
        coordinates = coordinates[0]
    assert len(coordinates) == 2


def test_rust_cli_drops_m_measure_consistently_with_fiona_oracle(tmp_path: Path) -> None:
    record = struct.pack("<i3d", 21, 10.0, 20.0, 99.0)
    entries = build_shape_dataset(
        prefix="point-m",
        shape_type=21,
        record_content=record,
        bbox=(10.0, 20.0, 10.0, 20.0),
    )

    payload = _parse_direct(tmp_path, entries)

    assert payload["geometries"] == [{"type": "Point", "coordinates": [10.0, 20.0]}]


@pytest.mark.parametrize(
    ("name", "parts", "expected_polygon_count", "expected_ring_count"),
    [
        (
            "first-ring",
            [
                (4, [(0.0, 0.0, 1.0), (0.0, 3.0, 1.0), (3.0, 3.0, 1.0), (0.0, 0.0, 1.0)]),
                (5, [(0.5, 0.5, 1.0), (1.0, 0.5, 1.0), (0.5, 1.0, 1.0), (0.5, 0.5, 1.0)]),
            ],
            1,
            2,
        ),
        (
            "inner-ring",
            [
                (2, [(0.0, 0.0, 1.0), (0.0, 3.0, 1.0), (3.0, 3.0, 1.0), (0.0, 0.0, 1.0)]),
                (3, [(0.5, 0.5, 1.0), (1.0, 0.5, 1.0), (0.5, 1.0, 1.0), (0.5, 0.5, 1.0)]),
            ],
            1,
            2,
        ),
        (
            "two-outer-rings",
            [
                (2, [(0.0, 0.0, 1.0), (0.0, 3.0, 1.0), (3.0, 3.0, 1.0), (0.0, 0.0, 1.0)]),
                (2, [(10.0, 0.0, 1.0), (10.0, 3.0, 1.0), (13.0, 3.0, 1.0), (10.0, 0.0, 1.0)]),
            ],
            2,
            1,
        ),
        (
            "two-first-rings",
            [
                (4, [(0.0, 0.0, 1.0), (0.0, 3.0, 1.0), (3.0, 3.0, 1.0), (0.0, 0.0, 1.0)]),
                (4, [(10.0, 0.0, 1.0), (10.0, 3.0, 1.0), (13.0, 3.0, 1.0), (10.0, 0.0, 1.0)]),
            ],
            2,
            1,
        ),
        (
            "triangle-fan",
            [(1, [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)])],
            2,
            1,
        ),
        (
            "triangle-strip",
            [(0, [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0), (1.0, 1.0, 1.0)])],
            2,
            1,
        ),
    ],
)
def test_rust_cli_parses_each_multipatch_family_policy(
    tmp_path: Path,
    name: str,
    parts: list[tuple[int, list[tuple[float, float, float]]]],
    expected_polygon_count: int,
    expected_ring_count: int,
) -> None:
    payload = _parse_direct(
        tmp_path,
        build_multipatch_dataset(prefix=name, parts=parts),
    )

    geometry = payload["geometries"][0]
    assert geometry["type"] == "MultiPolygon"
    assert len(geometry["coordinates"]) == expected_polygon_count
    assert len(geometry["coordinates"][0]) == expected_ring_count


def test_rust_cli_rejects_disguised_non_shapefile(tmp_path: Path) -> None:
    (tmp_path / "disguised.shp").write_text(
        '{"type":"FeatureCollection","features":[]}', encoding="utf-8"
    )
    (tmp_path / "disguised.shx").write_bytes(b"not-an-index")
    (tmp_path / "disguised.dbf").write_bytes(b"not-a-dbf")

    with pytest.raises(ShapeConverterError) as error:
        asyncio.run(
            convert._run_parser_worker(
                shp_path=tmp_path / "disguised.shp",
                output_path=tmp_path / "payload.json",
                scratch=SimpleNamespace(request_dir=tmp_path),
            )
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
        asyncio.run(
            convert._run_parser_worker(
                shp_path=shp_path,
                output_path=tmp_path / "payload.json",
                scratch=SimpleNamespace(request_dir=tmp_path),
            )
        )

    assert error.value.code == "archive_quota_exceeded"
    assert "vertex_limit_exceeded" in error.value.details


@pytest.mark.parametrize(
    ("entries", "point_count_offset", "deleted"),
    [
        (build_multipoint_dataset(prefix="oversize-multipoint"), 144, False),
        (
            build_multipart_dataset(
                prefix="oversize-multipart",
                shape_type=3,
                parts=[[(0.0, 0.0), (1.0, 1.0)]],
            ),
            148,
            True,
        ),
    ],
)
def test_rust_cli_rejects_declared_vertex_limit_before_geometry_allocation(
    tmp_path: Path,
    entries: dict[str, bytes],
    point_count_offset: int,
    deleted: bool,
) -> None:
    shp_name = next(name for name in entries if name.endswith(".shp"))
    shp = bytearray(entries[shp_name])
    struct.pack_into("<I", shp, point_count_offset, 101)
    entries[shp_name] = bytes(shp)
    if deleted:
        dbf_name = next(name for name in entries if name.endswith(".dbf"))
        dbf = bytearray(entries[dbf_name])
        header_length = struct.unpack_from("<H", dbf, 8)[0]
        dbf[header_length] = ord("*")
        entries[dbf_name] = bytes(dbf)
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path)

    assert result.returncode == 5
    assert not output_path.exists()
    assert not list(tmp_path.glob("payload.tmp.*"))


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


def test_rust_cli_address_space_limit_fails_closed(tmp_path: Path) -> None:
    entries = build_repeated_point_dataset(record_count=50_000, prefix="memory")
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(
        tmp_path,
        shp_path,
        output_path,
        **{
            "max-input-bytes": 100 * 1024 * 1024,
            "max-payload-bytes": 100 * 1024 * 1024,
            "max-features": 100_000,
            "max-memory-bytes": 1024 * 1024,
        },
    )

    assert result.returncode == -signal.SIGABRT
    assert not output_path.exists()
    assert not list(tmp_path.glob("payload.tmp.*"))


def test_rust_cli_cpu_limit_fails_closed(tmp_path: Path) -> None:
    entries = build_repeated_point_dataset(record_count=235_000, prefix="cpu")
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(
        tmp_path,
        shp_path,
        output_path,
        **{
            "max-input-bytes": 100 * 1024 * 1024,
            "max-payload-bytes": 100 * 1024 * 1024,
            "max-features": 300_000,
            "max-memory-bytes": 384 * 1024 * 1024,
            "max-cpu-seconds": 1,
        },
    )

    assert result.returncode == -signal.SIGKILL
    assert not output_path.exists()
    assert not list(tmp_path.glob("payload.tmp.*"))


def test_rust_cli_feature_limit_has_dedicated_exit_and_no_output(tmp_path: Path) -> None:
    shp_path = _write_dataset(tmp_path, _two_point_dataset())
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path, **{"max-features": 1})

    assert result.returncode == 4
    assert not output_path.exists()


def test_repeated_point_fixture_reproduces_feature_ceiling(tmp_path: Path) -> None:
    entries = build_repeated_point_dataset(record_count=101, prefix="ceiling")
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(
        tmp_path,
        shp_path,
        output_path,
        **{"max-features": 100},
    )

    assert result.returncode == 4
    assert not output_path.exists()
    assert not list(tmp_path.glob("payload.tmp.*"))


def test_rust_cli_rejects_extra_shp_record_not_indexed_by_shx_or_dbf(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="misaligned")
    shp = bytearray(entries["misaligned.shp"])
    extra_record = bytearray(shp[100:])
    struct.pack_into(">I", extra_record, 0, 2)
    shp.extend(extra_record)
    struct.pack_into(">I", shp, 24, len(shp) // 2)
    entries["misaligned.shp"] = bytes(shp)
    shp_path = _write_dataset(tmp_path, entries)

    result = _run_cli(tmp_path, shp_path, tmp_path / "payload.json")

    assert result.returncode == 1
    assert not (tmp_path / "payload.json").exists()


def test_rust_cli_rejects_shx_offset_mismatch(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="bad-index")
    shx = bytearray(entries["bad-index.shx"])
    struct.pack_into(">I", shx, 100, 51)
    entries["bad-index.shx"] = bytes(shx)
    shp_path = _write_dataset(tmp_path, entries)

    result = _run_cli(tmp_path, shp_path, tmp_path / "payload.json")

    assert result.returncode == 1
    assert not (tmp_path / "payload.json").exists()


def test_rust_cli_rejects_duplicate_dbf_field_names(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="duplicates")
    entries["duplicates.dbf"] = _dbf_bytes(
        [("NAME", "C", 5, 0, b"first"), ("name", "C", 6, 0, b"second")]
    )
    shp_path = _write_dataset(tmp_path, entries)

    result = _run_cli(tmp_path, shp_path, tmp_path / "payload.json")

    assert result.returncode == 1
    assert not (tmp_path / "payload.json").exists()


def test_rust_cli_preserves_wide_integral_dbf_as_finite_number(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="wide-number")
    entries["wide-number.dbf"] = _dbf_bytes(
        [("VALUE", "N", 20, 0, b"12345678901234567890")]
    )
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path)

    assert result.returncode == 0, result.stderr
    assert json.loads(output_path.read_text(encoding="utf-8"))["properties"] == [
        {"VALUE": 1.2345678901234567e19}
    ]


def test_rust_cli_handles_deleted_dbf_record_without_misalignment(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="deleted")
    entries["deleted.dbf"] = _dbf_bytes(
        [("NAME", "C", 10, 0, b"deleted")],
        deleted=True,
    )
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["properties"] == []
    assert payload["geometries"] == []


def test_rust_cli_rejects_unsupported_dbf_language_driver(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="unsupported-ldid")
    dbf = bytearray(entries["unsupported-ldid.dbf"])
    dbf[29] = 0x01
    entries["unsupported-ldid.dbf"] = bytes(dbf)
    shp_path = _write_dataset(tmp_path, entries)

    result = _run_cli(tmp_path, shp_path, tmp_path / "payload.json")

    assert result.returncode == 1


@pytest.mark.parametrize(("raw", "expected"), [(b"T", True), (b"0", False), (b"?", None)])
def test_rust_cli_parses_dbf_logical_values(
    tmp_path: Path,
    raw: bytes,
    expected: bool | None,
) -> None:
    entries = build_minimal_point_dataset(prefix="logical")
    entries["logical.dbf"] = _dbf_bytes([("ACTIVE", "L", 1, 0, raw)])

    payload = _parse_direct(tmp_path, entries)

    assert payload["properties"] == [{"ACTIVE": expected}]


@pytest.mark.parametrize(
    ("prefix", "language_driver", "encoded", "expected"),
    [
        ("cp1251", 0xC9, "тест".encode("cp1251"), "тест"),
        ("cp1250", 0xC8, "český".encode("cp1250"), "český"),
    ],
)
def test_rust_cli_decodes_supported_dbf_language_driver(
    tmp_path: Path,
    prefix: str,
    language_driver: int,
    encoded: bytes,
    expected: str,
) -> None:
    entries = build_minimal_point_dataset(prefix=prefix)
    entries[f"{prefix}.dbf"] = _dbf_bytes(
        [("NAME", "C", 8, 0, encoded)],
        language_driver=language_driver,
    )

    payload = _parse_direct(tmp_path, entries)

    assert payload["properties"] == [{"NAME": expected}]


def test_rust_cli_rejects_paths_outside_request_root(tmp_path: Path) -> None:
    request_root = tmp_path / "request"
    request_root.mkdir()
    dataset_root = tmp_path / "outside"
    dataset_root.mkdir()
    shp_path = _write_dataset(dataset_root, build_minimal_point_dataset(prefix="outside"))

    outside_input = _run_cli(request_root, shp_path, request_root / "payload.json")
    escaping_output = _run_cli(
        dataset_root,
        shp_path,
        tmp_path / "escaping-payload.json",
    )

    assert outside_input.returncode == 2
    assert escaping_output.returncode == 2


def test_rust_cli_rejects_symlinked_required_sidecar(tmp_path: Path) -> None:
    entries = build_minimal_point_dataset(prefix="linked")
    shp_path = _write_dataset(tmp_path, entries)
    real_dbf = tmp_path / "real.dbf"
    (tmp_path / "linked.dbf").replace(real_dbf)
    (tmp_path / "linked.dbf").symlink_to(real_dbf)

    result = _run_cli(tmp_path, shp_path, tmp_path / "payload.json")

    assert result.returncode == 1
    assert not (tmp_path / "payload.json").exists()


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


def test_rust_cli_rejects_malformed_multipart_offset(tmp_path: Path) -> None:
    entries = build_multipart_dataset(
        prefix="bad-parts",
        shape_type=3,
        parts=[[(0.0, 0.0), (1.0, 1.0)], [(2.0, 0.0), (3.0, 1.0)]],
    )
    shp = bytearray(entries["bad-parts.shp"])
    # First part must begin at point zero; offset one makes the record ambiguous.
    struct.pack_into("<i", shp, 152, 1)
    entries["bad-parts.shp"] = bytes(shp)
    shp_path = _write_dataset(tmp_path, entries)
    output_path = tmp_path / "payload.json"

    result = _run_cli(tmp_path, shp_path, output_path)

    assert result.returncode == 1
    assert not output_path.exists()


def test_rust_cli_command_receives_every_resource_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_command: list[str] = []

    class Process:
        pid = 123
        returncode = 0

        async def wait(self):
            return self.returncode

    async def fake_exec(*command, **_kwargs):  # noqa: ANN001
        captured_command.extend(command)
        return Process()

    monkeypatch.setattr(convert.asyncio, "create_subprocess_exec", fake_exec)
    asyncio.run(
        convert._run_parser_worker(
            shp_path=tmp_path / "sample.shp",
            output_path=tmp_path / "payload.json",
            scratch=SimpleNamespace(request_dir=tmp_path),
        )
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


def test_parser_cancellation_terminates_real_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = tmp_path / "blocking-parser"
    parser.write_text(
        "#!/bin/sh\nsleep 60 &\nchild=$!\nprintf '%s %s\\n' $$ \"$child\" > parser-pids\nwait\n",
        encoding="utf-8",
    )
    parser.chmod(0o755)
    monkeypatch.setenv("SHAPE_CONVERTER_PARSER_CLI", str(parser))

    async def _exercise() -> tuple[int, int]:
        task = asyncio.create_task(
            convert._run_parser_worker(
                shp_path=tmp_path / "sample.shp",
                output_path=tmp_path / "payload.json",
                scratch=SimpleNamespace(request_dir=tmp_path),
            )
        )
        pid_file = tmp_path / "parser-pids"
        for _ in range(100):
            if pid_file.exists():
                break
            await asyncio.sleep(0.01)
        assert pid_file.exists()
        parent_pid, child_pid = (int(value) for value in pid_file.read_text().split())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return parent_pid, child_pid

    parent_pid, child_pid = asyncio.run(_exercise())

    def _running(pid: int) -> bool:
        stat_path = Path(f"/proc/{pid}/stat")
        try:
            state = stat_path.read_text(encoding="utf-8").split()[2]
        except (FileNotFoundError, ProcessLookupError):
            return False
        return state != "Z"

    assert not _running(parent_pid)
    assert not _running(child_pid)
    assert not (tmp_path / "payload.json").exists()
    assert not list(tmp_path.glob("payload.tmp.*"))


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

    tampered_sidecar = dict(payload)
    tampered_source = dict(payload["source"])
    tampered_source["manifest_sha256"] = "0" * 64
    tampered_sidecar["source"] = tampered_source
    sidecar.write_text(json.dumps(tampered_sidecar), encoding="utf-8")
    invalid_manifest = subprocess.run(
        [sys.executable, str(validator), "--binary", str(binary), "--sidecar", str(sidecar)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid_manifest.returncode != 0
    assert "manifest digest mismatch" in invalid_manifest.stderr
    assert validate_parser_executable(binary) == (False, "parser_provenance_contract_invalid")
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

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
