# Copyright (c) 2016-2020, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import shutil

from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from typing import Union

from copy import deepcopy

from datetime import date

import jsonpickle

from .....all_your_base import RasterDatasetInterpolator, isfloat, RDIOutOfBoundsException
from ....base import NoDbBase, TriggerEvents

from ..location_mixin import LocationMixin

from .....climates.cligen import StationMeta, Cligen, ClimateFile
from ....climate import Climate, ClimateMode, ClimateSpatialMode, ClimateStationMode
from ....soils import Soils
from ....watershed import Watershed
from ....wepp import Wepp
from .....wepp.soils.utils import modify_ksat

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class TurkeyModNoDbLockedException(Exception):
    pass


DEFAULT_WEPP_TYPE = 'Volcanic'
PMET__MID_SEASON_CROP_COEFF__DEFAULT = 0.95
CRITICAL_SHEAR_DEFAULT = 140.0


_soils_map = {
    '1': ('3611', 'soils/Cevirme_Forest.sol'),
    '2': ('23115', 'soils/Cevirme_Mera.sol'),
    '3': ('15203', 'soils/Cevirme_Bozuk_Mese.sol'),
    '4': ('109', 'soils/Cevirme_Bozuk_Mese.sol'),
    '5': ('169', 'soils/Cevirme_Bozuk_Mese.sol'),
    '6': ('1759', 'soils/Cevirme_Bozuk_Mese.sol'),
    '-9999': ('-9999', 'soils/Cevirme_Mera.sol'),

}

class TurkeyMod(NoDbBase, LocationMixin):
    __name__ = 'PortlandMod'

    def __init__(self, wd, config):
        super(TurkeyMod, self).__init__(wd, config)

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
        with open(_join(wd, 'turkey.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, TurkeyMod), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'turkey.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'turkey.nodb.lock')

    def on(self, evt):
        pass
        """
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
    """
        
    @property
    def data_dir(self):
        global _data_dir

        if not hasattr(self, '_data_dir'):
            return _data_dir

        return self._data_dir

    def build_landuse(self):
        from wepppy.nodb import Landuse
        from wepppy.landcover import LandcoverMap

        landuse = Landuse.getInstance(self.wd)

        lc_fn = landuse.lc_fn
        assert _exists(landuse.lc_fn)

        # create LandcoverMap instance
        lc = LandcoverMap(lc_fn)

        try:
            landuse.lock()
            # build the grid
            # domlc_fn map is a property of NoDbBase
            # domlc_d is a dictionary with topaz_id keys
            landuse.domlc_d = lc.build_lcgrid(self.subwta_arc, None)
            landuse.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        landuse = Landuse.getInstance(self.wd)
        landuse.build_managements()

    def build_soils(self):
        from wepppy.nodb import Soils
        from wepppy.landcover import LandcoverMap
        from wepppy.soils.ssurgo import SoilSummary

        soils = Soils.getInstance(self.wd)
        soils_dir = soils.soils_dir

        lc_fn = soils.lc_fn
        assert _exists(soils.lc_fn)

        # create LandcoverMap instance
        lc = LandcoverMap(lc_fn)

        try:
            soils.lock()
            # build the grid
            # domlc_fn map is a property of NoDbBase
            # domlc_d is a dictionary with topaz_id keys
            soils.domsoil_d = lc.build_lcgrid(self.subwta_arc, None)
            soils.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        soils = Soils.getInstance(self.wd)

        soils_d = {}
        for topaz_id, k in soils.domsoil_d.items():
            mukey, soil_fn = _soils_map[k]

            shutil.copyfile(_join(_data_dir, soil_fn),
                            _join(soils_dir, _split(soil_fn)[-1]))
            soils_d[str(k)] = SoilSummary(
                Mukey=str(k),
                FileName=_split(soil_fn)[-1],
                soils_dir=soils_dir,
                BuildDate="N/A",
                Description=soil_fn,
                pct_coverage=-1
            )

        try:
            soils.lock()
            soils.soils = soils_d
            soils.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def build_climate(self, user_par='bingol2020.par', years=100, cliver='4.3'):
        wd = self.wd
        climate = Climate.getInstance(wd)
        climate.climatestation_mode = ClimateStationMode.UserDefined
        climate.climatestation = 'bingol2020'
        climate.climate_spatialmode = ClimateSpatialMode.Single
        climate.climate_mode = ClimateMode.Vanilla
        climate.input_years = years

        stationmeta = StationMeta(state='Bingol, Turkey', desc='', par=_join(_data_dir, user_par),
                                  latitude=38.88, longitude=40.49, years=45, _type=2,
                                  elevation=3795.0, tp5=1.14, tp6=5.20, _distance=None)

        cligen = Cligen(stationmeta, wd=climate.cli_dir, cliver=cliver)
        cli_fn = cligen.run_multiple_year(years)

        cli = ClimateFile(_join(climate.cli_dir, cli_fn))
        monthlies = cli.calc_monthlies()

        from pprint import pprint
        pprint(monthlies)

        climate.lock()

        # noinspection PyBroadInspection
        try:
            climate.monthlies = monthlies
            climate.par_fn = user_par
            climate.cli_fn = cli_fn
            climate.dump_and_unlock()
            climate.log_done()

        except Exception:
            climate.unlock('-f')
            raise