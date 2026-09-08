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
from os.path import exists as _exists

from typing import Any, Dict, Mapping, Optional, Sequence

# non-standard

from wepppy.all_your_base.dateutils import YearlessDate
import pandas as pd
import pyarrow.parquet as pq


from wepppy.nodb.base import NoDbBase


from wepppy.query_engine.activate import update_catalog_entry

from .ashpost_documentation import generate_ashpost_documentation
from .ashpost_versioning import (
    ASHPOST_VERSION,
    remove_incompatible_outputs,
    write_version_manifest,
)

from wepppy.wepp.interchange._rust_interchange import require_wepppyo3_interchange

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


def watershed_daily_aggregated(
    wd: str,
    recurrence: Sequence[int] = (1000, 500, 200, 100, 50, 25, 20, 10, 5, 2),
    verbose: bool = True,
) -> Optional[tuple[ReturnPeriods, ReturnPeriods, BurnClassReturnPeriods]]:
    """Discover ordered hillslope inputs and delegate aggregation to native code."""
    from wepppy.nodb.core import Watershed
    from wepppy.nodb.mods.ash_transport import Ash

    watershed = Watershed.getInstance(wd)
    ash = Ash.getInstance(wd)
    translator = watershed.translator_factory()
    root = Path(wd)
    manifest = []
    for topaz_id in watershed._subs_summary:
        wepp_id = translator.wepp(top=topaz_id)
        burn_class = ash.meta[topaz_id]['burn_class']
        area_ha = watershed.hillslope_area(topaz_id) / 10000
        path = Path(ash.ash_dir) / f'H{wepp_id}_ash.parquet'
        if path.exists():
            manifest.append((os.path.relpath(path, root), int(topaz_id), area_ha, burn_class))
    if not manifest:
        return None

    # Schema metadata is small; source rows remain entirely on the native side.
    names = set(pq.read_schema(root / manifest[0][0]).names) | set(common_cols)
    names |= {name.replace('tonne/ha', 'tonne').replace('(mm)', '(m^3)') for name in names}
    metadata = {}
    for name in names:
        field = {}
        if units := _infer_units(name):
            field['units'] = units
        if description := _describe_column(name):
            field['description'] = description
        metadata[name] = field

    def optional_path(name):
        path = root / 'wepp' / 'output' / 'interchange' / name
        return os.path.relpath(path, root) if path.exists() else None

    ash_wepp_ids = []
    for topaz_id in watershed._subs_summary:
        meta = ash.meta.get(str(topaz_id), ash.meta.get(topaz_id, {}))
        if meta.get('ash_type') is not None:
            ash_wepp_ids.append(int(translator.wepp(top=topaz_id)))
    native = require_wepppyo3_interchange('AshPost', 'ashpost_to_parquet')
    result = native.ashpost_to_parquet(
        str(root), str(Path(ash.ash_dir) / 'post'), manifest, list(recurrence),
        hydrology_path=optional_path('totalwatsed3.parquet'),
        wat_path=optional_path('H.wat.parquet'), ash_wepp_ids=ash_wepp_ids,
        field_metadata=metadata,
    )
    if warning := result.get('streamflow_exceedance'):
        ash.logger.warning(
            "AshPost: corrected streamflow exceeds original on %d day(s); max overage %.4f mm. Samples:\n%s",
            warning['count'], warning['max_overage_mm'],
            pd.DataFrame(warning['samples'], columns=[
                'year', 'julian', 'Streamflow_orig (mm)', 'Streamflow_ash_corr (mm)'
            ]).to_string(index=False),
        )
    if verbose:
        ash.logger.info('Native AshPost completed: input_rows=%s rows_written=%s',
                        result['input_rows'], result['rows_written'])
    return (result['return_periods'], result['cum_return_periods'],
            result['burn_class_return_periods'])


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
