# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Watershed mixins extracted from the Watershed NoDb facade.

These classes hold operational and lookup-heavy methods to keep
``wepppy/nodb/core/watershed.py`` below code-quality red-zone size thresholds
without changing the public Watershed facade contract.
"""

from typing import Generator, Dict, Union, Tuple, Optional, List, Any, Callable

import time
import os
import inspect
import math
import sys

from os.path import join as _join
from os.path import exists as _exists

import numpy as np

from osgeo import gdal, osr
from osgeo.gdalconst import *

from deprecated import deprecated

from wepppy.topo.watershed_abstraction import WeppTopTranslator
from wepppy.topo.peridot.peridot_runner import (
    run_peridot_abstract_watershed,
    run_peridot_wbt_abstract_watershed,
    read_network,
)
from wepppy.topo.peridot.flowpath import (
    PeridotHillslope,
    PeridotChannel,
)

from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.topo.watershed_abstraction.support import (
    ChannelSummary,
    HillSummary,
    identify_edge_hillslopes,
    json_to_wgs,
    polygonize_netful,
)
from wepppy.topo.watershed_abstraction.slope_file import mofe_distance_fractions
from wepppy.topo.wbt import WhiteboxToolsTopazEmulator
from wepppy.all_your_base.geo import read_raster
from wepppy.all_your_base.geo.vrt import build_windowed_vrt_from_window
from wepppy.nodb.duckdb_agents import get_watershed_chns_summary

from wepppy.nodir.parquet_sidecars import (
    pick_existing_parquet_path as _default_pick_existing_parquet_path,
)
from wepppy.nodb.base import nodb_setter
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.nodb.duckdb_agents import (
    get_watershed_subs_summary,
    get_watershed_sub_summary,
    get_watershed_chn_summary,
)

from .topaz import Topaz

# Debris-flow routines need the portion of the basin with slopes steeper than 30%.
# ``hillslopes.parquet`` stores slope as a rise/run ratio, so 30% equals 0.30.
_SLOPE_RATIO_THRESHOLD = 0.30


def _pick_existing_parquet_path(wd: str, relpath: str) -> Optional[str]:
    """Read parquet-path resolver through watershed module for monkeypatch parity."""
    watershed_module = sys.modules.get("wepppy.nodb.core.watershed")
    picker = getattr(watershed_module, "pick_existing_parquet_path", None)
    if callable(picker):
        return picker(wd, relpath)
    return _default_pick_existing_parquet_path(wd, relpath)


class WatershedOperationsMixin:
    def translator_factory(self) -> WeppTopTranslator:
        # Try to get IDs from in-memory summaries first
        if self._subs_summary is not None and self._chns_summary is not None:
            return WeppTopTranslator(
                map(int, self._subs_summary.keys()), map(int, self._chns_summary.keys())
            )
        
        # Fall back to loading IDs from parquet files
        hillslopes_parquet = _pick_existing_parquet_path(
            self.wd, "watershed/hillslopes.parquet"
        )
        channels_parquet = _pick_existing_parquet_path(
            self.wd, "watershed/channels.parquet"
        )
        
        if hillslopes_parquet is not None and channels_parquet is not None:
            import duckdb
            with duckdb.connect() as con:
                sub_ids = con.execute(
                    f"SELECT topaz_id FROM read_parquet('{hillslopes_parquet}')"
                ).fetchall()
                chn_ids = con.execute(
                    f"SELECT topaz_id FROM read_parquet('{channels_parquet}')"
                ).fetchall()
            return WeppTopTranslator(
                (row[0] for row in sub_ids), (row[0] for row in chn_ids)
            )
        
        raise RuntimeError(
            "No sub_ids/chn_ids available for translator (no summaries or parquet files)"
        )

    #
    # build channels
    #
    def build_channels(self, csa: Optional[float] = None, mcl: Optional[float] = None) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}(csa={csa}, mcl={mcl})')

        assert not self.islocked()

        self.logger.info("Building Channels")

        reset_channels_vrt = self.flovec_netful_relief_chnjnt_are_vrt
        if csa is not None or mcl is not None or reset_channels_vrt:
            with self.locked():
                if csa is not None:
                    self._csa = csa

                if mcl is not None:
                    self._mcl = mcl

                if reset_channels_vrt:
                    self._flovec_netful_relief_chnjnt_are_vrt = False

        # Preserve outlet information during channel building
        preserved_outlet = self.outlet
        if preserved_outlet is not None:
            self.remove_outlet()

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            Topaz.getInstance(self.wd).build_channels(csa=self.csa, mcl=self.mcl)
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            ron = self.ron_instance
            wbt = WhiteboxToolsTopazEmulator(
                self.wbt_wd,
                ron.dem_fn,
                logger=self.logger,
            )
            wbt.flovec_netful_relief_are_vrt = False
            wbt.delineate_channels(
                csa=self.csa,
                mcl=self.mcl,
                fill_or_breach=self.wbt_fill_or_breach,
                blc_dist=self.wbt_blc_dist,
                logger=self.logger,
            )
            self._wbt = wbt

      
        if _exists(self.subwta):
            self.logger.info(f' Removing subcatchment: {self.subwta}')
            os.remove(self.subwta)

        prep = RedisPrep.getInstance(self.wd)
        prep.timestamp(TaskEnum.build_channels)

    def symlink_channels_map(
        self,
        flovec_src: str,
        netful_src: str,
        relief_src: Optional[str] = None,
        chnjnt_src: Optional[str] = None,
        *,
        as_cropped_vrt: bool = True,
        crop_window: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(
            f"{self.class_name}.{func_name}(flovec_src={flovec_src}, netful_src={netful_src}, "
            f"relief_src={relief_src}, chnjnt_src={chnjnt_src})"
        )

        if not self.delineation_backend_is_wbt:
            raise RuntimeError("symlink_channels_map requires WBT delineation backend")

        flovec_src = os.path.abspath(flovec_src)
        netful_src = os.path.abspath(netful_src)
        if relief_src is not None:
            relief_src = os.path.abspath(relief_src)
        if chnjnt_src is not None:
            chnjnt_src = os.path.abspath(chnjnt_src)

        if not _exists(flovec_src):
            raise FileNotFoundError(f"Flow vector file does not exist: {flovec_src}")
        if not _exists(netful_src):
            raise FileNotFoundError(f"Stream network file does not exist: {netful_src}")
        if relief_src is not None and not _exists(relief_src):
            raise FileNotFoundError(f"Relief file does not exist: {relief_src}")
        if chnjnt_src is not None and not _exists(chnjnt_src):
            raise FileNotFoundError(f"Channel junction file does not exist: {chnjnt_src}")

        os.makedirs(self.wbt_wd, exist_ok=True)

        ron = self.ron_instance
        if as_cropped_vrt:
            if crop_window is None:
                crop_window = ron.crop_window
            if crop_window is None:
                raise ValueError("Crop window cannot be identified for as_cropped_vrt=True")

        def _ensure_symlink(src: str, dest: str) -> None:
            if os.path.lexists(dest):
                if os.path.islink(dest):
                    existing = os.path.realpath(dest)
                    if existing != src:
                        os.unlink(dest)
                else:
                    if os.path.samefile(dest, src):
                        return
                    raise FileExistsError(
                        f"Destination exists and is not a symlink: {dest}"
                    )
            if not os.path.lexists(dest):
                os.symlink(src, dest)

        def _ensure_vrt(src: str, dest: str) -> None:
            if crop_window is None:
                raise ValueError("crop_window is required to build windowed VRTs")
            build_windowed_vrt_from_window(
                src,
                dest,
                crop_window,
                reference_geotransform=ron.crop_reference_geotransform,
                reference_shape=ron.crop_reference_shape,
            )

        if as_cropped_vrt:
            # Use .vrt extension so WhiteboxTools recognizes the format
            _ensure_vrt(flovec_src, _join(self.wbt_wd, "flovec.vrt"))
            _ensure_vrt(netful_src, _join(self.wbt_wd, "netful.vrt"))
            if relief_src is not None:
                _ensure_vrt(relief_src, _join(self.wbt_wd, "relief.vrt"))
            if chnjnt_src is not None:
                _ensure_vrt(chnjnt_src, _join(self.wbt_wd, "chnjnt.vrt"))
        else:
            _ensure_symlink(flovec_src, _join(self.wbt_wd, "flovec.tif"))
            _ensure_symlink(netful_src, _join(self.wbt_wd, "netful.tif"))
            if relief_src is not None:
                _ensure_symlink(relief_src, _join(self.wbt_wd, "relief.tif"))
            if chnjnt_src is not None:
                _ensure_symlink(chnjnt_src, _join(self.wbt_wd, "chnjnt.tif"))

        channels_are_vrt = bool(as_cropped_vrt)
        self._flovec_netful_relief_chnjnt_are_vrt = channels_are_vrt
        wbt = getattr(self, "_wbt", None)
        if wbt is not None:
            wbt.flovec_netful_relief_are_vrt = channels_are_vrt

        netful_geojson = self.netful_utm_shp
        netful_wgs_geojson = self.netful_shp
        for path in (netful_geojson, netful_wgs_geojson):
            if path and _exists(path):
                os.remove(path)

        polygonize_netful(self.netful, netful_geojson)
        json_to_wgs(netful_geojson)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_channels)
        except FileNotFoundError:
            pass

        if not self.islocked():
            with self.locked():
                self._flovec_netful_relief_chnjnt_are_vrt = channels_are_vrt

    @property
    def target_watershed_path(self) -> str:
        return _join(self.wd, 'dem', "target_watershed.tif")

    def set_outlet(self, lng: Optional[float] = None, lat: Optional[float] = None, da: float = 0.0) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}(lng={lng}, lat={lat}, da={da})')
        
        assert not self.islocked()
        self.logger.info("Setting Outlet")

        if lng is None or lat is None:
            raise ValueError("lng and lat must be provided")
        
        assert float(lng), lng
        assert float(lat), lat

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            topaz = Topaz.getInstance(self.wd)
            topaz.set_outlet(lng=lng, lat=lat, da=da)
            _outlet = topaz.outlet
            if _outlet is None:
                raise ValueError("Failed to set outlet in Topaz")
            self.outlet = _outlet
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = self._ensure_wbt()
            _outlet = wbt.set_outlet(lng=lng, lat=lat, logger=self.logger)
            if _outlet is None:
                raise ValueError("Failed to set outlet in WBT")

            with self.locked():
                self._outlet = _outlet
                self._wbt = wbt
        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.set_outlet)
        except FileNotFoundError:
            pass

    def remove_outlet(self) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')

        self.outlet = None

    #
    # build subcatchments
    #
    def build_subcatchments(self, pkcsa: Optional[str] = None) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}(pkcsa={pkcsa})')

        assert not self.islocked()

        if _exists(self.subwta):
            self.logger.info(f' Removing subcatchment: {self.subwta}')
            os.remove(self.subwta)

        if self.delineation_backend_is_topaz:
            self.logger.info(f' delineation_backend_is_topaz')
            Topaz.getInstance(self.wd).build_subcatchments()
        elif self.delineation_backend_is_wbt:
            self.logger.info(f' delineation_backend_is_wbt')
            wbt = self._ensure_wbt()
            wbt.delineate_subcatchments(self.logger)
            self.identify_edge_hillslopes()
        else:
            self.logger.info(f' delineation_backend_is_taudem')
            with self.locked():
                if pkcsa is not None:
                    self._pkcsa = pkcsa
            self._taudem_build_subcatchments()

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_subcatchments)
        except FileNotFoundError:
            pass

    def identify_edge_hillslopes(self) -> None:
        """
        Identify edge hillslopes in the watershed.
        This is used to determine which hillslopes are at the edge of the watershed.
        """
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')

        if self.readonly:
            self._edge_hillslopes = identify_edge_hillslopes(self.subwta, self.logger)
            return
            
        with self.locked():
            self._edge_hillslopes = identify_edge_hillslopes(self.subwta, self.logger)


    @property
    def edge_hillslopes(self) -> List[int]:
        """
        Get the edge hillslopes in the watershed.
        """
        if not hasattr(self, "_edge_hillslopes"):
            self.identify_edge_hillslopes()
        return self._edge_hillslopes

    @property
    def pkcsa(self) -> Optional[str]:
        return getattr(self, "_pkcsa", None)

    @property
    def network(self) -> Any:
        if self.abstraction_backend_is_peridot:
            network = read_network(_join(self.wat_dir, "network.txt"))
            return network
        else:
            raise NotImplementedError("network not implemented")

    #
    # abstract watershed
    #

    def abstract_watershed(self) -> None:
        assert not self.islocked()
        self.logger.info("Abstracting Watershed")

        if self.abstraction_backend_is_peridot:
            if self.delineation_backend_is_topaz:
                run_peridot_abstract_watershed(
                    self.wd,
                    clip_hillslopes=False,
                    clip_hillslope_length=self.clip_hillslope_length,
                    bieger2015_widths=self.bieger2015_widths,
                )
            elif self.delineation_backend_is_wbt:
                run_peridot_wbt_abstract_watershed(
                    self.wd,
                    clip_hillslopes=self.clip_hillslopes,
                    clip_hillslope_length=self.clip_hillslope_length,
                    bieger2015_widths=self.bieger2015_widths,
                    skip_flowpaths=self.skip_flowpaths,
                    representative_flowpath=self.representative_flowpath,
                )

            self._peridot_post_abstract_watershed()

        else:
            if self.delineation_backend_is_topaz:
                self._topaz_abstract_watershed()
            else:
                self._taudem_abstract_watershed()

        if self.multi_ofe:
            self._build_multiple_ofe()

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.abstract_watershed)
        except FileNotFoundError:
            pass

    @property
    def mofe_nsegments(self) -> Optional[Dict[str, int]]:
        return getattr(self, "_mofe_nsegments", None)

    @property
    def mofe_target_length(self) -> float:
        return getattr(self, "_mofe_target_length", 50)

    @mofe_target_length.setter
    @nodb_setter
    def mofe_target_length(self, value: float) -> None:
        self._mofe_target_length = value

    @property
    def mofe_buffer(self) -> bool:
        return getattr(self, "_mofe_buffer", False)

    @mofe_buffer.setter
    @nodb_setter
    def mofe_buffer(self, value: bool) -> None:
        self._mofe_buffer = bool(value)

    @property
    def mofe_max_ofes(self) -> int:
        return getattr(self, "_mofe_max_ofes", 19)

    @mofe_max_ofes.setter
    @nodb_setter
    def mofe_max_ofes(self, value: int) -> None:
        self._mofe_max_ofes = value

    @property
    def mofe_buffer_length(self) -> float:
        return getattr(self, "_mofe_buffer_length", 15)

    @mofe_buffer_length.setter
    @nodb_setter
    def mofe_buffer_length(self, value: float) -> None:
        self._mofe_buffer_length = value

    def _build_multiple_ofe(self) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')
        _mofe_nsegments: Dict[str, int] = {}
        for topaz_id, wat_ss in self.subs_summary.items():
            not_top = not str(topaz_id).endswith("1")

            if isinstance(wat_ss, HillSummary):
                slp_fn = _join(self.wat_dir, wat_ss.fname)
            elif isinstance(wat_ss, PeridotHillslope):
                slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)
            else:
                # Handle dict case
                slp_fn = _join(self.wat_dir, wat_ss.get('slp_rel_path', wat_ss.get('fname', '')))

            slp = SlopeFile(slp_fn)
            _mofe_nsegments[topaz_id] = slp.segmented_multiple_ofe(
                target_length=self.mofe_target_length,
                apply_buffer=self.mofe_buffer and not_top,
                buffer_length=self.mofe_buffer_length,
                max_ofes=self.mofe_max_ofes,
            )

        with self.locked():
            self._mofe_nsegments = _mofe_nsegments

        self._build_mofe_map()

    @property
    def mofe_map(self) -> str:
        return _join(self.wat_dir, "mofe.tif")

    def _build_mofe_map(self) -> None:
        func_name = inspect.currentframe().f_code.co_name  # type: ignore
        self.logger.info(f'{self.class_name}.{func_name}()')
        subwta, transform_s, proj_s = read_raster(self.subwta, dtype=np.int32)
        discha_path = self.discha
        if discha_path is None:
            raise ValueError("discha path is None")
        discha, transform_d, proj_d = read_raster(discha_path, dtype=np.int32)
        mofe_nsegments = self.mofe_nsegments

        mofe_map = np.zeros(subwta.shape, np.int32)
        for topaz_id, wat_ss in self.subs_summary.items():
            indices = np.where(subwta == int(topaz_id))
            _discha_vals = discha[indices]
            max_discha = np.max(_discha_vals)

            if isinstance(wat_ss, HillSummary):
                slp_fn = _join(self.wat_dir, wat_ss.fname)
            elif isinstance(wat_ss, PeridotHillslope):
                slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)
            else:
                # Handle dict case
                slp_fn = _join(self.wat_dir, wat_ss.get('slp_rel_path', wat_ss.get('fname', '')))

            mofe_slp_fn = _join(self.wat_dir, slp_fn.replace(".slp", ".mofe.slp"))
            d_fractions = mofe_distance_fractions(mofe_slp_fn)

            n_ofe = len(d_fractions) - 1
            if n_ofe == 1:
                mofe_indices = np.where(subwta == int(topaz_id))
                mofe_map[mofe_indices] = 1
            else:
                j = 1
                for i in range(n_ofe):
                    _max_pct = (1.0 - d_fractions[i]) * 100
                    _min_pct = (1.0 - d_fractions[i + 1]) * 100
                    _min = np.percentile(_discha_vals, _min_pct)
                    _max = np.percentile(_discha_vals, _max_pct)

                    mofe_indices = np.where(
                        (subwta == int(topaz_id))
                        & (mofe_map == 0)
                        & (discha >= _min)
                        & (discha <= _max)
                    )
                    if len(mofe_indices[0]) == 0:
                        target_value = (1.0 - d_fractions[i]) * max_discha
                        diff = np.abs(target_value - _discha_vals)
                        closest_index = np.argmin(diff)
                        mofe_indices = (
                            indices[0][closest_index],
                            indices[1][closest_index],
                        )

                    mofe_map[mofe_indices] = j
                    j += 1

            mofe_ids = set(mofe_map[indices])
            if 0 in mofe_ids:
                mofe_ids.remove(0)

            assert len(mofe_ids) == n_ofe, (topaz_id, mofe_ids)

        num_cols, num_rows = mofe_map.shape

        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(self.mofe_map, num_cols, num_rows, 1, GDT_Byte)  # type: ignore[name-defined]

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj_s)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform_s)
        band = dst.GetRasterBand(1)
        band.WriteArray(mofe_map.T)
        del dst  # Writes and closes file

        assert _exists(self.mofe_map)


class WatershedLookupMixin:
    @property
    def report(self) -> Dict[str, Union[int, float]]:
        return dict(hillslope_n=self.sub_n, channel_n=self.chn_n, totalarea=self.wsarea)

    @property
    def centroid(self) -> Optional[Tuple[float, float]]:
        return self._centroid

    def sub_summary(self, topaz_id: Union[str, int]) -> Union[PeridotHillslope, Dict[str, Any], None]:
        if _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet") is not None:
            return PeridotHillslope.from_dict(
                get_watershed_sub_summary(self.wd, topaz_id)
            )

        if _exists(_join(self.wat_dir, "hillslopes.csv")):
            import duckdb

            csv_fn = _join(self.wat_dir, "hillslopes.csv")
            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT * FROM read_csv('{csv_fn}') WHERE topaz_id = ?", [topaz_id]
                ).fetchall()

                columns = [desc[0] for desc in con.description]
                result = [dict(zip(columns, row)) for row in result]
                return result[0]

        return self._deprecated_sub_summary(topaz_id)

    @deprecated
    def _deprecated_sub_summary(self, topaz_id: Union[str, int]) -> Union[Dict[str, Any], None]:
        if self._subs_summary is None:
            return None

        if str(topaz_id) in self._subs_summary:
            d = self._subs_summary[str(topaz_id)]
            if isinstance(d, dict):
                return d
            else:
                return d.as_dict()
        else:
            return None

    @property
    def fps_summary(self) -> Optional[Dict[str, List[str]]]:
        flowpaths_parquet = _pick_existing_parquet_path(
            self.wd, "watershed/flowpaths.parquet"
        )
        if flowpaths_parquet is not None:
            import duckdb

            fps_summary: Dict[str, List[str]] = {}
            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT topaz_id, fp_id FROM read_parquet('{flowpaths_parquet}')"
                ).fetchall()

                for row in result:
                    topaz_id = str(row[0])
                    fp_id = str(row[1])
                    if topaz_id not in fps_summary:
                        fps_summary[topaz_id] = []
                    fps_summary[topaz_id].append(fp_id)
            return fps_summary
        return None

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id: int) -> Union[HillSummary, ChannelSummary]:
        translator = self.translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))

        if self._subs_summary is not None and topaz_id in self._subs_summary:
            return self._subs_summary[topaz_id]
        elif self._chns_summary is not None and topaz_id in self._chns_summary:
            return self._chns_summary[topaz_id]

        raise IndexError

    @property
    def subs_summary(self) -> Dict[str, Union[PeridotHillslope, Dict[str, Any]]]:
        if _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet") is not None:

            summaries = get_watershed_subs_summary(self.wd)
            return {
                str(topaz_id): PeridotHillslope.from_dict(d)
                for topaz_id, d in summaries.items()
            }

        if self._subs_summary is None:
            return {}
        return {str(k): v.as_dict() for k, v in self._subs_summary.items()}

    def chn_summary(self, topaz_id: Union[str, int]) -> Union[PeridotChannel, Dict[str, Any], None]:
        if _pick_existing_parquet_path(self.wd, "watershed/channels.parquet") is not None:
            return PeridotChannel.from_dict(
                get_watershed_chn_summary(self.wd, topaz_id)
            )

        if _exists(_join(self.wat_dir, "channels.csv")):
            import duckdb

            csv_fn = _join(self.wat_dir, "channels.csv")
            with duckdb.connect() as con:
                result = con.execute(
                    f"SELECT * FROM read_csv('{csv_fn}') WHERE topaz_id = ?", [topaz_id]
                ).fetchall()

                columns = [desc[0] for desc in con.description]
                result = [dict(zip(columns, row)) for row in result]
                return result[0]

        return self._deprecated_chn_summary(topaz_id)

    @deprecated
    def _deprecated_chn_summary(self, topaz_id: Union[str, int]) -> Union[Dict[str, Any], None]:
        if self._chns_summary is None:
            return None
        if str(topaz_id) in self._chns_summary:
            d = self._chns_summary[str(topaz_id)]
            if isinstance(d, dict):
                return d
            else:
                return d.as_dict()
        else:
            return None

    @property
    def chns_summary(self) -> Dict[str, Union[PeridotChannel, Dict[str, Any]]]:
        if _pick_existing_parquet_path(self.wd, "watershed/channels.parquet") is not None:

            summaries = get_watershed_chns_summary(self.wd)
            return {
                topaz_id: PeridotChannel.from_dict(d)
                for topaz_id, d in summaries.items()
            }

        if self._chns_summary is None:
            return {}
        return {k: v.as_dict() for k, v in self._chns_summary.items()}

    def _load_lookup_from_duckdb(
        self,
        cache_attr: str,
        source_path: str,
        *,
        source_kind: str,
        value_columns: Tuple[str, ...],
        value_builder: Callable[[Tuple[Any, ...]], Any],
    ) -> Dict[str, Any]:
        import duckdb

        reader = {"parquet": "read_parquet", "csv": "read_csv"}.get(source_kind)
        if reader is None:
            raise ValueError(f"Unsupported source kind: {source_kind}")

        select_columns = ", ".join(("topaz_id", *value_columns))
        query = f"SELECT {select_columns} FROM {reader}('{source_path}')"

        with duckdb.connect() as con:
            rows = con.execute(query).fetchall()

        lookup = {str(row[0]): value_builder(row) for row in rows}
        setattr(self, cache_attr, lookup)
        return lookup

    def hillslope_area(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_sub_area_lookup"):
            return self._sub_area_lookup[str(topaz_id)]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is not None:
            sub_area_lookup = self._load_lookup_from_duckdb("_sub_area_lookup", parquet_fn, source_kind="parquet", value_columns=("area",), value_builder=lambda row: row[1])
            return sub_area_lookup[str(topaz_id)]

        return self._deprecated_area_of(topaz_id)

    def hillslope_slope(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_sub_slope_lookup"):
            return self._sub_slope_lookup[str(topaz_id)]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is not None:
            sub_slope_lookup = self._load_lookup_from_duckdb("_sub_slope_lookup", parquet_fn, source_kind="parquet", value_columns=("slope_scalar",), value_builder=lambda row: row[1])
            return sub_slope_lookup[str(topaz_id)]

        raise Exception('Cannot find slope without hillslope.parquet file')

    def channel_area(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_chn_area_lookup"):
            return self._chn_area_lookup[str(topaz_id)]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/channels.parquet")
        if parquet_fn is not None:
            chn_area_lookup = self._load_lookup_from_duckdb("_chn_area_lookup", parquet_fn, source_kind="parquet", value_columns=("area",), value_builder=lambda row: row[1])
            return chn_area_lookup[str(topaz_id)]

        return self._deprecated_area_of(topaz_id)

    @deprecated
    def _deprecated_area_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if self._chns_summary is None or self._subs_summary is None:
            raise ValueError("Summary data is None")
        if topaz_id_str.endswith("4"):
            return self._chns_summary[topaz_id_str].area
        else:
            return self._subs_summary[topaz_id_str].area

    def hillslope_length(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_sub_length_lookup"):
            return self._sub_length_lookup[str(topaz_id)]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is not None:
            sub_length_lookup = self._load_lookup_from_duckdb("_sub_length_lookup", parquet_fn, source_kind="parquet", value_columns=("length",), value_builder=lambda row: row[1])
            return sub_length_lookup[str(topaz_id)]

        return self._deprecated_length_of(topaz_id)

    def _compute_area_gt30_from_hillslopes(self) -> float:
        """Determine basin area with slopes ≥30% using hillslopes parquet data."""
        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is None:
            raise FileNotFoundError(
                "hillslopes parquet not found (expected watershed/hillslopes.parquet)"
            )

        import duckdb

        query = (
            f"SELECT COALESCE(SUM(area), 0.0) "
            f"FROM read_parquet('{parquet_fn}') "
            f"WHERE slope_scalar >= {_SLOPE_RATIO_THRESHOLD}"
        )

        try:
            with duckdb.connect() as con:
                result = con.execute(query).fetchone()
        except duckdb.duckdb.IOException:
            time.sleep(4)
            with duckdb.connect() as con:
                result = con.execute(query).fetchone()

        area = result[0] if result else 0.0
        return float(area or 0.0)

    def _compute_ruggedness_from_dem(self) -> float:
        """Approximate ruggedness using DEM statistics when TOPAZ values are absent."""
        ron = self.ron_instance
        dem_path = ron.dem_fn
        if not _exists(dem_path):
            raise FileNotFoundError(f"DEM not found at {dem_path}; cannot compute ruggedness")

        dataset = gdal.Open(dem_path, gdal.GA_ReadOnly)
        if dataset is None:
            raise RuntimeError(f"Unable to open DEM at {dem_path}")

        try:
            band = dataset.GetRasterBand(1)
            if band is None:
                raise RuntimeError("DEM is missing band 1; cannot compute ruggedness")

            stats = band.GetStatistics(False, True)
            if not stats or stats[0] is None or stats[1] is None:
                raise RuntimeError("Failed to compute DEM statistics for ruggedness")

            min_z, max_z = float(stats[0]), float(stats[1])

            geotransform = dataset.GetGeoTransform()
            if geotransform is None:
                raise RuntimeError("DEM lacks geotransform; cannot derive pixel area")

            pixel_width = float(geotransform[1])
            pixel_height = float(geotransform[5])
            if pixel_width == 0.0 or pixel_height == 0.0:
                raise RuntimeError("DEM pixel size is zero; cannot compute area")

            pixel_area = abs(pixel_width * pixel_height)
            raster_area = pixel_area * dataset.RasterXSize * dataset.RasterYSize
            if raster_area <= 0.0:
                raise RuntimeError("Computed DEM area is non-positive; cannot compute ruggedness")

            return float((max_z - min_z) / math.sqrt(raster_area))
        finally:
            dataset = None

    def channel_length(self, topaz_id: Union[str, int]) -> float:
        if hasattr(self, "_chn_length_lookup"):
            return self._chn_length_lookup[str(topaz_id)]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/channels.parquet")
        if parquet_fn is not None:
            chn_length_lookup = self._load_lookup_from_duckdb("_chn_length_lookup", parquet_fn, source_kind="parquet", value_columns=("length",), value_builder=lambda row: row[1])
            return chn_length_lookup[str(topaz_id)]

        return self._deprecated_length_of(topaz_id)

    def hillslope_width(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if hasattr(self, "_sub_width_lookup") and topaz_id_str in self._sub_width_lookup:  # type: ignore[attr-defined]
            return self._sub_width_lookup[topaz_id_str]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is not None:
            sub_width_lookup = self._load_lookup_from_duckdb("_sub_width_lookup", parquet_fn, source_kind="parquet", value_columns=("width",), value_builder=lambda row: float(row[1]))
            if topaz_id_str in sub_width_lookup:
                return sub_width_lookup[topaz_id_str]
            return self._deprecated_width_of(topaz_id_str)

        csv_fn = _join(self.wat_dir, "hillslopes.csv")
        if _exists(csv_fn):
            sub_width_lookup = self._load_lookup_from_duckdb("_sub_width_lookup", csv_fn, source_kind="csv", value_columns=("width",), value_builder=lambda row: float(row[1]))
            if topaz_id_str in sub_width_lookup:
                return sub_width_lookup[topaz_id_str]
            return self._deprecated_width_of(topaz_id_str)

        return self._deprecated_width_of(topaz_id_str)

    def channel_width(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if hasattr(self, "_chn_width_lookup") and topaz_id_str in self._chn_width_lookup:  # type: ignore[attr-defined]
            return self._chn_width_lookup[topaz_id_str]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/channels.parquet")
        if parquet_fn is not None:
            chn_width_lookup = self._load_lookup_from_duckdb("_chn_width_lookup", parquet_fn, source_kind="parquet", value_columns=("width",), value_builder=lambda row: float(row[1]))
            if topaz_id_str in chn_width_lookup:
                return chn_width_lookup[topaz_id_str]
            return self._deprecated_width_of(topaz_id_str)

        csv_fn = _join(self.wat_dir, "channels.csv")
        if _exists(csv_fn):
            chn_width_lookup = self._load_lookup_from_duckdb("_chn_width_lookup", csv_fn, source_kind="csv", value_columns=("width",), value_builder=lambda row: float(row[1]))
            if topaz_id_str in chn_width_lookup:
                return chn_width_lookup[topaz_id_str]
            return self._deprecated_width_of(topaz_id_str)

        return self._deprecated_width_of(topaz_id_str)

    @deprecated
    def _deprecated_length_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if self._chns_summary is None or self._subs_summary is None:
            raise ValueError("Summary data is None")
        if topaz_id_str.endswith("4"):
            return self._chns_summary[topaz_id_str].length
        else:
            return self._subs_summary[topaz_id_str].length

    @deprecated
    def _deprecated_width_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if topaz_id_str.endswith("4"):
            if self._chns_summary is None:
                raise ValueError("Channel summary data is None")
            channel_summary = self._chns_summary[topaz_id_str]
            if isinstance(channel_summary, dict):
                return float(channel_summary["width"])
            return float(channel_summary.width)

        if self._subs_summary is None:
            raise ValueError("Hillslope summary data is None")
        hillslope_summary = self._subs_summary[topaz_id_str]
        if isinstance(hillslope_summary, dict):
            return float(hillslope_summary["width"])
        return float(hillslope_summary.width)

    def width_of(self, topaz_id: Union[str, int]) -> float:
        topaz_id_str = str(topaz_id)
        if topaz_id_str.endswith("4"):
            return self.channel_width(topaz_id)
        return self.hillslope_width(topaz_id)

    def hillslope_centroid_lnglat(self, topaz_id: Union[str, int]) -> Tuple[float, float]:
        if hasattr(self, "_sub_centroid_lookup"):
            return self._sub_centroid_lookup[str(topaz_id)]  # type: ignore[attr-defined]

        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is not None:
            sub_centroid_lookup = self._load_lookup_from_duckdb("_sub_centroid_lookup", parquet_fn, source_kind="parquet", value_columns=("centroid_lon", "centroid_lat"), value_builder=lambda row: (row[1], row[2]))
            return sub_centroid_lookup[str(topaz_id)]

        if self._subs_summary is None:
            raise ValueError("subs_summary is None")
        wat_ss = self._subs_summary[str(topaz_id)]
        lng, lat = wat_ss.centroid.lnglat
        return lng, lat

    def hillslope_slp_fn(self, topaz_id: Union[str, int]) -> str:
        wat_ss = self.subs_summary[str(topaz_id)]
        if isinstance(wat_ss, HillSummary):  # deprecated
            slp_fn = _join(self.wat_dir, wat_ss.fname)
        elif isinstance(wat_ss, PeridotHillslope):
            slp_fn = _join(self.wat_dir, wat_ss.slp_rel_path)
        else:
            # Handle dict case
            slp_fn = _join(self.wat_dir, wat_ss.get('slp_rel_path', wat_ss.get('fname', '')))

        return slp_fn

    def centroid_hillslope_iter(self) -> Generator[Tuple[Union[str, int], Tuple[float, float]], None, None]:
        parquet_fn = _pick_existing_parquet_path(self.wd, "watershed/hillslopes.parquet")
        if parquet_fn is not None:
            import duckdb

            with duckdb.connect() as con:
                # lazy load self._sub_area_lookup with duckdb
                result = con.execute(
                    f"SELECT topaz_id, centroid_lon, centroid_lat FROM read_parquet('{parquet_fn}')"
                ).fetchall()
                for topaz_id, lon, lat in result:
                    yield topaz_id, (lon, lat)

        else:
            yield from self._deprecated_centroid_hillslope_iter()

    @deprecated
    def _deprecated_centroid_hillslope_iter(self) -> Generator[Tuple[str, Tuple[float, float]], None, None]:
        if self._subs_summary is None:
            return
        i = 0
        for topaz_id, wat_ss in self._subs_summary.items():
            yield topaz_id, wat_ss.centroid.lnglat
            i += 1

        assert i == self.sub_n, (i, self.sub_n)
