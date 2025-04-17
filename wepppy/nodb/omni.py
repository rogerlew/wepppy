import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

from enum import IntEnum
from copy import deepcopy
from glob import glob
import json
import shutil
from time import sleep

# non-standard
import jsonpickle
import utm

# wepppy
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.export.gpkg_export import gpkg_extract_objective_parameter

from .base import (
    NoDbBase,
    TriggerEvents
)

class OmniScenario(IntEnum):
    UniformLow = 1
    UniformModerate = 2
    UniformHigh = 3
    Thinning = 4
    Mulch30 = 5
    Mulch60 = 6
    SBSmap = 7

    # TODO: search for references to mulching30 and mulching60
    @staticmethod
    def parse(x):
        if x == 'uniform_low':
            return OmniScenario.UniformLow
        elif x == 'uniform_moderate':
            return OmniScenario.UniformModerate
        elif x == 'uniform_high':
            return OmniScenario.UniformHigh
        elif x == 'thinning':
            return OmniScenario.Thinning
        elif x == 'mulch30':
            return OmniScenario.Mulch30
        elif x == 'mulch60':
            return OmniScenario.Mulch60
        elif x == 'sbsmap':
            return OmniScenario.SBSmap
        raise KeyError

    def __str__(self):
        if self == OmniScenario.UniformLow:
            return 'uniform_low'
        elif self == OmniScenario.UniformModerate:
            return 'uniform_moderate'
        elif self == OmniScenario.UniformHigh:
            return 'uniform_high'
        elif self == OmniScenario.Thinning:
            return 'thinning'
        elif self == OmniScenario.Mulch30:
            return 'mulching30'
        elif self == OmniScenario.Mulch60:
            return 'mulching60'
        elif self == OmniScenario.SBSmap:
            return 'sbsmap'
        
        raise KeyError
    

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


def _omni_clone(scenario: OmniScenario, wd):
    _scenario = str(scenario)
    omni_dir = _join(wd, 'omni', 'scenarios', _scenario)

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

def _build_scenario(scenario: OmniScenario, wd, mulching_base_scenario=None):
    from wepppy.nodb import Landuse, Soils, Wepp
    from wepppy.nodb.mods import Disturbed

    _scenario = str(scenario)

    # change to working dir of parent weppcloud project
    os.chdir(wd)
    
    # assert we know how to handle the scenario
    assert isinstance(scenario, OmniScenario)
    new_wd = _omni_clone(scenario, wd)

    # identify burn class
    sbs = None
    if scenario == OmniScenario.UniformLow:
        sbs = 1
    elif scenario == OmniScenario.UniformModerate:
        sbs = 2
    elif scenario == OmniScenario.UniformHigh:
        sbs = 3

    # get disturbed and landuse instances
    disturbed = Disturbed.getInstance(new_wd)
    landuse = Landuse.getInstance(new_wd)
    
    # handle uniform burn severity cases
    if sbs in [1, 2, 3]:
        sbs_fn = disturbed.build_uniform_sbs(int(sbs))
        res = disturbed.validate(sbs_fn)

        landuse.build()

    elif scenario == OmniScenario.SBSmap:
        raise NotImplementedError


    elif scenario == OmniScenario.Mulch30 or \
         scenario == OmniScenario.Mulch60:
        
        assert mulching_base_scenario is not None, \
            'Mulching scenario requires a base scenario'
        assert mulching_base_scenario in [OmniScenario.UniformLow, 
                                          OmniScenario.UniformModerate, 
                                          OmniScenario.UniformHigh, 
                                          OmniScenario.SBSmap], \
            'Mulching scenario requires a base scenario' 
        
        for topaz_id, dom in landuse.domlc_d.items():
            # treat burned forest, shrub, and grass with mulching by increasing cover
            pass


    # handle other cases
    else:
        disturbed_key = disturbed.get_disturbed_key_lookup()
        # TODO: and mulching30, mulching60, landcover map
        lc_key = disturbed_key[_scenario]  # assumes scenario is a key in the disturbed map wepp/managements/*.json

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


class Omni(NoDbBase, LogMixin):
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

            self._scenarios = {OmniScenario.parse(v) for v in self.config_get_list('omni', 'scenarios')}
            self._contrasts = self.config_get_list('omni', 'contrasts')

            self._contrast_scenario = None
            self._control_scenario = None
            self._contrast_object_param = None
            self._contrast_cumulative_obj_param_threshold_fraction = None
            self._contrast_hillslope_limit = None
            self._contrast_hill_min_slope = None
            self._contrast_hill_max_slope = None
            self._contrast_select_burn_severities = None
            self._contrast_select_topaz_ids = None

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def scenarios(self):
        return self._scenarios
    
    @scenarios.setter
    def scenarios(self, value: set[OmniScenario]):

        self.lock()
        try:
            self._scenarios = value
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise


    def parse_inputs(self, kwds):
        self.lock()

        # noinspection PyBroadException
        try:        

            _scenarios = set()

            if kwds.get('omni_run_uniform_scenario_low_severity_fire', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.UniformLow)

            if kwds.get('omni_run_uniform_scenario_moderate_severity_fire', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.UniformModerate)

            if kwds.get('omni_run_uniform_scenario_high_severity_fire', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.UniformHigh)

            if kwds.get('omni_run_uniform_scenario_thinning', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.Thinning)

            if kwds.get('omni_run_uniform_scenario_mulching30', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.Mulch30)

            if kwds.get('omni_run_uniform_scenario_mulching60', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.Mulch60)

            if kwds.get('omni_run_uniform_scenario_sbsmap', 'off').lower().startswith('on'):
                _scenarios.add(OmniScenario.SBSmap)

            self._scenarios = _scenarios

            control_scenario = kwds.get('omni_control_scenario', None)
            if control_scenario is not None:
                self._control_scenario =OmniScenario.parse(control_scenario)

            contrast_scenario = kwds.get('omni_contrast_scenario', None)
            if contrast_scenario is not None:
                self._contrast_scenario = OmniScenario.parse(contrast_scenario)

            omni_contrast_objective_parameter = kwds.get('omni_contrast_objective_parameter', None)
            if omni_contrast_objective_parameter is not None:
                self._contrast_object_param = omni_contrast_objective_parameter

            contrast_cumulative_obj_param_threshold_fraction = kwds.get('omni_contrast_cumulative_obj_param_threshold_fraction', None)
            if contrast_cumulative_obj_param_threshold_fraction is not None:
                self._contrast_cumulative_obj_param_threshold_fraction = contrast_cumulative_obj_param_threshold_fraction
                
            contrast_hillslope_limit = kwds.get('omni_contrast_hillslope_limit', None)
            if contrast_hillslope_limit is not None:
                self._contrast_hillslope_limit = contrast_hillslope_limit
                
            hill_min_slope = kwds.get('omni_contrast_hill_min_slope', None)
            if hill_min_slope is not None:
                self._contrast_hill_min_slope = hill_min_slope

            hill_max_slope = kwds.get('ommni_contrast_hill_max_slope', None)
            if hill_max_slope is not None:
                self._contrast_hill_max_slope = hill_max_slope
                
            select_burn_severities = kwds.get('omni_contrast_select_burn_severities', None)
            if select_burn_severities is not None:
                self._contrast_select_burn_severities = select_burn_severities
            
            select_topaz_ids = kwds.get('omni_contrast_select_topaz_ids', None)
            if select_topaz_ids is not None:
                self._contrast_select_topaz_ids = select_topaz_ids

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

        objective_parameter_descending, total_objective_parameter = gpkg_extract_objective_parameter(gpkg_fn, obj_param=objective_parameter)
        return objective_parameter_descending, total_objective_parameter
    
    def build_contrasts(self, control_scenario=OmniScenario.UniformHigh, contrast_scenario=OmniScenario.Thinning,
                        obj_param='Runoff_mm',
                        contrast_cumulative_obj_param_threshold_fraction=0.8,
                        contrast_hillslope_limit=None,
                        hill_min_slope=None, hill_max_slope=None,
                        select_burn_severities=None,
                        select_topaz_ids=None):
        """
        Extracts the specified objective parameter from the specified GeoPackage file.

        Parameters
        ----------
        control_scenario : OmniScenario
            The control scenario to use for the contrast. Must be one of the following:
            'uniform_low', 'uniform_moderate', 'uniform_high', 'thinning', 'mulching30', 'mulching60', None
        contrast_scenario : OmniScenario
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

        self.log('Omni::build_contrasts')

        # save parameters for defining contrasts
        self.lock()
        try:
            self._contrast_scenario = contrast_scenario
            self._control_scenario = control_scenario
            self._contrast_object_param = obj_param
            self._contrast_cumulative_obj_param_threshold_fraction = contrast_cumulative_obj_param_threshold_fraction
            self._contrast_hillslope_limit = contrast_hillslope_limit
            self._contrast_hill_min_slope = hill_min_slope
            self._contrast_hill_max_slope = hill_max_slope
            self._contrast_select_burn_severities = select_burn_severities
            self._contrast_select_topaz_ids = select_topaz_ids

            self.dump_and_unlock()
        except:
            self.unlock('-f')
            raise

        self._build_contrasts()

    def _build_contrasts(self):
        obj_param = self._contrast_object_param
        contrast_cumulative_obj_param_threshold_fraction = self._contrast_cumulative_obj_param_threshold_fraction
        contrast_hillslope_limit = self._contrast_hillslope_limit
        contrast_hill_min_slope = self._contrast_hill_min_slope
        contrast_hill_max_slope = self._contrast_hill_max_slope
        contrast_select_burn_severities = self._contrast_select_burn_severities
        contrast_select_topaz_ids = self._contrast_select_topaz_ids
        contrast_scenario = self._contrast_scenario
        control_scenario = self._control_scenario


        # TODO
        # filter
        #   hillslope slope steepness criteria < 60%
        #   slope length, aspect, etc.
        #   manually defined topaz_ids
        #   burn severity filter 

        # filter and selection report


        from wepppy.nodb import Watershed

        wd = self.wd

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        top2wepp = {k: v for k, v in translator.top2wepp.items() if not (str(k).endswith('4') or int(k) == 0)}

        # find hillslopes with the most erosion from the control scenario
        # soils_erosion_descending is a list of ObjectiveParameter named_tuples with fields: topaz_id, wepp_id, and value
        obj_param_descending, total_erosion_kg = self.get_objective_parameter_from_gpkg(obj_param, scenario=control_scenario)

        from pprint import pprint
        pprint(obj_param_descending)

        if len(obj_param_descending) == 0:
            raise Exception('No soil erosion data found!')
        
        contrasts = {}
        running_obj_param = 0.0
        for i, d in enumerate(obj_param_descending):
            if contrast_hillslope_limit is not None and i >= contrast_hillslope_limit:
                break

            running_obj_param += d.value
            if running_obj_param / total_erosion_kg > contrast_cumulative_obj_param_threshold_fraction:
                break

            topaz_id = d.topaz_id
            wepp_id = d.wepp_id
            if contrast_scenario is None:
                contrast_name = f'{control_scenario},{topaz_id}_to_undisturbed'
            
            else:
                contrast_name = f'{control_scenario},{topaz_id}_to_{contrast_scenario}'
            
#            contrast_dir = _join(wd, f'omni/contrasts/{contrast_name}/wepp/runs/')
            
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

      
    def run_omni_contrasts(self):

        self.log('Omni::run_omni_contrasts')

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
    def _status_channel(self):
        return f'{self.runid}:omni'

    @property
    def _nodb(self):
        return _join(self.wd, 'omni.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'omni.nodb.lock')

    def run_omni_scenarios(self):
        self.log('Omni::run_omni_scenarios\n')

        if not self.scenarios:
            self.log('  Omni::run_omni_scenarios: No scenarios to run\n')
            raise Exception('No scenarios to run')

        for scenario in self.scenarios:
            self.log(f'  Omni::run_omni_scenarios: {scenario}\n')
            _build_scenario(scenario, self.wd)
