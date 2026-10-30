"""Canonical, property-preserving 200 mm boundary for generated WEPP soils.

This operates on serialized records so appended hydraulic values and legacy
parameter tokens are copied verbatim. It does not repair or estimate properties.
Uploaded-soil preservation is an explicit separate serialization path.
"""
from __future__ import annotations

import math
import re

__all__ = ["ensure_200mm_boundary"]

_TOKEN = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|\S+")
_VERSIONS = {94.1, 95.1, 95.3, 97.3, 97.5, 98.4, 2006.0, 2006.2, 7777.0, 7778.0,
             9001.0, 9002.0, 9003.0, 9005.0}


def ensure_200mm_boundary(text: str) -> str:
    """Insert an identical-material boundary in each generated OFE when needed.

    Only a copied horizon's depth and its OFE's declared count change. No I/O
    occurs, and a failure must be handled before opening the destination file.
    Profiles already ending at 200 mm, shallower profiles, and zero-layer legacy
    water profiles need no insertion. A required eleventh layer fails explicitly.
    """
    lines = text.splitlines(keepends=True)
    records = [i for i, line in enumerate(lines)
               if line.strip() and not line.lstrip().startswith('#')]
    if len(records) < 3:
        raise ValueError('Soil boundary insertion requires version, comment and OFE count records')
    try:
        version = float(lines[records[0]].strip())
        count_index = 2 if version >= 95.3 else 1
        nofe = int(lines[records[count_index]].split()[0])
    except (ValueError, IndexError) as exc:
        raise ValueError('Invalid soil version or OFE count') from exc
    if version not in _VERSIONS or nofe < 0:
        raise ValueError(f'Unsupported soil version or OFE count: {version}, {nofe}')
    edits: dict[int, str] = {}
    additions: dict[int, str] = {}
    cursor = count_index + 1
    for ofe in range(1, nofe + 1):
        if version > 9000:
            cursor += 1  # Native landuse/hydraulic metadata precedes the soil header.
        if cursor >= len(records):
            raise ValueError(f'Missing soil header for OFE {ofe}')
        header_index = records[cursor]
        tokens = list(_TOKEN.finditer(lines[header_index]))
        try:
            count_token = tokens[2]
            nsl = int(count_token.group())
        except (IndexError, ValueError) as exc:
            raise ValueError(f'Invalid soil layer count for OFE {ofe}') from exc
        if nsl > 10:
            raise ValueError(f'OFE {ofe}: generated soil exceeds the native 10-layer limit')
        if nsl < 0:
            raise ValueError(f'Negative soil layer count for OFE {ofe}')
        cursor += 1
        previous = 0.0
        crossing = None
        for _ in range(nsl):
            if cursor >= len(records):
                raise ValueError(f'Missing soil horizon for OFE {ofe}')
            index = records[cursor]
            match = re.match(r'\s*(\S+)', lines[index])
            try:
                depth = float(match.group(1))
            except (AttributeError, ValueError) as exc:
                raise ValueError(f'Invalid horizon depth for OFE {ofe}') from exc
            # Existing clipping may leave equal terminal depths; do not invent
            # a topology repair here. A decreasing/nonfinite depth is invalid.
            if not math.isfinite(depth) or depth <= 0 or depth < previous:
                raise ValueError(f'Invalid cumulative horizon depth for OFE {ofe}: {depth}')
            if previous < 200.0 < depth:
                crossing = (index, match)
            previous = depth
            cursor += 1
        if version >= 2006:
            if cursor >= len(records):
                raise ValueError(f'Missing restrictive layer for OFE {ofe}')
            cursor += 1
        if crossing is not None:
            if nsl >= 10:
                raise ValueError(f'OFE {ofe}: inserting 200 mm boundary would exceed the native 10-layer limit')
            index, match = crossing
            line = lines[index]
            added = line[:match.start(1)] + '200.0' + line[match.end(1):]
            if not added.endswith(('\n', '\r')):
                added += '\r\n' if '\r\n' in text else '\n'
            additions[index] = added
            header = lines[header_index]
            edits[header_index] = header[:count_token.start()] + str(nsl + 1) + header[count_token.end():]
    if cursor != len(records):
        raise ValueError('Trailing soil records or inconsistent declared layer count')
    if not additions:
        return text
    return ''.join(additions.get(i, '') + edits.get(i, line) for i, line in enumerate(lines))
