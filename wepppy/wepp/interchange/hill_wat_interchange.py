from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .schema_utils import pa_field
from .versioning import schema_with_version
from ._rust_interchange import call_wepppyo3_interchange, resolve_cli_calendar_path, version_args

LOGGER = logging.getLogger(__name__)


def _wat_source_signature(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _daily_source_fingerprint(
    path: str, signature: tuple[int, ...], cache: dict | None = None,
) -> str:
    """Bind a digest before reading, amortized across hills in one generation."""
    identity = (path, signature)
    if cache:
        if cache['identity'] != identity:
            raise ValueError("Ash WAT source changed between hillslope loads")
        return cache['digest']
    source = Path(path)
    if _wat_source_signature(source) != signature:
        raise ValueError("H.wat changed before daily loading")
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if _wat_source_signature(source) != signature:
        raise ValueError("H.wat changed during input fingerprinting")
    value = digest.hexdigest()
    if cache is not None:
        cache.update(identity=identity, digest=value)
    return value


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32()),
            pa_field("ofe_id", pa.int16()),
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32(), description="1-indexed simulation day"),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("OFE", pa.int16()),
            pa_field("P", pa.float64(), units="mm", description="Precipitation"),
            pa_field("RM", pa.float64(), units="mm", description="Rainfall+Irrigation+Snowmelt"),
            pa_field("Q", pa.float64(), units="mm", description="Daily runoff over eff length"),
            pa_field("Ep", pa.float64(), units="mm", description="Plant transpiration"),
            pa_field("Es", pa.float64(), units="mm", description="Soil evaporation"),
            pa_field("Er", pa.float64(), units="mm", description="Residue evaporation"),
            pa_field("Dp", pa.float64(), units="mm", description="Deep percolation"),
            pa_field("UpStrmQ", pa.float64(), units="mm", description="Runon added to OFE"),
            pa_field("SubRIn", pa.float64(), units="mm", description="Subsurface runon added to OFE"),
            pa_field("latqcc", pa.float64(), units="mm", description="Lateral subsurface flow"),
            pa_field("Total-Soil Water", pa.float64(), units="mm", description="Unfrozen water in soil profile"),
            pa_field("frozwt", pa.float64(), units="mm", description="Frozen water in soil profile"),
            pa_field("Snow-Water", pa.float64(), units="mm", description="Water in surface snow"),
            pa_field("QOFE", pa.float64(), units="mm", description="Daily runoff scaled to single OFE"),
            pa_field("Tile", pa.float64(), units="mm", description="Tile drainage"),
            pa_field("Irr", pa.float64(), units="mm", description="Irrigation"),
            pa_field("Area", pa.float64(), units="m^2", description="Area that depths apply over"),
            pa_field(
                "SoilWaterTotal",
                pa.float64(),
                units="mm",
                description="Full-profile soil water depth (watcon + frozwt), optional producer-authoritative term",
            ),
            pa_field(
                "ProfileDepth",
                pa.float64(),
                units="mm",
                description="Full soil profile depth (solthk(nsl)), optional producer-authoritative term",
            ),
            pa_field(
                "ProfilePorosityCap",
                pa.float64(),
                units="mm",
                description="Full-profile porosity storage capacity (sum(por * dg)), optional producer-authoritative term",
            ),
            pa_field(
                "ProfileFCStore",
                pa.float64(),
                units="mm",
                description="Full-profile field-capacity storage (sum(thetfc * dg)), optional producer-authoritative term",
            ),
            pa_field(
                "ProfileWPStore",
                pa.float64(),
                units="mm",
                description="Full-profile wilting-point storage (sum(thetdr * dg)), optional producer-authoritative term",
            ),
            pa_field(
                "InterceptionStorage",
                pa.float64(),
                units="mm",
                description="Plant/residue interception carryover storage (pintlv + resint), optional producer-authoritative term",
            ),
        ]
    )
)

WAT_OPTIONAL_COLUMN_NAMES = [
    "SoilWaterTotal",
    "ProfileDepth",
    "ProfilePorosityCap",
    "ProfileFCStore",
    "ProfileWPStore",
    "InterceptionStorage",
]

CANONICAL_COLUMN_ALIASES = {
    "wepp_id": ("wepp_id",),
    "year": ("year", "Y"),
    "sim_day_index": ("sim_day_index", "day", "D"),
    "julian": ("julian", "J"),
    "month": ("month", "M"),
    "day_of_month": ("day_of_month", "day", "D"),
    "water_year": ("water_year", "Water Year"),
    "Area": ("Area", "Area (m^2)"),
    "OFE": ("OFE", "OFE (#)"),
    "P": ("P", "P (mm)"),
    "RM": ("RM", "RM (mm)"),
    "Q": ("Q", "Q (mm)"),
    "Ep": ("Ep", "Ep (mm)"),
    "Es": ("Es", "Es (mm)"),
    "Er": ("Er", "Er (mm)"),
    "Dp": ("Dp", "Dp (mm)"),
    "UpStrmQ": ("UpStrmQ", "UpStrmQ (mm)"),
    "SubRIn": ("SubRIn", "SubRIn (mm)"),
    "latqcc": ("latqcc", "latqcc (mm)"),
    "Total-Soil Water": ("Total-Soil Water", "Total-Soil Water (mm)"),
    "frozwt": ("frozwt", "frozwt (mm)"),
    "Snow-Water": ("Snow-Water", "Snow-Water (mm)"),
    "QOFE": ("QOFE", "QOFE (mm)"),
    "Tile": ("Tile", "Tile (mm)"),
    "Irr": ("Irr", "Irr (mm)"),
    "SoilWaterTotal": ("SoilWaterTotal", "SoilWaterTotal (mm)"),
    "ProfileDepth": ("ProfileDepth", "ProfileDepth (mm)"),
    "ProfilePorosityCap": ("ProfilePorosityCap", "ProfilePorosityCap (mm)"),
    "ProfileFCStore": ("ProfileFCStore", "ProfileFCStore (mm)"),
    "ProfileWPStore": ("ProfileWPStore", "ProfileWPStore (mm)"),
    "InterceptionStorage": ("InterceptionStorage", "InterceptionStorage (mm)"),
}

PANDAS_TYPE_MAP: Dict[str, np.dtype] = {
    field.name: field.type.to_pandas_dtype()  # type: ignore[attr-defined]
    for field in SCHEMA
}

DAILY_MM_COLUMNS: Tuple[str, ...] = (
    "P",
    "RM",
    "Q",
    "Ep",
    "Es",
    "Er",
    "Dp",
    "UpStrmQ",
    "SubRIn",
    "latqcc",
    "Total-Soil Water",
    "frozwt",
    "Snow-Water",
    "QOFE",
    "Tile",
    "Irr",
    *WAT_OPTIONAL_COLUMN_NAMES,
)


def _empty_wat_dataframe() -> pd.DataFrame:
    data: Dict[str, pd.Series] = {
        name: pd.Series(dtype=dtype) for name, dtype in PANDAS_TYPE_MAP.items()
    }
    return pd.DataFrame(data)[SCHEMA.names]


def _resolve_column_aliases(path: Path) -> Dict[str, str | None]:
    schema = pq.read_schema(path)
    available = set(schema.names)
    resolved: Dict[str, str | None] = {}
    for canonical in SCHEMA.names:
        candidates = CANONICAL_COLUMN_ALIASES.get(canonical, (canonical,))
        for candidate in candidates:
            if candidate in available:
                resolved[canonical] = candidate
                break
        else:
            if canonical in available:
                resolved[canonical] = canonical
            elif canonical in WAT_OPTIONAL_COLUMN_NAMES:
                resolved[canonical] = None
            else:
                raise KeyError(f"Column '{canonical}' not found in {path}")
    return resolved


def _coerce_wat_dtypes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    for name, dtype in PANDAS_TYPE_MAP.items():
        if name in frame.columns:
            frame[name] = frame[name].astype(dtype, copy=False)
    return frame


def run_wepp_hillslope_wat_interchange(
    wepp_output_dir: Path | str,
    *,
    expected_hillslopes: int | None = None,
    max_workers: int | None = None,
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    wat_files = sorted(base.glob("H*.wat.dat"))
    if expected_hillslopes is not None and len(wat_files) != expected_hillslopes:
        raise FileNotFoundError(
            f"Expected {expected_hillslopes} hillslope wat files but found {len(wat_files)} in {base}"
        )
    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target_path = interchange_dir / "H.wat.parquet"

    cli_calendar_path = resolve_cli_calendar_path(base, log=LOGGER)
    major, minor = version_args()
    call_wepppyo3_interchange(
        "hillslope WAT",
        "hillslope_wat_files_to_parquet",
        [str(path) for path in wat_files],
        str(target_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        compression="snappy",
    )
    LOGGER.info("wepp interchange: hillslope WAT direct-to-Parquet via WEPPpyo3")
    return target_path


def load_hill_wat_dataframe(
    wepp_output_dir: Path | str,
    wepp_id: int,
    *,
    collapse: str | None = "daily",
    _source_fingerprint_cache: dict | None = None,
) -> pd.DataFrame:
    """
    Load a hillslope WAT time series for the provided WEPP output directory and hillslope id.

    Parameters
    ----------
    wepp_output_dir
        Path to the WEPP output directory (``.../wepp/output``).
    wepp_id
        Integer hillslope identifier (WEPP id).
    collapse
         ``"daily"`` (default) returns one record per simulation day aggregated across OFEs
         with local area-weighted fields, physical terminal Q, and terminal lateral
         volume divided by full hillslope area. QOFE/transfer/Tile fields retain
         diagnostic reductions; they are not whole-hillslope external fluxes.
        ``None`` returns the raw OFE-level records using
         the original schema emitted by the interchange writer.
    """
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    wat_path = base / "interchange" / "H.wat.parquet"
    if not wat_path.exists():
        raise FileNotFoundError(wat_path)

    if collapse is None:
        normalized_collapse: str | None = None
    elif isinstance(collapse, str):
        normalized_collapse = collapse.lower()
    else:
        raise TypeError("collapse must be a string or None")

    if normalized_collapse not in (None, "daily"):
        raise ValueError(f"Unsupported collapse value: {collapse!r}")

    source_signature = _wat_source_signature(wat_path)
    source_digest = None
    if normalized_collapse == "daily":
        source_digest = _daily_source_fingerprint(
            str(wat_path), source_signature, _source_fingerprint_cache
        )
    wepp_id_int = int(wepp_id)
    alias_map = _resolve_column_aliases(wat_path)

    con = duckdb.connect(database=":memory:")
    try:
        if normalized_collapse is None:
            select_list = [
                f'"{alias_map[name]}" AS "{name}"' if alias_map[name] is not None else f'NULL AS "{name}"'
                for name in SCHEMA.names
            ]
            query = f"""
                SELECT {', '.join(select_list)}
                FROM read_parquet('{wat_path.as_posix()}')
                WHERE "{alias_map['wepp_id']}" = {wepp_id_int}
                ORDER BY "{alias_map['year']}", "{alias_map['julian']}", "{alias_map['sim_day_index']}", "{alias_map['ofe_id']}"
            """
            frame = con.execute(query).df()
            if frame.empty:
                frame = _empty_wat_dataframe()
            else:
                frame = frame[SCHEMA.names]
                frame = _coerce_wat_dtypes(frame)
        else:
            area_column = alias_map["Area"]
            if area_column is None:
                raise KeyError(f"Column 'Area' not found in {wat_path}")
            # Full-source geometry precedes daily selection. Q is already a
            # whole-hill depth; lateral is a terminal local-area depth.
            quoted_path = wat_path.as_posix().replace("'", "''")
            geometry_query = f"""
                SELECT "{alias_map['ofe_id']}" AS ofe,
                       MIN("{area_column}") AS area,
                       COUNT(DISTINCT "{area_column}") AS area_count,
                       BOOL_OR("{area_column}" IS NULL OR NOT isfinite("{area_column}")
                               OR "{area_column}" <= 0) AS invalid
                FROM read_parquet('{quoted_path}')
                WHERE "{alias_map['wepp_id']}" = {wepp_id_int}
                GROUP BY 1
            """
            geometry = con.execute(geometry_query).fetchall()
            if any(ofe is None or count != 1 or invalid for ofe, _, count, invalid in geometry):
                raise ValueError("H.wat requires stationary finite positive Area and OFE identity")
            terminal = max((row[0] for row in geometry), default=0)
            hill_area = sum(row[1] for row in geometry)
            if not np.isfinite(hill_area):
                raise ValueError("H.wat area overflow")
            duplicate = con.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT "{alias_map['year']}", "{alias_map['julian']}", "{alias_map['ofe_id']}"
                    FROM read_parquet('{quoted_path}')
                    WHERE "{alias_map['wepp_id']}" = {wepp_id_int}
                    GROUP BY ALL HAVING COUNT(*) > 1)
            """).fetchone()[0]
            if duplicate:
                raise ValueError("Duplicate H.wat daily OFE observation")
            mm_volume_expr = ",\n                    ".join(
                f'SUM("{alias_map[column]}" * 0.001 * "{area_column}") AS "{column}_volume"'
                if alias_map[column] is not None
                else f'CAST(NULL AS DOUBLE) AS "{column}_volume"'
                for column in DAILY_MM_COLUMNS
            )
            query = f"""
                SELECT
                    "{alias_map['wepp_id']}" AS wepp_id,
                    "{alias_map['year']}" AS year,
                    "{alias_map['sim_day_index']}" AS sim_day_index,
                    "{alias_map['julian']}" AS julian,
                    "{alias_map['month']}" AS month,
                    "{alias_map['day_of_month']}" AS day_of_month,
                    "{alias_map['water_year']}" AS water_year,
                    SUM("{area_column}") AS Area,
                    COUNT(*) FILTER (WHERE "{alias_map['ofe_id']}" = {terminal}) AS __terminal_count,
                    MAX(CASE WHEN "{alias_map['ofe_id']}" = {terminal}
                        THEN "{alias_map['Q']}" END) AS __outlet_q,
                    MAX(CASE WHEN "{alias_map['ofe_id']}" = {terminal}
                        THEN "{alias_map['latqcc']}" * "{area_column}" / NULLIF({hill_area}, 0)
                        END) AS __outlet_lateral,
                    {mm_volume_expr}
                FROM read_parquet('{wat_path.as_posix()}')
                WHERE "{alias_map['wepp_id']}" = {wepp_id_int}
                GROUP BY
                    "{alias_map['wepp_id']}",
                    "{alias_map['year']}",
                    "{alias_map['sim_day_index']}",
                    "{alias_map['julian']}",
                    "{alias_map['month']}",
                    "{alias_map['day_of_month']}",
                    "{alias_map['water_year']}"
                ORDER BY
                    "{alias_map['year']}",
                    "{alias_map['julian']}",
                    "{alias_map['sim_day_index']}"
            """
            frame = con.execute(query).df()
            if frame.empty:
                frame = _empty_wat_dataframe()
            else:
                terminal_count = frame.pop("__terminal_count")
                outlet_q = frame.pop("__outlet_q").to_numpy(dtype=np.float64)
                outlet_lateral = frame.pop("__outlet_lateral").to_numpy(dtype=np.float64)
                if (terminal_count != 1).any() or not np.isfinite(outlet_q).all() or not np.isfinite(outlet_lateral).all():
                    raise ValueError("Missing or nonfinite known H.wat terminal observation")
                area = frame["Area"].to_numpy(dtype=np.float64, copy=False)
                for column in DAILY_MM_COLUMNS:
                    volume_col = f"{column}_volume"
                    volumes = frame.pop(volume_col).to_numpy(dtype=np.float64, copy=False)
                    depths = np.zeros_like(volumes, dtype=np.float64)
                    np.divide(volumes, area, out=depths, where=area > 0.0)
                    depths *= 1000.0
                    frame[column] = depths

                frame["Q"] = outlet_q
                frame["latqcc"] = outlet_lateral
                length = len(frame)
                frame["ofe_id"] = np.zeros(length, dtype=np.int16)
                frame["OFE"] = np.zeros(length, dtype=np.int16)
                frame = frame[SCHEMA.names]
                frame = _coerce_wat_dtypes(frame)
    finally:
        con.close()

    if source_signature != _wat_source_signature(wat_path):
        raise ValueError("H.wat changed during daily loading")
    frame.attrs["source_signature"] = source_signature
    if source_digest is not None:
        frame.attrs["water_source_sha256"] = source_digest
    frame.attrs["water_aggregation"] = "mofe-water-v2" if normalized_collapse == "daily" else "raw"
    frame.attrs["source_path"] = str(wat_path)
    frame.attrs["wepp_id"] = wepp_id_int
    frame.attrs["collapse"] = "daily" if normalized_collapse == "daily" else "raw"
    return frame
