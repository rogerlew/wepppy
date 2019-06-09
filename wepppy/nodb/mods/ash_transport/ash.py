import math
import csv
import os
import shutil
import enum

from os.path import join as _join
from os.path import exists as _exists

from copy import deepcopy

# non-standard
import jsonpickle
import numpy as np
import pandas as pd

# wepppy
from wepppy.landcover import LandcoverMap

from wepppy.all_your_base import isfloat, isint, YearlessDate

from wepppy.wepp import Element
from wepppy.climates.cligen import ClimateFile

# wepppy submodules
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.soils import Soils
from wepppy.nodb.topaz import Topaz
from wepppy.nodb.climate import Climate
from wepppy.nodb.mods import Baer
from wepppy.nodb.wepp import Wepp


from .wind_transport_thresholds import *
from .ash_model import *

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class AshNoDbLockedException(Exception):
    pass


class Ash(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Ash'

    def __init__(self, wd, cfg_fn):
        super(Ash, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            # config = self.config
            self.fire_date = None
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
        with open(_join(wd, 'ash.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Ash), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'ash.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'ash.nodb.lock')

    @property
    def ash_dir(self):
        return _join(self.wd, 'ash')

    def run_ash(self, fire_date='8/4', ini_white_ash_depth_mm=5.0, ini_black_ash_depth_mm=3.0):
        global black_ash_parameters, white_ash_parameters

        self.lock()

        # noinspection PyBroadException
        try:
            self.fire_date = fire_date = YearlessDate.from_string(fire_date)
            self.ini_white_ash_depth_mm = ini_white_ash_depth_mm
            self.ini_black_ash_depth_mm = ini_black_ash_depth_mm

            wd = self.wd
            ash_dir = self.ash_dir

            if _exists(ash_dir):
                shutil.rmtree(ash_dir)
            os.mkdir(ash_dir)

            soils = Soils.getInstance(wd)
            topaz = Topaz.getInstance(wd)
            baer = Baer.getInstance(wd)
            watershed = Watershed.getInstance(wd)
            climate = Climate.getInstance(wd)
            wepp = Wepp.getInstance(wd)

            cli_path = climate.cli_path
            cli_df = ClimateFile(cli_path).as_dataframe(calc_peak_intensities=True)

            # create LandcoverMap instance
            sbs = SoilBurnSeverityMap(baer.baer_cropped, baer.breaks, baer._nodata_vals)

            baer_4class = baer.baer_cropped.replace('.tif', '.4class.tif')
            sbs.export_4class_map(baer_4class)

            lc = LandcoverMap(baer_4class)
            sbs_d = lc.build_lcgrid(self.subwta_arc)

            translator = watershed.translator_factory()
            for topaz_id, sub in watershed.sub_iter():
                wepp_id = translator.wepp(top=topaz_id)

                print(topaz_id, wepp_id)
                burn_class = int(sbs_d[topaz_id])

                if burn_class in [2, 3]:
                    ash_model = WhiteAshModel()
                    ash_model.ini_ash_depth_mm = ini_black_ash_depth_mm

                elif burn_class in [4]:
                    ash_model = BlackAshModel()
                    ash_model.ini_ash_depth_mm = ini_black_ash_depth_mm

                else:
                    continue

                years = climate.input_years
                assert isint(years)
                assert years > 0

                element_fn = _join(wepp.output_dir, 'H{wepp_id}.element.dat'.format(wepp_id=wepp_id))
                element = Element(element_fn)

                ash_model.run_model(fire_date, element.d, cli_df, ash_dir, 'H{wepp_id}'.format(wepp_id=wepp_id))

                print(dict(width=sub.width,
                           length=sub.length,
                           area=sub.area,
                           gradient=sub.slope_scalar,
                           burn_class=burn_class,
                           ash_type=ash_model.ash_type,
                           years=years))

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise


if __name__ == "__main__":
    from pprint import pprint

    ash = Ash.getInstance('/geodata/weppcloud_runs/devvme13-d785-4734-a023-c55cb168aaa1')
    ash.run_ash()