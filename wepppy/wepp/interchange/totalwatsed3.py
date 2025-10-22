from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, TYPE_CHECKING, Any

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .schema_utils import pa_field
from .versioning import schema_with_version

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import BaseflowOpts
else:
    BaseflowOpts = Any  # type: ignore[assignment]

DATE_COLUMNS = ("year", "sim_day_index", "julian", "month", "day_of_month", "water_year")
PASS_METRIC_COLUMNS = (
    "runvol",
    "sbrunv",
    "tdet",
    "tdep",
    "seddep_1",
    "seddep_2",
    "seddep_3",
    "seddep_4",
    "seddep_5",
)

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32()),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("runvol", pa.float64(), units="m^3", description="Runoff volume"),
            pa_field("sbrunv", pa.float64(), units="m^3", description="Subsurface runoff volume"),
            pa_field("tdet", pa.float64(), units="kg", description="Total detachment"),
            pa_field("tdep", pa.float64(), units="kg", description="Total deposition"),
            pa_field("seddep_1", pa.float64(), units="kg", description="Sediment Class 1 deposition"),
            pa_field("seddep_2", pa.float64(), units="kg", description="Sediment Class 2 deposition"),
            pa_field("seddep_3", pa.float64(), units="kg", description="Sediment Class 3 deposition"),
            pa_field("seddep_4", pa.float64(), units="kg", description="Sediment Class 4 deposition"),
            pa_field("seddep_5", pa.float64(), units="kg", description="Sediment Class 5 deposition"),
            pa_field("Area", pa.float64(), units="m^2", description="Area that depths apply over"),
            pa_field("P", pa.float64(), units="m^3", description="Precipitation volume"),
            pa_field("RM", pa.float64(), units="m^3", description="Rainfall+Irrigation+Snowmelt volume"),
            pa_field("Q", pa.float64(), units="m^3", description="Daily runoff over effective length volume"),
            pa_field("Dp", pa.float64(), units="m^3", description="Deep percolation volume"),
            pa_field("latqcc", pa.float64(), units="m^3", description="Lateral subsurface flow volume"),
            pa_field("QOFE", pa.float64(), units="m^3", description="Daily runoff scaled to single OFE volume"),
            pa_field("Ep", pa.float64(), units="m^3", description="Plant transpiration volume"),
            pa_field("Es", pa.float64(), units="m^3", description="Soil evaporation volume"),
            pa_field("Er", pa.float64(), units="m^3", description="Residue evaporation volume"),
            pa_field("UpStrmQ", pa.float64(), units="mm", description="Runon added to OFE depth"),
            pa_field("SubRIn", pa.float64(), units="mm", description="Subsurface runon added to OFE depth"),
            pa_field("Total-Soil Water", pa.float64(), units="mm", description="Unfrozen water in soil profile depth"),
            pa_field("frozwt", pa.float64(), units="mm", description="Frozen water in soil profile depth"),
            pa_field("Snow-Water", pa.float64(), units="mm", description="Water in surface snow depth"),
            pa_field("Tile", pa.float64(), units="mm", description="Tile drainage depth"),
            pa_field("Irr", pa.float64(), units="mm", description="Irrigation depth"),
            pa_field("Precipitation", pa.float64(), units="mm", description="Precipitation depth"),
            pa_field("Rain+Melt", pa.float64(), units="mm", description="Rainfall+Irrigation+Snowmelt depth"),
            pa_field("Percolation", pa.float64(), units="mm", description="Deep percolation depth"),
            pa_field("Lateral Flow", pa.float64(), units="mm", description="Lateral subsurface flow depth"),
            pa_field("Runoff", pa.float64(), units="mm", description="Daily runoff scaled to single OFE depth"),
            pa_field("Transpiration", pa.float64(), units="mm", description="Plant transpiration depth"),
            pa_field("Evaporation", pa.float64(), units="mm", description="Soil + residue evaporation depth"),
            pa_field("ET", pa.float64(), units="mm", description="Total evapotranspiration depth"),
            pa_field("Baseflow", pa.float64(), units="mm", description="Baseflow depth"),
            pa_field("Aquifer losses", pa.float64(), units="mm", description="Aquifer losses depth"),
            pa_field("Reservoir Volume", pa.float64(), units="mm", description="Groundwater storage depth"),
            pa_field("Streamflow", pa.float64(), units="mm", description="Streamflow depth"),
        ]
    )
)

EMPTY_TABLE = pa.table({field.name: pa.array([], type=field.type) for field in SCHEMA}, schema=SCHEMA)


@dataclass(frozen=True)
class _QueryTargets:
    pass_path: Path
    wat_path: Path
    output_path: Path


def _normalize_wepp_ids(wepp_ids: Sequence[int] | None) -> list[int] | None:
    if wepp_ids is None:
        return None
    normalized = sorted({int(wepp_id) for wepp_id in wepp_ids})
    return normalized


def _build_where_clause(wepp_ids: list[int] | None) -> str:
    if wepp_ids is None:
        return ""
    if not wepp_ids:
        return "WHERE FALSE"
    id_list = ",".join(str(wepp_id) for wepp_id in wepp_ids)
    return f"WHERE wepp_id IN ({id_list})"


def _resolve_sim_day_column(path: Path) -> str:
    schema = pq.read_schema(path)
    if "sim_day_index" in schema.names:
        return "sim_day_index"
    if "day" in schema.names:
        return "day"
    raise KeyError(f"Neither 'sim_day_index' nor 'day' column present in {path}")


def _aggregate_pass(con: duckdb.DuckDBPyConnection, pass_path: Path, where_clause: str) -> pd.DataFrame:
    day_column = _resolve_sim_day_column(pass_path)
    query = f"""
        SELECT
            year,
            "{day_column}" AS sim_day_index,
            julian,
            month,
            day_of_month,
            water_year,
            SUM(runvol) AS runvol,
            SUM(sbrunv) AS sbrunv,
            SUM(tdet) AS tdet,
            SUM(tdep) AS tdep,
            SUM(sedcon_1 * runvol) AS seddep_1,
            SUM(sedcon_2 * runvol) AS seddep_2,
            SUM(sedcon_3 * runvol) AS seddep_3,
            SUM(sedcon_4 * runvol) AS seddep_4,
            SUM(sedcon_5 * runvol) AS seddep_5
        FROM read_parquet('{pass_path.as_posix()}')
        {where_clause}
        GROUP BY year, "{day_column}", julian, month, day_of_month, water_year
        ORDER BY year, julian, "{day_column}"
    """
    return con.execute(query).df()


def _aggregate_wat(con: duckdb.DuckDBPyConnection, wat_path: Path, where_clause: str) -> pd.DataFrame:
    day_column = _resolve_sim_day_column(wat_path)
    query = f"""
        SELECT
            year,
            "{day_column}" AS sim_day_index,
            julian,
            month,
            day_of_month,
            water_year,
            SUM(Area) AS Area,
            SUM(P * 0.001 * Area) AS P,
            SUM(RM * 0.001 * Area) AS RM,
            SUM(Q * 0.001 * Area) AS Q,
            SUM(Dp * 0.001 * Area) AS Dp,
            SUM(latqcc * 0.001 * Area) AS latqcc,
            SUM(QOFE * 0.001 * Area) AS QOFE,
            SUM(Ep * 0.001 * Area) AS Ep,
            SUM(Es * 0.001 * Area) AS Es,
            SUM(Er * 0.001 * Area) AS Er,
            SUM(UpStrmQ * 0.001 * Area) AS UpStrmQ_volume,
            SUM(SubRIn * 0.001 * Area) AS SubRIn_volume,
            SUM("Total-Soil Water" * 0.001 * Area) AS Total_Soil_Water_volume,
            SUM(frozwt * 0.001 * Area) AS frozwt_volume,
            SUM("Snow-Water" * 0.001 * Area) AS Snow_Water_volume,
            SUM(Tile * 0.001 * Area) AS Tile_volume,
            SUM(Irr * 0.001 * Area) AS Irr_volume
        FROM read_parquet('{wat_path.as_posix()}')
        {where_clause}
        GROUP BY year, "{day_column}", julian, month, day_of_month, water_year
        ORDER BY year, julian, "{day_column}"
    """
    return con.execute(query).df()


def _safe_depth(volume: np.ndarray, area: np.ndarray) -> np.ndarray:
    result = np.zeros_like(volume, dtype=np.float64)
    np.divide(volume, area, out=result, where=area > 0)
    result *= 1000.0
    return result


def _compute_baseflow(percolation_mm: np.ndarray, baseflow_opts: BaseflowOpts) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = percolation_mm.size
    if n == 0:
        return (
            np.zeros(0, dtype=np.float64),
            np.zeros(0, dtype=np.float64),
            np.zeros(0, dtype=np.float64),
        )
    reservoir = np.zeros(n, dtype=np.float64)
    baseflow = np.zeros(n, dtype=np.float64)
    aquifer_losses = np.zeros(n, dtype=np.float64)
    reservoir[0] = baseflow_opts.gwstorage
    for idx in range(n):
        if idx == 0:
            continue
        aquifer_losses[idx - 1] = reservoir[idx - 1] * baseflow_opts.dscoeff
        reservoir[idx] = reservoir[idx - 1] - baseflow[idx - 1] + percolation_mm[idx] - aquifer_losses[idx - 1]
        baseflow[idx] = reservoir[idx] * baseflow_opts.bfcoeff
    return reservoir, baseflow, aquifer_losses


def _prepare_paths(interchange_dir: Path | str) -> _QueryTargets:
    base = Path(interchange_dir)
    pass_path = base / "H.pass.parquet"
    wat_path = base / "H.wat.parquet"
    output_path = base / "totalwatsed3.parquet"
    if not pass_path.exists():
        raise FileNotFoundError(pass_path)
    if not wat_path.exists():
        raise FileNotFoundError(wat_path)
    base.mkdir(parents=True, exist_ok=True)
    return _QueryTargets(pass_path=pass_path, wat_path=wat_path, output_path=output_path)


def _finalise_table(df: pd.DataFrame) -> pa.Table:
    if df.empty:
        return EMPTY_TABLE
    int16_cols = ["year", "julian", "water_year"]
    int32_cols = ["sim_day_index"]
    int8_cols = ["month", "day_of_month"]
    for col in int16_cols:
        df[col] = df[col].astype(np.int16, copy=False)
    for col in int32_cols:
        df[col] = df[col].astype(np.int32, copy=False)
    for col in int8_cols:
        df[col] = df[col].astype(np.int8, copy=False)
    float_cols = [name for name in SCHEMA.names if name not in int16_cols + int8_cols + int32_cols]
    for col in float_cols:
        df[col] = df[col].astype(np.float64, copy=False)
    df = df[SCHEMA.names]
    return pa.Table.from_pandas(df, schema=SCHEMA, preserve_index=False)


def run_totalwatsed3(interchange_dir: Path | str, baseflow_opts: BaseflowOpts, wepp_ids: Sequence[int] | None = None) -> Path:
    """
    Create totalwatsed3.parquet in ``interchange_dir`` by aggregating H.pass and H.wat parquet outputs.
    """
    targets = _prepare_paths(interchange_dir)
    wepp_ids_normalized = _normalize_wepp_ids(wepp_ids)
    where_clause = _build_where_clause(wepp_ids_normalized)

    with duckdb.connect() as con:
        pass_df = _aggregate_pass(con, targets.pass_path, where_clause)
        wat_df = _aggregate_wat(con, targets.wat_path, where_clause)

    if wat_df.empty:
        table = EMPTY_TABLE
        pq.write_table(table, targets.output_path, compression="snappy", use_dictionary=True)
        return targets.output_path

    merged = wat_df.merge(pass_df, on=list(DATE_COLUMNS), how="left", suffixes=("", "_pass"))
    if pass_df.empty:
        merged[list(PASS_METRIC_COLUMNS)] = 0.0
    else:
        merged[list(PASS_METRIC_COLUMNS)] = merged[list(PASS_METRIC_COLUMNS)].fillna(0.0)

    area = merged["Area"].to_numpy(dtype=np.float64, copy=False)

    merged["UpStrmQ"] = _safe_depth(merged.pop("UpStrmQ_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["SubRIn"] = _safe_depth(merged.pop("SubRIn_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Total-Soil Water"] = _safe_depth(merged.pop("Total_Soil_Water_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["frozwt"] = _safe_depth(merged.pop("frozwt_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Snow-Water"] = _safe_depth(merged.pop("Snow_Water_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Tile"] = _safe_depth(merged.pop("Tile_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Irr"] = _safe_depth(merged.pop("Irr_volume").to_numpy(dtype=np.float64, copy=False), area)

    merged["Precipitation"] = _safe_depth(merged["P"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Rain+Melt"] = _safe_depth(merged["RM"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Percolation"] = _safe_depth(merged["Dp"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Lateral Flow"] = _safe_depth(merged["latqcc"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Runoff"] = _safe_depth(merged["QOFE"].to_numpy(dtype=np.float64, copy=False), area)

    merged["Transpiration"] = _safe_depth(merged["Ep"].to_numpy(dtype=np.float64, copy=False), area)
    evaporation_volume = merged["Es"].to_numpy(dtype=np.float64, copy=False) + merged["Er"].to_numpy(dtype=np.float64, copy=False)
    merged["Evaporation"] = _safe_depth(evaporation_volume, area)
    merged["ET"] = _safe_depth(
        merged["Ep"].to_numpy(dtype=np.float64, copy=False)
        + merged["Es"].to_numpy(dtype=np.float64, copy=False)
        + merged["Er"].to_numpy(dtype=np.float64, copy=False),
        area,
    )

    percolation_mm = merged["Percolation"].to_numpy(dtype=np.float64, copy=False)
    reservoir, baseflow, aquifer_losses = _compute_baseflow(percolation_mm, baseflow_opts)
    merged["Reservoir Volume"] = reservoir
    merged["Baseflow"] = baseflow
    merged["Aquifer losses"] = aquifer_losses
    merged["Streamflow"] = merged["Runoff"] + merged["Lateral Flow"] + merged["Baseflow"]

    merged = merged.sort_values(["year", "julian", "sim_day_index"], kind="mergesort").reset_index(drop=True)
    table = _finalise_table(merged)
    pq.write_table(table.combine_chunks(), targets.output_path, compression="snappy", use_dictionary=True)
    return targets.output_path


__all__ = ["run_totalwatsed3"]
