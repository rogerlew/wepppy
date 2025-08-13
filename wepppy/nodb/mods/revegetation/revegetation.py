# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from copy import deepcopy

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION

from glob import glob

import shutil
from time import sleep
from enum import IntEnum

import pandas as pd
import numpy as np

# non-standard
import jsonpickle

from datetime import datetime

# non-standard


from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture

# wepppy submodules
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase

from wepppy.nodb.mods import RangelandCover
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.soils import Soils
from wepppy.wepp.soils.utils import WeppSoilUtil, SoilMultipleOfeSynth

from wepppy.nodb.climate import Climate

from wepppy.nodb.wepp import Wepp

from wepppy.all_your_base import isfloat, NCPU

from ...base import NoDbBase, TriggerEvents


_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')
_cover_transforms_dir = _join(_data_dir, 'cover_transforms')


class RevegetationNoDbLockedException(Exception):
    pass


class Revegetation(NoDbBase, LogMixin):
    __name__ = 'Revegetation'

    def __init__(self, wd, cfg_fn):
        super(Revegetation, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self.clean()
            self._cover_transform_fn = ''
            self._user_defined_cover_transform = False
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def validate_user_defined_cover_transform(self, fn):
        self.lock()

        # noinspection PyBroadException
        try:
            assert _exists(_join(self.revegetation_dir, fn)), fn

            self._cover_transform_fn = fn
            self._user_defined_cover_transform = True
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def user_defined_cover_transform(self) -> bool:
        return getattr(self, '_user_defined_cover_transform', False)
    
    def load_cover_transform(self, reveg_scenario: str):
        if reveg_scenario == 'user_cover_transform':
            return
        
        if reveg_scenario == '':
            self.cover_transform_fn = ''
            return
        
        src_fn = _join(_cover_transforms_dir, reveg_scenario)
        assert _exists(src_fn), src_fn
        self.cover_transform_fn = reveg_scenario
        shutil.copyfile(src_fn, self.cover_transform_path)

    @property
    def cover_transform_fn(self) -> str:
        return getattr(self, '_cover_transform_fn', '')
    
    @cover_transform_fn.setter
    def cover_transform_fn(self, value: str) -> str:
        self.lock()

        # noinspection PyBroadException
        try:
            self._cover_transform_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def revegetation_dir(self):
        return _join(self.wd, 'revegetation')

    @property
    def cover_transform_path(self) -> str:
        return _join(self.revegetation_dir, self.cover_transform_fn)
    

    @property
    def cover_transform(self):
        cover_transform_path = self.cover_transform_path 
        if not _exists(cover_transform_path) or not cover_transform_path.endswith('.csv'):
            return None

        # Replace 'your_file.csv' with the path to your CSV file
        df = pd.read_csv(cover_transform_path, header=None)

        # Extracting the first two rows for keys
        sbs = df.iloc[0]  # Soil burn severities
        landuse = df.iloc[1]  # Landuse types

        # Initialize the dictionary
        data_dict = {}

        # Iterate over columns to populate the dictionary
        for col in range(df.shape[1]):
            key = (sbs[col], landuse[col])
            if key not in data_dict:
                data_dict[key] = []
            data_dict[key].extend(df.iloc[2:, col])

        # Convert lists to np.array of type np.float32
        for key in data_dict:
            data_dict[key] = np.array(data_dict[key], dtype=np.float32)

        return data_dict

    @property
    def status_log(self):
        return os.path.abspath(_join(self.revegetation_dir, 'status.log'))

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        with open(_join(wd, 'revegetation.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Revegetation)

        if _exists(_join(wd, 'READONLY')):
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            if not db.islocked():
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Revegetation.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)

    @property
    def _nodb(self):
        return _join(self.wd, 'revegetation.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'revegetation.nodb.lock')

    def clean(self):
        revegetation_dir = self.revegetation_dir
        if _exists(revegetation_dir):
            shutil.rmtree(revegetation_dir)
        os.mkdir(revegetation_dir)

    def on(self, evt):
        pass
