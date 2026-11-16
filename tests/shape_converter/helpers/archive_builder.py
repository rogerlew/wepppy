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

SENSITIVE_METADATA_MARKERS = (
    "alice.private@example.test",
    "/Users/alice/private/workspace",
    "+1-555-0109",
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


def build_repeated_point_dataset(
    *,
    record_count: int,
    prefix: str = "repeated_points",
    include_prj: bool = True,
) -> dict[str, bytes]:
    """Build a deterministic large point fixture for ceiling/recovery probes."""

    if record_count < 1:
        raise ValueError("record_count must be positive")
    record_content = struct.pack("<i2d", 1, 10.0, 20.0)
    content_words = len(record_content) // 2
    shp_body = bytearray()
    shx_body = bytearray()
    next_offset_words = 50
    for record_number in range(1, record_count + 1):
        shp_body.extend(struct.pack(">2i", record_number, content_words))
        shp_body.extend(record_content)
        shx_body.extend(struct.pack(">2i", next_offset_words, content_words))
        next_offset_words += 4 + content_words
    bbox = (10.0, 20.0, 10.0, 20.0)
    shp = _build_shp_header(
        file_length_words=(100 + len(shp_body)) // 2,
        shape_type=1,
        bbox=bbox,
    ) + bytes(shp_body)
    shx = _build_shp_header(
        file_length_words=(100 + len(shx_body)) // 2,
        shape_type=1,
        bbox=bbox,
    ) + bytes(shx_body)
    base_dbf = _build_dbf_one_text_field(field_name="NAME", value="demo")
    header_length = struct.unpack_from("<H", base_dbf, 8)[0]
    record_length = struct.unpack_from("<H", base_dbf, 10)[0]
    record = base_dbf[header_length : header_length + record_length]
    dbf_header = bytearray(base_dbf[:header_length])
    struct.pack_into("<I", dbf_header, 4, record_count)
    entries = {
        f"{prefix}.shp": shp,
        f"{prefix}.shx": shx,
        f"{prefix}.dbf": bytes(dbf_header) + record * record_count + b"\x1a",
    }
    if include_prj:
        entries[f"{prefix}.prj"] = WGS84_PRJ_TEXT.encode("utf-8")
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


def build_shape_dataset(
    *,
    prefix: str,
    shape_type: int,
    record_content: bytes,
    bbox: tuple[float, float, float, float],
    property_value: str = "demo",
) -> dict[str, bytes]:
    """Build a one-record dataset from an explicitly encoded shape record."""

    shp_bytes, shx_bytes = _build_single_record_sidecars(
        record_content=record_content,
        shape_type=shape_type,
        bbox=bbox,
    )
    return {
        f"{prefix}.shp": shp_bytes,
        f"{prefix}.shx": shx_bytes,
        f"{prefix}.dbf": _build_dbf_one_text_field(
            field_name="NAME", value=property_value
        ),
    }


def build_multipart_dataset(
    *,
    prefix: str,
    shape_type: int,
    parts: list[list[tuple[float, float]]],
    measures: list[float] | None = None,
) -> dict[str, bytes]:
    """Build a PolyLine/Polygon or corresponding M-variant fixture."""

    points = [point for part in parts for point in part]
    if not parts or any(not part for part in parts):
        raise ValueError("Every multipart fixture part must contain points.")
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    bbox = (min(x_values), min(y_values), max(x_values), max(y_values))
    part_offsets: list[int] = []
    offset = 0
    for part in parts:
        part_offsets.append(offset)
        offset += len(part)
    record_content = (
        struct.pack("<i4d2i", shape_type, *bbox, len(parts), len(points))
        + b"".join(struct.pack("<i", value) for value in part_offsets)
        + b"".join(struct.pack("<2d", *point) for point in points)
    )
    if shape_type in {23, 25}:
        active_measures = measures or [float(index) for index in range(len(points))]
        if len(active_measures) != len(points):
            raise ValueError("M fixtures require one measure per point.")
        record_content += struct.pack(
            f"<{len(active_measures) + 2}d",
            min(active_measures),
            max(active_measures),
            *active_measures,
        )
    return build_shape_dataset(
        prefix=prefix,
        shape_type=shape_type,
        record_content=record_content,
        bbox=bbox,
        property_value="multipart",
    )


def build_multipoint_dataset(
    *,
    prefix: str = "multipoint",
    shape_type: int = 8,
    points: list[tuple[float, float]] | None = None,
    measures: list[float] | None = None,
) -> dict[str, bytes]:
    """Build a MultiPoint or MultiPointM fixture."""

    active_points = points or [(10.0, 20.0), (12.0, 21.0)]
    x_values = [point[0] for point in active_points]
    y_values = [point[1] for point in active_points]
    bbox = (min(x_values), min(y_values), max(x_values), max(y_values))
    record_content = (
        struct.pack("<i4di", shape_type, *bbox, len(active_points))
        + b"".join(struct.pack("<2d", *point) for point in active_points)
    )
    if shape_type == 28:
        active_measures = measures or [float(index) for index in range(len(active_points))]
        if len(active_measures) != len(active_points):
            raise ValueError("MultiPointM fixtures require one measure per point.")
        record_content += struct.pack(
            f"<{len(active_measures) + 2}d",
            min(active_measures),
            max(active_measures),
            *active_measures,
        )
    return build_shape_dataset(
        prefix=prefix,
        shape_type=shape_type,
        record_content=record_content,
        bbox=bbox,
        property_value="multipoint",
    )


def build_multipatch_dataset(
    *,
    prefix: str,
    parts: list[tuple[int, list[tuple[float, float, float]]]],
) -> dict[str, bytes]:
    """Build a MultiPatch fixture with explicit ESRI patch-family codes."""

    if not parts or any(not points for _, points in parts):
        raise ValueError("Every MultiPatch part must contain points.")
    points = [point for _, part_points in parts for point in part_points]
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    z_values = [point[2] for point in points]
    bbox = (min(x_values), min(y_values), max(x_values), max(y_values))
    offsets: list[int] = []
    offset = 0
    for _, part_points in parts:
        offsets.append(offset)
        offset += len(part_points)
    record_content = (
        struct.pack("<i4d2i", 31, *bbox, len(parts), len(points))
        + b"".join(struct.pack("<i", value) for value in offsets)
        + b"".join(struct.pack("<i", patch_type) for patch_type, _ in parts)
        + b"".join(struct.pack("<2d", x_coord, y_coord) for x_coord, y_coord, _ in points)
        + struct.pack(f"<{len(z_values) + 2}d", min(z_values), max(z_values), *z_values)
        + struct.pack(f"<{len(points) + 2}d", 0.0, 0.0, *([0.0] * len(points)))
    )
    return build_shape_dataset(
        prefix=prefix,
        shape_type=31,
        record_content=record_content,
        bbox=bbox,
        property_value="multipatch",
    )


def build_zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for arcname, content in entries.items():
            archive.writestr(arcname, content)
    return buffer.getvalue()


def build_xml_entity_expansion_payload(*, root_tag: str = "metadata") -> bytes:
    """Return an XML payload representative of entity-expansion abuse input."""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE {root_tag} [
  <!ENTITY a "aaaaaaaaaaaaaaaa">
  <!ENTITY b "&a;&a;&a;&a;">
  <!ENTITY c "&b;&b;&b;&b;">
]>
<{root_tag}>
  <creator>&c;</creator>
  <notes>&c;</notes>
</{root_tag}>
""".encode("utf-8")


def build_sensitive_metadata_payload(*, include_xml_shell: bool = True) -> bytes:
    """Return sidecar metadata bytes containing deterministic PII-like markers."""

    body = (
        f"contact={SENSITIVE_METADATA_MARKERS[0]}\n"
        f"path={SENSITIVE_METADATA_MARKERS[1]}\n"
        f"phone={SENSITIVE_METADATA_MARKERS[2]}\n"
    )
    if not include_xml_shell:
        return body.encode("utf-8")
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<metadata>\n"
        f"  <contact>{SENSITIVE_METADATA_MARKERS[0]}</contact>\n"
        f"  <path>{SENSITIVE_METADATA_MARKERS[1]}</path>\n"
        f"  <phone>{SENSITIVE_METADATA_MARKERS[2]}</phone>\n"
        "</metadata>\n"
    ).encode("utf-8")


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


def _build_single_record_sidecars(
    *,
    record_content: bytes,
    shape_type: int,
    bbox: tuple[float, float, float, float],
) -> tuple[bytes, bytes]:
    record_header = struct.pack(">2i", 1, len(record_content) // 2)
    body = record_header + record_content
    shp_header = _build_shp_header(
        file_length_words=(100 + len(body)) // 2,
        shape_type=shape_type,
        bbox=bbox,
    )
    shx_record = struct.pack(">2i", 50, len(record_content) // 2)
    shx_header = _build_shp_header(
        file_length_words=(100 + len(shx_record)) // 2,
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
