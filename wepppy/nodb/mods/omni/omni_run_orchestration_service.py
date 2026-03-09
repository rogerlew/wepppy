from __future__ import annotations

import time
from os.path import join as _join
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from wepppy.nodb.base import NoDbAlreadyLockedError

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, ScenarioDef


class OmniRunOrchestrationService:
    """Coordinate scenario/contrast run orchestration while keeping facade seams stable."""

    def run_omni_contrasts(self, omni: "Omni") -> None:
        from wepppy.nodb.mods.omni.omni import _run_contrast

        omni.logger.info("run_omni_contrasts")

        def _set_dependency_tree_with_retry(tree: Dict[str, Dict[str, Any]]) -> None:
            max_tries = 5
            for attempt in range(max_tries):
                try:
                    with omni.locked():
                        omni._contrast_dependency_tree = tree
                except NoDbAlreadyLockedError:
                    if attempt + 1 == max_tries:
                        raise
                    time.sleep(1.0)
                else:
                    break

        if not omni.contrast_names:
            omni.logger.info("  run_omni_contrasts: No contrasts to run")
            if omni.contrast_dependency_tree:
                _set_dependency_tree_with_retry({})
            omni._clean_stale_contrast_runs([])
            return

        dependency_tree: Dict[str, Dict[str, Any]] = dict(omni.contrast_dependency_tree)
        active_contrasts: Set[str] = set()
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]] = {}

        contrast_names: List[Optional[str]] = omni.contrast_names or []
        active_ids = [
            contrast_id
            for contrast_id, contrast_name in enumerate(contrast_names, start=1)
            if contrast_name
        ]
        total_contrasts = len(active_ids)
        output_options = omni.contrast_output_options()

        if total_contrasts == 0:
            omni.logger.info("  run_omni_contrasts: No contrasts to run")
            if dependency_tree:
                dependency_tree.clear()
                _set_dependency_tree_with_retry(dependency_tree)
            omni._clean_stale_contrast_runs(active_ids)
            return

        for ordinal, contrast_id in enumerate(active_ids, start=1):
            contrast_name = contrast_names[contrast_id - 1]
            if not contrast_name:
                continue
            active_contrasts.add(contrast_name)
            skip_reason = omni._contrast_landuse_skip_reason(
                contrast_id,
                contrast_name,
                landuse_cache=landuse_cache,
            )
            if skip_reason:
                omni.logger.info(
                    "  run_omni_contrasts: %s skipped (%s)",
                    contrast_name,
                    skip_reason,
                )
                omni._clean_contrast_run(contrast_id)
                dependency_tree.pop(contrast_name, None)
                continue
            run_status = omni._contrast_run_status(contrast_id, contrast_name)
            if run_status == "up_to_date":
                omni.logger.info("  run_omni_contrasts: %s up-to-date, skipping", contrast_name)
                continue
            if run_status == "in_progress":
                omni.logger.info("  run_omni_contrasts: %s already running, skipping", contrast_name)
                continue

            try:
                contrast_payload = omni._load_contrast_sidecar(contrast_id)
            except FileNotFoundError:
                omni.logger.info(
                    "  run_omni_contrasts: Missing sidecar for contrast_id=%s, skipping.",
                    contrast_id,
                )
                continue

            omni.logger.info(
                "  run_omni_contrasts: Running contrast %s of %s (id=%s): %s",
                ordinal,
                total_contrasts,
                contrast_id,
                contrast_name,
            )
            control_key, contrast_key = omni._contrast_scenario_keys(contrast_name)
            omni_wd = _run_contrast(
                str(contrast_id),
                contrast_name,
                contrast_payload,
                omni.wd,
                omni.runid,
                control_key,
                contrast_key,
                output_options=output_options,
            )
            omni._post_omni_run(omni_wd, contrast_name)

            dependency_entry = omni._contrast_dependency_entry(contrast_id, contrast_name)
            dependency_tree[contrast_name] = dependency_entry
            _set_dependency_tree_with_retry(dependency_tree)

        stale = set(dependency_tree.keys()) - active_contrasts
        for contrast_name in stale:
            dependency_tree.pop(contrast_name, None)
        _set_dependency_tree_with_retry(dependency_tree)
        omni._clean_stale_contrast_runs(active_ids)

    def run_omni_contrast(
        self,
        omni: "Omni",
        contrast_id: int,
        *,
        rq_job_id: Optional[str] = None,
    ) -> str:
        from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR, _run_contrast

        omni.logger.info(f"run_omni_contrast {contrast_id}")
        contrast_names = omni.contrast_names or []
        if contrast_id < 1 or contrast_id > len(contrast_names):
            raise ValueError(f"Contrast id {contrast_id} is out of range")
        contrast_name = contrast_names[contrast_id - 1]
        if not contrast_name:
            raise ValueError(f"Contrast id {contrast_id} is skipped")

        skip_reason = omni._contrast_landuse_skip_reason(contrast_id, contrast_name)
        if skip_reason:
            omni.logger.info("run_omni_contrast: %s skipped (%s)", contrast_name, skip_reason)
            omni._clean_contrast_run(contrast_id)
            omni._remove_contrast_dependency_entry(contrast_name)
            omni._clear_contrast_run_status(contrast_id)
            return _join(omni.wd, OMNI_REL_DIR, "contrasts", str(contrast_id))

        contrast_payload = omni._load_contrast_sidecar(contrast_id)
        control_key, contrast_key = omni._contrast_scenario_keys(contrast_name)
        output_options = omni.contrast_output_options()
        omni._write_contrast_run_status(
            contrast_id,
            contrast_name,
            "started",
            job_id=rq_job_id,
        )
        try:
            omni_wd = _run_contrast(
                str(contrast_id),
                contrast_name,
                contrast_payload,
                omni.wd,
                omni.runid,
                control_key,
                contrast_key,
                output_options=output_options,
            )
            omni._post_omni_run(omni_wd, contrast_name)
            dependency_entry = omni._contrast_dependency_entry(contrast_id, contrast_name)
            omni._update_contrast_dependency_tree(contrast_name, dependency_entry)
        except Exception as exc:  # Boundary: status tracking must record any run failure before re-raising.
            omni._write_contrast_run_status(
                contrast_id,
                contrast_name,
                "failed",
                job_id=rq_job_id,
                error=str(exc),
            )
            raise
        omni._write_contrast_run_status(
            contrast_id,
            contrast_name,
            "completed",
            job_id=rq_job_id,
        )
        return omni_wd

    @staticmethod
    def _normalize_start_year(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            if isinstance(value, str) and value.strip() == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def run_omni_scenario(
        self,
        omni: "Omni",
        scenario_def: "ScenarioDef",
    ) -> tuple[str, str]:
        import os

        from wepppy.nodb.core import Climate, Landuse, Soils, Wepp
        from wepppy.nodb.mods.disturbed import Disturbed
        from wepppy.nodb.mods.omni.omni import (
            OmniScenario,
            _OMNI_MODE_BUILD_SERVICES,
            _omni_clone,
            _omni_clone_sibling,
            _post_watershed_run_cleanup,
            _scenario_name_from_scenario_definition,
            run_wepp_hillslope_interchange,
        )

        wd = omni.wd
        base_scenario = omni.base_scenario
        scenario_name = _scenario_name_from_scenario_definition(scenario_def)

        scenario = OmniScenario.parse(scenario_def.get("type"))
        omni_base_scenario_name = scenario_def.get("base_scenario", None)

        if scenario in [OmniScenario.PrescribedFire, OmniScenario.Thinning]:
            if base_scenario != OmniScenario.Undisturbed:
                omni_base_scenario_name = "undisturbed"
                omni.logger.info(f"  {scenario_name}: omni_base_scenario_name:{omni_base_scenario_name}")

        os.chdir(wd)

        if not isinstance(scenario, OmniScenario):
            raise TypeError(f"Invalid omni scenario type: {scenario!r}")
        with omni.timed(f"  {scenario_name}: _omni_clone({scenario_def}, {wd}, {omni.runid})"):
            new_wd = _omni_clone(scenario_def, wd, omni.runid)

        if omni_base_scenario_name is not None:
            if not omni_base_scenario_name == str(base_scenario):
                with omni.timed(
                    f"  {scenario_name}: _omni_clone_sibling({new_wd}, {omni_base_scenario_name}, {omni.runid}, {omni.wd})"
                ):
                    _omni_clone_sibling(new_wd, omni_base_scenario_name, omni.runid, omni.wd)

        disturbed = Disturbed.getInstance(new_wd)
        landuse = Landuse.getInstance(new_wd)
        soils = Soils.getInstance(new_wd)

        _OMNI_MODE_BUILD_SERVICES.apply_scenario_mode(
            omni,
            scenario_name=scenario_name,
            scenario=scenario,
            scenario_def=scenario_def,
            new_wd=new_wd,
            disturbed=disturbed,
            landuse=landuse,
            soils=soils,
            omni_base_scenario_name=omni_base_scenario_name,
        )

        landuse.build_managements()
        wepp = Wepp.getInstance(new_wd)

        man_relpath = ""
        cli_relpath = os.path.relpath(omni.runs_dir, wepp.runs_dir)
        slp_relpath = os.path.relpath(omni.runs_dir, wepp.runs_dir)
        sol_relpath = ""

        if not cli_relpath.endswith("/"):
            cli_relpath += "/"
        if not slp_relpath.endswith("/"):
            slp_relpath += "/"

        with omni.timed(f"  {scenario_name}: prep hillslopes"):
            wepp.prep_hillslopes(
                man_relpath=man_relpath,
                cli_relpath=cli_relpath,
                slp_relpath=slp_relpath,
                sol_relpath=sol_relpath,
                max_workers=omni.rq_job_pool_max_worker_per_scenario_task,
            )
        with omni.timed(f"  {scenario_name}: run hillslopes"):
            wepp.run_hillslopes(
                man_relpath=man_relpath,
                cli_relpath=cli_relpath,
                slp_relpath=slp_relpath,
                sol_relpath=sol_relpath,
                max_workers=omni.rq_job_pool_max_worker_per_scenario_task,
            )

        with omni.timed(f"  {scenario_name}: run hillslope interchange"):
            start_year = None
            climate = Climate.getInstance(new_wd)
            for candidate in (
                getattr(climate, "observed_start_year", None),
                getattr(climate, "future_start_year", None),
            ):
                normalized = self._normalize_start_year(candidate)
                if normalized is not None:
                    start_year = normalized
                    break
            # Watershed routing still depends on the raw H*.pass.dat files.
            # Deleting hillslope sources immediately after interchange breaks
            # the subsequent watershed run for omni scenarios.
            delete_after_interchange = bool(
                omni.delete_after_interchange and not wepp.run_wepp_watershed
            )
            run_wepp_hillslope_interchange(
                wepp.output_dir,
                start_year=start_year,
                delete_after_interchange=delete_after_interchange,
            )

        with omni.timed(f"  {scenario_name}: prep watershed"):
            wepp.prep_watershed()

        with omni.timed(f"  {scenario_name}: run watershed"):
            wepp.run_watershed()
            _post_watershed_run_cleanup(wepp)

        return new_wd, scenario_name

    def run_omni_scenarios(self, omni: "Omni") -> None:
        from wepppy.nodb.mods.omni.omni import (
            OmniScenario,
            ScenarioDependency,
            _hash_file_sha1,
            _scenario_name_from_scenario_definition,
        )

        omni.logger.info("run_omni_scenarios")

        if not omni.scenarios:
            omni.logger.info("  run_omni_scenarios: No scenarios to run")
            raise RuntimeError("No scenarios to run")

        dependency_tree: ScenarioDependency = dict(omni.scenario_dependency_tree)

        run_states: List[Dict[str, Any]] = []
        omni.scenario_run_state = run_states

        active_scenarios = set()
        processed_scenarios = set()
        base_scenario_key = str(omni.base_scenario)

        def dependency_info(scenario_enum: Any, scenario_def: "ScenarioDef"):
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            active_scenarios.add(scenario_name)
            dependency_target = omni._scenario_dependency_target(scenario_enum, scenario_def)
            dependency_path = omni._loss_pw0_path_for_scenario(dependency_target)
            dependency_hash = _hash_file_sha1(dependency_path)
            signature = omni._scenario_signature(scenario_def)
            base_years = omni._year_set_for_scenario(base_scenario_key)
            scenario_years = omni._year_set_for_scenario(scenario_name)
            years_match = (
                base_years is not None and
                scenario_years is not None and
                scenario_years == base_years
            )
            prev_entry = dependency_tree.get(scenario_name)
            up_to_date = (
                prev_entry is not None and
                prev_entry.get("dependency_sha1") == dependency_hash and
                prev_entry.get("signature") == signature
            )
            return scenario_name, dependency_target, dependency_path, dependency_hash, signature, up_to_date, years_match

        for scenario_def in omni.scenarios:
            scenario_enum = OmniScenario.parse(scenario_def.get("type"))
            if scenario_enum == OmniScenario.Mulch:
                continue

            if omni.base_scenario != OmniScenario.Undisturbed and scenario_enum in [
                OmniScenario.Thinning,
                OmniScenario.PrescribedFire,
            ]:
                continue

            (
                scenario_name,
                dependency_target,
                dependency_path,
                dependency_hash,
                signature,
                up_to_date,
                years_match,
            ) = dependency_info(scenario_enum, scenario_def)
            processed_scenarios.add(scenario_name)

            target_key = omni._normalize_scenario_key(dependency_target)

            if up_to_date and years_match:
                omni.logger.info(f"  run_omni_scenarios: {scenario_name} dependency unchanged, skipping")
                ts = time.time()
                dependency_tree[scenario_name] = {
                    "dependency_target": target_key,
                    "dependency_path": dependency_path,
                    "dependency_sha1": dependency_hash,
                    "signature": signature,
                    "timestamp": ts,
                }
                omni.scenario_dependency_tree = dependency_tree
                run_states.append(
                    {
                        "scenario": scenario_name,
                        "status": "skipped",
                        "reason": "dependency_unchanged",
                        "dependency_target": target_key,
                        "dependency_path": dependency_path,
                        "dependency_sha1": dependency_hash,
                        "timestamp": ts,
                    }
                )
                omni.scenario_run_state = run_states
                continue

            run_reason = "dependency_changed"
            if up_to_date and not years_match:
                run_reason = "year_set_mismatch"
                omni.logger.info(
                    f"  run_omni_scenarios: {scenario_name} year set mismatch vs base scenario, rerunning"
                )
            else:
                omni.logger.info(f"  run_omni_scenarios: {scenario_name}")
            omni_dir, scenario_name = omni.run_omni_scenario(scenario_def)
            omni._post_omni_run(omni_dir, scenario_name)

            updated_hash = _hash_file_sha1(dependency_path)
            ts = time.time()
            dependency_tree[scenario_name] = {
                "dependency_target": target_key,
                "dependency_path": dependency_path,
                "dependency_sha1": updated_hash,
                "signature": signature,
                "timestamp": ts,
            }
            omni.scenario_dependency_tree = dependency_tree
            run_states.append(
                {
                    "scenario": scenario_name,
                    "status": "executed",
                    "reason": run_reason,
                    "dependency_target": target_key,
                    "dependency_path": dependency_path,
                    "dependency_sha1": updated_hash,
                    "timestamp": ts,
                }
            )
            omni.scenario_run_state = run_states

        for scenario_def in omni.scenarios:
            scenario_enum = OmniScenario.parse(scenario_def.get("type"))
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            if scenario_name in processed_scenarios:
                continue

            (
                scenario_name,
                dependency_target,
                dependency_path,
                dependency_hash,
                signature,
                up_to_date,
                years_match,
            ) = dependency_info(scenario_enum, scenario_def)
            processed_scenarios.add(scenario_name)

            target_key = omni._normalize_scenario_key(dependency_target)

            if up_to_date and years_match:
                omni.logger.info(f"  run_omni_scenarios: {scenario_name} dependency unchanged, skipping")
                ts = time.time()
                dependency_tree[scenario_name] = {
                    "dependency_target": target_key,
                    "dependency_path": dependency_path,
                    "dependency_sha1": dependency_hash,
                    "signature": signature,
                    "timestamp": ts,
                }
                omni.scenario_dependency_tree = dependency_tree
                run_states.append(
                    {
                        "scenario": scenario_name,
                        "status": "skipped",
                        "reason": "dependency_unchanged",
                        "dependency_target": target_key,
                        "dependency_path": dependency_path,
                        "dependency_sha1": dependency_hash,
                        "timestamp": ts,
                    }
                )
                omni.scenario_run_state = run_states
                continue

            run_reason = "dependency_changed"
            if up_to_date and not years_match:
                run_reason = "year_set_mismatch"
                omni.logger.info(
                    f"  run_omni_scenarios: {scenario_name} year set mismatch vs base scenario, rerunning"
                )
            else:
                omni.logger.info(f"  run_omni_scenarios: {scenario_name}")
            omni_dir, scenario_name = omni.run_omni_scenario(scenario_def)
            omni._post_omni_run(omni_dir, scenario_name)

            updated_hash = _hash_file_sha1(dependency_path)
            ts = time.time()
            dependency_tree[scenario_name] = {
                "dependency_target": target_key,
                "dependency_path": dependency_path,
                "dependency_sha1": updated_hash,
                "signature": signature,
                "timestamp": ts,
            }
            omni.scenario_dependency_tree = dependency_tree
            run_states.append(
                {
                    "scenario": scenario_name,
                    "status": "executed",
                    "reason": run_reason,
                    "dependency_target": target_key,
                    "dependency_path": dependency_path,
                    "dependency_sha1": updated_hash,
                    "timestamp": ts,
                }
            )
            omni.scenario_run_state = run_states

        stale = set(dependency_tree.keys()) - active_scenarios
        for scenario_name in stale:
            dependency_tree.pop(scenario_name, None)
        omni.scenario_dependency_tree = dependency_tree

        omni.logger.info("  run_omni_scenarios: compiling hillslope summaries")
        omni.compile_hillslope_summaries()
        omni.logger.info("  run_omni_scenarios: compiling channel summaries")
        omni.compile_channel_summaries()
        omni.logger.info("  run_omni_scenarios: compiling scenario report")
        omni.scenarios_report()
