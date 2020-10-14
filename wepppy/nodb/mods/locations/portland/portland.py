# Copyright (c) 2016-2020, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os

from os.path import join as _join
from os.path import exists as _exists
from typing import Union

from copy import deepcopy

from datetime import date

import jsonpickle

from .....all_your_base import RasterDatasetInterpolator, isfloat, RDIOutOfBoundsException
from ....base import NoDbBase, TriggerEvents

from ..location_mixin import LocationMixin

from ....climate import Climate, ClimateMode, ClimateSpatialMode
from ....soils import Soils
from ....watershed import Watershed
from ....wepp import Wepp
from .....wepp.soils.utils import modify_ksat


from .livneh_daily_observed import LivnehDataManager
from .bedrock import ShallowLandSlideSusceptibility, BullRunBedrock

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir)


class PortlandModNoDbLockedException(Exception):
    pass


DEFAULT_WEPP_TYPE = 'Volcanic'
PMET__MID_SEASON_CROP_COEFF__DEFAULT = 0.95
CRITICAL_SHEAR_DEFAULT = 140.0


def _daymet_cli_adjust(cli_dir, cli_fn, pp_scale, adjust_date=date(2005, 11, 2)):
    from .....climates.cligen import ClimateFile
    cli = ClimateFile(_join(cli_dir, cli_fn))

    if adjust_date is not None:
        cli.discontinuous_temperature_adjustment(adjust_date)

    cli.transform_precip(offset=0, scale=pp_scale)
    cli.write(_join(cli_dir, 'adj_' + cli_fn))

    return 'adj_' + cli_fn


def _gridmet_cli_adjust(cli_dir, cli_fn, pp_scale):
    from .....climates.cligen import ClimateFile
    cli = ClimateFile(_join(cli_dir, cli_fn))
    cli.transform_precip(offset=0, scale=pp_scale)
    cli.write(_join(cli_dir, 'adj_' + cli_fn))

    return 'adj_' + cli_fn


class PortlandMod(NoDbBase, LocationMixin):
    __name__ = 'PortlandMod'

    def __init__(self, wd, cfg_fn):
        super(PortlandMod, self).__init__(wd, cfg_fn)

        self._lc_lookup_fn = 'landSoilLookup.csv'
        self._default_wepp_type = DEFAULT_WEPP_TYPE
        self._data_dir = _data_dir

        self.lock()

        # noinspection PyBroadException
        try:

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'portland.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, PortlandMod), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'portland.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'portland.nodb.lock')

    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
        if evt == TriggerEvents.LANDUSE_BUILD_COMPLETE:
            pass
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
            self.modify_soils_ksat()
        # elif evt == TriggerEvents.PREPPING_PHOSPHORUS:
        #     self.determine_phosphorus()
        elif evt == TriggerEvents.CLIMATE_BUILD_COMPLETE:
            climate = Climate.getInstance(self.wd)

            if climate.climate_mode in [ClimateMode.Observed, ClimateMode.ObservedPRISM]:
                self.modify_climates(_daymet_cli_adjust, 'daymet_scale.tif')

            elif climate.climate_mode in [ClimateMode.GridMetPRISM, ClimateMode.Future]:
                self.modify_climates(_gridmet_cli_adjust, 'gridmet_scale.tif')

        elif evt == TriggerEvents.WEPP_PREP_WATERSHED_COMPLETE:
            self.modify_erod_cs()
            self.modify_pmet()

    @property
    def lc_lookup_fn(self):
        if not hasattr(self, '_lc_lookup_fn'):
            return 'landSoilLookup.csv'

        return self._lc_lookup_fn

    @lc_lookup_fn.setter
    def lc_lookup_fn(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._lc_lookup_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def default_wepp_type(self):
        if not hasattr(self, '_default_wepp_type'):
            return DEFAULT_WEPP_TYPE

        return self._default_wepp_type

    @default_wepp_type.setter
    def default_wepp_type(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._default_wepp_type = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def data_dir(self):
        global _data_dir

        if not hasattr(self, '_data_dir'):
            return _data_dir

        return self._data_dir

    def modify_climates(self, adjust_func, pp_scale_raster):
        climate = Climate.getInstance(self.wd)
        climate.lock()
        watershed = Watershed.getInstance(self.wd)
        lng, lat = watershed.centroid
        rdi = RasterDatasetInterpolator(_join(_data_dir, pp_scale_raster))
        pp_scale = rdi.get_location_info(lng, lat)
        if not isfloat(pp_scale):
            return

        cli_dir = climate.cli_dir
        adj_cli_fn = adjust_func(cli_dir, climate.cli_fn, pp_scale)
        climate.cli_fn = adj_cli_fn

        if climate.climate_spatialmode == ClimateSpatialMode.Multiple:
            for topaz_id in climate.sub_cli_fns:
                adj_cli_fn = adjust_func(cli_dir, climate.sub_cli_fns[topaz_id], pp_scale)
                climate.sub_cli_fns[topaz_id] = adj_cli_fn

        climate.dump_and_unlock()

    def modify_soils_ksat(self):
        wd = self.wd
        watershed = Watershed.getInstance(wd)

        soils = Soils.getInstance(wd)

        ksat_mod = None

        _landslide = ShallowLandSlideSusceptibility()
        _bedrock = BullRunBedrock()

        if 'landslide' in wd:
            ksat_mod = 'l'
        elif 'groundwater' in wd:
            ksat_mod = 'g'
        else:
            ksat_mod = 'h'

        _domsoil_d = soils.domsoil_d
        _soils = soils.soils
        for topaz_id, ss in watershed._subs_summary.items():
            lng, lat = ss.centroid.lnglat

            if ksat_mod == 'l':
                _landslide_pt = _landslide.get_bedrock(lng, lat)
                ksat = _landslide_pt['ksat']
                name = _landslide_pt['Unit_Name'].replace(' ', '_')

            elif ksat_mod == 'g':
                _bedrock_pt = _bedrock.get_bedrock(lng, lat)
                ksat = _bedrock_pt['ksat']
                name = _bedrock_pt['Unit_Name'].replace(' ', '_')
            else:
                _landslide_pt = _landslide.get_bedrock(lng, lat)
                _landslide_pt_ksat = _landslide_pt['ksat']

                _bedrock_pt = _bedrock.get_bedrock(lng, lat)
                _bedrock_pt_ksat = _bedrock_pt['ksat']
                ksat = _landslide_pt_ksat
                name = _landslide_pt['Unit_Name'].replace(' ', '_')

                if isfloat(_bedrock_pt_ksat):
                    ksat = _bedrock_pt_ksat
                    name = _bedrock_pt['Unit_Name'].replace(' ', '_')

            dom = _domsoil_d[str(topaz_id)]
            _soil = deepcopy(_soils[dom])

            _dom = '{dom}-{ksat_mod}_{bedrock_name}' \
                .format(dom=dom, ksat_mod=ksat_mod, bedrock_name=name)

            _soil.mukey = _dom

            if _dom not in _soils:
                _soil_fn = '{dom}.sol'.format(dom=_dom)
                src_soil_fn = _join(_soil.soils_dir, _soil.fname)
                dst_soil_fn = _join(_soil.soils_dir, _soil_fn)
                modify_ksat(src_soil_fn, dst_soil_fn, ksat)

                _soil.fname = _soil_fn
                _soils[_dom] = _soil

            _domsoil_d[str(topaz_id)] = _dom

        soils.lock()
        soils.domsoil_d = _domsoil_d
        soils.soils = _soils
        soils.dump_and_unlock()

    def modify_erod_cs(self):
        wd = self.wd
        wepp = Wepp.getInstance(wd)

        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()

        lng, lat = watershed.centroid
        rdi = RasterDatasetInterpolator(_join(_data_dir, 'critical_shear.tif'))

        try:
            critical_shear = rdi.get_location_info(lng, lat)
        except RDIOutOfBoundsException:
            critical_shear = CRITICAL_SHEAR_DEFAULT

        if not isfloat(critical_shear):
            critical_shear = CRITICAL_SHEAR_DEFAULT
        else:
            if critical_shear < 0.0 or critical_shear >= 255.0:
                critical_shear = CRITICAL_SHEAR_DEFAULT

        wepp._prep_channel_chn(translator, 0.000001, critical_shear)
        wepp._prep_impoundment()
        wepp._prep_channel_soils(translator, 0.000001, critical_shear)

    def modify_pmet(self):
        wd = self.wd
        wepp = Wepp.getInstance(wd)

        watershed = Watershed.getInstance(wd)

        lng, lat = watershed.centroid

        rdi = RasterDatasetInterpolator(_join(_data_dir, 'pmet__mid_season_crop_coeff.tif'))
        try:
            mid_season_crop_coeff = rdi.get_location_info(lng, lat)
        except RDIOutOfBoundsException:
            mid_season_crop_coeff = PMET__MID_SEASON_CROP_COEFF__DEFAULT

        if not isfloat(mid_season_crop_coeff):
            mid_season_crop_coeff = PMET__MID_SEASON_CROP_COEFF__DEFAULT
        else:
            if mid_season_crop_coeff < 0.0:
                mid_season_crop_coeff = PMET__MID_SEASON_CROP_COEFF__DEFAULT

        p_coeff = 0.75
        wepp._prep_pmet(mid_season_crop_coeff=mid_season_crop_coeff, p_coeff=p_coeff)
