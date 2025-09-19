from __future__ import annotations
from typing import List, Optional

import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

from csv import DictWriter

import base64

import pandas as pd

from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

from enum import IntEnum
from copy import deepcopy
from glob import glob
import json
import shutil
from time import sleep

# non-standard
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
    Mulch = 5
    SBSmap = 8
    Undisturbed = 9
    PrescribedFire = 10

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
        elif x == 'mulch':
            return OmniScenario.Mulch
        elif x == 'sbs_map':
            return OmniScenario.SBSmap
        elif x == 'undisturbed':
            return OmniScenario.Undisturbed
        elif x == 'prescribed_fire':
            return OmniScenario.PrescribedFire
        raise KeyError(f"Invalid scenario: {x}")

    def __str__(self):
        """
        the string representations match the distubed_class names
        """
        if self == OmniScenario.UniformLow:
            return 'uniform_low'
        elif self == OmniScenario.UniformModerate:
            return 'uniform_moderate'
        elif self == OmniScenario.UniformHigh:
            return 'uniform_high'
        elif self == OmniScenario.Thinning:
            return 'thinning'
        elif self == OmniScenario.Mulch:
            return 'mulch'
        elif self == OmniScenario.SBSmap:
            return 'sbs_map'
        elif self == OmniScenario.Undisturbed:
            return 'undisturbed'
        elif self == OmniScenario.PrescribedFire:
            return 'prescribed_fire'
        raise KeyError

    def __eq__(self, other):
        if isinstance(other, OmniScenario):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        if isinstance(other, str):
            return self.value == OmniScenario.parse(other).value
        return False
    

def _run_contrast(contrast_id, contrast_name, contrasts, wd, wepp_bin='wepp_a557997'):
    from wepppy.nodb import Landuse, Soils, Wepp

    omni_dir = _join(wd, 'omni', 'contrasts', contrast_id)

    if _exists(omni_dir):
        shutil.rmtree(omni_dir)

    os.makedirs(omni_dir)
    os.makedirs(_join(omni_dir, 'soils'), exist_ok=True)
    os.makedirs(_join(omni_dir, 'landuse'), exist_ok=True)

    for fn in os.listdir(wd):
        if fn in ['climate', 'watershed', 'climate.nodb', 'watershed.nodb', 'landuse.nodb', 'soils.nodb']:
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
    wepp.report_loss()


def _omni_clone(scenario_def: dict, wd: str):
    
    scenario = scenario_def.get('type')
    _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
    omni_dir = _join(wd, 'omni', 'scenarios', _scenario_name)

    if _exists(omni_dir):
        shutil.rmtree(omni_dir)

    os.makedirs(omni_dir)

    for fn in os.listdir(wd):
        if fn in ['climate', 'dem', 'watershed', 'climate.nodb', 'dem.nodb', 'watershed.nodb']:
            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                os.symlink(src, dst)

        elif fn in ['disturbed', 'soils']:
            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                shutil.copytree(src, dst)

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


def _omni_clone_sibling(new_wd: str, omni_clone_sibling_name: str):
    """
    after _omni_clone copies watershed, climates, wepp from the base_scenario (parent)

    we copy the sibling scenario's disturbed, landuse, and soils so that managements/treatments
    are applied to the correct scenario.
    """
    
    sibling_wd = _join(new_wd, '..', omni_clone_sibling_name)
    if not _exists(sibling_wd):
        raise FileNotFoundError(f"'{sibling_wd}' not found!")
    
    # replace disturbed, landuse, and soils
    os.remove(_join(new_wd, 'disturbed.nodb'))
    os.remove(_join(new_wd, 'landuse.nodb'))
    os.remove(_join(new_wd, 'soils.nodb'))

    shutil.rmtree(_join(new_wd, 'disturbed'))
    shutil.rmtree(_join(new_wd, 'landuse'))
    shutil.rmtree(_join(new_wd, 'soils'))

    # copy the sibling scenario
    shutil.copyfile(_join(sibling_wd, 'disturbed.nodb'), _join(new_wd, 'disturbed.nodb'))
    shutil.copyfile(_join(sibling_wd, 'landuse.nodb'), _join(new_wd, 'landuse.nodb'))
    shutil.copyfile(_join(sibling_wd, 'soils.nodb'), _join(new_wd, 'soils.nodb'))

    # copy the sibling directories
    shutil.copytree(_join(sibling_wd, 'disturbed'), _join(new_wd, 'disturbed'))
    shutil.copytree(_join(sibling_wd, 'landuse'), _join(new_wd, 'landuse'))
    shutil.copytree(_join(sibling_wd, 'soils'), _join(new_wd, 'soils'))


def _scenario_name_from_scenario_definition(scenario_def) -> str:
    """
    Get the scenario name from the scenario definition.
    :param scenario_def: The scenario definition.
    :return: The scenario name.
    """
    _scenario = scenario_def.get('type')

    if _scenario == OmniScenario.Thinning:
        canopy_cover = scenario_def.get('canopy_cover')
        ground_cover = scenario_def.get('ground_cover')
        return f'{_scenario}_{canopy_cover}_{ground_cover}'.replace('%', '')
    elif _scenario == OmniScenario.Mulch:
        ground_cover_increase = scenario_def.get('ground_cover_increase')
        base_scenario = scenario_def.get('base_scenario')
        return f'{_scenario}_{ground_cover_increase}_{base_scenario}'.replace('%', '')
    elif _scenario == OmniScenario.SBSmap:
        sbs_file_path = scenario_def.get('sbs_file_path', None)
        if sbs_file_path is not None:
            sbs_fn = _split(sbs_file_path)[-1]
            sbs_hash = base64.b64encode(bytes(sbs_fn, 'utf-8')).decode('utf-8').rstrip('=')
            return f'{_scenario}_{sbs_hash}'
        return f'{_scenario}'
    else:
        return str(_scenario)


class OmniNoDbLockedException(Exception):
    pass


class Omni(NoDbBase, LogMixin):
    """
    Omni: Manage and execute nested WEPP scenarios and contrasts without a database.
    This class persists its state in a NoDb file (omni.nodb) and provides a high-level
    interface for:
        - Defining multiple scenarios (e.g., thinning, prescribed fire, uniform burns, mulch, SBS map)
        - Parsing user inputs from a web backend or CLI into scenario definitions
        - Building and running individual scenarios or batches of scenarios
        - Defining and executing contrast analyses between a control scenario and one or more 
            contrast scenarios based on objective parameters (e.g., runoff, soil loss)
        - Generating summary reports and parquet outputs for scenarios and contrasts
    Key Responsibilities:
        • Initialization & Locking
            - __init__(wd, cfg_fn='0.cfg'): load or create omni.nodb, set up working directory,
                acquire a lock during modifications
            - getInstance / getInstanceFromRunID: load a persisted Omni instance, honoring locks
        • Scenario Management
            - scenarios (property): list of scenario definitions (dicts)
            - parse_scenarios(parsed_inputs): validate and store a list of (scenario_enum, params)
            - run_omni_scenario(scenario_def): build and run one scenario, append to scenarios list
            - run_omni_scenarios(): execute all parsed scenarios in a consistent order
            - clean_scenarios(): remove and recreate the omni/scenarios directory
        • Contrast Management
            - contrasts (property): mapping of contrast_name → per-hillslope path dict
            - parse_inputs(kwds): read control/contrast scenario parameters from keyword dict
            - build_contrasts(control_scenario_def, contrast_scenario_def, …): compute and save
                per-hillslope contrasts up to a cumulative objective-parameter fraction
            - run_omni_contrasts(): invoke _run_contrast for each saved contrast
        • Reporting
            - scenarios_report(): concatenate per-scenario loss_pw0 parquet files into one DataFrame
            - compile_hillslope_summaries(exclude_yr_indxs=None): build and save detailed
                hillslope summaries across base and all parsed scenarios
    Public Attributes (stored in omni.nodb):
        - wd: working directory for WEPP inputs/outputs
        - _scenarios: list of scenario definition dicts
        - _contrasts: dict mapping contrast names to input/output path mappings
        - _control_scenario, _contrast_scenario: OmniScenario enums
        - _contrast_object_param, _contrast_cumulative_obj_param_threshold_fraction, etc.: parameters
            controlling contrast selection and filtering
    Usage Example:
            omni = Omni.getInstance(wd="/path/to/project")
            omni.parse_scenarios([
                    (OmniScenario.Thinning, {"type": "thinning", "canopy_cover": 0.80, "ground_cover": 0.50}),
                    (OmniScenario.UniformHigh, {"type": "uniform_high"})
            ])
            omni.run_omni_scenarios()
            report_df = omni.scenarios_report()
            omni.build_contrasts(
                    control_scenario_def={"type": "uniform_high"},
                    contrast_scenario_def={"type": "thinning"},
                    obj_param="Runoff_mm",
                    contrast_cumulative_obj_param_threshold_fraction=0.75
            )
            omni.run_omni_contrasts()
            contrasts_df = pd.read_parquet(os.path.join(omni.wd, "omni", "contrasts.out.parquet"))
    """
    filename = 'omni.nodb'
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

            self._scenarios = []
            self._contrasts = None
            self._contrast_names = None

            self._contrast_scenario = None
            self._control_scenario = None
            self._contrast_object_param = None
            self._contrast_cumulative_obj_param_threshold_fraction = None
            self._contrast_hillslope_limit = None
            self._contrast_hill_min_slope = None
            self._contrast_hill_max_slope = None
            self._contrast_select_burn_severities = None
            self._contrast_select_topaz_ids = None
            self._mulching_base_scenario = None

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

    def parse_scenarios(self, parsed_inputs):
        """
        Parse the scenarios and their parameters into the NoDb structure.
        :param parsed_inputs: List of (scenario_enum, params) tuples
        """
        self.lock()

        try:
            self._scenarios = []  # Reset scenarios

            for scenario_enum, params in parsed_inputs:
                scenario_type = params.get('type')
                
                # Handle scenarios with parameters
                if scenario_enum == OmniScenario.Thinning:
                    canopy_cover = params.get('canopy_cover')
                    ground_cover = params.get('ground_cover')
                    if not canopy_cover or not ground_cover:
                        raise ValueError('Thinning requires canopy_cover and ground_cover')
                    self._scenarios.append({
                        'type': scenario_type,
                        'canopy_cover': canopy_cover,
                        'ground_cover': ground_cover
                    })
                elif scenario_enum == OmniScenario.Mulch:
                    ground_cover_increase = params.get('ground_cover_increase')
                    base_scenario = params.get('base_scenario')
                    if not ground_cover_increase or not base_scenario:
                        raise ValueError('Mulching requires ground_cover_increase and base_scenario')
                    
                    self._scenarios.append({
                        'type': scenario_type,
                        'ground_cover_increase': ground_cover_increase,
                        'base_scenario': base_scenario
                    })
                elif scenario_enum == OmniScenario.SBSmap:
                    sbs_file_path = params.get('sbs_file_path')
                    if not sbs_file_path:
                        raise ValueError('SBS Map requires a file path')
                    self._scenarios.append({
                        'type': scenario_type,
                        'sbs_file_path': sbs_file_path
                    })
                else:
                    # Scenarios without parameters (UniformLow, UniformModerate, etc.)
                    self._scenarios.append({
                        'type': scenario_type
                    })

            self.dump_and_unlock()

        except Exception as e:
            self.unlock()
            raise Exception(f'Failed to parse inputs: {str(e)}')


    def parse_inputs(self, kwds):
        """
        this is called from the web backend to set the parameters in the nodb
        """
        self.lock()

        # noinspection PyBroadException
        try:        

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
    def contrast_names(self):
        return self._contrast_names

    @contrast_names.setter
    def contrast_names(self, value):

        self.lock()
        try:
            self._contrast_names = value
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

    def clean_scenarios(self):
        scenarios_dir = _join(self.omni_dir, 'scenarios')

        if _exists(scenarios_dir):
            shutil.rmtree(scenarios_dir)
            sleep(1)

        os.makedirs(scenarios_dir)

    def get_objective_parameter_from_gpkg(self, objective_parameter, scenario=None):
        if scenario is None:
            gpkg_fn = glob(_join(self.wd, 'export/arcmap/*.gpkg'))[0]
        else:
            gpkg_fn = glob(_join(self.wd, f'omni/scenarios/{scenario}/export/arcmap/*.gpkg'))[0]

        objective_parameter_descending, total_objective_parameter = gpkg_extract_objective_parameter(gpkg_fn, obj_param=objective_parameter)
        return objective_parameter_descending, total_objective_parameter

    def clear_contrasts(self):
        self.lock()
        try:
            self._contrasts = None
            self._contrast_names = None
            self.dump_and_unlock()
        except Exception:
            self.unlock('-f')
            raise

    def build_contrasts(self, control_scenario_def, contrast_scenario_def,
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

        control_scenario = _scenario_name_from_scenario_definition(control_scenario_def)
        contrast_scenario = _scenario_name_from_scenario_definition(contrast_scenario_def)

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

    @property
    def base_scenario(self):
        if self.has_sbs:
            return OmniScenario.SBSmap
        return OmniScenario.Undisturbed

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

        if contrast_scenario == str(self.base_scenario):
            contrast_scenario = None

        if control_scenario == str(self.base_scenario):
            control_scenario = None

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

        if len(obj_param_descending) == 0:
            raise Exception('No soil erosion data found!')
        
        contrasts = []
        contrast_names = []

        report_fn = _join(self.wd, 'omni', 'contrasts', 'build_report.ndjson')
        report_fp = open(report_fn, 'a')

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
                contrast_name = f'{control_scenario},{topaz_id}__to__{self.base_scenario}'
            else:
                contrast_name = f'{control_scenario},{topaz_id}__to__{contrast_scenario}'
            
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

            contrasts.append(contrast)
            contrast_names.append(contrast_name)
            
            report_fp.write(json.dumps({
                'control_scenario': control_scenario,
                'contrast_scenario': contrast_scenario,
                'wepp_id': wepp_id,
                'topaz_id': topaz_id,
                'obj_param': d.value,
                'running_obj_param': running_obj_param,
                'pct_cumulative': running_obj_param / total_erosion_kg * 100
            }) + '\n')

        report_fp.close()
        try:
            self.lock()
            if self._contrasts is None:
                self._contrasts = contrasts
                self._contrast_names = contrast_names
            else:
                self._contrasts.extend(contrasts)
                self._contrast_names.extend(contrast_names)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def run_omni_contrasts(self):

        self.log('Omni::run_omni_contrasts')

        for contrast_id, (contrast_name, _contrasts) in enumerate(zip(self.contrast_names, self.contrasts), start=1):
            print(f'Running contrast {contrast_id} of {len(self.contrasts)}: {contrast_name}')
            _run_contrast(str(contrast_id), contrast_name, _contrasts, self.wd)

    def run_omni_contrast(self, contrast_id: int):
        self.log(f'Omni::run_omni_contrast {contrast_id}')
        contrast_name = self.contrast_names[contrast_id - 1]
        _contrasts = self.contrasts[contrast_id - 1]
        _run_contrast(str(contrast_id), contrast_name, _contrasts, self.wd)

    def contrasts_report(self):
        from wepppy.nodb.wepp import Wepp

        parquet_files = {}

        for contrast_id, (contrast_name, _contrasts) in enumerate(zip(self.contrast_names, self.contrasts), start=1):
            parquet_files[contrast_name] = _join(self.wd, 'omni', 'contrasts', str(contrast_id), 'wepp', 'output', 'loss_pw0.out.parquet')

        dfs = []
        for contrast_id, (contrast_name, path) in enumerate(parquet_files.items(), start=1):
            if not os.path.isfile(path):
                continue

            control_scenario, contrast_scenario = contrast_name.split('__to__')
            control_scenario, topaz_id = control_scenario.split(',')

            if control_scenario == 'None':
                control_scenario = str(self.base_scenario)
                ctrl_parquet = _join(self.wd, 'wepp', 'output', 'loss_pw0.out.parquet')
            else:
                ctrl_parquet = _join(self.wd, 'omni', 'scenarios', control_scenario, 'wepp', 'output', 'loss_pw0.out.parquet')

            if not _exists(ctrl_parquet):
                raise FileNotFoundError(f"Control scenario parquet file '{ctrl_parquet}' does not exist!")

            df = pd.read_parquet(path)         # expects columns: key, v, units
            df['control_scenario'] = control_scenario
            df['contrast_topaz_id'] = topaz_id
            df['contrast'] = contrast_name
            df['_contrast_name'] = str(contrast_name)
            df['contrast_id'] = contrast_id

            ctrl_df = pd.read_parquet(ctrl_parquet)

            # Join control metrics by 'key' and add difference (control - contrast)
            _ctrl = (
                ctrl_df[['key', 'v', 'units']]
                .drop_duplicates(subset=['key'])
                .rename(columns={'v': 'control_v', 'units': 'control_units'})
            )

            df = df.merge(_ctrl, on='key', how='left')

            # Sanity check: units should match between control and contrast
            _bad = df[df['control_units'].notna() & (df['units'] != df['control_units'])]
            if not _bad.empty:
                self.log(f"WARNING[contrasts_report]: units mismatch for keys -> {sorted(_bad['key'].unique())}\n")

            # Requested measure: control - contrast
            df['control-contrast_v'] = df['control_v'] - df['v']

            dfs.append(df)

        if not dfs:
            # nothing to do
            return pd.DataFrame(columns=['key', 'v', 'units', 'contrast'])

        combined = pd.concat(dfs, ignore_index=True)
        out_path = _join(self.wd, 'omni', 'contrasts.out.parquet')
        combined.to_parquet(out_path)

        return combined

    @property
    def _status_channel(self):
        return f'{self.runid}:omni'

    @property
    def _nodb(self):
        return _join(self.wd, 'omni.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'omni.nodb.lock')
    
    def run_omni_scenario(self, scenario_def: dict):
        scenario = scenario_def.get('type')

        self.log(f'Omni::run_scenario({scenario})\n')

        if not isinstance(scenario, OmniScenario):
            raise TypeError('scenario must be an instance of OmniScenario')

        self._build_scenario(scenario_def, self.wd, self.base_scenario)

        if scenario not in self.scenarios:
            self.scenarios = self.scenarios + [scenario_def]
            
        self.log(f'  Omni::run_scenario({scenario}): {scenario} completed\n')

    @property
    def ran_scenarios(self) -> List[str]:
        """
        Returns a list of scenario names that have been run.
        :return: List of scenario names.
        """
        ran_scenarios = []
        for scenario_def in self.scenarios:
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if _exists(_join(self.wd, 'omni', 'scenarios', _scenario_name, 'wepp', 'output', 'loss_pw0.out.parquet')):
                ran_scenarios.append(_scenario_name)
                
        return ran_scenarios
    
    def run_omni_scenarios(self):
        self.log('Omni::run_omni_scenarios\n')

        self.clean_scenarios()

        if not self.scenarios:
            self.log('  Omni::run_omni_scenarios: No scenarios to run\n')
            raise Exception('No scenarios to run')

        ran_scenarios = []
        for scenario_def in self.scenarios:
            scenario = OmniScenario.parse(scenario_def.get('type'))
            if scenario in [OmniScenario.Mulch]:
                continue

            if  self.base_scenario != OmniScenario.Undisturbed and \
                scenario in [OmniScenario.Thinning, OmniScenario.PrescribedFire]:
                # skip undisturbed if the base scenario is sbs_map
                continue

            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            self.log(f'  Omni::run_omni_scenarios: {_scenario_name}\n')
            self._build_scenario(scenario_def)
            ran_scenarios.append(_scenario_name)

        for scenario_def in self.scenarios:
            self.log(f'  Omni::run_omni_scenarios: djskd {scenario_def}\n')
            
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if _scenario_name in ran_scenarios:
                continue

            self.log(f'  Omni::run_omni_scenarios: {_scenario_name}\n')
            self._build_scenario(scenario_def)
            self.log_done()

        self.log('  Omni::run_omni_scenarios: compiling hillslope summaries\n')
        self.compile_hillslope_summaries()
        self.log_done()

    def _build_scenario(
            self,
            scenario_def: dict):
        from wepppy.nodb import Landuse, Soils, Wepp
        from wepppy.nodb.mods import Disturbed
        from wepppy.nodb.mods import Treatments
            
        wd = self.wd
        base_scenario = self.base_scenario

        scenario = OmniScenario.parse(scenario_def.get('type'))
        _scenario = str(scenario)
        omni_base_scenario_name = scenario_def.get('base_scenario', None)

        if scenario in [OmniScenario.PrescribedFire, OmniScenario.Thinning]:  # prescribed fire and thining has to be applied to undisturbed
            if base_scenario != OmniScenario.Undisturbed:  # if the base scenario is SBSmap, we need to clone it from the undisturbed sibling
                omni_base_scenario_name = 'undisturbed'

        # change to working dir of parent weppcloud project
        os.chdir(wd)
        
        # assert we know how to handle the scenario
        assert isinstance(scenario, OmniScenario)
        new_wd = _omni_clone(scenario_def, wd)

        self.log(f'  Omni::_build_scenario: new_wd:{new_wd}\n')

        if omni_base_scenario_name is not None:
            if not omni_base_scenario_name == str(base_scenario):  # base scenario is either sbs_map or undisturbed
                # e.g. scenario is mulch and omni_base_scenario is uniform_low, uniform_moderate, uniform_high, or sbs_map
                self.log(f'  Omni::_build_scenario: _omni_clone_sibling:{omni_base_scenario_name}\n')
                _omni_clone_sibling(new_wd, omni_base_scenario_name)
                
        # get disturbed and landuse instances
        disturbed = Disturbed.getInstance(new_wd)
        landuse = Landuse.getInstance(new_wd)
        soils = Soils.getInstance(new_wd)

        # handle uniform burn severity cases
        if scenario == OmniScenario.UniformLow or \
            scenario == OmniScenario.UniformModerate or \
            scenario == OmniScenario.UniformHigh:

            self.log(f'  Omni::_build_scenario: uniform burn severity\n')

            # identify burn class
            sbs = None
            if scenario == OmniScenario.UniformLow:
                sbs = 1
            elif scenario == OmniScenario.UniformModerate:
                sbs = 2
            elif scenario == OmniScenario.UniformHigh:
                sbs = 3

            sbs_fn = disturbed.build_uniform_sbs(int(sbs))
            disturbed.validate(sbs_fn)
            landuse.build()
            soils.build()

        elif scenario == OmniScenario.Undisturbed:
            self.log(f'  Omni::_build_scenario: undisturbed\n')

            if not Disturbed.getInstance(wd).has_sbs:
                raise Exception('Undisturbed scenario requires a base scenario with sbs')
            disturbed.remove_sbs()
            landuse.build()
            soils.build()

        elif scenario == OmniScenario.SBSmap:
            self.log(f'  Omni::_build_scenario: sbs\n')

            sbs_file_path = scenario_def.get('sbs_file_path')
            if not _exists(sbs_file_path):
                raise FileNotFoundError(f"'{sbs_file_path}' not found!")
            
            # move from _limbo to new_wd/disturbed and validate
            sbs_fn = _split(sbs_file_path)[-1]
            new_sbs_file_path = _join(disturbed.disturbed_dir, sbs_fn)
            shutil.copyfile(sbs_file_path, new_sbs_file_path)
            os.remove(sbs_file_path)

            disturbed.validate(sbs_fn)
            landuse.build()
            soils.build()

        elif scenario == OmniScenario.Mulch:
            self.log(f'  Omni::_build_scenario: mulch\n')

            assert omni_base_scenario_name is not None, \
                'Mulching scenario requires a base scenario'

            soils.build()

            treatments = Treatments.getInstance(new_wd)

            ground_cover_increase = scenario_def.get('ground_cover_increase')
            treatment_key = treatments.treatments_lookup[f'mulch_{ground_cover_increase}'.replace('%', '')]

            treatments_domlc_d = {}
            for topaz_id, dom in landuse.domlc_d.items():
                if str(topaz_id).endswith('4'):
                    continue

                # treat burned forest, shrub, and grass with mulching by increasing cover
                man_summary = landuse.managements[dom]
                disturbed_class = getattr(man_summary, 'disturbed_class', '')
                if isinstance(disturbed_class, str) and 'fire' in disturbed_class:
                    treatments_domlc_d[topaz_id] = treatment_key

            treatments.treatments_domlc_d = treatments_domlc_d
            treatments.build_treatments()
            
        elif scenario == OmniScenario.PrescribedFire:
            self.log(f'  Omni::_build_scenario: prescribed fire\n')

            # should have cloned undisturbed
            if disturbed.has_sbs:
                raise Exception('Cloned omni scenario should be undisturbed')

            soils.build()
            
            treatments = Treatments.getInstance(new_wd)
            treatment_key = treatments.treatments_lookup[str(scenario)]

            treatments_domlc_d = {}
            for topaz_id, dom in landuse.domlc_d.items():
                if str(topaz_id).endswith('4'):
                    continue

                man_summary = landuse.managements[dom]
                disturbed_class = getattr(man_summary, 'disturbed_class', '')
                if 'forest' in disturbed_class and 'young' not in disturbed_class:
                    treatments_domlc_d[topaz_id] = treatment_key

            treatments.treatments_domlc_d = treatments_domlc_d
            treatments.build_treatments()

        elif scenario == OmniScenario.Thinning:
            self.log(f'  Omni::_build_scenario: thinning\n')

            # should have cloned undisturbed
            if disturbed.has_sbs:
                raise Exception('Cloned omni scenario should be undisturbed')

            soils.build()
            
            treatments = Treatments.getInstance(new_wd)
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            treatment_key = treatments.treatments_lookup[_scenario_name]

            treatments_domlc_d = {}
            for topaz_id, dom in landuse.domlc_d.items():
                if str(topaz_id).endswith('4'):
                    continue
                    
                man_summary = landuse.managements[dom]
                disturbed_class = getattr(man_summary, 'disturbed_class', '')
                if 'forest' in disturbed_class and 'young' not in disturbed_class:
                    treatments_domlc_d[topaz_id] = treatment_key

            treatments.treatments_domlc_d = treatments_domlc_d
            treatments.build_treatments()

        wepp = Wepp.getInstance(new_wd)

        wepp.prep_hillslopes(omni=True)
        wepp.run_hillslopes(omni=True)

        wepp.prep_watershed()
        wepp.run_watershed()

    @property
    def has_ran_scenarios(self):
        if not hasattr(self, 'scenarios'):
            return False

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if not _exists(_join(self.wd, 'omni', 'scenarios', _scenario_name, 'wepp', 'output', 'loss_pw0.out.parquet')):
                return False

        return True

    def scenarios_report(self):
        """
        compiles the loss_pw0.out.parquet across the scenarios
        """

        parquet_files = {str(self.base_scenario): _join(self.wd, 'wepp', 'output', 'loss_pw0.out.parquet')}

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            parquet_files[_scenario_name] = _join(self.wd, 'omni', 'scenarios', _scenario_name, 'wepp', 'output', 'loss_pw0.out.parquet')

        dfs = []
        for scenario, path in parquet_files.items():
            if not os.path.isfile(path):
                continue
            df = pd.read_parquet(path)         # expects columns: key, v, units
            df['scenario'] = str(scenario)
            dfs.append(df)

        if not dfs:
            # nothing to do
            return pd.DataFrame(columns=['key', 'v', 'units', 'scenario'])

        combined = pd.concat(dfs, ignore_index=True)
        out_path = _join(self.wd, 'omni', 'scenarios.out.parquet')
        combined.to_parquet(out_path)

        return combined
    
    def compile_hillslope_summaries(self, exclude_yr_indxs=None):
        from wepppy.nodb import Wepp
        from wepppy.wepp.stats import HillSummary

        scenario_wds = {str(self.base_scenario): self.wd}

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            scenario_wds[_scenario_name] = _join(self.wd, 'omni', 'scenarios', _scenario_name)

        dfs = []
        for scenario, wd in scenario_wds.items():
            loss = Wepp.getInstance(wd).report_loss(exclude_yr_indxs=exclude_yr_indxs)
            is_singlestorm = loss.is_singlestorm
            hill_rpt = HillSummary(loss)
            df = hill_rpt.to_dataframe()  # returns a DataFrame with columns: key, v, units
            df['scenario'] = scenario
            dfs.append(df)

        combined = pd.concat(dfs, ignore_index=True)

        # WeppID,TopazID,Landuse,Soil,Length (m),Hillslope Area (ha),Runoff (mm),Lateral Flow (mm),Baseflow (mm),Soil Loss (kg/ha),Sediment Deposition (kg/ha),Sediment Yield (kg/ha),scenario


        # 1. Convert depths (mm) over area (ha) → volumes in m³:
        #    1 mm over 1 ha = 0.001 m * 10 000 m² = 10 m³
        combined['Runoff (m^3)']       = combined['Runoff (mm)']       * combined['Hillslope Area (ha)'] * 10
        combined['Lateral Flow (m^3)'] = combined['Lateral Flow (mm)'] * combined['Hillslope Area (ha)'] * 10
        combined['Baseflow (m^3)']     = combined['Baseflow (mm)']     * combined['Hillslope Area (ha)'] * 10

        # 2. Convert per‐area masses (kg/ha) over area (ha) → total mass in tonnes:
        #    (kg/ha * ha) gives kg; divide by 1 000 → tonnes
        combined['Soil Loss (t)']             = combined['Soil Loss (kg/ha)']             * combined['Hillslope Area (ha)'] / 1_000
        combined['Sediment Deposition (t)']   = combined['Sediment Deposition (kg/ha)']   * combined['Hillslope Area (ha)'] / 1_000
        combined['Sediment Yield (t)']        = combined['Sediment Yield (kg/ha)']        * combined['Hillslope Area (ha)'] / 1_000

        # Calculate NTU in g/L (combined['Sediment Yield (t)'] * 1_000_000) / (combined['Runoff (m^3)'] * 1_000)
        combined['NTU (g/L)'] = (combined['Sediment Yield (t)'] * 1_000) / combined['Runoff (m^3)']

        out_path = _join(self.wd, 'omni', 'scenarios.hillslope_summaries.parquet')
        combined.to_parquet(out_path)


    def compile_channel_summaries(self, exclude_yr_indxs=None):
        from wepppy.nodb import Wepp
        from wepppy.wepp.stats import ChannelSummary

        scenario_wds = {str(self.base_scenario): self.wd}

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            scenario_wds[_scenario_name] = _join(self.wd, 'omni', 'scenarios', _scenario_name)

        dfs = []
        for scenario, wd in scenario_wds.items():
            loss = Wepp.getInstance(wd).report_loss(exclude_yr_indxs=exclude_yr_indxs)
            is_singlestorm = loss.is_singlestorm
            channel_rpt = ChannelSummary(loss)
            df = channel_rpt.to_dataframe()  # returns a DataFrame with columns: key, v, units
            df['scenario'] = scenario
            dfs.append(df)

        combined = pd.concat(dfs, ignore_index=True)

        # WeppID,TopazID,Landuse,Soil,Length (m),Hillslope Area (ha),Runoff (mm),Lateral Flow (mm),Baseflow (mm),Soil Loss (kg/ha),Sediment Deposition (kg/ha),Sediment Yield (kg/ha),scenario


        out_path = _join(self.wd, 'omni', 'scenarios.channel_summaries.parquet')
        combined.to_parquet(out_path)

# [x] add NTU
# [ ] add NTU for outlet
# [x] revise mulching cover model
# [ ] add peak runoff (50 yr)
# [x] treat low and moderate severity conditions
# [x] rerun https://wepp.cloud/weppcloud/runs/rlew-indecorous-vest/disturbed9002/
# [x] run contrast scenarios


# [ ] ability to run solution scenario for PATH with specified treatments across hillslopes
