"""Rangeland Analysis Platform (RAP) time-series controller.

The RAP time-series mod orchestrates multi-year downloads of the RAP fractional
cover rasters, summarizes the per-band values to TOPAZ hillslopes (and optional
multi-OFE footprints), and persists the results for downstream analytics.

Inputs:
- Watershed rasters (`subwta`, optional `mofe_map`) supplied by the `Watershed`
  controller and cached in the working directory.
- RAP fractional cover rasters fetched through
  `RangelandAnalysisPlatformV3.retrieve` for the configured year range.
- Optional revegetation metadata (burn classes, cover transforms) when the
  `Revegetation` mod is active.

Outputs and integrations:
- `rap_ts.parquet` capturing the summarized fractional cover values for each
  RAP band, year, TOPAZ hillslope, and optional OFE. Dashboards and notebooks
  read this parquet for time-series analytics.
- `.cov` files written to WEPP run directories via `prep_cover`, enabling WEPP
  and RHEM runs to incorporate time-varying cover.
- Redis task timestamps updated through `RedisPrep` so UI controllers can
  reflect job completion.
"""

from __future__ import annotations

# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, ClassVar, Dict, Iterator, Optional, Tuple, TypeAlias

import pandas as pd
import pyarrow
from osgeo import gdal

import wepppyo3
from wepppyo3.raster_characteristics import identify_median_intersecting_raster_keys
from wepppyo3.raster_characteristics import identify_median_single_raster_key

from wepppy.landcover.rap import RAP_Band, RangelandAnalysisPlatformV3
from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.query_engine.activate import update_catalog_entry

from .rap import RAPPointData

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


__all__ = [
    'RAPNoDbLockedException',
    'RAP_TS',
]

YearKey: TypeAlias = int | str
TopazId: TypeAlias = int | str
MofeId: TypeAlias = int | str
SingleOFEValues: TypeAlias = Dict[TopazId, float]
MultiOFEValues: TypeAlias = Dict[TopazId, Dict[MofeId, float]]
BandYearSummary: TypeAlias = Dict[YearKey, SingleOFEValues | MultiOFEValues]
RAPTimeSeriesData: TypeAlias = Dict[RAP_Band, BandYearSummary]


class RAPNoDbLockedException(Exception):
    pass


class RAP_TS(NoDbBase):
    __name__: ClassVar[str] = 'RAP_TS'

    filename: ClassVar[str] = 'rap_ts.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        self.data: Optional[RAPTimeSeriesData] = None
        self._rap_start_year: Optional[int] = None
        self._rap_end_year: Optional[int] = None
        self._rap_mgr: Optional[RangelandAnalysisPlatformV3] = None

        with self.locked():
            os.makedirs(self.rap_dir, exist_ok=True)
            self.data = None
            self._rap_start_year = None
            self._rap_end_year = None
            self._rap_mgr = None

    def __getstate__(self) -> Dict[str, Any]:
        """
        Customize object serialization. If data is stored in Parquet,
        remove it from the state dictionary to prevent it from being
        written to the .nodb file.
        """
        super().__getstate__()
        state = self.__dict__.copy()
        parquet_path = _join(self.rap_dir, 'rap_ts.parquet')
        if _exists(parquet_path):
            if 'data' in state:
                del state['data']
        return state

    @classmethod
    def _post_instance_loaded(cls, instance: 'RAP_TS') -> 'RAP_TS':
        instance = super()._post_instance_loaded(instance)

        # New method: Hydrate from parquet for performance
        parquet_path = _join(instance.rap_dir, 'rap_ts.parquet')
        if _exists(parquet_path):
            if pd is None or pyarrow is None:
                raise ImportError("pandas and pyarrow are required to read RAP data from parquet.")

            df = pd.read_parquet(parquet_path)

            # Reconstruct the nested dictionary from the flat DataFrame
            reconstructed_data: RAPTimeSeriesData = {}
            is_multi_ofe = 'mofe_id' in df.columns and (df['mofe_id'] != -1).any()

            for row in df.itertuples():
                band = RAP_Band(row.band)
                year = str(row.year)
                topaz_id = str(row.topaz_id)
                value = row.value

                if band not in reconstructed_data:
                    reconstructed_data[band] = {}

                if year not in reconstructed_data[band]:
                    reconstructed_data[band][year] = {}

                if is_multi_ofe:
                    mofe_id = str(row.mofe_id)
                    if topaz_id not in reconstructed_data[band][year]:
                        reconstructed_data[band][year][topaz_id] = {}
                    reconstructed_data[band][year][topaz_id][mofe_id] = value
                else:
                    reconstructed_data[band][year][topaz_id] = value

            instance.data = reconstructed_data
            return instance

        # Backwards compatibility: data is in the nodb file
        data = getattr(instance, 'data', None)
        if data is not None:
            mapped: RAPTimeSeriesData = {}
            for key in RAP_Band:
                key_repr = repr(key)
                if key_repr in data:
                    mapped[key] = data[key_repr]
            instance.data = mapped

        return instance

    @property
    def rap_end_year(self) -> Optional[int]:
        return self._rap_end_year

    @rap_end_year.setter
    @nodb_setter
    def rap_end_year(self, value: int) -> None:
        self._rap_end_year = value

    @property
    def rap_start_year(self) -> Optional[int]:
        return self._rap_start_year

    @rap_start_year.setter
    @nodb_setter
    def rap_start_year(self, value: int) -> None:
        self._rap_start_year = value

    @property
    def rap_dir(self) -> str:
        return _join(self.wd, 'rap')

    def acquire_rasters(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> None:

        def retrieve_rap_year(year: int) -> int:
            self.logger.info(f'  retrieving rap {year}...')
            retries = rap_mgr.retrieve([year])
            if retries > 0:
                self.logger.info(f'  retries: {retries}\n')
            return year

        def oncomplete(future: Future[int]) -> None:
            year = future.result()
            self.logger.info(f'  retrieving rap {year} completed.\n')

        with self.locked():
            if start_year is not None:
                self._rap_start_year = start_year
            else:
                start_year = self.rap_start_year

            if end_year is not None:
                self._rap_end_year = end_year
            else:
                end_year = self.rap_end_year

            _map = Ron.getInstance(self.wd).map
            rap_mgr = RangelandAnalysisPlatformV3(wd=self.rap_dir, bbox=_map.extent, cellsize=_map.cellsize)

            futures: list[Future[int]] = []
            with ThreadPoolExecutor() as pool:
                for year in range(start_year, end_year + 1):
                    future = pool.submit(retrieve_rap_year, year)
                    future.add_done_callback(oncomplete)
                    futures.append(future)

                futures_n = len(futures)
                count = 0
                pending: set[Future[int]] = set(futures)
                while pending:
                    done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

                    if not done:
                        self.logger.warning('  RAP raster retrieval still running after 60 seconds; continuing to wait.')
                        continue

                    for future in done:
                        try:
                            future.result()
                            count += 1
                            self.logger.info(f'  ({count}/{futures_n}) rasters retrieved)')
                        except Exception as exc:
                            for remaining in pending:
                                remaining.cancel()
                            self.logger.error(f'  RAP raster retrieval failed with an error: {exc}')
                            raise

            self._rap_mgr = rap_mgr
            update_catalog_entry(self.wd, self.rap_dir)

    def on(self, evt: TriggerEvents) -> None:
        pass

        #if evt == TriggerEvents.WATERSHED_ABSTRACTION_COMPLETE:
        #    self.acquire_rasters()

    def get_cover(
        self,
        topaz_id: TopazId,
        year: YearKey,
        fallback: bool = True
    ) -> float:
        if self.data is None:
            return 0.0

        cover = 0.0
        for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                     RAP_Band.PERENNIAL_FORB_AND_GRASS,
                     RAP_Band.SHRUB,
                     RAP_Band.TREE]:
            band_years = self.data.get(band, {})
            year_key = str(year)
            values = band_years.get(year_key, {})
            cover_value = None
            if isinstance(values, dict):
                cover_value = values.get(str(topaz_id))
                if cover_value is None and fallback:
                    cover_value = values.get(str(topaz_id), 0.0)

            cover += float(cover_value if cover_value is not None else 0.0)
        return cover

    def analyze(self, use_sbs: bool = False, verbose: bool = False) -> None:
        start_year = self.rap_start_year
        end_year = self.rap_end_year
        if start_year is None or end_year is None:
            raise ValueError('RAP start and end years must be set before analysis.')

        watershed = Watershed.getInstance(self.wd)
        rap_mgr = self._rap_mgr
        if rap_mgr is None:
            raise RuntimeError('RAP rasters must be acquired before analysis.')

        with self.locked():
            data_ds: RAPTimeSeriesData = {}

            def analyze_band_year(year: int, band: RAP_Band) -> Tuple[int, RAP_Band]:
                if verbose:
                    print(year, band)

                if band not in data_ds:
                    data_ds[band] = {}

                self.logger.info(f'  analyzing rap {year} {band}...')

                rap_ds_fn = rap_mgr.get_dataset_fn(year=year)
                if self.multi_ofe:
                    result = identify_median_intersecting_raster_keys(
                        key_fn=watershed.subwta, key2_fn=watershed.mofe_map, parameter_fn=rap_ds_fn, band_indx=band.value)
                else:
                    result = identify_median_single_raster_key(
                        key_fn=watershed.subwta, parameter_fn=rap_ds_fn, band_indx=band.value)

                data_ds[band][year] = result
                return year, band

            def oncomplete(future: Future[Tuple[int, RAP_Band]]) -> None:
                year, band = future.result()
                self.logger.info(f'  analyzing rap {year} {band} completed.\n')

            futures: list[Future[Tuple[int, RAP_Band]]] = []
            with ThreadPoolExecutor() as pool:
                for year in range(start_year, end_year + 1):
                    for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                                 RAP_Band.BARE_GROUND,
                                 RAP_Band.LITTER,
                                 RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                 RAP_Band.SHRUB,
                                 RAP_Band.TREE]:
                        future = pool.submit(analyze_band_year, year, band)
                        future.add_done_callback(oncomplete)
                        futures.append(future)

                futures_n = len(futures)
                count = 0
                pending: set[Future[Tuple[int, RAP_Band]]] = set(futures)
                while pending:
                    done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

                    if not done:
                        self.logger.warning('  RAP analysis still running after 60 seconds; continuing to wait.')
                        continue

                    for future in done:
                        try:
                            future.result()
                            count += 1
                            self.logger.info(f'  ({count}/{futures_n}) analyses complete)')
                        except Exception as exc:
                            for remaining in pending:
                                remaining.cancel()
                            self.logger.error(f'  RAP analysis failed with an error: {exc}')
                            raise

            # For new projects, save data to parquet for performance.
            if pd is not None and pyarrow is not None and data_ds:
                records: list[dict[str, int | float]] = []
                # Check the structure of the first data point to determine if multi-ofe
                first_band = next(iter(data_ds.keys()))
                first_year = next(iter(data_ds[first_band].keys()))
                first_topaz_data = data_ds[first_band][first_year]
                first_value = next(iter(first_topaz_data.values()))
                is_multi_ofe = isinstance(first_value, dict)

                for band, year_data in data_ds.items():
                    for year, topaz_data in year_data.items():
                        if is_multi_ofe:
                            for topaz_id, mofe_data in topaz_data.items():
                                for mofe_id, value in mofe_data.items():
                                    records.append({
                                        'band': band.value,
                                        'year': int(year),
                                        'topaz_id': int(topaz_id),
                                        'mofe_id': int(mofe_id),
                                        'value': value
                                    })
                        else:
                            for topaz_id, value in topaz_data.items():
                                records.append({
                                    'band': band.value,
                                    'year': int(year),
                                    'topaz_id': int(topaz_id),
                                    'mofe_id': -1,  # Sentinel for non-mofe
                                    'value': value
                                })
                
                if records:
                    df = pd.DataFrame(records)
                    parquet_path = _join(self.rap_dir, 'rap_ts.parquet')
                    df.to_parquet(parquet_path)
                    update_catalog_entry(self.wd, 'rap/rap_ts.parquet')

            self.data = data_ds

        self.logger.info('analysis complete...')

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.fetch_rap_ts)
        except FileNotFoundError:
            pass

    def __iter__(self) -> Iterator[Tuple[str, RAPPointData]]:
        if self.data is None or self.multi_ofe:
            return iter(())

        tree_band = self.data.get(RAP_Band.TREE, {})
        if not tree_band:
            return iter(())

        year_keys = list(tree_band.keys())
        str_years = {str(key) for key in year_keys}

        target_year = None
        if self.rap_end_year is not None:
            candidate = str(self.rap_end_year)
            if candidate in str_years:
                target_year = candidate

        if target_year is None:
            def sort_key(value: YearKey) -> Tuple[int, str]:
                text = str(value)
                return (int(text) if text.isdigit() else -1, text)

            sorted_years = sorted(year_keys, key=sort_key)
            if not sorted_years:
                return iter(())
            target_year = str(sorted_years[-1])

        def resolve_single_ofe(mapping: BandYearSummary, key: str) -> Optional[SingleOFEValues]:
            value = mapping.get(key)
            if value is None and key.isdigit():
                value = mapping.get(int(key))
            if isinstance(value, dict):
                first_value = next(iter(value.values()), None)
                if isinstance(first_value, dict):
                    return None
                cleaned: SingleOFEValues = {}
                for k, v in value.items():
                    if v is None:
                        continue
                    cleaned[str(k)] = float(v)
                return cleaned
            return None

        reference_values = resolve_single_ofe(tree_band, target_year)
        if reference_values is None:
            return iter(())

        def iterator() -> Iterator[Tuple[str, RAPPointData]]:
            for topaz_key in reference_values:
                payload: Dict[str, Optional[float]] = {}
                for band in [RAP_Band.ANNUAL_FORB_AND_GRASS,
                             RAP_Band.BARE_GROUND,
                             RAP_Band.LITTER,
                             RAP_Band.PERENNIAL_FORB_AND_GRASS,
                             RAP_Band.SHRUB,
                             RAP_Band.TREE]:
                    band_years = self.data.get(band, {})
                    band_values = resolve_single_ofe(band_years, target_year)
                    payload[band.name.lower()] = band_values.get(topaz_key) if band_values else None
                yield str(topaz_key), RAPPointData(**payload)

        return iterator()

    def prep_cover(self, runs_dir: str, fallback: bool = True) -> None:
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.revegetation import Revegetation

        wd = self.wd

        disturbed = Disturbed.getInstance(wd)
        fire_date = None
        if disturbed is not None:
            fire_date = disturbed.fire_date

        reveg = Revegetation.tryGetInstance(wd)
        cover_transform = None
        if reveg is not None:
            cover_transform = reveg.cover_transform

        if fire_date is not None and  cover_transform is not None:
            return self._prep_transformed_cover(runs_dir)

        self.logger.info('RAP_TS::prep_cover\n')
        data = self.data

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        with open(_join(runs_dir, 'cancov.txt'), 'w') as fp:
            fp.write("")

        years = sorted([yr for yr in data[RAP_Band.TREE]])

        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = str(translator.top(wepp=wepp_id))

            with open(_join(runs_dir, f'p{wepp_id}.cov'), 'w') as fp:
                fp.write(' \t'.join([str(yr) for yr in years]))
                fp.write('\n')

                if self.multi_ofe:
                    for fp_id in sorted(data[RAP_Band.TREE][years[0]][str(topaz_id)]):
                        self.logger.info(f'  topaz_id={topaz_id}, fp_id={fp_id}\n')

                        for band in [RAP_Band.TREE,
                                     RAP_Band.SHRUB,
                                     RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                     RAP_Band.ANNUAL_FORB_AND_GRASS,
                                     RAP_Band.LITTER,
                                     RAP_Band.BARE_GROUND,
                                     ]:
                            fp.write(' \t'.join([str(data[band][yr][topaz_id][fp_id]) for yr in years]))
                            fp.write('\n')

                else:
                    self.logger.info(f'  topaz_id={topaz_id}\n')

                    for band in [RAP_Band.TREE,
                                 RAP_Band.SHRUB,
                                 RAP_Band.PERENNIAL_FORB_AND_GRASS,
                                 RAP_Band.ANNUAL_FORB_AND_GRASS,
                                 RAP_Band.LITTER,
                                 RAP_Band.BARE_GROUND,
                                 ]:
                        _covers = []
                        for yr in years:
                            _cover = data[band][yr].get(topaz_id, None)
                            if _cover is None and yr-1 in data[band] and fallback:
                                _cover = data[band][yr-1].get(topaz_id, 0.0)
                            if _cover is None:
                                _cover = 0.0
                            _covers.append(_cover)
                        fp.write(' \t'.join([str(_cover) for _cover in _covers]))
                        fp.write('\n')

    def _prep_transformed_cover(self, runs_dir: str) -> None:
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.revegetation import Revegetation
        from wepppy.nodb.core import Landuse

        self.logger.info('RAP_TS::_prep_transformed_cover\n')

        wd = self.wd

        disturbed = Disturbed.getInstance(wd)
        reveg = Revegetation.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        fire_date = disturbed.fire_date
        cover_transform = reveg.cover_transform
        managements = landuse.managements

        data = self.data

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        with open(_join(runs_dir, 'simfire.txt'), 'w') as fp:
            fp.write("")

        with open(_join(runs_dir, 'cancov.txt'), 'w') as fp:
            fp.write("")

        years = sorted([yr for yr in data[RAP_Band.TREE]])
        fire_mo, fire_da, fire_year = fire_date.replace('-', ' ').replace('/', ' ').split()
        fire_year = int(fire_year)
        fire_years = {str(yr): int(yr) - fire_year for yr in years}

        for wepp_id in translator.iter_wepp_sub_ids():
            topaz_id = str(translator.top(wepp=wepp_id))

            with open(_join(runs_dir, f'p{wepp_id}.cov'), 'w') as fp:
                fp.write(' \t'.join([str(yr) for yr in years]))
                fp.write('\n')

                if self.multi_ofe:
                    for mofe_id in sorted(data[RAP_Band.TREE][years[0]][str(topaz_id)]):

                        burn_class = landuse.identify_burn_class(topaz_id, mofe_id)

                        for band, name in [(RAP_Band.TREE, 'Tree'),
                                   (RAP_Band.SHRUB, 'Shrub'),
                                   (RAP_Band.PERENNIAL_FORB_AND_GRASS, 'Perennial'),
                                   (RAP_Band.ANNUAL_FORB_AND_GRASS, 'Annual'),
                                   (RAP_Band.LITTER, 'Litter'),
                                   (RAP_Band.BARE_GROUND, 'Bare')
                                   ]:
                            key = (burn_class, name)

                            self.logger.info(f'  topaz_id={topaz_id}, mofe_id={mofe_id}, burn_class={burn_class}, rap_band={name}\n')
                            
                            if key in cover_transform:
                                x = []
                                for yr in years:
                                    indx = fire_years.get(str(yr), None)

                                    if indx is not None and indx < 0:
                                        x.append(data[band][yr][topaz_id][mofe_id])
                                        continue

                                    if indx is None:
                                        scale = cover_transform[key][-1]
                                    else:
                                        scale = cover_transform[key][indx]
                                    x.append(data[band][str(fire_year)][topaz_id][mofe_id] * scale)
                                fp.write(' \t'.join([f'{v:0.1f}' for v in x]))
                            else:
                                fp.write(' \t'.join([str(data[band][yr][topaz_id][mofe_id]) for yr in years]))
                            fp.write('\n')

                else:
                    burn_class = landuse.identify_burn_class(topaz_id)

                    for band, name in [(RAP_Band.TREE, 'Tree'),
                               (RAP_Band.SHRUB, 'Shrub'),
                               (RAP_Band.PERENNIAL_FORB_AND_GRASS, 'Perennial'),
                               (RAP_Band.ANNUAL_FORB_AND_GRASS, 'Annual'),
                               (RAP_Band.LITTER, 'Litter'),
                               (RAP_Band.BARE_GROUND, 'Bare')
                               ]:
                        key = (burn_class, name)
                        
                        self.logger.info(f'  topaz_id={topaz_id}, burn_class={burn_class}, rap_band={name}\n')

                        if key in cover_transform:
                            x = []
                            for yr in years:
                                indx = fire_years.get(str(yr), None)

                                if indx is not None and indx < 0:
                                    x.append(data[band][yr][topaz_id])
                                    continue

                                if indx is None:
                                    scale = cover_transform[key][-1]
                                else:
                                    scale = cover_transform[key][indx]
                                x.append(data[band][str(fire_year)][topaz_id] * scale)
                            fp.write(' \t'.join([f'{v:0.1f}' for v in x]))
                        else:
                            fp.write(' \t'.join([str(data[band][yr][topaz_id]) for yr in years]))
                        fp.write('\n')
