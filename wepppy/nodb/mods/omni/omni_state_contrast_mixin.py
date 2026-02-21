"""State and contrast management mixin for Omni facade.

This module holds stateful Omni facade methods that do not need to live in the
primary orchestration file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wepppy.nodb.base import NoDbAlreadyLockedError, nodb_setter

if TYPE_CHECKING:
    from typing import Dict, Iterable, List, Optional, Set, Tuple

    from wepppy.nodb.mods.omni.omni import (
        ContrastDependency,
        ContrastDependencies,
        ContrastMapping,
        OmniScenario,
        ScenarioDef,
        ScenarioDependency,
    )


OMNI_REL_DIR = '_pups/omni'


def _omni_module():
    from wepppy.nodb.mods.omni import omni as omni_module

    return omni_module


class _OmniAttrProxy:
    """Resolve Omni module attributes lazily to avoid import cycles."""

    def __init__(self, attr_name: str) -> None:
        self._attr_name = attr_name

    def __getattr__(self, item: str) -> Any:
        target = getattr(_omni_module(), self._attr_name)
        return getattr(target, item)


_OMNI_INPUT_PARSER = _OmniAttrProxy('_OMNI_INPUT_PARSER')
_OMNI_STATION_CATALOG_SERVICE = _OmniAttrProxy('_OMNI_STATION_CATALOG_SERVICE')
_OMNI_BUILD_ROUTER = _OmniAttrProxy('_OMNI_BUILD_ROUTER')

os = _OmniAttrProxy('os')
shutil = _OmniAttrProxy('shutil')
json = _OmniAttrProxy('json')
time = _OmniAttrProxy('time')


def _exists(path: str) -> bool:
    return bool(_omni_module()._exists(path))


def _join(*parts: str) -> str:
    return _omni_module()._join(*parts)


def isdir(path: str) -> bool:
    return bool(_omni_module().isdir(path))


def _scenario_name_from_scenario_definition(scenario_def: dict[str, Any]) -> str:
    return _omni_module()._scenario_name_from_scenario_definition(scenario_def)


def _clear_nodb_cache_and_locks(runid: str, pup_relpath: str | None = None) -> None:
    _omni_module()._clear_nodb_cache_and_locks(runid, pup_relpath=pup_relpath)


def _hash_file_sha1(path: str | None) -> str | None:
    return _omni_module()._hash_file_sha1(path)


class OmniStateContrastMixin:
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
        _OMNI_INPUT_PARSER.parse_scenarios(self, parsed_inputs)

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
            self._remove_scenario_artifacts(name, removed, missing)

        aggregated = _join(self.omni_dir, 'scenarios.out.parquet')
        if _exists(aggregated):
            try:
                os.remove(aggregated)
            except OSError as exc:
                self.logger.debug('Failed to remove aggregated scenario summary %s: %s', aggregated, exc)

        self._refresh_catalog(OMNI_REL_DIR)
        return {'removed': removed, 'missing': missing}

    def _remove_scenario_artifacts(
        self,
        name: str,
        removed: List[str],
        missing: List[str],
    ) -> None:
        scenario_dir = _join(self.wd, OMNI_REL_DIR, 'scenarios', name)
        if _exists(scenario_dir):
            try:
                shutil.rmtree(scenario_dir)
                pup_relpath = os.path.relpath(scenario_dir, self.wd)
                _clear_nodb_cache_and_locks(self.runid, pup_relpath)
            except OSError as exc:
                self.logger.debug('Failed to remove scenario directory %s: %s', scenario_dir, exc)
            if name not in removed:
                removed.append(name)
            return

        if name not in removed:
            missing.append(name)

    def parse_inputs(self, kwds: Dict[str, Any]) -> None:
        _OMNI_INPUT_PARSER.parse_inputs(self, kwds)

    def _normalize_contrast_pairs(self, value: Any) -> List[Dict[str, str]]:
        return _OMNI_INPUT_PARSER.normalize_contrast_pairs(self, value)

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
    def contrast_batch_size(self) -> int:
        raw_value = getattr(self, "_contrast_batch_size", None)
        if raw_value in (None, ""):
            raw_value = self.config_get_int("omni", "contrast_batch_size", 6)
        try:
            batch_size = int(raw_value)
        except (TypeError, ValueError):
            batch_size = 6
        return max(batch_size, 1)

    @contrast_batch_size.setter
    @nodb_setter
    def contrast_batch_size(self, value: Optional[int]) -> None:
        self._contrast_batch_size = value

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
    def contrast_output_chan_out(self) -> bool:
        value = getattr(self, "_contrast_output_chan_out", None)
        if value is None:
            return False
        return bool(value)

    @contrast_output_chan_out.setter
    @nodb_setter
    def contrast_output_chan_out(self, value: bool) -> None:
        self._contrast_output_chan_out = bool(value)

    @property
    def contrast_output_tcr_out(self) -> bool:
        value = getattr(self, "_contrast_output_tcr_out", None)
        if value is None:
            return False
        return bool(value)

    @contrast_output_tcr_out.setter
    @nodb_setter
    def contrast_output_tcr_out(self, value: bool) -> None:
        self._contrast_output_tcr_out = bool(value)

    @property
    def contrast_output_chnwb(self) -> bool:
        value = getattr(self, "_contrast_output_chnwb", None)
        if value is None:
            return False
        return bool(value)

    @contrast_output_chnwb.setter
    @nodb_setter
    def contrast_output_chnwb(self, value: bool) -> None:
        self._contrast_output_chnwb = bool(value)

    @property
    def contrast_output_soil_pw0(self) -> bool:
        value = getattr(self, "_contrast_output_soil_pw0", None)
        if value is None:
            return False
        return bool(value)

    @contrast_output_soil_pw0.setter
    @nodb_setter
    def contrast_output_soil_pw0(self, value: bool) -> None:
        self._contrast_output_soil_pw0 = bool(value)

    @property
    def contrast_output_plot_pw0(self) -> bool:
        value = getattr(self, "_contrast_output_plot_pw0", None)
        if value is None:
            return False
        return bool(value)

    @contrast_output_plot_pw0.setter
    @nodb_setter
    def contrast_output_plot_pw0(self, value: bool) -> None:
        self._contrast_output_plot_pw0 = bool(value)

    @property
    def contrast_output_ebe_pw0(self) -> bool:
        value = getattr(self, "_contrast_output_ebe_pw0", None)
        if value is None:
            return True
        return bool(value)

    @contrast_output_ebe_pw0.setter
    @nodb_setter
    def contrast_output_ebe_pw0(self, value: bool) -> None:
        self._contrast_output_ebe_pw0 = bool(value)

    def contrast_output_options(self) -> Dict[str, bool]:
        return {
            "chan_out": self.contrast_output_chan_out,
            "tcr_out": self.contrast_output_tcr_out,
            "chnwb": self.contrast_output_chnwb,
            "soil_pw0": self.contrast_output_soil_pw0,
            "plot_pw0": self.contrast_output_plot_pw0,
            "ebe_pw0": self.contrast_output_ebe_pw0,
        }

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
            except OSError as exc:
                self.logger.debug('Failed to remove contrast build report %s: %s', report_path, exc)
        contrasts_report = _join(self.omni_dir, 'contrasts.out.parquet')
        if _exists(contrasts_report):
            try:
                os.remove(contrasts_report)
            except OSError as exc:
                self.logger.debug('Failed to remove contrast summary %s: %s', contrasts_report, exc)

    def _reset_contrast_build_state(self) -> None:
        with self.locked():
            self._contrasts = None
            self._contrast_names = []
            self._contrast_labels = {}
            self._contrast_dependency_tree = {}
        self._clean_contrast_runs()

    def _clean_contrast_runs(self) -> None:
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        if not _exists(contrasts_dir):
            contrasts_dir = None
        if contrasts_dir:
            for entry in os.listdir(contrasts_dir):
                if entry == '_uploads':
                    continue
                path = _join(contrasts_dir, entry)
                if os.path.isdir(path):
                    shutil.rmtree(path)
        status_dir = self._contrast_sidecar_dir()
        if _exists(status_dir):
            for entry in os.listdir(status_dir):
                if not entry.endswith(".status.json"):
                    continue
                path = _join(status_dir, entry)
                if _exists(path):
                    try:
                        os.remove(path)
                    except OSError as exc:
                        self.logger.debug("Failed to remove contrast status %s: %s", path, exc)

    def _clean_stale_contrast_runs(self, active_ids: Iterable[int]) -> None:
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        if not _exists(contrasts_dir):
            contrasts_dir = None
        active = {str(contrast_id) for contrast_id in active_ids}
        if contrasts_dir:
            for entry in os.listdir(contrasts_dir):
                if entry == '_uploads':
                    continue
                path = _join(contrasts_dir, entry)
                if os.path.isdir(path) and entry not in active:
                    shutil.rmtree(path)
        status_dir = self._contrast_sidecar_dir()
        if _exists(status_dir):
            for entry in os.listdir(status_dir):
                if not entry.endswith(".status.json"):
                    continue
                stem = entry.rsplit(".", maxsplit=2)[0]
                contrast_token = stem.replace("contrast_", "")
                try:
                    contrast_id = int(contrast_token)
                except (TypeError, ValueError):
                    continue
                if str(contrast_id) not in active:
                    path = _join(status_dir, entry)
                    if _exists(path):
                        try:
                            os.remove(path)
                        except OSError as exc:
                            self.logger.debug("Failed to remove contrast status %s: %s", path, exc)

    def _clean_contrast_run(self, contrast_id: int) -> None:
        contrasts_dir = _join(self.wd, OMNI_REL_DIR, 'contrasts')
        path = _join(contrasts_dir, str(contrast_id))
        if isdir(path):
            shutil.rmtree(path)
        self._clear_contrast_run_status(contrast_id)

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

    def _contrast_run_status_path(self, contrast_id: int) -> str:
        return _join(self._contrast_sidecar_dir(), f"contrast_{contrast_id:05d}.status.json")

    def _load_contrast_run_status(self, contrast_id: int) -> Optional[Dict[str, Any]]:
        path = self._contrast_run_status_path(contrast_id)
        if not _exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.debug("Failed to read contrast status from %s: %s", path, exc)
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _write_contrast_run_status(
        self,
        contrast_id: int,
        contrast_name: str,
        status: str,
        *,
        job_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "contrast_id": contrast_id,
            "contrast_name": contrast_name,
            "status": status,
            "timestamp": time.time(),
        }
        if job_id:
            payload["job_id"] = job_id
        if error:
            payload["error"] = error
        path = self._contrast_run_status_path(contrast_id)
        os.makedirs(self._contrast_sidecar_dir(), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(payload, fp)
        except OSError as exc:
            self.logger.debug("Failed to write contrast status to %s: %s", path, exc)

    def _clear_contrast_run_status(self, contrast_id: int) -> None:
        path = self._contrast_run_status_path(contrast_id)
        if _exists(path):
            try:
                os.remove(path)
            except OSError as exc:
                self.logger.debug("Failed to remove contrast status %s: %s", path, exc)

    def _normalize_landuse_key(self, value: Any) -> Optional[str]:
        return _OMNI_STATION_CATALOG_SERVICE.normalize_landuse_key(self, value)

    def _normalize_landuse_key_impl(self, value: Any) -> Optional[str]:
        return _OMNI_STATION_CATALOG_SERVICE.normalize_landuse_key(self, value)

    def _load_landuse_key_map(self, landuse_wd: str) -> Optional[Dict[int, Optional[str]]]:
        return _OMNI_STATION_CATALOG_SERVICE.load_landuse_key_map(self, landuse_wd)

    def _load_landuse_key_map_impl(self, landuse_wd: str) -> Optional[Dict[int, Optional[str]]]:
        return _OMNI_STATION_CATALOG_SERVICE.load_landuse_key_map(self, landuse_wd)

    def _contrast_landuse_skip_reason(
        self,
        contrast_id: int,
        contrast_name: str,
        *,
        landuse_cache: Optional[Dict[str, Optional[Dict[int, Optional[str]]]]] = None,
    ) -> Optional[str]:
        return _OMNI_STATION_CATALOG_SERVICE.contrast_landuse_skip_reason(
            self,
            contrast_id,
            contrast_name,
            landuse_cache=landuse_cache,
        )

    def _contrast_landuse_skip_reason_impl(
        self,
        contrast_id: int,
        contrast_name: str,
        *,
        landuse_cache: Optional[Dict[str, Optional[Dict[int, Optional[str]]]]] = None,
    ) -> Optional[str]:
        return _OMNI_STATION_CATALOG_SERVICE.contrast_landuse_skip_reason(
            self,
            contrast_id,
            contrast_name,
            landuse_cache=landuse_cache,
        )

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
        return _OMNI_STATION_CATALOG_SERVICE.contrast_scenario_keys(self, contrast_name)

    def _contrast_scenario_keys_impl(self, contrast_name: str) -> Tuple[str, str]:
        return _OMNI_STATION_CATALOG_SERVICE.contrast_scenario_keys(self, contrast_name)

    def _contrast_run_status(self, contrast_id: int, contrast_name: str) -> str:
        run_marker = self._contrast_run_readme_path(contrast_id)
        if not _exists(run_marker):
            status_entry = self._load_contrast_run_status(contrast_id)
            if status_entry and status_entry.get("status") == "started":
                return "in_progress"
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
