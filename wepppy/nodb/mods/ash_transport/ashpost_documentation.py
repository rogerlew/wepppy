from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

ASH_POST_DOC_ORDER: List[Tuple[str, str]] = [
    (
        "hillslope_annuals.parquet",
        "Per-hillslope averages of wind, water, and total ash transport (tonne/ha) for the first post-fire year.",
    ),
    (
        "watershed_daily.parquet",
        "Daily watershed totals of ash transport and remaining ash aggregated across all hillslopes.",
    ),
    (
        "watershed_daily_by_burn_class.parquet",
        "Daily watershed totals segmented by soil burn severity class for severity-specific comparisons.",
    ),
    (
        "watershed_annuals.parquet",
        "Annual watershed totals summarising wind, water, and total ash transport along with residual ash.",
    ),
    (
        "watershed_cumulatives.parquet",
        "Per fire-year cumulative transport metrics captured when transportable ash is exhausted.",
    ),
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


def generate_ashpost_documentation(ash_post_dir: Path | str, to_readme_md: bool = True) -> str:
    base = Path(ash_post_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    sections: List[str] = [
        "# Ash Transport Post-Processing\n",
        "Derived parquet artifacts created by `AshPost` to summarise hillslope and watershed ash transport.\n",
    ]

    for filename, description in ASH_POST_DOC_ORDER:
        parquet_path = base / filename
        if parquet_path.exists():
            sections.append(_summarize_file(parquet_path, description))

    md = "\n".join(sections)

    if to_readme_md:
        readme_path = base / "README.md"
        readme_path.write_text(md)

    return md
