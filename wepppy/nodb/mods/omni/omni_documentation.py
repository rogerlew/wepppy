from __future__ import annotations

import math
from pathlib import Path
from typing import List, Mapping, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq


MAX_SAMPLE_ROWS = 3

SCENARIO_PRODUCTS: Sequence[Tuple[str, str]] = (
    (
        "scenarios.out.parquet",
        "Long-form, average-annual watershed outlet metrics for the base run and each Omni scenario.",
    ),
    (
        "scenarios.hillslope_summaries.parquet",
        "Wide, average-annual hillslope summaries for the base run and each Omni scenario.",
    ),
    (
        "scenarios.channel_summaries.parquet",
        "Wide, average-annual channel summaries for the base run and each Omni scenario.",
    ),
)

CONTRAST_PRODUCTS: Sequence[Tuple[str, str]] = (
    (
        "contrasts.out.parquet",
        "Long-form, average-annual watershed outlet metrics for each targeted-treatment contrast and its control.",
    ),
)

OUTLET_METRIC_DESCRIPTIONS: Mapping[str, str] = {
    "Total contributing area to outlet": "Watershed area that drains to the modeled outlet.",
    "Avg. Ann. Precipitation volume in contributing area": (
        "Mean annual precipitation volume over the area contributing to the outlet."
    ),
    "Avg. Ann. irrigation volume in contributing area": (
        "Mean annual irrigation volume over the area contributing to the outlet."
    ),
    "Avg. Ann. water discharge from outlet": "Mean annual water volume discharged at the watershed outlet.",
    "Avg. Ann. total hillslope soil loss": (
        "Mean annual gross soil loss reported across all hillslope elements; "
        "this is not the mass delivered at the outlet."
    ),
    "Avg. Ann. total channel soil loss": "Mean annual gross soil loss reported across all channel elements.",
    "Avg. Ann. sediment discharge from outlet": (
        "Mean annual sediment mass leaving the watershed at the modeled outlet."
    ),
    "Avg. Ann. Sed. delivery per unit area of watershed": (
        "Mean annual outlet sediment discharge divided by the contributing watershed area."
    ),
    "Sediment Delivery Ratio for Watershed": (
        "Outlet sediment discharge divided by total hillslope plus channel soil loss; dimensionless."
    ),
    "Avg. Ann. Phosphorus discharge from outlet": (
        "Mean annual phosphorus mass leaving the watershed at the modeled outlet."
    ),
    "Avg. Ann. P. delivery per unit area of watershed": (
        "Mean annual outlet phosphorus discharge divided by the contributing watershed area."
    ),
}

COMMON_COLUMN_DESCRIPTIONS: Mapping[str, str] = {
    "key": "WEPP outlet metric name. See the Metric keys table for the observed values.",
    "value": "Metric value for the row; equivalent to `v` when both columns are present.",
    "v": "Metric value for the row; retained as a compatibility alias of `value`.",
    "units": "Units for `value`, `v`, and the corresponding control/difference values.",
    "scenario": "Base-run or Omni scenario name.",
    "control_scenario": "Scenario used as the untreated control for this contrast.",
    "contrast_topaz_id": (
        "Selected TOPAZ hillslope identifier in cumulative-selection mode; absent in other selection modes."
    ),
    "contrast": "Human-facing contrast label or generated contrast name.",
    "_contrast_name": "Internal generated contrast name used to preserve contrast provenance.",
    "contrast_id": (
        "Stable positive contrast identifier; joins to `contrast_id_definitions.psv` "
        "and the matching contrast run directory."
    ),
    "group_index": (
        "User-defined hillslope-group index; present only for user-defined hillslope-group contrasts."
    ),
    "control_v": "Value of the same `key` in the control scenario.",
    "control_units": "Units reported for `control_v`; expected to match `units`.",
    "control-contrast_v": (
        "`control_v - v`. Positive values mean the contrast reduced the metric; negative values mean it increased it."
    ),
    "Wepp ID": "Sequential WEPP hillslope identifier.",
    "Topaz ID": "TOPAZ watershed element identifier.",
    "Landuse Key": "WEPPcloud land-use class key assigned to the hillslope.",
    "Landuse Description": "Human-readable land-use class assigned to the hillslope.",
    "Soil Key": "WEPPcloud soil identifier assigned to the hillslope.",
    "Soil Description": "Human-readable soil description assigned to the hillslope.",
    "Length (m)": "Representative element length.",
    "Width (m)": "Representative element width.",
    "Slope": "Representative dimensionless slope gradient (rise/run).",
    "Landuse Area (ha)": "Hillslope area used for land-use and density calculations.",
    "Runoff Depth (mm/yr)": "Mean annual surface-runoff depth.",
    "Lateral Flow Depth (mm/yr)": "Mean annual subsurface lateral-flow depth.",
    "Baseflow Depth (mm/yr)": "Mean annual baseflow depth.",
    "Soil Loss (kg/yr)": "Mean annual gross hillslope soil loss.",
    "Soil Loss Density (kg/ha/yr)": "Mean annual gross hillslope soil loss per unit hillslope area.",
    "Sediment Deposition (kg/yr)": "Mean annual sediment deposition on the hillslope.",
    "Sediment Deposition Density (kg/ha/yr)": "Mean annual hillslope sediment deposition per unit area.",
    "Sediment Yield (kg/yr)": "Mean annual sediment mass leaving the hillslope.",
    "Sediment Yield Density (kg/ha/yr)": "Mean annual hillslope sediment yield per unit area.",
    "Runoff (m^3)": "Mean annual runoff volume, derived from runoff depth and hillslope area.",
    "Lateral Flow (m^3)": "Mean annual lateral-flow volume, derived from depth and hillslope area.",
    "Baseflow (m^3)": "Mean annual baseflow volume, derived from depth and hillslope area.",
    "Soil Loss (t)": "Mean annual gross hillslope soil loss in metric tonnes.",
    "Sediment Deposition (t)": "Mean annual hillslope sediment deposition in metric tonnes.",
    "Sediment Yield (t)": "Mean annual sediment mass leaving the hillslope in metric tonnes.",
    "NTU (g/L)": (
        "Historical column label for sediment yield divided by runoff plus baseflow volume. "
        "The computed unit is g/L; it is a concentration proxy, not measured turbidity in NTU."
    ),
    "Channel ID": "Channel identifier from the WEPP loss report.",
    "Wepp Channel ID": "Sequential WEPP channel identifier.",
    "Channel Enum": "Channel enumeration used to join WEPP output to watershed channel metadata.",
    "Order": "Channel order from the watershed channel network.",
    "Channel Area (ha)": "Plan-view channel area used for density calculations.",
    "Contributing Area (ha)": "Watershed area draining to the channel.",
    "Discharge Depth (mm/yr)": "Mean annual channel discharge expressed over contributing area.",
    "Upland Charge Depth (mm/yr)": "Mean annual upland inflow to the channel expressed over contributing area.",
    "Sediment Yield (tonne/yr)": "Mean annual sediment mass leaving the channel.",
    "Channel Erosion (kg/yr)": "Mean annual gross channel erosion.",
    "Channel Erosion Density (kg/ha/yr)": "Mean annual gross channel erosion per unit channel area.",
    "Soluble Reactive P (kg/yr)": "Mean annual soluble reactive phosphorus mass.",
    "Soluble Reactive P Density (kg/ha/yr)": "Mean annual soluble reactive phosphorus mass per unit area.",
    "Particulate P (kg/yr)": "Mean annual particulate phosphorus mass.",
    "Particulate P Density (kg/ha/yr)": "Mean annual particulate phosphorus mass per unit area.",
    "Total P (kg/yr)": "Mean annual total phosphorus mass.",
    "Total P Density (kg/ha/yr)": "Mean annual total phosphorus mass per unit area.",
}


def _field_metadata(field: pa.Field, key: bytes) -> str:
    if field.metadata and key in field.metadata:
        return field.metadata[key].decode()
    return ""


def _column_units(field: pa.Field) -> str:
    metadata_units = _field_metadata(field, b"units")
    if metadata_units:
        return metadata_units
    if field.name in {"value", "v", "control_v", "control-contrast_v"}:
        return "varies by `key`"
    if field.name == "control_units":
        return "unit label"
    if "(" in field.name and field.name.endswith(")"):
        return field.name.rsplit("(", 1)[1][:-1]
    return ""


def _column_description(field: pa.Field) -> str:
    metadata_description = _field_metadata(field, b"description")
    if metadata_description:
        return metadata_description
    return COMMON_COLUMN_DESCRIPTIONS.get(field.name, "Column present in the generated Parquet schema.")


def _schema_markdown(schema: pa.Schema) -> str:
    lines = ["| Column | Type | Units | Description |", "| --- | --- | --- | --- |"]
    for field in schema:
        lines.append(
            f"| `{field.name}` | `{field.type}` | {_column_units(field)} | {_column_description(field)} |"
        )
    return "\n".join(lines)


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
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table_preview_markdown(table: pa.Table) -> str:
    if table.num_rows == 0:
        return "_No rows_"
    frame = table.slice(0, min(MAX_SAMPLE_ROWS, table.num_rows)).to_pandas()
    headers = " | ".join(str(name).replace("|", "\\|") for name in frame.columns)
    separator = " | ".join(["---"] * len(frame.columns))
    rows = [" | ".join(_format_value(value) for value in row) for row in frame.values.tolist()]
    return "\n".join([headers, separator, *rows])


def _metric_keys_markdown(table: pa.Table) -> str:
    if "key" not in table.column_names:
        return ""
    columns = ["key"]
    if "units" in table.column_names:
        columns.append("units")
    frame = table.select(columns).to_pandas().drop_duplicates().sort_values(columns)
    lines = ["| Key | Units | Description |", "| --- | --- | --- |"]
    for row in frame.to_dict(orient="records"):
        key = str(row["key"])
        units = str(row.get("units") or "")
        description = OUTLET_METRIC_DESCRIPTIONS.get(
            key,
            (
                "Outlet metric emitted by the WEPP loss summary; interpret according to "
                "the literal key and reported units."
            ),
        )
        lines.append(f"| `{key}` | {units} | {description} |")
    return "\n".join(lines)


def _summarize_product(path: Path, description: str) -> str:
    table = pq.read_table(path)
    parts = [
        f"## `{path.name}`",
        "",
        description,
        "",
        f"Rows: {table.num_rows:,}.",
        "",
        "### Columns",
        "",
        _schema_markdown(table.schema),
    ]
    metric_keys = _metric_keys_markdown(table)
    if metric_keys:
        parts.extend(
            [
                "",
                "### Metric keys",
                "",
                "This is a long-form table: the modeled variables are values in `key`, not separate columns.",
                "",
                metric_keys,
            ]
        )
    parts.extend(["", "### Preview", "", _table_preview_markdown(table)])
    return "\n".join(parts)


def _generate_documentation(
    omni_dir: Path | str,
    *,
    title: str,
    overview: str,
    products: Sequence[Tuple[str, str]],
    readme_name: str,
    notes: Sequence[str],
    to_readme_md: bool,
) -> str:
    base = Path(omni_dir)
    base.mkdir(parents=True, exist_ok=True)
    sections: List[str] = [
        f"# {title}",
        "",
        overview,
        "",
        (
            "This file is generated from the Parquet files currently present in this directory. "
            "Regenerate the Omni reports after changing an artifact schema."
        ),
    ]
    if notes:
        sections.extend(["", "## Interpretation notes", ""])
        sections.extend(f"- {note}" for note in notes)

    found = False
    for filename, description in products:
        path = base / filename
        if not path.exists():
            continue
        found = True
        sections.extend(["", _summarize_product(path, description)])
    if not found:
        sections.extend(["", "_No matching Omni Parquet artifacts are currently present._"])

    markdown = "\n".join(sections).rstrip() + "\n"
    if to_readme_md:
        (base / readme_name).write_text(markdown, encoding="utf-8")
    return markdown


def generate_omni_scenarios_documentation(
    omni_dir: Path | str,
    to_readme_md: bool = True,
) -> str:
    return _generate_documentation(
        omni_dir,
        title="Omni Scenario Data",
        overview=(
            "Scenario artifacts compare complete base and treatment simulations at watershed, hillslope, "
            "and channel scales. Values are average annual results unless a column says otherwise."
        ),
        products=SCENARIO_PRODUCTS,
        readme_name="README.scenarios.md",
        notes=(
            "Each `scenario` value identifies the base run or a complete Omni treatment scenario.",
            "Do not sum density or depth columns across elements; use the corresponding mass or volume columns.",
            (
                "`scenarios.out.parquet` is long-form, while hillslope and channel summaries are wide-form. "
                "Their column sets intentionally differ."
            ),
        ),
        to_readme_md=to_readme_md,
    )


def generate_omni_contrasts_documentation(
    omni_dir: Path | str,
    to_readme_md: bool = True,
) -> str:
    return _generate_documentation(
        omni_dir,
        title="Omni Contrast Data",
        overview=(
            "Contrast artifacts compare a targeted-treatment simulation (`v`) with the matching untreated "
            "control (`control_v`) for each watershed outlet metric."
        ),
        products=CONTRAST_PRODUCTS,
        readme_name="README.contrasts.md",
        notes=(
            "`control-contrast_v = control_v - v`; positive means a reduction under treatment.",
            (
                "Selection-mode columns are conditional: `contrast_topaz_id` is cumulative-mode specific, "
                "and `group_index` is user-defined hillslope-group specific."
            ),
            (
                "`contrast_id` joins to `contrast_id_definitions.psv`; that pipe-separated file records the "
                "TOPAZ hillslope IDs selected for each contrast."
            ),
        ),
        to_readme_md=to_readme_md,
    )
