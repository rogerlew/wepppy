from typing import Dict, List, Optional, Tuple
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

try:
    from wepppy.all_your_base import isint, isfloat
except ImportError:  # pragma: no cover - fallback for reduced package exports
    from wepppy.all_your_base.all_your_base import isint, isfloat
from wepppy.all_your_base.geo import wgs84_proj4, read_raster, haversine, raster_stacker, validate_srs
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, WeppSoilUtil, SoilMultipleOfeSynth
from wepppy.wepp.management import ManagementSummary, Management, get_management_summary

from wepppy.nodb.core import *
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.nodb.mods.disturbed import Disturbed

from .mulch_application import ground_cover_change as mulch_ground_cover_change

from wepppyo3.raster_characteristics import identify_mode_single_raster_key

__all__ = [
    'TreatmentsNoDbLockedException',
    'TreatmentsMode',
    'Treatments',
]

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

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(Treatments, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

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

        # resolve path (accept basename or absolute path)
        if _exists(fn):
            treatment_path = fn
        else:
            treatment_path = _join(self.treatments_dir, fn)
            if not _exists(treatment_path):
                raise FileNotFoundError(f"'{fn}' not found!")
        treatment_path = os.path.abspath(treatment_path)

        # ensure file lives in treatments_dir
        if os.path.abspath(os.path.dirname(treatment_path)) != os.path.abspath(self.treatments_dir):
            raise FileNotFoundError(f"'{fn}' not found in '{self.treatments_dir}'!")

        # check it is a gdal friendly raster
        try:
            ds = gdal.Open(treatment_path)
            if ds is None:
                raise ValueError(f"'{treatment_path}' is not a valid gdal raster file!")

            # validate it has an srs
            srs = ds.GetProjection()
            if not validate_srs(srs):
                raise ValueError(f"'{treatment_path}' does not have a valid srs!")
        except Exception:
            raise ValueError(f"'{treatment_path}' is not a valid gdal raster file!")

        # reproject to align with the subwta
        if not _exists(subwta_fn):
            raise FileNotFoundError(f"'{subwta_fn}' not found!")

        raster_stacker(treatment_path, subwta_fn, self.treatments_map)

        # identify treatments from map
        domlc_d = identify_mode_single_raster_key(
            key_fn=subwta_fn,
            parameter_fn=self.treatments_map,
            ignore_channels=True,
            ignore_keys=set(),
        )
        domlc_d = {str(k): str(v) for k, v in domlc_d.items()}

        # filter out non treatment keys
        valid_keys = set(self.get_valid_treatment_keys())
        domlc_d = {k: v for k, v in domlc_d.items() if v in valid_keys}
        if domlc_d:
            self.treatments_domlc_d = domlc_d
        else:
            self.logger.info("Treatments map contained no valid treatment keys.")

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

        for viewmodel templates/controls/treatments_pure.htm
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

        def _infer_mulch_base(dom_value: str) -> Optional[str]:
            if not dom_value.isdigit():
                return None
            dom_int = int(dom_value)
            pct = dom_int % 1000
            if pct not in (15, 30, 60):
                return None
            base = dom_int // 1000
            return str(base) if base > 0 else None

        with landuse.locked():
            domlc_d = dict(landuse.domlc_d or {})
            for topaz_id, treatment_dom in treatments_domlc_d.items():
                treatment = mapping[treatment_dom]['DisturbedClass']  # 'mulch_30', 'mulch_60', 'thinning_40_90', 'prescribed_fire'
                dom = landuse.domlc_d[topaz_id]  # -> key from map
                dom_key = str(dom)
                man_summary = landuse.managements.get(dom_key)
                if man_summary is None:
                    base_dom = _infer_mulch_base(dom_key)
                    if base_dom is not None and base_dom in landuse.managements:
                        dom = base_dom
                        dom_key = base_dom
                        landuse.domlc_d[topaz_id] = base_dom
                        domlc_d[str(topaz_id)] = base_dom
                        man_summary = landuse.managements[base_dom]
                if man_summary is None:
                    raise KeyError(dom_key)
                disturbed_class = getattr(man_summary, 'disturbed_class', None)  # 'tall grass', 'shrub', 'forest', 'forest high sev' etc.
                new_dom = self._apply_treatment(
                    landuse,
                    disturbed,
                    topaz_id,
                    treatment,
                    man_summary,
                    disturbed_class,
                )
                if new_dom is not None:
                    domlc_d[str(topaz_id)] = str(new_dom)
            landuse.domlc_d = domlc_d
            missing_dom_keys = sorted(
                {str(dom) for dom in domlc_d.values() if str(dom) not in landuse.managements}
            )
            for dom_key in missing_dom_keys:
                base_dom = _infer_mulch_base(dom_key)
                if base_dom is None or base_dom not in landuse.managements:
                    continue
                pct = int(dom_key) % 1000
                treatment = f"mulch_{pct}"
                base_summary = landuse.managements[base_dom]
                man = base_summary.get_management()

                mulch_application = float(pct) / 30.0
                inrcov = man.inis[0].data.inrcov
                new_inrcov = mulch_ground_cover_change(
                    initial_ground_cover_pct=inrcov * 100.0,
                    mulch_tonperacre=mulch_application,
                ) / 100.0
                man.inis[0].data.inrcov = new_inrcov

                rilcov = man.inis[0].data.rilcov
                new_rilcov = mulch_ground_cover_change(
                    initial_ground_cover_pct=rilcov * 100.0,
                    mulch_tonperacre=mulch_application,
                ) / 100.0
                man.inis[0].data.rilcov = new_rilcov

                new_man_fn = _split(base_summary.man_fn)[-1][:-4] + f'_{treatment}.man'
                new_man_path = _join(self.wd, 'landuse', new_man_fn)
                if not _exists(new_man_path):
                    with open(new_man_path, 'w') as f:
                        f.write(str(man))

                new_man_summary = deepcopy(base_summary)
                new_man_summary.man_dir = _join(self.wd, 'landuse')
                new_man_summary.man_fn = new_man_fn
                base_disturbed = getattr(base_summary, 'disturbed_class', None)
                if base_disturbed:
                    new_man_summary.disturbed_class = f'{base_disturbed}-{treatment}'
                new_man_summary.desc = f'{base_summary.desc} - {treatment}'
                new_man_summary.inrcov = new_inrcov
                new_man_summary.rilcov = new_rilcov
                try:
                    new_man_summary.key = int(dom_key)
                except (TypeError, ValueError):
                    new_man_summary.key = dom_key
                landuse.managements[dom_key] = new_man_summary

        land_soil_replacements_d = disturbed.land_soil_replacements_d

        soils = Soils.getInstance(self.wd)
        landuse.dump_landuse_parquet()
        with soils.locked():
            for topaz_id, treatment_dom in treatments_domlc_d.items():
                self._modify_soil(landuse, soils, disturbed, topaz_id)


    def _apply_treatment(
                         self,
                         landuse_instance: Landuse, 
                         disturbed_instance: Disturbed,
                         topaz_id: str, 
                         treatment: str, 
                         man_summary: ManagementSummary, 
                         disturbed_class: str) -> Optional[str]:
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

        new_dom = None
        if 'mulch' in treatment:
            new_dom = self._apply_mulch(
                landuse_instance,
                disturbed_instance,
                topaz_id,
                treatment,
                man_summary,
                disturbed_class,
            )

        elif 'prescribed_fire' in treatment:
            new_dom = self._apply_prescribed_fire(
                landuse_instance,
                disturbed_instance,
                topaz_id,
                treatment,
                man_summary,
                disturbed_class,
            )

        elif 'thinning' in treatment:
            new_dom = self._apply_thinning(
                landuse_instance,
                disturbed_instance,
                topaz_id,
                treatment,
                man_summary,
                disturbed_class,
            )

            
        self.logger.info(f'  _apply_treatment: {topaz_id} -> {landuse_instance.domlc_d[topaz_id]}\n')

        return new_dom

    def _mulch_management_key(self, dom_key: str, treatment: str) -> str:
        base_token = str(dom_key).split("-", maxsplit=1)[0]
        percent_token = treatment.replace("mulch_", "").strip()
        try:
            base_value = int(base_token)
            percent_value = int(percent_token)
        except (TypeError, ValueError):
            return f"{dom_key}-{treatment}"
        return str(base_value * 1000 + percent_value)
    
    def _apply_mulch(
                     self,
                     landuse_instance: Landuse, 
                     disturbed_instance: Disturbed,
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str) -> Optional[str]:
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
            new_man_summary.desc = f'{man_summary.desc} - {treatment}'
            new_man_summary.inrcov = new_inrcov
            new_man_summary.rilcov = new_rilcov

            base_dom = landuse_instance.domlc_d[topaz_id]
            new_dom = self._mulch_management_key(base_dom, treatment)
            landuse_instance.domlc_d[topaz_id] = new_dom
            self.logger.info(f'  _apply_mulch: {topaz_id} -> {new_dom}\n')

            if new_dom not in landuse_instance.managements:
                try:
                    new_man_summary.key = int(new_dom)
                except (TypeError, ValueError):
                    new_man_summary.key = new_dom
                landuse_instance.managements[new_dom] = new_man_summary

            return new_dom

        self.logger.info(f'Could not apply mulch treatment to hillslope {topaz_id} with disturbed_class {disturbed_class}\n')
        

    def _apply_prescribed_fire(
                     self,
                     landuse_instance: Landuse, 
                     disturbed_instance: Disturbed,
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str) -> Optional[str]:
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

        return prescribed_dom

    def _apply_thinning(
                     self,
                     landuse_instance: Landuse, 
                     disturbed_instance: Disturbed,
                     topaz_id: str, 
                     treatment: str, 
                     man_summary: ManagementSummary, 
                     disturbed_class: str) -> Optional[str]:
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

        return treatment_dom if disturbed_class in ['forest'] else None

    def _resolve_source_soil_path(
        self,
        soils_instance: Soils,
        soil_fname: str,
        *,
        topaz_id: str,
        mukey: str,
        soil_summary_dir: Optional[str] = None,
    ) -> str:
        local_soil_path = _join(soils_instance.soils_dir, soil_fname)
        if _exists(local_soil_path):
            return local_soil_path

        checked_paths = [local_soil_path]

        if isinstance(soil_summary_dir, str) and soil_summary_dir:
            summary_soil_path = _join(soil_summary_dir, soil_fname)
            if summary_soil_path not in checked_paths:
                checked_paths.append(summary_soil_path)
                if _exists(summary_soil_path):
                    self.logger.info(
                        "Using summary soil path for topaz_id=%s mukey=%s: %s",
                        topaz_id,
                        mukey,
                        summary_soil_path,
                    )
                    return summary_soil_path

        parent_wd = getattr(soils_instance, "parent_wd", None)
        if isinstance(parent_wd, str) and parent_wd:
            parent_soil_path = _join(parent_wd, "soils", soil_fname)
            if parent_soil_path not in checked_paths:
                checked_paths.append(parent_soil_path)
                if _exists(parent_soil_path):
                    self.logger.info(
                        "Using parent soil path for topaz_id=%s mukey=%s: %s",
                        topaz_id,
                        mukey,
                        parent_soil_path,
                    )
                    return parent_soil_path

        checked = ", ".join(checked_paths)
        raise FileNotFoundError(
            f"Missing source soil file for topaz_id={topaz_id!r}, mukey={mukey!r}. "
            f"Checked: {checked}"
        )

    def _modify_soil(self, 
                     landuse_instance: Landuse, 
                     soils_instance: Soils,
                     disturbed_instance: Disturbed,
                     topaz_id: str):

        sol_ver = disturbed_instance.sol_ver
        land_soil_replacements_d = disturbed_instance.land_soil_replacements_d
        
        if not soils_instance.islocked():
            raise RuntimeError("soils.nodb is not locked!")

        raw_mukey = soils_instance.domsoil_d[topaz_id]

        # Prefer the "base" soil key (token before the first '-') so we don't stack
        # modifications when domsoil_d already points at a disturbed derivative.
        # Legacy ISRIC keys used '-' as part of the base ID (e.g. "Cambisols-clay loam"),
        # so we fall back to the raw key when the base token is not present.
        base_mukey = raw_mukey
        if "-" in base_mukey:
            base_mukey = base_mukey.split("-", 1)[0]

        if base_mukey in soils_instance.soils:
            lookup_mukey = base_mukey
            mukey = base_mukey
        elif raw_mukey in soils_instance.soils:
            lookup_mukey = raw_mukey
            mukey = raw_mukey
        else:
            raise KeyError(
                f"Unknown soil key for topaz_id={topaz_id!r}: domsoil_d={raw_mukey!r} (base={base_mukey!r})"
            )

        _soil = soils_instance.soils[lookup_mukey]
        soil_u = None
        source_soil_path = None

        # SoilSummary properties (`clay`, `sand`) parse from on-disk .sol files.
        # Scenario clones can carry soils.nodb without local .sol payloads, so
        # resolve the source path explicitly with parent-run fallback.
        if isinstance(_soil, SoilSummary):
            source_soil_path = self._resolve_source_soil_path(
                soils_instance,
                _soil.fname,
                topaz_id=str(topaz_id),
                mukey=str(mukey),
                soil_summary_dir=getattr(_soil, "soils_dir", None),
            )
            soil_u = WeppSoilUtil(source_soil_path)
            clay = soil_u.clay
            sand = soil_u.sand
        else:
            clay = getattr(_soil, "clay", None)
            sand = getattr(_soil, "sand", None)

        assert isfloat(clay), clay
        assert isfloat(sand), sand

        texid = simple_texture(clay=clay, sand=sand)

        dom = landuse_instance.domlc_d[topaz_id]
        man_summary = landuse_instance.managements.get(dom)
        if man_summary is not None:
            disturbed_class = getattr(man_summary, "disturbed_class", None)
            if isinstance(disturbed_class, str):
                if "mulch" in disturbed_class:
                    disturbed_class = "mulch"
                elif "thinning" in disturbed_class:
                    disturbed_class = "thinning"
        else:
            disturbed_class = None

        if disturbed_class is None:
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

            if soil_u is None:
                soil_fname = getattr(_soil, "fname", None)
                if not isinstance(soil_fname, str) or not soil_fname:
                    raise FileNotFoundError(
                        f"Cannot resolve source soil file for topaz_id={topaz_id!r}, mukey={mukey!r}"
                    )
                source_soil_path = self._resolve_source_soil_path(
                    soils_instance,
                    soil_fname,
                    topaz_id=str(topaz_id),
                    mukey=str(mukey),
                    soil_summary_dir=getattr(_soil, "soils_dir", None),
                )
                soil_u = WeppSoilUtil(source_soil_path)

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
