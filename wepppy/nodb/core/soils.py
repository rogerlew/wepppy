# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Soil data management and WEPP soil parameter file generation.

This module provides the Soils NoDb controller for managing soil data acquisition,
processing, and WEPP .sol file generation. It integrates with USDA soil databases
(SSURGO, STATSGO) and the Rosetta pedotransfer function model.

Key Components:
    Soils: NoDb controller for soil data management
    SoilsMode: Enum defining soil data sources
    
Soil Data Sources:
    - SSURGO: Soil Survey Geographic Database (high resolution)
    - STATSGO: State Soil Geographic Database (coarse resolution)
    - Single: Uniform soil across watershed
    - Gridded: Custom gridded soil data
    
Processing Pipeline:
    1. Acquire spatial soil maps (raster or vector)
    2. Extract dominant soil types per subcatchment
    3. Query soil database for hydraulic properties
    4. Apply Rosetta pedotransfer functions if needed
    5. Generate WEPP .sol files per hillslope

Example:
    >>> from wepppy.nodb.core import Soils, SoilsMode
    >>> soils = Soils.getInstance('/wc1/runs/my-run')
    >>> soils.mode = SoilsMode.SSURGO
    >>> soils.build_soils()
    >>> print(soils.domsoil_d)  # Dominant soil by subcatchment

See Also:
    - wepppy.soils.ssurgo: SSURGO database integration
    - wepppy.wepp.soils: WEPP soil file handling
    - rosetta: Pedotransfer function model

Note:
    Soil files (.sol) are generated per hillslope as p{wepp_id}.sol
    in the {wd}/wepp/runs/ directory.
    
Warning:
    Soil assignment requires completed watershed abstraction.
    SSURGO data availability varies by region.
"""

import os
import inspect
import json
import tempfile

from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path
import shutil
from enum import IntEnum
from copy import deepcopy

from concurrent.futures import wait, FIRST_COMPLETED

from collections import Counter

# non-standard
import pandas as pd
from deprecated import deprecated
import duckdb

# wepppy
from wepppy.soils.ssurgo import (
    SSURGO_PROJECT_CACHE_FILENAME,
    STATSGO_PROJECT_CACHE_FILENAME,
    SurgoMap,
    StatsgoSpatial,
    SurgoSoilCollection,
    SoilSummary,
    SsurgoRequestError,
    surgo_cache_metadata_path,
)
from wepppy.topo.watershed_abstraction.support import is_channel
from wepppy.all_your_base.geo import read_raster, raster_stacker
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.all_your_base.geo.vrt import build_windowed_vrt_from_window
from wepppy.wepp.soils.soilsdb import load_db, get_soil

from wepppy.nodb.base import (
    NoDbBase,
    TriggerEvents, nodb_setter,
    createProcessPoolExecutor,
)

from .ron import Ron
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.nodb.duckdb_agents import (
    get_soil_sub_summary,
    get_soil_subs_summary
)
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path

from wepppy.query_engine import update_catalog_entry

__all__ = [
    'SoilsNoDbLockedException',
    'SoilsMode',
    'Soils',
]


try:
    import wepppyo3
    from wepppyo3.raster_characteristics import identify_mode_single_raster_key
    from wepppyo3.raster_characteristics import identify_mode_intersecting_raster_keys
    from wepppyo3.raster_characteristics import local_mukey_candidates
except ImportError:
    print("wepppyo3 not found, using fallback methods.")
    wepppyo3 = None

class SoilsNoDbLockedException(Exception):
    pass


class SoilsMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1
    SingleDb = 2
    UserDefined = 2
    RRED_Unburned = 3
    RRED_Burned = 4
    SpatialAPI = 9


def _clear_directory_preserving_symlink_mount(path: str) -> None:
    """Clear directory contents without deleting an active NoDir projection symlink."""
    if not os.path.lexists(path):
        return

    if os.path.islink(path):
        resolved = os.path.realpath(path)
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Expected directory symlink target for soils root: {path}")
        run_root = os.path.dirname(os.path.abspath(path))
        managed_projection_roots = (
            os.path.join(run_root, ".nodir", "lower", "soils"),
            os.path.join(run_root, ".nodir", "upper", "soils"),
        )

        def _is_managed_projection_target() -> bool:
            for managed_root in managed_projection_roots:
                managed_abs = os.path.abspath(managed_root)
                try:
                    if os.path.commonpath([resolved, managed_abs]) == managed_abs:
                        return True
                except ValueError:
                    continue
            return False

        if not _is_managed_projection_target():
            # Unmanaged symlink: drop only the link and preserve target contents.
            os.unlink(path)
            return

        for name in os.listdir(resolved):
            candidate = os.path.join(resolved, name)
            if os.path.isdir(candidate) and not os.path.islink(candidate):
                shutil.rmtree(candidate)
            else:
                os.unlink(candidate)
        return

    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


# noinspection PyPep8Naming
class Soils(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Soils'
    
    _js_decode_replacements = (
        ("\"simple_texture\"", "\"_simple_texture\""),
        ("\"texture\"", "\"_texture\""),
        ("\"clay_pct\"", "\"_old_clay_pct\""),
        ("\"sand\"", "\"_old_sand\""),
        ("\"avke\"", "\"_old_avke\""),
        ("\"ll\"", "\"_old_ll\""),
        ("\"liquid_limit\"", "\"_old_liquid_limit\""),
        ("\"clay\"", "\"_old_clay\""),
    )

    filename = 'soils.nodb'
    
    def __init__(
        self, 
        wd: str, 
        cfg_fn: str, 
        run_group: Optional[str] = None, 
        group_name: Optional[str] = None
    ) -> None:
        super(Soils, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._mode = SoilsMode.Gridded
            self._single_selection = 0
            self._single_dbselection = None

            self._ssurgo_db = self.config_get_path('soils', 'ssurgo_db')

            self.domsoil_d = None  # topaz_id keys
            self.ssurgo_domsoil_d = None
            self.raw_ssurgo_domsoil_d = None
            self.ssurgo_substitution_d = {}
            self.ssurgo_candidate_shadow_d = {}
            self.ssurgo_candidate_preparation = {"status": "not_attempted", "affected_hillslopes": 0}

            self.soils = None
            self._subs_summary = None
            self._chns_summary = None
            
            self._initial_sat = 0.75
            self._ksflag = self.config_get_bool('soils', 'ksflag')
            self._clip_soils = self.config_get_bool('soils', 'clip_soils', False)
            self._clip_soils_depth = self.config_get_float('soils', 'clip_soils_depth', 1000)
            self._clip_soils_minimum = self.config_get_bool('soils', 'clip_soils_minimum', False)
            self._clip_soils_minimum_depth = self.config_get_float('soils', 'clip_soils_minimum_depth', 0)
            self._clear_ssurgo_cache_on_rebuild = False
            self._rosetta_wc_fc_from_disturbed_bd_override = self.config_get_bool(
                'soils',
                'rosetta_wc_fc_from_disturbed_bd_override',
                False,
            )
            self._soils_is_vrt = False

            self._soils_map = self.config_get_path('soils', 'soils_map', None)

    @classmethod
    def _post_instance_loaded(cls, instance: "Soils") -> "Soils":
        instance = super()._post_instance_loaded(instance)
        instance._soils_map = instance._expand_config_path_tokens(getattr(instance, "_soils_map", None))
        instance._ssurgo_db = instance._expand_config_path_tokens(getattr(instance, "_ssurgo_db", None))
        if not hasattr(instance, "_clear_ssurgo_cache_on_rebuild"):
            instance._clear_ssurgo_cache_on_rebuild = False
        if not hasattr(instance, "raw_ssurgo_domsoil_d"):
            instance.raw_ssurgo_domsoil_d = None
        if (
            not hasattr(instance, "ssurgo_substitution_d")
            or instance.ssurgo_substitution_d is None
        ):
            instance.ssurgo_substitution_d = {}
        if not hasattr(instance, "ssurgo_candidate_shadow_d") or instance.ssurgo_candidate_shadow_d is None:
            instance.ssurgo_candidate_shadow_d = {}
        if not hasattr(instance, "ssurgo_candidate_preparation") or instance.ssurgo_candidate_preparation is None:
            instance.ssurgo_candidate_preparation = {"status": "not_attempted", "affected_hillslopes": 0}

        soils = getattr(instance, "soils", None)
        if not isinstance(soils, dict):
            return instance

        canonical_soils_dir = instance.soils_dir
        for summary in soils.values():
            if summary is None:
                continue
            if hasattr(summary, "soils_dir"):
                summary.soils_dir = canonical_soils_dir
            if hasattr(summary, "_weppsoilutil"):
                try:
                    delattr(summary, "_weppsoilutil")
                except AttributeError:
                    pass

        return instance

    @property
    def clip_soils(self) -> bool:
        return getattr(self, '_clip_soils', False)

    @clip_soils.setter
    @nodb_setter
    def clip_soils(self, value: bool) -> None:
        self._clip_soils = value

    @property
    def clip_soils_depth(self) -> float:
        return getattr(self, '_clip_soils_depth', 1000)

    @clip_soils_depth.setter
    @nodb_setter
    def clip_soils_depth(self, value: float) -> None:
        self._clip_soils_depth = value

    @property
    def clip_soils_minimum(self) -> bool:
        return getattr(self, '_clip_soils_minimum', False)

    @clip_soils_minimum.setter
    @nodb_setter
    def clip_soils_minimum(self, value: bool) -> None:
        self._clip_soils_minimum = value

    @property
    def clip_soils_minimum_depth(self) -> float:
        return getattr(self, '_clip_soils_minimum_depth', 0)

    @clip_soils_minimum_depth.setter
    @nodb_setter
    def clip_soils_minimum_depth(self, value: float) -> None:
        self._clip_soils_minimum_depth = value

    @property
    def initial_sat(self) -> float:
        return getattr(self, '_initial_sat', 0.75)

    @initial_sat.setter
    @nodb_setter
    def initial_sat(self, value: float) -> None:
        self._initial_sat = value

    @property
    def clear_ssurgo_cache_on_rebuild(self) -> bool:
        return bool(getattr(self, '_clear_ssurgo_cache_on_rebuild', False))

    @clear_ssurgo_cache_on_rebuild.setter
    @nodb_setter
    def clear_ssurgo_cache_on_rebuild(self, value: bool) -> None:
        self._clear_ssurgo_cache_on_rebuild = bool(value)

    @property
    def rosetta_wc_fc_from_disturbed_bd_override(self) -> bool:
        return bool(getattr(self, '_rosetta_wc_fc_from_disturbed_bd_override', False))

    @rosetta_wc_fc_from_disturbed_bd_override.setter
    @nodb_setter
    def rosetta_wc_fc_from_disturbed_bd_override(self, value: bool) -> None:
        self._rosetta_wc_fc_from_disturbed_bd_override = bool(value)

    def snapshot_wepp_run_payload_updates(self) -> dict[str, Any]:
        """Capture mutable WEPP payload fields for rollback handling."""

        return {
            "_clip_soils": getattr(self, "_clip_soils", False),
            "_clip_soils_depth": getattr(self, "_clip_soils_depth", 1000),
            "_clip_soils_minimum": getattr(self, "_clip_soils_minimum", False),
            "_clip_soils_minimum_depth": getattr(self, "_clip_soils_minimum_depth", 0),
            "_rosetta_wc_fc_from_disturbed_bd_override": bool(
                getattr(self, "_rosetta_wc_fc_from_disturbed_bd_override", False)
            ),
            "_initial_sat": getattr(self, "_initial_sat", 0.75),
        }

    def restore_wepp_run_payload_updates(self, snapshot: dict[str, Any]) -> None:
        """Restore WEPP payload fields from a prior snapshot."""

        self._clip_soils = bool(snapshot["_clip_soils"])
        self._clip_soils_depth = snapshot["_clip_soils_depth"]
        self._clip_soils_minimum = bool(snapshot["_clip_soils_minimum"])
        self._clip_soils_minimum_depth = snapshot["_clip_soils_minimum_depth"]
        self._rosetta_wc_fc_from_disturbed_bd_override = bool(
            snapshot["_rosetta_wc_fc_from_disturbed_bd_override"]
        )
        self._initial_sat = snapshot["_initial_sat"]

    def stage_wepp_run_payload_updates(
        self,
        *,
        clip_soils: Optional[bool] = None,
        clip_soils_depth: Optional[float] = None,
        clip_soils_minimum: Optional[bool] = None,
        clip_soils_minimum_depth: Optional[float] = None,
        rosetta_wc_fc_from_disturbed_bd_override: Optional[bool] = None,
        initial_sat: Optional[float] = None,
    ) -> bool:
        """Apply WEPP payload fields in-memory without locking or persistence."""

        has_updates = any(
            value is not None
            for value in (
                clip_soils,
                clip_soils_depth,
                clip_soils_minimum,
                clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat,
            )
        )
        if not has_updates:
            return False

        if clip_soils is not None:
            self._clip_soils = bool(clip_soils)
        if clip_soils_depth is not None:
            self._clip_soils_depth = clip_soils_depth
        if clip_soils_minimum is not None:
            self._clip_soils_minimum = bool(clip_soils_minimum)
        if clip_soils_minimum_depth is not None:
            self._clip_soils_minimum_depth = clip_soils_minimum_depth
        if rosetta_wc_fc_from_disturbed_bd_override is not None:
            self._rosetta_wc_fc_from_disturbed_bd_override = bool(
                rosetta_wc_fc_from_disturbed_bd_override
            )
        if initial_sat is not None:
            self._initial_sat = initial_sat
        return True

    def finalize_grouped_wepp_run_payload_updates(self) -> None:
        """Persist grouped WEPP payload updates while lock ownership is external."""

        self.dump()

    def post_finalize_grouped_wepp_run_payload_updates(self, *, validate: bool = True) -> None:
        """Run post-dump semantics after grouped dump/unlock completes."""

        if validate:
            type(self).getInstance(self.wd)
        type(self)._post_dump_and_unlock(self)

    def apply_wepp_run_payload_updates(
        self,
        *,
        clip_soils: Optional[bool] = None,
        clip_soils_depth: Optional[float] = None,
        clip_soils_minimum: Optional[bool] = None,
        clip_soils_minimum_depth: Optional[float] = None,
        rosetta_wc_fc_from_disturbed_bd_override: Optional[bool] = None,
        initial_sat: Optional[float] = None,
    ) -> None:
        """Apply WEPP payload soil mutations in a single lock scope."""
        has_updates = any(
            value is not None
            for value in (
                clip_soils,
                clip_soils_depth,
                clip_soils_minimum,
                clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat,
            )
        )
        if not has_updates:
            return

        with self.locked():
            self.stage_wepp_run_payload_updates(
                clip_soils=clip_soils,
                clip_soils_depth=clip_soils_depth,
                clip_soils_minimum=clip_soils_minimum,
                clip_soils_minimum_depth=clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override=rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat=initial_sat,
            )

    @property
    def ksflag(self) -> bool:
        if not hasattr(self, '_ksflag'):
            return True

        return self._ksflag

    @ksflag.setter
    @nodb_setter
    def ksflag(self, value: bool) -> None:
        assert value in (True, False)
        self._ksflag = value

    @property
    def mode(self) -> SoilsMode:
        return self._mode

    @mode.setter
    @nodb_setter
    def mode(self, value: Any) -> None:
        if isinstance(value, SoilsMode):
            self._mode = value
        elif isinstance(value, int):
            self._mode = SoilsMode(value)
        else:
            raise ValueError('most be SoilsMode or int')
        
    @property
    def soils_map(self) -> Optional[str]:
        return self._expand_config_path_tokens(getattr(self, '_soils_map', None))

    @property
    def single_selection(self) -> int:
        return self._single_selection

    @single_selection.setter
    @nodb_setter
    def single_selection(self, mukey: int) -> None:
        self._single_selection = mukey

    @property
    def single_dbselection(self) -> Optional[str]:
        return getattr(self, '_single_dbselection', None)

    @single_dbselection.setter
    @nodb_setter
    def single_dbselection(self, sol: str) -> None:
        self._single_dbselection = sol
        
    @property
    def has_soils(self) -> bool:
        mode = self.mode
        assert isinstance(mode, SoilsMode)

        if mode == SoilsMode.Undefined:
            return False
        else:
            return self.domsoil_d is not None

    @property
    def soils_is_vrt(self) -> bool:
        return bool(getattr(self, "_soils_is_vrt", False))

    @property
    def soils_dir(self) -> str:
        return _join(self.wd, "soils")

    @property
    def ssurgo_cache_db_path(self) -> str:
        return _join(self.soils_dir, SSURGO_PROJECT_CACHE_FILENAME)

    @property
    def statsgo_cache_db_path(self) -> str:
        return _join(self.soils_dir, STATSGO_PROJECT_CACHE_FILENAME)

    def _project_surgo_cache_path(self, *, use_statsgo: bool = False) -> str:
        os.makedirs(self.soils_dir, exist_ok=True)
        if use_statsgo:
            return self.statsgo_cache_db_path
        return self.ssurgo_cache_db_path

    def _prepare_project_surgo_cache(self, *, use_statsgo: bool = False) -> str:
        cache_path = self._project_surgo_cache_path(use_statsgo=use_statsgo)
        if self.clear_ssurgo_cache_on_rebuild:
            self._clear_project_surgo_cache(use_statsgo=use_statsgo)
        return cache_path

    def _clear_project_surgo_cache(self, *, use_statsgo: bool = False) -> None:
        cache_path = self._project_surgo_cache_path(use_statsgo=use_statsgo)
        wd_root = os.path.realpath(self.wd)
        soils_dir = os.path.realpath(self.soils_dir)
        try:
            soils_under_project = os.path.commonpath([wd_root, soils_dir]) == wd_root
        except ValueError as exc:
            raise ValueError(f"Invalid project soils directory: {self.soils_dir}") from exc
        if not soils_under_project:
            raise ValueError(f"Refusing to clear cache outside project directory: {self.soils_dir}")

        for candidate in (
            cache_path,
            f"{cache_path}-wal",
            f"{cache_path}-shm",
            surgo_cache_metadata_path(cache_path),
        ):
            abs_candidate = os.path.abspath(candidate)
            real_candidate = os.path.realpath(candidate)
            try:
                candidate_under_soils = os.path.commonpath([soils_dir, real_candidate]) == soils_dir
            except ValueError as exc:
                raise ValueError(f"Invalid SSURGO cache path: {candidate}") from exc
            if not candidate_under_soils:
                raise ValueError(f"Refusing to clear cache outside soils directory: {candidate}")

            if not os.path.lexists(abs_candidate):
                continue
            if os.path.isdir(abs_candidate) and not os.path.islink(abs_candidate):
                raise IsADirectoryError(
                    f"Refusing to remove directory while clearing SSURGO cache: {abs_candidate}"
                )
            os.unlink(abs_candidate)

    @property
    def ssurgo_fn(self) -> str:
        ext = "vrt" if self.soils_is_vrt else "tif"
        return _join(self.soils_dir, f"ssurgo.{ext}")

    @property
    def domsoil_fn(self) -> str:
        return _join(self.soils_dir, "soilscov.asc")

    @property
    def legend(self) -> List[str]:
        mukeys = sorted(set(self.domsoil_d.values()))
        soils = [self.soils[mukey] for mukey in mukeys]
        descs = [soil.desc for soil in soils]
        colors = [soil.color for soil in soils]

        return list(zip(mukeys, descs, colors))

    #
    # build
    #
    def clean(self) -> None:

        soils_dir = self.soils_dir
        _clear_directory_preserving_symlink_mount(soils_dir)
        os.makedirs(soils_dir, exist_ok=True)
        self._soils_is_vrt = False
        if not self.islocked():
            with self.locked():
                self._soils_is_vrt = False

    def symlink_soils_map(
        self,
        soils_fn: str,
        *,
        as_cropped_vrt: bool = False,
        crop_window: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        soils_src = os.path.abspath(soils_fn)
        if not _exists(soils_src):
            raise FileNotFoundError(f"Soils map does not exist: {soils_src}")

        os.makedirs(self.soils_dir, exist_ok=True)
        use_vrt = bool(as_cropped_vrt)
        ron = self.ron_instance
        if use_vrt:
            if crop_window is None:
                crop_window = ron.crop_window
            if crop_window is None:
                raise ValueError("Crop window cannot be identified for as_cropped_vrt=True")

        self._soils_is_vrt = use_vrt
        dest = self.ssurgo_fn

        if use_vrt:
            build_windowed_vrt_from_window(
                soils_src,
                dest,
                crop_window,
                reference_geotransform=ron.crop_reference_geotransform,
                reference_shape=ron.crop_reference_shape,
            )
        else:
            if os.path.lexists(dest):
                if os.path.islink(dest):
                    existing = os.path.realpath(dest)
                    if existing != soils_src:
                        os.unlink(dest)
                else:
                    if os.path.samefile(dest, soils_src):
                        pass
                    else:
                        raise FileExistsError(
                            f"Soils map path already exists and is not a symlink: {dest}"
                        )

            if not os.path.lexists(dest):
                os.symlink(soils_src, dest)

            prj_src = os.path.splitext(soils_src)[0] + ".prj"
            if _exists(prj_src):
                prj_dest = os.path.splitext(dest)[0] + ".prj"
                if os.path.lexists(prj_dest):
                    if os.path.islink(prj_dest):
                        existing = os.path.realpath(prj_dest)
                        if existing != prj_src:
                            os.unlink(prj_dest)
                    else:
                        if os.path.samefile(prj_dest, prj_src):
                            pass
                        else:
                            raise FileExistsError(
                                "Soils projection path already exists and is not a symlink: "
                                f"{prj_dest}"
                            )
                if not os.path.lexists(prj_dest):
                    os.symlink(prj_src, prj_dest)

        base = os.path.abspath(self.wd)
        if os.path.commonpath([base, soils_src]) == base:
            update_catalog_entry(self.wd, dest)
        else:
            self.logger.info(
                "Skipping catalog update for external soils symlink: %s",
                soils_src,
            )

        if not self.islocked():
            with self.locked():
                self._soils_is_vrt = use_vrt

    @property
    def ssurgo_db(self) -> Optional[str]:
        path = getattr(self, '_ssurgo_db', self.config_get_str('soils', 'ssurgo_db'))
        path = self._expand_config_path_tokens(path)
        return path.replace('gNATSGO', 'gNATSGSO')

    @ssurgo_db.setter
    @nodb_setter
    def ssurgo_db(self, value: str) -> None:
        self._ssurgo_db = value

    def build_chile(
        self, 
        initial_sat: Optional[float] = None, 
        ksflag: Optional[bool] = None
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(initial_sat={initial_sat}, ksflag={ksflag})')

        from wepppy.locales.chile.soils import get_soil_fn
        from wepppy.wepp.soils.utils import WeppSoilUtil

        wd = self.wd
        watershed = self.watershed_instance
        if not watershed.is_abstracted:
            from wepppy.nodb.core.watershed import WatershedNotAbstractedError
            raise WatershedNotAbstractedError()

        ron = self.ron_instance
        _map = ron.map 

        soils_dir = self.soils_dir

        with self.locked():
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = bool(ksflag)

            self._soils_is_vrt = False
            ssurgo_fn = self.ssurgo_fn
            wmesque_retrieve(self.soils_map, _map.extent, ssurgo_fn, _map.cellsize, v=self.wmesque_version)
            update_catalog_entry(self.wd, ssurgo_fn)

            domsoil_d = identify_mode_single_raster_key(
                key_fn=watershed.subwta, parameter_fn=ssurgo_fn, ignore_channels=True, ignore_keys=set())
            domsoil_d = {str(k): str(v) for k, v in domsoil_d.items()}

            self.logger.info(f'domsoil_d: {repr(domsoil_d)}')

            soils = {}
            for topaz_id in watershed._subs_summary:
                mukey = domsoil_d.get(str(topaz_id), None)

                if mukey is None:
                    mukey = domsoil_d[str(topaz_id)] = '1'

                src_sol_fn, soil_id = get_soil_fn(mukey)
                sol_fn = _join(soils_dir, f'{soil_id}.sol')
                if not _exists(sol_fn):
                    shutil.copyfile(src_sol_fn, sol_fn)

                if mukey not in soils:
                    wsu = WeppSoilUtil(sol_fn)
                    soils[mukey] = SoilSummary(
                        mukey=mukey,
                        fname=f'{soil_id}.sol',
                        soils_dir=soils_dir,
                        build_date=str(datetime.now()),
                        desc=wsu.obj['ofes'][0]['slid'],
                        pct_coverage=0.0
                    )

            self.logger.info(repr(soils))

            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.hillslope_area(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def build_isric(
        self, 
        initial_sat: Optional[float] = None, 
        ksflag: Optional[bool] = None,
        max_workers: int = 16
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(initial_sat={initial_sat}, ksflag={ksflag})')
        from wepppy.locales.earth.soils.isric import ISRICSoilData

#        if max_workers < 1:
#            max_workers = 1
#        if max_workers > 8:
#            max_workers = 8

        max_workers = 1

        wd = self.wd
        watershed = self.watershed_instance
        if not watershed.is_abstracted:
            from wepppy.nodb.core.watershed import WatershedNotAbstractedError
            raise WatershedNotAbstractedError()

        ron = self.ron_instance

        soils_dir = self.soils_dir

        with self.locked():
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = bool(ksflag)

            isric = ISRICSoilData(soils_dir)
            with self.timed('  Fetching ISRIC data'):
                isric.fetch(ron.map.extent, status_channel=self._status_channel)

            domsoil_d = {}
            soils = {}
            valid_k_counts = Counter()

            self.logger.info('building soils...')

            # Prepare arguments for multiprocessing

            # Execute in parallel
            with createProcessPoolExecutor(max_workers=max_workers, logger=self.logger, prefer_spawn=True) as executor:
                futures = []
                for topaz_id, (lng, lat) in watershed.centroid_hillslope_iter():
                    futures.append(
                        executor.submit(
                            isric.build_soil, lng, lat,
                            ksflag=self._ksflag, ini_sat=self._initial_sat,
                            meta=dict(topaz_id=topaz_id)))

                domsoil_d = {}
                soils = {}
                valid_k_counts = Counter()

                futures_n = len(futures)
                count = 0
                pending = set(futures)
                while pending:
                    done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

                    if not done:
                        self.logger.warning('  ISRIC soil building still running after 30 seconds; continuing to wait.')
                        continue

                    for future in done:
                        try:
                            mukey, soil_summary, meta = future.result()
                            count += 1
                            self.logger.info(f'  {count}/{futures_n} ISRIC soil building completed, mukey={mukey}')
                        except Exception as exc:
                            # Concurrency boundary: surface worker failures after canceling outstanding futures.
                            self.logger.error(
                                "  ISRIC soil building failed with an error: %s",
                                exc,
                                exc_info=True,
                            )
                            for remaining in pending:
                                remaining.cancel()
                            raise

                        topaz_id = meta['topaz_id']
                        if mukey is not None:
                            domsoil_d[str(topaz_id)] = mukey
                            valid_k_counts[mukey] += watershed.hillslope_area(topaz_id)
                            soils[mukey] = soil_summary


            # now assign hillslopes with invalid mukeys the most common valid mukey
            most_common_k = valid_k_counts.most_common()[0][0]
            for topaz_id in watershed._subs_summary:
                if topaz_id not in domsoil_d:
                   domsoil_d[topaz_id] = most_common_k

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.hillslope_area(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def build_statsgo(
        self, 
        initial_sat: Optional[float] = None, 
        ksflag: Optional[bool] = None
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(initial_sat={initial_sat}, ksflag={ksflag})')

        wd = self.wd
        watershed = self.watershed_instance
        if not watershed.is_abstracted:
            from wepppy.nodb.core.watershed import WatershedNotAbstractedError
            raise WatershedNotAbstractedError()

        soils_dir = self.soils_dir

        with self.locked():
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = bool(ksflag)

            statsgoSpatial = StatsgoSpatial()
            watershed = self.watershed_instance

            domsoil_d = {}
            for topaz_id, (lng, lat) in watershed.centroid_hillslope_iter():
                mukey = statsgoSpatial.identify_mukey_point(lng, lat)
                domsoil_d[str(topaz_id)] = str(mukey)

            mukeys = set(domsoil_d.values())
            surgo_c = SurgoSoilCollection(
                mukeys,
                use_statsgo=True,
                cache_db_path=self._prepare_project_surgo_cache(use_statsgo=True),
            )
            surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)
            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}
            surgo_c.logInvalidSoils(wd=soils_dir)

            # all the mukeys might not be valid. Need to identify the most common so we can use this instead
            valid_k_counts = Counter() 
            for topaz_id, k in domsoil_d.items():
                if k in soils:
                    valid_k_counts[k] += 1

            # now assign hillslopes with invalid mukeys the most common valid mukey
            most_common_k = valid_k_counts.most_common()[0][0]
            for topaz_id, k in domsoil_d.items():
                if k not in soils:
                    domsoil_d[topaz_id] = most_common_k

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.hillslope_area(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils
#            self.clay_pct = self._calc_clay_pct(clay_d)

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def _build_by_identify(self, build_func: Any) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(build_func={build_func})')

        soils_dir = self.soils_dir
        wd = self.wd
        with self.locked():
            watershed = self.watershed_instance

            orders = []
            for topaz_id, (lng, lat) in watershed.centroid_hillslope_iter():
                orders.append([topaz_id, (lng, lat)])

            soils, domsoil_d = build_func(orders, soils_dir, status_channel=self._status_channel)
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.hillslope_area(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def _build_from_map_db(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        from wepppy.wepp.soils.utils import WeppSoilUtil

        wd = self.wd
        watershed = self.watershed_instance

        soils_dir = self.soils_dir

        with self.locked():
            assert _exists(self.soils_map)
            soils_db_dir = _join(_split(self.soils_map)[0], 'db')

            soils_fn = _join(soils_dir, 'soils.tif')
            if _exists(soils_fn):
                os.remove(soils_fn)

            raster_stacker(self.soils_map, watershed.dem_fn, soils_fn)

            domsoil_d = identify_mode_single_raster_key(
                key_fn=watershed.subwta, parameter_fn=soils_fn, ignore_channels=True, ignore_keys=set())
            domsoil_d = {str(k): str(v) for k, v in domsoil_d.items()}

            self.logger.info(f'domsoil_d: {repr(domsoil_d)}')

            soils = {}
            for topaz_id, mukey in domsoil_d.items():
                if mukey not in soils:
                    src_sol_fn = _join(soils_db_dir, f'{mukey}.sol')
                    sol_fn = _join(soils_dir, f'{mukey}.sol')
                    # Refresh the run-local copy on each build so locale DB fixes are propagated.
                    shutil.copyfile(src_sol_fn, sol_fn)
                    wsu = WeppSoilUtil(sol_fn)
                    soils[mukey] = SoilSummary(
                        mukey=mukey,
                        fname=f'{mukey}.sol',
                        soils_dir=soils_dir,
                        build_date=str(datetime.now()),
                        desc=wsu.obj['ofes'][0]['slid'],
                        pct_coverage=0.0
                    )

            self.logger.info(repr(soils))

            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.hillslope_area(topaz_id)

            for k in soils:
                coverage = 100.0 * soils[k].area / watershed.sub_area
                soils[k].pct_coverage = coverage

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def _build_spatial_api(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        _map = self.ron_instance.map

        self._soils_is_vrt = False
        ssurgo_fn = self.ssurgo_fn
        soils_dir = self.soils_dir

        with self.timed('  Retrieving ssurgo data'):
            wmesque_retrieve(self.ssurgo_db, _map.extent,
                                ssurgo_fn, _map.cellsize, 
                                v=self.wmesque_version, 
                                wmesque_endpoint=self.wmesque_endpoint)
            update_catalog_entry(self.wd, ssurgo_fn)

        # Make SSURGO Soils
        sm = SurgoMap(ssurgo_fn)
        mukeys = set(sm.mukeys)
        self.logger.info(f"ssurgo mukeys: {mukeys}")

        with self.locked():
            ssurgo_cache_db_path = self._prepare_project_surgo_cache(use_statsgo=False)
            surgo_c = SurgoSoilCollection(mukeys, cache_db_path=ssurgo_cache_db_path)
            surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)

            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}
            surgo_c.logInvalidSoils(wd=soils_dir)

        self.logger.info(f"valid mukeys: {soils.keys()}")

        valid = list(int(v) for v in soils.keys())

        if len(valid) == 0:
            # falling back to statsgo
            self.logger.info(f"falling back to statsgo")

            statsgoSpatial = StatsgoSpatial()

            mukeys = statsgoSpatial.identify_mukeys_extent(_map.extent)
            with self.locked():
                statsgo_cache_db_path = self._prepare_project_surgo_cache(use_statsgo=True)
                surgo_c = SurgoSoilCollection(
                    mukeys,
                    use_statsgo=True,
                    cache_db_path=statsgo_cache_db_path,
                )
                surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)
                soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
                soils = {str(k): v for k, v in soils.items()}
                surgo_c.logInvalidSoils(wd=soils_dir)

        with self.locked():
            self._soils_is_vrt = False
            self._soils = soils

    def build(
        self, 
        initial_sat: Optional[float] = None, 
        ksflag: Optional[bool] = None, 
        max_workers: Optional[int] = None,
        retrieve_gridded_ssurgo: bool = True,
    ) -> None:
        self.logger.info(f'='*100)
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(initial_sat={initial_sat}, ksflag={ksflag})')
        self.logger.info(f' SoilsMode: {self._mode}')
        os.makedirs(self.soils_dir, exist_ok=True)
        with self.locked():
            self.domsoil_d = None
            self.ssurgo_domsoil_d = None
            self.raw_ssurgo_domsoil_d = None
            self.ssurgo_substitution_d = {}
            self.ssurgo_candidate_preparation = {"status": "not_attempted", "affected_hillslopes": 0}

        if self._mode == SoilsMode.SpatialAPI:
            self._build_spatial_api()
            return

        wd = self.wd
        watershed = self.watershed_instance
        if not watershed.is_abstracted:
            from wepppy.nodb.core.watershed import WatershedNotAbstractedError
            raise WatershedNotAbstractedError()

        if 'ChileCayumanque' in self.locales:
            self.logger.info('  Locale: ChileCayumanque')
            self.build_chile(initial_sat=initial_sat, ksflag=ksflag)
        elif self.soils_map is not None:
            self.logger.info(f'  Using soils map: {self.soils_map}')
            self._build_from_map_db()
        elif self.config_stem.startswith('ak'):
            self.logger.info('  Locale: Alaska')
            self._build_ak()
        elif self.mode == SoilsMode.Gridded:
            self.logger.info('  Gridded Soils Mode')
            if self.ssurgo_db == 'isric':
                self.logger.info('    Using ISRIC database')
                self.build_isric(initial_sat=initial_sat, ksflag=ksflag)
            elif 'eu' in self.locales:
                self.logger.info('    Using ESDAC database')
                from wepppy.eu.soils import build_esdac_soils
                self._build_by_identify(build_esdac_soils)
            elif 'au' in self.locales:
                self.logger.info('    Using ASRIS database')
                from wepppy.au.soils import build_asris_soils
                self._build_by_identify(build_asris_soils)
            else:
                self.logger.info('    Using SSURGO/STATSGO database')
                self._build_gridded(
                    initial_sat=initial_sat,
                    ksflag=ksflag,
                    max_workers=max_workers,
                    retrieve_gridded_ssurgo=retrieve_gridded_ssurgo,
                )
        elif self.mode == SoilsMode.Single:
            self.logger.info('  Single Soil Mode')
            self._build_single(initial_sat=initial_sat, ksflag=ksflag)
        elif self.mode == SoilsMode.SingleDb:
            self.logger.info('  Single Soil from Database Mode')
            self._build_singledb()
        elif self._mode in [SoilsMode.RRED_Burned, SoilsMode.RRED_Unburned]:
            self.logger.info('  RRED Soils Mode')
            import wepppy
            rred = wepppy.nodb.mods.Rred.getInstance(self.wd)
            rred.build_soils(self._mode)
            return

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_soils)
        except FileNotFoundError:
            pass

    @property
    def bd_d(self) -> Dict:
        """Returns dict of mukey -> bulk density."""
        parquet_path = pick_existing_parquet_path(self.wd, "soils/soils.parquet")
        if parquet_path is not None:
            parquet_fn = str(parquet_path)
            with duckdb.connect() as con:
                result = con.execute(f"SELECT mukey, bd FROM read_parquet('{parquet_fn}')").fetchall()
                return {row[0]: row[1] for row in result}

        return self._deprecated_bd_d()

    @deprecated
    def _deprecated_bd_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.bd
        return d 

    @property
    def clay_d(self) -> Dict:
        """Returns dict of mukey -> clay percentage."""
        parquet_path = pick_existing_parquet_path(self.wd, "soils/soils.parquet")
        if parquet_path is not None:
            parquet_fn = str(parquet_path)
            with duckdb.connect() as con:
                result = con.execute(f"SELECT mukey, clay FROM read_parquet('{parquet_fn}')").fetchall()
                return {row[0]: row[1] for row in result}

        return self._deprecated_clay_d()

    @deprecated
    def _deprecated_clay_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.clay
        return d 

    @property
    def sand_d(self) -> Dict:
        """Returns dict of mukey -> sand percentage."""
        parquet_path = pick_existing_parquet_path(self.wd, "soils/soils.parquet")
        if parquet_path is not None:
            parquet_fn = str(parquet_path)
            with duckdb.connect() as con:
                result = con.execute(f"SELECT mukey, sand FROM read_parquet('{parquet_fn}')").fetchall()
                return {row[0]: row[1] for row in result}
            
        return self._deprecated_sand_d()

    @deprecated
    def _deprecated_sand_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.clay
        return d 

    @property
    def ll_d(self) -> Dict:
        """Returns dict of mukey -> liquid limit."""
        parquet_path = pick_existing_parquet_path(self.wd, "soils/soils.parquet")
        if parquet_path is not None:
            parquet_fn = str(parquet_path)
            with duckdb.connect() as con:
                result = con.execute(f"SELECT mukey, ll FROM read_parquet('{parquet_fn}')").fetchall()
                return {row[0]: row[1] for row in result}
    
        return self._deprecated_ll_d()

    @deprecated
    def _deprecated_ll_d(self):
        d = {}
        for mukey, sol_summary in self.soils.items():
            d[mukey] = sol_summary.liquid_limit
        return d 

    def _weighted_metric_from_soils_parquet(
        self,
        parquet_fn: str,
        value_column: str,
        *,
        ignore_null_values: bool = False,
    ) -> float:
        with duckdb.connect() as con:
            schema_result = con.execute(f"SELECT * FROM read_parquet('{parquet_fn}') LIMIT 0")
            column_names = {desc[0] for desc in schema_result.description}
            where_clause = f" WHERE {value_column} IS NOT NULL" if ignore_null_values else ""

            if "area" in column_names:
                rows = con.execute(
                    f"SELECT topaz_id, {value_column}, area FROM read_parquet('{parquet_fn}'){where_clause}"
                ).fetchall()
                weighted = [
                    (float(value), float(area))
                    for _topaz_id, value, area in rows
                    if value is not None and area is not None
                ]
            else:
                rows = con.execute(
                    f"SELECT topaz_id, {value_column} FROM read_parquet('{parquet_fn}'){where_clause}"
                ).fetchall()
                watershed = self.watershed_instance
                weighted = [
                    (float(value), float(watershed.hillslope_area(topaz_id)))
                    for topaz_id, value in rows
                    if value is not None
                ]

        if not weighted:
            return 0.0

        totalarea = sum(area for _value, area in weighted)
        if totalarea <= 0.0:
            return 0.0

        wsum = sum(value * area for value, area in weighted)
        return wsum / totalarea

    @property
    def clay_pct(self):
        parquet_path = pick_existing_parquet_path(self.wd, "soils/soils.parquet")
        if parquet_path is not None:
            return self._weighted_metric_from_soils_parquet(str(parquet_path), "clay")

        return self._deprecated_clay_pct()
    
    @deprecated
    def _deprecated_clay_pct(self):
        # This method should only be called for legacy runs without soils.parquet
        clay_d = self.clay_d
        domsoil_d = self.ssurgo_domsoil_d

        if domsoil_d is None:
            return 0.0

        totalarea = 0.0
        wsum = 0.0
        watershed = self.watershed_instance

        if watershed._subs_summary is None:
            return 0.0

        for topaz_id in watershed._subs_summary:
            mukey = domsoil_d[str(topaz_id)]
            clay = clay_d[str(mukey)]
            area = watershed.hillslope_area(topaz_id)
            wsum += area * clay
            totalarea += area

        return wsum / totalarea if totalarea > 0 else 0.0

    @property
    def liquid_limit(self):
        # Try parquet first
        parquet_path = pick_existing_parquet_path(self.wd, "soils/soils.parquet")
        if parquet_path is not None:
            return self._weighted_metric_from_soils_parquet(
                str(parquet_path),
                "ll",
                ignore_null_values=True,
            )

        # Fall back to deprecated method
        return self._deprecated_liquid_limit()

    @deprecated
    def _deprecated_liquid_limit(self):
        # This method should only be called for legacy runs without soils.parquet
        ll_d = self.ll_d

        domsoil_d = self.domsoil_d
        if domsoil_d is None:
            return 0.0

        totalarea = 0.0
        wsum = 0.0
        watershed = self.watershed_instance
        
        if watershed._subs_summary is None:
            return 0.0
            
        for topaz_id in watershed._subs_summary:
            mukey = domsoil_d[str(topaz_id)]
            ll = ll_d[str(mukey)]
            if ll is None:
                continue

            area = watershed.hillslope_area(topaz_id)
            wsum += area * ll
            totalarea += area

        return wsum / totalarea if totalarea > 0 else 0.0

    def _build_ak(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')

        wd = self.wd
        with self.locked():
            watershed = self.watershed_instance
            mukey = -9999

            domsoil_d = {}
            soils = {str(mukey): SoilSummary(
                        mukey=mukey,
                        fname=None,
                        soils_dir=None,
                        build_date=str(datetime.now()),
                        desc=None,
                        pct_coverage=100.0
                    )}

            for topaz_id in watershed._subs_summary:
                domsoil_d[str(topaz_id)] = str(mukey)

            soils[str(mukey)].pct_coverage = 100.0

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)
            self.soils = soils

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def _build_single(
        self, 
        initial_sat: Optional[float] = None, 
        ksflag: bool = True
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')
        

        soils_dir = self.soils_dir

        with self.locked():
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = None

            watershed = self.watershed_instance
            mukey = self.single_selection
            surgo_c = SurgoSoilCollection(
                [mukey],
                cache_db_path=self._prepare_project_surgo_cache(use_statsgo=False),
            )
            surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag)
            surgo_c.logInvalidSoils(wd=soils_dir)

            assert surgo_c.weppSoils[mukey].valid()
            soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
            soils = {str(k): v for k, v in soils.items()}

            domsoil_d = {}
            for topaz_id in watershed._subs_summary:
                domsoil_d[str(topaz_id)] = str(mukey)

            soils[str(mukey)].pct_coverage = 100.0

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id, k in domsoil_d.items():
                soils[k].area += watershed.hillslope_area(topaz_id)

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)

            self.soils = soils
            #self.clay_pct = self._calc_clay_pct(clay_d)

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def _build_singledb(self) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')
        
        wd = self.wd

        if self.single_dbselection is None:
            self.single_dbselection = load_db()[0]
            self = self.getInstance(wd)

        soils_dir = self.soils_dir

        with self.locked():
            watershed = self.watershed_instance
            key = self.single_dbselection

            sol = get_soil(key)
            fn = _split(sol)[-1]

            mukey = key.replace('/', '-').replace('.sol', '')
            soils = {mukey: SoilSummary(
                mukey=mukey,
                fname=fn,
                soils_dir=soils_dir,
                build_date=str(datetime.now()),
                desc=key
            )}

            shutil.copyfile(sol, _join(soils_dir, fn))

            domsoil_d = {}
            for topaz_id in watershed._subs_summary:
                domsoil_d[str(topaz_id)] = mukey

            soils[mukey].pct_coverage = 100.0

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            for topaz_id in watershed._subs_summary:
                soils[mukey].area += watershed.hillslope_area(topaz_id)

            # store the soils dict
            self.domsoil_d = domsoil_d
            self.ssurgo_domsoil_d = deepcopy(domsoil_d)

            self.soils = soils

        self.logger.info('triggering SOILS_BUILD_COMPLETE')
        self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
        self = type(self).getInstance(self.wd)  # reload instance from .nodb

    def _build_ssurgo_candidate_shadow(
        self, raw_domsoil_d: Dict[str, str], valid_mukeys: set[str], ssurgo_fn: str,
        subwta_fn: str, current_global_mukey: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Collect shadow-only local candidate evidence without changing assignments."""
        if wepppyo3 is None:
            return {}
        import rasterio
        from rasterio.windows import Window, bounds as window_bounds

        invalid_ids = [topaz_id for topaz_id, mukey in raw_domsoil_d.items() if mukey not in valid_mukeys]
        if not invalid_ids:
            return {}
        with rasterio.open(subwta_fn) as subwta:
            values = subwta.read(1)
            bounds_by_topaz: Dict[str, Tuple[float, float, float, float]] = {}
            for topaz_id in invalid_ids:
                rows, cols = (values == int(topaz_id)).nonzero()
                if rows.size == 0:
                    continue
                window = Window(cols.min(), rows.min(), cols.max() - cols.min() + 1, rows.max() - rows.min() + 1)
                bounds_by_topaz[topaz_id] = window_bounds(window, subwta.transform)

        groups: List[Dict[str, Any]] = []
        for topaz_id in sorted(bounds_by_topaz, key=int):
            min_x, min_y, max_x, max_y = bounds_by_topaz[topaz_id]
            expanded = (min_x - 250.0, min_y - 250.0, max_x + 250.0, max_y + 250.0)
            matched = [group for group in groups if not (
                expanded[2] < group["expanded"][0] or expanded[0] > group["expanded"][2]
                or expanded[3] < group["expanded"][1] or expanded[1] > group["expanded"][3]
            )]
            if not matched:
                groups.append({"members": [topaz_id], "bounds": bounds_by_topaz[topaz_id], "expanded": expanded})
                continue
            group = matched[0]
            group["members"].append(topaz_id)
            group["bounds"] = (
                min(group["bounds"][0], min_x), min(group["bounds"][1], min_y),
                max(group["bounds"][2], max_x), max(group["bounds"][3], max_y),
            )
            group["expanded"] = (
                min(group["expanded"][0], expanded[0]), min(group["expanded"][1], expanded[1]),
                max(group["expanded"][2], expanded[2]), max(group["expanded"][3], expanded[3]),
            )
            for duplicate in matched[1:]:
                group["members"].extend(duplicate["members"])
                groups.remove(duplicate)
        clusters = [
            (f"shadow-{'-'.join(group['members'])}", [int(raw_domsoil_d[member]) for member in group["members"]], group["bounds"])
            for group in groups
        ]
        numeric_valid_mukeys = {int(str(mukey).split("-", 1)[0]) for mukey in valid_mukeys}
        results = local_mukey_candidates(
            ssurgo_fn, clusters, numeric_valid_mukeys,
            initial_radius_m=250.0, max_radius_m=2000.0, min_candidates=1,
        )
        shadow: Dict[str, Dict[str, Any]] = {}
        for group in groups:
            cluster_id = f"shadow-{'-'.join(group['members'])}"
            _, radius, support, exhausted, pixels_read = results[cluster_id]
            ordered_support = sorted(((str(mukey), count) for mukey, count in support), key=lambda item: (-item[1], int(item[0])))
            for topaz_id in group["members"]:
                shadow[topaz_id] = {
                "raw_mukey": raw_domsoil_d[topaz_id], "cluster_id": cluster_id,
                "bounds_epsg5070": list(bounds_by_topaz[topaz_id]), "search_radius_m": radius,
                "candidate_support": ordered_support,
                "proposed_mukey": ordered_support[0][0] if ordered_support else None,
                "current_global_mukey": current_global_mukey,
                "exhausted": bool(exhausted), "pixels_read": pixels_read,
                "reason": "local_candidate_shadow" if ordered_support else "no_local_valid_candidate",
                }
        return shadow

    @staticmethod
    def _ssurgo_direct_profile(collection: SurgoSoilCollection, mukey: str) -> Dict[str, Any]:
        """Read direct raw profile evidence without using converter defaults."""
        from wepppy.soils.ssurgo.fallback import direct_shallow_profile

        for component in collection.get_components(int(mukey)):
            profile = direct_shallow_profile(collection.get_layers(component["cokey"]))
            if profile["direct_values"]:
                return profile
        return {"horizon_index": None, "chkey": None, "direct_values": {}}

    def _materialize_added_ssurgo_donor(self, wepp_soil: Any, soils_dir: str) -> SoilSummary:
        """Write one selected added donor before publishing any assignment to it."""
        temporary_dir = tempfile.mkdtemp(prefix=".ssurgo-donor-", dir=soils_dir)
        destination: Optional[Path] = None
        published = False
        try:
            summary = wepp_soil.write(temporary_dir, overwrite=True)
            filename = str(summary.fname)
            if Path(filename).name != filename or not filename.endswith(".sol") or not filename[:-4].isdigit():
                raise ValueError(f"candidate donor filename is invalid: {filename!r}")
            temporary_root = Path(temporary_dir).resolve(strict=True)
            soils_root = Path(soils_dir).resolve(strict=True)
            source = (temporary_root / filename).resolve(strict=True)
            destination = soils_root / filename
            if (
                not source.is_file()
                or source.is_symlink()
                or source.parent != temporary_root
                or destination.is_symlink()
                or destination.exists()
                or destination.parent.resolve(strict=True) != soils_root
            ):
                raise OSError("candidate donor source or destination is not a new regular run-local soil")
            with source.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(source, destination)
            published = True
            directory_fd = os.open(soils_root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            summary.soils_dir = soils_dir
            return summary
        except OSError:
            if published and destination is not None and destination.exists() and not destination.is_symlink():
                destination.unlink()
                directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            raise
        finally:
            shutil.rmtree(temporary_dir, ignore_errors=True)

    def _select_ssurgo_intelligent_fallbacks(
        self,
        *,
        soils_dir: str,
        ssurgo_fn: str,
        subwta_fn: str,
        raw_domsoil_d: Dict[str, str],
        primary_soils: Dict[str, SoilSummary],
        primary_collection: SurgoSoilCollection,
        global_mukey: str,
        max_workers: Optional[int],
    ) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]], Dict[str, SoilSummary], Dict[str, Any]]:
        """Apply ADR-0025 local selection for residual-invalid dominant hillslopes."""
        from wepppy.soils.ssurgo.fallback import (
            CandidateRasterUnavailable,
            candidate_raster_mukeys,
            categorical_candidate_support_wgs84,
            prepare_padded_candidate_raster,
            raw_mukey_source_locations_wgs84,
            select_vector_donor,
        )

        final_domsoil_d = deepcopy(raw_domsoil_d)
        final_soils = dict(primary_soils)
        residual_invalid = sorted(
            {str(mukey) for mukey in raw_domsoil_d.values() if str(mukey) not in primary_soils},
            key=int,
        )
        affected_topaz_ids = [
            str(topaz_id) for topaz_id, mukey in raw_domsoil_d.items() if str(mukey) in set(residual_invalid)
        ]
        if not affected_topaz_ids:
            return final_domsoil_d, {}, final_soils, {"status": "not_attempted", "affected_hillslopes": 0}

        try:
            artifact = prepare_padded_candidate_raster(soils_dir=soils_dir, primary_raster_path=ssurgo_fn)
            padded_mukeys = candidate_raster_mukeys(artifact)
            added_mukeys = sorted(padded_mukeys - {int(mukey) for mukey in primary_collection.mukeys})
        except RuntimeError as exc:
            # Native categorical support is a required dependency, not a fallback condition.
            if "wepppyo3" in str(exc):
                raise
            self.logger.warning("SSURGO local candidate preparation unavailable: %s", exc)
            return self._global_ssurgo_substitutions(
                raw_domsoil_d, primary_soils, global_mukey, "candidate_preparation_unavailable"
            ) + ({"status": "unavailable", "error": str(exc)},)
        except (CandidateRasterUnavailable, FileNotFoundError, OSError, ValueError) as exc:
            self.logger.warning("SSURGO local candidate preparation unavailable: %s", exc)
            return self._global_ssurgo_substitutions(
                raw_domsoil_d, primary_soils, global_mukey, "candidate_preparation_unavailable"
            ) + ({"status": "unavailable", "error": str(exc)},)

        try:
            candidate_collection = SurgoSoilCollection(
                added_mukeys,
                cache_db_path=self._prepare_project_surgo_cache(use_statsgo=False),
            )
            candidate_collection.makeWeppSoils(
                initial_sat=self.initial_sat,
                ksflag=self.ksflag,
                logger=self.logger,
                max_workers=max_workers,
            )
            added_wepp_soils = candidate_collection.weppSoils or {}
        except RuntimeError as exc:
            if "wepppyo3" in str(exc):
                raise
            self.logger.exception("SSURGO local candidate build failed")
            return self._global_ssurgo_substitutions(
                raw_domsoil_d, primary_soils, global_mukey, "candidate_build_unavailable"
            ) + ({"status": "build_unavailable", "error": str(exc)},)
        except (SsurgoRequestError, OSError, ValueError) as exc:
            self.logger.exception("SSURGO local candidate build failed")
            return self._global_ssurgo_substitutions(
                raw_domsoil_d, primary_soils, global_mukey, "candidate_build_unavailable"
            ) + ({"status": "build_unavailable", "error": str(exc)},)

        buildable_mukeys = set(primary_soils) | {str(mukey) for mukey in added_wepp_soils}
        substitutions: Dict[str, Dict[str, Any]] = {}
        candidate_identity = {
            "manifest": str(artifact.manifest_path.relative_to(Path(soils_dir))),
            "raster_sha256": artifact.metadata["raster_sha256"],
            "source_identity": artifact.metadata["source"]["identity"],
            "source_sha256": artifact.metadata["source"]["sha256"],
            "bounds": artifact.metadata["bounds"],
            "crs_wkt": artifact.metadata["crs_wkt"],
        }
        try:
            source_locations = raw_mukey_source_locations_wgs84(
                subwta_fn,
                ssurgo_fn,
                [(topaz_id, raw_domsoil_d[topaz_id]) for topaz_id in affected_topaz_ids],
            )
        except RuntimeError as exc:
            if "wepppyo3" in str(exc):
                raise
            self.logger.warning("SSURGO raw-map source locations unavailable: %s", exc)
            return self._global_ssurgo_substitutions(
                raw_domsoil_d, primary_soils, global_mukey, "candidate_location_unavailable"
            ) + ({"status": "location_unavailable", "error": str(exc)},)
        except (OSError, ValueError) as exc:
            self.logger.warning("SSURGO raw-map source locations unavailable: %s", exc)
            return self._global_ssurgo_substitutions(
                raw_domsoil_d, primary_soils, global_mukey, "candidate_location_unavailable"
            ) + ({"status": "location_unavailable", "error": str(exc)},)
        for topaz_id in affected_topaz_ids:
            raw_mukey = str(raw_domsoil_d[topaz_id])
            source_location = source_locations[topaz_id]
            source_profile = self._ssurgo_direct_profile(primary_collection, raw_mukey)
            selected = None
            successful_radius = None
            selected_support: list[tuple[str, int]] = []
            candidate_support_error: Optional[str] = None
            for radius_m in (250.0, 500.0, 1_000.0, 2_000.0):
                try:
                    support = categorical_candidate_support_wgs84(
                        artifact.raster_path,
                        source_location[0],
                        source_location[1],
                        radius_m,
                        residual_invalid,
                        buildable_mukeys,
                    )
                except RuntimeError as exc:
                    if "wepppyo3" in str(exc):
                        raise
                    candidate_support_error = str(exc)
                    break
                except (OSError, ValueError) as exc:
                    candidate_support_error = str(exc)
                    break
                if support:
                    successful_radius = radius_m
                    selected_support = support
                    candidate_records = []
                    for candidate_mukey, pixel_support in support:
                        collection = primary_collection if candidate_mukey in primary_soils else candidate_collection
                        candidate_records.append(
                            {
                                "mukey": candidate_mukey,
                                "pixel_support": pixel_support,
                                "profile": self._ssurgo_direct_profile(collection, candidate_mukey),
                            }
                        )
                    selected = select_vector_donor(source_profile, candidate_records)
                    break
            if selected is None:
                final_domsoil_d[topaz_id] = global_mukey
                substitutions[topaz_id] = {
                    "raw_mukey": raw_mukey,
                    "replacement_mukey": global_mukey,
                    "reason": "invalid_dominant_mukey",
                    "selection_policy": "watershed_global",
                    "global_mukey": global_mukey,
                    "source_location_wgs84": list(source_location),
                    "candidate_raster": candidate_identity,
                    "search_radius_m": successful_radius,
                    "candidate_support": [[mukey, support] for mukey, support in selected_support],
                    "source_profile": source_profile,
                    "selected_profile": None,
                    "fallback_reason": (
                        "candidate_support_unavailable"
                        if candidate_support_error is not None
                        else "no_comparable_local_donor"
                    ),
                }
                continue
            donor_mukey = str(selected["mukey"])
            if donor_mukey not in final_soils:
                try:
                    final_soils[donor_mukey] = self._materialize_added_ssurgo_donor(
                        added_wepp_soils[int(donor_mukey)], soils_dir
                    )
                except (KeyError, OSError, ValueError):
                    self.logger.exception("SSURGO selected donor materialization failed: %s", donor_mukey)
                    final_domsoil_d[topaz_id] = global_mukey
                    substitutions[topaz_id] = {
                        "raw_mukey": raw_mukey,
                        "replacement_mukey": global_mukey,
                        "reason": "invalid_dominant_mukey",
                        "selection_policy": "watershed_global",
                        "global_mukey": global_mukey,
                        "source_location_wgs84": list(source_location),
                        "candidate_raster": candidate_identity,
                        "search_radius_m": successful_radius,
                        "candidate_support": [[mukey, support] for mukey, support in selected_support],
                        "source_profile": source_profile,
                        "selected_profile": None,
                        "fallback_reason": "donor_materialization_failed",
                    }
                    continue
            final_domsoil_d[topaz_id] = donor_mukey
            substitutions[topaz_id] = {
                "raw_mukey": raw_mukey,
                "replacement_mukey": donor_mukey,
                "reason": "invalid_dominant_mukey",
                "selection_policy": "ssurgo_local_vector_profile_v1",
                "global_mukey": global_mukey,
                "source_location_wgs84": list(source_location),
                "candidate_raster": candidate_identity,
                "search_radius_m": successful_radius,
                "candidate_support": [[mukey, support] for mukey, support in selected_support],
                "source_profile": source_profile,
                "selected_profile": {
                    "mukey": donor_mukey,
                    "horizon_index": selected["profile"]["horizon_index"],
                    "chkey": selected["profile"]["chkey"],
                    "shared_fields": selected["shared_fields"],
                    "scales": selected["scales"],
                    "distance": selected["distance"],
                },
                "fallback_reason": None,
            }
        return final_domsoil_d, substitutions, final_soils, {
            "status": "prepared",
            "affected_hillslopes": len(affected_topaz_ids),
            "manifest": candidate_identity["manifest"],
        }

    @staticmethod
    def _global_ssurgo_substitutions(
        raw_domsoil_d: Dict[str, str], primary_soils: Dict[str, SoilSummary], global_mukey: str, fallback_reason: str
    ) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]], Dict[str, SoilSummary]]:
        domsoil_d = deepcopy(raw_domsoil_d)
        substitutions: Dict[str, Dict[str, Any]] = {}
        for topaz_id, mukey in domsoil_d.items():
            if str(mukey) not in primary_soils:
                domsoil_d[topaz_id] = global_mukey
                substitutions[str(topaz_id)] = {
                    "raw_mukey": str(mukey), "replacement_mukey": global_mukey,
                    "reason": "invalid_dominant_mukey", "selection_policy": "watershed_global",
                    "global_mukey": global_mukey, "source_location_wgs84": None,
                    "candidate_raster": None, "search_radius_m": None, "candidate_support": None,
                    "source_profile": None, "selected_profile": None, "fallback_reason": fallback_reason,
                }
        return domsoil_d, substitutions, dict(primary_soils)

    def _build_gridded(
        self, 
        initial_sat: Optional[float] = None, 
        ksflag: Optional[bool] = None, 
        max_workers: Optional[int] = None,
        retrieve_gridded_ssurgo: bool = True,
    ) -> None:
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}(initial_sat={initial_sat}, ksflag={ksflag}, max_workers={max_workers})')

        global wepppyo3

        soils_dir = self.soils_dir
        os.makedirs(soils_dir, exist_ok=True)
        failed = True
        with self.locked():
            if initial_sat is not None:
                self._initial_sat = initial_sat
            if ksflag is not None:
                self._ksflag = ksflag

            _map = self.ron_instance.map
            watershed = self.watershed_instance

            with self.timed('  Retrieving ssurgo data'):
                if retrieve_gridded_ssurgo:
                    self._soils_is_vrt = False
                ssurgo_fn = self.ssurgo_fn
                if retrieve_gridded_ssurgo:
                    wmesque_retrieve(
                        self.ssurgo_db,
                        _map.extent,
                        ssurgo_fn,
                        _map.cellsize,
                        v=self.wmesque_version,
                        wmesque_endpoint=self.wmesque_endpoint,
                    )
                    update_catalog_entry(self.wd, ssurgo_fn)
                elif not _exists(ssurgo_fn):
                    raise FileNotFoundError(f"'{ssurgo_fn}' not found!")

            with self.timed('  Building SSURGO Soils'):
                sm = SurgoMap(ssurgo_fn)
                mukeys = set(sm.mukeys)
                self.logger.info(f"    ssurgo mukeys: {mukeys}")

                surgo_c = SurgoSoilCollection(
                    mukeys,
                    cache_db_path=self._prepare_project_surgo_cache(use_statsgo=False),
                )
                surgo_c.makeWeppSoils(initial_sat=self.initial_sat, ksflag=self.ksflag, logger=self.logger,
                                      max_workers=max_workers)

                soils = surgo_c.writeWeppSoils(wd=soils_dir, write_logs=True)
                soils = {str(k): v for k, v in soils.items()}
                surgo_c.logInvalidSoils(wd=soils_dir)

            self.logger.info(f"valid mukeys: {soils.keys()}")
            valid = list(int(v) for v in soils.keys())

            if wepppyo3 is None:
                with self.timed('  Identifying dominant soils  (wepppyo3 not available)'):
                    domsoil_d = sm.build_soilgrid(watershed.subwta)
            else:
                with self.timed('  Identifying dominant soils with wepppyo3 (rustlang)'):
                    domsoil_d = identify_mode_single_raster_key(
                        key_fn=watershed.subwta, parameter_fn=ssurgo_fn, ignore_channels=True, ignore_keys={-2147483648,})
                    domsoil_d = {k: str(v) for k, v in domsoil_d.items() if int(k) > 0}
            raw_domsoil_d = deepcopy(domsoil_d)
            ssurgo_substitution_d = {}

            dom_mukey = None
            for mukey, count in Counter(domsoil_d.values()).most_common():
                if mukey in soils:
                    dom_mukey = mukey
                    break

            if dom_mukey is None:
                if len(valid) > 0:
                    dom_mukey = str(valid[0])


            failed = dom_mukey is None
            if not failed:
                (
                    domsoil_d,
                    ssurgo_substitution_d,
                    soils,
                    ssurgo_candidate_preparation,
                ) = self._select_ssurgo_intelligent_fallbacks(
                    soils_dir=soils_dir,
                    ssurgo_fn=ssurgo_fn,
                    subwta_fn=watershed.subwta,
                    raw_domsoil_d=raw_domsoil_d,
                    primary_soils=soils,
                    primary_collection=surgo_c,
                    global_mukey=dom_mukey,
                    max_workers=max_workers,
                )

                # while we are at it we will calculate the pct coverage
                # for the landcover types in the watershed
                with self.timed('  Calculating soil coverage'):
                    for k in soils:
                        soils[k].area = 0.0

                    # Keep coverage denominator aligned with Landuse: hillslopes only.
                    total_area = watershed.sub_area
                    for topaz_id, k in domsoil_d.items():
                        soils[k].area += watershed.hillslope_area(topaz_id)

                    for k in soils:
                        coverage = 100.0 * soils[k].area / total_area
                        soils[k].pct_coverage = coverage

                with self.timed('  Storing soils'):
                    self.domsoil_d = domsoil_d
                    self.ssurgo_domsoil_d = deepcopy(domsoil_d)
                    self.raw_ssurgo_domsoil_d = raw_domsoil_d
                    self.ssurgo_substitution_d = ssurgo_substitution_d
                    self.ssurgo_candidate_shadow_d = {}
                    self.ssurgo_candidate_preparation = ssurgo_candidate_preparation
                    self.soils = {str(k): v for k, v in soils.items()}

        # fallback to statsgo if surgo failed
        if failed:
            self.logger.info('no surgo keys found, falling back to statsgo')
            self.build_statsgo(initial_sat=self.initial_sat,
                                ksflag=self.ksflag)
        else:
            self.logger.info('triggering SOILS_BUILD_COMPLETE')
            self.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
            self = type(self).getInstance(self.wd)  # reload instance from .nodb

    @property
    def report(self) -> str:
        """
        returns a list of managements sorted by coverage in
        descending order
        """
        used_soils = set([str(x) for x in self.domsoil_d.values()])
        report = [s for s in list(self.soils.values()) if str(s.mukey) in used_soils]
        report.sort(key=lambda soil: soil.pct_coverage or 0, reverse=True)

        return [soil.as_dict(abbreviated=True) for soil in report]

    def _x_summary(self, topaz_id, abbreviated=False):

        if pick_existing_parquet_path(self.wd, "soils/soils.parquet") is not None:
            return get_soil_sub_summary(self.wd, topaz_id)
        
        domsoil_d = self.domsoil_d

        if domsoil_d is None:
            return None

        if str(topaz_id) in domsoil_d:
            mukey = str(domsoil_d[str(topaz_id)])
            return self.soils[mukey].as_dict(abbreviated=abbreviated)
        else:
            return None

    def sub_summary(
        self, 
        topaz_id: str, 
        abbreviated: bool = False
    ) -> Optional[Dict]:
        return self._x_summary(topaz_id, abbreviated=abbreviated)

    def chn_summary(
        self, 
        topaz_id: str, 
        abbreviated: bool = False
    ) -> Optional[Dict]:
        return self._x_summary(topaz_id, abbreviated=abbreviated)

    @property
    def subs_summary(self) -> Dict:
        """
        Returns a dictionary with topaz_id keys and dictionary soils values.
        """
        if pick_existing_parquet_path(self.wd, "soils/soils.parquet") is not None:
            return get_soil_subs_summary(self.wd)
            
        return self._subs_summary_gen()


    def _subs_summary_gen(self):

        domsoil_d = self.domsoil_d

        if domsoil_d is None:
            return None

        soils = self.soils

        # Cache soil dictionaries to avoid multiple calls to as_dict for the same soil
        soil_dicts_cache = {mukey: soil.as_dict() for mukey, soil in soils.items()}

        # Compile the summary using cached soil dictionaries
        summary = {
            topaz_id: deepcopy(soil_dicts_cache[mukey])
            for topaz_id, mukey in domsoil_d.items()
            if not is_channel(topaz_id)
        }
        raw_domsoil_d = getattr(self, "raw_ssurgo_domsoil_d", None) or {}
        ssurgo_substitution_d = getattr(self, "ssurgo_substitution_d", None) or {}
        shadow_d = getattr(self, "ssurgo_candidate_shadow_d", None) or {}
        for topaz_id, soil_data in summary.items():
            str_topaz_id = str(topaz_id)
            raw_mukey = raw_domsoil_d.get(str_topaz_id)
            soil_data["raw_mukey"] = None if raw_mukey is None else str(raw_mukey)

            substitution = ssurgo_substitution_d.get(str_topaz_id)
            shadow = shadow_d.get(str_topaz_id)
            soil_data["shadow_cluster_id"] = None if shadow is None else shadow["cluster_id"]
            soil_data["shadow_search_radius_m"] = None if shadow is None else shadow["search_radius_m"]
            soil_data["shadow_proposed_mukey"] = None if shadow is None else shadow["proposed_mukey"]
            soil_data["shadow_candidate_support_json"] = None if shadow is None else json.dumps(shadow["candidate_support"])
            soil_data["shadow_reason"] = None if shadow is None else shadow["reason"]
            if substitution is None:
                soil_data["substituted_mukey"] = None
                soil_data["substitution_reason"] = None
                soil_data["selection_policy"] = None
                soil_data["global_mukey"] = None
                soil_data["source_location_wgs84_json"] = None
                soil_data["candidate_raster_json"] = None
                soil_data["search_radius_m"] = None
                soil_data["candidate_support_json"] = None
                soil_data["source_profile_json"] = None
                soil_data["selected_profile_json"] = None
                soil_data["fallback_reason"] = None
                continue

            soil_data["substituted_mukey"] = str(substitution["replacement_mukey"])
            soil_data["substitution_reason"] = str(substitution["reason"])
            soil_data["selection_policy"] = substitution.get("selection_policy")
            soil_data["global_mukey"] = None if substitution.get("global_mukey") is None else str(substitution["global_mukey"])
            soil_data["source_location_wgs84_json"] = json.dumps(substitution.get("source_location_wgs84"))
            soil_data["candidate_raster_json"] = json.dumps(substitution.get("candidate_raster"))
            soil_data["search_radius_m"] = substitution.get("search_radius_m")
            soil_data["candidate_support_json"] = json.dumps(substitution.get("candidate_support"))
            soil_data["source_profile_json"] = json.dumps(substitution.get("source_profile"))
            soil_data["selected_profile_json"] = json.dumps(substitution.get("selected_profile"))
            soil_data["fallback_reason"] = substitution.get("fallback_reason")

        return summary

    def dump_soils_parquet(self) -> None:
        """
        Dumps the subs_summary to a Parquet file using Pandas.
        """
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info(f'{self.class_name}.{func_name}()')
        
        dict_result = self._subs_summary_gen()
        if dict_result is None or len(dict_result) == 0:
            return
        
        df = pd.DataFrame.from_dict(dict_result, orient='index')
        df.index.name = 'topaz_id'
        df.reset_index(inplace=True)

        df['topaz_id'] = pd.to_numeric(df['topaz_id'], errors='raise').astype('Int32')
        df['mukey'] = df['mukey'].astype(str)

        translator = None
        try:
            import duckdb  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            try:
                translator = self.watershed_instance.translator_factory()
            except (RuntimeError, FileNotFoundError, ValueError):
                translator = None
        else:
            try:
                translator = self.watershed_instance.translator_factory()
            except (RuntimeError, FileNotFoundError, ValueError, duckdb.Error):
                translator = None

        if 'wepp_id' in df.columns:
            df['wepp_id'] = pd.to_numeric(df['wepp_id'], errors='coerce').astype('Int32')
        else:
            if translator is not None:
                wepp_values = []
                for top in df['topaz_id']:
                    if pd.isna(top):
                        wepp_values.append(pd.NA)
                    else:
                        try:
                            value = translator.wepp(top=int(top))
                        except (KeyError, TypeError, ValueError):
                            value = None
                        wepp_values.append(value if value is not None else pd.NA)
                df['wepp_id'] = pd.Series(pd.array(wepp_values, dtype='Int32'))
            else:
                df['wepp_id'] = pd.Series(pd.array([pd.NA] * len(df), dtype='Int32'))

        for legacy_col in ('TopazID', 'WeppID'):
            if legacy_col in df.columns:
                df.drop(columns=[legacy_col], inplace=True)

        preferred = ['topaz_id', 'wepp_id']
        remaining = [c for c in df.columns if c not in preferred]
        df = df.loc[:, preferred + remaining]

        parquet_path = Path(self.soils_dir) / "soils.parquet"
        with tempfile.NamedTemporaryFile(
            prefix=".soils.parquet.", suffix=".tmp", dir=self.soils_dir, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            df.to_parquet(temporary_path, index=False)
            with temporary_path.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary_path, parquet_path)
            directory_fd = os.open(self.soils_dir, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        update_catalog_entry(self.wd, 'soils/soils.parquet')
        
    def _post_dump_and_unlock(self):
        if not _exists(self.soils_dir):
            return self
        self.dump_soils_parquet()
        return self

    @property
    def hill_table(self) -> List[Dict]:
        """
        Returns a pandas DataFrame with the hill table.
        """
        if pick_existing_parquet_path(self.wd, "soils/soils.parquet") is not None:
            return get_soil_subs_summary(self.wd, return_as_df=True)
        
        result_dict = self._subs_summary_gen()
        df = pd.DataFrame.from_dict(result_dict, orient='index')
        df.index.name = 'topaz_id'
        df.reset_index(inplace=True)
        df['topaz_id'] = pd.to_numeric(df['topaz_id'], errors='raise').astype('Int32')
        df['mukey'] = df['mukey'].astype(str)

        translator = None
        try:
            import duckdb  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            try:
                translator = self.watershed_instance.translator_factory()
            except (RuntimeError, FileNotFoundError, ValueError):
                translator = None
        else:
            try:
                translator = self.watershed_instance.translator_factory()
            except (RuntimeError, FileNotFoundError, ValueError, duckdb.Error):
                translator = None

        if translator is not None:
            wepp_values = []
            for top in df['topaz_id']:
                if pd.isna(top):
                    wepp_values.append(pd.NA)
                else:
                    try:
                        value = translator.wepp(top=int(top))
                    except (KeyError, TypeError, ValueError):
                        value = None
                    wepp_values.append(value if value is not None else pd.NA)
            df['wepp_id'] = pd.Series(pd.array(wepp_values, dtype='Int32'))
        else:
            df['wepp_id'] = pd.Series(pd.array([pd.NA] * len(df), dtype='Int32'))

        return df

    def sub_iter(self):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is not None:
            for topaz_id, k in domsoil_d.items():
                topaz_id = str(topaz_id)
                if is_channel(topaz_id):
                    continue

                yield topaz_id, soils[k]
        
    @property
    def chns_summary(self):
        """
        returns a dictionary of topaz_id keys and jsonified soils
        values
        """
        domsoil_d = self.domsoil_d
        
        if domsoil_d is None:
            return None
            
        soils = self.soils

        summary = {}
        for topaz_id, k in domsoil_d.items():
            topaz_id = str(topaz_id)
            if not is_channel(topaz_id):
                continue

            summary[topaz_id] = soils[k].as_dict()

        return summary

    def chn_iter(self):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is not None:
            for topaz_id, k in domsoil_d.items():
                topaz_id = str(topaz_id)
                if not is_channel(topaz_id):
                    continue

                yield topaz_id, soils[k]
        
    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id):
        domsoil_d = self.domsoil_d
        soils = self.soils

        if domsoil_d is None:
            raise IndexError
        
        translator = self.watershed_instance.translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))
        
        if topaz_id in domsoil_d:
            topaz_id = str(topaz_id)
            k = domsoil_d[topaz_id]
            return soils[k]
    
        raise IndexError
