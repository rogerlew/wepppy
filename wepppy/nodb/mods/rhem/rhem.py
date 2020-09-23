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

from wepppy.watershed_abstraction import SlopeFile

# wepppy submodules
from wepppy.nodb.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods import RangelandCover
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.soils import Soils
from wepppy.nodb.topaz import Topaz
from wepppy.nodb.climate import Climate

from wepppy.nodb.mods import Baer
from wepppy.nodb.wepp import Wepp

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os
import math
from enum import IntEnum
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from subprocess import Popen, PIPE
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_EXCEPTION

from datetime import datetime
import time

import pickle

from glob import glob

import shutil

# non-standard
import jsonpickle

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

import wepppy

# wepppy

from wepppy.rhem import make_parameter_file, make_hillslope_run, run_hillslope

from wepppy.climates.cligen import ClimateFile

from wepppy.wepp.stats import ChannelWatbal, HillslopeWatbal, ReturnPeriods, SedimentDelivery

from .rhempost import RhemPost

try:
    NCPU = int(os.environ['WEPPPY_NCPU'])
except KeyError:
    NCPU = math.floor(multiprocessing.cpu_count() * 0.5)
    if NCPU < 1:
        NCPU = 1


class RhemNoDbLockedException(Exception):
    pass


class Rhem(NoDbBase, LogMixin):
    __name__ = 'Rhem'

    def __init__(self, wd, cfg_fn):
        super(Rhem, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            rhem_dir = self.rhem_dir
            if not _exists(rhem_dir):
                os.mkdir(rhem_dir)

            config = self.config
            self.clean()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def rhem_dir(self):
        return _join(self.wd, 'rhem')

    @property
    def runs_dir(self):
        return _join(self.wd, 'rhem', 'runs')

    @property
    def output_dir(self):
        return _join(self.wd, 'rhem', 'output')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.runs_dir, 'status.log'))

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'rhem.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Rhem)

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'rhem.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rhem.nodb.lock')

    @property
    def has_run(self):
        return len(glob(_join(self.output_dir, '*.sum'))) > 0

    #
    # hillslopes
    #
    def prep_hillslopes(self):
        self.log('Prepping Hillslopes... ')
        wd = self.wd

        watershed = Watershed.getInstance(wd)

        soils = Soils.getInstance(wd)
        rangeland_covers = RangelandCover.getInstance(wd)
        climate = Climate.getInstance(self.wd)
        cli_dir = self.cli_dir
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        out_dir = self.output_dir

        for topaz_id, summary in watershed.sub_iter():
            mukey = soils.domsoil_d[topaz_id]
            soil_texture = soils.soils[mukey].texture
            slp_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
            slp = SlopeFile(slp_fn)
            cover = rangeland_covers.covers[topaz_id]

            scn_name = 'hill_{}'.format(topaz_id)
            par_fn = make_parameter_file(scn_name=scn_name,
                                         out_dir=runs_dir,
                                         soil_texture=soil_texture,
                                         moisture_content=0.25,
                                         bunchgrass_cover=cover['bunchgrass'],
                                         forbs_cover=cover['forbs'],
                                         shrubs_cover=cover['shrub'],
                                         sodgrass_cover=cover['sodgrass'],
                                         rock_cover=cover['rock'],
                                         basal_cover=cover['basal'],
                                         litter_cover=cover['litter'],
                                         cryptogams_cover=cover['cryptogams'],
                                         slope_length=slp.length,
                                         slope_steepness=slp.slope_scalar,
                                         sl=slp.slopes,
                                         sx=slp.distances,
                                         width=summary.width,
                                         model_version='WEPPcloud')

            stm_fn = _join(runs_dir, 'hill_{}.stm'.format(topaz_id))

            cli_summary = climate.sub_summary(topaz_id)
            cli_path = _join(cli_dir, cli_summary['cli_fn'])
            climate_file = ClimateFile(cli_path)
            climate_file.make_storm_file(stm_fn)

            run_fn = _join(runs_dir, 'hill_{}.run'.format(topaz_id))
            make_hillslope_run(run_fn, par_fn, stm_fn, _join(out_dir, 'hill_{}.sum'.format(topaz_id)), scn_name)

        self.log_done()

    def clean(self):
        if _exists(self.status_log):
            os.remove(self.status_log)

        runs_dir = self.runs_dir
        if _exists(runs_dir):
            shutil.rmtree(runs_dir)
        os.mkdir(runs_dir)

        output_dir = self.output_dir
        if _exists(output_dir):
            shutil.rmtree(output_dir)
        os.mkdir(output_dir)

    def run_hillslopes(self):
        self.log('Running Hillslopes\n')
        watershed = Watershed.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)

        pool = ThreadPoolExecutor(NCPU)
        futures = []

        def oncomplete(rhemrun):
            status, _id, elapsed_time = rhemrun.result()
            assert status
            self.log('  {} completed run in {}s\n'.format(_id, elapsed_time))

        sub_n = watershed.sub_n
        for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
            self.log('  submitting topaz={} (hill {} of {})\n'.format(topaz_id, i + 1, sub_n))
            futures.append(pool.submit(lambda p: run_hillslope(*p), (topaz_id, runs_dir)))
            futures[-1].add_done_callback(oncomplete)

        wait(futures, return_when=FIRST_EXCEPTION)

        self.log('Running RhemPost... ')
        rhempost = RhemPost.getInstance(self.wd)
        rhempost.run_post()

        try:
            from wepppy.weppcloud import RunStatistics
            rs = RunStatistics.getInstance('/geodata/weppcloud_runs')
            rs.increment_hillruns(watershed.config_stem, watershed.sub_n)
        except Exception:
            pass

        self.log_done()

    def report_loss(self):
        output_dir = self.output_dir

        raise NotImplementedError

    def report_return_periods(self):
        output_dir = self.output_dir

        raise NotImplementedError

    def run_wepp_hillslopes(self):
        wepp = Wepp.getInstance(self.wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()