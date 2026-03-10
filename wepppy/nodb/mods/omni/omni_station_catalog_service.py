from __future__ import annotations

import json
import os
from os.path import exists as _exists
from os.path import join as _join
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple

import pandas as pd

from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import ContrastDependencies, Omni, OmniScenario, ScenarioDef


class OmniStationCatalogService:
    """Resolve Omni scenario/catalog paths and dependency metadata."""

    def normalize_landuse_key(self, omni: "Omni", value: Any) -> Optional[str]:
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

    def load_landuse_key_map(self, omni: "Omni", landuse_wd: str) -> Optional[Dict[int, Optional[str]]]:
        parquet_path = pick_existing_parquet_path(landuse_wd, "landuse/landuse.parquet")
        if parquet_path is None:
            return None
        parquet_fn = str(parquet_path)

        for id_column in ("topaz_id", "TopazID"):
            try:
                df = pd.read_parquet(parquet_fn, columns=[id_column, "key"])
            except (KeyError, ValueError) as exc:
                omni.logger.debug(
                    "Failed landuse key map read with %s from %s: %s",
                    id_column,
                    parquet_fn,
                    exc,
                )
                continue
            except (ImportError, OSError) as exc:
                omni.logger.warning(
                    "Failed to read landuse key parquet %s (landuse_wd=%s): %s",
                    parquet_fn,
                    landuse_wd,
                    exc,
                )
                return None
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
                key_map[topaz_id] = self.normalize_landuse_key(omni, getattr(row, "key", None))
            if key_map:
                return key_map
        return None

    def contrast_landuse_skip_reason(
        self,
        omni: "Omni",
        contrast_id: int,
        contrast_name: str,
        *,
        landuse_cache: Optional[Dict[str, Optional[Dict[int, Optional[str]]]]] = None,
    ) -> Optional[str]:
        if not contrast_name:
            return None

        try:
            contrast_payload = omni._load_contrast_sidecar(contrast_id)
        except FileNotFoundError:
            return None

        control_key, contrast_key = self.contrast_scenario_keys(omni, contrast_name)
        if control_key == contrast_key:
            return "landuse_unchanged"

        from wepppy.nodb.mods.omni.omni import (
            _contrast_topaz_ids_from_mapping,
            _resolve_base_scenario_key,
            _resolve_contrast_scenario_wd,
        )

        base_key = _resolve_base_scenario_key(omni.wd)
        try:
            contrast_wd = _resolve_contrast_scenario_wd(omni.wd, contrast_key, base_key)
        except FileNotFoundError:
            return None

        contrast_topaz_ids = _contrast_topaz_ids_from_mapping(contrast_payload, contrast_wd)
        if not contrast_topaz_ids:
            return None

        cache = landuse_cache if landuse_cache is not None else {}
        if control_key not in cache:
            try:
                control_wd = _resolve_contrast_scenario_wd(omni.wd, control_key, base_key)
            except FileNotFoundError:
                return None
            cache[control_key] = self.load_landuse_key_map(omni, control_wd)
        if contrast_key not in cache:
            cache[contrast_key] = self.load_landuse_key_map(omni, contrast_wd)

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

    def normalize_scenario_key(self, omni: "Omni", name: Optional[Any]) -> str:
        from wepppy.nodb.mods.omni.omni import OmniScenario

        if isinstance(name, OmniScenario):
            name = str(name)
        if name in (None, "None"):
            return str(omni.base_scenario)
        return str(name)

    def loss_pw0_path_for_scenario(self, omni: "Omni", scenario_name: Optional[Any]) -> str:
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

        scenario_key = self.normalize_scenario_key(omni, scenario_name)
        base_path = _join(
            omni.wd,
            "wepp",
            "output",
            "interchange",
            "loss_pw0.out.parquet",
        )
        scenario_path = _join(
            omni.wd,
            OMNI_REL_DIR,
            "scenarios",
            scenario_key,
            "wepp",
            "output",
            "interchange",
            "loss_pw0.out.parquet",
        )

        if scenario_key == str(omni.base_scenario) and not _exists(scenario_path):
            return base_path
        return scenario_path if _exists(scenario_path) else (
            base_path if scenario_key == str(omni.base_scenario) else scenario_path
        )

    def interchange_class_data_path_for_scenario(self, omni: "Omni", scenario_name: Optional[Any]) -> str:
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

        scenario_key = self.normalize_scenario_key(omni, scenario_name)
        base_path = _join(
            omni.wd,
            "wepp",
            "output",
            "interchange",
            "loss_pw0.all_years.class_data.parquet",
        )
        scenario_path = _join(
            omni.wd,
            OMNI_REL_DIR,
            "scenarios",
            scenario_key,
            "wepp",
            "output",
            "interchange",
            "loss_pw0.all_years.class_data.parquet",
        )

        if scenario_key == str(omni.base_scenario) and not _exists(scenario_path):
            return base_path
        return scenario_path if _exists(scenario_path) else (
            base_path if scenario_key == str(omni.base_scenario) else scenario_path
        )

    def year_set_for_scenario(self, omni: "Omni", scenario_name: Optional[Any]) -> Optional[Set[int]]:
        path = self.interchange_class_data_path_for_scenario(omni, scenario_name)
        if not os.path.isfile(path):
            return None

        try:
            df = pd.read_parquet(path, columns=["year"])
        except Exception as exc:
            omni.logger.debug("Failed to read years for scenario %s from %s: %s", scenario_name, path, exc)
            return None

        if "year" not in df:
            return None

        try:
            return set(int(y) for y in df["year"].dropna().unique().tolist())
        except Exception as exc:
            omni.logger.debug("Failed to normalize years for scenario %s from %s: %s", scenario_name, path, exc)
            return None

    def scenario_signature(self, omni: "Omni", scenario_def: "ScenarioDef") -> str:
        from wepppy.nodb.mods.omni.omni import OmniScenario

        sanitized: Dict[str, Any] = {}
        for key, value in scenario_def.items():
            if key == "type" and isinstance(value, OmniScenario):
                sanitized[key] = str(value)
            else:
                sanitized[key] = value
        return json.dumps(sanitized, sort_keys=True, default=str)

    def scenario_dependency_target(
        self,
        omni: "Omni",
        scenario: "OmniScenario",
        scenario_def: "ScenarioDef",
    ) -> Optional[str]:
        from wepppy.nodb.mods.omni.omni import OmniScenario

        if scenario == OmniScenario.Mulch:
            return scenario_def.get("base_scenario")
        return str(omni.base_scenario)

    def contrast_dependencies(self, omni: "Omni", contrast_name: str) -> "ContrastDependencies":
        from wepppy.nodb.mods.omni.omni import _hash_file_sha1

        control_key, target_key = self.contrast_scenario_keys(omni, contrast_name)
        scenarios = {control_key, target_key}
        dependencies: ContrastDependencies = {}
        for scenario_name in scenarios:
            loss_path = self.loss_pw0_path_for_scenario(omni, scenario_name)
            dependencies[scenario_name] = {
                "loss_path": loss_path,
                "sha1": _hash_file_sha1(loss_path),
            }
        return dependencies

    def contrast_scenario_keys(self, omni: "Omni", contrast_name: str) -> Tuple[str, str]:
        control_part, target_part = contrast_name.split("__to__")
        control_scenario_raw = control_part.split(",")[0]
        control_key = self.normalize_scenario_key(omni, control_scenario_raw)
        target_key = self.normalize_scenario_key(omni, target_part)
        return control_key, target_key
