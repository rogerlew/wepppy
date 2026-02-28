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
from wepppy.runtime_paths.thaw_freeze import maintenance_lock as nodir_maintenance_lock

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import ContrastMapping, Omni, OmniScenario, ScenarioDef

_OMNI_LOCK_WAIT_SECONDS = 300.0
_OMNI_LOCK_RETRY_INTERVAL_SECONDS = 0.25


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
            with nodir_maintenance_lock(wd, root, purpose=purpose):
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
                    stack.enter_context(nodir_maintenance_lock(wd, root, purpose=f"{purpose}/{root}"))
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

                    treatments_domlc_d = {}
                    for topaz_id, dom in landuse.domlc_d.items():
                        if str(topaz_id).endswith("4"):
                            continue

                        man_summary = landuse.managements[dom]
                        disturbed_class = getattr(man_summary, "disturbed_class", "")
                        if "forest" in disturbed_class and "young" not in disturbed_class:
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
                    treatment_key = treatments.treatments_lookup[scenario_name]

                    treatments_domlc_d = {}
                    for topaz_id, dom in landuse.domlc_d.items():
                        if str(topaz_id).endswith("4"):
                            continue

                        man_summary = landuse.managements[dom]
                        disturbed_class = getattr(man_summary, "disturbed_class", "")
                        if "forest" in disturbed_class and "young" not in disturbed_class:
                            treatments_domlc_d[topaz_id] = treatment_key

                    treatments.treatments_domlc_d = treatments_domlc_d
                    treatments.build_treatments()

                _run_landuse_and_soils(_apply_treatments)
