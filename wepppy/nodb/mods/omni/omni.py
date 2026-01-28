"""Omni scenario orchestration controller.

The Omni mod manages scenario clones and contrast analyses for WEPPcloud runs.
It snapshots the working directory into `_pups/omni`, applies treatments,
rebuilds WEPP inputs, executes hillslope and watershed runs, and aggregates
loss metrics into DuckDB-backed parquet outputs. Results feed dashboards
(`scenarios.out.parquet`, contrast NDJSON audit logs) and inform follow-on
analytics such as RAP/RHEM summaries.

Inputs:
* Project working directory (climate, watershed, soils, landuse, disturbed data)
* Scenario definitions provided by the UI (uniform burn, thinning, mulch, SBS map)
* Contrast objectives and selection filters coming from Omni forms

Outputs:
* Per-scenario WEPP outputs stored under `_pups/omni/scenarios/*`
* Contrast clones with curated `loss_pw0` datasets
* Combined parquet reports for scenarios, hillslopes, and channels
"""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import os
import hashlib
import time
import logging
import re
from pathlib import Path

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir
from os.path import isfile as _isfile

from csv import DictWriter
from collections import namedtuple

import base64

import pandas as pd
from enum import IntEnum
from copy import deepcopy
from glob import glob
import json
import shutil
from time import sleep

from wepppy.nodb.core import Climate, Ron, Soils, Watershed, Wepp
from wepppy.nodb.core.climate import ClimateMode
from wepppy.nodb.base import (
    NoDbAlreadyLockedError,
    NoDbBase,
    clear_locks,
    clear_nodb_file_cache,
    nodb_setter,
)
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.version import copy_version_for_clone
from wepppy.wepp.interchange import (
    run_wepp_hillslope_interchange,
    run_wepp_watershed_tc_out_interchange,
)
from wepppy.wepp.reports import refresh_return_period_events
from wepppy.rq.topo_utils import _prune_stream_order

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except Exception:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

__all__ = [
    'OMNI_REL_DIR',
    'LOGGER',
    'OmniScenario',
    'OmniNoDbLockedException',
    'Omni',
]

OMNI_REL_DIR = '_pups/omni'

LOGGER = logging.getLogger(__name__)

CoverValues = Dict[str, float]
RhemRunResult = Tuple[bool, str, float]
ScenarioDef = Dict[str, Any]
ScenarioDependency = Dict[str, Dict[str, Any]]
ObjectiveParameter = namedtuple('ObjectiveParameter', ['topaz_id', 'wepp_id', 'value'])


def _update_nodb_wd(d: Dict[str, Any], new_wd: str, parent_wd: Optional[str] = None) -> None:
    """Update wd (and optionally _parent_wd) in nodb JSON, handling both formats.
    
    Old jsonpickle format stores properties at top level.
    New format (with __getstate__) wraps properties in py/state.
    """
    if 'py/state' in d:
        # New format: properties nested in py/state
        d['py/state']['wd'] = new_wd
        if parent_wd is not None:
            d['py/state']['_parent_wd'] = parent_wd
    else:
        # Old format: properties at top level
        d['wd'] = new_wd
        if parent_wd is not None:
            d['_parent_wd'] = parent_wd


ContrastMapping = Dict[int | str, str]
ContrastDependencies = Dict[str, Dict[str, Optional[str]]]
ContrastDependency = Dict[str, Dict[str, Any]]


def _clear_nodb_cache_and_locks(runid: str, pup_relpath: Optional[str] = None) -> None:
    """Best-effort clearing of cached NoDb entries and locks for a run scope."""
    try:
        cleared_entries = clear_nodb_file_cache(runid, pup_relpath=pup_relpath)
        if cleared_entries:
            LOGGER.debug(
                'Cleared %d NoDb cache entries for run %s (scope=%s)',
                len(cleared_entries),
                runid,
                pup_relpath or 'root'
            )
    except RuntimeError as exc:
        if 'Redis NoDb cache client is unavailable' in str(exc):
            LOGGER.debug('Redis NoDb cache unavailable while clearing cache for %s (scope=%s)', runid, pup_relpath)
        else:
            LOGGER.warning('Failed to clear NoDb cache for %s (scope=%s): %s', runid, pup_relpath, exc)
    except Exception as exc:
        LOGGER.warning('Failed to clear NoDb cache for %s (scope=%s): %s', runid, pup_relpath, exc)

    try:
        clear_locks(runid, pup_relpath=pup_relpath)
    except RuntimeError as exc:
        if 'Redis lock client is unavailable' in str(exc):
            LOGGER.debug('Redis lock client unavailable while clearing locks for %s', runid)
        else:
            LOGGER.warning('Failed to clear NoDb locks for %s: %s', runid, exc)
    except Exception as exc:
        LOGGER.warning('Failed to clear NoDb locks for %s: %s', runid, exc)


def _post_watershed_run_cleanup(wepp: Wepp) -> None:
    """Mirror RQ post-run cleanup by moving .out files and copying tc_out.txt."""
    climate = Climate.getInstance(wepp.wd)
    if climate.climate_mode == ClimateMode.SingleStormBatch:
        for batch in climate.ss_batch_storms:
            ss_batch_key = batch["ss_batch_key"]
            wepp.logger.info("    moving .out files...")
            for fn in glob(_join(wepp.runs_dir, "*.out")):
                dst_path = _join(wepp.output_dir, ss_batch_key, _split(fn)[1])
                shutil.move(fn, dst_path)
    else:
        wepp.logger.info("    moving .out files...")
        for fn in glob(_join(wepp.runs_dir, "*.out")):
            dst_path = _join(wepp.output_dir, _split(fn)[1])
            shutil.move(fn, dst_path)

    tc_src = _join(wepp.runs_dir, "tc_out.txt")
    if _exists(tc_src):
        tc_dst = _join(wepp.output_dir, "tc_out.txt")
        wepp.logger.info("    moving tc_out.txt...")
        shutil.move(tc_src, tc_dst)
        if _exists(tc_dst):
            run_wepp_watershed_tc_out_interchange(wepp.output_dir)

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
    def parse(value: int | str | OmniScenario) -> OmniScenario:
        if isinstance(value, OmniScenario):
            return value
        if value == 'uniform_low' or value == OmniScenario.UniformLow.value:
            return OmniScenario.UniformLow
        elif value == 'uniform_moderate' or value == OmniScenario.UniformModerate.value:
            return OmniScenario.UniformModerate
        elif value == 'uniform_high' or value == OmniScenario.UniformHigh.value:
            return OmniScenario.UniformHigh
        elif value == 'thinning' or value == OmniScenario.Thinning.value:
            return OmniScenario.Thinning
        elif value == 'mulch' or value == OmniScenario.Mulch.value:
            return OmniScenario.Mulch
        elif value == 'sbs_map' or value == OmniScenario.SBSmap.value:
            return OmniScenario.SBSmap
        elif value == 'undisturbed' or value == OmniScenario.Undisturbed.value:
            return OmniScenario.Undisturbed
        elif value == 'prescribed_fire' or value == OmniScenario.PrescribedFire.value:
            return OmniScenario.PrescribedFire
        raise KeyError(f"Invalid scenario: {value}")

    def __str__(self) -> str:
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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OmniScenario):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        if isinstance(other, str):
            return self.value == OmniScenario.parse(other).value
        return False
    

def _resolve_base_scenario_key(wd: str) -> str:
    from wepppy.nodb.mods.disturbed import Disturbed

    disturbed = Disturbed.getInstance(wd)
    if disturbed.has_sbs:
        return str(OmniScenario.SBSmap)
    return str(OmniScenario.Undisturbed)


def _resolve_contrast_scenario_wd(wd: str, scenario_key: str, base_key: str) -> str:
    if scenario_key == base_key:
        return wd
    scenario_dir = _join(wd, OMNI_REL_DIR, "scenarios", scenario_key)
    if not _exists(scenario_dir):
        raise FileNotFoundError(f"Scenario directory missing for {scenario_key}: {scenario_dir}")
    return scenario_dir


def _contrast_topaz_ids_from_mapping(
    contrasts: Dict[int | str, str],
    contrast_wd: str,
) -> Set[int]:
    contrast_output_dir = os.path.normpath(_join(contrast_wd, "wepp", "output"))
    prefix = contrast_output_dir + os.sep
    contrast_topaz_ids: Set[int] = set()
    for topaz_id, wepp_id_path in contrasts.items():
        if not isinstance(wepp_id_path, str):
            continue
        normalized_path = os.path.normpath(wepp_id_path)
        if normalized_path == contrast_output_dir or normalized_path.startswith(prefix):
            try:
                contrast_topaz_ids.add(int(topaz_id))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid topaz id in contrast mapping: {topaz_id}") from exc
    return contrast_topaz_ids


def _merge_contrast_parquet(
    *,
    control_parquet_fn: str,
    contrast_parquet_fn: str,
    output_parquet_fn: str,
    contrast_topaz_ids: Set[int],
    label: str,
) -> None:
    if not _exists(control_parquet_fn):
        raise FileNotFoundError(f"Missing control parquet for {label}: {control_parquet_fn}")
    if not _exists(contrast_parquet_fn):
        raise FileNotFoundError(f"Missing contrast parquet for {label}: {contrast_parquet_fn}")

    if not contrast_topaz_ids:
        shutil.copyfile(control_parquet_fn, output_parquet_fn)
        return

    control_df = pd.read_parquet(control_parquet_fn)
    contrast_df = pd.read_parquet(contrast_parquet_fn)

    if "topaz_id" not in control_df.columns or "topaz_id" not in contrast_df.columns:
        raise ValueError(f"{label} parquet must include topaz_id column.")

    control_topaz = pd.to_numeric(control_df["topaz_id"], errors="coerce")
    contrast_topaz = pd.to_numeric(contrast_df["topaz_id"], errors="coerce")
    available_contrast_ids = set(contrast_topaz.dropna().astype(int).tolist())
    missing = contrast_topaz_ids - available_contrast_ids
    if missing:
        missing_list = ", ".join(str(value) for value in sorted(missing))
        raise ValueError(f"{label} contrast parquet is missing topaz ids: {missing_list}")

    control_mask = control_topaz.isin(contrast_topaz_ids)
    contrast_mask = contrast_topaz.isin(contrast_topaz_ids)
    merged = pd.concat(
        [control_df[~control_mask], contrast_df[contrast_mask]],
        ignore_index=True,
    )
    merged.to_parquet(output_parquet_fn, index=False)


def _run_contrast(
    contrast_id: str,
    contrast_name: str,
    contrasts: Dict[int | str, str],
    wd: str,
    runid: str,
    control_scenario_key: str,
    contrast_scenario_key: str,
    wepp_bin: str = 'wepp_a557997'
) -> str:
    from wepppy.nodb.core import Landuse, Soils, Wepp
    global OMNI_REL_DIR

    new_wd = _join(wd, OMNI_REL_DIR, 'contrasts', contrast_id)
    pup_relpath = os.path.relpath(new_wd, wd)

    if _exists(new_wd):
        shutil.rmtree(new_wd)
        _clear_nodb_cache_and_locks(runid, pup_relpath)

    os.makedirs(new_wd)
    copy_version_for_clone(wd, new_wd)

    os.makedirs(_join(new_wd, 'soils'), exist_ok=True)
    os.makedirs(_join(new_wd, 'landuse'), exist_ok=True)

    symlink_entries = {
        'climate',
        'watershed',
        'climate.nodb',
        'watershed.nodb',
        'landuse.nodb',
        'soils.nodb',
        'unitizer.nodb',
        'treatments.nodb',
    }
    symlink_nodb_files = {entry for entry in symlink_entries if entry.endswith('.nodb')}

    for fn in os.listdir(wd):
        if fn in symlink_entries:
            src = _join(wd, fn)
            dst = _join(new_wd, fn)
            if not _exists(dst):
                os.symlink(src, dst)

    for nodb_fn in os.listdir(wd):
        if not nodb_fn.endswith('.nodb'):
            continue
        if nodb_fn in symlink_nodb_files:
            continue
        src = _join(wd, nodb_fn)
        if not _isfile(src):
            continue
        dst = _join(new_wd, nodb_fn)
        if not _exists(dst):
            shutil.copy(src, dst)

        with open(dst, 'r') as f:
            d = json.load(f)

        _update_nodb_wd(d, new_wd, parent_wd=wd)

        with open(dst, 'w') as fp:
            json.dump(d, fp)
            fp.flush()                 # flush Python’s userspace buffer
            os.fsync(fp.fileno())      # fsync forces kernel page-cache to disk

    wepp = Wepp.getInstance(new_wd)
    wepp.wepp_bin = wepp_bin
    wepp.clean()  # this creates the directories in the {omni_dir}/wepp

    # symlink the other wepp watershed input files
    og_runs_dir = _join(wd, 'wepp', 'runs/')
    omni_runs_dir = _join(new_wd, 'wepp', 'runs/')
    for fn in os.listdir(og_runs_dir):
        _fn = _split(fn)[-1]
        if _fn in ('pw0.run', 'pw0.err'):
            continue
        src = _join(og_runs_dir, fn)
        if not _isfile(src):
            continue
        dst = _join(omni_runs_dir, fn)
        if not _exists(dst):
            os.symlink(src, dst)

    old_prefix = _join(wd, 'omni')
    new_prefix = _join(wd, OMNI_REL_DIR)
    normalized_contrasts: Dict[int | str, str] = {}
    for topaz_id, wepp_id_path in contrasts.items():
        normalized_path = wepp_id_path
        if isinstance(wepp_id_path, str) and wepp_id_path.startswith(old_prefix):
            candidate = new_prefix + wepp_id_path[len(old_prefix):]
            if _exists(f"{candidate}.pass.dat"):
                LOGGER.info('Updating contrast path %s -> %s', wepp_id_path, candidate)
                normalized_path = candidate
        normalized_contrasts[topaz_id] = normalized_path

    base_key = _resolve_base_scenario_key(wd)
    control_wd = _resolve_contrast_scenario_wd(wd, control_scenario_key, base_key)
    contrast_wd = _resolve_contrast_scenario_wd(wd, contrast_scenario_key, base_key)
    contrast_topaz_ids = _contrast_topaz_ids_from_mapping(normalized_contrasts, contrast_wd)
    if not contrast_topaz_ids and control_scenario_key != contrast_scenario_key:
        raise ValueError(f"No contrast hillslopes detected for {contrast_name}.")

    _merge_contrast_parquet(
        control_parquet_fn=_join(control_wd, "landuse", "landuse.parquet"),
        contrast_parquet_fn=_join(contrast_wd, "landuse", "landuse.parquet"),
        output_parquet_fn=_join(new_wd, "landuse", "landuse.parquet"),
        contrast_topaz_ids=contrast_topaz_ids,
        label="landuse",
    )
    _merge_contrast_parquet(
        control_parquet_fn=_join(control_wd, "soils", "soils.parquet"),
        contrast_parquet_fn=_join(contrast_wd, "soils", "soils.parquet"),
        output_parquet_fn=_join(new_wd, "soils", "soils.parquet"),
        contrast_topaz_ids=contrast_topaz_ids,
        label="soils",
    )

    wepp.make_watershed_run(wepp_id_paths=list(normalized_contrasts.values()))
    wepp.run_watershed()
    _post_watershed_run_cleanup(wepp)
    wepp.report_loss()

    return new_wd


def _omni_clone(scenario_def: Dict[str, Any], wd: str, runid: str) -> str:
    global OMNI_REL_DIR
    
    scenario = scenario_def.get('type')
    _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
    new_wd = _join(wd, OMNI_REL_DIR, 'scenarios', _scenario_name)
    pup_relpath = os.path.relpath(new_wd, wd)

    if _exists(new_wd):
        shutil.rmtree(new_wd)
        # clear cached NoDb payloads and locks for the previous scenario clone
        _clear_nodb_cache_and_locks(runid, pup_relpath)


    os.makedirs(new_wd)

    for fn in os.listdir(wd):
        if fn in ['climate', 'dem', 'watershed', 'climate.nodb', 'dem.nodb', 'watershed.nodb']:
            src = _join(wd, fn)
            dst = _join(new_wd, fn)
            if not _exists(dst):
                os.symlink(src, dst)

        elif fn in ['disturbed', 'soils', 'rap']:
            src = _join(wd, fn)
            dst = _join(new_wd, fn)
            if not _exists(dst):
                shutil.copytree(src, dst)

        elif fn.endswith('.nodb'):
            if fn == 'omni.nodb':
                continue

            src = _join(wd, fn)
            dst = _join(new_wd, fn)
            if not _exists(dst):
                shutil.copy(src, dst)

            with open(dst, 'r') as f:
                d = json.load(f)
                
            _update_nodb_wd(d, new_wd, parent_wd=wd)

            with open(dst, 'w') as fp:
                json.dump(d, fp)
                fp.flush()                 # flush Python’s userspace buffer
                os.fsync(fp.fileno())      # fsync forces kernel page-cache to disk
    
    for fn in os.listdir(wd):
        if fn == '_pups':
            continue

        src = _join(wd, fn)
        if os.path.isdir(src):
            dst = _join(new_wd, fn)

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


    # remove READONLY file flag if present
    if _exists(_join(new_wd, 'READONLY')):
        os.remove(_join(new_wd, 'READONLY'))

    return new_wd


def _omni_clone_sibling(new_wd: str, omni_clone_sibling_name: str, runid: str, parent_wd: str) -> None:
    """
    after _omni_clone copies watershed, climates, wepp from the base_scenario (parent)

    we copy the sibling scenario's disturbed, landuse, and soils so that managements/treatments
    are applied to the correct scenario.
    """
    
    sibling_wd = _join(new_wd, '..', omni_clone_sibling_name)
    if not _exists(sibling_wd):
        raise FileNotFoundError(f"'{sibling_wd}' not found!")

    pup_relpath = os.path.relpath(new_wd, parent_wd)

    copy_version_for_clone(sibling_wd, new_wd)
    
    # replace disturbed, landuse, and soils
    os.remove(_join(new_wd, 'disturbed.nodb'))
    os.remove(_join(new_wd, 'landuse.nodb'))
    os.remove(_join(new_wd, 'soils.nodb'))

    # clear cached NoDb payloads and locks after removing the existing nodb files
    _clear_nodb_cache_and_locks(runid, pup_relpath)

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

    # set wd to new_wd for the nodb files that are copied
    for fn in ['disturbed.nodb', 'landuse.nodb', 'soils.nodb']:
        dst = _join(new_wd, fn)
        with open(dst, 'r') as f:
            d = json.load(f)
            
        _update_nodb_wd(d, new_wd)

        with open(dst, 'w') as fp:
            json.dump(d, fp)
            fp.flush()                 # flush Python’s userspace buffer
            os.fsync(fp.fileno())      # fsync forces kernel page-cache to disk

    # remove READONLY file flag if present
    if _exists(_join(new_wd, 'READONLY')):
        os.remove(_join(new_wd, 'READONLY'))


def _scenario_name_from_scenario_definition(scenario_def: Dict[str, Any]) -> str:
    """
    Get the scenario name from the scenario definition.
    :param scenario_def: The scenario definition.
    :return: The scenario name.
    """
    _scenario = scenario_def.get('type')
    scenario_enum: Optional[OmniScenario]
    try:
        scenario_enum = OmniScenario.parse(_scenario) if _scenario is not None else None
    except Exception:
        scenario_enum = None

    if scenario_enum == OmniScenario.Thinning:
        canopy_cover = scenario_def.get('canopy_cover')
        ground_cover = scenario_def.get('ground_cover')
        return f'{scenario_enum}_{canopy_cover}_{ground_cover}'.replace('%', '')
    elif scenario_enum == OmniScenario.Mulch:
        ground_cover_increase = scenario_def.get('ground_cover_increase')
        base_scenario = scenario_def.get('base_scenario')
        return f'{scenario_enum}_{ground_cover_increase}_{base_scenario}'.replace('%', '')
    elif scenario_enum == OmniScenario.SBSmap:
        sbs_file_path = scenario_def.get('sbs_file_path', None)
        if sbs_file_path is not None:
            sbs_fn = _split(sbs_file_path)[-1]
            sbs_hash = base64.b64encode(bytes(sbs_fn, 'utf-8')).decode('utf-8').rstrip('=')
            return f'{scenario_enum}_{sbs_hash}'
        return f'{scenario_enum}'
    else:
        return str(scenario_enum or _scenario)


def _hash_file_sha1(path: Optional[str]) -> Optional[str]:
    if not path or not _exists(path):
        return None

    h = hashlib.sha1()
    try:
        with open(path, 'rb') as fp:
            for chunk in iter(lambda: fp.read(8192), b''):
                h.update(chunk)
    except (OSError, IOError):
        return None
    return h.hexdigest()


class OmniNoDbLockedException(Exception):
    pass


class Omni(NoDbBase):
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
            - compile_hillslope_summaries(): build and save detailed
                hillslope summaries across base and all parsed scenarios
    Public Attributes (stored in omni.nodb):
        - wd: working directory for WEPP inputs/outputs
        - _scenarios: list of scenario definition dicts
        - _contrast_names: list of contrast identifiers aligned to feature order (sidecar mappings live under omni/contrasts)
        - _contrast_labels: optional mapping of contrast_id → display label for reports
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
    __name__ = 'Omni'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    filename = 'omni.nodb'

    def __init__(self, wd, cfg_fn='0.cfg', run_group=None, group_name=None):
        super(Omni, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            if not _exists(self.omni_dir):
                os.makedirs(self.omni_dir)

            self._scenarios = []
            self._contrasts = None
            self._contrast_names = None
            self._contrast_labels = None

            self._contrast_scenario = None
            self._control_scenario = None
            self._contrast_object_param = None
            self._contrast_cumulative_obj_param_threshold_fraction = None
            self._contrast_hillslope_limit = None
            self._contrast_hill_min_slope = None
            self._contrast_hill_max_slope = None
            self._contrast_select_burn_severities = None
            self._contrast_select_topaz_ids = None
            self._contrast_selection_mode = None
            self._contrast_geojson_path = None
            self._contrast_geojson_name_key = None
            self._contrast_hillslope_groups = None
            self._contrast_order_reduction_passes = None
            self._contrast_pairs = []

            self._scenario_dependency_tree = {}
            self._contrast_dependency_tree = {}
            self._scenario_run_state = []

    def __getstate__(self) -> dict[str, Any]:
        state = super().__getstate__()
        state.pop('_contrasts', None)
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self.__dict__.pop('_contrasts', None)

    def _refresh_catalog(self, rel_path: Optional[str] = None) -> None:
        """Best-effort catalog refresh for Omni artifacts."""
        if _update_catalog_entry is None:
            return
        target = rel_path or OMNI_REL_DIR
        try:
            _update_catalog_entry(self.wd, target)
        except Exception:  # pragma: no cover - catalog refresh best effort
            LOGGER.warning(
                "Failed to refresh catalog for Omni artifacts in %s (target=%s)",
                self.wd,
                target,
                exc_info=True,
            )

    @property
    def scenarios(self) -> List[Dict[str, Any]]:
        return getattr(self, '_scenarios', []) or []
    
    @scenarios.setter
    @nodb_setter
    def scenarios(self, value: List[Dict[str, Any]]) -> None:
        self._scenarios = value

    @property
    def scenario_dependency_tree(self) -> ScenarioDependency:
        return getattr(self, '_scenario_dependency_tree', {}) or {}

    @scenario_dependency_tree.setter
    @nodb_setter
    def scenario_dependency_tree(self, value: ScenarioDependency) -> None:
        self._scenario_dependency_tree = value

    @property
    def scenario_run_state(self) -> List[Dict[str, Any]]:
        return getattr(self, '_scenario_run_state', []) or []

    @scenario_run_state.setter
    @nodb_setter
    def scenario_run_state(self, value: List[Dict[str, Any]]) -> None:
        self._scenario_run_state = value

    def parse_scenarios(self, parsed_inputs: Iterable[Tuple[OmniScenario, ScenarioDef]]) -> None:
        """
        Parse the scenarios and their parameters into the NoDb structure.
        :param parsed_inputs: List of (scenario_enum, params) tuples
        """
        with self.locked():
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

    def delete_scenarios(self, scenario_names: Iterable[str]) -> Dict[str, List[str]]:
        """
        Remove scenarios by name, deleting their clones and pruning cached summaries.
        """
        names = [str(name) for name in scenario_names if str(name).strip()]
        # Preserve order and deduplicate
        target_names: List[str] = list(dict.fromkeys(names))
        if not target_names:
            return {'removed': [], 'missing': []}

        removed: List[str] = []
        missing: List[str] = []

        existing_defs = list(self.scenarios)
        kept_defs: List[Dict[str, Any]] = []
        existing_names: Set[str] = set()

        for scenario_def in existing_defs:
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            existing_names.add(scenario_name)
            if scenario_name in target_names:
                removed.append(scenario_name)
            else:
                kept_defs.append(scenario_def)

        missing.extend([name for name in target_names if name not in existing_names])
        self.scenarios = kept_defs

        kept_names = {_scenario_name_from_scenario_definition(defn) for defn in kept_defs}

        dependency_tree = dict(self.scenario_dependency_tree)
        for key in list(dependency_tree.keys()):
            if key not in kept_names:
                dependency_tree.pop(key, None)
        self.scenario_dependency_tree = dependency_tree

        run_state = [
            state for state in (self.scenario_run_state or [])
            if state.get('scenario') in kept_names
        ]
        self.scenario_run_state = run_state

        for name in target_names:
            scenario_dir = _join(self.wd, OMNI_REL_DIR, 'scenarios', name)
            if _exists(scenario_dir):
                try:
                    shutil.rmtree(scenario_dir)
                    pup_relpath = os.path.relpath(scenario_dir, self.wd)
                    _clear_nodb_cache_and_locks(self.runid, pup_relpath)
                except Exception as exc:
                    self.logger.debug('Failed to remove scenario directory %s: %s', scenario_dir, exc)
                if name not in removed:
                    removed.append(name)
            elif name not in removed:
                missing.append(name)

        aggregated = _join(self.omni_dir, 'scenarios.out.parquet')
        if _exists(aggregated):
            try:
                os.remove(aggregated)
            except Exception as exc:
                self.logger.debug('Failed to remove aggregated scenario summary %s: %s', aggregated, exc)

        self._refresh_catalog(OMNI_REL_DIR)
        return {'removed': removed, 'missing': missing}

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        """
        this is called from the web backend to set the parameters in the nodb
        """
        def normalize_scenario_value(value: Any) -> Optional[str]:
            if value is None:
                return None
            if isinstance(value, OmniScenario):
                return str(value)
            if isinstance(value, int):
                try:
                    return str(OmniScenario(value))
                except ValueError:
                    return str(value)
            return str(value)

        with self.locked():
            control_scenario = kwds.get('omni_control_scenario', None)
            if control_scenario is not None:
                self._control_scenario = normalize_scenario_value(control_scenario)

            contrast_scenario = kwds.get('omni_contrast_scenario', None)
            if contrast_scenario is not None:
                self._contrast_scenario = normalize_scenario_value(contrast_scenario)

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

            hill_max_slope = kwds.get('omni_contrast_hill_max_slope', None)
            if hill_max_slope is not None:
                self._contrast_hill_max_slope = hill_max_slope
                
            select_burn_severities = kwds.get('omni_contrast_select_burn_severities', None)
            if select_burn_severities is not None:
                self._contrast_select_burn_severities = select_burn_severities
            
            select_topaz_ids = kwds.get('omni_contrast_select_topaz_ids', None)
            if select_topaz_ids is not None:
                self._contrast_select_topaz_ids = select_topaz_ids

            contrast_selection_mode = kwds.get('omni_contrast_selection_mode', None)
            if contrast_selection_mode is not None:
                self._contrast_selection_mode = str(contrast_selection_mode)

            contrast_geojson_path = kwds.get('omni_contrast_geojson_path', None)
            if contrast_geojson_path is not None:
                self._contrast_geojson_path = str(contrast_geojson_path)

            contrast_geojson_name_key = kwds.get('omni_contrast_geojson_name_key', None)
            if contrast_geojson_name_key is not None:
                self._contrast_geojson_name_key = str(contrast_geojson_name_key)

            contrast_hillslope_groups = kwds.get("omni_contrast_hillslope_groups", None)
            if contrast_hillslope_groups is not None:
                self._contrast_hillslope_groups = contrast_hillslope_groups

            order_reduction_passes = kwds.get('order_reduction_passes', None)
            if order_reduction_passes is not None:
                self._contrast_order_reduction_passes = order_reduction_passes

            contrast_pairs = kwds.get("omni_contrast_pairs", None)
            if contrast_pairs is None:
                contrast_pairs = kwds.get("contrast_pairs", None)
            if contrast_pairs is not None:
                self._contrast_pairs = self._normalize_contrast_pairs(contrast_pairs)

    def _normalize_contrast_pairs(self, value: Any) -> List[Dict[str, str]]:
        if value in (None, ""):
            return []
        if isinstance(value, dict):
            candidates = [value]
        elif isinstance(value, (list, tuple)):
            candidates = list(value)
        else:
            return []

        normalized: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            control_raw = entry.get("control_scenario")
            contrast_raw = entry.get("contrast_scenario")
            if control_raw in (None, "") or contrast_raw in (None, ""):
                continue
            control_key = self._normalize_scenario_key(control_raw)
            contrast_key = self._normalize_scenario_key(contrast_raw)
            pair_key = f"{control_key}::{contrast_key}"
            if pair_key in seen:
                continue
            normalized.append(
                {
                    "control_scenario": control_key,
                    "contrast_scenario": contrast_key,
                }
            )
            seen.add(pair_key)
        return normalized

    @property
    def contrasts(self) -> Optional[List[ContrastMapping]]:
        contrasts = getattr(self, '_contrasts', None)
        if contrasts is not None:
            return contrasts
        contrast_names = self.contrast_names or []
        if not contrast_names:
            return None
        loaded: List[ContrastMapping] = []
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            if not contrast_name:
                continue
            try:
                loaded.append(self._load_contrast_sidecar(contrast_id))
            except FileNotFoundError:
                self.logger.info(
                    "Contrast sidecar missing for contrast_id=%s; skipping load.",
                    contrast_id,
                )
                continue
        self._contrasts = loaded
        return loaded
    
    @contrasts.setter
    @nodb_setter
    def contrasts(self, value: Optional[List[ContrastMapping]]) -> None:
        self._contrasts = value

    @property
    def contrast_names(self) -> Optional[List[Optional[str]]]:
        return getattr(self, '_contrast_names', None)

    @contrast_names.setter
    @nodb_setter
    def contrast_names(self, value: Optional[List[Optional[str]]]) -> None:
        self._contrast_names = value

    @property
    def contrast_dependency_tree(self) -> ContrastDependency:
        return getattr(self, '_contrast_dependency_tree', {}) or {}

    @contrast_dependency_tree.setter
    @nodb_setter
    def contrast_dependency_tree(self, value: ContrastDependency) -> None:
        self._contrast_dependency_tree = value

    @property
    def control_scenario(self) -> Optional[str]:
        return getattr(self, '_control_scenario', None)

    @control_scenario.setter
    @nodb_setter
    def control_scenario(self, value: Optional[str]) -> None:
        self._control_scenario = value

    @property
    def contrast_scenario(self) -> Optional[str]:
        return getattr(self, '_contrast_scenario', None)

    @contrast_scenario.setter
    @nodb_setter
    def contrast_scenario(self, value: Optional[str]) -> None:
        self._contrast_scenario = value

    @property
    def contrast_object_param(self) -> Optional[str]:
        return getattr(self, '_contrast_object_param', None)

    @contrast_object_param.setter
    @nodb_setter
    def contrast_object_param(self, value: Optional[str]) -> None:
        self._contrast_object_param = value

    @property
    def contrast_cumulative_obj_param_threshold_fraction(self) -> Optional[float]:
        return getattr(self, '_contrast_cumulative_obj_param_threshold_fraction', None)

    @contrast_cumulative_obj_param_threshold_fraction.setter
    @nodb_setter
    def contrast_cumulative_obj_param_threshold_fraction(self, value: Optional[float]) -> None:
        self._contrast_cumulative_obj_param_threshold_fraction = value

    @property
    def contrast_hillslope_limit(self) -> Optional[int]:
        return getattr(self, '_contrast_hillslope_limit', None)

    @contrast_hillslope_limit.setter
    @nodb_setter
    def contrast_hillslope_limit(self, value: Optional[int]) -> None:
        self._contrast_hillslope_limit = value

    @property
    def contrast_hill_min_slope(self) -> Optional[float]:
        return getattr(self, '_contrast_hill_min_slope', None)

    @contrast_hill_min_slope.setter
    @nodb_setter
    def contrast_hill_min_slope(self, value: Optional[float]) -> None:
        self._contrast_hill_min_slope = value

    @property
    def contrast_hill_max_slope(self) -> Optional[float]:
        return getattr(self, '_contrast_hill_max_slope', None)

    @contrast_hill_max_slope.setter
    @nodb_setter
    def contrast_hill_max_slope(self, value: Optional[float]) -> None:
        self._contrast_hill_max_slope = value

    @property
    def contrast_select_burn_severities(self) -> Optional[List[int]]:
        return getattr(self, '_contrast_select_burn_severities', None)

    @contrast_select_burn_severities.setter
    @nodb_setter
    def contrast_select_burn_severities(self, value: Optional[List[int]]) -> None:
        self._contrast_select_burn_severities = value

    @property
    def contrast_select_topaz_ids(self) -> Optional[List[int]]:
        return getattr(self, '_contrast_select_topaz_ids', None)

    @contrast_select_topaz_ids.setter
    @nodb_setter
    def contrast_select_topaz_ids(self, value: Optional[List[int]]) -> None:
        self._contrast_select_topaz_ids = value

    @property
    def contrast_selection_mode(self) -> Optional[str]:
        return getattr(self, '_contrast_selection_mode', None)

    @contrast_selection_mode.setter
    @nodb_setter
    def contrast_selection_mode(self, value: Optional[str]) -> None:
        self._contrast_selection_mode = value

    @property
    def contrast_geojson_path(self) -> Optional[str]:
        return getattr(self, '_contrast_geojson_path', None)

    @contrast_geojson_path.setter
    @nodb_setter
    def contrast_geojson_path(self, value: Optional[str]) -> None:
        self._contrast_geojson_path = value

    @property
    def contrast_geojson_name_key(self) -> Optional[str]:
        return getattr(self, '_contrast_geojson_name_key', None)

    @contrast_geojson_name_key.setter
    @nodb_setter
    def contrast_geojson_name_key(self, value: Optional[str]) -> None:
        self._contrast_geojson_name_key = value

    @property
    def contrast_hillslope_groups(self) -> Optional[str]:
        return getattr(self, "_contrast_hillslope_groups", None)

    @contrast_hillslope_groups.setter
    @nodb_setter
    def contrast_hillslope_groups(self, value: Optional[str]) -> None:
        self._contrast_hillslope_groups = value

    @property
    def contrast_order_reduction_passes(self) -> Optional[int]:
        return getattr(self, '_contrast_order_reduction_passes', None)

    @contrast_order_reduction_passes.setter
    @nodb_setter
    def contrast_order_reduction_passes(self, value: Optional[int]) -> None:
        self._contrast_order_reduction_passes = value

    @property
    def contrast_pairs(self) -> List[Dict[str, str]]:
        return getattr(self, "_contrast_pairs", []) or []

    @contrast_pairs.setter
    @nodb_setter
    def contrast_pairs(self, value: List[Dict[str, str]]) -> None:
        self._contrast_pairs = value

    @property
    def omni_dir(self) -> str:
        # `wd/omni` contains the aggregated .parquet outputs and _limbo
        # `_pups/omni` contains the scenario clones and contrasts to make _pups generic to all projects
        # AGENTS: don't mess with this structure without checking with roger
        return _join(self.wd, 'omni')
    
    def get_objective_parameter_from_gpkg(self, objective_parameter: str, scenario: Optional[str] = None) -> Tuple[List[Any], float]:
        """Return objective parameter ranking using interchange loss_pw0.hill.parquet."""
        global OMNI_REL_DIR
        scenario_suffix = None if scenario in (None, '', 'None') else str(scenario)

        if scenario_suffix is None:
            hill_fn = _join(self.wd, 'wepp', 'output', 'interchange', 'loss_pw0.hill.parquet')
        else:
            hill_fn = _join(
                self.wd,
                OMNI_REL_DIR,
                'scenarios',
                scenario_suffix,
                'wepp',
                'output',
                'interchange',
                'loss_pw0.hill.parquet',
            )

        if not _exists(hill_fn):
            raise FileNotFoundError(f"Interchange hillslope summary not found: {hill_fn}")

        param_key = str(objective_parameter).strip()
        param_lookup = {
            'soil_loss_kg': {'column': 'Soil Loss', 'mode': 'scalar'},
            'runoff_volume_m3': {'column': 'Runoff Volume', 'mode': 'scalar'},
            'subrunoff_volume_m3': {'column': 'Subrunoff Volume', 'mode': 'scalar'},
            'runoff_mm': {'column': 'Runoff Volume', 'mode': 'depth'},
            'subrunoff_mm': {'column': 'Subrunoff Volume', 'mode': 'depth'},
            'total_phosphorus_kg': {'column': 'Total Pollutant', 'mode': 'scalar'},
        }
        param_spec = param_lookup.get(param_key.lower())
        if not param_spec:
            raise ValueError(f"Invalid objective parameter: {objective_parameter}")

        df = pd.read_parquet(hill_fn)

        if 'Type' in df.columns:
            df = df[df['Type'].astype(str).str.lower() == 'hill']

        if 'wepp_id' not in df.columns:
            raise ValueError(f"Interchange hillslope summary missing wepp_id: {hill_fn}")

        column = param_spec['column']
        if column not in df.columns:
            raise ValueError(f"Interchange hillslope summary missing column '{column}': {hill_fn}")

        values = pd.to_numeric(df[column], errors='coerce')
        if param_spec['mode'] == 'depth':
            if 'Hillslope Area' not in df.columns:
                raise ValueError(f"Interchange hillslope summary missing Hillslope Area: {hill_fn}")
            area_ha = pd.to_numeric(df['Hillslope Area'], errors='coerce')
            area_m2 = area_ha * 10000.0
            values = values / area_m2 * 1000.0

        df = df.assign(_objective_value=values)
        df = df[df['_objective_value'].notna() & (df['_objective_value'] > 0.0)]

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        top2wepp = {
            k: v
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith('4') or int(k) == 0)
        }
        wepp2topaz = {str(v): str(k) for k, v in top2wepp.items()}

        records: List[ObjectiveParameter] = []
        for _, row in df.iterrows():
            wepp_id = str(row['wepp_id'])
            topaz_id = wepp2topaz.get(wepp_id)
            if topaz_id is None:
                continue
            records.append(ObjectiveParameter(topaz_id, wepp_id, float(row['_objective_value'])))

        records.sort(key=lambda item: item.value, reverse=True)
        total_value = float(sum(item.value for item in records))
        return records, total_value
    
    def clear_contrasts(self) -> None:
        with self.locked():
            self._contrasts = None
            self._contrast_names = None
            self._contrast_labels = None
            self._contrast_dependency_tree = {}
            self._contrast_pairs = []
        self._clean_contrast_runs()
        sidecar_dir = _join(self.omni_dir, 'contrasts')
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        report_path = self._contrast_build_report_path()
        if _exists(report_path):
            try:
                os.remove(report_path)
            except Exception as exc:
                self.logger.debug('Failed to remove contrast build report %s: %s', report_path, exc)
        contrasts_report = _join(self.omni_dir, 'contrasts.out.parquet')
        if _exists(contrasts_report):
            try:
                os.remove(contrasts_report)
            except Exception as exc:
                self.logger.debug('Failed to remove contrast summary %s: %s', contrasts_report, exc)

    def _clean_contrast_runs(self) -> None:
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        if not _exists(contrasts_dir):
            return
        for entry in os.listdir(contrasts_dir):
            if entry == '_uploads':
                continue
            path = _join(contrasts_dir, entry)
            if os.path.isdir(path):
                shutil.rmtree(path)

    def _clean_stale_contrast_runs(self, active_ids: Iterable[int]) -> None:
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        if not _exists(contrasts_dir):
            return
        active = {str(contrast_id) for contrast_id in active_ids}
        for entry in os.listdir(contrasts_dir):
            if entry == '_uploads':
                continue
            path = _join(contrasts_dir, entry)
            if os.path.isdir(path) and entry not in active:
                shutil.rmtree(path)

    def _clean_contrast_run(self, contrast_id: int) -> None:
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        path = _join(contrasts_dir, str(contrast_id))
        if isdir(path):
            shutil.rmtree(path)

    def _contrast_sidecar_dir(self) -> str:
        return _join(self.omni_dir, 'contrasts')

    def _contrast_sidecar_path(self, contrast_id: int) -> str:
        return _join(self._contrast_sidecar_dir(), f'contrast_{contrast_id:05d}.tsv')

    def _contrast_build_report_path(self) -> str:
        return _join(self.wd, OMNI_REL_DIR, 'contrasts', 'build_report.ndjson')

    def _contrast_ids_geojson_path(self) -> str:
        return _join(self.omni_dir, "contrasts", "contrast_ids.wgs.geojson")

    def _load_contrast_build_report(self) -> List[Dict[str, Any]]:
        report_path = self._contrast_build_report_path()
        if not _exists(report_path):
            return []
        entries: List[Dict[str, Any]] = []
        with open(report_path, 'r', encoding='utf-8') as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    entries.append(payload)
        return entries

    def _load_contrast_sidecar(self, contrast_id: int) -> ContrastMapping:
        sidecar_fn = self._contrast_sidecar_path(contrast_id)
        if not _exists(sidecar_fn):
            raise FileNotFoundError(f'Contrast sidecar missing: {sidecar_fn}')
        contrast: ContrastMapping = {}
        with open(sidecar_fn, 'r', encoding='ascii') as fp:
            for line in fp:
                line = line.rstrip('\n')
                if not line:
                    continue
                topaz_id, sep, wepp_id_path = line.partition('\t')
                if not sep:
                    continue
                contrast[topaz_id] = wepp_id_path
        return contrast

    def _write_contrast_sidecar(self, contrast_id: int, contrast: ContrastMapping) -> str:
        sidecar_dir = self._contrast_sidecar_dir()
        os.makedirs(sidecar_dir, exist_ok=True)
        sidecar_fn = self._contrast_sidecar_path(contrast_id)
        with open(sidecar_fn, 'w', encoding='ascii', newline='\n') as fp:
            for topaz_id, wepp_id_path in contrast.items():
                fp.write(f'{topaz_id}\t{wepp_id_path}\n')
        return sidecar_fn

    def _contrast_run_readme_path(self, contrast_id: int) -> str:
        return _join(
            self.wd,
            OMNI_REL_DIR,
            'contrasts',
            str(contrast_id),
            'wepp',
            'output',
            'interchange',
            'README.md',
        )

    def _normalize_landuse_key(self, value: Any) -> Optional[str]:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                return str(value)
            if numeric_value.is_integer():
                return str(int(numeric_value))
        return str(value)

    def _load_landuse_key_map(self, landuse_wd: str) -> Optional[Dict[int, Optional[str]]]:
        parquet_fn = _join(landuse_wd, "landuse", "landuse.parquet")
        if not _exists(parquet_fn):
            return None

        for id_column in ("topaz_id", "TopazID"):
            try:
                df = pd.read_parquet(parquet_fn, columns=[id_column, "key"])
            except Exception:
                continue
            if id_column not in df.columns or "key" not in df.columns:
                continue
            key_map: Dict[int, Optional[str]] = {}
            for row in df.itertuples(index=False):
                topaz_value = getattr(row, id_column, None)
                if topaz_value is None or pd.isna(topaz_value):
                    continue
                try:
                    topaz_id = int(topaz_value)
                except (TypeError, ValueError):
                    continue
                key_map[topaz_id] = self._normalize_landuse_key(getattr(row, "key", None))
            if key_map:
                return key_map
        return None

    def _contrast_landuse_skip_reason(
        self,
        contrast_id: int,
        contrast_name: str,
        *,
        landuse_cache: Optional[Dict[str, Optional[Dict[int, Optional[str]]]]] = None,
    ) -> Optional[str]:
        if not contrast_name:
            return None

        try:
            contrast_payload = self._load_contrast_sidecar(contrast_id)
        except FileNotFoundError:
            return None

        control_key, contrast_key = self._contrast_scenario_keys(contrast_name)
        if control_key == contrast_key:
            return "landuse_unchanged"

        base_key = _resolve_base_scenario_key(self.wd)
        try:
            contrast_wd = _resolve_contrast_scenario_wd(self.wd, contrast_key, base_key)
        except FileNotFoundError:
            return None

        contrast_topaz_ids = _contrast_topaz_ids_from_mapping(contrast_payload, contrast_wd)
        if not contrast_topaz_ids:
            return None

        cache = landuse_cache if landuse_cache is not None else {}
        if control_key not in cache:
            try:
                control_wd = _resolve_contrast_scenario_wd(self.wd, control_key, base_key)
            except FileNotFoundError:
                return None
            cache[control_key] = self._load_landuse_key_map(control_wd)
        if contrast_key not in cache:
            cache[contrast_key] = self._load_landuse_key_map(contrast_wd)

        control_map = cache.get(control_key)
        contrast_map = cache.get(contrast_key)
        if not control_map or not contrast_map:
            return None

        for topaz_id in contrast_topaz_ids:
            control_value = control_map.get(int(topaz_id))
            contrast_value = contrast_map.get(int(topaz_id))
            if control_value is None or contrast_value is None:
                return None
            if control_value != contrast_value:
                return None

        return "landuse_unchanged"

    def _scenario_run_readme_path(self, scenario_name: Optional[Any]) -> str:
        scenario_key = self._normalize_scenario_key(scenario_name)
        if scenario_key == str(self.base_scenario):
            return _join(self.wd, "wepp", "output", "interchange", "README.md")
        return _join(
            self.wd,
            OMNI_REL_DIR,
            "scenarios",
            scenario_key,
            "wepp",
            "output",
            "interchange",
            "README.md",
        )

    def _redisprep_snapshot(self, path: str) -> Optional[Dict[str, Any]]:
        if not _exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as fp:
                payload = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.debug('Failed to read redisprep snapshot from %s: %s', path, exc)
            return None
        if not isinstance(payload, dict):
            return None
        snapshot = {
            key: value
            for key, value in payload.items()
            if str(key).startswith('timestamps:')
        }
        return self._normalize_contrast_redisprep_snapshot(snapshot)

    def _normalize_contrast_redisprep_snapshot(
        self, snapshot: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not snapshot:
            return None
        keep_keys = {"timestamps:run_wepp_hillslopes", "timestamps:run_wepp_watershed"}
        filtered = {key: snapshot.get(key) for key in keep_keys if key in snapshot}
        if "timestamps:run_wepp_watershed" not in filtered:
            return None
        return filtered

    def _scenario_redisprep_snapshot(self, scenario_key: str) -> Optional[Dict[str, Any]]:
        if scenario_key == str(self.base_scenario):
            redisprep_path = _join(self.wd, 'redisprep.dump')
        else:
            redisprep_path = _join(
                self.wd,
                OMNI_REL_DIR,
                'scenarios',
                scenario_key,
                'redisprep.dump',
            )
        return self._redisprep_snapshot(redisprep_path)

    def _contrast_scenario_keys(self, contrast_name: str) -> Tuple[str, str]:
        control_part, target_part = contrast_name.split('__to__')
        control_scenario_raw = control_part.split(',')[0]
        control_key = self._normalize_scenario_key(control_scenario_raw)
        target_key = self._normalize_scenario_key(target_part)
        return control_key, target_key

    def _contrast_run_status(self, contrast_id: int, contrast_name: str) -> str:
        run_marker = self._contrast_run_readme_path(contrast_id)
        if not _exists(run_marker):
            return 'needs_run'

        sidecar_sha1 = _hash_file_sha1(self._contrast_sidecar_path(contrast_id))
        if not sidecar_sha1:
            return 'needs_run'

        control_key, target_key = self._contrast_scenario_keys(contrast_name)
        control_snapshot = self._scenario_redisprep_snapshot(control_key)
        contrast_snapshot = self._scenario_redisprep_snapshot(target_key)
        if control_snapshot is None or contrast_snapshot is None:
            return 'needs_run'

        prev_entry = self.contrast_dependency_tree.get(contrast_name)
        if not prev_entry:
            return 'needs_run'
        selection_mode = (getattr(self, "_contrast_selection_mode", None) or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode == "stream_order":
            try:
                current_passes = self._resolve_order_reduction_passes()
            except ValueError:
                return "needs_run"
            prev_passes = prev_entry.get("order_reduction_passes")
            if prev_passes is None:
                return "needs_run"
            try:
                prev_passes = int(prev_passes)
            except (TypeError, ValueError):
                return "needs_run"
            if prev_passes != current_passes:
                return "needs_run"
        prev_control = self._normalize_contrast_redisprep_snapshot(prev_entry.get('control_redisprep'))
        prev_contrast = self._normalize_contrast_redisprep_snapshot(prev_entry.get('contrast_redisprep'))
        if prev_control is None or prev_contrast is None:
            return 'needs_run'
        if prev_entry.get('sidecar_sha1') != sidecar_sha1:
            return 'needs_run'
        if prev_control != control_snapshot:
            return 'needs_run'
        if prev_contrast != contrast_snapshot:
            return 'needs_run'

        return 'up_to_date'

    def _contrast_dependency_entry(
        self,
        contrast_id: int,
        contrast_name: str,
    ) -> Dict[str, Any]:
        dependencies = self._contrast_dependencies(contrast_name)
        sidecar_sha1 = _hash_file_sha1(self._contrast_sidecar_path(contrast_id))
        control_key, target_key = self._contrast_scenario_keys(contrast_name)
        control_snapshot = self._scenario_redisprep_snapshot(control_key)
        contrast_snapshot = self._scenario_redisprep_snapshot(target_key)
        entry = {
            'dependencies': dependencies,
            'sidecar_sha1': sidecar_sha1,
            'control_redisprep': control_snapshot,
            'contrast_redisprep': contrast_snapshot,
            'last_run': time.time(),
        }
        selection_mode = (getattr(self, "_contrast_selection_mode", None) or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode == "stream_order":
            entry["order_reduction_passes"] = self._resolve_order_reduction_passes()
        return entry

    def _update_contrast_dependency_tree(
        self,
        contrast_name: str,
        dependency_entry: Dict[str, Any],
        *,
        max_tries: int = 5,
        delay: float = 1.0,
    ) -> None:
        for attempt in range(max_tries):
            try:
                omni = type(self).getInstance(self.wd)
                with omni.locked():
                    dependency_tree = dict(omni.contrast_dependency_tree)
                    dependency_tree[contrast_name] = dependency_entry
                    omni._contrast_dependency_tree = dependency_tree
            except NoDbAlreadyLockedError:
                if attempt + 1 == max_tries:
                    raise
                time.sleep(delay)
            else:
                break

    def _remove_contrast_dependency_entry(
        self,
        contrast_name: str,
        *,
        max_tries: int = 5,
        delay: float = 1.0,
    ) -> None:
        for attempt in range(max_tries):
            try:
                omni = type(self).getInstance(self.wd)
                with omni.locked():
                    dependency_tree = dict(omni.contrast_dependency_tree)
                    dependency_tree.pop(contrast_name, None)
                    omni._contrast_dependency_tree = dependency_tree
            except NoDbAlreadyLockedError:
                if attempt + 1 == max_tries:
                    raise
                time.sleep(delay)
            else:
                break

    def build_contrasts(
        self,
        control_scenario_def: Optional[ScenarioDef],
        contrast_scenario_def: Optional[ScenarioDef],
        obj_param: str = 'Runoff_mm',
        contrast_cumulative_obj_param_threshold_fraction: float = 0.8,
        contrast_hillslope_limit: Optional[int] = None,
        hill_min_slope: Optional[float] = None,
        hill_max_slope: Optional[float] = None,
        select_burn_severities: Optional[List[int]] = None,
        select_topaz_ids: Optional[List[int]] = None,
        contrast_pairs: Optional[List[Dict[str, str]]] = None,
    ) -> None:
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

        self.logger.info('build_contrasts')

        selection_mode_value = getattr(self, "_contrast_selection_mode", None)
        selection_mode = (selection_mode_value or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"

        control_scenario = (
            _scenario_name_from_scenario_definition(control_scenario_def)
            if control_scenario_def is not None
            else None
        )
        contrast_scenario = (
            _scenario_name_from_scenario_definition(contrast_scenario_def)
            if contrast_scenario_def is not None
            else None
        )
        if selection_mode not in {"user_defined_areas", "stream_order", "user_defined_hillslope_groups"} and (
            control_scenario is None
            or contrast_scenario is None
        ):
            raise ValueError("control_scenario_def and contrast_scenario_def are required for contrast builds")

        # save parameters for defining contrasts
        with self.locked():
            self._contrast_scenario = contrast_scenario
            self._control_scenario = control_scenario
            self._contrast_object_param = obj_param
            self._contrast_cumulative_obj_param_threshold_fraction = contrast_cumulative_obj_param_threshold_fraction
            self._contrast_hillslope_limit = contrast_hillslope_limit
            self._contrast_hill_min_slope = hill_min_slope
            self._contrast_hill_max_slope = hill_max_slope
            self._contrast_select_burn_severities = select_burn_severities
            self._contrast_select_topaz_ids = select_topaz_ids
            if contrast_pairs is not None:
                self._contrast_pairs = self._normalize_contrast_pairs(contrast_pairs)

        self._build_contrasts()
        self._build_contrast_ids_geojson()

    @property
    def base_scenario(self) -> OmniScenario:
        if self.has_sbs:
            return OmniScenario.SBSmap
        return OmniScenario.Undisturbed

    def _build_contrasts(self) -> None:
        global OMNI_REL_DIR

        selection_mode_value = getattr(self, "_contrast_selection_mode", None)
        selection_mode = (selection_mode_value or 'cumulative').strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"

        if selection_mode == "user_defined_areas":
            self._build_contrasts_user_defined_areas()
            return
        if selection_mode == "user_defined_hillslope_groups":
            self._build_contrasts_user_defined_hillslope_groups()
            return
        if selection_mode == "stream_order":
            self._build_contrasts_stream_order()
            return

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

        from wepppy.nodb.core import Watershed
        apply_advanced_filters = selection_mode == 'cumulative'
        if not apply_advanced_filters:
            if any(
                value is not None
                for value in (
                    contrast_hill_min_slope,
                    contrast_hill_max_slope,
                    contrast_select_burn_severities,
                    contrast_select_topaz_ids,
                )
            ):
                self.logger.info(
                    "Contrast selection mode '%s' ignores advanced filters; apply cumulative mode to use them.",
                    selection_mode,
                )
            contrast_hill_min_slope = None
            contrast_hill_max_slope = None
            contrast_select_burn_severities = None
            contrast_select_topaz_ids = None
            if contrast_hillslope_limit is not None:
                self.logger.info(
                    "Contrast selection mode '%s' ignores omni_contrast_hillslope_limit.",
                    selection_mode,
                )
                contrast_hillslope_limit = None

        contrast_hillslope_limit_max = 100 if selection_mode == 'cumulative' else None

        if contrast_hillslope_limit is not None:
            try:
                contrast_hillslope_limit = int(contrast_hillslope_limit)
            except (TypeError, ValueError) as exc:
                raise ValueError("omni_contrast_hillslope_limit must be an integer") from exc
            if contrast_hillslope_limit <= 0:
                raise ValueError("omni_contrast_hillslope_limit must be >= 1")
            if contrast_hillslope_limit_max is not None and contrast_hillslope_limit > contrast_hillslope_limit_max:
                self.logger.warning(
                    "omni_contrast_hillslope_limit capped at %d (requested %d).",
                    contrast_hillslope_limit_max,
                    contrast_hillslope_limit,
                )
                contrast_hillslope_limit = contrast_hillslope_limit_max

        def _normalize_int_set(value: Any, label: str) -> Optional[Set[int]]:
            if value is None or value == "":
                return None
            if isinstance(value, str):
                raw_items = [item.strip() for item in value.split(",") if item.strip()]
            elif isinstance(value, (list, tuple, set)):
                raw_items = list(value)
            else:
                raw_items = [value]
            parsed: Set[int] = set()
            for item in raw_items:
                if item is None or item == "":
                    continue
                try:
                    parsed.add(int(item))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{label} entries must be integers") from exc
            return parsed or None

        def _normalize_slope(value: Any, label: str) -> Optional[float]:
            if value is None or value == "":
                return None
            try:
                slope = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{label} must be a number") from exc
            if slope < 0:
                raise ValueError(f"{label} must be >= 0")
            if slope > 1.0:
                slope = slope / 100.0
            return slope

        if apply_advanced_filters:
            contrast_hill_min_slope = _normalize_slope(
                contrast_hill_min_slope,
                "omni_contrast_hill_min_slope",
            )
            contrast_hill_max_slope = _normalize_slope(
                contrast_hill_max_slope,
                "omni_contrast_hill_max_slope",
            )
            if (
                contrast_hill_min_slope is not None
                and contrast_hill_max_slope is not None
                and contrast_hill_min_slope > contrast_hill_max_slope
            ):
                raise ValueError("omni_contrast_hill_min_slope must be <= omni_contrast_hill_max_slope")
            contrast_select_burn_severities = _normalize_int_set(
                contrast_select_burn_severities,
                "omni_contrast_select_burn_severities",
            )
            contrast_select_topaz_ids = _normalize_int_set(
                contrast_select_topaz_ids,
                "omni_contrast_select_topaz_ids",
            )

        wd = self.wd

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        top2wepp = {k: v for k, v in translator.top2wepp.items() if not (str(k).endswith('4') or int(k) == 0)}

        # find hillslopes with the most erosion from the control scenario
        # soils_erosion_descending is a list of ObjectiveParameter named_tuples with fields: topaz_id, wepp_id, and value
        obj_param_descending, total_erosion_kg = self.get_objective_parameter_from_gpkg(obj_param, scenario=control_scenario)

        if len(obj_param_descending) == 0:
            raise Exception('No soil erosion data found!')

        if apply_advanced_filters and any(
            value is not None
            for value in (
                contrast_hill_min_slope,
                contrast_hill_max_slope,
                contrast_select_burn_severities,
                contrast_select_topaz_ids,
            )
        ):
            original_count = len(obj_param_descending)
            topaz_filter = None
            if contrast_select_topaz_ids is not None:
                topaz_filter = {str(topaz_id) for topaz_id in contrast_select_topaz_ids}

            slope_lookup: Dict[str, float] = {}
            burn_lookup: Dict[str, int] = {}
            burn_set = contrast_select_burn_severities
            landuse = None
            if burn_set is not None:
                burn_set = set(burn_set)
                invalid = [val for val in burn_set if val not in {0, 1, 2, 3}]
                if invalid:
                    raise ValueError(
                        f"omni_contrast_select_burn_severities must be 0-3; got {sorted(invalid)}"
                    )
                from wepppy.nodb.core import Landuse

                control_wd = self.wd if control_scenario is None else _join(
                    self.wd,
                    OMNI_REL_DIR,
                    'scenarios',
                    control_scenario,
                )
                landuse = Landuse.getInstance(control_wd)

            def _burn_value(label: Optional[str]) -> int:
                name = (label or "Unburned").strip().lower()
                mapping = {
                    "unburned": 0,
                    "low": 1,
                    "moderate": 2,
                    "mod": 2,
                    "high": 3,
                }
                if name not in mapping:
                    raise ValueError(f"Unknown burn class '{label}' while filtering contrasts")
                return mapping[name]

            filtered: List[ObjectiveParameter] = []
            for item in obj_param_descending:
                topaz_id = str(item.topaz_id)
                if topaz_filter is not None and topaz_id not in topaz_filter:
                    continue
                if contrast_hill_min_slope is not None or contrast_hill_max_slope is not None:
                    slope = slope_lookup.get(topaz_id)
                    if slope is None:
                        slope = watershed.hillslope_slope(topaz_id)
                        slope_lookup[topaz_id] = slope
                    if contrast_hill_min_slope is not None and slope < contrast_hill_min_slope:
                        continue
                    if contrast_hill_max_slope is not None and slope > contrast_hill_max_slope:
                        continue
                if burn_set is not None and landuse is not None:
                    burn_class = burn_lookup.get(topaz_id)
                    if burn_class is None:
                        burn_class = _burn_value(landuse.identify_burn_class(topaz_id))
                        burn_lookup[topaz_id] = burn_class
                    if burn_class not in burn_set:
                        continue
                filtered.append(item)

            obj_param_descending = filtered
            total_erosion_kg = float(sum(item.value for item in obj_param_descending))
            self.logger.info(
                "  contrast filters reduced candidates from %d to %d",
                original_count,
                len(obj_param_descending),
            )

        if not obj_param_descending:
            raise ValueError("No hillslopes matched contrast filters.")
        if total_erosion_kg <= 0:
            raise ValueError("Contrast objective parameter total is zero after filtering.")
        
        with self.locked():
            self._contrasts = None
            self._contrast_names = []

        sidecar_dir = self._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts: List[ContrastMapping] = []
        contrast_names: List[str] = []
        existing_contrast_count = 0

        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        os.makedirs(contrasts_dir, exist_ok=True)
        report_fn = _join(contrasts_dir, 'build_report.ndjson')
        report_fp = open(report_fn, 'w')

        running_obj_param = 0.0
        for d in obj_param_descending:
            if contrast_hillslope_limit is not None:
                if len(contrasts) >= contrast_hillslope_limit:
                    break
            elif contrast_hillslope_limit_max is not None and len(contrasts) >= contrast_hillslope_limit_max:
                self.logger.warning(
                    "Contrast selection reached cap of %d hillslopes without an explicit limit; stopping.",
                    contrast_hillslope_limit_max,
                )
                break

            running_obj_param += d.value

            topaz_id = d.topaz_id
            wepp_id = d.wepp_id
            if contrast_scenario is None:
                contrast_name = f'{control_scenario},{topaz_id}__to__{self.base_scenario}'
            else:
                contrast_name = f'{control_scenario},{topaz_id}__to__{contrast_scenario}'
            contrast_id = existing_contrast_count + len(contrasts) + 1
            report_control_scenario = control_scenario or str(self.base_scenario)
            
            contrast = {}
            for _topaz_id, _wepp_id in top2wepp.items():

                # need to do it this way so the wepp_ids stay ordered.
                if str(_topaz_id) == str(topaz_id):
                    if contrast_scenario is None:
                        wepp_id_path = _join(wd, f'wepp/output/H{wepp_id}')   
                    else: 
                        wepp_id_path = _join(
                            wd,
                            OMNI_REL_DIR,
                            'scenarios',
                            contrast_scenario,
                            'wepp',
                            'output',
                            f'H{wepp_id}',
                        )
                else:
                    if control_scenario is None:
                        wepp_id_path = _join(wd, f'wepp/output/H{_wepp_id}')
                    else:
                        wepp_id_path = _join(
                            wd,
                            OMNI_REL_DIR,
                            'scenarios',
                            control_scenario,
                            'wepp',
                            'output',
                            f'H{_wepp_id}',
                        )
                contrast[_topaz_id] = wepp_id_path  # os.path.relpath(wepp_id_path, contrast_dir)

            contrasts.append(contrast)
            contrast_names.append(contrast_name)
            self._write_contrast_sidecar(contrast_id, contrast)
            
            report_fp.write(json.dumps({
                'contrast_id': contrast_id,
                'control_scenario': report_control_scenario,
                'contrast_scenario': contrast_scenario,
                'wepp_id': wepp_id,
                'topaz_id': topaz_id,
                'obj_param': d.value,
                'running_obj_param': running_obj_param,
                'pct_cumulative': running_obj_param / total_erosion_kg * 100
            }) + '\n')

            if running_obj_param / total_erosion_kg >= contrast_cumulative_obj_param_threshold_fraction:
                break

        report_fp.close()

        with self.locked():
            self._contrasts = None
            self._contrast_names = contrast_names

    def _build_contrast_ids_geojson(self) -> Optional[str]:
        selection_mode = (getattr(self, "_contrast_selection_mode", None) or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"

        report_entries = self._load_contrast_build_report()

        def _sorted_keys(values: Iterable[Any]) -> List[Any]:
            try:
                return sorted(values, key=lambda item: int(item))
            except (TypeError, ValueError):
                return sorted(values, key=lambda item: str(item))

        selections: List[Tuple[str, Set[str], Dict[str, Any]]] = []
        stream_groups: Dict[int, Dict[str, Any]] = {}

        if selection_mode == "user_defined_areas":
            feature_map: Dict[Any, Tuple[str, Set[str], Dict[str, Any]]] = {}
            for entry in report_entries:
                if entry.get("selection_mode") != "user_defined_areas":
                    continue
                feature_index = entry.get("feature_index")
                if feature_index in (None, ""):
                    continue
                try:
                    feature_key: Any = int(feature_index)
                except (TypeError, ValueError):
                    feature_key = str(feature_index)
                if feature_key in feature_map:
                    continue
                topaz_ids = entry.get("topaz_ids") or []
                topaz_set = {str(item) for item in topaz_ids if item not in (None, "")}
                if not topaz_set:
                    continue
                label = str(feature_key)
                feature_map[feature_key] = (label, topaz_set, {"feature_index": feature_key})
            for key in _sorted_keys(feature_map.keys()):
                selections.append(feature_map[key])
        elif selection_mode == "user_defined_hillslope_groups":
            group_map: Dict[Any, Tuple[str, Set[str], Dict[str, Any]]] = {}
            for entry in report_entries:
                if entry.get("selection_mode") != "user_defined_hillslope_groups":
                    continue
                group_index = entry.get("group_index")
                if group_index in (None, ""):
                    continue
                try:
                    group_key: Any = int(group_index)
                except (TypeError, ValueError):
                    group_key = str(group_index)
                if group_key in group_map:
                    continue
                topaz_ids = entry.get("topaz_ids") or []
                topaz_set = {str(item) for item in topaz_ids if item not in (None, "")}
                if not topaz_set:
                    continue
                label = str(group_key)
                group_map[group_key] = (label, topaz_set, {"group_index": group_key})
            for key in _sorted_keys(group_map.keys()):
                selections.append(group_map[key])
        elif selection_mode == "stream_order":
            group_map: Dict[Any, Dict[str, Any]] = {}
            for entry in report_entries:
                if entry.get("selection_mode") != "stream_order":
                    continue
                group_value = entry.get("subcatchments_group")
                if group_value in (None, ""):
                    continue
                try:
                    group_key: Any = int(group_value)
                except (TypeError, ValueError):
                    group_key = str(group_value)
                if group_key in group_map:
                    continue
                if entry.get("status") == "skipped" or entry.get("n_hillslopes") in (None, 0, 0.0):
                    continue
                group_map[group_key] = entry
            for key in _sorted_keys(group_map.keys()):
                stream_groups[int(key)] = group_map[key]
        else:
            seen: Set[str] = set()
            for entry in report_entries:
                entry_mode = entry.get("selection_mode")
                if entry_mode not in (None, "", "cumulative"):
                    continue
                topaz_id = entry.get("topaz_id")
                if topaz_id in (None, ""):
                    continue
                label = str(topaz_id)
                if label in seen:
                    continue
                seen.add(label)
                try:
                    topaz_value: Any = int(topaz_id)
                except (TypeError, ValueError):
                    topaz_value = label
                selections.append((label, {label}, {"topaz_id": topaz_value}))

        output_path = self._contrast_ids_geojson_path()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if selection_mode == "stream_order":
            if not stream_groups:
                with open(output_path, "w", encoding="ascii", newline="\n") as fp:
                    json.dump({"type": "FeatureCollection", "features": []}, fp, ensure_ascii=True)
                return output_path
            try:
                import rasterio
                from rasterio.features import shapes
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError("rasterio is required for stream-order contrast overlay GeoJSON.") from exc
            try:
                from shapely.geometry import shape
                from shapely.ops import unary_union
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError("shapely is required for stream-order contrast overlay GeoJSON.") from exc

            watershed = Watershed.getInstance(self.wd)
            order_reduction_passes = self._resolve_order_reduction_passes()
            wbt_dir = Path(getattr(watershed, "wbt_wd", _join(self.wd, "dem", "wbt")))
            subwta_pruned_path = wbt_dir / f"subwta.strahler_pruned_{order_reduction_passes}.tif"
            if not subwta_pruned_path.exists():
                raise FileNotFoundError(f"Missing stream-order subwta raster: {subwta_pruned_path}")

            group_values: Dict[int, int] = {}
            for group_id in _sorted_keys(stream_groups.keys()):
                try:
                    group_id_int = int(group_id)
                except (TypeError, ValueError):
                    continue
                raw_value = group_id_int // 10 if group_id_int % 10 == 0 else group_id_int
                if raw_value <= 0:
                    continue
                group_values[raw_value] = group_id_int
            if not group_values:
                with open(output_path, "w", encoding="ascii", newline="\n") as fp:
                    json.dump({"type": "FeatureCollection", "features": []}, fp, ensure_ascii=True)
                return output_path

            geometries: Dict[int, List[Any]] = {key: [] for key in group_values}
            crs = None
            with rasterio.open(subwta_pruned_path) as dataset:
                data = dataset.read(1, masked=True)
                transform = dataset.transform
                crs = dataset.crs
                mask = None
                if hasattr(data, "mask"):
                    mask = ~data.mask
                for geom, value in shapes(data, mask=mask, transform=transform):
                    try:
                        value_int = int(value)
                    except (TypeError, ValueError):
                        continue
                    if value_int not in group_values:
                        continue
                    geometries[value_int].append(shape(geom))

            features: List[Dict[str, Any]] = []
            for raw_value in _sorted_keys(group_values.keys()):
                geoms = geometries.get(raw_value, [])
                if not geoms:
                    continue
                merged = unary_union(geoms)
                if merged is None or getattr(merged, "is_empty", False):
                    continue
                group_id = group_values[raw_value]
                label = str(group_id)
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "contrast_label": label,
                            "label": label,
                            "selection_mode": selection_mode,
                            "subcatchments_group": group_id,
                        },
                        "geometry": merged.__geo_interface__,
                    }
                )

            utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
            geojson = {"type": "FeatureCollection", "features": features}
            if crs:
                geojson["crs"] = {"type": "name", "properties": {"name": str(crs)}}
            with open(utm_path, "w", encoding="ascii", newline="\n") as fp:
                json.dump(geojson, fp, ensure_ascii=True)
            from wepppy.topo.watershed_abstraction.support import json_to_wgs
            wgs_path = json_to_wgs(utm_path, s_srs=str(crs) if crs else None)
            if wgs_path != output_path:
                os.replace(wgs_path, output_path)
            return output_path

        if selection_mode == "user_defined_areas":
            if not selections:
                with open(output_path, "w", encoding="ascii", newline="\n") as fp:
                    json.dump({"type": "FeatureCollection", "features": []}, fp, ensure_ascii=True)
                return output_path
            try:
                import numpy as np
                import rasterio
                from rasterio.features import shapes
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError("rasterio is required for user-defined contrast overlay GeoJSON.") from exc
            try:
                from shapely.geometry import shape
                from shapely.ops import unary_union
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError("shapely is required for user-defined contrast overlay GeoJSON.") from exc

            watershed = Watershed.getInstance(self.wd)
            subwta_path = getattr(watershed, "subwta", None)
            if not subwta_path or not _exists(subwta_path):
                raise FileNotFoundError("Hillslope raster not found for user-defined contrast overlay GeoJSON.")

            with rasterio.open(subwta_path) as dataset:
                data = dataset.read(1, masked=True)
                transform = dataset.transform
                crs = dataset.crs
                data_array = data
                base_mask = None
                if hasattr(data, "mask"):
                    base_mask = ~data.mask
                    data_array = data.data

            features: List[Dict[str, Any]] = []
            for label, topaz_ids, extra in selections:
                topaz_values: List[int] = []
                for topaz_id in topaz_ids:
                    try:
                        topaz_values.append(int(topaz_id))
                    except (TypeError, ValueError):
                        continue
                if not topaz_values:
                    continue
                mask = np.isin(data_array, topaz_values)
                if base_mask is not None:
                    mask = mask & base_mask
                if not mask.any():
                    continue
                geoms = [shape(geom) for geom, _ in shapes(data_array, mask=mask, transform=transform)]
                if not geoms:
                    continue
                merged = unary_union(geoms)
                if merged is None or getattr(merged, "is_empty", False):
                    continue
                props = {"contrast_label": label, "label": label, "selection_mode": selection_mode}
                props.update(extra)
                features.append(
                    {
                        "type": "Feature",
                        "properties": props,
                        "geometry": merged.__geo_interface__,
                    }
                )

            utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
            geojson = {"type": "FeatureCollection", "features": features}
            if crs:
                geojson["crs"] = {"type": "name", "properties": {"name": str(crs)}}
            with open(utm_path, "w", encoding="ascii", newline="\n") as fp:
                json.dump(geojson, fp, ensure_ascii=True)
            from wepppy.topo.watershed_abstraction.support import json_to_wgs
            wgs_path = json_to_wgs(utm_path, s_srs=str(crs) if crs else None)
            if wgs_path != output_path:
                os.replace(wgs_path, output_path)
            return output_path

        if not selections:
            with open(output_path, "w", encoding="ascii", newline="\n") as fp:
                json.dump({"type": "FeatureCollection", "features": []}, fp, ensure_ascii=True)
            return output_path

        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("geopandas is required for contrast overlay GeoJSON.") from exc

        watershed = Watershed.getInstance(self.wd)
        hillslope_path = getattr(watershed, "subwta_shp", None)
        if not hillslope_path or not _exists(hillslope_path):
            raise FileNotFoundError("Hillslope polygons not found for contrast overlay GeoJSON.")

        hillslope_gdf = gpd.read_file(hillslope_path)
        if hillslope_gdf.empty:
            raise ValueError("No hillslope polygons available for contrast overlay GeoJSON.")

        id_column = None
        for candidate in ("TopazID", "topaz_id", "TOPAZ_ID"):
            if candidate in hillslope_gdf.columns:
                id_column = candidate
                break
        if id_column is None:
            raise ValueError("Hillslope polygons missing a TopazID field.")

        hillslope_lookup: Dict[str, Any] = {}
        for _, row in hillslope_gdf.iterrows():
            topaz_raw = row.get(id_column)
            if topaz_raw in (None, ""):
                continue
            topaz_id = str(topaz_raw)
            if topaz_id == "0" or topaz_id.endswith("4"):
                continue
            geom = row.geometry
            if geom is None or getattr(geom, "is_empty", False):
                continue
            hillslope_lookup[topaz_id] = geom

        if not hillslope_lookup:
            raise ValueError("No valid hillslope polygons available for contrast overlay GeoJSON.")

        from shapely.geometry import mapping
        from shapely.ops import unary_union

        features: List[Dict[str, Any]] = []
        missing_topaz: Set[str] = set()
        for label, topaz_ids, extra in selections:
            geoms = []
            for topaz_id in topaz_ids:
                geom = hillslope_lookup.get(topaz_id)
                if geom is None:
                    missing_topaz.add(topaz_id)
                    continue
                geoms.append(geom)
            if not geoms:
                continue
            merged = unary_union(geoms)
            if merged is None or getattr(merged, "is_empty", False):
                continue
            props = {"contrast_label": label, "label": label, "selection_mode": selection_mode}
            props.update(extra)
            features.append(
                {
                    "type": "Feature",
                    "properties": props,
                    "geometry": mapping(merged),
                }
            )

        if missing_topaz:
            self.logger.info(
                "Contrast overlay GeoJSON skipped %d hillslopes missing geometry.",
                len(missing_topaz),
            )

        with open(output_path, "w", encoding="ascii", newline="\n") as fp:
            json.dump(
                {"type": "FeatureCollection", "features": features},
                fp,
                ensure_ascii=True,
            )

        return output_path

    def _resolve_order_reduction_passes(self) -> int:
        raw_value = getattr(self, "_contrast_order_reduction_passes", None)
        if raw_value in (None, ""):
            raw_value = self.config_get_int("omni", "order_reduction_passes", 1)
        try:
            passes = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("order_reduction_passes must be an integer") from exc
        if passes == 0:
            return 1
        if passes < 0:
            raise ValueError("order_reduction_passes must be >= 1")
        return passes

    def _build_contrasts_stream_order(self) -> None:
        global OMNI_REL_DIR

        watershed = Watershed.getInstance(self.wd)
        if not watershed.delineation_backend_is_wbt:
            raise ValueError("Stream-order pruning requires the WBT delineation backend.")

        contrast_pairs = self._normalize_contrast_pairs(getattr(self, "_contrast_pairs", None))
        if not contrast_pairs:
            raise ValueError("omni_contrast_pairs is required for stream-order pruning")

        order_reduction_passes = self._resolve_order_reduction_passes()

        wbt_dir = Path(getattr(watershed, "wbt_wd", _join(self.wd, "dem", "wbt")))
        if not wbt_dir.exists():
            raise FileNotFoundError(f"WBT workspace not found: {wbt_dir}")

        def _resolve_wbt_raster(stem: str) -> Path:
            tif_path = wbt_dir / f"{stem}.tif"
            vrt_path = wbt_dir / f"{stem}.vrt"
            if tif_path.exists():
                return tif_path
            if vrt_path.exists():
                return vrt_path
            return tif_path

        flovec_path = _resolve_wbt_raster("flovec")
        netful_path = _resolve_wbt_raster("netful")
        relief_path = _resolve_wbt_raster("relief")
        chnjnt_path = _resolve_wbt_raster("chnjnt")
        bound_path = _resolve_wbt_raster("bound")
        subwta_path = _resolve_wbt_raster("subwta")
        outlet_path = wbt_dir / "outlet.geojson"

        for required_path, label in (
            (flovec_path, "flow vector"),
            (netful_path, "stream network"),
            (relief_path, "relief"),
            (chnjnt_path, "channel junctions"),
            (bound_path, "watershed boundary"),
            (subwta_path, "subwta"),
            (outlet_path, "outlet"),
        ):
            if not required_path.exists():
                raise FileNotFoundError(f"Missing WBT {label} file: {required_path}")

        prep = RedisPrep.getInstance(self.wd)
        build_subcatchments_ts = prep[TaskEnum.build_subcatchments]

        def _is_stale(path: Path) -> bool:
            if build_subcatchments_ts is None:
                return False
            try:
                return path.stat().st_mtime < build_subcatchments_ts
            except FileNotFoundError:
                return True

        strahler_path = netful_path.with_name("netful.strahler.tif")
        pruned_streams_path = netful_path.with_name(
            f"netful.pruned_{order_reduction_passes}.tif"
        )
        needs_prune = (
            not strahler_path.exists()
            or not pruned_streams_path.exists()
            or _is_stale(strahler_path)
            or _is_stale(pruned_streams_path)
        )
        if needs_prune:
            _prune_stream_order(
                flovec_path,
                netful_path,
                order_reduction_passes,
                overwrite_netful=False,
            )

        if not strahler_path.exists():
            raise FileNotFoundError(f"Missing Strahler order raster: {strahler_path}")
        if not pruned_streams_path.exists():
            raise FileNotFoundError(f"Missing pruned stream raster: {pruned_streams_path}")

        subwta_pruned_path = wbt_dir / f"subwta.strahler_pruned_{order_reduction_passes}.tif"
        netw_pruned_path = wbt_dir / f"netw.strahler_pruned_{order_reduction_passes}.tsv"
        order_pruned_path = wbt_dir / f"netful.strahler_pruned_{order_reduction_passes}.tif"
        chnjnt_pruned_path = wbt_dir / f"chnjnt.strahler_pruned_{order_reduction_passes}.tif"
        needs_hillslopes = (
            needs_prune
            or not subwta_pruned_path.exists()
            or not netw_pruned_path.exists()
            or _is_stale(subwta_pruned_path)
            or _is_stale(netw_pruned_path)
        )
        if needs_hillslopes:
            from whitebox_tools import WhiteboxTools

            wbt = WhiteboxTools(verbose=False, raise_on_error=True)
            wbt.set_working_dir(str(wbt_dir))
            rebuild_order = (
                needs_prune
                or not order_pruned_path.exists()
                or _is_stale(order_pruned_path)
            )
            if rebuild_order:
                ret = wbt.strahler_stream_order(
                    d8_pntr=str(flovec_path),
                    streams=str(pruned_streams_path),
                    output=str(order_pruned_path),
                    esri_pntr=False,
                    zero_background=False,
                )
                if ret != 0 or not order_pruned_path.exists():
                    raise RuntimeError(
                        "StrahlerStreamOrder failed "
                        f"(flovec={flovec_path}, streams={pruned_streams_path}, output={order_pruned_path})"
                    )
            rebuild_chnjnt = (
                needs_prune
                or not chnjnt_pruned_path.exists()
                or _is_stale(chnjnt_pruned_path)
            )
            if rebuild_chnjnt:
                ret = wbt.stream_junction_identifier(
                    d8_pntr=str(flovec_path),
                    streams=str(pruned_streams_path),
                    output=str(chnjnt_pruned_path),
                )
                if ret != 0 or not chnjnt_pruned_path.exists():
                    raise RuntimeError(
                        "StreamJunctionIdentifier failed "
                        f"(flovec={flovec_path}, streams={pruned_streams_path}, output={chnjnt_pruned_path})"
                    )
            ret = wbt.hillslopes_topaz(
                dem=str(relief_path),
                d8_pntr=str(flovec_path),
                streams=str(pruned_streams_path),
                pour_pts=str(outlet_path),
                watershed=str(bound_path),
                chnjnt=str(chnjnt_pruned_path),
                subwta=str(subwta_pruned_path),
                order=str(order_pruned_path),
                netw=str(netw_pruned_path),
            )
            if ret != 0:
                raise RuntimeError(
                    "hillslopes_topaz failed "
                    f"(subwta={subwta_pruned_path}, netw={netw_pruned_path})"
                )
        if not subwta_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order subwta raster: {subwta_pruned_path}")
        if not netw_pruned_path.exists():
            raise FileNotFoundError(f"Missing stream-order netw table: {netw_pruned_path}")

        from wepppyo3.raster_characteristics import identify_mode_single_raster_key
        import numpy as np
        import rasterio

        group_assignments = identify_mode_single_raster_key(
            key_fn=str(subwta_path),
            parameter_fn=str(subwta_pruned_path),
            ignore_channels=True,
        )

        with rasterio.open(subwta_pruned_path) as dataset:
            data = dataset.read(1, masked=True)
        unique_values = np.unique(data.compressed()) if data is not None else []

        group_map: Dict[int, List[str]] = {}
        for raw_value in unique_values:
            try:
                group_value = int(raw_value)
            except (TypeError, ValueError):
                continue
            if group_value <= 0:
                continue
            if str(group_value).endswith("4"):
                continue
            group_map[group_value * 10] = []

        translator = watershed.translator_factory()
        top2wepp = {
            str(k): str(v)
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith("4") or int(k) == 0)
        }
        valid_topaz = set(top2wepp.keys())

        for topaz_id, group_value in group_assignments.items():
            topaz_key = str(topaz_id)
            if topaz_key not in valid_topaz:
                continue
            try:
                group_id = int(group_value)
            except (TypeError, ValueError):
                continue
            if group_id <= 0:
                continue
            if str(group_id).endswith("4"):
                continue
            group_id = group_id * 10
            group_map.setdefault(group_id, []).append(topaz_key)

        def _sorted_group_ids(values: Iterable[int]) -> List[int]:
            try:
                return sorted(values, key=lambda item: int(item))
            except (TypeError, ValueError):
                return sorted(values)

        with self.locked():
            self._contrast_order_reduction_passes = order_reduction_passes
            self._contrasts = None
            self._contrast_names = []
            self._contrast_labels = {}

        sidecar_dir = self._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts_dir = _join(self.wd, OMNI_REL_DIR, "contrasts")
        os.makedirs(contrasts_dir, exist_ok=True)
        report_fn = _join(contrasts_dir, "build_report.ndjson")

        contrast_names: List[Optional[str]] = []
        contrast_id = 0

        with open(report_fn, "w", encoding="ascii") as report_fp:
            for group_id in _sorted_group_ids(group_map.keys()):
                topaz_ids = group_map.get(group_id, [])
                n_hillslopes = len(topaz_ids)
                topaz_set = set(topaz_ids)

                for pair in contrast_pairs:
                    control_key = self._normalize_scenario_key(pair.get("control_scenario"))
                    contrast_key = self._normalize_scenario_key(pair.get("contrast_scenario"))
                    control_scenario = None if control_key == str(self.base_scenario) else control_key
                    contrast_scenario = None if contrast_key == str(self.base_scenario) else contrast_key

                    contrast_id += 1
                    while len(contrast_names) < contrast_id:
                        contrast_names.append(None)

                    report_entry = {
                        "contrast_id": contrast_id,
                        "control_scenario": control_key,
                        "contrast_scenario": contrast_key,
                        "wepp_id": None,
                        "topaz_id": None,
                        "obj_param": None,
                        "running_obj_param": None,
                        "pct_cumulative": None,
                        "selection_mode": "stream_order",
                        "n_hillslopes": n_hillslopes,
                        "subcatchments_group": group_id,
                    }

                    if n_hillslopes == 0:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    contrast_name = f"{control_key},{contrast_id}__to__{contrast_key}"

                    contrast: ContrastMapping = {}
                    for topaz_key, wepp_id in top2wepp.items():
                        if topaz_key in topaz_set:
                            if contrast_scenario is None:
                                wepp_id_path = _join(self.wd, f"wepp/output/H{wepp_id}")
                            else:
                                wepp_id_path = _join(
                                    self.wd,
                                    OMNI_REL_DIR,
                                    "scenarios",
                                    contrast_scenario,
                                    "wepp",
                                    "output",
                                    f"H{wepp_id}",
                                )
                        else:
                            if control_scenario is None:
                                wepp_id_path = _join(self.wd, f"wepp/output/H{wepp_id}")
                            else:
                                wepp_id_path = _join(
                                    self.wd,
                                    OMNI_REL_DIR,
                                    "scenarios",
                                    control_scenario,
                                    "wepp",
                                    "output",
                                    f"H{wepp_id}",
                                )
                        contrast[topaz_key] = wepp_id_path

                    contrast_names[contrast_id - 1] = contrast_name
                    self._write_contrast_sidecar(contrast_id, contrast)
                    report_fp.write(json.dumps(report_entry) + "\n")

        with self.locked():
            self._contrasts = None
            self._contrast_names = contrast_names

    def _build_contrasts_user_defined_hillslope_groups(self) -> None:
        global OMNI_REL_DIR

        contrast_groups_raw = getattr(self, "_contrast_hillslope_groups", None)

        def _parse_groups(value: Any) -> List[List[str]]:
            if value in (None, ""):
                return []
            if isinstance(value, (list, tuple)):
                rows = list(value)
            else:
                rows = str(value).splitlines()
            groups: List[List[str]] = []
            for row in rows:
                if row is None:
                    continue
                if isinstance(row, (list, tuple, set)):
                    tokens = [str(item) for item in row if item not in (None, "")]
                else:
                    line = str(row).strip()
                    if not line:
                        continue
                    line = line.rstrip(";")
                    tokens = [token for token in re.split(r"[,\s;]+", line) if token]
                if not tokens:
                    continue
                group: List[str] = []
                for token in tokens:
                    value_str = str(token).strip()
                    if not value_str:
                        continue
                    try:
                        parsed = int(value_str)
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            "omni_contrast_hillslope_groups entries must be integers"
                        ) from exc
                    group.append(str(parsed))
                if group:
                    groups.append(group)
            return groups

        group_rows = _parse_groups(contrast_groups_raw)
        if not group_rows:
            raise ValueError(
                "omni_contrast_hillslope_groups is required for user_defined_hillslope_groups mode"
            )

        contrast_pairs = self._normalize_contrast_pairs(getattr(self, "_contrast_pairs", None))
        if not contrast_pairs:
            raise ValueError(
                "omni_contrast_pairs is required for user_defined_hillslope_groups mode"
            )

        ignored_fields = []
        if self._contrast_hillslope_limit is not None:
            ignored_fields.append("omni_contrast_hillslope_limit")
        if self._contrast_hill_min_slope is not None:
            ignored_fields.append("omni_contrast_hill_min_slope")
        if self._contrast_hill_max_slope is not None:
            ignored_fields.append("omni_contrast_hill_max_slope")
        if self._contrast_select_burn_severities is not None:
            ignored_fields.append("omni_contrast_select_burn_severities")
        if self._contrast_select_topaz_ids is not None:
            ignored_fields.append("omni_contrast_select_topaz_ids")
        if ignored_fields:
            self.logger.info(
                "User-defined hillslope groups ignore filters: %s",
                ", ".join(ignored_fields),
            )

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        top2wepp = {
            str(k): str(v)
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith("4") or int(k) == 0)
        }
        valid_topaz = set(top2wepp.keys())

        def _sorted_topaz_ids(values: Set[str]) -> List[str]:
            try:
                return sorted(values, key=lambda item: int(item))
            except (TypeError, ValueError):
                return sorted(values)

        missing_topaz: Set[str] = set()

        with self.locked():
            self._contrasts = None
            self._contrast_names = []
            self._contrast_labels = {}

        sidecar_dir = self._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts_dir = _join(self.wd, OMNI_REL_DIR, "contrasts")
        os.makedirs(contrasts_dir, exist_ok=True)
        report_fn = _join(contrasts_dir, "build_report.ndjson")

        existing_signature_map = self._load_user_defined_hillslope_group_signature_map()
        next_id = max(existing_signature_map.values(), default=0) + 1

        contrast_names: List[Optional[str]] = []
        contrast_labels: Dict[int, str] = {}

        with open(report_fn, "w", encoding="ascii") as report_fp:
            for group_index, raw_group in enumerate(group_rows, start=1):
                selected_topaz: Set[str] = set()
                for topaz_key in raw_group:
                    if topaz_key in (None, ""):
                        continue
                    if topaz_key == "0" or str(topaz_key).endswith("4"):
                        continue
                    if topaz_key not in valid_topaz:
                        missing_topaz.add(str(topaz_key))
                        continue
                    selected_topaz.add(topaz_key)

                topaz_ids = _sorted_topaz_ids(selected_topaz)
                n_hillslopes = len(selected_topaz)

                for pair_index, pair in enumerate(contrast_pairs, start=1):
                    control_key = self._normalize_scenario_key(pair.get("control_scenario"))
                    contrast_key = self._normalize_scenario_key(pair.get("contrast_scenario"))
                    control_scenario = None if control_key == str(self.base_scenario) else control_key
                    contrast_scenario = None if contrast_key == str(self.base_scenario) else contrast_key

                    signature = self._contrast_pair_signature(
                        control_key,
                        contrast_key,
                        str(group_index),
                    )
                    contrast_id = existing_signature_map.get(signature)
                    if contrast_id is None:
                        contrast_id = next_id
                        next_id += 1
                        existing_signature_map[signature] = contrast_id

                    contrast_labels[contrast_id] = str(group_index)
                    while len(contrast_names) < contrast_id:
                        contrast_names.append(None)

                    report_entry = {
                        "contrast_id": contrast_id,
                        "control_scenario": control_key,
                        "contrast_scenario": contrast_key,
                        "wepp_id": None,
                        "topaz_id": None,
                        "obj_param": None,
                        "running_obj_param": None,
                        "pct_cumulative": None,
                        "selection_mode": "user_defined_hillslope_groups",
                        "group_index": group_index,
                        "n_hillslopes": n_hillslopes,
                        "topaz_ids": topaz_ids,
                        "pair_index": pair_index,
                    }

                    if not selected_topaz:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    if contrast_scenario is None:
                        contrast_name = f"{control_scenario},{contrast_id}__to__{self.base_scenario}"
                    else:
                        contrast_name = f"{control_scenario},{contrast_id}__to__{contrast_scenario}"

                    contrast: ContrastMapping = {}
                    for topaz_id, wepp_id in top2wepp.items():
                        if topaz_id in selected_topaz:
                            if contrast_scenario is None:
                                wepp_id_path = _join(self.wd, f"wepp/output/H{wepp_id}")
                            else:
                                wepp_id_path = _join(
                                    self.wd,
                                    OMNI_REL_DIR,
                                    "scenarios",
                                    contrast_scenario,
                                    "wepp",
                                    "output",
                                    f"H{wepp_id}",
                                )
                        else:
                            if control_scenario is None:
                                wepp_id_path = _join(self.wd, f"wepp/output/H{wepp_id}")
                            else:
                                wepp_id_path = _join(
                                    self.wd,
                                    OMNI_REL_DIR,
                                    "scenarios",
                                    control_scenario,
                                    "wepp",
                                    "output",
                                    f"H{wepp_id}",
                                )
                        contrast[topaz_id] = wepp_id_path

                    contrast_names[contrast_id - 1] = contrast_name
                    self._write_contrast_sidecar(contrast_id, contrast)
                    report_fp.write(json.dumps(report_entry) + "\n")

        if missing_topaz:
            self.logger.info(
                "Skipped %d hillslopes missing from translator during group parsing.",
                len(missing_topaz),
            )

        with self.locked():
            self._contrasts = None
            self._contrast_names = contrast_names
            self._contrast_labels = contrast_labels

    def _build_contrasts_user_defined_areas(self) -> None:
        global OMNI_REL_DIR

        geojson_path = getattr(self, "_contrast_geojson_path", None)
        if not geojson_path:
            raise ValueError("omni_contrast_geojson_path is required for user_defined_areas mode")
        if not _exists(geojson_path):
            raise FileNotFoundError(f"Contrast GeoJSON not found: {geojson_path}")

        contrast_pairs = self._normalize_contrast_pairs(getattr(self, "_contrast_pairs", None))
        if not contrast_pairs:
            raise ValueError("omni_contrast_pairs is required for user_defined_areas mode")

        ignored_fields = []
        if self._contrast_hillslope_limit is not None:
            ignored_fields.append("omni_contrast_hillslope_limit")
        if self._contrast_hill_min_slope is not None:
            ignored_fields.append("omni_contrast_hill_min_slope")
        if self._contrast_hill_max_slope is not None:
            ignored_fields.append("omni_contrast_hill_max_slope")
        if self._contrast_select_burn_severities is not None:
            ignored_fields.append("omni_contrast_select_burn_severities")
        if self._contrast_select_topaz_ids is not None:
            ignored_fields.append("omni_contrast_select_topaz_ids")
        if ignored_fields:
            self.logger.info(
                "User-defined contrast selection ignores filters: %s",
                ", ".join(ignored_fields),
            )

        try:
            import geopandas as gpd
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("geopandas is required for user-defined contrast selection") from exc

        watershed = Watershed.getInstance(self.wd)
        hillslope_path = watershed.subwta_utm_shp
        if not hillslope_path or not _exists(hillslope_path):
            raise FileNotFoundError("Hillslope polygons not found for user-defined contrasts.")

        hillslope_gdf = gpd.read_file(hillslope_path)
        if hillslope_gdf.empty:
            raise ValueError("No hillslope polygons available for user-defined contrasts.")

        ron = Ron.getInstance(self.wd)
        project_srid = getattr(ron, "srid", None)
        target_crs = hillslope_gdf.crs
        if target_crs is None:
            if project_srid:
                target_crs = f"EPSG:{project_srid}"
                hillslope_gdf = hillslope_gdf.set_crs(target_crs)
                self.logger.info(
                    "Hillslope GeoJSON missing CRS; setting to project CRS EPSG:%s",
                    project_srid,
                )
            else:
                raise ValueError("Project CRS unavailable; cannot align contrast GeoJSON.")

        user_gdf = gpd.read_file(geojson_path)
        if user_gdf.empty:
            raise ValueError("Contrast GeoJSON contains no features.")
        if user_gdf.crs is None:
            user_gdf = user_gdf.set_crs(epsg=4326)
            self.logger.info("Contrast GeoJSON missing CRS; assuming WGS84 (EPSG:4326).")
        if target_crs is None:
            raise ValueError("Target CRS unavailable for user-defined contrasts.")
        user_gdf = user_gdf.to_crs(target_crs)

        translator = watershed.translator_factory()
        top2wepp = {
            str(k): str(v)
            for k, v in translator.top2wepp.items()
            if not (str(k).endswith("4") or int(k) == 0)
        }

        id_column = None
        for candidate in ("TopazID", "topaz_id", "TOPAZ_ID"):
            if candidate in hillslope_gdf.columns:
                id_column = candidate
                break
        if id_column is None:
            raise ValueError("Hillslope polygons missing a TopazID field.")

        hillslope_lookup: Dict[int, Dict[str, Any]] = {}
        missing_topaz = 0
        for idx, row in hillslope_gdf.iterrows():
            topaz_raw = row.get(id_column)
            if topaz_raw in (None, ""):
                continue
            topaz_id = str(topaz_raw)
            if topaz_id.endswith("4") or topaz_id == "0":
                continue
            if topaz_id not in top2wepp:
                missing_topaz += 1
                continue
            geom = row.geometry
            if geom is None or getattr(geom, "is_empty", False):
                continue
            area = float(getattr(geom, "area", 0.0) or 0.0)
            if area <= 0.0:
                continue
            hillslope_lookup[idx] = {
                "topaz_id": topaz_id,
                "geometry": geom,
                "area": area,
            }

        if missing_topaz:
            self.logger.info(
                "Skipped %d hillslopes with Topaz IDs missing from translator.",
                missing_topaz,
            )
        if not hillslope_lookup:
            raise ValueError("No valid hillslopes available for user-defined contrasts.")

        sindex = getattr(hillslope_gdf, "sindex", None)
        hill_indices = list(hillslope_lookup.keys())

        existing_signature_map = self._load_user_defined_signature_map()
        next_id = max(existing_signature_map.values(), default=0) + 1

        name_key = getattr(self, "_contrast_geojson_name_key", None)

        with self.locked():
            self._contrasts = None
            self._contrast_names = []
            self._contrast_labels = {}

        sidecar_dir = self._contrast_sidecar_dir()
        if _exists(sidecar_dir):
            shutil.rmtree(sidecar_dir)
        os.makedirs(sidecar_dir, exist_ok=True)

        contrasts_dir = _join(self.wd, OMNI_REL_DIR, "contrasts")
        os.makedirs(contrasts_dir, exist_ok=True)
        report_fn = _join(contrasts_dir, "build_report.ndjson")

        contrast_names: List[Optional[str]] = []
        contrast_labels: Dict[int, str] = {}

        def _sorted_topaz_ids(values: Set[str]) -> List[str]:
            try:
                return sorted(values, key=lambda item: int(item))
            except (TypeError, ValueError):
                return sorted(values)

        with open(report_fn, "w", encoding="ascii") as report_fp:
            for pair_index, pair in enumerate(contrast_pairs, start=1):
                control_key = self._normalize_scenario_key(pair.get("control_scenario"))
                contrast_key = self._normalize_scenario_key(pair.get("contrast_scenario"))
                control_scenario = None if control_key == str(self.base_scenario) else control_key
                contrast_scenario = None if contrast_key == str(self.base_scenario) else contrast_key

                for feature_index, (_, row) in enumerate(user_gdf.iterrows(), start=1):
                    label = None
                    if name_key:
                        raw_label = row.get(name_key)
                        if raw_label not in (None, ""):
                            label = str(raw_label).strip()
                    if not label:
                        label = str(feature_index)

                    signature = self._contrast_pair_signature(control_key, contrast_key, label)
                    contrast_id = existing_signature_map.get(signature)
                    if contrast_id is None:
                        contrast_id = next_id
                        next_id += 1
                        existing_signature_map[signature] = contrast_id
                    contrast_labels[contrast_id] = label
                    while len(contrast_names) < contrast_id:
                        contrast_names.append(None)

                    geom = row.geometry
                    selected_topaz: Set[str] = set()
                    if geom is not None and not getattr(geom, "is_empty", False):
                        try:
                            if sindex is not None:
                                candidate_indices = list(sindex.intersection(geom.bounds))
                            else:
                                candidate_indices = hill_indices
                            for idx in candidate_indices:
                                hill = hillslope_lookup.get(idx)
                                if not hill:
                                    continue
                                hill_area = hill["area"]
                                if hill_area <= 0.0:
                                    continue
                                inter_area = float(geom.intersection(hill["geometry"]).area)
                                if inter_area / hill_area >= 0.5:
                                    selected_topaz.add(hill["topaz_id"])
                        except Exception as exc:
                            self.logger.info(
                                "Failed to evaluate contrast feature %s: %s",
                                feature_index,
                                exc,
                            )

                    report_entry = {
                        "contrast_id": contrast_id,
                        "control_scenario": control_key,
                        "contrast_scenario": contrast_key,
                        "wepp_id": None,
                        "topaz_id": None,
                        "obj_param": None,
                        "running_obj_param": None,
                        "pct_cumulative": None,
                        "selection_mode": "user_defined_areas",
                        "feature_index": feature_index,
                        "area_label": label,
                        "n_hillslopes": len(selected_topaz),
                        "topaz_ids": _sorted_topaz_ids(selected_topaz),
                        "pair_index": pair_index,
                    }

                    if not selected_topaz:
                        report_entry["status"] = "skipped"
                        report_fp.write(json.dumps(report_entry) + "\n")
                        continue

                    if contrast_scenario is None:
                        contrast_name = f"{control_scenario},{contrast_id}__to__{self.base_scenario}"
                    else:
                        contrast_name = f"{control_scenario},{contrast_id}__to__{contrast_scenario}"

                    contrast: ContrastMapping = {}
                    for topaz_id, wepp_id in top2wepp.items():
                        if topaz_id in selected_topaz:
                            if contrast_scenario is None:
                                wepp_id_path = _join(self.wd, f"wepp/output/H{wepp_id}")
                            else:
                                wepp_id_path = _join(
                                    self.wd,
                                    OMNI_REL_DIR,
                                    "scenarios",
                                    contrast_scenario,
                                    "wepp",
                                    "output",
                                    f"H{wepp_id}",
                                )
                        else:
                            if control_scenario is None:
                                wepp_id_path = _join(self.wd, f"wepp/output/H{wepp_id}")
                            else:
                                wepp_id_path = _join(
                                    self.wd,
                                    OMNI_REL_DIR,
                                    "scenarios",
                                    control_scenario,
                                    "wepp",
                                    "output",
                                    f"H{wepp_id}",
                                )
                        contrast[topaz_id] = wepp_id_path

                    contrast_names[contrast_id - 1] = contrast_name
                    self._write_contrast_sidecar(contrast_id, contrast)
                    report_fp.write(json.dumps(report_entry) + "\n")

        with self.locked():
            self._contrasts = None
            self._contrast_names = contrast_names
            self._contrast_labels = contrast_labels

    def build_contrasts_dry_run_report(
        self,
        control_scenario_def: Optional[ScenarioDef],
        contrast_scenario_def: Optional[ScenarioDef],
        obj_param: str = 'Runoff_mm',
        contrast_cumulative_obj_param_threshold_fraction: float = 0.8,
        contrast_hillslope_limit: Optional[int] = None,
        hill_min_slope: Optional[float] = None,
        hill_max_slope: Optional[float] = None,
        select_burn_severities: Optional[List[int]] = None,
        select_topaz_ids: Optional[List[int]] = None,
        contrast_pairs: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        self.build_contrasts(
            control_scenario_def=control_scenario_def,
            contrast_scenario_def=contrast_scenario_def,
            obj_param=obj_param,
            contrast_cumulative_obj_param_threshold_fraction=contrast_cumulative_obj_param_threshold_fraction,
            contrast_hillslope_limit=contrast_hillslope_limit,
            hill_min_slope=hill_min_slope,
            hill_max_slope=hill_max_slope,
            select_burn_severities=select_burn_severities,
            select_topaz_ids=select_topaz_ids,
            contrast_pairs=contrast_pairs,
        )

        return self.contrast_status_report()

    def contrast_status_report(self) -> Dict[str, Any]:
        selection_mode = (self._contrast_selection_mode or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"
        if selection_mode not in {"cumulative", "user_defined_areas", "user_defined_hillslope_groups", "stream_order"}:
            raise ValueError(f'Contrast selection mode "{selection_mode}" is not implemented yet.')
        contrast_names = self.contrast_names or []
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]] = {}

        if selection_mode == "user_defined_areas":
            report_entries = {}
            for entry in self._load_contrast_build_report():
                if entry.get("selection_mode") != "user_defined_areas":
                    continue
                contrast_id = entry.get("contrast_id")
                if isinstance(contrast_id, str):
                    try:
                        contrast_id = int(contrast_id)
                    except ValueError:
                        continue
                if isinstance(contrast_id, int):
                    report_entries[contrast_id] = entry

            control_scenario = self._normalize_scenario_key(self._control_scenario)
            contrast_scenario = self._normalize_scenario_key(self._contrast_scenario)
            contrast_labels = getattr(self, "_contrast_labels", None) or {}

            items: List[Dict[str, Any]] = []
            max_id = max(report_entries.keys(), default=0)
            if len(contrast_names) > max_id:
                max_id = len(contrast_names)
            for contrast_id in range(1, max_id + 1):
                contrast_name = contrast_names[contrast_id - 1] if contrast_id - 1 < len(contrast_names) else None
                report_entry = report_entries.get(contrast_id, {})
                label = report_entry.get("area_label")
                if not label:
                    label = contrast_labels.get(contrast_id) or contrast_labels.get(str(contrast_id))
                if not label:
                    label = str(contrast_id)

                raw_count = report_entry.get("n_hillslopes")
                if raw_count is None:
                    topaz_ids = report_entry.get("topaz_ids")
                    if isinstance(topaz_ids, list):
                        raw_count = len(topaz_ids)
                try:
                    n_hillslopes = int(raw_count) if raw_count is not None else 0
                except (TypeError, ValueError):
                    n_hillslopes = 0

                skipped = (
                    not contrast_name
                    or report_entry.get("status") == "skipped"
                    or n_hillslopes == 0
                )
                if skipped:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": "no_hillslopes"}
                else:
                    skip_reason = self._contrast_landuse_skip_reason(
                        contrast_id,
                        contrast_name,
                        landuse_cache=landuse_cache,
                    )
                    if skip_reason:
                        run_status = "skipped"
                        skip_status = {"skipped": True, "reason": skip_reason}
                    else:
                        run_status = self._contrast_run_status(contrast_id, contrast_name)
                        skip_status = {"skipped": False, "reason": None}

                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": report_entry.get("control_scenario") or control_scenario,
                        "contrast_scenario": report_entry.get("contrast_scenario") or contrast_scenario,
                        "area_label": label,
                        "n_hillslopes": n_hillslopes,
                        "skip_status": skip_status,
                        "run_status": run_status,
                    }
                )

            return {"selection_mode": selection_mode, "items": items}

        if selection_mode == "user_defined_hillslope_groups":
            report_entries = {}
            for entry in self._load_contrast_build_report():
                if entry.get("selection_mode") != "user_defined_hillslope_groups":
                    continue
                contrast_id = entry.get("contrast_id")
                if isinstance(contrast_id, str):
                    try:
                        contrast_id = int(contrast_id)
                    except ValueError:
                        continue
                if isinstance(contrast_id, int):
                    report_entries[contrast_id] = entry

            contrast_labels = getattr(self, "_contrast_labels", None) or {}

            items: List[Dict[str, Any]] = []
            max_id = max(report_entries.keys(), default=0)
            if len(contrast_names) > max_id:
                max_id = len(contrast_names)
            for contrast_id in range(1, max_id + 1):
                contrast_name = contrast_names[contrast_id - 1] if contrast_id - 1 < len(contrast_names) else None
                report_entry = report_entries.get(contrast_id, {})

                control_scenario = report_entry.get("control_scenario")
                contrast_scenario = report_entry.get("contrast_scenario")
                if (control_scenario is None or contrast_scenario is None) and contrast_name:
                    try:
                        control_part, target_part = contrast_name.split("__to__", maxsplit=1)
                        control_scenario = control_part.split(",", maxsplit=1)[0]
                        contrast_scenario = target_part
                    except ValueError:
                        control_scenario = control_scenario or None
                        contrast_scenario = contrast_scenario or None

                group_index = report_entry.get("group_index")
                if group_index in (None, ""):
                    group_index = contrast_labels.get(contrast_id) or contrast_labels.get(str(contrast_id))

                raw_count = report_entry.get("n_hillslopes")
                if raw_count is None:
                    topaz_ids = report_entry.get("topaz_ids")
                    if isinstance(topaz_ids, list):
                        raw_count = len(topaz_ids)
                try:
                    n_hillslopes = int(raw_count) if raw_count is not None else 0
                except (TypeError, ValueError):
                    n_hillslopes = 0

                skipped = (
                    not contrast_name
                    or report_entry.get("status") == "skipped"
                    or n_hillslopes == 0
                )
                if skipped:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": "no_hillslopes"}
                else:
                    skip_reason = self._contrast_landuse_skip_reason(
                        contrast_id,
                        contrast_name,
                        landuse_cache=landuse_cache,
                    )
                    if skip_reason:
                        run_status = "skipped"
                        skip_status = {"skipped": True, "reason": skip_reason}
                    else:
                        run_status = self._contrast_run_status(contrast_id, contrast_name)
                        skip_status = {"skipped": False, "reason": None}

                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": control_scenario,
                        "contrast_scenario": contrast_scenario,
                        "group_index": group_index,
                        "n_hillslopes": n_hillslopes,
                        "skip_status": skip_status,
                        "run_status": run_status,
                    }
                )

            return {"selection_mode": selection_mode, "items": items}

        if selection_mode == "stream_order":
            report_entries = {}
            for entry in self._load_contrast_build_report():
                if entry.get("selection_mode") != "stream_order":
                    continue
                contrast_id = entry.get("contrast_id")
                if isinstance(contrast_id, str):
                    try:
                        contrast_id = int(contrast_id)
                    except ValueError:
                        continue
                if isinstance(contrast_id, int):
                    report_entries[contrast_id] = entry

            items: List[Dict[str, Any]] = []
            max_id = max(report_entries.keys(), default=0)
            if len(contrast_names) > max_id:
                max_id = len(contrast_names)
            for contrast_id in range(1, max_id + 1):
                contrast_name = contrast_names[contrast_id - 1] if contrast_id - 1 < len(contrast_names) else None
                report_entry = report_entries.get(contrast_id, {})

                control_scenario = report_entry.get("control_scenario")
                contrast_scenario = report_entry.get("contrast_scenario")
                if (control_scenario is None or contrast_scenario is None) and contrast_name:
                    try:
                        control_part, target_part = contrast_name.split("__to__", maxsplit=1)
                        control_scenario = control_part.split(",", maxsplit=1)[0]
                        contrast_scenario = target_part
                    except ValueError:
                        control_scenario = control_scenario or None
                        contrast_scenario = contrast_scenario or None

                raw_count = report_entry.get("n_hillslopes")
                try:
                    n_hillslopes = int(raw_count) if raw_count is not None else 0
                except (TypeError, ValueError):
                    n_hillslopes = 0

                skipped = (
                    not contrast_name
                    or report_entry.get("status") == "skipped"
                    or n_hillslopes == 0
                )
                if skipped:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": "no_hillslopes"}
                else:
                    skip_reason = self._contrast_landuse_skip_reason(
                        contrast_id,
                        contrast_name,
                        landuse_cache=landuse_cache,
                    )
                    if skip_reason:
                        run_status = "skipped"
                        skip_status = {"skipped": True, "reason": skip_reason}
                    else:
                        run_status = self._contrast_run_status(contrast_id, contrast_name)
                        skip_status = {"skipped": False, "reason": None}

                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": control_scenario,
                        "contrast_scenario": contrast_scenario,
                        "subcatchments_group": report_entry.get("subcatchments_group"),
                        "n_hillslopes": n_hillslopes,
                        "skip_status": skip_status,
                        "run_status": run_status,
                    }
                )

            return {"selection_mode": selection_mode, "items": items}

        items = []
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            topaz_id = None
            if contrast_name:
                try:
                    control_part, _ = contrast_name.split("__to__", maxsplit=1)
                    _, topaz_id = control_part.split(",", maxsplit=1)
                except ValueError:
                    topaz_id = None
                skip_reason = self._contrast_landuse_skip_reason(
                    contrast_id,
                    contrast_name,
                    landuse_cache=landuse_cache,
                )
                if skip_reason:
                    run_status = "skipped"
                    skip_status = {"skipped": True, "reason": skip_reason}
                else:
                    run_status = self._contrast_run_status(contrast_id, contrast_name)
                    skip_status = {"skipped": False, "reason": None}
            else:
                run_status = "skipped"
                skip_status = {"skipped": True, "reason": "no_hillslopes"}
            items.append(
                {
                    "contrast_id": contrast_id,
                    "topaz_id": str(topaz_id) if topaz_id is not None else None,
                    "skip_status": skip_status,
                    "run_status": run_status,
                }
            )

        return {"selection_mode": selection_mode, "items": items}

    def run_omni_contrasts(self) -> None:
        global OMNI_REL_DIR

        self.logger.info('run_omni_contrasts')

        def _set_dependency_tree_with_retry(tree: ContrastDependency) -> None:
            max_tries = 5
            for attempt in range(max_tries):
                try:
                    with self.locked():
                        self._contrast_dependency_tree = tree
                except NoDbAlreadyLockedError:
                    if attempt + 1 == max_tries:
                        raise
                    time.sleep(1.0)
                else:
                    break

        if not self.contrast_names:
            self.logger.info('  run_omni_contrasts: No contrasts to run')
            if self.contrast_dependency_tree:
                _set_dependency_tree_with_retry({})
            self._clean_stale_contrast_runs([])
            return

        dependency_tree: ContrastDependency = dict(self.contrast_dependency_tree)
        active_contrasts: Set[str] = set()
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]] = {}

        contrast_names: List[Optional[str]] = self.contrast_names or []
        active_ids = [
            contrast_id
            for contrast_id, contrast_name in enumerate(contrast_names, start=1)
            if contrast_name
        ]
        total_contrasts = len(active_ids)

        if total_contrasts == 0:
            self.logger.info("  run_omni_contrasts: No contrasts to run")
            if dependency_tree:
                dependency_tree.clear()
                _set_dependency_tree_with_retry(dependency_tree)
            self._clean_stale_contrast_runs(active_ids)
            return

        for ordinal, contrast_id in enumerate(active_ids, start=1):
            contrast_name = contrast_names[contrast_id - 1]
            if not contrast_name:
                continue
            active_contrasts.add(contrast_name)
            skip_reason = self._contrast_landuse_skip_reason(
                contrast_id,
                contrast_name,
                landuse_cache=landuse_cache,
            )
            if skip_reason:
                self.logger.info(
                    "  run_omni_contrasts: %s skipped (%s)",
                    contrast_name,
                    skip_reason,
                )
                self._clean_contrast_run(contrast_id)
                dependency_tree.pop(contrast_name, None)
                continue
            run_status = self._contrast_run_status(contrast_id, contrast_name)
            if run_status == 'up_to_date':
                self.logger.info('  run_omni_contrasts: %s up-to-date, skipping', contrast_name)
                continue

            try:
                _contrasts = self._load_contrast_sidecar(contrast_id)
            except FileNotFoundError:
                self.logger.info(
                    "  run_omni_contrasts: Missing sidecar for contrast_id=%s, skipping.",
                    contrast_id,
                )
                continue

            self.logger.info(
                "  run_omni_contrasts: Running contrast %s of %s (id=%s): %s",
                ordinal,
                total_contrasts,
                contrast_id,
                contrast_name,
            )
            control_key, contrast_key = self._contrast_scenario_keys(contrast_name)
            omni_wd = _run_contrast(
                str(contrast_id),
                contrast_name,
                _contrasts,
                self.wd,
                self.runid,
                control_key,
                contrast_key,
            )
            self._post_omni_run(omni_wd, contrast_name)

            dependency_entry = self._contrast_dependency_entry(contrast_id, contrast_name)
            dependency_tree[contrast_name] = dependency_entry
            _set_dependency_tree_with_retry(dependency_tree)

        stale = set(dependency_tree.keys()) - active_contrasts
        for contrast_name in stale:
            dependency_tree.pop(contrast_name, None)
        _set_dependency_tree_with_retry(dependency_tree)
        self._clean_stale_contrast_runs(active_ids)

    def run_omni_contrast(self, contrast_id: int) -> str:
        self.logger.info(f'run_omni_contrast {contrast_id}')
        contrast_names = self.contrast_names or []
        if contrast_id < 1 or contrast_id > len(contrast_names):
            raise ValueError(f"Contrast id {contrast_id} is out of range")
        contrast_name = contrast_names[contrast_id - 1]
        if not contrast_name:
            raise ValueError(f"Contrast id {contrast_id} is skipped")
        skip_reason = self._contrast_landuse_skip_reason(contrast_id, contrast_name)
        if skip_reason:
            self.logger.info("run_omni_contrast: %s skipped (%s)", contrast_name, skip_reason)
            self._clean_contrast_run(contrast_id)
            self._remove_contrast_dependency_entry(contrast_name)
            return _join(self.wd, OMNI_REL_DIR, "contrasts", str(contrast_id))
        _contrasts = self._load_contrast_sidecar(contrast_id)
        control_key, contrast_key = self._contrast_scenario_keys(contrast_name)
        omni_wd = _run_contrast(
            str(contrast_id),
            contrast_name,
            _contrasts,
            self.wd,
            self.runid,
            control_key,
            contrast_key,
        )
        self._post_omni_run(omni_wd, contrast_name)
        dependency_entry = self._contrast_dependency_entry(contrast_id, contrast_name)
        self._update_contrast_dependency_tree(contrast_name, dependency_entry)
        return omni_wd

    def contrasts_report(self) -> pd.DataFrame:
        global OMNI_REL_DIR

        def _resolve_loss_out_parquet(output_dir: str) -> str:
            interchange_path = _join(output_dir, 'interchange', 'loss_pw0.out.parquet')
            legacy_path = _join(output_dir, 'loss_pw0.out.parquet')
            return interchange_path if _exists(interchange_path) else legacy_path

        def _ensure_value_columns(frame: pd.DataFrame) -> pd.DataFrame:
            needs_v = 'v' not in frame.columns and 'value' in frame.columns
            needs_value = 'value' not in frame.columns and 'v' in frame.columns
            if not (needs_v or needs_value):
                return frame
            frame = frame.copy()
            if needs_v:
                frame['v'] = frame['value']
            if needs_value:
                frame['value'] = frame['v']
            return frame

        parquet_entries: List[Tuple[int, str, str]] = []

        if not self.contrast_names:
            return pd.DataFrame(columns=['key', 'value', 'v', 'units', 'control_scenario', 'contrast_topaz_id', 'contrast'])

        for contrast_id, contrast_name in enumerate(self.contrast_names or [], start=1):
            if not contrast_name:
                continue
            output_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts', str(contrast_id), 'wepp', 'output')
            parquet_entries.append((contrast_id, contrast_name, _resolve_loss_out_parquet(output_dir)))

        dfs = []
        selection_mode = (self._contrast_selection_mode or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"
        contrast_labels = getattr(self, "_contrast_labels", None) or {}
        for contrast_id, contrast_name, path in parquet_entries:
            if not os.path.isfile(path):
                continue

            try:
                control_part, contrast_scenario = contrast_name.split('__to__')
                control_scenario, topaz_id = control_part.split(',', maxsplit=1)
            except ValueError:
                continue

            df = _ensure_value_columns(pd.read_parquet(path))
            base_control = control_scenario == 'None'
            if base_control:
                control_scenario = str(self.base_scenario)
            df['control_scenario'] = control_scenario
            if selection_mode == "cumulative":
                df['contrast_topaz_id'] = topaz_id
            if selection_mode == "user_defined_areas":
                label = contrast_labels.get(contrast_id)
                if label is None:
                    label = contrast_labels.get(str(contrast_id))
                df['contrast'] = label or str(contrast_id)
            elif selection_mode == "user_defined_hillslope_groups":
                label = contrast_labels.get(contrast_id)
                if label is None:
                    label = contrast_labels.get(str(contrast_id))
                label_value = label or str(contrast_id)
                df["contrast"] = label_value
                try:
                    df["group_index"] = int(label_value)
                except (TypeError, ValueError):
                    df["group_index"] = label_value
            else:
                df['contrast'] = contrast_name
            df['_contrast_name'] = str(contrast_name)
            df['contrast_id'] = contrast_id

            if selection_mode == "stream_order":
                ctrl_df = df[["key", "v", "units"]].drop_duplicates(subset=["key"])
            else:
                if base_control:
                    ctrl_output_dir = _join(self.wd, 'wepp', 'output')
                else:
                    ctrl_output_dir = _join(
                        self.wd,
                        OMNI_REL_DIR,
                        'scenarios',
                        control_scenario,
                        'wepp',
                        'output',
                    )
                ctrl_parquet = _resolve_loss_out_parquet(ctrl_output_dir)
                if not _exists(ctrl_parquet):
                    raise FileNotFoundError(
                        f"Control scenario parquet file '{ctrl_parquet}' does not exist!"
                    )
                ctrl_df = _ensure_value_columns(pd.read_parquet(ctrl_parquet))

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
                self.logger.info(f"WARNING[contrasts_report]: units mismatch for keys -> {sorted(_bad['key'].unique())}\n")

            # Requested measure: control - contrast
            df['control-contrast_v'] = df['control_v'] - df['v']

            dfs.append(df)

        if not dfs:
            # nothing to do
            return pd.DataFrame(columns=['key', 'value', 'v', 'units', 'contrast'])

        combined = pd.concat(dfs, ignore_index=True)
        out_path = _join(self.omni_dir, 'contrasts.out.parquet')
        combined.to_parquet(out_path)
        self._refresh_catalog(os.path.relpath(out_path, self.wd))

        return combined
    
    def _normalize_scenario_key(self, name: Optional[Any]) -> str:
        if isinstance(name, OmniScenario):
            name = str(name)
        if name in (None, 'None'):
            return str(self.base_scenario)
        return str(name)

    def _loss_pw0_path_for_scenario(self, scenario_name: Optional[Any]) -> str:
        global OMNI_REL_DIR
        scenario_key = self._normalize_scenario_key(scenario_name)

        base_path = _join(self.wd, 'wepp', 'output', 'loss_pw0.txt')
        scenario_path = _join(self.wd, OMNI_REL_DIR, 'scenarios', scenario_key, 'wepp', 'output', 'loss_pw0.txt')

        if scenario_key == str(self.base_scenario) and not _exists(scenario_path):
            return base_path

        return scenario_path if _exists(scenario_path) else (base_path if scenario_key == str(self.base_scenario) else scenario_path)

    def _interchange_class_data_path_for_scenario(self, scenario_name: Optional[Any]) -> str:
        global OMNI_REL_DIR
        scenario_key = self._normalize_scenario_key(scenario_name)

        base_path = _join(self.wd, 'wepp', 'output', 'interchange', 'loss_pw0.all_years.class_data.parquet')
        scenario_path = _join(self.wd, OMNI_REL_DIR, 'scenarios', scenario_key, 'wepp', 'output', 'interchange', 'loss_pw0.all_years.class_data.parquet')

        if scenario_key == str(self.base_scenario) and not _exists(scenario_path):
            return base_path

        return scenario_path if _exists(scenario_path) else (base_path if scenario_key == str(self.base_scenario) else scenario_path)

    def _year_set_for_scenario(self, scenario_name: Optional[Any]) -> Optional[Set[int]]:
        path = self._interchange_class_data_path_for_scenario(scenario_name)
        if not os.path.isfile(path):
            return None

        try:
            df = pd.read_parquet(path, columns=['year'])
        except Exception as exc:
            self.logger.debug('Failed to read years for scenario %s from %s: %s', scenario_name, path, exc)
            return None

        if 'year' not in df:
            return None

        try:
            return set(int(y) for y in df['year'].dropna().unique().tolist())
        except Exception as exc:
            self.logger.debug('Failed to normalize years for scenario %s from %s: %s', scenario_name, path, exc)
            return None

    def _scenario_signature(self, scenario_def: ScenarioDef) -> str:
        sanitized: Dict[str, Any] = {}
        for key, value in scenario_def.items():
            if key == 'type' and isinstance(value, OmniScenario):
                sanitized[key] = str(value)
            else:
                sanitized[key] = value
        return json.dumps(sanitized, sort_keys=True, default=str)

    def _scenario_dependency_target(self, scenario: OmniScenario, scenario_def: ScenarioDef) -> Optional[str]:
        if scenario == OmniScenario.Mulch:
            return scenario_def.get('base_scenario')
        return str(self.base_scenario)

    def _contrast_dependencies(self, contrast_name: str) -> ContrastDependencies:
        control_part, target_part = contrast_name.split('__to__')
        control_scenario_raw = control_part.split(',')[0]
        control_key = self._normalize_scenario_key(control_scenario_raw)
        target_key = self._normalize_scenario_key(target_part)

        scenarios = {control_key, target_key}
        dependencies: ContrastDependencies = {}
        for scenario_name in scenarios:
            loss_path = self._loss_pw0_path_for_scenario(scenario_name)
            dependencies[scenario_name] = {
                'loss_path': loss_path,
                'sha1': _hash_file_sha1(loss_path)
            }
        return dependencies

    def _contrast_signature(self, contrast_name: str, contrast_payload: ContrastMapping) -> str:
        payload_serializable = {
            'name': contrast_name,
            'items': sorted((str(k), str(v)) for k, v in contrast_payload.items())
        }
        return hashlib.sha1(json.dumps(payload_serializable, sort_keys=True).encode('utf-8')).hexdigest()

    def _contrast_pair_signature(self, control_key: str, contrast_key: str, area_label: str) -> str:
        return f"{control_key}|{contrast_key}|{area_label}"

    def _load_user_defined_signature_map(self) -> Dict[str, int]:
        signature_map: Dict[str, int] = {}
        for entry in self._load_contrast_build_report():
            if entry.get("selection_mode") != "user_defined_areas":
                continue
            contrast_id = entry.get("contrast_id")
            if isinstance(contrast_id, str):
                try:
                    contrast_id = int(contrast_id)
                except (TypeError, ValueError):
                    continue
            if not isinstance(contrast_id, int):
                continue
            control_key = self._normalize_scenario_key(entry.get("control_scenario"))
            contrast_key = self._normalize_scenario_key(entry.get("contrast_scenario"))
            label = entry.get("area_label")
            if label in (None, ""):
                label = str(contrast_id)
            signature = self._contrast_pair_signature(control_key, contrast_key, str(label))
            signature_map[signature] = contrast_id
        if signature_map:
            return signature_map

        contrast_labels = getattr(self, "_contrast_labels", None) or {}
        contrast_names = self.contrast_names or []
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            if not contrast_name:
                continue
            try:
                control_part, target_part = contrast_name.split("__to__", maxsplit=1)
            except ValueError:
                continue
            control_key = self._normalize_scenario_key(control_part.split(",")[0])
            contrast_key = self._normalize_scenario_key(target_part)
            label = contrast_labels.get(contrast_id) or str(contrast_id)
            signature = self._contrast_pair_signature(control_key, contrast_key, str(label))
            signature_map[signature] = contrast_id
        return signature_map

    def _load_user_defined_hillslope_group_signature_map(self) -> Dict[str, int]:
        signature_map: Dict[str, int] = {}
        for entry in self._load_contrast_build_report():
            if entry.get("selection_mode") != "user_defined_hillslope_groups":
                continue
            contrast_id = entry.get("contrast_id")
            if isinstance(contrast_id, str):
                try:
                    contrast_id = int(contrast_id)
                except (TypeError, ValueError):
                    continue
            if not isinstance(contrast_id, int):
                continue
            group_index = entry.get("group_index")
            if group_index in (None, ""):
                continue
            control_key = self._normalize_scenario_key(entry.get("control_scenario"))
            contrast_key = self._normalize_scenario_key(entry.get("contrast_scenario"))
            signature = self._contrast_pair_signature(control_key, contrast_key, str(group_index))
            signature_map[signature] = contrast_id
        if signature_map:
            return signature_map

        contrast_labels = getattr(self, "_contrast_labels", None) or {}
        contrast_names = self.contrast_names or []
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            if not contrast_name:
                continue
            try:
                control_part, target_part = contrast_name.split("__to__", maxsplit=1)
            except ValueError:
                continue
            control_key = self._normalize_scenario_key(control_part.split(",")[0])
            contrast_key = self._normalize_scenario_key(target_part)
            label = contrast_labels.get(contrast_id) or str(contrast_id)
            signature = self._contrast_pair_signature(control_key, contrast_key, str(label))
            signature_map[signature] = contrast_id
        return signature_map

    def _post_omni_run(self, omni_wd: str, scenario_name: str):
        from wepppy.nodb.core import Ron
        ron = Ron.getInstance(omni_wd)
        try:
            refresh_return_period_events(omni_wd)
        except Exception:
            ron.logger.warning("omni: failed to refresh return-period assets", exc_info=True)
        with ron.locked():
            ron._mods = [mod for mod in ron._mods if mod != 'omni']
            ron._name = scenario_name
            ron.readonly = True

    @property
    def ran_scenarios(self) -> List[str]:
        """
        Returns a list of scenario names that have been run.
        :return: List of scenario names.
        """
        global OMNI_REL_DIR

        ran_scenarios = []
        for scenario_def in self.scenarios:
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if _exists(_join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name, 'wepp', 'output', 'loss_pw0.out.parquet')):
                ran_scenarios.append(_scenario_name)
                
        return ran_scenarios

    def scenario_run_markers(self) -> Dict[str, bool]:
        markers: Dict[str, bool] = {}
        for scenario_def in self.scenarios:
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            markers[scenario_name] = _exists(self._scenario_run_readme_path(scenario_name))
        base_name = str(self.base_scenario)
        if base_name not in markers:
            markers[base_name] = _exists(self._scenario_run_readme_path(base_name))
        return markers
    
    @property
    def use_rq_job_pool_concurrency(self) -> bool:
        return getattr(self, '_use_rq_job_pool_concurrency', True)
    
    @use_rq_job_pool_concurrency.setter
    @nodb_setter
    def use_rq_job_pool_concurrency(self, value: bool):
        self._use_rq_job_pool_concurrency = value

    @property
    def rq_job_pool_max_worker_per_scenario_task(self) -> int:
        cpu_count = os.cpu_count() or 1
        if not self.scenarios:
            return cpu_count
        
        if self.use_rq_job_pool_concurrency:
            return max(cpu_count // len(self.scenarios), 1)

        return cpu_count


    def run_omni_scenarios(self) -> None:
        """
        Runs all the scenarios in two passes to ensure dependencies are met.
        has dependency checking and skips scenarios that are up-to-date.
        1st pass: runs scenarios thar are only dependent on base_scenario (Undisturbed, SBSmap, Uniform*)
        2nd pass: runs scenarios dependent on 1st pass scenarios (Thinning, Mulching)

        Intended as a development hook for testing scenario running without the additional
        complexties of having rq as seperate jobs.
        """
        self.logger.info('run_omni_scenarios')

        if not self.scenarios:
            self.logger.info('  run_omni_scenarios: No scenarios to run')
            raise Exception('No scenarios to run')

        dependency_tree: ScenarioDependency = dict(self.scenario_dependency_tree)

        run_states: List[Dict[str, Any]] = []
        self.scenario_run_state = run_states

        active_scenarios = set()
        processed_scenarios = set()
        base_scenario_key = str(self.base_scenario)

        def dependency_info(scenario_enum: OmniScenario, scenario_def: ScenarioDef):
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            active_scenarios.add(scenario_name)
            dependency_target = self._scenario_dependency_target(scenario_enum, scenario_def)
            dependency_path = self._loss_pw0_path_for_scenario(dependency_target)
            dependency_hash = _hash_file_sha1(dependency_path)
            signature = self._scenario_signature(scenario_def)
            base_years = self._year_set_for_scenario(base_scenario_key)
            scenario_years = self._year_set_for_scenario(scenario_name)
            years_match = (
                base_years is not None and
                scenario_years is not None and
                scenario_years == base_years
            )
            prev_entry = dependency_tree.get(scenario_name)
            up_to_date = (
                prev_entry is not None and
                prev_entry.get('dependency_sha1') == dependency_hash and
                prev_entry.get('signature') == signature
            )
            return scenario_name, dependency_target, dependency_path, dependency_hash, signature, up_to_date, years_match

        # pass 1 scenarios: dependent on base_scenario
        for scenario_def in self.scenarios:
            scenario_enum = OmniScenario.parse(scenario_def.get('type'))
            if scenario_enum == OmniScenario.Mulch:
                continue

            if self.base_scenario != OmniScenario.Undisturbed and \
               scenario_enum in [OmniScenario.Thinning, OmniScenario.PrescribedFire]:
                # defer thinning/prescribed fire until after dependent scenarios build
                continue

            scenario_name, dependency_target, dependency_path, dependency_hash, signature, up_to_date, years_match = \
                dependency_info(scenario_enum, scenario_def)
            processed_scenarios.add(scenario_name)

            target_key = self._normalize_scenario_key(dependency_target)

            if up_to_date and years_match:
                self.logger.info(f'  run_omni_scenarios: {scenario_name} dependency unchanged, skipping')
                ts = time.time()
                dependency_tree[scenario_name] = {
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'signature': signature,
                    'timestamp': ts
                }
                self.scenario_dependency_tree = dependency_tree
                run_states.append({
                    'scenario': scenario_name,
                    'status': 'skipped',
                    'reason': 'dependency_unchanged',
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'timestamp': ts
                })
                self.scenario_run_state = run_states
                continue

            run_reason = 'dependency_changed'
            if up_to_date and not years_match:
                run_reason = 'year_set_mismatch'
                self.logger.info(f'  run_omni_scenarios: {scenario_name} year set mismatch vs base scenario, rerunning')
            else:
                self.logger.info(f'  run_omni_scenarios: {scenario_name}')
            omni_dir, scenario_name = self.run_omni_scenario(scenario_def)
            self._post_omni_run(omni_dir, scenario_name)

            updated_hash = _hash_file_sha1(dependency_path)
            ts = time.time()
            dependency_tree[scenario_name] = {
                'dependency_target': target_key,
                'dependency_path': dependency_path,
                'dependency_sha1': updated_hash,
                'signature': signature,
                'timestamp': ts
            }
            self.scenario_dependency_tree = dependency_tree
            run_states.append({
                'scenario': scenario_name,
                'status': 'executed',
                'reason': run_reason,
                'dependency_target': target_key,
                'dependency_path': dependency_path,
                'dependency_sha1': updated_hash,
                'timestamp': ts
            })
            self.scenario_run_state = run_states

        # pass 2 scenarios: dependent on pass 1
        for scenario_def in self.scenarios:
            scenario_enum = OmniScenario.parse(scenario_def.get('type'))
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if scenario_name in processed_scenarios:
                continue

            scenario_name, dependency_target, dependency_path, dependency_hash, signature, up_to_date, years_match = dependency_info(scenario_enum, scenario_def)
            processed_scenarios.add(scenario_name)

            target_key = self._normalize_scenario_key(dependency_target)

            if up_to_date and years_match:
                self.logger.info(f'  run_omni_scenarios: {scenario_name} dependency unchanged, skipping')
                ts = time.time()
                dependency_tree[scenario_name] = {
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'signature': signature,
                    'timestamp': ts
                }
                self.scenario_dependency_tree = dependency_tree
                run_states.append({
                    'scenario': scenario_name,
                    'status': 'skipped',
                    'reason': 'dependency_unchanged',
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'timestamp': ts
                })
                self.scenario_run_state = run_states
                continue

            run_reason = 'dependency_changed'
            if up_to_date and not years_match:
                run_reason = 'year_set_mismatch'
                self.logger.info(f'  run_omni_scenarios: {scenario_name} year set mismatch vs base scenario, rerunning')
            else:
                self.logger.info(f'  run_omni_scenarios: {scenario_name}')
            omni_dir, scenario_name = self.run_omni_scenario(scenario_def)
            self._post_omni_run(omni_dir, scenario_name)
            
            updated_hash = _hash_file_sha1(dependency_path)
            ts = time.time()
            dependency_tree[scenario_name] = {
                'dependency_target': target_key,
                'dependency_path': dependency_path,
                'dependency_sha1': updated_hash,
                'signature': signature,
                'timestamp': ts
            }
            self.scenario_dependency_tree = dependency_tree
            run_states.append({
                'scenario': scenario_name,
                'status': 'executed',
                'reason': run_reason,
                'dependency_target': target_key,
                'dependency_path': dependency_path,
                'dependency_sha1': updated_hash,
                'timestamp': ts
            })
            self.scenario_run_state = run_states

        stale = set(dependency_tree.keys()) - active_scenarios
        for scenario_name in stale:
            dependency_tree.pop(scenario_name, None)
        self.scenario_dependency_tree = dependency_tree

        self.logger.info('  run_omni_scenarios: compiling hillslope summaries')
        self.compile_hillslope_summaries()
        self.logger.info('  run_omni_scenarios: compiling channel summaries')
        self.compile_channel_summaries()
        self.logger.info('  run_omni_scenarios: compiling scenario report')
        self.scenarios_report()

    def run_omni_scenario(self, scenario_def: ScenarioDef) -> Tuple[str, str]:
        from wepppy.nodb.core import Landuse, Soils, Wepp
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.treatments import Treatments
            
        wd = self.wd
        base_scenario = self.base_scenario
        scenario_name = _scenario_name_from_scenario_definition(scenario_def)

        scenario = OmniScenario.parse(scenario_def.get('type'))
        _scenario = str(scenario)
        omni_base_scenario_name = scenario_def.get('base_scenario', None)

        if scenario in [OmniScenario.PrescribedFire, OmniScenario.Thinning]:  # prescribed fire and thining has to be applied to undisturbed
            if base_scenario != OmniScenario.Undisturbed:  # if the base scenario is SBSmap, we need to clone it from the undisturbed sibling
                omni_base_scenario_name = 'undisturbed'
                self.logger.info(f'  {scenario_name}: omni_base_scenario_name:{omni_base_scenario_name}')

        # change to working dir of parent weppcloud project
        os.chdir(wd)
        
        # assert we know how to handle the scenario
        assert isinstance(scenario, OmniScenario)
        with self.timed(f'  {scenario_name}: _omni_clone({scenario_def}, {wd}, {self.runid})'):
            new_wd = _omni_clone(scenario_def, wd, self.runid)

        if omni_base_scenario_name is not None:
            if not omni_base_scenario_name == str(base_scenario):  # base scenario is either sbs_map or undisturbed
                # e.g. scenario is mulch and omni_base_scenario is uniform_low, uniform_moderate, uniform_high, or sbs_map
                with self.timed(f'  {scenario_name}: _omni_clone_sibling({new_wd}, {omni_base_scenario_name}, {self.runid}, {self.wd})'):
                    _omni_clone_sibling(new_wd, omni_base_scenario_name, self.runid, self.wd)
                
        # get disturbed and landuse instances
        disturbed = Disturbed.getInstance(new_wd)
        landuse = Landuse.getInstance(new_wd)
        soils = Soils.getInstance(new_wd)

        # handle uniform burn severity cases
        if scenario == OmniScenario.UniformLow or \
            scenario == OmniScenario.UniformModerate or \
            scenario == OmniScenario.UniformHigh:

            # identify burn class
            sbs = None
            if scenario == OmniScenario.UniformLow:
                sbs = 1
            elif scenario == OmniScenario.UniformModerate:
                sbs = 2
            elif scenario == OmniScenario.UniformHigh:
                sbs = 3

            self.logger.info(f' {scenario_name}: scenario == uniform burn severity -> {sbs}')

            with self.timed(f'  {scenario_name}: build uniform sbs {sbs}'):
                sbs_fn = disturbed.build_uniform_sbs(int(sbs))
            with self.timed(f'  {scenario_name}: validate sbs {sbs_fn}'):
                disturbed.validate(sbs_fn, mode=1, uniform_severity=int(sbs))
            with self.timed(f'  {scenario_name}: build landuse and soils'):
                landuse.build()
            with self.timed(f'  {scenario_name}: build soils'):
                soils.build(max_workers=self.rq_job_pool_max_worker_per_scenario_task)

        elif scenario == OmniScenario.Undisturbed:
            self.logger.info(f' {scenario_name}: scenario == undisturbed')

            if not self.has_sbs:
                raise Exception('Undisturbed scenario requires a base scenario with sbs')

            with self.timed(f'  {scenario_name}: remove sbs'):
                disturbed.remove_sbs()
            with self.timed(f'  {scenario_name}: build landuse'):
                landuse.build()
            with self.timed(f'  {scenario_name}: build soils'):
                soils.build(max_workers=self.rq_job_pool_max_worker_per_scenario_task)

        elif scenario == OmniScenario.SBSmap:
            self.logger.info(f' {scenario_name}: scenario == sbs')

            sbs_file_path = scenario_def.get('sbs_file_path')
            if not _exists(sbs_file_path):
                raise FileNotFoundError(f"'{sbs_file_path}' not found!")
            
            with self.timed(f'  {scenario_name}: copy sbs to disturbed dir from _limbo'):
                sbs_fn = _split(sbs_file_path)[-1]
                new_sbs_file_path = _join(disturbed.disturbed_dir, sbs_fn)
                shutil.copyfile(sbs_file_path, new_sbs_file_path)
                os.remove(sbs_file_path)

            with self.timed(f'  {scenario_name}: validate sbs {sbs_fn}'):
                disturbed.validate(sbs_fn, mode=0)
            with self.timed(f'  {scenario_name}: build landuse and soils'):
                landuse.build()
            with self.timed(f'  {scenario_name}: build soils'):
                soils.build(max_workers=self.rq_job_pool_max_worker_per_scenario_task)

        elif scenario == OmniScenario.Mulch:
            self.logger.info(f'  {scenario_name}: scenario == mulch')

            assert omni_base_scenario_name is not None, \
                'Mulching scenario requires a base scenario'

            with self.timed(f'  {scenario_name}: applying treatments'):
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
            
            with self.timed(f'  {scenario_name}: build soils'):
                soils.build(max_workers=self.rq_job_pool_max_worker_per_scenario_task)

        elif scenario == OmniScenario.PrescribedFire:
            self.logger.info(f'  {scenario_name}: scenario == prescribed fire')

            # should have cloned undisturbed
            if disturbed.has_sbs:
                raise Exception('Cloned omni scenario should be undisturbed')

            with self.timed(f'  {scenario_name}: build soils'):
                soils.build(max_workers=self.rq_job_pool_max_worker_per_scenario_task)
            
            with self.timed(f'  {scenario_name}: applying treatments'):
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
            self.logger.info(f'  {scenario_name}: scenario == thinning')

            # should have cloned undisturbed
            if disturbed.has_sbs:
                raise Exception('Cloned omni scenario should be undisturbed')

            with self.timed(f'  {scenario_name}: build soils'):
                soils.build(max_workers=self.rq_job_pool_max_worker_per_scenario_task)
            
            with self.timed(f'  {scenario_name}: applying treatments'):
                treatments = Treatments.getInstance(new_wd)
                treatment_key = treatments.treatments_lookup[scenario_name]

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

        landuse.build_managements()
        wepp = Wepp.getInstance(new_wd)

        # use the climate and slope from the parent project's wepp/run directory
                
        # these specify path's relative to the wepp.runs_dir
        # e.g.
        # > runs_dir = '/wc1/runs/lo/looking-glass/_pups/omni/scenarios/undisturbed/wepp/runs'
        # > base_runs_dir = '/wc1/runs/lo/looking-glass/wepp/runs'
        # > os.path.relpath(base_runs_dir, runs_dir)
        # '../../../../../../wepp/runs'

        man_relpath = ''
        cli_relpath = os.path.relpath(self.runs_dir, wepp.runs_dir)  # self is Omni instance in parent. _pups do not have Omni
        slp_relpath = os.path.relpath(self.runs_dir, wepp.runs_dir)
        sol_relpath = ''

        if not cli_relpath.endswith('/'):
            cli_relpath += '/'
        if not slp_relpath.endswith('/'):
            slp_relpath += '/'

        with self.timed(f'  {scenario_name}: prep hillslopes'):
            wepp.prep_hillslopes(man_relpath=man_relpath,
                                cli_relpath=cli_relpath,
                                slp_relpath=slp_relpath,
                                sol_relpath=sol_relpath,
                                max_workers=self.rq_job_pool_max_worker_per_scenario_task)
        with self.timed(f'  {scenario_name}: run hillslopes'):
            wepp.run_hillslopes(man_relpath=man_relpath,
                                cli_relpath=cli_relpath,
                                slp_relpath=slp_relpath,
                                sol_relpath=sol_relpath,
                                max_workers=self.rq_job_pool_max_worker_per_scenario_task)

        with self.timed(f'  {scenario_name}: run hillslope interchange'):
                
            def _normalize_start_year(value):
                try:
                    if value is None:
                        return None
                    if isinstance(value, str) and value.strip() == '':
                        return None
                    return int(value)
                except (TypeError, ValueError):
                    return None

            start_year = None
            climate = Climate.getInstance(new_wd)
            for candidate in (
                getattr(climate, "observed_start_year", None),
                getattr(climate, "future_start_year", None),
            ):
                normalized = _normalize_start_year(candidate)
                if normalized is not None:
                    start_year = normalized
                    break
            run_wepp_hillslope_interchange(wepp.output_dir, start_year=start_year)

        with self.timed(f'  {scenario_name}: prep watershed'):
            wepp.prep_watershed()

        with self.timed(f'  {scenario_name}: run watershed'):
            wepp.run_watershed()
            # run_wepp_watershed_interchange and generate_interchange_documentation is at end of wepp.run_watershed()
            _post_watershed_run_cleanup(wepp)

        return new_wd, scenario_name

    @property
    def has_ran_scenarios(self) -> bool:
        global OMNI_REL_DIR
        if not hasattr(self, 'scenarios'):
            return False

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if not (_exists(_join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name, 'wepp', 'output', 'loss_pw0.out.parquet')) or
                    _exists(_join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name, 'wepp', 'output', 'interchange', 'loss_pw0.out.parquet'))):
                return False

        return True

    @property
    def has_ran_contrasts(self) -> bool:
        global OMNI_REL_DIR
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        if not _exists(contrasts_dir):
            return False

        for entry in os.listdir(contrasts_dir):
            if entry == '_uploads':
                continue
            entry_dir = _join(contrasts_dir, entry)
            if not os.path.isdir(entry_dir):
                continue
            output_dir = _join(entry_dir, 'wepp', 'output')
            if _exists(_join(output_dir, 'interchange', 'loss_pw0.out.parquet')):
                return True
            if _exists(_join(output_dir, 'loss_pw0.out.parquet')):
                return True

        return False

    def scenarios_report(self) -> pd.DataFrame:
        """
        compiles the loss_pw0.out.parquet across the scenarios
        """
        global OMNI_REL_DIR
        parquet_files = {}
        _legacy_path = _join(self.wd, 'wepp', 'output', 'loss_pw0.out.parquet')
        if _exists(_legacy_path):
            parquet_files = {str(self.base_scenario): _legacy_path}
        _interchange_path = _join(self.wd, 'wepp', 'output', 'interchange', 'loss_pw0.out.parquet')
        if _exists(_interchange_path):
            parquet_files = {str(self.base_scenario): _interchange_path}

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            _legacy_path =  _join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name, 'wepp', 'output', 'loss_pw0.out.parquet')
            if _exists(_legacy_path):
                parquet_files[_scenario_name] = _legacy_path
                continue
            _interchange_path =  _join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name, 'wepp', 'output', 'interchange', 'loss_pw0.out.parquet')
            if _exists(_interchange_path):
                parquet_files[_scenario_name] = _interchange_path
                continue
            
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
        out_path = _join(self.omni_dir, 'scenarios.out.parquet')
        combined.to_parquet(out_path)
        self._refresh_catalog(os.path.relpath(out_path, self.wd))

        return combined
    
    def compile_hillslope_summaries(self) -> pd.DataFrame:
        global OMNI_REL_DIR
        from wepppy.wepp.reports import HillSummaryReport

        scenario_wds = {str(self.base_scenario): self.wd}

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            scenario_wds[_scenario_name] = _join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name)

        readonly_rons: List[Ron] = []
        try:
            # HillSummaryReport activates the query engine; temporarily allow writes.
            for wd in scenario_wds.values():
                ron = Ron.getInstance(wd)
                if ron.readonly:
                    ron.readonly = False
                    readonly_rons.append(ron)

            dfs = []
            for scenario, wd in scenario_wds.items():
                loss = Wepp.getInstance(wd).report_loss()
                hill_rpt = HillSummaryReport(loss)
                df = hill_rpt.to_dataframe()  # returns a DataFrame with columns: key, v, units
                df['scenario'] = scenario
                dfs.append(df)
        finally:
            for ron in readonly_rons:
                try:
                    ron.readonly = True
                except Exception as exc:  # pragma: no cover - best-effort restore
                    self.logger.warning('Failed to restore readonly flag for %s: %s', ron.wd, exc)

        combined = pd.concat(dfs, ignore_index=True)

        # Data columns (total 20 columns):
        #  #   Column                                  Non-Null Count  Dtype  
        # ---  ------                                  --------------  -----  
        #  0   Wepp ID                                 2936 non-null   int64  
        #  1   Topaz ID                                2936 non-null   int64  
        #  2   Landuse Key                             2936 non-null   int64  
        #  3   Landuse Description                     2936 non-null   object 
        #  4   Soil Key                                2936 non-null   object 
        #  5   Soil Description                        2936 non-null   object 
        #  6   Length (m)                              2936 non-null   float64
        #  7   Width (m)                               2936 non-null   float64
        #  8   Slope                                   2936 non-null   float64
        #  9   Landuse Area (ha)                       2936 non-null   float64
        #  10  Runoff Depth (mm/yr)                    2936 non-null   float64
        #  11  Lateral Flow Depth (mm/yr)              2936 non-null   float64
        #  12  Baseflow Depth (mm/yr)                  2936 non-null   float64
        #  13  Soil Loss (kg/yr)                       2936 non-null   float64
        #  14  Soil Loss Density (kg/ha/yr)            2936 non-null   float64
        #  15  Sediment Deposition (kg/yr)             2936 non-null   float64
        #  16  Sediment Deposition Density (kg/ha/yr)  2936 non-null   float64
        #  17  Sediment Yield (kg/yr)                  2936 non-null   float64
        #  18  Sediment Yield Density (kg/ha/yr)       2936 non-null   float64
        #  19  scenario                                2936 non-null   object 
        # dtypes: float64(13), int64(3), object(4)

        # 1. Convert depths (mm) over area (ha) → volumes in m³:
        combined['Runoff (m^3)']       = combined['Runoff Depth (mm/yr)']       * combined['Landuse Area (ha)'] * 10
        combined['Lateral Flow (m^3)'] = combined['Lateral Flow Depth (mm/yr)'] * combined['Landuse Area (ha)'] * 10
        combined['Baseflow (m^3)']     = combined['Baseflow Depth (mm/yr)']     * combined['Landuse Area (ha)'] * 10

        # 2. Convert per‐area masses (kg/ha) over area (ha) → total mass in tonnes:
        combined['Soil Loss (t)']           = combined['Soil Loss Density (kg/ha/yr)']            * combined['Landuse Area (ha)'] / 1_000
        combined['Sediment Deposition (t)'] = combined['Sediment Deposition Density (kg/ha/yr)']  * combined['Landuse Area (ha)'] / 1_000
        combined['Sediment Yield (t)']      = combined['Sediment Yield Density (kg/ha/yr)']       * combined['Landuse Area (ha)'] / 1_000

        # Calculate NTU in g/L (combined['Sediment Yield (t)'] * 1_000_000) / (combined['Runoff (m^3)'] * 1_000)
        combined['NTU (g/L)'] = (combined['Sediment Yield (t)'] * 1_000) / (combined['Runoff (m^3)'] + combined['Baseflow (m^3)'] )

        out_path = _join(self.omni_dir, 'scenarios.hillslope_summaries.parquet')
        combined.to_parquet(out_path)
        self._refresh_catalog(os.path.relpath(out_path, self.wd))

        return combined

    def compile_channel_summaries(self) -> pd.DataFrame:
        global OMNI_REL_DIR
        from wepppy.wepp.reports import ChannelSummaryReport

        scenario_wds = {str(self.base_scenario): self.wd}

        for scenario_def in self.scenarios:
            scenario = scenario_def.get('type')
            _scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            scenario_wds[_scenario_name] = _join(self.wd, OMNI_REL_DIR, 'scenarios', _scenario_name)

        readonly_rons: List[Ron] = []
        try:
            # ChannelSummaryReport activates the query engine; temporarily allow writes.
            for wd in scenario_wds.values():
                ron = Ron.getInstance(wd)
                if ron.readonly:
                    ron.readonly = False
                    readonly_rons.append(ron)

            dfs = []
            for scenario, wd in scenario_wds.items():
                loss = Wepp.getInstance(wd).report_loss()
                channel_rpt = ChannelSummaryReport(loss)
                df = channel_rpt.to_dataframe()  # returns a DataFrame with columns: key, v, units
                df['scenario'] = scenario
                dfs.append(df)
        finally:
            for ron in readonly_rons:
                try:
                    ron.readonly = True
                except Exception as exc:  # pragma: no cover - best-effort restore
                    self.logger.warning('Failed to restore readonly flag for %s: %s', ron.wd, exc)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True)


        out_path = _join(self.omni_dir, 'scenarios.channel_summaries.parquet')
        combined.to_parquet(out_path)
        self._refresh_catalog(os.path.relpath(out_path, self.wd))

        return combined

# [x] add NTU
# [ ] add NTU for outlet
# [x] revise mulching cover model
# [ ] add peak runoff (50 yr)
# [x] treat low and moderate severity conditions
# [x] rerun https://wepp.cloud/weppcloud/runs/rlew-indecorous-vest/disturbed9002/
# [x] run contrast scenarios
# [ ] cameron peak in colorado **
# [ ] Blackwood with contrasts ****


# [ ] ability to run solution scenario for PATH with specified treatments across hillslopes
