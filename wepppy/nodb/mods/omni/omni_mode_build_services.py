from __future__ import annotations

from contextlib import ExitStack
import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple

from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.thaw_freeze import (
    maintenance_lock as nodir_maintenance_lock,
    maintenance_lock_scope_token as nodir_maintenance_lock_scope_token,
)

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import ContrastMapping, Omni, OmniScenario, ScenarioDef

_OMNI_LOCK_WAIT_SECONDS = 300.0
_OMNI_LOCK_RETRY_INTERVAL_SECONDS = 0.25
_OMNI_LOCK_SCOPE = "effective_root_path_compat"


def _require_directory_root(wd: str, root: str) -> None:
    resolved = nodir_resolve(wd, root, view="effective")
    if resolved is not None and getattr(resolved, "form", "dir") != "dir":
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_ACTIVE",
            message=f"{root} root is archive-backed; directory root required",
        )


def _run_with_directory_root_lock(
    wd: str,
    root: str,
    callback,
    *,
    purpose: str,
):
    _require_directory_root(wd, root)
    deadline = monotonic() + _OMNI_LOCK_WAIT_SECONDS
    while True:
        try:
            scope_token = nodir_maintenance_lock_scope_token(
                wd,
                root,
                scope=_OMNI_LOCK_SCOPE,
            )
            with nodir_maintenance_lock(
                wd,
                root,
                purpose=purpose,
                scope=_OMNI_LOCK_SCOPE,
                scope_token=scope_token,
            ):
                _require_directory_root(wd, root)
                return callback()
        except NoDirError as exc:
            if exc.code != "NODIR_LOCKED" or monotonic() >= deadline:
                raise
            sleep(min(_OMNI_LOCK_RETRY_INTERVAL_SECONDS, max(0.0, deadline - monotonic())))


def _run_with_directory_roots_lock(
    wd: str,
    roots: tuple[str, ...],
    callback,
    *,
    purpose: str,
):
    lock_roots = tuple(sorted({str(root) for root in roots}))
    for root in lock_roots:
        _require_directory_root(wd, root)
    with ExitStack() as stack:
        for root in lock_roots:
            deadline = monotonic() + _OMNI_LOCK_WAIT_SECONDS
            while True:
                try:
                    scope_token = nodir_maintenance_lock_scope_token(
                        wd,
                        root,
                        scope=_OMNI_LOCK_SCOPE,
                    )
                    stack.enter_context(
                        nodir_maintenance_lock(
                            wd,
                            root,
                            purpose=f"{purpose}/{root}",
                            scope=_OMNI_LOCK_SCOPE,
                            scope_token=scope_token,
                        )
                    )
                    break
                except NoDirError as exc:
                    if exc.code != "NODIR_LOCKED" or monotonic() >= deadline:
                        raise
                    sleep(min(_OMNI_LOCK_RETRY_INTERVAL_SECONDS, max(0.0, deadline - monotonic())))
        for root in lock_roots:
            _require_directory_root(wd, root)
        return callback()


class OmniModeBuildServices:
    """Dispatch Omni scenario/contrast builds by selection and scenario mode."""

    _SCENARIO_FILTER_MIN_SLOPE_FIELD = "filter_hill_min_slope_pct"
    _SCENARIO_FILTER_MAX_SLOPE_FIELD = "filter_hill_max_slope_pct"
    _SCENARIO_FILTER_BURN_FIELD = "filter_burn_severities"

    @staticmethod
    def _parse_optional_int_percent(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        raw_token = None
        if isinstance(value, str):
            raw_token = value.strip().replace("%", "")
            if not raw_token:
                return None
            numeric_source: Any = raw_token
        else:
            numeric_source = value

        try:
            parsed = float(numeric_source)
        except (TypeError, ValueError):
            raise ValueError("Scenario slope filters must be integer percentages")

        if parsed < 0:
            raise ValueError("Scenario slope filters must be >= 0")

        if parsed <= 1.0:
            if isinstance(value, float):
                parsed = parsed * 100.0
            elif raw_token is not None and "." in raw_token:
                parsed = parsed * 100.0

        if int(parsed) != parsed:
            raise ValueError("Scenario slope filters must be integer percentages")
        return int(parsed)

    @staticmethod
    def _parse_burn_severity_set(value: Any) -> Optional[Set[int]]:
        if value in (None, "", []):
            return None
        if isinstance(value, str):
            raw_items = [item.strip() for item in value.split(",")]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        else:
            raw_items = [value]

        parsed: Set[int] = set()
        for item in raw_items:
            if item in (None, ""):
                continue
            token = str(item).strip()
            if not token:
                continue
            try:
                burn = int(token)
            except (TypeError, ValueError) as exc:
                raise ValueError("Scenario burn filters must be integers in 0-3") from exc
            if burn not in {0, 1, 2, 3}:
                raise ValueError("Scenario burn filters must be integers in 0-3")
            parsed.add(burn)
        return parsed or None

    @staticmethod
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
            raise ValueError(f"Unknown burn class '{label}' while applying scenario filters")
        return mapping[name]

    def _parse_scenario_filter_mask(
        self,
        scenario_def: "ScenarioDef",
    ) -> Tuple[Optional[int], Optional[int], Optional[Set[int]]]:
        min_slope_pct = self._parse_optional_int_percent(
            scenario_def.get(self._SCENARIO_FILTER_MIN_SLOPE_FIELD)
        )
        max_slope_pct = self._parse_optional_int_percent(
            scenario_def.get(self._SCENARIO_FILTER_MAX_SLOPE_FIELD)
        )
        if (
            min_slope_pct is not None
            and max_slope_pct is not None
            and min_slope_pct > max_slope_pct
        ):
            raise ValueError(
                f"{self._SCENARIO_FILTER_MIN_SLOPE_FIELD} must be <= {self._SCENARIO_FILTER_MAX_SLOPE_FIELD}"
            )
        burn_set = self._parse_burn_severity_set(
            scenario_def.get(self._SCENARIO_FILTER_BURN_FIELD)
        )
        return min_slope_pct, max_slope_pct, burn_set

    def _passes_treatment_filter_mask(
        self,
        *,
        topaz_id: Any,
        watershed: Optional[Any],
        slope_lookup: Dict[str, float],
        min_slope_pct: Optional[int],
        max_slope_pct: Optional[int],
        burn_set: Optional[Set[int]],
        burn_landuse: Optional[Any],
        burn_lookup: Dict[str, int],
    ) -> bool:
        topaz_key = str(topaz_id)
        if watershed is not None and (min_slope_pct is not None or max_slope_pct is not None):
            slope = slope_lookup.get(topaz_key)
            if slope is None:
                slope = watershed.hillslope_slope(topaz_key)
                slope_lookup[topaz_key] = slope
            slope_pct = float(slope) * 100.0
            if min_slope_pct is not None and slope_pct < float(min_slope_pct):
                return False
            if max_slope_pct is not None and slope_pct > float(max_slope_pct):
                return False

        if burn_set is not None and burn_landuse is not None:
            burn_class = burn_lookup.get(topaz_key)
            if burn_class is None:
                burn_class = self._burn_value(burn_landuse.identify_burn_class(topaz_key))
                burn_lookup[topaz_key] = burn_class
            if burn_class not in burn_set:
                return False

        return True

    def build_contrasts_for_selection_mode(self, omni: "Omni", selection_mode: str) -> bool:
        if selection_mode == "user_defined_areas":
            omni._build_contrasts_user_defined_areas()
            return True
        if selection_mode == "user_defined_hillslope_groups":
            omni._build_contrasts_user_defined_hillslope_groups()
            return True
        if selection_mode == "stream_order":
            omni._build_contrasts_stream_order()
            return True
        return False

    def build_contrast_mapping(
        self,
        omni: "Omni",
        *,
        top2wepp: Dict[Any, Any],
        selected_topaz_ids: Set[Any],
        control_scenario: Optional[str],
        contrast_scenario: Optional[str],
        contrast_id: Any,
        control_label: Optional[Any] = None,
        contrast_label: Optional[Any] = None,
    ) -> Tuple[str, "ContrastMapping"]:
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR

        name_control = control_label if control_label is not None else control_scenario
        if contrast_label is not None:
            name_contrast = contrast_label
        elif contrast_scenario is None:
            name_contrast = omni.base_scenario
        else:
            name_contrast = contrast_scenario
        contrast_name = f"{name_control},{contrast_id}__to__{name_contrast}"

        selected_topaz_tokens = {str(value) for value in selected_topaz_ids}
        contrast: "ContrastMapping" = {}
        for topaz_id, wepp_id in top2wepp.items():
            scenario_name = contrast_scenario if str(topaz_id) in selected_topaz_tokens else control_scenario
            if scenario_name is None:
                wepp_id_path = _join(omni.wd, f"wepp/output/H{wepp_id}")
            else:
                wepp_id_path = _join(
                    omni.wd,
                    OMNI_REL_DIR,
                    "scenarios",
                    str(scenario_name),
                    "wepp",
                    "output",
                    f"H{wepp_id}",
                )
            contrast[topaz_id] = wepp_id_path

        return contrast_name, contrast

    def apply_scenario_mode(
        self,
        omni: "Omni",
        *,
        scenario_name: str,
        scenario: "OmniScenario",
        scenario_def: "ScenarioDef",
        new_wd: str,
        disturbed: Any,
        landuse: Any,
        soils: Any,
        omni_base_scenario_name: Optional[str],
    ) -> None:
        scenario_key = str(scenario)
        (
            min_slope_pct,
            max_slope_pct,
            burn_filter_set,
        ) = self._parse_scenario_filter_mask(scenario_def)
        watershed = None
        if min_slope_pct is not None or max_slope_pct is not None:
            from wepppy.nodb.core import Watershed

            watershed = Watershed.getInstance(omni.wd)
        slope_lookup: Dict[str, float] = {}
        burn_lookup: Dict[str, int] = {}

        def _run_landuse_and_soils(callback: Any) -> None:
            _run_with_directory_roots_lock(
                new_wd,
                ("landuse", "soils"),
                callback,
                purpose=f"omni-{scenario_key}-landuse-soils",
            )

        def _run_soils(callback: Any) -> None:
            _run_with_directory_root_lock(
                new_wd,
                "soils",
                callback,
                purpose=f"omni-{scenario_key}-soils",
            )

        if scenario_key in {"uniform_low", "uniform_moderate", "uniform_high"}:
            sbs = None
            if scenario_key == "uniform_low":
                sbs = 1
            elif scenario_key == "uniform_moderate":
                sbs = 2
            elif scenario_key == "uniform_high":
                sbs = 3

            omni.logger.info(f" {scenario_name}: scenario == uniform burn severity -> {sbs}")

            with omni.timed(f"  {scenario_name}: build uniform sbs {sbs}"):
                sbs_fn = disturbed.build_uniform_sbs(int(sbs))
            with omni.timed(f"  {scenario_name}: validate sbs {sbs_fn}"):
                disturbed.validate(sbs_fn, mode=1, uniform_severity=int(sbs))
            with omni.timed(f"  {scenario_name}: build landuse and soils"):
                _run_landuse_and_soils(
                    lambda: (
                        landuse.build(),
                        soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task),
                    ),
                )
            return

        if scenario_key == "undisturbed":
            omni.logger.info(f" {scenario_name}: scenario == undisturbed")

            runid_leaf = str(omni.runid).split(";;")[-1] if omni.runid else ""
            wd_leaf = os.path.basename(os.path.normpath(omni.wd))
            is_base_project = runid_leaf == "_base" or wd_leaf == "_base"

            if not omni.has_sbs and not is_base_project:
                raise Exception("Undisturbed scenario requires a base scenario with sbs")
            if not omni.has_sbs and is_base_project:
                omni.logger.info(f"  {scenario_name}: skipping sbs guard for _base project context")

            with omni.timed(f"  {scenario_name}: remove sbs"):
                disturbed.remove_sbs()
            with omni.timed(f"  {scenario_name}: build landuse and soils"):
                _run_landuse_and_soils(
                    lambda: (
                        landuse.build(),
                        soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task),
                    ),
                )
            return

        if scenario_key == "sbs_map":
            omni.logger.info(f" {scenario_name}: scenario == sbs")

            sbs_file_path = scenario_def.get("sbs_file_path")
            if not _exists(sbs_file_path):
                raise FileNotFoundError(f"'{sbs_file_path}' not found!")

            with omni.timed(f"  {scenario_name}: copy sbs to disturbed dir from _limbo"):
                sbs_fn = _split(sbs_file_path)[-1]
                new_sbs_file_path = _join(disturbed.disturbed_dir, sbs_fn)
                shutil.copyfile(sbs_file_path, new_sbs_file_path)
                os.remove(sbs_file_path)

            with omni.timed(f"  {scenario_name}: validate sbs {sbs_fn}"):
                disturbed.validate(sbs_fn, mode=0)
            with omni.timed(f"  {scenario_name}: build landuse and soils"):
                _run_landuse_and_soils(
                    lambda: (
                        landuse.build(),
                        soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task),
                    ),
                )
            return

        if scenario_key == "mulch":
            omni.logger.info(f"  {scenario_name}: scenario == mulch")
            assert omni_base_scenario_name is not None, "Mulching scenario requires a base scenario"

            from wepppy.nodb.mods.treatments import Treatments

            with omni.timed(f"  {scenario_name}: applying treatments"):
                def _apply_treatments() -> None:
                    treatments = Treatments.getInstance(new_wd)
                    ground_cover_increase = scenario_def.get("ground_cover_increase")
                    treatment_key = treatments.treatments_lookup[f"mulch_{ground_cover_increase}".replace("%", "")]

                    treatments_domlc_d = {}
                    for topaz_id, dom in landuse.domlc_d.items():
                        if str(topaz_id).endswith("4"):
                            continue

                        man_summary = landuse.managements[dom]
                        disturbed_class = getattr(man_summary, "disturbed_class", "")
                        if isinstance(disturbed_class, str) and "fire" in disturbed_class:
                            if not self._passes_treatment_filter_mask(
                                topaz_id=topaz_id,
                                watershed=watershed,
                                slope_lookup=slope_lookup,
                                min_slope_pct=min_slope_pct,
                                max_slope_pct=max_slope_pct,
                                burn_set=burn_filter_set,
                                burn_landuse=landuse,
                                burn_lookup=burn_lookup,
                            ):
                                continue
                            treatments_domlc_d[topaz_id] = treatment_key

                    treatments.treatments_domlc_d = treatments_domlc_d
                    treatments.build_treatments()

                _run_landuse_and_soils(
                    _apply_treatments,
                )

            with omni.timed(f"  {scenario_name}: build soils"):
                _run_soils(
                    lambda: soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task),
                )
            return

        if scenario_key == "prescribed_fire":
            omni.logger.info(f"  {scenario_name}: scenario == prescribed fire")

            if disturbed.has_sbs:
                raise Exception("Cloned omni scenario should be undisturbed")

            from wepppy.nodb.mods.treatments import Treatments

            with omni.timed(f"  {scenario_name}: build soils"):
                _run_soils(
                    lambda: soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task),
                )

            with omni.timed(f"  {scenario_name}: applying treatments"):
                def _apply_treatments() -> None:
                    treatments = Treatments.getInstance(new_wd)
                    treatments_lookup = treatments.treatments_lookup
                    treatment_key = treatments_lookup.get(scenario_key)
                    if treatment_key is None:
                        available = ", ".join(sorted(treatments_lookup)) if treatments_lookup else "none"
                        raise ValueError(
                            "Prescribed fire scenario requires a treatment mapping for 'prescribed_fire', "
                            "but the current landuse mapping does not define it. "
                            f"Available treatment keys: {available}."
                        )

                    burn_source_landuse = None
                    if burn_filter_set is not None:
                        if omni.has_sbs:
                            from wepppy.nodb.core import Landuse

                            try:
                                burn_source_landuse = Landuse.getInstance(omni.wd)
                            except Exception as exc:
                                omni.logger.info(
                                    "  %s: unable to load base/project burn classes, "
                                    "ignoring burn-severity scenario filter (%s)",
                                    scenario_name,
                                    exc,
                                )
                        else:
                            omni.logger.info(
                                "  %s: project/base SBS burn classes unavailable; "
                                "ignoring burn-severity scenario filter",
                                scenario_name,
                            )

                    treatments_domlc_d = {}
                    for topaz_id, dom in landuse.domlc_d.items():
                        if str(topaz_id).endswith("4"):
                            continue

                        man_summary = landuse.managements[dom]
                        disturbed_class = getattr(man_summary, "disturbed_class", "")
                        if "forest" in disturbed_class and "young" not in disturbed_class:
                            if not self._passes_treatment_filter_mask(
                                topaz_id=topaz_id,
                                watershed=watershed,
                                slope_lookup=slope_lookup,
                                min_slope_pct=min_slope_pct,
                                max_slope_pct=max_slope_pct,
                                burn_set=burn_filter_set,
                                burn_landuse=burn_source_landuse,
                                burn_lookup=burn_lookup,
                            ):
                                continue
                            treatments_domlc_d[topaz_id] = treatment_key

                    treatments.treatments_domlc_d = treatments_domlc_d
                    treatments.build_treatments()

                _run_landuse_and_soils(
                    _apply_treatments,
                )
            return

        if scenario_key == "thinning":
            omni.logger.info(f"  {scenario_name}: scenario == thinning")

            if disturbed.has_sbs:
                raise Exception("Cloned omni scenario should be undisturbed")

            from wepppy.nodb.mods.treatments import Treatments

            with omni.timed(f"  {scenario_name}: build soils"):
                _run_soils(
                    lambda: soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task),
                )

            with omni.timed(f"  {scenario_name}: applying treatments"):
                def _apply_treatments() -> None:
                    treatments = Treatments.getInstance(new_wd)
                    canopy_cover = str(scenario_def.get("canopy_cover", "")).replace("%", "")
                    ground_cover = str(scenario_def.get("ground_cover", "")).replace("%", "")
                    treatment_lookup_key = f"thinning_{canopy_cover}_{ground_cover}"
                    treatment_key = treatments.treatments_lookup[treatment_lookup_key]

                    burn_source_landuse = None
                    if burn_filter_set is not None:
                        if omni.has_sbs:
                            from wepppy.nodb.core import Landuse

                            try:
                                burn_source_landuse = Landuse.getInstance(omni.wd)
                            except Exception as exc:
                                omni.logger.info(
                                    "  %s: unable to load base/project burn classes, "
                                    "ignoring burn-severity scenario filter (%s)",
                                    scenario_name,
                                    exc,
                                )
                        else:
                            omni.logger.info(
                                "  %s: project/base SBS burn classes unavailable; "
                                "ignoring burn-severity scenario filter",
                                scenario_name,
                            )

                    treatments_domlc_d = {}
                    for topaz_id, dom in landuse.domlc_d.items():
                        if str(topaz_id).endswith("4"):
                            continue

                        man_summary = landuse.managements[dom]
                        disturbed_class = getattr(man_summary, "disturbed_class", "")
                        if "forest" in disturbed_class and "young" not in disturbed_class:
                            if not self._passes_treatment_filter_mask(
                                topaz_id=topaz_id,
                                watershed=watershed,
                                slope_lookup=slope_lookup,
                                min_slope_pct=min_slope_pct,
                                max_slope_pct=max_slope_pct,
                                burn_set=burn_filter_set,
                                burn_landuse=burn_source_landuse,
                                burn_lookup=burn_lookup,
                            ):
                                continue
                            treatments_domlc_d[topaz_id] = treatment_key

                    treatments.treatments_domlc_d = treatments_domlc_d
                    treatments.build_treatments()

                _run_landuse_and_soils(_apply_treatments)
