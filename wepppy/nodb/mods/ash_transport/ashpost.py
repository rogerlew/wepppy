# Copyright (c) 2016-2023, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.


"""Post-processing and aggregation utilities for ash transport outputs."""

from __future__ import annotations

import os
from pathlib import Path
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from copy import deepcopy

import shutil
import math
from typing import TYPE_CHECKING, Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

# non-standard
import numpy as np

from wepppy.all_your_base.dateutils import YearlessDate
import pandas as pd
import dask.dataframe as dd
import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base import isfloat
from wepppy.all_your_base.stats import probability_of_occurrence, weibull_series

from wepppy.nodb.base import NoDbBase

from pprint import pprint

from wepppy.query_engine.activate import update_catalog_entry
from wepppy.wepp.interchange.schema_utils import pa_field

from .ashpost_documentation import generate_ashpost_documentation
from .ashpost_versioning import (
    ASHPOST_VERSION,
    remove_incompatible_outputs,
    schema_with_version,
    write_version_manifest,
)

if TYPE_CHECKING:
    from wepppy.nodb.mods.ash_transport.ash import Ash

__all__ = [
    'AshPostNoDbLockedException',
    'AshPost',
]

common_cols =  ['area (ha)', 'topaz_id', 'year', 'mo', 'da', 'julian', 'days_from_fire (days)', 'year0', 'burn_class']

out_cols = ['year0', 'year', 'julian', 'days_from_fire (days)',
            'wind_transport (tonne/ha)', 'water_transport (tonne/ha)', 'ash_transport (tonne/ha)',
            'ash_runoff (mm)', 'ash_depth (mm)', 'transportable_ash (tonne/ha)']

VOLUME_COLUMNS_M3 = (
    'ash_depth (m^3)',
    'ash_runoff (m^3)',
)

ASH_POST_FILES: Dict[str, str] = {
    'hillslope_annuals': 'hillslope_annuals.parquet',
    'watershed_annuals': 'watershed_annuals.parquet',
    'watershed_daily': 'watershed_daily.parquet',
    'watershed_daily_by_burn_class': 'watershed_daily_by_burn_class.parquet',
    'watershed_cumulatives': 'watershed_cumulatives.parquet',
}

COLUMN_DESCRIPTIONS: Dict[str, str] = {
    'topaz_id': 'TOPAZ hillslope identifier for the modeled subwatershed.',
    'area': 'Surface area represented by the aggregation.',
    'burn_class': 'Soil burn severity class assigned to the hillslope (1=unburned, 4=high).',
    'year0': 'Calendar year containing the simulated fire ignition date.',
    'year': 'Simulation calendar year for the record.',
    'julian': 'Julian day of year for the record.',
    'da': 'Day of month for the record.',
    'mo': 'Month of year for the record.',
    'days_from_fire': 'Number of days elapsed since the fire ignition.',
    'fire_year': 'Zero-based index of the post-fire year (0 during fire year).',
    'precip': 'Daily precipitation depth applied to the hillslope.',
    'rainmelt': 'Daily rainfall plus snowmelt depth.',
    'snow_water_equivalent': 'Snow water equivalent depth.',
    'runoff': 'Daily surface runoff depth.',
    'tot_soil_water': 'Total soil water content.',
    'infiltration': 'Daily infiltration depth.',
    'cum_infiltration': 'Cumulative infiltration depth since the fire.',
    'cum_runoff': 'Cumulative surface runoff depth since the fire.',
    'bulk_density': 'Modeled ash bulk density.',
    'porosity': 'Modeled surface ash layer porosity.',
    'remaining_ash': 'Ash mass remaining on the hillslope.',
    'transportable_ash': 'Ash mass still available for transport.',
    'ash_depth': 'Modeled ash layer depth or volume depending on units.',
    'ash_runoff': 'Ash-laden runoff depth.',
    'transport': 'Instantaneous transport capacity used in dynamic routing.',
    'tau': 'Dynamic transport capacity coefficient τ.',
    'k_r': 'Runoff transport depletion coefficient k_r.',
    'M_0': 'Reference transport capacity M₀.',
    'water_transport': 'Ash transported by water runoff for the interval.',
    'wind_transport': 'Ash transported by wind for the interval.',
    'ash_transport': 'Total ash transported by wind and water for the interval.',
    'ash_decomp': 'Ash mass lost to decomposition for the interval.',
    'cum_water_transport': 'Cumulative water-driven ash transport since the fire.',
    'cum_wind_transport': 'Cumulative wind-driven ash transport since the fire.',
    'cum_ash_transport': 'Cumulative total ash transport since the fire.',
    'cum_ash_runoff': 'Cumulative ash-laden runoff depth since the fire.',
    'cum_ash_decomp': 'Cumulative ash decomposition since the fire.',
}

UINT16_COLUMNS = {
    'topaz_id',
    'year0',
    'year',
    'julian',
    'days_from_fire (days)',
    'fire_year (yr)',
    'da',
    'mo',
}

UINT8_COLUMNS = {
    'burn_class',
}

ReturnPeriodEntry = Dict[str, Any]
ReturnPeriods = Dict[int, ReturnPeriodEntry]
BurnClassReturnPeriods = Dict[int, Dict[str, ReturnPeriods]]


def _base_column_name(column: str) -> str:
    """Extract the base column name without any unit suffix."""
    return column.split(' (')[0]


def _infer_units(column: str) -> str | None:
    """Return the unit suffix embedded in a column name, if present."""
    if '(' in column and column.endswith(')'):
        return column[column.rfind('(') + 1:-1]
    return None


def _describe_column(column: str) -> str | None:
    """Map a column name to a human-readable description."""
    base = _base_column_name(column)
    if base in COLUMN_DESCRIPTIONS:
        return COLUMN_DESCRIPTIONS[base]
    if base.startswith('cum_'):
        origin = base[4:]
        if origin in COLUMN_DESCRIPTIONS:
            return f"Cumulative {COLUMN_DESCRIPTIONS[origin][0].lower() + COLUMN_DESCRIPTIONS[origin][1:]}"
    return None


def _cast_integral_columns(df: pd.DataFrame) -> None:
    """Downcast known integral columns to compact unsigned dtypes."""
    for column in UINT16_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype('uint16')
    for column in UINT8_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype('uint8')


def _add_per_area_columns(
    df: pd.DataFrame,
    source_columns: Sequence[str],
    area_column: str = 'area (ha)',
) -> None:
    """Add per-area columns (tonne/ha, mm) derived from volumetric inputs."""
    if area_column not in df.columns:
        return
    area = df[area_column].to_numpy(dtype=np.float64)
    with np.errstate(divide='ignore', invalid='ignore'):
        for col in source_columns:
            if col not in df.columns:
                continue
            per_ha_col = col.replace(' (tonne)', ' (tonne/ha)').replace(' (m^3)', ' (mm)')
            result = np.divide(
                df[col].to_numpy(dtype=np.float64),
                area,
                out=np.zeros_like(area, dtype=np.float64),
                where=area > 0,
            )
            if per_ha_col.endswith(' (mm)'):
                # convert average depth from meters to millimeters
                result *= 1000.0 / 10000.0
            df[per_ha_col] = result


def _write_parquet(df: pd.DataFrame, path: str) -> None:
    """Persist a DataFrame with schema metadata and AshPost versioning."""
    if not len(df.columns):
        empty_schema = schema_with_version(pa.schema([]))
        table = pa.Table.from_arrays([], schema=empty_schema)
        pq.write_table(table, path, compression='snappy')
        return

    table = pa.Table.from_pandas(df, preserve_index=False)
    schema_fields = []
    for field in table.schema:
        units = _infer_units(field.name)
        description = _describe_column(field.name)
        schema_fields.append(pa_field(field.name, field.type, units=units, description=description))
    schema = pa.schema(schema_fields)
    schema = schema_with_version(schema)
    table = table.cast(schema)
    pq.write_table(table, path, compression='snappy')


def calculate_return_periods(
    df: pd.DataFrame,
    measure: str,
    recurrence: Sequence[int],
    num_fire_years: float,
    cols_to_extract: Sequence[str],
) -> ReturnPeriods:
    """Compute Weibull return period stats for a single measure."""

    measure_rank = measure.replace(' (tonne)', '_rank')\
                          .replace(' (days)', '_rank')
    measure_ri = measure.replace(' (tonne)', '_ri')\
                        .replace(' (days)', '_ri')
    measure_poo = measure.replace(' (tonne)', '_probability')\
                         .replace(' (days)', '_probability')

    cols_to_extract = [measure, measure_rank, measure_ri, measure_poo] + cols_to_extract

    df.sort_values(by=measure, ascending=False, inplace=True)

    df[measure_rank] = df[measure].rank(ascending=False)
    df[measure_ri] = (num_fire_years + 1) / df[measure_rank]
    df[measure_poo] = df[measure_ri].apply(lambda ri: probability_of_occurrence(ri, 1.0))

    rec = weibull_series(recurrence, num_fire_years)


    num_events = (df[measure] > 0).sum()
    return_periods: ReturnPeriods = {}
    for retperiod in recurrence:
        if retperiod not in rec:
            return_periods[retperiod] = { measure: 0,
                                          'probability': 0,
                                          'rank': 0,
                                          'ri': 0 }
        else:
            indx = rec[retperiod]
            if indx > num_events - 1:
                indx = num_events - 1

            _row = df.iloc[indx][cols_to_extract].to_dict()
            for _m in _row:
                if _m in ('date_int', 'year0', 'year', 'mo', 'da', 'days_from_fire (days)', measure_rank):
                    _row[_m] = int(_row[_m])
                elif isfloat(_row[_m]):
                    _row[_m] = float(_row[_m])
                else:
                    _row[_m] = str(_row[_m])

            _row['probability'] = _row[measure_poo]
            _row['rank'] = _row[measure_rank]
            _row['ri'] = _row[measure_ri]

            del _row[measure_poo]
            del _row[measure_rank]
            del _row[measure_ri]

            return_periods[retperiod] = _row

    return return_periods


def calculate_cumulative_transport(
    df: pd.DataFrame,
    recurrence: Sequence[int],
    ash_post_dir: str,
) -> ReturnPeriods:
    """Aggregate cumulative transport metrics and compute return periods."""

    # Early exit if no data
    if df.empty:
        return {}

    # group the filtered rows by year0 and aggregate the cum_ columns and weighted average of days_from_fire
    agg_d = {'days_from_fire (days)': 'first'}

    for col_name in df.columns:
        if col_name.startswith('cum_'):
            agg_d[col_name] = 'sum'

    df_agg = df.groupby('year0').agg(agg_d)

    # create a new dataframe with one row per unique year
    cum_df = pd.DataFrame({'year0': df['year0'].unique()})

    # merge the aggregated data with the new dataframe
    cum_df = pd.merge(cum_df, df_agg, on='year0')
    cum_df.sort_values('year0', inplace=True)
    _cast_integral_columns(cum_df)
    _write_parquet(cum_df, _join(ash_post_dir, ASH_POST_FILES['watershed_cumulatives']))

    # calculate return intervals and probabilities for cumulative results
    num_fire_years = len(cum_df)
    
    # Guard against empty dataframe
    if num_fire_years == 0:
        return {}
    
    cum_return_periods: ReturnPeriods = {}
    cols_to_extract = ['year0']

    for measure in ['cum_wind_transport (tonne)', 'cum_water_transport (tonne)',
                    'cum_ash_transport (tonne)', 'days_from_fire (days)']:
        cum_return_periods[measure] = calculate_return_periods(cum_df, measure, recurrence, num_fire_years,
                                                               cols_to_extract)

    return cum_return_periods


def calculate_hillslope_statistics(
    df: pd.DataFrame,
    ash: "Ash",
    ash_post_dir: str,
    first_year_only: bool = False,
) -> None:
    """Summarize hillslope-level transport metrics and persist annual stats."""
    agg_d = { 'wind_transport (tonne/ha)': 'sum',
              'water_transport (tonne/ha)': 'sum',
              'ash_transport (tonne/ha)': 'sum' }

    # group the dataframe by topaz_id and year, and calculate the sum of x within each group

#    print(len(df.index), 'rows in hillslope data frame')
    if first_year_only:
        df = df[df['days_from_fire (days)'] <= 365]

#    df.to_parquet(_join(ash_post_dir, 'sanity_check_first_year.parquet'), index=False)
#    print(len(df.index), 'rows in hillslope data frame')

    df_hillslope_annuals = df.groupby(['topaz_id', 'year']).agg(agg_d).reset_index()
    df_hillslope_average_annuals = df_hillslope_annuals.groupby('topaz_id').mean(numeric_only=True).reset_index()
    if 'year' in df_hillslope_average_annuals.columns:
        df_hillslope_average_annuals.drop('year', axis=1, inplace=True)
    _cast_integral_columns(df_hillslope_average_annuals)
    ordered_cols = [
        'topaz_id',
        'wind_transport (tonne/ha)',
        'water_transport (tonne/ha)',
        'ash_transport (tonne/ha)',
    ]
    df_hillslope_average_annuals = df_hillslope_average_annuals[[col for col in ordered_cols if col in df_hillslope_average_annuals.columns]]
    _write_parquet(df_hillslope_average_annuals, _join(ash_post_dir, ASH_POST_FILES['hillslope_annuals']))


def calculate_watershed_statisics(
    df: pd.DataFrame,
    ash_post_dir: str,
    recurrence: Sequence[int],
    burn_classes: Sequence[int] = (1, 2, 3),
    first_year_only: bool = False,
) -> tuple[ReturnPeriods, BurnClassReturnPeriods]:
    """Aggregate watershed transport metrics and compute return periods."""
    burn_classes = list(burn_classes)

    if first_year_only:
        df = df[df['days_from_fire (days)'] <= 365]

    global common_cols

    #df.to_pickle(_join(ash_post_dir, 'full.pkl'))

    measures = ['wind_transport (tonne)', 'water_transport (tonne)', 'ash_transport (tonne)']

    ws_cols_to_drop = ['date_int', 'topaz_id']
    for col in ['da', 'mo', 'julian']:
        if col in out_cols:
            ws_cols_to_drop.append(col)

    agg_d = {}
    for col in df.columns:
        if col == 'area (ha)':
            agg_d[col] = 'sum'
            continue
        # Sum volumetric/mass columns; depths and densities will be dropped and recalculated
        if 'm^3' in col or 'tonne' in col:
            agg_d[col] = 'sum'
        if col in common_cols:
            agg_d[col] = 'first'

        # Drop per-area columns; they will be recalculated from totals after aggregation
        if 'mm' in col or 'tonne/ha' in col or col.startswith('cum_'):
            ws_cols_to_drop.append(col)

    df_annuals = df.groupby('year', as_index=False).agg(agg_d)
    df_annuals.drop(ws_cols_to_drop, axis=1, inplace=True, errors='ignore')
    df_annuals.drop(columns=['burn_class'], inplace=True, errors='ignore')
    _cast_integral_columns(df_annuals)
    tonne_cols = [
        'wind_transport (tonne)',
        'water_transport (tonne)',
        'ash_transport (tonne)',
        'transportable_ash (tonne)',
    ]
    volume_cols_annual = [col for col in VOLUME_COLUMNS_M3 if col in df_annuals.columns]
    _add_per_area_columns(df_annuals, tonne_cols)
    if volume_cols_annual:
        _add_per_area_columns(df_annuals, volume_cols_annual)
    annual_cols = [
        'year',
        'year0',
        'days_from_fire (days)',
        'area (ha)',
        'wind_transport (tonne)',
        'wind_transport (tonne/ha)',
        'water_transport (tonne)',
        'water_transport (tonne/ha)',
        'ash_transport (tonne)',
        'ash_transport (tonne/ha)',
        'transportable_ash (tonne)',
        'transportable_ash (tonne/ha)',
    ]
    for volume_col in volume_cols_annual:
        annual_cols.extend([
            volume_col,
            volume_col.replace(' (m^3)', ' (mm)'),
        ])
    df_annuals = df_annuals[[col for col in annual_cols if col in df_annuals.columns]]
    _write_parquet(df_annuals, _join(ash_post_dir, ASH_POST_FILES['watershed_annuals']))

    df_daily = df.groupby(['year0', 'year', 'julian'], as_index=False).agg(agg_d)
    df_daily.drop(columns=['burn_class'], inplace=True, errors='ignore')
    _cast_integral_columns(df_daily)
    existing_density_cols = [col for col in df_daily.columns if '(tonne/ha)' in col or col.endswith(' (mm)')]
    if existing_density_cols:
        df_daily.drop(columns=existing_density_cols, inplace=True)
    volume_cols_daily = [col for col in VOLUME_COLUMNS_M3 if col in df_daily.columns]
    _add_per_area_columns(df_daily, tonne_cols)
    if volume_cols_daily:
        _add_per_area_columns(df_daily, volume_cols_daily)
    daily_cols = [
        'year0',
        'year',
        'julian',
        'days_from_fire (days)',
        'area (ha)',
        'wind_transport (tonne)',
        'wind_transport (tonne/ha)',
        'water_transport (tonne)',
        'water_transport (tonne/ha)',
        'ash_transport (tonne)',
        'ash_transport (tonne/ha)',
        'transportable_ash (tonne)',
        'transportable_ash (tonne/ha)',
    ]
    for volume_col in volume_cols_daily:
        daily_cols.extend([
            volume_col,
            volume_col.replace(' (m^3)', ' (mm)'),
        ])
    df_daily = df_daily[[col for col in daily_cols if col in df_daily.columns]]
    _write_parquet(df_daily, _join(ash_post_dir, ASH_POST_FILES['watershed_daily']))

    num_days = len(df_daily.julian)
    num_fire_years = num_days / 365.25
    return_periods = {}
    cols_to_extract = ['days_from_fire (days)', 'year0', 'year', 'julian']

    # Group the DataFrame by 'date_int' and 'burn_class' columns
    grouped_df = df.groupby(['year0', 'year', 'julian', 'burn_class'], as_index=False).agg(agg_d)
    _cast_integral_columns(grouped_df)
    existing_density_cols = [col for col in grouped_df.columns if '(tonne/ha)' in col or col.endswith(' (mm)')]
    if existing_density_cols:
        grouped_df.drop(columns=existing_density_cols, inplace=True)
    volume_cols_class = [col for col in VOLUME_COLUMNS_M3 if col in grouped_df.columns]
    _add_per_area_columns(grouped_df, tonne_cols)
    if volume_cols_class:
        _add_per_area_columns(grouped_df, volume_cols_class)
    class_cols = [
        'burn_class',
        'year0',
        'year',
        'julian',
        'days_from_fire (days)',
        'area (ha)',
        'wind_transport (tonne)',
        'wind_transport (tonne/ha)',
        'water_transport (tonne)',
        'water_transport (tonne/ha)',
        'ash_transport (tonne)',
        'ash_transport (tonne/ha)',
        'transportable_ash (tonne)',
        'transportable_ash (tonne/ha)',
    ]
    for volume_col in volume_cols_class:
        class_cols.extend([
            volume_col,
            volume_col.replace(' (m^3)', ' (mm)'),
        ])
    grouped_df = grouped_df[[col for col in class_cols if col in grouped_df.columns]]
    _write_parquet(grouped_df, _join(ash_post_dir, ASH_POST_FILES['watershed_daily_by_burn_class']))

    # Initialize the return_periods dictionary
    burn_class_return_periods = {}
    for burn_class in burn_classes:
        burn_class_return_periods[burn_class] = {}
        for measure in measures:
            burn_class_return_periods[burn_class][measure] = {}
            for rec in recurrence:
                burn_class_return_periods[burn_class][measure][rec] = {}

    for measure in measures:
        return_periods[measure] = calculate_return_periods(df_daily, measure, recurrence, num_fire_years,
                                                           cols_to_extract)

        for rec in return_periods[measure]:
            v = return_periods[measure][rec][measure]

            year0 = return_periods[measure][rec].get('year0', None)
            year = return_periods[measure][rec].get('year', None)
            julian = return_periods[measure][rec].get('julian', None)

            for burn_class in burn_classes:
                burn_class_return_periods[burn_class][measure][rec] = deepcopy(return_periods[measure][rec])
                burn_class_return_periods[burn_class][measure][rec][measure] = 0.0

                if v == 0:
                    continue

                # Calculate return_periods using the values for the current burn_class
                # Boolean indexing to filter rows

                filtered_df = grouped_df[(grouped_df['year0'] == np.uint16(year0)) &
                                         (grouped_df['year'] == np.uint16(year)) &
                                         (grouped_df['julian'] == np.uint16(julian)) &
                                         (grouped_df['burn_class'] == np.uint8(burn_class))]

                num_rows = len(filtered_df)

                if num_rows == 0:
                    continue
                elif num_rows == 1:
                    burn_class_return_periods[burn_class][measure][rec][measure] = float(filtered_df.iloc[0][measure])
                else:
                    raise Exception('Unexpected number of rows: {}'.format(num_rows))

    return return_periods, burn_class_return_periods


def read_hillslope_out_fn(
    out_fn: str,
    meta_data: Optional[Mapping[str, Any]] = None,
    meta_data_types: Optional[Mapping[str, str]] = None,
    cumulative: bool = False,
) -> pd.DataFrame:
    """Load a single hillslope ash parquet and attach run metadata."""
    global common_cols, out_cols

    if cumulative:
        df = pd.read_parquet(out_fn)
    else:
        df = pd.read_parquet(out_fn, columns=out_cols)

    if meta_data is not None:
        for key, value in meta_data.items():
            if meta_data_types and key in meta_data_types and meta_data_types[key] == 'category':
                df[key] = pd.Categorical([value] * len(df))
            else:
                df[key] = pd.Series([value] * len(df)).astype(meta_data_types.get(key) if meta_data_types else None)

    # Create a unique index from year and julian columns (avoid uint16 overflow)
    year_ord = df['year'].astype(np.int32, copy=False)
    julian_ord = df['julian'].astype(np.int32, copy=False)
    df['date_int'] = year_ord * 1000 + julian_ord
    df.set_index('date_int', inplace=True)

    # Select columns to aggregate
    agg_d = {}
    for col in df.columns:
        if '(mm)' in col or '(tonne/ha)' in col or '(gm/cm3)' in col:
            agg_d[col] = 'sum'
        if col in common_cols:
            agg_d[col] = 'first'

    # Pivot and aggregate the data
    df_agg =  df.groupby('date_int').agg(agg_d)

    # Reset the index to get a dataframe with one row per unique combination of year, julian, and topaz_id
    df_agg.reset_index(inplace=True)

    area_ha = float(df_agg['area (ha)'].iloc[0])

    # Convert columns in tonne/ha to tonne by multiplying by area_ha
    for col in df_agg.columns:
        if 'tonne/ha' in col:
            df_agg[col.replace('tonne/ha', 'tonne')] = df_agg[col] * area_ha

    # Convert columns in mm to m^3 using area_ha
    for col in df_agg.columns:
        if 'mm' in col:
            df_agg[col.replace('mm', 'm^3')] = ( df_agg[col] * 0.001) *  (area_ha * 10000)

    if cumulative:
        # Get the last day for each fire year (year0) instead of filtering by exact zero
        # This is more robust than checking transportable_ash == 0.0 due to floating-point issues
        df_agg = df_agg.sort_values(['year0', 'julian'])
        df_agg = df_agg.groupby('year0').tail(1)
    return df_agg



def watershed_daily_aggregated(
    wd: str,
    recurrence: Sequence[int] = (1000, 500, 200, 100, 50, 25, 20, 10, 5, 2),
    verbose: bool = True,
) -> Optional[tuple[ReturnPeriods, ReturnPeriods, BurnClassReturnPeriods]]:
    """Aggregate hillslope outputs across the watershed and compute summaries."""
    #
    # Setup stuff
    #

    from wepppy.nodb.core import Watershed
    from wepppy.nodb.mods.ash_transport import Ash

    # Get NoDB instances
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
    ash = Ash.getInstance(wd)

    ash_post_dir = _join(ash.ash_dir, 'post')
    os.makedirs(ash_post_dir, exist_ok=True)

    #
    # Read all hillslope output files to a single df
    #

    # loop over the hillslopes and read their ash output files.
    hill_data_frames = []
    for topaz_id in watershed._subs_summary:
        # get the wepp_id
        wepp_id = translator.wepp(top=topaz_id)

        # get the burn class
        burn_class = ash.meta[topaz_id]['burn_class']

        # get the area in hectares
        area_m2 = watershed.hillslope_area(topaz_id)
        area_ha = area_m2 / 10000


        # get the list of output files
        out_fn = _join(ash.ash_dir, f'H{wepp_id}_ash.parquet')

        if _exists(out_fn):
            # read the output files into dataframes and append them to hill_data_frames
            meta = {"topaz_id": topaz_id, "area (ha)": area_ha, "burn_class": burn_class}
            meta_dtypes = {"topaz_id": "uint16", "area (ha)": "float32", "burn_class": "uint8"}
            hill_data_frames.append(read_hillslope_out_fn(out_fn,
                meta_data=meta,
                meta_data_types=meta_dtypes))

    if hill_data_frames == []:
        return None


    # Combine all data into a single DataFrame
    df = pd.concat(hill_data_frames, ignore_index=True)

    calculate_hillslope_statistics(deepcopy(df), ash, ash_post_dir, first_year_only=True)

    return_periods, burn_class_return_periods = calculate_watershed_statisics(deepcopy(df), ash_post_dir, recurrence, first_year_only=True)

    del df
    del hill_data_frames

    # Calculate cumulative return periods
    # read the last day of each fire run
    hill_data_frames = []
    for topaz_id in watershed._subs_summary:
        # get the wepp_id
        wepp_id = translator.wepp(top=topaz_id)

        # get the burn class
        burn_class = ash.meta[topaz_id]['burn_class']

        # get the area in hectares
        area_m2 = watershed.hillslope_area(topaz_id)
        area_ha = area_m2 / 10000

        # get the list of output files
        out_fn = _join(ash.ash_dir, f'H{wepp_id}_ash.parquet')

        if _exists(out_fn):
            # read the output files into dataframes and append them to hill_data_frames
            meta = {"topaz_id": topaz_id, "area (ha)": area_ha, "burn_class": burn_class}
            meta_dtypes = {"topaz_id": "uint16", "area (ha)": "float32", "burn_class": "uint8"}
            hill_data_frames.append(read_hillslope_out_fn(out_fn,
                meta_data=meta, meta_data_types=meta_dtypes, cumulative=True))

    # combine to single dataframe
    df = pd.concat(hill_data_frames, ignore_index=True)

    cum_return_periods = calculate_cumulative_transport(df, recurrence, ash_post_dir)

    del df
    del hill_data_frames

    # return all the results
    return return_periods, cum_return_periods, burn_class_return_periods



class AshPostNoDbLockedException(Exception):
    """Raised when AshPost operations encounter a locked NoDb instance."""


class AshPost(NoDbBase):
    """Coordinates post-processing of ash transport model outputs."""
    
    __name__ = 'AshPost'

    _js_decode_replacements = (("\"pw0_stats\"", "\"_pw0_stats\""),)

    filename = 'ashpost.nodb'

    _return_periods: Optional[ReturnPeriods]
    _cum_return_periods: Optional[ReturnPeriods]
    _burn_class_return_periods: Optional[BurnClassReturnPeriods]

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(AshPost, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._return_periods = None
            self._cum_return_periods = None
            self._burn_class_return_periods = None

    @property
    def return_periods(self) -> Optional[ReturnPeriods]:
        """Return-period statistics aggregated across the watershed."""
        return self._return_periods

    @property
    def burn_class_return_periods(self) -> Optional[BurnClassReturnPeriods]:
        """Return-period statistics stratified by burn class."""
        return self._burn_class_return_periods

    @property
    def cum_return_periods(self) -> Optional[ReturnPeriods]:
        """Cumulative transport return periods across fire years."""
        return self._cum_return_periods

    @property
    def pw0_stats(self) -> Dict[str, Dict[str, float]]:
        """Summaries of cumulative transport by burn class."""

        meta = self.meta

        # Initialize the dictionary with default values
        pw0_stats = {
            burn_class: {
                'count': 0,
                'cum_water_transport (tonne)': 0,
                'cum_wind_transport (tonne)': 0,
                'cum_ash_transport (tonne)': 0,
            }
            for burn_class in ['1', '2', '3', '4']
        }

        for topaz_id, hill_annuals in self.hillslope_annuals.items():
            burn_class = str(meta[topaz_id]['burn_class'])
            area_ha = meta[topaz_id]['area_ha']

            pw0_stats[burn_class]['cum_water_transport (tonne)'] += hill_annuals['water_transport (tonne/ha)'] * area_ha
            pw0_stats[burn_class]['cum_wind_transport (tonne)'] += hill_annuals['wind_transport (tonne/ha)'] * area_ha
            pw0_stats[burn_class]['cum_ash_transport (tonne)'] += hill_annuals['ash_transport (tonne/ha)'] * area_ha

        return pw0_stats

    @property
    def recurrence_intervals(self) -> list[str]:
        rec_int = sorted([int(k) for k in self._return_periods['ash_transport (tonne)']])
        return [str(k) for k in rec_int]

    def run_post(self, recurrence: Sequence[int] = (1000, 500, 200, 100, 50, 25, 20, 10, 5, 2)) -> None:
        with self.locked():
            ash_post_path = Path(self.ash_post_dir)
            remove_incompatible_outputs(ash_post_path, version=ASHPOST_VERSION)
            res = watershed_daily_aggregated(self.wd, recurrence=recurrence)
            if res != None:
                self._return_periods, self._cum_return_periods, self._burn_class_return_periods = res
                write_version_manifest(ash_post_path, version=ASHPOST_VERSION)
                generate_ashpost_documentation(self.ash_post_dir)
            else:
                self._return_periods, self._cum_return_periods, self._burn_class_return_periods = None, None, None

        update_catalog_entry(self.wd, 'ash')
        
    @property
    def meta(self) -> Mapping[str, Any]:
        from wepppy.nodb.mods.ash_transport import Ash
        ash = Ash.getInstance(self.wd)
        return ash.meta

    @property
    def fire_date(self) -> YearlessDate:
        from wepppy.nodb.mods.ash_transport import Ash
        ash = Ash.getInstance(self.wd)
        return ash.fire_date

    @property
    def ash_post_dir(self) -> str:
        return _join(self.ash_dir, 'post')


    @property
    def hillslope_annuals(self) -> Dict[str, Dict[str, Any]]:
        path = _join(self.ash_post_dir, ASH_POST_FILES['hillslope_annuals'])
        if not _exists(path):
            return {}
        df = pd.read_parquet(path)
        d = {}
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            topaz_id = row_dict['topaz_id']
            d[str(int(topaz_id))] = row_dict
        return d

    @property
    def watershed_annuals(self) -> Dict[str, Dict[str, Any]]:
        path = _join(self.ash_post_dir, ASH_POST_FILES['watershed_annuals'])
        if not _exists(path):
            return {}
        df = pd.read_parquet(path)
        d = {}
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            key = None
            for candidate in ('year', 'topaz_id'):
                if candidate in row_dict and not pd.isna(row_dict[candidate]):
                    key = row_dict[candidate]
                    break
            if key is None:
                key = index
            d[str(int(key))] = row_dict
        return d

    @property
    def ash_out(self) -> Dict[str, Dict[str, Any]]:
        ash_out = self.meta
        hillslope_annuals = self.hillslope_annuals

        for topaz_id in ash_out:
            if ash_out[topaz_id]['ash_type'] is None or topaz_id not in hillslope_annuals:
                ash_out[topaz_id]['water_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['wind_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['ash_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['ash_ini_depth (mm)'] = 0.0
            else:
                ash_out[topaz_id]['water_transport (tonne/ha)'] = hillslope_annuals[topaz_id]['water_transport (tonne/ha)']
                ash_out[topaz_id]['wind_transport (tonne/ha)'] = hillslope_annuals[topaz_id]['wind_transport (tonne/ha)']
                ash_out[topaz_id]['ash_transport (tonne/ha)'] = hillslope_annuals[topaz_id]['ash_transport (tonne/ha)']
                ash_out[topaz_id]['ash_ini_depth (mm)'] = ash_out[topaz_id]['ini_ash_depth']
                ash_out[topaz_id]['area (ha)'] = ash_out[topaz_id]['area_ha']

            if 'ini_ash_depth' in ash_out[topaz_id]:
                del ash_out[topaz_id]['ini_ash_depth']

            del ash_out[topaz_id]['area_ha']

        return ash_out
