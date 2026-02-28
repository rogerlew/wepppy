"""CSV exports summarizing hillslope and channel preparation details."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Sequence

import duckdb

from wepppy.nodb.core import Ron
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path

ColumnSpec = tuple[str, str]

_SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

_HILLSLOPE_COLUMNS: tuple[ColumnSpec, ...] = (
    ("topaz_id", "topaz_id"),
    ("wepp_id", "wepp_id"),
    ("length", "length_m"),
    ("width", "width_m"),
    ("area", "area_m2"),
    ("slope_scalar", "slope_scalar"),
    ("aspect", "aspect_deg"),
    ("direction", "direction_deg"),
    ("elevation", "elevation_m"),
    ("centroid_lon", "centroid_lon"),
    ("centroid_lat", "centroid_lat"),
    ("centroid_px", "centroid_px"),
    ("centroid_py", "centroid_py"),
    ("fp_longest", "fp_longest"),
    ("fp_longest_length", "fp_longest_length_m"),
    ("fp_longest_slope", "fp_longest_slope"),
)

_CHANNEL_COLUMNS: tuple[ColumnSpec, ...] = (
    ("topaz_id", "topaz_id"),
    ("wepp_id", "wepp_id"),
    ("chn_enum", "chn_enum"),
    ("order", "stream_order"),
    ("length", "length_m"),
    ("width", "width_m"),
    ("area", "area_m2"),
    ("slope_scalar", "slope_scalar"),
    ("aspect", "aspect_deg"),
    ("direction", "direction_deg"),
    ("elevation", "elevation_m"),
    ("centroid_lon", "centroid_lon"),
    ("centroid_lat", "centroid_lat"),
    ("centroid_px", "centroid_px"),
    ("centroid_py", "centroid_py"),
)

_LANDUSE_COLUMNS: tuple[ColumnSpec, ...] = (
    ("key", "landuse_key"),
    ("desc", "landuse_desc"),
    ("landuse", "landuse_name"),
    ("_map", "landuse_map"),
    ("pct_coverage", "landuse_pct_coverage"),
    ("cancov", "landuse_cancov"),
    ("inrcov", "landuse_inrcov"),
    ("rilcov", "landuse_rilcov"),
    ("disturbed_class", "landuse_disturbed_class"),
)

_SOIL_COLUMNS: tuple[ColumnSpec, ...] = (
    ("mukey", "soil_mukey"),
    ("desc", "soil_desc"),
    ("texture", "soil_texture"),
    ("simple_texture", "soil_simple_texture"),
    ("clay", "soil_clay"),
    ("sand", "soil_sand"),
    ("avke", "soil_avke"),
    ("ll", "soil_ll"),
    ("bd", "soil_bd"),
    ("soil_depth", "soil_depth"),
    ("rock", "soil_rock"),
    ("pct_coverage", "soil_pct_coverage"),
)


def _escape_sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _quote_identifier(identifier: str) -> str:
    if _SAFE_IDENTIFIER.match(identifier):
        return identifier
    return f'"{identifier.replace("\"", "\"\"")}"'


def _read_parquet_columns(con: duckdb.DuckDBPyConnection, parquet_path: Path) -> set[str]:
    description = con.execute(
        f"SELECT * FROM read_parquet('{_escape_sql_path(parquet_path)}') LIMIT 0"
    ).description
    return {desc[0] for desc in description}


def _select_columns(prefix: str, available: set[str], columns: Sequence[ColumnSpec]) -> list[str]:
    selections: list[str] = []
    for column, alias in columns:
        if column in available:
            selections.append(f"{prefix}.{_quote_identifier(column)} AS {alias}")
    return selections


def _resolve_id_column(columns: set[str], parquet_path: Path) -> str:
    if "topaz_id" in columns:
        return "topaz_id"
    if "TopazID" in columns:
        return "TopazID"
    raise ValueError(f"Missing topaz_id column in {parquet_path}")


def _copy_to_csv(con: duckdb.DuckDBPyConnection, sql: str, output_path: Path) -> None:
    out_sql = _escape_sql_path(output_path)
    con.execute(f"COPY ({sql}) TO '{out_sql}' (HEADER, DELIMITER ',')")


def export_hillslopes_prep_details(wd: str) -> str:
    """Write a CSV describing each hillslope prepared during model setup.

    Args:
        wd: Working directory for the WEPP run.

    Returns:
        Absolute path to the generated `hillslopes.csv`.
    """
    ron = Ron.getInstance(wd)
    out_dir = Path(ron.export_dir) / "prep_details"
    out_dir.mkdir(parents=True, exist_ok=True)

    hillslopes_parquet = pick_existing_parquet_path(wd, "watershed/hillslopes.parquet")
    if hillslopes_parquet is None:
        raise FileNotFoundError(
            "Missing watershed hillslopes parquet (watershed/hillslopes.parquet)"
        )
    landuse_parquet = pick_existing_parquet_path(wd, "landuse/landuse.parquet")
    if landuse_parquet is None:
        raise FileNotFoundError("Missing landuse parquet (landuse/landuse.parquet)")
    soils_parquet = pick_existing_parquet_path(wd, "soils/soils.parquet")
    if soils_parquet is None:
        raise FileNotFoundError("Missing soils parquet (soils/soils.parquet)")

    output_path = out_dir / "hillslopes.csv"

    with duckdb.connect() as con:
        hills_cols = _read_parquet_columns(con, hillslopes_parquet)
        landuse_cols = _read_parquet_columns(con, landuse_parquet)
        soils_cols = _read_parquet_columns(con, soils_parquet)

        hills_id = _resolve_id_column(hills_cols, hillslopes_parquet)
        landuse_id = _resolve_id_column(landuse_cols, landuse_parquet)
        soils_id = _resolve_id_column(soils_cols, soils_parquet)

        select_parts = _select_columns("hills", hills_cols, _HILLSLOPE_COLUMNS)
        if "area" in hills_cols:
            select_parts.append(
                f"hills.{_quote_identifier('area')} / 10000.0 AS area_ha"
            )
        select_parts.extend(_select_columns("lu", landuse_cols, _LANDUSE_COLUMNS))
        select_parts.extend(_select_columns("soil", soils_cols, _SOIL_COLUMNS))

        if not select_parts:
            raise ValueError("No columns available for hillslope prep details export")

        order_column = "wepp_id" if "wepp_id" in hills_cols else hills_id
        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM read_parquet('{_escape_sql_path(hillslopes_parquet)}') AS hills "
            f"LEFT JOIN read_parquet('{_escape_sql_path(landuse_parquet)}') AS lu "
            f"ON hills.{_quote_identifier(hills_id)} = lu.{_quote_identifier(landuse_id)} "
            f"LEFT JOIN read_parquet('{_escape_sql_path(soils_parquet)}') AS soil "
            f"ON hills.{_quote_identifier(hills_id)} = soil.{_quote_identifier(soils_id)} "
            f"ORDER BY hills.{_quote_identifier(order_column)}"
        )

        _copy_to_csv(con, sql, output_path)

    return str(output_path)


def export_channels_prep_details(wd: str) -> str:
    """Write a CSV describing each channel prepared during model setup.

    Args:
        wd: Working directory for the WEPP run.

    Returns:
        Absolute path to the generated `channels.csv`.
    """
    ron = Ron.getInstance(wd)
    out_dir = Path(ron.export_dir) / "prep_details"
    out_dir.mkdir(parents=True, exist_ok=True)

    channels_parquet = pick_existing_parquet_path(wd, "watershed/channels.parquet")
    if channels_parquet is None:
        raise FileNotFoundError(
            "Missing watershed channels parquet (watershed/channels.parquet)"
        )
    output_path = out_dir / "channels.csv"

    with duckdb.connect() as con:
        channel_cols = _read_parquet_columns(con, channels_parquet)
        channel_id = _resolve_id_column(channel_cols, channels_parquet)

        select_parts = _select_columns("chn", channel_cols, _CHANNEL_COLUMNS)
        if "area" in channel_cols:
            select_parts.append(
                f"chn.{_quote_identifier('area')} / 10000.0 AS area_ha"
            )

        if not select_parts:
            raise ValueError("No columns available for channel prep details export")

        if "chn_enum" in channel_cols:
            order_column = "chn_enum"
        elif "wepp_id" in channel_cols:
            order_column = "wepp_id"
        else:
            order_column = channel_id

        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM read_parquet('{_escape_sql_path(channels_parquet)}') AS chn "
            f"ORDER BY chn.{_quote_identifier(order_column)}"
        )

        _copy_to_csv(con, sql, output_path)

    return str(output_path)
