"""Deterministic M0 evidence generator; never imported by production code.

Run with the existing WEPPpy venv (PyArrow 16.1.0, Shapely 2.0.4). PyArrow is
only a trusted fixture writer/oracle. Hostile cases use a tiny compact-protocol
*writer*, not a Python parser or a proposed runtime dependency.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import CRS, Transformer
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping
from shapely.wkb import dumps

ROOT = Path(__file__).resolve().parent
I32, I64, BINARY, LIST, STRUCT = 5, 6, 8, 9, 12


def varint(value: int) -> bytes:
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def integer(value: int) -> bytes:
    return varint(value * 2 if value >= 0 else -value * 2 - 1)


def binary(value: str | bytes) -> bytes:
    value = value.encode() if isinstance(value, str) else value
    return varint(len(value)) + value


def sequence(kind: int, values: list[bytes]) -> bytes:
    head = bytes([(min(len(values), 15) << 4) | kind])
    return head + (varint(len(values)) if len(values) >= 15 else b"") + b"".join(values)


def record(fields: list[tuple[int, int, bytes]]) -> bytes:
    result = bytearray()
    previous = 0
    for field_id, kind, value in sorted(fields):
        delta = field_id - previous
        result.extend(bytes([(delta << 4) | kind]) if 0 < delta < 16 else bytes([kind]) + integer(field_id))
        result.extend(value)
        previous = field_id
    result.append(0)
    return bytes(result)


def geo_metadata(version: str = "1.1.0", **column: object) -> dict:
    return {"version": version, "primary_column": "geometry", "columns": {
        "geometry": {"encoding": "WKB", "geometry_types": ["Polygon"], **column}}}


def manual_file(wkb: bytes, *, codec: int = 0, declared_size: int | None = None,
                body: bytes | None = None, encoding: int = 0, count: int = 1,
                v2_rows: int | None = None,
                v2_is_compressed: bool | None = None,
                external: bool = False, encrypted_column: bool = False,
                encrypted_footer: bool = False, dictionary: bool = False,
                header_extra: bytes = b"", footer_override: bytes | None = None) -> bytes:
    """Emit one required BYTE_ARRAY column, one row group, one page.

    Optional contradictions are intentional and named in the fixture manifest.
    The ordinary emitted file is verified with an independent PyArrow readback.
    """
    decoded = struct.pack("<I", len(wkb)) + wkb
    page_body = decoded if body is None else body
    if codec == 1:
        page_body = bytes(pa.Codec("snappy").compress(page_body))
    if v2_rows is not None:
        details = [(1, I32, integer(count)), (2, I32, integer(0)),
                   (3, I32, integer(v2_rows)), (4, I32, integer(encoding)),
                   (5, I32, integer(0)), (6, I32, integer(0)),
                   (7, 1 if (codec != 0 if v2_is_compressed is None else v2_is_compressed) else 2, b"")]
        page_type = 3
        detail_field = 8
    else:
        details = [(1, I32, integer(count)), (2, I32, integer(encoding))]
        if not dictionary:
            details += [(3, I32, integer(3)), (4, I32, integer(3))]
        page_type = 2 if dictionary else 0
        detail_field = 7 if dictionary else 5
    header = record([
        (1, I32, integer(page_type)),
        (2, I32, integer(len(decoded) if declared_size is None else declared_size)),
        (3, I32, integer(len(page_body))),
        (detail_field, STRUCT, record(details)),
    ])
    if header_extra:
        # Field 15 (unknown optional binary) inserted before the struct STOP.
        header = header[:-1] + bytes([BINARY]) + integer(15) + header_extra + b"\0"
    total = len(header) + len(page_body)
    uncompressed_total = len(header) + (len(decoded) if declared_size is None else declared_size)
    column_meta = record([
        (1, I32, integer(6)),
        (2, LIST, sequence(I32, [integer(encoding), integer(3)])),
        (3, LIST, sequence(BINARY, [binary("geometry")])),
        (4, I32, integer(codec)), (5, I64, integer(1)),
        (6, I64, integer(uncompressed_total)), (7, I64, integer(total)),
        (11 if dictionary else 9, I64, integer(4)),
        *([(9, I64, integer(4))] if dictionary else []),
    ])
    column_fields = [(2, I64, integer(4)), (3, STRUCT, column_meta)]
    if external:
        column_fields.append((1, BINARY, binary("/tmp/vector-must-never-open.parquet")))
    if encrypted_column:
        column_fields.append((8, STRUCT, record([(1, STRUCT, record([]))])))
    schema = [record([(4, BINARY, binary("schema")), (5, I32, integer(1))]),
              record([(1, I32, integer(6)), (3, I32, integer(0)), (4, BINARY, binary("geometry"))])]
    footer_fields = [
        (1, I32, integer(1)), (2, LIST, sequence(STRUCT, schema)),
        (3, I64, integer(1)),
        (4, LIST, sequence(STRUCT, [record([
            (1, LIST, sequence(STRUCT, [record(column_fields)])),
            (2, I64, integer(total)), (3, I64, integer(1)),
        ])])),
        (5, LIST, sequence(STRUCT, [record([
            (1, BINARY, binary("geo")),
            (2, BINARY, binary(json.dumps(geo_metadata(), separators=(",", ":")))),
        ])])),
        (6, BINARY, binary("wepppy-m0-fixtures-v1")),
    ]
    if encrypted_footer:
        footer_fields.append((8, STRUCT, record([(1, STRUCT, record([]))])))
    footer = record(footer_fields) if footer_override is None else footer_override
    return b"PAR1" + header + page_body + footer + struct.pack("<I", len(footer)) + b"PAR1"


def arrow_file(wkbs: list[bytes | None], *, metadata: dict | None = None,
               properties: dict | None = None, codec: str = "snappy",
               dictionary: bool = False, extra_metadata: dict | None = None,
               page_encoding: str | None = None, row_group_size: int | None = None) -> bytes:
    props = {"field_id": list(range(1, len(wkbs) + 1)), "label": ["fixture"] * len(wkbs)} if properties is None else properties
    table = pa.table({"geometry": pa.array(wkbs, type=pa.binary()), **props})
    meta = {} if metadata is None else {b"geo": json.dumps(metadata, separators=(",", ":")).encode()}
    meta = {**meta, **(extra_metadata or {})}
    table = table.replace_schema_metadata(meta)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression=codec, use_dictionary=dictionary,
                   write_statistics=False, store_schema=True, version="1.0",
                   data_page_version="1.0", column_encoding=page_encoding,
                   row_group_size=row_group_size)
    data = sink.getvalue().to_pybytes()
    # In PyArrow 16, store_schema=False drops *all* key/value metadata, including
    # geo. Remove only the known serialized Arrow schema from this trusted writer
    # output. This is not a reader for attacker input: exact encoded bytes and a
    # unique footer occurrence are required, followed by independent readback.
    written = pq.read_metadata(pa.BufferReader(data)).metadata
    original_items = [*meta.items(), (b"ARROW:schema", written[b"ARROW:schema"])]

    def key_values(items: list) -> bytes:
        return sequence(STRUCT, [record([(1, BINARY, binary(key)), (2, BINARY, binary(value))])
                                 for key, value in items])

    footer_size = struct.unpack("<I", data[-8:-4])[0]
    footer = data[-8 - footer_size:-8]
    original = key_values(original_items)
    assert footer.count(original) == 1, "trusted writer metadata layout changed"
    footer = footer.replace(original, key_values(list(meta.items())), 1)
    result = data[:-8 - footer_size] + footer + struct.pack("<I", len(footer)) + b"PAR1"
    assert (pq.read_metadata(pa.BufferReader(result)).metadata or {}) == meta
    return result


def main() -> None:
    polygon = Polygon([(-116, 44), (-115.9, 44), (-115.9, 44.1), (-116, 44.1), (-116, 44)])
    line = LineString([(-116, 44), (-115.9, 44.1), (-115.8, 44.05)])
    geometries = {"polygon": polygon, "line": line, "multipolygon": MultiPolygon([polygon]), "point": Point(-116, 44)}
    entries = []

    def save(name: str, data: bytes, category: str, outcome: str, **extra: object) -> None:
        path = ROOT / name
        path.write_bytes(data)
        entries.append({"file": name, "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data), "category": category, "expected": outcome, **extra})

    for name, geometry in geometries.items():
        payload = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
            "field_id": 1, "label": "fixture"}, "geometry": mapping(geometry)}]}
        expected = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        save(f"{name}.geojson", expected, "workflow-control", "workflow-specific",
             workflows=["roads"] if name == "line" else ["agfields", "omni", "batch"] if name != "point" else [])
        for version, codec in [("1.0.0", "NONE"), ("1.1.0", "snappy")]:
            meta = geo_metadata(version, geometry_types=[geometry.geom_type])
            data = arrow_file([dumps(geometry)], metadata=meta, codec=codec)
            # Read only trusted controls. Malformed files are never sent to this oracle.
            readback = pq.read_table(pa.BufferReader(data)).to_pydict()
            assert readback["geometry"] == [dumps(geometry)]
            assert readback["field_id"] == [1]
            assert json.loads(pq.read_metadata(pa.BufferReader(data)).metadata[b"geo"]) == meta
            save(f"{name}-{version}-{codec.lower()}.parquet", data, "valid", "convert",
                 semantic_oracle=f"{name}.geojson", crs="CRS84 (absent metadata)")

    wkb = dumps(polygon)
    valid = arrow_file([wkb], metadata=geo_metadata())
    rejects = [
        ("missing-geo", arrow_file([wkb]), "metadata"),
        ("version-unsupported", arrow_file([wkb], metadata=geo_metadata("0.4.0")), "metadata"),
        ("crs-null", arrow_file([wkb], metadata=geo_metadata(crs=None)), "crs"),
        ("crs-invalid", arrow_file([wkb], metadata=geo_metadata(crs={"type": "NotACRS"})), "crs"),
        ("encoding-geoarrow", arrow_file([wkb], metadata=geo_metadata(encoding="polygon")), "metadata"),
        ("primary-column-missing", arrow_file([wkb], metadata={**geo_metadata(), "primary_column": "missing"}), "schema"),
        ("nested-properties", arrow_file([wkb], metadata=geo_metadata(), properties={"field_id": [1], "nested": [[1, 2]]}), "schema"),
        ("schema-columns", arrow_file([wkb], metadata=geo_metadata(), properties={f"c{i}": [i] for i in range(65)}), "schema-budget"),
        ("extension-metadata", arrow_file([wkb], metadata=geo_metadata(), extra_metadata={b"ARROW:extension:name": b"untrusted.extension"}), "extension"),
        ("codec-gzip", arrow_file([wkb], metadata=geo_metadata(), codec="gzip"), "codec"),
        ("encoding-delta", arrow_file([wkb], metadata=geo_metadata(), properties={}, page_encoding="DELTA_LENGTH_BYTE_ARRAY"), "encoding"),
        ("wkb-truncated", arrow_file([wkb[:12]], metadata=geo_metadata()), "wkb"),
        ("wkb-count-bomb", arrow_file([b"\x01" + struct.pack("<II", 2, 0x7fffffff)], metadata=geo_metadata(geometry_types=["LineString"])), "wkb-budget"),
        ("wkb-nesting", arrow_file([(b"\x01" + struct.pack("<II", 7, 1)) * 20 + dumps(Point(0, 0))], metadata=geo_metadata(geometry_types=["GeometryCollection"])), "wkb-depth"),
        ("coordinates-nonfinite", arrow_file([b"\x01" + struct.pack("<Idd", 1, float("inf"), 44)], metadata=geo_metadata(geometry_types=["Point"])), "nonfinite"),
        ("property-nonfinite", arrow_file([wkb], metadata=geo_metadata(), properties={"field_id": [1], "value": [float("inf")]}), "nonfinite"),
        ("magic-head", b"NOPE" + valid[4:], "magic"),
        ("magic-tail", valid[:-4] + b"NOPE", "magic"),
        ("encrypted-pare", b"PARE" + valid[4:-4] + b"PARE", "encryption"),
        ("footer-truncated", valid[:-12], "footer"),
        ("footer-size-bomb", valid[:-8] + struct.pack("<I", 0x7fffffff) + b"PAR1", "footer-budget"),
        ("footer-list-bomb", manual_file(wkb, footer_override=bytes([0x15, 0x02, 0x19, 0xfc, 0xff, 0xff, 0xff, 0xff, 0x07])), "metadata-budget"),
        ("external-path", manual_file(wkb, external=True), "external"),
        ("encrypted-column", manual_file(wkb, encrypted_column=True), "encryption"),
        ("encrypted-footer-metadata", manual_file(wkb, encrypted_footer=True), "encryption"),
        ("page-declared-expansion", manual_file(wkb, codec=1, declared_size=0x7fffffff), "page-budget"),
        ("page-actual-expansion", manual_file(wkb, codec=1, declared_size=4, body=b"\0" * 32768), "decompression"),
        ("page-value-count", manual_file(wkb, count=0x7fffffff), "page-budget"),
        ("dictionary-value-count", manual_file(wkb, count=0x7fffffff, dictionary=True), "dictionary-budget"),
        ("page-header-string-bomb", manual_file(wkb, header_extra=varint(0x7fffffff)), "header-budget"),
    ]
    for name, data, category in rejects:
        save(name + ".parquet", data, category, "reject")
    plain = manual_file(wkb)
    assert pq.read_table(pa.BufferReader(plain)).to_pydict()["geometry"] == [wkb]
    save("manual-plain-control.parquet", plain, "valid", "convert", note="geometry only; AgFields must reject missing field_id")
    dictionary = arrow_file([wkb, wkb], metadata=geo_metadata(), dictionary=True)
    assert pq.read_table(pa.BufferReader(dictionary)).num_rows == 2
    save("dictionary-control.parquet", dictionary, "valid", "convert", expected_rows=2)
    v2 = manual_file(wkb, v2_rows=1)
    assert pq.read_table(pa.BufferReader(v2)).to_pydict()["geometry"] == [wkb]
    save("data-page-v2-control.parquet", v2, "valid-v2", "convert", expected_rows=1)
    save("data-page-v2-row-mismatch.parquet", manual_file(wkb, v2_rows=2),
         "v2-row-count", "reject")
    compressed_v2 = manual_file(wkb, codec=1, v2_rows=1)
    assert pq.read_table(pa.BufferReader(compressed_v2)).to_pydict()["geometry"] == [wkb]
    save("data-page-v2-snappy-control.parquet", compressed_v2,
         "valid-v2-snappy", "convert", expected_rows=1)
    save("data-page-v2-snappy-flag-mismatch.parquet",
         manual_file(wkb, codec=1, v2_rows=1, v2_is_compressed=False),
         "v2-compression-flag", "reject")
    multiple_row_groups = arrow_file([wkb, wkb], metadata=geo_metadata(), row_group_size=1)
    assert pq.read_metadata(pa.BufferReader(multiple_row_groups)).num_row_groups == 2
    save("multiple-row-groups-control.parquet", multiple_row_groups,
         "row-group-control", "convert", expected_rows=2, expected_row_groups=2)
    projected_xy = Transformer.from_crs(4326, 32611, always_xy=True).transform(-116, 44)
    projected_point = dumps(Point(*projected_xy))
    projected_metadata = geo_metadata(
        geometry_types=["Point"], crs=CRS.from_epsg(32611).to_json_dict()
    )
    save(
        "projected-crs-control.parquet",
        arrow_file([projected_point], metadata=projected_metadata),
        "projected-crs-control",
        "convert",
        expected_wgs84=[-116.0, 44.0],
    )
    missing_grid_metadata = geo_metadata(
        geometry_types=["Point"], crs=CRS.from_epsg(4746).to_json_dict()
    )
    save(
        "missing-grid-crs.parquet",
        arrow_file([dumps(Point(-149.5, -17.5))], metadata=missing_grid_metadata),
        "workflow-rejection",
        "workflow-rejection",
        note="Rust parser accepts data; shape-converter rejects unavailable best offline grid.",
    )
    save("null-geometry.parquet", arrow_file([None], metadata=geo_metadata(geometry_types=[])),
         "all-null-geometry", "reject", note="Parser rejects all-null input: finite observed bounds are required")
    save("mixed-polygon-point.parquet", arrow_file([wkb, dumps(Point(-116, 44))],
         metadata=geo_metadata(geometry_types=["Polygon", "Point"])), "workflow-rejection", "batch/agfields/omni reject before replacement")
    manifest = {"schema": "vector-upload-red-fixtures-v1", "generator": "generate_fixtures.py",
                "writer": {"pyarrow": pa.__version__}, "fixtures": entries,
                "note": "Expected outcomes are acceptance assertions, not observed candidate results."}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"fixtures": len(entries), "total_bytes": sum(e["bytes"] for e in entries)}))


if __name__ == "__main__":
    main()
