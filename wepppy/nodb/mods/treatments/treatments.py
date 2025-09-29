from typing import Dict, List, Tuple
import os
import ast
import csv
import inspect
import shutil
from collections import Counter
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
from enum import IntEnum
from deprecated import deprecated

from wepppy.all_your_base import isint, isfloat
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine, raster_stacker, validate_srs
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, WeppSoilUtil, SoilMultipleOfeSynth
from wepppy.wepp.management import ManagementSummary, Management, get_management_summary

from ...landuse import Landuse, LanduseMode
from ...soils import Soils
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...redis_prep import RedisPrep, TaskEnum
from ...base import NoDbBase, TriggerEvents, nodb_setter
from ..baer.sbs_map import SoilBurnSeverityMap
from ..disturbed import Disturbed

from .mulch_application import ground_cover_change as mulch_ground_cover_change

from wepppyo3.raster_characteristics import identify_mode_single_raster_key

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

class TreatmentsNoDbLockedException(Exception):
    pass

class TreatmentsMode(IntEnum):
    Undefined = -1
    UserDefinedSelection = 1
    UserDefinedMap = 4


class Treatments(NoDbBase):
    """
    Treatments class for WEPPcloud.

    Treatments are applied to the hillslopes based on the landuse and sbs state, after building the landuse and applying disturbed adjustments.
    """
    __name__ = 'Treatments'
    filename = 'treatments.nodb'

    def __init__(self, wd, cfg_fn):
        super(Treatments, self).__init__(wd, cfg_fn)

        with self.locked():
            os.makedirs(self.treatments_dir, exist_ok=True)
            self._treatments_domlc_d = {}
            self._treatments = {}
            self._mode = TreatmentsMode.Undefined
    
    @property
    def mode(self) -> TreatmentsMode:
        return self._mode
    
    @mode.setter
    @nodb_setter
    def mode(self, value):
        if isinstance(value, TreatmentsMode):
            self._mode = value
        elif isinstance(value, int):
            self._mode = TreatmentsMode(value)
        else:
            raise ValueError('most be TreatmentsMode or int')
            
    @property
    def treatments_dir(self):
        """
        The treatments directory.
        """
        return _join(self.wd, 'treatments')

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
    @nodb_setter
    def treatments_domlc_d(self, value: Dict[str, str]):
        """
        Set the treatments dictionary.
        """

        _domlc_d ={str(k): str(v) for k, v in value.items()}

        valid_treatment_keys = self.get_valid_treatment_keys()
        for k, v in _domlc_d.items():
            if v not in valid_treatment_keys:
                raise ValueError(f"Invalid treatment key: {k} not in {valid_treatment_keys}")

        self._treatments_domlc_d = _domlc_d

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
        if not _exists(_join(self.treatments_dir, fn)):
            raise FileNotFoundError(f"'{fn}' not found in '{self.treatments_dir}'!")

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

        raster_stacker(fn, subwta_fn, self.treatments_map)

        with self.locked():
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
            if v.get('IsTreatment', False):
                valid_keys.append(k)

        return valid_keys

    @property
    def treatments_lookup(self) -> Dict[str, str]:
        """
        Returns a dictionary of treatment disturbed_classes (e.g. mulch15, mulch30, mulch60, prescribed_fire and their valid treatment keys).

        for viewmodel templates/controls/treatments.htm
        """
        landuse = Landuse.getInstance(self.wd)
        mapping = landuse.get_mapping_dict()

        valid_treatments = {}
        for k, v in mapping.items():
            if v.get('IsTreatment', False):
                valid_treatments[v['DisturbedClass']] = k

        return valid_treatments
    
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
            self.logger.info("Treatments dictionary is empty!")
            return

        landuse = Landuse.getInstance(self.wd)
        mapping = landuse.get_mapping_dict()
        self.logger.info(f'self.wd: {self.wd}')
        self.logger.info(f'Applying treatments to {len(treatments_domlc_d)} hillslopes')
        disturbed = Disturbed.getInstance(self.wd)

        with landuse.locked():
            for topaz_id, treatment_dom in treatments_domlc_d.items():
                treatment = mapping[treatment_dom]['DisturbedClass']  # 'mulch_30', 'mulch_60', 'thinning_40_90', 'prescribed_fire'
                dom = landuse.domlc_d[topaz_id]  # -> key from map

                man_summary = landuse.managements[dom]  # -> ManagementSummary instance
                disturbed_class = getattr(man_summary, 'disturbed_class', None)  # 'tall grass', 'shrub', 'forest', 'forest high sev' etc.
                self._apply_treatment(landuse, disturbed, topaz_id, treatment, man_summary, disturbed_class)

        land_soil_replacements_d = disturbed.land_soil_replacements_d

        soils = Soils.getInstance(self.wd)
        with soils.locked():
            for topaz_id, treatment_dom in treatments_domlc_d.items():
                self._modify_soil(landuse, soils, disturbed, topaz_id)


    def _apply_treatment(self, 
                         landuse_instance: Landuse, 
                         disturbed_instance: Disturbed,
                         topaz_id: str, 
                         treatment: str, 
                         man_summary: ManagementSummary, 
                         disturbed_class: str):
        """
        Apply the treatment to the hillslope.
        """
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(topaz_id={topaz_id}, treatment={treatment}, man_summary={man_summary.as_dict()}, disturbed_class={disturbed_class})')

        if not landuse_instance.islocked():
            raise RuntimeError("Treatments.nodb is not locked!")
        
        if topaz_id.endswith('4'):
            self.logger.info(f"Skipping treatment for {topaz_id} because it is a channel.")
            return
        self.logger.info(f'topaz_id: {topaz_id}\t treatment:{treatment}\t disturbed_class: {disturbed_class}\n')

        retcode = 0
        if 'mulch' in treatment:
            retcode = self._apply_mulch(landuse_instance, disturbed_instance, topaz_id, treatment, man_summary, disturbed_class)

        elif 'prescribed_fire' in treatment:
            retcode = self._apply_prescribed_fire(landuse_instance, disturbed_instance, topaz_id, treatment, man_summary, disturbed_class)

        elif 'thinning' in treatment:
            retcode = self._apply_thinning(landuse_instance, disturbed_instance, topaz_id, treatment, man_summary, disturbed_class)

            
        self.logger.info(f'  _apply_treatment: {topaz_id} -> {landuse_instance.domlc_d[topaz_id]}\n')

        return retcode
    
    def _apply_mulch(self, 
                     landuse_instance: Landuse, 
                     disturbed_instance: Disturbed,
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

        mulch_application = treatment.replace('mulch_', '')
        mulch_application = float(mulch_application) / 30.0 # in tons per acre

        if disturbed_class in ['grass high sev fire', 'grass moderate sev fire', 'grass low sev fire',
                               'shrub high sev fire', 'shrub moderate sev fire', 'shrub low sev fire',
                               'forest high sev fire', 'forest moderate sev fire', 'forest low sev fire']:

 #       if disturbed_class in ['grass high sev fire', 'shrub high sev fire',  'forest high sev fire']:

            self.logger.info(f'Applying mulch treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')

            inrcov = man.inis[0].data.inrcov
            new_inrcov = mulch_ground_cover_change(initial_ground_cover_pct=inrcov * 100.0,
                                                   mulch_tonperacre=mulch_application) / 100.0
            self.logger.info(f'Old inrcov: {inrcov}\t New inrcov: {new_inrcov}\n')
            man.inis[0].data.inrcov = new_inrcov

            rilcov = man.inis[0].data.rilcov
            new_rilcov = mulch_ground_cover_change(initial_ground_cover_pct=rilcov * 100.0,
                                                   mulch_tonperacre=mulch_application) / 100.0
            self.logger.info(f'Old rilcov: {rilcov}\t New rilcov: {new_rilcov}\n')
            man.inis[0].data.rilcov = new_rilcov

            # write the management to disk
            new_man_fn = _split(man_summary.man_fn)[-1][:-4] + f'_{treatment}.man'
            new_man_path = _join(self.wd, 'landuse', new_man_fn)

            if not _exists(new_man_path):
                with open(new_man_path, 'w') as f:
                    f.write(str(man))

            # update the management summary
            new_man_summary = deepcopy(man_summary)
            new_man_summary.man_dir = _join(self.wd, 'landuse')
            new_man_summary.man_fn = new_man_fn
            new_man_summary.disturbed_class = f'{disturbed_class}-{treatment}'
            new_man_summary.desc += f'{man_summary.desc} - {treatment}'

            new_dom = f'{landuse_instance.domlc_d[topaz_id]}-{treatment}'
            landuse_instance.domlc_d[topaz_id] = new_dom
            self.logger.info(f'  _apply_mulch: {topaz_id} -> {new_dom}\n')

            if new_dom not in landuse_instance.managements:
                landuse_instance.managements[new_dom] = new_man_summary

            return 1

        self.logger.info(f'Could not apply mulch treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
        

    def _apply_prescribed_fire(self, 
                     landuse_instance: Landuse, 
                     disturbed_instance: Disturbed,
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str):
        """
        Apply the prescribed fire treatment to the hillslope.
        """
        if not landuse_instance.islocked():
            raise RuntimeError("Treatments.nodb is not locked!")

        disturbed_key_lookup = disturbed_instance.get_disturbed_key_lookup()

        prescribed_dom = None
        if 'forest' in disturbed_class:
            prescribed_dom = disturbed_key_lookup['forest_prescribed_fire']
            self.logger.info(f'Applying prescribed fire treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
            landuse_instance.domlc_d[topaz_id] = prescribed_dom
            self.logger.info(f'  _apply_prescribed_fire: {topaz_id} -> {prescribed_dom}\n')

        elif 'shrub' in disturbed_class:
            prescribed_dom = disturbed_key_lookup['shrub_prescribed_fire']
            self.logger.info(f'Applying prescribed fire treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
            landuse_instance.domlc_d[topaz_id] = prescribed_dom
            self.logger.info(f'  _apply_prescribed_fire: {topaz_id} -> {prescribed_dom}\n')

        elif 'grass' in disturbed_class:
            prescribed_dom = disturbed_key_lookup['grass_prescribed_fire']
            self.logger.info(f'Applying prescribed fire treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
            landuse_instance.domlc_d[topaz_id] = prescribed_dom
            self.logger.info(f'  _apply_prescribed_fire: {topaz_id} -> {prescribed_dom}\n')

        if prescribed_dom is not None and prescribed_dom not in landuse_instance.managements:
            man = get_management_summary(prescribed_dom, landuse_instance.mapping)
            landuse_instance.managements[prescribed_dom] = man

    def _apply_thinning(self, 
                     landuse_instance: Landuse, 
                     disturbed_instance: Disturbed,
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str):
        """
        Apply the prescribed fire treatment to the hillslope.
        """
        if not landuse_instance.islocked():
            raise RuntimeError("landuse.nodb is not locked!")

        disturbed_key_lookup = disturbed_instance.get_disturbed_key_lookup()
        treatment_dom = disturbed_key_lookup[treatment]

        if disturbed_class in ['forest']:
            self.logger.info(f'Applying prescribed fire treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
            landuse_instance.domlc_d[topaz_id] = treatment_dom
            self.logger.info(f'  _apply_thinning: {topaz_id} -> {treatment_dom}\n')

        if treatment_dom is not None and treatment_dom not in landuse_instance.managements:
            man = get_management_summary(treatment_dom, landuse_instance.mapping)
            landuse_instance.managements[treatment_dom] = man

    def _modify_soil(self, 
                     landuse_instance: Landuse, 
                     soils_instance: Soils,
                     disturbed_instance: Disturbed,
                     topaz_id: str):

        sol_ver = disturbed_instance.sol_ver
        land_soil_replacements_d = disturbed_instance.land_soil_replacements_d
        
        if not soils_instance.islocked():
            raise RuntimeError("soils.nodb is not locked!")

        mukey = soils_instance.domsoil_d[topaz_id]

        if '-' in mukey:
            mukey = mukey.split('-')[0]

        _soil = soils_instance.soils[mukey]
        clay = _soil.clay
        sand = _soil.sand

        assert isfloat(clay), clay
        assert isfloat(sand), sand

        texid = simple_texture(clay=clay, sand=sand)

        dom = landuse_instance.domlc_d[topaz_id]

        if 'mulch' in dom:
            disturbed_class = 'mulch'
        elif 'thinning' in dom:
            disturbed_class = 'thinning'
        else:
            man = get_management_summary(dom, landuse_instance.mapping)
            disturbed_class = man.disturbed_class

        key = (texid, disturbed_class)
        if key not in land_soil_replacements_d:
            self.logger.info(f'No soil replacements for {key} in {land_soil_replacements_d}')
            return

        disturbed_mukey = f'{mukey}-{texid}-{disturbed_class}'

        if disturbed_mukey not in soils_instance.soils:
            disturbed_fn = disturbed_mukey + '.sol'
            replacements = land_soil_replacements_d[key]

            if 'fire' in disturbed_class:
                _h0_max_om = disturbed_instance.h0_max_om
            else:
                _h0_max_om = None

            soil_u = WeppSoilUtil(_join(soils_instance.soils_dir, _soil.fname))
            if sol_ver == 7778.0:
                new = soil_u.to_7778disturbed(replacements, h0_max_om=_h0_max_om)
            else:
                new = soil_u.to_over9000(replacements, h0_max_om=_h0_max_om,
                                        version=sol_ver)

            new.write(_join(soils_instance.soils_dir, disturbed_fn))

            desc = f'{_soil.desc} - {disturbed_class}'
            soils_instance.soils[disturbed_mukey] = SoilSummary(mukey=disturbed_mukey,
                                                        fname=disturbed_fn,
                                                        soils_dir=soils_instance.soils_dir,
                                                        desc=desc,
                                                        meta_fn=_soil.meta_fn,
                                                        build_date=str(datetime.now()))

        soils_instance.domsoil_d[topaz_id] = disturbed_mukey
        self.logger.info(f'  _modify_soil: {topaz_id} -> {disturbed_mukey}\n')
