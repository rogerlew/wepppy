import math
import csv
import os
import shutil
import json
import enum
from glob import glob

from os.path import join as _join
from os.path import exists as _exists

from copy import deepcopy
from collections import Counter

# non-standard
import jsonpickle
import numpy as np
import pandas as pd
import multiprocessing

# wepppy
from wepppy.landcover import LandcoverMap

from wepppy.all_your_base import isfloat, isint, YearlessDate, probability_of_occurrence

from wepppy.wepp import Element
from wepppy.climates.cligen import ClimateFile

# wepppy submodules
from wepppy.nodb.log_mixin import LogMixin
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

NCPU = math.floor(multiprocessing.cpu_count() * 0.6)
if NCPU < 1:
    NCPU = 1

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


def run_ash_model(kwds):
    """
    global function for running ash model to add with multiprocessing

    :param kwds: args package by Ash.run_model
    :return:
    """
    ash_type = kwds['ash_type']

    if ash_type == AshType.BLACK:
        ini_ash_depth = kwds['ini_black_ash_depth_mm']
        ash_model = WhiteAshModel(ini_ash_depth)
    else:
        ini_ash_depth = kwds['ini_white_ash_depth_mm']
        ash_model = BlackAshModel(ini_ash_depth)

    del kwds['ash_type']
    del kwds['ini_black_ash_depth_mm']
    del kwds['ini_white_ash_depth_mm']
    out_fn, return_periods, annuals = \
        ash_model.run_model(**kwds)

    return out_fn


class AshNoDbLockedException(Exception):
    pass


class Ash(NoDbBase, LogMixin):
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
            self.ini_black_ash_depth_mm = None
            self.ini_white_ash_depth_mm = None
            self.meta = None
            self.fire_years = None
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
    def status_log(self):
        return os.path.abspath(_join(self.ash_dir, 'status.log'))

    @property
    def ash_dir(self):
        return _join(self.wd, 'ash')

    def run_ash(self, fire_date='8/4', ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0):

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

            meta = {}
            args = []
            for topaz_id, sub in watershed.sub_iter():
                area_ha = sub.area / 10000

                meta[topaz_id] = {}

                wepp_id = translator.wepp(top=topaz_id)

                burn_class = int(sbs_d[topaz_id])
                meta[topaz_id]['burn_class'] = burn_class
                meta[topaz_id]['area_ha'] = area_ha

                if burn_class in [2, 3]:
                    ash_type = AshType.WHITE

                elif burn_class in [4]:
                    ash_type = AshType.BLACK
                else:
                    continue

                meta[topaz_id]['ash_type'] = ash_type

                element_fn = _join(wepp.output_dir,
                                   'H{wepp_id}.element.dat'.format(wepp_id=wepp_id))
                element = Element(element_fn)

                kwds = dict(ash_type=ash_type,
                            ini_white_ash_depth_mm=ini_white_ash_depth_mm,
                            ini_black_ash_depth_mm=ini_black_ash_depth_mm,
                            fire_date=fire_date,
                            element_d=element.d,
                            cli_df=cli_df,
                            out_dir=ash_dir,
                            prefix='H{wepp_id}'.format(wepp_id=wepp_id),
                            area_ha=area_ha)
                args.append(kwds)

            pool = multiprocessing.Pool(NCPU)
            for out_fn in pool.imap_unordered(run_ash_model, args):
                self.log('  done running {}\n'.format(out_fn))

            self.meta = meta
            try:
                self.fire_years = climate.input_years - 1
            except:
                pass

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def burnclass_summary(self):
        assert self.meta is not None

        burnclass_sum = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}

        for topaz_id, d in self.meta.items():
            burnclass_sum[d['burn_class']] += d['area_ha']

        return {k: burnclass_sum[k] for k in sorted(burnclass_sum)}

    def report(self, recurrence=[100, 50, 20, 10, 5, 2.5, 1]):
        """
        builds recurrence interval and annuals report for the watershed

        :param recurrence:
        :return:
        """
        wd = self.wd
        ash_dir = self.ash_dir
        fire_date = self.fire_date
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()

        water = []
        wind = []
        ash = []
        cum_water = []
        cum_wind = []
        cum_ash = []

        for topaz_id, sub in watershed.sub_iter():
            wepp_id = translator.wepp(top=topaz_id)
            ash_fn = _join(ash_dir, 'H{wepp_id}_ash.csv'.format(wepp_id=wepp_id))

            # unburned landuses won't have ash outputs
            if _exists(ash_fn):
                df = pd.read_csv(ash_fn)
                water.append(df['ash_by_water_delivery (tonne)'].to_numpy())
                wind.append(df['ash_by_wind_delivery (tonne)'].to_numpy())
                ash.append(df['ash_delivery (tonne)'].to_numpy())
                cum_water.append(df['cum_ash_by_water_delivery (tonne)'].to_numpy())
                cum_wind.append(df['cum_ash_by_wind_delivery (tonne)'].to_numpy())
                cum_ash.append(df['cum_ash_delivery (tonne)'].to_numpy())

        water = np.array(water)
        water = np.sum(water, axis=0)
        wind = np.array(wind)
        wind = np.sum(wind, axis=0)
        ash = np.array(ash)
        ash = np.sum(ash, axis=0)

        cum_water = np.array(cum_water)
        cum_water = np.sum(cum_water, axis=0)
        cum_wind = np.array(cum_wind)
        cum_wind = np.sum(cum_wind, axis=0)
        cum_ash = np.array(cum_ash)
        cum_ash = np.sum(cum_ash, axis=0)

        df = deepcopy(df)
        df['ash_by_water_delivery (tonne)'] = pd.Series(water, index=df.index)
        df['ash_by_wind_delivery (tonne)'] = pd.Series(wind, index=df.index)
        df['ash_delivery (tonne)'] = pd.Series(ash, index=df.index)

        df['cum_ash_by_water_delivery (tonne)'] = pd.Series(cum_water, index=df.index)
        df['cum_ash_by_wind_delivery (tonne)'] = pd.Series(cum_wind, index=df.index)
        df['cum_ash_delivery (tonne)'] = pd.Series(cum_ash, index=df.index)

        breaks = []    # list of indices of new fire years
        last_day = fire_date.yesterday
        for i, _row in df.iterrows():
            if _row.mo == last_day.month and _row.da == last_day.day:
                breaks.append(i)  # record the index for the new year

        yr_df = df.loc[[brk for brk in breaks],
                       ['year',
                        'cum_ash_by_water_delivery (tonne)',
                        'cum_ash_by_wind_delivery (tonne)',
                        'cum_ash_delivery (tonne)']]

        num_fire_years = len(breaks)

        annuals = {}
        for measure in ['cum_ash_by_water_delivery (tonne)',
                        'cum_ash_by_wind_delivery (tonne)',
                        'cum_ash_delivery (tonne)']:

            annuals[measure] = []
            yr_df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            colnames =['year', measure, 'probability', 'rank', 'return_interval']
            for j, (i, _row) in enumerate(yr_df.iterrows()):
                val = _row[measure]

                if val == 0.0:
                    break

                rank = j + 1
                ri = (num_fire_years + 1) / rank
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), val, prob, int(rank), ri])
                annuals[measure].append(dict(zip(colnames, data[-1])))

            _df = pd.DataFrame(data, columns=colnames)
            _df.to_csv(_join(ash_dir, '%s_ash_stats_per_year_%s.csv' % ('pw0', measure.replace(' (tonne)', ''))),
                       index=False)

        num_days = len(df.da)
        return_periods = {}
        for measure in ['ash_by_wind_delivery (tonne)', 'ash_by_water_delivery (tonne)', 'ash_delivery (tonne)']:
            return_periods[measure] = {}
            df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            for j, (i, _row) in enumerate(df.iterrows()):
                val = _row[measure]

                if val == 0.0:
                    break

                dff = _row['days_from_fire (days)']
                rank = j + 1
                ri = (num_days + 1) / rank
                ri /= 365.25
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), int(_row.mo), int(_row.da), dff, val, prob, rank, ri])

            _df = pd.DataFrame(data, columns=
            ['year', 'mo', 'da', 'days_from_fire', measure, 'probability', 'rank', 'return_interval'])
            _df.to_csv(_join(ash_dir, '%s_ash_stats_per_event_%s.csv' % ('pw0', measure.replace(' (tonne)', ''))), index=False)

            rec = weibull_series(recurrence, num_fire_years)

            num_events = len(_df.da)
            for retperiod in recurrence:
                if retperiod not in rec:
                    return_periods[measure][retperiod] = None
                else:
                    indx = rec[retperiod]
                    if indx >= num_events:
                        return_periods[measure][retperiod] = None
                    else:
                        _row = dict(_df.loc[indx, :])
                        for _m in ['year', 'mo', 'da', 'days_from_fire', 'rank']:
                            _row[_m] = int(_row[_m])

                        return_periods[measure][retperiod] = _row

        return recurrence, return_periods, annuals
