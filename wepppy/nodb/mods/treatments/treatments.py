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
from wepppy.wepp.management import ManagementSummary, Management

from ...landuse import Landuse, LanduseMode
from ...soils import Soils
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...redis_prep import RedisPrep, TaskEnum
from ...base import NoDbBase, TriggerEvents
from ..baer.sbs_map import SoilBurnSeverityMap
from ...mixins.log_mixin import LogMixin

from wepppyo3.raster_characteristics import identify_mode_single_raster_key

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

class Treatments(NoDbBase, LogMixin):
    __name__ = 'Treatments'

    def __init__(self, wd, cfg_fn):
        super(Treatments, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            os.makedirs(self.treatments_dir, exist_ok=True)

            self._treatments_domlc_d = {}
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
    def treatments_dir(self):
        """
        The treatments directory.
        """
        return _join(self.wd, 'treatments')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.treatments_dir, 'status.log'))

    @property
    def treatments_map(self):
        """
        The treatments map path.
        """
        return _join(self.treatments_dir, 'treatments.tif')
    
    @property
    def treatments_domlc_d(self):
        """
        The treatments dictionary.
        """
        return self._treatments_domlc_d
    
    @treatments_domlc_d.setter
    def treatments_domlc_d(self, value: Dict[str, str]):
        """
        Set the treatments dictionary.
        """

        _domlc_d ={str(k): str(v) for k, v in value.items()}

        valid_treatment_keys = self.get_valid_treatment_keys()
        for k, v in _domlc_d.items():
            if v not in valid_treatment_keys:
                raise ValueError(f"Invalid treatment key: {k} not in {valid_treatment_keys}")
            
        self.lock()
        try:
            self._treatments_domlc_d = _domlc_d
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    def validate(self, fn):
        """
        Validate the treatments map.

        fn should be a gdal friendly raster file (e.g. .tif, .img) stored in the treatments directory.
        """

        subwta_fn = Watershed.getInstance(self.wd).subwta
        
        # check it exists
        if not _exists(fn):
            raise FileNotFoundError(f"'{fn}' not found!")
        
        # check it is in the treatments_dir
        if not _exists(_join(self.disturbed_dir, fn)):
            raise FileNotFoundError(f"'{fn}' not found in '{self.disturbed_dir}'!")

        # check it is a gdal friendly raster
        try:
            ds = gdal.Open(fn)
            if ds is None:
                raise ValueError(f"'{fn}' is not a valid gdal raster file!")

            # validate it has an srs
            srs = ds.GetProjection()
            if not validate_srs(srs):
                raise ValueError(f"'{fn}' does not have a valid srs!")
        except:
            raise ValueError(f"'{fn}' is not a valid gdal raster file!")

        # reproject to align with the subwta
        if not _exists(subwta_fn):
            raise FileNotFoundError(f"'{subwta_fn}' not found!")

        raster_stacker(subwta_fn, fn, self.treatments_map)


        self.lock()

        # noinspection PyBroadException
        try:
            # identify treatments from map
            domlc_d = identify_mode_single_raster_key(
                key_fn=subwta_fn, 
                parameter_fn=self.treatments_map, 
                ignore_channels=True, 
                ignore_keys=set())
            domlc_d = {str(k): str(v) for k, v in domlc_d.items()}

            # filter out non treatment keys
            valid_keys = self.get_valid_treatment_keys()
            domlc_d = {k: v for k, v in domlc_d.items() if k in valid_keys}

            self._treatments_dom_lc = {k: str(v) for k, v in domlc_d.items()}

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

    def get_valid_treatment_keys(self):
        landuse = Landuse.getInstance(self.wd)
        mapping = landuse.get_mapping_dict()

        valid_keys = []
        for k, v in mapping.items():
            if v['ManagementFile'].endswith('null.man'):
                valid_keys.append(k)

        return valid_keys


    def build_treatments(self):
        """
        Apply and build the treatments to the project.

        treatments_domlc_d should be set at this point.
        """

        from wepppy.nodb.mods.disturbed import Disturbed

        # treatment keys need to be topaz ids
        watershed = self.watershed_instance
        translator = watershed.translator_factory()

        treatments_domlc_d = self.treatments_domlc_d

        if treatments_domlc_d is None:
            raise ValueError("Treatments dictionary is not set!")

        if len(treatments_domlc_d) == 0:
            self.log("Treatments dictionary is empty!")
            return

        landuse = Landuse.getInstance(self.wd)
        mapping = landuse.get_mapping_dict()

        landuse.lock()
        try:
            # loop over the treatments_domlc_d and apply the treatments to the hillslope based on it's
            # existing landuse and sbs state

            for topaz_id, treatment_dom in treatments_domlc_d.items():
                treatment = mapping[treatment_dom]['DisturbedClass']  # 'mulch30', 'mulch60', 'prescribed_fire'
                dom = landuse.domlc_d[topaz_id]  # -> key from map

                man_summary = landuse.managements[dom]  # -> ManagementSummary instance
                disturbed_class = getattr(man_summary, 'disturbed_class', None)  # 'tall grass', 'shrub', 'forest', 'forest high sev' etc.
                self._apply_treatment(landuse, topaz_id, treatment, man_summary, disturbed_class)

            landuse.dump_and_unlock()
        except Exception:
            landuse.unlock('-f')
            raise
    
    def _apply_treatment(self, 
                         landuse_instance: Landuse, 
                         topaz_id: str, 
                         treatment: str, 
                         man_summary: ManagementSummary, 
                         disturbed_class: str):
        """
        Apply the treatment to the hillslope.
        """

        if not landuse_instance.islocked():
            raise RuntimeError("Treatments.nodb is not locked!")
        
        if treatment not in ['mulch30', 'mulch60', 'prescribed_fire']:
            raise NotImplementedError(f"Treatment '{treatment}' not implemented!")

        if topaz_id.endswith('4'):
            self.log(f"Skipping treatment for {topaz_id} because it is a channel.")
            return
        self.log(f'topaz_id: {topaz_id}\t treatment:{treatment}\t disturbed_class: {disturbed_class}\n')

        if 'mulch' in treatment:
            return self._apply_mulch(landuse_instance, topaz_id, treatment, man_summary, disturbed_class)

        if 'prescribed_fire' in treatment:
            return self._apply_prescribed_fire(landuse_instance, topaz_id, treatment, man_summary, disturbed_class)

    def _apply_mulch(self, 
                     landuse_instance: Landuse, 
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str):
        """
        Apply the mulch treatment to the hillslope.
        """

        # test with camp creek fire at bullrun

        if not landuse_instance.islocked():
            raise RuntimeError("Treatments.nodb is not locked!")

        man = man_summary.get_management()  # Management instance, reads from disk

        mulch_cover_change = treatment.replace('mulch', '')
        mulch_cover_change = int(mulch_cover_change) / 100.0

        if disturbed_class in ['grass high sev fire', 'grass moderate sev fire', 'grass low sev fire',
                               'shrub high sev fire', 'shrub moderate sev fire', 'shrub low sev fire',
                               'forest high sev fire', 'forest moderate sev fire', 'forest low sev fire']:
 
            cancov = man.inis[0].data.cancov
            new_cancov = max(1.0, cancov + mulch_cover_change)
            self.log(f'Applying mulch treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
            self.log(f'Old cancov: {cancov}\t New cancov: {new_cancov}\n')
            man.inis[0].data.cancov = new_cancov

            # write the management to disk
            new_man_fn = _split(man_summary.man_fn)[-1][:-4] + f'_{treatment}.man'
            new_man_path = _join(self.wd, 'landuse', new_man_fn)
            with open(new_man_path, 'w') as f:
                f.write(str(man))

            # update the management summary
            new_man_summary = deepcopy(man_summary)
            new_man_summary.man_fn = new_man_fn
            new_man_summary.desc += f' - {treatment}'

            new_dom = f'{landuse_instance.domlc_d[topaz_id]}-{treatment}'
            landuse_instance.domlc_d[topaz_id] = new_dom

            if new_dom not in landuse_instance.managements:
                landuse_instance.managements[new_dom] = new_man_summary

            return 1

        self.log(f'Could not apply mulch treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
        

    def _apply_prescribed_fire(self, 
                     landuse_instance: Landuse, 
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str):
        """
        Apply the prescribed fire treatment to the hillslope.
        """
        if not landuse_instance.islocked():
            raise RuntimeError("Treatments.nodb is not locked!")

        man = man_summary.get_management()  # Management instance, reads from disk

        if disturbed_class in ['grass high sev fire', 'grass moderate sev fire', 'grass low sev fire',
                               'shrub high sev fire', 'shrub moderate sev fire', 'shrub low sev fire',
                               'forest', 'young forest', 'forest high sev fire', 'forest moderate sev fire', 'forest low sev fire']:
            # TODO
            raise NotImplementedError(f"Prescribed fire treatment not implemented for {disturbed_class}!")
