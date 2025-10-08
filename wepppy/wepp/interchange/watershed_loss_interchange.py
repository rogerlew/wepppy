from __future__ import annotations

import math
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

LOSS_FILENAME = "loss_pw0.txt"

AVERAGE_FILENAMES = {
    "hill": "loss_pw0.hill.parquet",
    "chn": "loss_pw0.chn.parquet",
    "out": "loss_pw0.out.parquet",
    "class_data": "loss_pw0.class_data.parquet",
}

ALL_YEARS_FILENAMES = {
    "hill": "loss_pw0.all_years.hill.parquet",
    "chn": "loss_pw0.all_years.chn.parquet",
    "out": "loss_pw0.all_years.out.parquet",
    "class_data": "loss_pw0.all_years.class_data.parquet",
}

SCHEMA_VERSION = b"1"

unit_consistency_map = {
    "T/ha/yr": "tonne/ha/yr",
    "tonnes/ha": "tonne/ha",
    "tonnes/yr": "tonne/yr",
    None: "",
}

HILL_HEADER = (
    "Type",
    "Hillslopes",
    "Runoff Volume",
    "Subrunoff Volume",
    "Baseflow Volume",
    "Soil Loss",
    "Sediment Deposition",
    "Sediment Yield",
    "Solub. React. Phosphorus",
    "Particulate Phosphorus",
    "Total Phosphorus",
)

HILL_AVG_HEADER = (
    "Type",
    "Hillslopes",
    "Runoff Volume",
    "Subrunoff Volume",
    "Baseflow Volume",
    "Soil Loss",
    "Sediment Deposition",
    "Sediment Yield",
    "Hillslope Area",
    "Solub. React. Phosphorus",
    "Particulate Phosphorus",
    "Total Phosphorus",
)

HILL_UNITS = (
    None,
    None,
    "m^3",
    "m^3",
    "m^3",
    "kg",
    "kg",
    "kg",
    "kg",
    "kg",
    "kg",
)

HILL_AVG_UNITS = (
    None,
    None,
    "m^3",
    "m^3",
    "m^3",
    "kg",
    "kg",
    "kg",
    "ha",
    "kg",
    "kg",
    "kg",
)

CHN_HEADER = (
    "Type",
    "Channels and Impoundments",
    "Discharge Volume",
    "Sediment Yield",
    "Soil Loss",
    "Upland Charge",
    "Subsuface Flow Volume",
    "Solub. React. Phosphorus",
    "Particulate Phosphorus",
    "Total Phosphorus",
)

CHN_AVG_HEADER = (
    "Type",
    "Channels and Impoundments",
    "Discharge Volume",
    "Sediment Yield",
    "Soil Loss",
    "Upland Charge",
    "Subsuface Flow Volume",
    "Contributing Area",
    "Solub. React. Phosphorus",
    "Particulate Phosphorus",
    "Total Phosphorus",
)

CHN_UNITS = (
    None,
    None,
    "m^3",
    "tonne",
    "kg",
    "m^3",
    "m^3",
    "kg",
    "kg",
    "kg",
    "kg",
)

CHN_AVG_UNITS = (
    None,
    None,
    "m^3",
    "tonne",
    "kg",
    "m^3",
    "m^3",
    "ha",
    "kg",
    "kg",
    "kg",
    "kg",
)

CLASS_HEADER = (
    "Class",
    "Diameter",
    "Specific Gravity",
    "Pct Sand",
    "Pct Silt",
    "Pct Clay",
    "Pct OM",
    "Fraction In Flow Exiting",
)

CLASS_UNITS = (
    None,
    "mm",
    None,
    "%",
    "%",
    "%",
    "%",
    "",
)

HILL_TYPES = (pa.int32(),) + (pa.float64(),) * 9
HILL_AVG_TYPES = (pa.int32(),) + (pa.float64(),) * 10
CHN_TYPES = (pa.int32(),) + (pa.float64(),) * 8
CHN_AVG_TYPES = (pa.int32(),) + (pa.float64(),) * 9


def _field(name: str, dtype: pa.DataType, *, units: Optional[str] = None, description: Optional[str] = None) -> pa.Field:
    metadata: Dict[bytes, bytes] = {}
    if units:
        metadata[b"units"] = units.encode()
    if description:
        metadata[b"description"] = description.encode()
    field = pa.field(name, dtype)
    if metadata:
        field = field.with_metadata(metadata)
    return field


HILL_ALL_YEARS_SCHEMA = pa.schema(
    [_field("year", pa.int16())]
    + [_field("Type", pa.string())]
    + [_field(name, dtype, units=units) for name, dtype, units in zip(HILL_HEADER[1:], HILL_TYPES, HILL_UNITS[1:])]
).with_metadata({b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.all_years.hill"})

HILL_AVERAGE_SCHEMA = pa.schema(
    [_field("Type", pa.string())]
    + [_field(name, dtype, units=units) for name, dtype, units in zip(HILL_AVG_HEADER[1:], HILL_AVG_TYPES, HILL_AVG_UNITS[1:])]
).with_metadata(
    {b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.hill"}
)

CHN_ALL_YEARS_SCHEMA = pa.schema(
    [_field("year", pa.int16())]
    + [_field("Type", pa.string())]
    + [_field(name, dtype, units=units) for name, dtype, units in zip(CHN_HEADER[1:], CHN_TYPES, CHN_UNITS[1:])]
).with_metadata({b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.all_years.chn"})

CHN_AVERAGE_SCHEMA = pa.schema(
    [_field("Type", pa.string())]
    + [_field(name, dtype, units=units) for name, dtype, units in zip(CHN_AVG_HEADER[1:], CHN_AVG_TYPES, CHN_AVG_UNITS[1:])]
).with_metadata(
    {b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.chn"}
)

OUT_ALL_YEARS_SCHEMA = pa.schema(
    [
        _field("year", pa.int16()),
        _field("key", pa.string()),
        _field("value", pa.float64()),
        _field("units", pa.string()),
    ]
).with_metadata({b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.all_years.out"})

OUT_AVERAGE_SCHEMA = pa.schema(
    [
        _field("key", pa.string()),
        _field("value", pa.float64()),
        _field("units", pa.string()),
    ]
).with_metadata({b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.out"})

CLASS_ALL_YEARS_SCHEMA = pa.schema([_field("year", pa.int16())] + [_field(name, pa.float64() if name != "Class" else pa.int8(), units=unit if name != "Class" else None) for name, unit in zip(CLASS_HEADER, CLASS_UNITS)]).with_metadata(
    {b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.all_years.class_data"}
)

CLASS_AVERAGE_SCHEMA = pa.schema([_field(name, pa.float64() if name != "Class" else pa.int8(), units=unit if name != "Class" else None) for name, unit in zip(CLASS_HEADER, CLASS_UNITS)]).with_metadata(
    {b"schema_version": SCHEMA_VERSION, b"table": b"loss_pw0.class_data"}
)


def _coerce_value(value: object, field: pa.Field) -> object:
    if value is None:
        return None
    target_type = field.type
    if pa.types.is_integer(target_type):
        if isinstance(value, (int,)):
            return int(value)
        if isinstance(value, float):
            if math.isnan(value):
                return None
            return int(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return int(float(value))
            except ValueError:
                return None
        return None

    if pa.types.is_floating(target_type):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return float(value)
            except ValueError:
                if value in {"********"}:
                    return float("nan")
                return None
        return None

    if pa.types.is_string(target_type):
        return str(value)

    return value


def _rows_to_table(rows: Iterable[Dict[str, object]], schema: pa.Schema) -> pa.Table:
    column_store: Dict[str, List[object]] = {field.name: [] for field in schema}
    fields = list(schema)
    for row in rows:
        for field in fields:
            column_store[field.name].append(_coerce_value(row.get(field.name), field))
    return pa.table(column_store, schema=schema)


def _find_tbl_starts(section_index: int, lines: List[str]) -> Tuple[int, int, int]:
    header_indx: List[int] = []
    for i, line in enumerate(lines[section_index + 2 :]):
        if line.startswith("----"):
            header_indx.append(i)
        if len(header_indx) == 3:
            break

    if len(header_indx) < 3:
        raise ValueError("Unable to locate table separators in loss file.")

    hill0 = header_indx[0] + 1 + section_index + 2
    chn0 = header_indx[1] + 2 + section_index + 2
    out0 = header_indx[2] + 2 + section_index + 2

    return hill0, chn0, out0


def _parse_tbl(lines: Iterable[str], header: Tuple[str, ...]) -> List[OrderedDict]:
    data: List[OrderedDict] = []
    for line in lines:
        if not line:
            break

        row: List[object] = []

        for token in line.split():
            if token.count(".") == 2:
                idx = token.find(".")
                part0 = token[: idx + 3]
                part1 = token[idx + 3 :]
                row.append(float(part0))
                row.append(float(part1))
            elif token.count(".") == 3:
                part0 = token[:3]
                part1 = token[3:11]
                part2 = token[11:]
                row.extend([float(part0), float(part1), float(part2)])
            elif "." in token:
                if "*" in token:
                    cleaned = token.replace("*", "")
                    if cleaned.endswith("."):
                        cleaned = cleaned[:-1]
                    if token.endswith("*"):
                        row.append(float(cleaned) if cleaned else float("nan"))
                        row.append("********")
                    else:
                        row.append("********")
                        row.append(float(cleaned))
                else:
                    try:
                        row.append(float(token))
                    except ValueError:
                        row.append(token.strip())
            else:
                try:
                    row.append(int(token))
                except ValueError:
                    if "NaN" in token:
                        row.append(float("nan"))
                    else:
                        row.append(token.strip())

        if len(row) != len(header):
            raise ValueError(f"Unexpected column count while parsing loss table: expected {len(header)}, got {len(row)}, line={line!r}")
        data.append(OrderedDict(zip(header, row)))

    return data


def _parse_out(lines: Iterable[str]) -> List[Dict[str, object]]:
    data: List[Dict[str, object]] = []
    for line in lines:
        if not line:
            break
        if "=" not in line:
            break

        key_part, value_part = line.split("=", 1)
        value_tokens = value_part.split()

        if len(value_tokens) == 2:
            value_str, units = value_tokens
            units = unit_consistency_map.get(units.strip(), units.strip())
        else:
            value_str = value_tokens[0]
            units = ""

        key = key_part.strip()
        value_str = value_str.strip()

        if "." in value_str:
            try:
                value: object = float(value_str)
            except ValueError:
                value = value_str
        else:
            try:
                value = int(value_str)
            except ValueError:
                if "NaN" in value_str:
                    value = float("nan")
                else:
                    value = value_str

        data.append({"key": key, "value": value, "units": units})

    return data


def _extract_class_data(lines: List[str]) -> List[OrderedDict]:
    class_lines: List[str] = []
    for line in lines:
        if not line:
            if class_lines:
                break
            continue
        stripped = line.strip()
        if set(stripped) == {"-"}:
            continue
        if stripped.lower().startswith("distribution of primary particles"):
            break
        if stripped[0].isdigit():
            class_lines.append(line)
    if not class_lines:
        return []
    return _parse_tbl(class_lines, CLASS_HEADER)


def _collect_class_block(lines: List[str], start: int, end: int) -> List[OrderedDict]:
    target_line = None
    for idx in range(start, end):
        if "sediment particle information leaving" in lines[idx].lower():
            target_line = idx
            break
    if target_line is None:
        return []

    data_lines = lines[target_line + 1 : end]
    return _extract_class_data(data_lines)


def _parse_loss_file(path: Path) -> Dict[str, List[Dict[str, object]]]:
    with path.open("r") as stream:
        raw_lines = stream.readlines()

    raw_lines = [line.replace("*** total soil loss < 1 kg ***", "") for line in raw_lines]
    lines = [line.strip() for line in raw_lines]

    yearly_sections: List[Tuple[int, int]] = []
    for idx, line in enumerate(lines):
        if "ANNUAL SUMMARY FOR WATERSHED IN YEAR" in line:
            match = re.search(r"YEAR\s+(\d+)", line)
            if not match:
                raise ValueError(f"Unable to extract year from line: {line}")
            yearly_sections.append((idx, int(match.group(1))))

    average_idx = None
    average_years = None
    for idx, line in enumerate(lines):
        if "YEAR AVERAGE ANNUAL VALUES FOR WATERSHED" in line:
            average_idx = idx
            numbers = re.findall(r"\d+", line)
            if numbers:
                average_years = int(numbers[0])
            break

    if average_idx is None:
        raise ValueError("Average annual section not found in loss file.")

    section_indices = [idx for idx, _ in yearly_sections] + [average_idx]
    section_indices.sort()

    average_start_pos = average_idx

    yearly_hill_rows: List[Dict[str, object]] = []
    yearly_chn_rows: List[Dict[str, object]] = []
    yearly_out_rows: List[Dict[str, object]] = []
    yearly_class_rows: List[Dict[str, object]] = []

    average_hill_rows: List[Dict[str, object]] = []
    average_chn_rows: List[Dict[str, object]] = []
    average_out_rows: List[Dict[str, object]] = []
    average_class_rows: List[Dict[str, object]] = []

    for idx, year in yearly_sections:
        hill_start, chn_start, out_start = _find_tbl_starts(idx, lines)
        next_section_pos_candidates = [pos for pos in section_indices if pos > idx]
        next_section_pos = next_section_pos_candidates[0] if next_section_pos_candidates else len(lines)

        hill_rows = _parse_tbl(lines[hill_start:], HILL_HEADER)
        for row in hill_rows:
            yearly_row = dict(row)
            yearly_row["year"] = year
            yearly_hill_rows.append(yearly_row)

        chn_rows = _parse_tbl(lines[chn_start:], CHN_HEADER)
        for row in chn_rows:
            yearly_row = dict(row)
            yearly_row["year"] = year
            yearly_chn_rows.append(yearly_row)

        out_rows = _parse_out(lines[out_start:])
        for row in out_rows:
            yearly_rows = dict(row)
            yearly_rows["year"] = year
            yearly_out_rows.append(yearly_rows)

        class_rows = _collect_class_block(lines, out_start, next_section_pos)
        for row in class_rows:
            yearly_row = dict(row)
            yearly_row["year"] = year
            yearly_class_rows.append(yearly_row)

    avg_hill_start, avg_chn_start, avg_out_start = _find_tbl_starts(average_start_pos, lines)

    avg_hill_rows = _parse_tbl(lines[avg_hill_start:], HILL_AVG_HEADER)
    for row in avg_hill_rows:
        average_hill_rows.append(dict(row))

    avg_chn_rows = _parse_tbl(lines[avg_chn_start:], CHN_AVG_HEADER)
    for row in avg_chn_rows:
        average_chn_rows.append(dict(row))

    avg_out_rows = _parse_out(lines[avg_out_start:])
    for row in avg_out_rows:
        average_out_rows.append(dict(row))

    avg_class_rows = _collect_class_block(lines, avg_out_start, len(lines))
    for row in avg_class_rows:
        average_class_rows.append(dict(row))

    return {
        "yearly_hill": yearly_hill_rows,
        "yearly_chn": yearly_chn_rows,
        "yearly_out": yearly_out_rows,
        "yearly_class": yearly_class_rows,
        "average_hill": average_hill_rows,
        "average_chn": average_chn_rows,
        "average_out": average_out_rows,
        "average_class": average_class_rows,
        "average_years": average_years,
    }


def _build_tables(parsed: Dict[str, List[Dict[str, object]]]) -> Dict[str, pa.Table]:
    tables: Dict[str, pa.Table] = {}

    tables["all_years_hill"] = _rows_to_table(parsed["yearly_hill"], HILL_ALL_YEARS_SCHEMA)
    tables["all_years_chn"] = _rows_to_table(parsed["yearly_chn"], CHN_ALL_YEARS_SCHEMA)
    tables["all_years_out"] = _rows_to_table(parsed["yearly_out"], OUT_ALL_YEARS_SCHEMA)
    tables["all_years_class"] = _rows_to_table(parsed["yearly_class"], CLASS_ALL_YEARS_SCHEMA)

    tables["average_hill"] = _rows_to_table(parsed["average_hill"], HILL_AVERAGE_SCHEMA)
    tables["average_chn"] = _rows_to_table(parsed["average_chn"], CHN_AVERAGE_SCHEMA)
    tables["average_out"] = _rows_to_table(parsed["average_out"], OUT_AVERAGE_SCHEMA)
    tables["average_class"] = _rows_to_table(parsed["average_class"], CLASS_AVERAGE_SCHEMA)

    if parsed.get("average_years") is not None:
        avg_years = str(parsed["average_years"]).encode()
        for key in ("average_hill", "average_chn", "average_out", "average_class"):
            table = tables[key]
            metadata = dict(table.schema.metadata or {})
            metadata[b"average_years"] = avg_years
            tables[key] = table.replace_schema_metadata(metadata)

    return tables


def run_wepp_watershed_loss_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    source = base / LOSS_FILENAME
    if not source.exists():
        raise FileNotFoundError(source)

    parsed = _parse_loss_file(source)
    tables = _build_tables(parsed)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, Path] = {}

    mapping = {
        "average_hill": interchange_dir / AVERAGE_FILENAMES["hill"],
        "average_chn": interchange_dir / AVERAGE_FILENAMES["chn"],
        "average_out": interchange_dir / AVERAGE_FILENAMES["out"],
        "average_class": interchange_dir / AVERAGE_FILENAMES["class_data"],
        "all_years_hill": interchange_dir / ALL_YEARS_FILENAMES["hill"],
        "all_years_chn": interchange_dir / ALL_YEARS_FILENAMES["chn"],
        "all_years_out": interchange_dir / ALL_YEARS_FILENAMES["out"],
        "all_years_class": interchange_dir / ALL_YEARS_FILENAMES["class_data"],
    }

    for key, path in mapping.items():
        pq.write_table(tables[key], path, compression="snappy", use_dictionary=True)
        outputs[key] = path

    return outputs
