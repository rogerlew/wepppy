from typing import Dict, List, Tuple
import os
import ast
import csv
import shutil
from collections import Counter
import jsonpickle
from datetime import datetime
from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from copy import deepcopy
from collections import Counter

import math
import numpy as np
from osgeo import gdal

from deprecated import deprecated

from wepppy.all_your_base import isint, isfloat
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine, raster_stacker, validate_srs
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, WeppSoilUtil, SoilMultipleOfeSynth

from ...landuse import Landuse, LanduseMode
from ...soils import Soils
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...redis_prep import RedisPrep, TaskEnum
from ...base import NoDbBase, TriggerEvents
from ..baer.sbs_map import SoilBurnSeverityMap

from wepppyo3.raster_characteristics import identify_mode_single_raster_key

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

class Treatments(NoDbBase):
    __name__ = 'Disturbed'

    def __init__(self, wd, cfg_fn):
        super(Treatments, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.disturbed_dir)

            self._treatments_map_fn = None
            self._treatments_dom = {}
            self._treatments = {}
            
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'treatments.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Treatments), db

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Treatments.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def _nodb(self):
        return _join(self.wd, 'treatments.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'treatments.nodb.lock')


    @property
    def treatments_map_fn(self):
        """
        The treatments map filename.
        """
        return self._treatments_map_fn
    
    @property
    def treatments_dom(self):
        """
        The treatments dictionary.
        """
        return self._treatments_dom
    
    @treatments_dom.setter
    def treatments_dom(self, value: Dict[str, str]):
        """
        Set the treatments dictionary.
        """

        self.lock()
        try:
            self._treatments_dom = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise


    def validate(self, fn, breaks=None, nodata_vals=None, color_map=None):
        self.lock()

        # noinspection PyBroadException
        try:
            self._treatments_map_fn = fn

            subwta = Topaz.getInstance(self.wd).subwta
            
            # TODO: build treatments_dom

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.landuse_map)
            prep.has_sbs = True
        except FileNotFoundError:
            pass

    def build_treatments(self, treatments: Dict[str, str]):
        """
        Apply and build the treatments from the given treatments dictionary.

        The treatments dictionary should have topaz_ids as keys and the treatment keys from the landuse map as values.
        """
        from wepppy.nodb.mods.disturbed import Disturbed

        # treatment keys need to be topaz ids
        watershed = self.watershed_instance
        translator = watershed.translator_factory()

        for topaz_id in treatments.keys():
            if f'hill_{topaz_id}' not in translator.sub_ids:
                raise ValueError(f"Invalid treatment key: {topaz_id}")
            
        landuse = self.landuse_instance

        mapping_dict = landuse.get_mapping_dict()
        # treatment values need to be in the disturbed map
        for treatment_dom in treatments.values():
            if treatment_dom not in mapping_dict:
                raise ValueError(f"Invalid treatment dom: {treatment_dom}")

        self.lock()

        try:
            self._treatments = treatments
            self._treatments_dom = {}
            self._treatments_map_fn = None

            for key, value in treatments.items():
                if isinstance(value, dict):
                    self._treatments_dom[key] = value
                else:
                    raise ValueError(f"Invalid treatment value: {value}")

            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise
    