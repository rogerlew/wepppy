from __future__ import annotations

import datetime as dt
import io
import struct
import zipfile
from pathlib import Path


WGS84_PRJ_TEXT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",'
    'SPHEROID["WGS 84",6378137,298.257223563],'
    'AUTHORITY["EPSG","6326"]],'
    'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
    'AUTHORITY["EPSG","4326"]]'
)


def build_minimal_point_dataset(
    prefix: str = "sample",
    *,
    include_prj: bool = True,
    x_coord: float = 10.0,
    y_coord: float = 20.0,
    prj_text: str | None = None,
) -> dict[str, bytes]:
    """Build a tiny valid shapefile sidecar set for tests."""

    shp_bytes = _build_point_shp(x_coord=x_coord, y_coord=y_coord)
    shx_bytes = _build_point_shx(x_coord=x_coord, y_coord=y_coord)
    dbf_bytes = _build_dbf_one_text_field(field_name="NAME", value="demo")

    entries: dict[str, bytes] = {
        f"{prefix}.shp": shp_bytes,
        f"{prefix}.shx": shx_bytes,
        f"{prefix}.dbf": dbf_bytes,
    }
    if include_prj:
        entries[f"{prefix}.prj"] = (prj_text or WGS84_PRJ_TEXT).encode("utf-8")
    return entries


def build_minimal_line_dataset(
    prefix: str = "sample_line",
    *,
    include_prj: bool = True,
    points: list[tuple[float, float]] | None = None,
    prj_text: str | None = None,
) -> dict[str, bytes]:
    """Build a tiny polyline shapefile sidecar set for tests."""

    active_points = points or [(10.0, 20.0), (11.0, 21.0), (12.0, 21.0)]
    shp_bytes, shx_bytes = _build_polyline_sidecars(active_points, shape_type=3)
    dbf_bytes = _build_dbf_one_text_field(field_name="NAME", value="line")

    entries: dict[str, bytes] = {
        f"{prefix}.shp": shp_bytes,
        f"{prefix}.shx": shx_bytes,
        f"{prefix}.dbf": dbf_bytes,
    }
    if include_prj:
        entries[f"{prefix}.prj"] = (prj_text or WGS84_PRJ_TEXT).encode("utf-8")
    return entries


def build_minimal_polygon_dataset(
    prefix: str = "sample_polygon",
    *,
    include_prj: bool = True,
    ring: list[tuple[float, float]] | None = None,
    prj_text: str | None = None,
) -> dict[str, bytes]:
    """Build a tiny polygon shapefile sidecar set for tests."""

    active_ring = ring or [
        (10.0, 20.0),
        (11.0, 20.0),
        (11.0, 21.0),
        (10.0, 21.0),
        (10.0, 20.0),
    ]
    shp_bytes, shx_bytes = _build_polyline_sidecars(active_ring, shape_type=5)
    dbf_bytes = _build_dbf_one_text_field(field_name="NAME", value="poly")

    entries: dict[str, bytes] = {
        f"{prefix}.shp": shp_bytes,
        f"{prefix}.shx": shx_bytes,
        f"{prefix}.dbf": dbf_bytes,
    }
    if include_prj:
        entries[f"{prefix}.prj"] = (prj_text or WGS84_PRJ_TEXT).encode("utf-8")
    return entries


def build_zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for arcname, content in entries.items():
            archive.writestr(arcname, content)
    return buffer.getvalue()


def write_zip_file(path: Path, entries: dict[str, bytes]) -> Path:
    path.write_bytes(build_zip_bytes(entries))
    return path


def mark_zip_as_encrypted(zip_bytes: bytes) -> bytes:
    """Patch zip headers to set encrypted bit on first local and central headers."""

    patched = bytearray(zip_bytes)
    local_sig = b"PK\x03\x04"
    central_sig = b"PK\x01\x02"

    local_offset = patched.find(local_sig)
    central_offset = patched.find(central_sig)
    if local_offset == -1 or central_offset == -1:
        return bytes(patched)

    patched[local_offset + 6 : local_offset + 8] = b"\x01\x00"
    patched[central_offset + 8 : central_offset + 10] = b"\x01\x00"
    return bytes(patched)


def _build_point_shp(*, x_coord: float, y_coord: float) -> bytes:
    record_content = struct.pack("<i2d", 1, x_coord, y_coord)
    record_header = struct.pack(">2i", 1, len(record_content) // 2)
    body = record_header + record_content

    file_length_words = (100 + len(body)) // 2
    header = _build_shp_header(file_length_words=file_length_words, shape_type=1, bbox=(x_coord, y_coord, x_coord, y_coord))
    return header + body


def _build_point_shx(*, x_coord: float, y_coord: float) -> bytes:
    index_record = struct.pack(">2i", 50, 10)
    file_length_words = (100 + len(index_record)) // 2
    header = _build_shp_header(
        file_length_words=file_length_words,
        shape_type=1,
        bbox=(x_coord, y_coord, x_coord, y_coord),
    )
    return header + index_record


def _build_polyline_sidecars(points: list[tuple[float, float]], *, shape_type: int) -> tuple[bytes, bytes]:
    if len(points) < 2:
        raise ValueError("At least two points are required.")

    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    bbox = (min(x_values), min(y_values), max(x_values), max(y_values))

    points_payload = b"".join(struct.pack("<2d", x_coord, y_coord) for x_coord, y_coord in points)
    record_content = (
        struct.pack("<i4d2i", shape_type, *bbox, 1, len(points))
        + struct.pack("<i", 0)
        + points_payload
    )
    record_header = struct.pack(">2i", 1, len(record_content) // 2)
    body = record_header + record_content

    shp_file_length_words = (100 + len(body)) // 2
    shp_header = _build_shp_header(
        file_length_words=shp_file_length_words,
        shape_type=shape_type,
        bbox=bbox,
    )

    shx_record = struct.pack(">2i", 50, len(record_content) // 2)
    shx_file_length_words = (100 + len(shx_record)) // 2
    shx_header = _build_shp_header(
        file_length_words=shx_file_length_words,
        shape_type=shape_type,
        bbox=bbox,
    )

    return shp_header + body, shx_header + shx_record


def _build_shp_header(*, file_length_words: int, shape_type: int, bbox: tuple[float, float, float, float]) -> bytes:
    header = bytearray(100)
    struct.pack_into(">i", header, 0, 9994)
    struct.pack_into(">i", header, 24, file_length_words)
    struct.pack_into("<i", header, 28, 1000)
    struct.pack_into("<i", header, 32, shape_type)
    struct.pack_into("<4d", header, 36, *bbox)
    struct.pack_into("<4d", header, 68, 0.0, 0.0, 0.0, 0.0)
    return bytes(header)


def _build_dbf_one_text_field(*, field_name: str, value: str) -> bytes:
    field_length = 10
    record_count = 1
    header_length = 32 + 32 + 1
    record_length = 1 + field_length

    now = dt.datetime.now(dt.UTC)
    year = now.year - 1900

    header = bytearray(32)
    header[0] = 0x03
    header[1] = year & 0xFF
    header[2] = now.month
    header[3] = now.day
    struct.pack_into("<I", header, 4, record_count)
    struct.pack_into("<H", header, 8, header_length)
    struct.pack_into("<H", header, 10, record_length)

    field_descriptor = bytearray(32)
    encoded_name = field_name.encode("ascii", errors="ignore")[:10]
    field_descriptor[: len(encoded_name)] = encoded_name
    field_descriptor[11] = ord("C")
    field_descriptor[16] = field_length
    field_descriptor[17] = 0

    record = bytearray(record_length)
    record[0] = ord(" ")
    encoded_value = value.encode("ascii", errors="ignore")[:field_length]
    record[1 : 1 + len(encoded_value)] = encoded_value
    for idx in range(1 + len(encoded_value), record_length):
        record[idx] = ord(" ")

    return bytes(header + field_descriptor + b"\r" + record + b"\x1A")
