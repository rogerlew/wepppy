from __future__ import annotations

import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni, OmniScenario, ScenarioDef


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
                landuse.build()
            with omni.timed(f"  {scenario_name}: build soils"):
                soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task)
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
            with omni.timed(f"  {scenario_name}: build landuse"):
                landuse.build()
            with omni.timed(f"  {scenario_name}: build soils"):
                soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task)
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
                landuse.build()
            with omni.timed(f"  {scenario_name}: build soils"):
                soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task)
            return

        if scenario_key == "mulch":
            omni.logger.info(f"  {scenario_name}: scenario == mulch")
            assert omni_base_scenario_name is not None, "Mulching scenario requires a base scenario"

            from wepppy.nodb.mods.treatments import Treatments

            with omni.timed(f"  {scenario_name}: applying treatments"):
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

            with omni.timed(f"  {scenario_name}: build soils"):
                soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task)
            return

        if scenario_key == "prescribed_fire":
            omni.logger.info(f"  {scenario_name}: scenario == prescribed fire")

            if disturbed.has_sbs:
                raise Exception("Cloned omni scenario should be undisturbed")

            from wepppy.nodb.mods.treatments import Treatments

            with omni.timed(f"  {scenario_name}: build soils"):
                soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task)

            with omni.timed(f"  {scenario_name}: applying treatments"):
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
            return

        if scenario_key == "thinning":
            omni.logger.info(f"  {scenario_name}: scenario == thinning")

            if disturbed.has_sbs:
                raise Exception("Cloned omni scenario should be undisturbed")

            from wepppy.nodb.mods.treatments import Treatments

            with omni.timed(f"  {scenario_name}: build soils"):
                soils.build(max_workers=omni.rq_job_pool_max_worker_per_scenario_task)

            with omni.timed(f"  {scenario_name}: applying treatments"):
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
