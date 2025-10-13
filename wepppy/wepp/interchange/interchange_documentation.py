from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from .versioning import INTERCHANGE_VERSION, read_version_manifest

HILLSLOPE_DOC_ORDER: List[Tuple[str, str]] = [
    ("H.element.parquet", "Daily hillslope element hydrology and sediment metrics."),
    ("H.wat.parquet", "Hillslope water balance per OFE; aligns with wat.out content."),
    ("H.pass.parquet", "Event/subevent sediment and runoff delivery by hillslope (PASS)."),
    ("H.loss.parquet", "Average annual particle class fractions at the hillslope outlet."),
    ("H.soil.parquet", "Daily soil state variables per OFE from soil.dat."),
    ("H.ebe.parquet", "Event-by-event hillslope runoff and sediment summaries."),
]

WATERSHED_DOC_ORDER: List[Tuple[str, str]] = [
    ("chan.out.parquet", "Peak discharge report for watershed channels (chan.out)."),
    ("chanwb.parquet", "Daily channel routing water balance."),
    ("chnwb.parquet", "Channel OFE water balance (chnwb.txt)."),
    ("ebe_pw0.parquet", "Watershed event-by-event runoff and sediment delivery."),
    ("soil_pw0.parquet", "Watershed soil-profile state variables."),
    ("loss_pw0.hill.parquet", "Average annual hillslope loss summary."),
    ("loss_pw0.chn.parquet", "Average annual channel loss summary."),
    ("loss_pw0.out.parquet", "Average annual watershed outlet summary."),
    ("loss_pw0.class_data.parquet", "Average annual particle size fractions at the outlet."),
    ("loss_pw0.all_years.hill.parquet", "Per-year hillslope loss summary."),
    ("loss_pw0.all_years.chn.parquet", "Per-year channel loss summary."),
    ("loss_pw0.all_years.out.parquet", "Per-year watershed outlet summary."),
    ("loss_pw0.all_years.class_data.parquet", "Per-year particle size fractions at the outlet."),
    ("pass_pw0.events.parquet", "Watershed PASS events table (runoff and sediment delivery)."),
    ("pass_pw0.metadata.parquet", "Watershed PASS metadata (particle diameters, areas, concentrations)."),
]

MAX_SAMPLE_ROWS = 3


def _format_units(field: pa.Field) -> str:
    if field.metadata and b"units" in field.metadata:
        return field.metadata[b"units"].decode()
    return ""


def _format_description(field: pa.Field) -> str:
    if field.metadata and b"description" in field.metadata:
        return field.metadata[b"description"].decode()
    return ""


def _schema_markdown(schema: pa.Schema) -> str:
    lines = ["| Column | Type | Units | Description |", "| --- | --- | --- | --- |"]
    for field in schema:
        lines.append(
            f"| {field.name} | {field.type} | {_format_units(field)} | {_format_description(field)} |"
        )
    return "\n".join(lines)


def _table_preview_markdown(table: pa.Table) -> str:
    if table.num_rows == 0:
        return "_No rows_\n"
    head = table.slice(0, min(MAX_SAMPLE_ROWS, table.num_rows))
    df = head.to_pandas()

    schema = table.schema
    column_names = list(df.columns)
    headers = " | ".join(column_names)
    separator = " | ".join(["---"] * len(column_names))

    units_map = {field.name: _format_units(field) for field in schema}
    units_row = " | ".join(units_map.get(name, "") for name in column_names)

    def _format_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            if math.isnan(value):
                return ""
            if value.is_integer():
                return str(int(value))
            return f"{value:g}"
        try:
            import numpy as np

            if isinstance(value, np.floating):
                if np.isnan(value):
                    return ""
                if float(value).is_integer():
                    return str(int(value))
                return f"{float(value):g}"
            if isinstance(value, np.integer):
                return str(int(value))
        except ImportError:
            pass
        if isinstance(value, int):
            return str(value)
        return str(value)

    rows = [" | ".join(_format_value(value) for value in row) for row in df.values.tolist()]
    return "\n".join([headers, separator, units_row, *rows])


def _summarize_file(parquet_path: Path, description: str) -> str:
    table = pq.read_table(parquet_path)
    schema = table.schema
    header = f"### `{parquet_path.name}`\n\n{description}\n\n"
    schema_md = _schema_markdown(schema)
    preview_md = _table_preview_markdown(table)
    return f"{header}{schema_md}\n\nPreview:\n\n{preview_md}\n"


def generate_interchange_documentation(interchange_dir: Path | str, to_readme_md: bool = True) -> str:
    base = Path(interchange_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    sections: List[str] = ["# Interchange Documentation\n"]

    manifest_version = read_version_manifest(base)
    if manifest_version is None:
        version_text = f"{INTERCHANGE_VERSION} (manifest missing)"
    else:
        version_text = str(manifest_version)
    sections.append(f"_Interchange Version: {version_text}_\n")

    sections.append("## Hillslope Products\n")
    for filename, description in HILLSLOPE_DOC_ORDER:
        parquet_path = base / filename
        if parquet_path.exists():
            sections.append(_summarize_file(parquet_path, description))

    sections.append("## Watershed Products\n")
    for filename, description in WATERSHED_DOC_ORDER:
        parquet_path = base / filename
        if parquet_path.exists():
            sections.append(_summarize_file(parquet_path, description))

    md = "\n".join(sections)

    if to_readme_md:
        readme_path = base / "README.md"
        readme_path.write_text(md)

    return md
