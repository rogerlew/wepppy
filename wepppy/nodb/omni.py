import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

from copy import deepcopy
from glob import glob
import json
import shutil
from time import sleep

# non-standard
import jsonpickle
import utm
import what3words

# wepppy
import requests

from wepppy.export.gpkg_export import gpkg_extract_objective_parameter

from .base import (
    NoDbBase,
    TriggerEvents
)

def _run_contrast(contrast_id, contrast_name, contrasts, wd, wepp_bin='wepp_a557997'):
    from wepppy.nodb import Landuse, Soils, Wepp

    omni_dir = _join(wd, 'omni', 'contrasts', contrast_id)

    if _exists(omni_dir):
        shutil.rmtree(omni_dir)

    os.makedirs(omni_dir)

    for fn in os.listdir(wd):
        if fn in ['climate', 'watershed', 'climate.nodb', 'watershed.nodb']:
            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                os.symlink(src, dst)

    for nodb_fn in ['wepp.nodb']:
        src = _join(wd, nodb_fn)
        dst = _join(omni_dir, nodb_fn)
        if not _exists(dst):
            shutil.copy(src, dst)

        with open(dst, 'r') as f:
            d = json.load(f)

        d['wd'] = omni_dir

        with open(dst, 'w') as f:
            json.dump(d, f)

    wepp = Wepp.getInstance(omni_dir)
    wepp.wepp_bin = wepp_bin
    wepp.clean()  # this creates the directories in the {omni_dir}/wepp

    # symlink the other wepp watershed input files
    og_runs_dir = _join(wd, 'wepp', 'runs/')
    omni_runs_dir = _join(omni_dir, 'wepp', 'runs/')
    for fn in os.listdir(og_runs_dir):
        _fn = _split(fn)[-1]
        if _fn.startswith('pw0') or _fn.endswith('.txt') or _fn.endswith('.inp'):
            src = _join(og_runs_dir, fn)
            dst = _join(omni_runs_dir, fn)
            if not _exists(dst):
                os.symlink(src, dst)

    wepp.make_watershed_run(wepp_id_paths=list(contrasts.values()))
    wepp.run_watershed()


def _omni_clone(scenario, wd):
    omni_dir = _join(wd, 'omni', 'scenarios', scenario)

    if _exists(omni_dir):
        shutil.rmtree(omni_dir)

    os.makedirs(omni_dir)

    for fn in os.listdir(wd):
        if fn in ['climate', 'dem', 'watershed', 'climate.nodb', 'dem.nodb', 'watershed.nodb']:
            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                os.symlink(src, dst)

        elif fn.endswith('.nodb'):
            if fn == 'omni.nodb':
                continue

            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                shutil.copy(src, dst)

            with open(dst, 'r') as f:
                d = json.load(f)

            d['wd'] = omni_dir

            with open(dst, 'w') as f:
                json.dump(d, f)
    
    for fn in os.listdir(wd):
        if fn == 'omni':
            continue

        src = _join(wd, fn)
        if os.path.isdir(src):
            dst = _join(omni_dir, fn)

            if not _exists(dst):
                try:
                    # Create directory structure without copying files
                    for root, dirs, _ in os.walk(src):
                        for dir_name in dirs:
                            src_dir = _join(root, dir_name)
                            rel_path = os.path.relpath(src_dir, src)
                            dst_dir = _join(dst, rel_path)
                            if not _exists(dst_dir):
                                os.makedirs(dst_dir, exist_ok=True)
                except PermissionError as e:
                    print(f"Permission denied creating directory: {e}")
                except OSError as e:
                    print(f"Error creating directory: {e}")

            if not _exists(dst):
                os.makedirs(dst, exist_ok=True)

    return omni_dir


def _build_scenario(scenario, wd):
    from wepppy.nodb import Landuse, Soils, Wepp
    from wepppy.nodb.mods import Disturbed

    # change to working dir of parent weppcloud project
    os.chdir(wd)
    
    # assert we know how to handle the scenario
    assert scenario in ['uniform_low', 'uniform_high', 'uniform_moderate', 'uniform_high', 'thinning']
    new_wd = _omni_clone(scenario, wd)

    # identify burn class
    sbs = None
    if scenario == 'uniform_low':
        sbs = 1
    elif scenario == 'uniform_moderate':
        sbs = 2
    elif scenario == 'uniform_high':
        sbs = 3


    # get disturbed and landuse instances
    disturbed = Disturbed.getInstance(new_wd)
    landuse = Landuse.getInstance(new_wd)
    
    # handle uniform burn severity cases
    if sbs in [1, 2, 3]:
        sbs_fn = disturbed.build_uniform_sbs(int(sbs))
        res = disturbed.validate(sbs_fn)

        landuse.build()

    # handle other cases
    else:
        disturbed_key = disturbed.get_disturbed_key_lookup()
        lc_key = disturbed_key[scenario]  # assumes scenario is a key in the disturbed map wepp/managements/*.json

        forest_keys = []
        for key, value in disturbed_key.items():
            if 'forest' in value:
                forest_keys.append(int(key))

        modify_list = []
        for topaz_id, dom in landuse.domlc_d.items():
            if int(dom) in forest_keys:
                modify_list.append(topaz_id)

        # this modifies the landuses and builds managements
        landuse.modify(modify_list, lc_key)

    soils = Soils.getInstance(new_wd)
    soils.build()

    wepp = Wepp.getInstance(new_wd)
    # todo: implement omni_hillslope_prep that uses symlinks

    wepp.prep_hillslopes(omni=True)
    wepp.run_hillslopes(omni=True)

    wepp.prep_watershed()
    wepp.run_watershed()


class OmniNoDbLockedException(Exception):
    pass


class Omni(NoDbBase):
    """
    Runs scenarios inside of a parent scenario
    """
    __name__ = 'Omni'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    def __init__(self, wd, cfg_fn='0.cfg'):
        super(Omni, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            
            if not _exists(self.omni_dir):
                os.makedirs(self.omni_dir)

            self._scenarios = self.config_get_list('omni', 'scenarios')
            self._contrasts = self.config_get_list('omni', 'contrasts')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def scenarios(self):
        return self._scenarios
    
    @scenarios.setter
    def scenarios(self, value):

        self.lock()
        try:
            self._scenarios = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def contrasts(self):
        return self._contrasts
    
    @contrasts.setter
    def contrasts(self, value):

        self.lock()
        try:
            self._contrasts = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    @property
    def omni_dir(self):
        return _join(self.wd, 'omni')
    
    @property
    def status_log(self):
        return os.path.abspath(_join(self.omni_dir, 'status.log'))

    def clean(self):
        shutil.rmtree(self.omni_dir)
        sleep(1)
        os.makedirs(self.omni_dir)

    def get_objective_parameter_from_gpkg(self, objective_parameter, scenario=None):
        if scenario is None:
            gpkg_fn = glob(_join(self.wd, 'export/arcmap/*.gpkg'))[0]
        else:
            gpkg_fn = glob(_join(self.wd, f'omni/scenarios/{scenario}/export/arcmap/*.gpkg'))[0]

        objective_parameter_descending, total_objective_parameter = gpkg_extract_objective_parameter(gpkg_fn)
        return objective_parameter_descending, total_objective_parameter
    
    def build_contrasts(self, control_scenario='uniform_high', contrast_scenario='thinning',
                        obj_param='runoff',
                        cumulative_obj_param_threshold_fraction=0.8,
                        contrast_hillslope_limit=None,
                        hill_min_slope=None, hill_max_slope=None,
                        select_burn_severities=None,
                        select_topaz_ids=None):
        """
        Extracts the specified objective parameter from the specified GeoPackage file.

        Parameters
        ----------
        control_scenario : str
            The control scenario to use for the contrast. Must be one of the following:
            'uniform_low', 'uniform_moderate', 'uniform_high', 'thinning', 'mulching30', 'mulching60', None
        contrast_scenario : str
            The contrast scenario to use for the contrast. Must be one of the following:
            'uniform_low', 'uniform_moderate', 'uniform_high', 'thinning', 'mulching30', 'mulching60', None
        obj_param : str
            The objective parameter to extract. Must be one of the following:
            'Soil_Loss_kg', 'Runoff_mm', 'Runoff_Volume_m3', 'Subrunoff_mm', 'Subrunoff_Volume_m3', 'Total_Phosphorus_kg'
        cumulative_obj_param_threshold_fraction : float
            The fraction of the total objective parameter to use as a threshold for the cumulative objective parameter.
            No more contrasts are created after this threshold is reached.
        contrast_hillslope_limit : int
            The maximum number of hillslopes to use for the contrast. If None, all hillslopes are selected.
        hill_min_slope : float
            The minimum slope of the hillslope to use for the contrast. If None, all hillslopes are selected.
        hill_max_slope : float
            The maximum slope of the hillslope to use for the contrast. If None, all hillslopes are selected.
        select_burn_severities : list
            A list of burn severities to use for the contrast. If None, all burn severities are selected.
            The burn severities must be one of the following: 1, 2, 3
        select_topaz_ids : list
            A list of topaz_ids to use for the contrast. If None, all topaz_ids are selected.
        """
        from wepppy.nodb import Watershed

        # TODO
        # filter
        #   hillslope slope steepness criteria < 60%
        #   slope length, aspect, etc.
        #   manually defined topaz_ids
        #   burn severity filter 

        # filter and selection report


        wd = self.wd

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        top2wepp = {k: v for k, v in translator.top2wepp.items() if not (str(k).endswith('4') or int(k) == 0)}

        # find hillslopes with the most erosion from the control scenario
        # soils_erosion_descending is a list of ObjectiveParameter named_tuples with fields: topaz_id, wepp_id, and value
        obj_param_descending, total_erosion_kg = self.get_objective_parameter_from_gpkg(obj_param, scene=control_scenario)

        if len(obj_param_descending) == 0:
            raise Exception('No soil erosion data found!')
        
        contrasts = {}
        running_obj_param = 0.0
        for i, d in enumerate(obj_param_descending):
            if contrast_hillslope_limit is not None and i >= contrast_hillslope_limit:
                break

            running_obj_param += d.soil_loss_kg
            if running_obj_param / total_erosion_kg > cumulative_obj_param_threshold_fraction:
                break

            topaz_id = d.topaz_id
            wepp_id = d.wepp_id
            if contrast_scenario is None:
                contrast_name = f'{control_scenario},{topaz_id}_to_undisturbed'
            
            else:
                contrast_name = f'{control_scenario},{topaz_id}_to_{contrast_scenario}'
            
            contrast_dir = _join(wd, f'omni/contrasts/{contrast_name}/wepp/runs/')
            
            contrast = {}
            for _topaz_id, _wepp_id in top2wepp.items():

                # need to do it this way so the wepp_ids stay ordered.
                if str(_topaz_id) == str(topaz_id):
                    if contrast_scenario is None:
                        wepp_id_path = _join(wd, f'wepp/output/H{wepp_id}')   
                    else: 
                        wepp_id_path = _join(wd, f'omni/scenarios/{contrast_scenario}/wepp/output/H{wepp_id}')
                else:
                    if control_scenario is None:
                        wepp_id_path = _join(wd, f'wepp/output/H{_wepp_id}')
                    else:
                        wepp_id_path = _join(wd, f'omni/scenarios/{control_scenario}/wepp/output/H{_wepp_id}')
                contrast[_topaz_id] = wepp_id_path  # os.path.relpath(wepp_id_path, contrast_dir)

            contrasts[contrast_name] = contrast

        self.contrasts = contrasts

        # save parameters for defining contrasts
        

    def run_omni_contrasts(self):
        for contrast_id, (contrast_name, _contrasts) in enumerate(self.contrasts.items()):
            _run_contrast(str(contrast_id), contrast_name, _contrasts, self.wd)

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'omni.nodb')

        if not _exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Omni), db

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
        return Omni.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def _nodb(self):
        return _join(self.wd, 'omni.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'omni.nodb.lock')

    def run_omni_scenarios(self):
        for scenario in self.scenarios:
            _build_scenario(scenario, self.wd)
