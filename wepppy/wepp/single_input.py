"""Strict admission for the certified single-OFE WEPP input subset (SUDI-01)."""
from __future__ import annotations

from copy import deepcopy
import math
import re
from pathlib import Path
import shlex
import struct
import unicodedata

from wepppy.wepp.management.managements import Management, Loops, ScenarioReference

__all__ = ["MAX_SOURCE_BYTES", "SingleInputError", "decode_source", "validate_filename", "validate_soil_text", "read_uploaded_management", "canonical_management"]
MAX_SOURCE_BYTES = 5 * 1024 * 1024
_NUMBER = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


class SingleInputError(ValueError):
    def __init__(self, message: str, *, code="invalid_single_input", status_code=400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def validate_filename(filename: str, kind: str) -> str:
    extension = ".man" if kind == "landuse" else ".sol"
    if (not isinstance(filename, str) or not filename
            or len(filename.encode("utf-8")) > 255
            or "/" in filename or "\\" in filename
            or any(unicodedata.category(char).startswith("C") for char in filename)
            or not filename.lower().endswith(extension)):
        raise SingleInputError(f"Choose a plain-text {extension} file with a valid filename.")
    return filename


def decode_source(raw: bytes) -> str:
    if len(raw) > MAX_SOURCE_BYTES:
        raise SingleInputError("The single input exceeds 5 MiB.", code="single_input_too_large", status_code=413)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SingleInputError("The input must be UTF-8 plain text.") from exc
    if not text.strip() or any(unicodedata.category(c).startswith("C") and c not in "\t\r\n" for c in text):
        raise SingleInputError("The input is empty or contains unsupported control characters.")
    lines = text.splitlines()
    if len(lines) > 100_000 or any(len(line.encode("utf-8")) > 16_384 for line in lines):
        raise SingleInputError("The input exceeds the text record limits.")
    for line in lines:
        for token in line.partition("#")[0].split():
            try:
                value = float(token)
            except ValueError:
                continue
            if len(token) > 64 or not _NUMBER.fullmatch(token) or not math.isfinite(value) or abs(value) > 3.4028234e38 or (abs(value) < 1.4012985e-45 and any(char in "123456789" for char in token.lower().split("e", 1)[0])):
                raise SingleInputError("Numeric values must be finite and at most 64 characters.")
    return "\n".join(lines) + "\n"


def _number(token: str) -> float:
    value = float(token)
    if len(token) > 64 or not _NUMBER.fullmatch(token) or not math.isfinite(value) or abs(value) > 3.4028234e38 or (abs(value) < 1.4012985e-45 and any(char in "123456789" for char in token.lower().split("e", 1)[0])):
        raise ValueError("Parameter is not a finite native REAL")
    return value


def _native_real(token: str) -> float:
    """Check ordered bounds at the native reader's single precision."""
    return struct.unpack('f', struct.pack('f', _number(token)))[0]


def _soil_tokens(line: str, text_fields: tuple[int, ...]) -> list[str]:
    # shlex alone accepts native list-directed controls and incompatible escapes.
    token = r"(?:'[^\"'\\]*'|\"[^\"'\\]*\"|[A-Za-z0-9_.:+-]+)"
    if not re.fullmatch(token + r"(?:[ \t]+" + token + r")*", line):
        raise ValueError("Unsupported native soil token syntax")
    for index, raw in enumerate(re.findall(token, line)):
        if index not in text_fields and not _NUMBER.fullmatch(raw):
            raise ValueError("Quoted or nonnumeric soil parameter")
    return shlex.split(line)


def validate_soil_text(text: str, *, max_ofes: int = 1) -> None:
    """Validate complete native soil records before the permissive owned parser."""
    try:
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        version = _number(lines[0])
        if version not in (2006, 2006.2, 7777, 7778, 9002):
            raise ValueError("version")
        count = re.split(r"[ \t]+", lines[2])
        if (len(count) != 2 or not re.fullmatch(r"[0-9]{1,2}", count[0])
                or not 1 <= int(count[0]) <= max_ofes or count[1] not in {"0", "1"}):
            raise ValueError("OFE/ksflag")
        position = 3
        for _ in range(int(count[0])):
            if version == 9002:
                adjustment = _soil_tokens(lines[position], (1, 2)); position += 1
                if (len(adjustment) != 5 or adjustment[0] not in {"0", "1"}
                        or any(_number(value) <= 0 for value in adjustment[3:])):
                    raise ValueError("9002 adjustment header")
            header = _soil_tokens(lines[position], (0, 1)); position += 1
            if (len(header) != (9 if version < 7777 else 8)
                    or not re.fullmatch(r"[0-9]{1,2}", header[2]) or not 1 <= int(header[2]) <= 10):
                raise ValueError("header/layers")
            salb, sat, ki, kr, shear = map(_number, header[3:8])
            if not (0 <= salb <= 1 and 0 <= sat <= 1 and min(ki, kr, shear) >= 0):
                raise ValueError("surface parameters")
            if version < 7777 and _number(header[8]) < 0:
                raise ValueError("avke")
            previous_depth = native_previous_depth = 0.0
            for _ in range(int(header[2])):
                fields = re.split(r"[ \t]+", lines[position]); position += 1
                if len(fields) != (6 if version < 7777 else 10 if version == 7777 else 18 if version == 9002 else 11):
                    raise ValueError("horizon width")
                values = list(map(_number, fields))
                native_values = list(map(_native_real, fields))
                if version < 7777:
                    depth, sand, clay, om, cec, rock = values
                else:
                    if version == 7777:
                        depth, bd, conductivity, fc, wp, sand, clay, om, cec, rock = values
                    else:
                        depth, bd, conductivity, anisotropy, fc, wp, sand, clay, om, cec, rock = values[:11]
                        if anisotropy < 0:
                            raise ValueError("layer anisotropy")
                    if not (bd > 0 and conductivity >= 0 and 0 <= wp <= fc <= 1):
                        raise ValueError("hydraulic parameters")
                if not (depth > previous_depth and cec >= 0
                        and all(0 <= value <= 100 for value in (sand, clay, om, rock)) and sand + clay <= 100):
                    raise ValueError("horizon parameters")
                if version == 9002:
                    for hydraulic_values in (values[11:], native_values[11:]):
                        residual, saturated, alpha, exponent, conductivity, wp, fc = hydraulic_values
                        if not (0 <= residual < saturated <= 1 and alpha > 0 and exponent > 1
                                and conductivity > 0 and 0 < wp < fc <= 1):
                            raise ValueError("9002 hydraulic parameters")
                if native_values[0] <= native_previous_depth:
                    raise ValueError("Native horizon depths must increase")
                previous_depth, native_previous_depth = depth, native_values[0]
            restrictive = re.split(r"[ \t]+", lines[position]); position += 1
            if (len(restrictive) != 3 or restrictive[0] not in {"0", "1"}
                    or any(_number(value) < 0 for value in restrictive[1:])):
                raise ValueError("restrictive layer")
        if position != len(lines):
            raise ValueError("trailing records")
    except (ValueError, IndexError, OverflowError) as exc:
        raise SingleInputError("Invalid soil input. Use a complete version 2006, 2006.2, 7777, 7778, or 9002 file with one OFE and 1–10 valid layers.") from exc


def _validate_management_graph(management: Management) -> None:
    for section in (management.plants, management.ops, management.inis, management.surfs,
                    management.contours, management.drains, management.years):
        names = [str(item.name) for item in section]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate scenario name")
    if any(ref.section_type is None for ref in management.man.ofeindx):
        raise ValueError("Missing initial condition")
    for initial in management.inis:
        if initial.data.iresd.section_type is None:
            raise ValueError("Missing residue plant scenario")
    for operation in management.ops:
        if operation.data.pcode in (10, 12) and operation.data.iresad.section_type is None:
            raise ValueError("Missing operation residue scenario")
    for surface in management.surfs:
        for tillage in surface.data:
            if tillage.op.section_type is None:
                raise ValueError("Missing tillage operation")
    for year in management.years:
        if year.data.itype.section_type is None:
            raise ValueError("Missing plant scenario")
    for rotation in management.man.loops:
        for year in rotation.years:
            for ofe in year:
                if any(ref.section_type is None for ref in ofe.manindx):
                    raise ValueError("Missing yearly scenario")
    # Inspect scalar science values without following cyclic graph ownership.
    seen = set()
    def visit(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite management parameter")
        if isinstance(value, (str, int, float, type(None), bool)) or id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, ScenarioReference):
            str(value)  # Resolve each named reference, including optional sections.
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)
        elif hasattr(value, "__dict__"):
            for key, child in vars(value).items():
                if key not in {"root", "parent", "this", "owner"}:
                    visit(child)
    visit(management)


def read_uploaded_management(path: str | Path, *, max_ofes: int = 1) -> Management:
    path = Path(path)
    try:
        management = Management(Key=None, ManagementFile=path.name, ManagementDir=str(path.parent),
                                Description="Single User-Defined", Color=(80, 130, 100, 255),
                                StrictUpload=True, InputMaxOfes=max_ofes)
        _validate_management_graph(management)
        return management
    except (ValueError, IndexError, KeyError, AssertionError, TypeError, NotImplementedError, OverflowError) as exc:
        raise SingleInputError("Invalid management input. Use a complete version98.4 cropland-format file with one OFE and valid scenario references.") from exc


def canonical_management(management: Management) -> str:
    """Flatten the complete schedule to one rotation, avoiding repeated headers."""
    result = deepcopy(management)
    years = Loops()
    for rotation in result.man.loops:
        years.extend(rotation.years)
    rotation = result.man.loops[0]
    rotation.years = years
    result.man.loops = Loops()
    result.man.loops.append(rotation)
    result.sim_years = len(years)
    result.setroot()
    return str(result) + "\n"
