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
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.errors import nodir_migration_required
from wepppy.wepp.interchange import (
    cleanup_hillslope_sources_for_completed_interchange,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_tc_out_interchange,
)
from wepppy.wepp.reports import refresh_return_period_events
from wepppy.rq.topo_utils import _prune_stream_order
from wepppy.nodb.mods.omni.omni_build_router import OmniBuildRouter
from wepppy.nodb.mods.omni.omni_contrast_build_service import OmniContrastBuildService
from wepppy.nodb.mods.omni.omni_input_parser import OmniInputParsingService
from wepppy.nodb.mods.omni.omni_mode_build_services import OmniModeBuildServices
from wepppy.nodb.mods.omni.omni_scaling_service import OmniScalingService
from wepppy.nodb.mods.omni.omni_artifact_export_service import OmniArtifactExportService
from wepppy.nodb.mods.omni.omni_clone_contrast_service import OmniCloneContrastService
from wepppy.nodb.mods.omni.omni_run_orchestration_service import OmniRunOrchestrationService
from wepppy.nodb.mods.omni.omni_station_catalog_service import OmniStationCatalogService
from wepppy.nodb.mods.omni.omni_state_contrast_mixin import OmniStateContrastMixin

try:
    from wepppy.query_engine import update_catalog_entry as _update_catalog_entry
except ImportError:  # pragma: no cover - optional dependency
    _update_catalog_entry = None

__all__ = [
    'OMNI_REL_DIR',
    'LOGGER',
    'OmniScenario',
    'OmniNoDbLockedException',
    'Omni',
]

OMNI_REL_DIR = '_pups/omni'
USER_DEFINED_CONTRAST_LIMIT = 200

LOGGER = logging.getLogger(__name__)
_OMNI_INPUT_PARSER = OmniInputParsingService()
_OMNI_MODE_BUILD_SERVICES = OmniModeBuildServices()
_OMNI_SCALING_SERVICE = OmniScalingService()
_OMNI_ARTIFACT_EXPORT_SERVICE = OmniArtifactExportService()
_OMNI_CONTRAST_BUILD_SERVICE = OmniContrastBuildService()
_OMNI_CLONE_CONTRAST_SERVICE = OmniCloneContrastService()
_OMNI_RUN_ORCHESTRATION_SERVICE = OmniRunOrchestrationService()
_OMNI_STATION_CATALOG_SERVICE = OmniStationCatalogService()
_OMNI_BUILD_ROUTER = OmniBuildRouter()

CoverValues = Dict[str, float]
RhemRunResult = Tuple[bool, str, float]
ScenarioDef = Dict[str, Any]
ScenarioDependency = Dict[str, Dict[str, Any]]
ObjectiveParameter = namedtuple('ObjectiveParameter', ['topaz_id', 'wepp_id', 'value'])


def _enforce_user_defined_contrast_limit(
    selection_mode: str,
    pair_count: int,
    group_count: int,
    *,
    group_label: str,
    limit: int = USER_DEFINED_CONTRAST_LIMIT,
) -> None:
    if pair_count <= 0 or group_count <= 0:
        return
    total = pair_count * group_count
    if total <= limit:
        return
    labels = {
        "user_defined_areas": "User-defined areas",
        "user_defined_hillslope_groups": "User-defined hillslope groups",
        "stream_order": "Stream-order grouping",
    }
    mode_label = labels.get(selection_mode, selection_mode)
    raise ValueError(
        f"{mode_label} contrasts are limited to {limit}. "
        f"You requested {total} ({pair_count} contrast pairs x {group_count} {group_label}). "
        f"Reduce the number of contrast pairs or {group_label} to {limit} or fewer."
    )


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
    except Exception as exc:  # Boundary: cache cleanup should not break clone teardown.
        LOGGER.warning('Failed to clear NoDb cache for %s (scope=%s): %s', runid, pup_relpath, exc)

    try:
        clear_locks(runid, pup_relpath=pup_relpath)
    except RuntimeError as exc:
        if 'Redis lock client is unavailable' in str(exc):
            LOGGER.debug('Redis lock client unavailable while clearing locks for %s', runid)
        else:
            LOGGER.warning('Failed to clear NoDb locks for %s: %s', runid, exc)
    except Exception as exc:  # Boundary: lock cleanup should not break clone teardown.
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
            run_wepp_watershed_tc_out_interchange(
                wepp.output_dir,
                delete_after_interchange=wepp.delete_after_interchange,
            )

    if wepp.delete_after_interchange:
        cleanup_hillslope_sources_for_completed_interchange(wepp.output_dir)


def _apply_contrast_output_triggers(wepp: Wepp, output_options: Dict[str, bool]) -> None:
    runs_dir = wepp.runs_dir

    chan_inp_path = _join(runs_dir, "chan.inp")
    if output_options.get("chan_out", False):
        if not _exists(chan_inp_path):
            try:
                wepp._prep_channel_input()
            except Exception as exc:
                LOGGER.warning("Failed to prepare chan.inp for contrast outputs: %s", exc)
    else:
        if _exists(chan_inp_path):
            os.remove(chan_inp_path)

    tc_path = _join(runs_dir, "tc.txt")
    if output_options.get("tcr_out", False):
        if not _exists(tc_path):
            with open(tc_path, "w", encoding="ascii", newline="\n") as fp:
                fp.write("")
    else:
        if _exists(tc_path):
            os.remove(tc_path)

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
    wepp_bin: str = 'wepp_dcc52a6',
    output_options: Optional[Dict[str, bool]] = None,
) -> str:
    return _OMNI_CLONE_CONTRAST_SERVICE.run_contrast(
        contrast_id=contrast_id,
        contrast_name=contrast_name,
        contrasts=contrasts,
        wd=wd,
        runid=runid,
        control_scenario_key=control_scenario_key,
        contrast_scenario_key=contrast_scenario_key,
        wepp_bin=wepp_bin,
        output_options=output_options,
    )


def _omni_clone(scenario_def: Dict[str, Any], wd: str, runid: str) -> str:
    return _OMNI_CLONE_CONTRAST_SERVICE.omni_clone(
        scenario_def=scenario_def,
        wd=wd,
        runid=runid,
    )




def _resolve_sibling_scenario_wd(new_wd: str, sibling_name: str) -> Path:
    if not isinstance(sibling_name, str):
        raise ValueError(f"Invalid sibling scenario key: {sibling_name!r}")

    normalized_name = sibling_name.strip()
    if not normalized_name:
        raise ValueError("Sibling scenario key cannot be empty")
    if normalized_name in {".", ".."}:
        raise ValueError(f"Invalid sibling scenario key: {sibling_name!r}")
    if "/" in normalized_name or "\\" in normalized_name:
        raise ValueError(f"Invalid sibling scenario key: {sibling_name!r}")

    scenarios_root = Path(new_wd).resolve().parent
    sibling_wd = (scenarios_root / normalized_name).resolve()
    try:
        sibling_wd.relative_to(scenarios_root)
    except ValueError as exc:
        raise ValueError(
            f"Sibling scenario path escapes scenarios root: {sibling_name!r}"
        ) from exc

    return sibling_wd

def _omni_clone_sibling(new_wd: str, omni_clone_sibling_name: str, runid: str, parent_wd: str) -> None:
    """
    after _omni_clone copies watershed, climates, wepp from the base_scenario (parent)

    we copy the sibling scenario's disturbed, landuse, and soils so that managements/treatments
    are applied to the correct scenario.
    """
    
    sibling_wd_path = _resolve_sibling_scenario_wd(new_wd, omni_clone_sibling_name)
    sibling_wd = str(sibling_wd_path)
    if not _exists(sibling_wd):
        raise FileNotFoundError(f"'{sibling_wd}' not found!")

    pup_relpath = os.path.relpath(new_wd, parent_wd)

    copy_version_for_clone(sibling_wd, new_wd)
    
    def _remove_tree_or_file(path: str) -> None:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
            return
        if os.path.lexists(path):
            os.remove(path)

    # replace disturbed, landuse, and soils
    for nodb_name in ('disturbed.nodb', 'landuse.nodb', 'soils.nodb'):
        _remove_tree_or_file(_join(new_wd, nodb_name))

    # clear cached NoDb payloads and locks after removing the existing nodb files
    _clear_nodb_cache_and_locks(runid, pup_relpath)

    for dirname in ('disturbed', 'landuse', 'soils'):
        _remove_tree_or_file(_join(new_wd, dirname))
    for archive_name in ('landuse.nodir', 'soils.nodir'):
        _remove_tree_or_file(_join(new_wd, archive_name))
    for sidecar_name in ("landuse.parquet", "soils.parquet"):
        _remove_tree_or_file(_join(new_wd, sidecar_name))

    # copy the sibling scenario
    shutil.copyfile(_join(sibling_wd, 'disturbed.nodb'), _join(new_wd, 'disturbed.nodb'))
    shutil.copyfile(_join(sibling_wd, 'landuse.nodb'), _join(new_wd, 'landuse.nodb'))
    shutil.copyfile(_join(sibling_wd, 'soils.nodb'), _join(new_wd, 'soils.nodb'))

    shutil.copytree(_join(sibling_wd, 'disturbed'), _join(new_wd, 'disturbed'))

    for root in ('landuse', 'soils'):
        resolved_root = nodir_resolve(sibling_wd, root, view='effective')
        if resolved_root is None:
            raise FileNotFoundError(f"'{_join(sibling_wd, root)}' not found!")

        if resolved_root.form != 'dir':
            raise nodir_migration_required(
                f"Unexpected NoDir root form for {root}: {resolved_root.form}. "
                "Migration to directory-backed resources is required."
            )

        dst_root = _join(new_wd, root)
        src_root = Path(resolved_root.dir_path)
        if resolved_root.inner_path:
            src_root = src_root / resolved_root.inner_path
        if not src_root.is_dir():
            raise FileNotFoundError(f"'{src_root}' not found!")
        shutil.copytree(str(src_root), dst_root)

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
    except (TypeError, ValueError, KeyError):
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


class Omni(OmniStateContrastMixin, NoDbBase):
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
            self._contrast_batch_size = None
            self._contrast_pairs = []
            self._contrast_output_chan_out = False
            self._contrast_output_tcr_out = False
            self._contrast_output_chnwb = False
            self._contrast_output_soil_pw0 = False
            self._contrast_output_plot_pw0 = False
            self._contrast_output_ebe_pw0 = True

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
        _OMNI_BUILD_ROUTER.build_contrasts(
            self,
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

    def _build_contrasts_router_impl(
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
        _OMNI_BUILD_ROUTER.build_contrasts(
            self,
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

    @property
    def base_scenario(self) -> OmniScenario:
        if self.has_sbs:
            return OmniScenario.SBSmap
        return OmniScenario.Undisturbed

    def _build_contrasts(self) -> None:
        _OMNI_CONTRAST_BUILD_SERVICE.build_contrasts_cumulative_default(self)

    def _build_contrast_ids_geojson(self) -> Optional[str]:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.build_contrast_ids_geojson(self)

    def _build_contrast_ids_geojson_impl(self) -> Optional[str]:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.build_contrast_ids_geojson(self)

    def _resolve_order_reduction_passes(self) -> int:
        return _OMNI_SCALING_SERVICE.resolve_order_reduction_passes(self)

    def _build_contrasts_stream_order(self) -> None:
        _OMNI_CONTRAST_BUILD_SERVICE.build_contrasts_stream_order(self)

    def _build_contrasts_user_defined_hillslope_groups(self) -> None:
        _OMNI_CONTRAST_BUILD_SERVICE.build_contrasts_user_defined_hillslope_groups(self)

    def _build_contrasts_user_defined_areas(self) -> None:
        _OMNI_CONTRAST_BUILD_SERVICE.build_contrasts_user_defined_areas(self)

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
        return _OMNI_BUILD_ROUTER.build_contrasts_dry_run_report(
            self,
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

    def _build_contrasts_dry_run_report_impl(
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
        return _OMNI_BUILD_ROUTER.build_contrasts_dry_run_report(
            self,
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

    def contrast_status_report(self) -> Dict[str, Any]:
        return _OMNI_BUILD_ROUTER.contrast_status_report(self)

    def _contrast_status_report_impl(self) -> Dict[str, Any]:
        return _OMNI_BUILD_ROUTER.contrast_status_report(self)

    def run_omni_contrasts(self) -> None:
        _OMNI_RUN_ORCHESTRATION_SERVICE.run_omni_contrasts(self)

    def run_omni_contrast(self, contrast_id: int, *, rq_job_id: Optional[str] = None) -> str:
        return _OMNI_RUN_ORCHESTRATION_SERVICE.run_omni_contrast(
            self,
            contrast_id,
            rq_job_id=rq_job_id,
        )

    def contrasts_report(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.contrasts_report(self)

    def _contrasts_report_impl(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.contrasts_report(self)

    def _normalize_scenario_key(self, name: Optional[Any]) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.normalize_scenario_key(self, name)

    def _normalize_scenario_key_impl(self, name: Optional[Any]) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.normalize_scenario_key(self, name)

    def _loss_pw0_path_for_scenario(self, scenario_name: Optional[Any]) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.loss_pw0_path_for_scenario(self, scenario_name)

    def _loss_pw0_path_for_scenario_impl(self, scenario_name: Optional[Any]) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.loss_pw0_path_for_scenario(self, scenario_name)

    def _interchange_class_data_path_for_scenario(self, scenario_name: Optional[Any]) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.interchange_class_data_path_for_scenario(self, scenario_name)

    def _interchange_class_data_path_for_scenario_impl(self, scenario_name: Optional[Any]) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.interchange_class_data_path_for_scenario(self, scenario_name)

    def _year_set_for_scenario(self, scenario_name: Optional[Any]) -> Optional[Set[int]]:
        return _OMNI_STATION_CATALOG_SERVICE.year_set_for_scenario(self, scenario_name)

    def _year_set_for_scenario_impl(self, scenario_name: Optional[Any]) -> Optional[Set[int]]:
        return _OMNI_STATION_CATALOG_SERVICE.year_set_for_scenario(self, scenario_name)

    def _scenario_signature(self, scenario_def: ScenarioDef) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.scenario_signature(self, scenario_def)

    def _scenario_signature_impl(self, scenario_def: ScenarioDef) -> str:
        return _OMNI_STATION_CATALOG_SERVICE.scenario_signature(self, scenario_def)

    def _scenario_dependency_target(self, scenario: OmniScenario, scenario_def: ScenarioDef) -> Optional[str]:
        return _OMNI_STATION_CATALOG_SERVICE.scenario_dependency_target(self, scenario, scenario_def)

    def _scenario_dependency_target_impl(self, scenario: OmniScenario, scenario_def: ScenarioDef) -> Optional[str]:
        return _OMNI_STATION_CATALOG_SERVICE.scenario_dependency_target(self, scenario, scenario_def)

    def _contrast_dependencies(self, contrast_name: str) -> ContrastDependencies:
        return _OMNI_STATION_CATALOG_SERVICE.contrast_dependencies(self, contrast_name)

    def _contrast_dependencies_impl(self, contrast_name: str) -> ContrastDependencies:
        return _OMNI_STATION_CATALOG_SERVICE.contrast_dependencies(self, contrast_name)

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
        except Exception:  # Boundary: return-period refresh should not block run finalization.
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
        _OMNI_RUN_ORCHESTRATION_SERVICE.run_omni_scenarios(self)

    def run_omni_scenario(self, scenario_def: ScenarioDef) -> Tuple[str, str]:
        return _OMNI_RUN_ORCHESTRATION_SERVICE.run_omni_scenario(self, scenario_def)

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
        return _OMNI_ARTIFACT_EXPORT_SERVICE.scenarios_report(self)

    def _scenarios_report_impl(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.scenarios_report(self)

    def compile_hillslope_summaries(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.compile_hillslope_summaries(self)

    def _compile_hillslope_summaries_impl(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.compile_hillslope_summaries(self)

    def compile_channel_summaries(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.compile_channel_summaries(self)

    def _compile_channel_summaries_impl(self) -> pd.DataFrame:
        return _OMNI_ARTIFACT_EXPORT_SERVICE.compile_channel_summaries(self)

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
