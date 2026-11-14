"""Data-only parser IPC. Limits and schema: ADR-0142 and service specification."""
from __future__ import annotations

import json
import math
import os
import stat
from pathlib import Path
from typing import NoReturn

MAX_DEPTH = 16
MAX_VALUES = 2_000_000
_KEYS = {'properties', 'geometries', 'source_bounds', 'source_crs_wkt'}
_LEVELS = {'Point': 0, 'MultiPoint': 1, 'LineString': 1, 'MultiLineString': 2,
           'Polygon': 2, 'MultiPolygon': 3}


def _scan_budget(text: str) -> None:
    """Bound allocation before decoding; JSON grammar is checked by json.loads."""
    depth = values = index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char in ' \t\r\n,:':
            index += 1
            continue
        if char in '[{':
            depth += 1
            values += 1
            if depth > MAX_DEPTH:
                raise ValueError('Parser JSON nesting limit exceeded.')
            index += 1
        elif char in ']}':
            depth -= 1
            index += 1
        elif char == '"':
            index += 1
            while index < length:
                if text[index] == '\\':
                    index += 2
                elif text[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            lookahead = index
            while lookahead < length and text[lookahead] in ' \t\r\n':
                lookahead += 1
            if lookahead == length or text[lookahead] != ':':
                values += 1
        else:
            values += 1
            while index < length and text[index] not in ' \t\r\n,]}:{["':
                index += 1
        if values > MAX_VALUES:
            raise ValueError('Parser JSON value limit exceeded.')


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate parser JSON key.')
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ValueError('Non-finite parser JSON number.')


def _number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _positions(value: object, level: int) -> int:
    if type(value) is not list:
        raise ValueError('Invalid coordinate structure.')
    if level == 0:
        if len(value) not in (2, 3) or not all(_number(item) for item in value):
            raise ValueError('Invalid coordinate position.')
        return 1
    return sum(_positions(item, level - 1) for item in value)


def _geometry_vertices(geometry: object) -> int:
    if geometry is None:
        return 0
    if type(geometry) is not dict:
        raise ValueError('Invalid geometry object.')
    kind = geometry.get('type')
    if kind == 'GeometryCollection':
        if set(geometry) != {'type', 'geometries'} or type(geometry['geometries']) is not list:
            raise ValueError('Invalid geometry collection.')
        if any(item is None for item in geometry['geometries']):
            raise ValueError('Invalid geometry collection member.')
        return sum(_geometry_vertices(item) for item in geometry['geometries'])
    if type(kind) is not str or kind not in _LEVELS or set(geometry) != {'type', 'coordinates'}:
        raise ValueError('Invalid geometry schema.')
    return _positions(geometry['coordinates'], _LEVELS[kind])


def validate_payload(payload: object, *, max_features: int, max_vertices: int) -> dict[str, object]:
    if type(payload) is not dict or set(payload) != _KEYS:
        raise ValueError('Invalid parser payload schema.')
    properties, geometries = payload['properties'], payload['geometries']
    if type(properties) is not list or type(geometries) is not list:
        raise ValueError('Invalid parser feature arrays.')
    if len(properties) != len(geometries) or len(properties) > max_features:
        raise ValueError('Invalid parser feature cardinality.')
    bounds = payload['source_bounds']
    if (type(bounds) is not list or len(bounds) != 4 or not all(_number(v) for v in bounds)
            or bounds[0] > bounds[2] or bounds[1] > bounds[3]):
        raise ValueError('Invalid parser bounds.')
    crs = payload['source_crs_wkt']
    if crs is not None and (type(crs) is not str or not crs.strip()):
        raise ValueError('Invalid parser CRS.')
    for props, geometry in zip(properties, geometries):
        if type(props) is not dict or any(type(key) is not str for key in props):
            raise ValueError('Invalid parser properties.')
        for value in props.values():
            if value is not None and type(value) not in (str, bool) and not _number(value):
                raise ValueError('Invalid parser property value.')
        if _geometry_vertices(geometry) > max_vertices:
            raise ValueError('Parser geometry vertex limit exceeded.')
    return payload


def decode_payload(data: bytes, *, max_bytes: int, max_features: int, max_vertices: int) -> dict[str, object]:
    if len(data) > max_bytes:
        raise ValueError('Parser payload exceeds limit.')
    text = data.decode('utf-8', errors='strict')
    _scan_budget(text)
    payload = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    return validate_payload(payload, max_features=max_features, max_vertices=max_vertices)


def read_payload(path: Path, *, max_bytes: int, max_features: int, max_vertices: int) -> dict[str, object]:
    # Check the opened descriptor, not a pathname that the worker can replace.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Parser payload must be a regular file.')
        if info.st_size > max_bytes:
            raise ValueError('Parser payload exceeds limit.')
        data = handle.read(max_bytes + 1)
    return decode_payload(data, max_bytes=max_bytes, max_features=max_features, max_vertices=max_vertices)


def write_payload(path: Path, payload: dict[str, object], *, max_bytes: int, max_features: int, max_vertices: int) -> None:
    # JSON roundtrip also normalizes worker tuple coordinates to arrays.
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    decode_payload(data, max_bytes=max_bytes, max_features=max_features, max_vertices=max_vertices)
    temporary = path.with_suffix('.partial')
    try:
        with temporary.open('xb') as handle:
            handle.write(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
