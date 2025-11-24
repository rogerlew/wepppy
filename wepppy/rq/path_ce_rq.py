"""RQ task wrappers for PATH cost-effective optimization workflows."""

from __future__ import annotations

import inspect
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Tuple

from rq import get_current_job

from wepppy.nodb.mods.omni.omni import Omni, OmniScenario, _scenario_name_from_scenario_definition
from wepppy.nodb.mods.path_ce import PathCostEffective
from wepppy.nodb.mods.path_ce.presets import PATH_CE_BASELINE_SCENARIO, build_path_omni_scenarios
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.rq.exception_logging import with_exception_logging

TIMEOUT: int = 43_200


def _hydrate_existing_scenarios(omni: Omni) -> List[Tuple[OmniScenario, Dict[str, Any]]]:
    hydrated: List[Tuple[OmniScenario, Dict[str, Any]]] = []
    for scenario_def in omni.scenarios:
        scenario_type = scenario_def.get("type")
        try:
            scenario_enum = OmniScenario.parse(scenario_type)
        except KeyError:
            continue
        hydrated.append((scenario_enum, dict(scenario_def)))
    return hydrated


def _hydrate_required_scenarios(base_scenario: str) -> List[Tuple[OmniScenario, Dict[str, Any]]]:
    required: List[Tuple[OmniScenario, Dict[str, Any]]] = []
    for payload in build_path_omni_scenarios(base_scenario):
        scenario_type = payload.get("type")
        scenario_enum = OmniScenario.parse(scenario_type)
        scenario_payload = dict(payload)
        scenario_payload["type"] = scenario_type
        required.append((scenario_enum, scenario_payload))
    return required


def _merge_scenario_sets(
    existing: Iterable[Tuple[OmniScenario, Dict[str, Any]]],
    required: Iterable[Tuple[OmniScenario, Dict[str, Any]]],
) -> List[Tuple[OmniScenario, Dict[str, Any]]]:
    merged: "OrderedDict[str, Tuple[OmniScenario, Dict[str, Any]]]" = OrderedDict()
    for entry in existing:
        scenario_enum, payload = entry
        try:
            scenario_name = _scenario_name_from_scenario_definition(payload)
        except Exception:
            continue
        merged[scenario_name] = (scenario_enum, payload)
    for entry in required:
        scenario_enum, payload = entry
        scenario_name = _scenario_name_from_scenario_definition(payload)
        merged[scenario_name] = (scenario_enum, payload)
    return list(merged.values())


@with_exception_logging
def run_path_cost_effective_rq(runid: str) -> Dict[str, Any]:
    """Run the PATH cost-effective optimization workflow for the given project.

    Args:
        runid: Identifier used to locate the working directory.

    Returns:
        Serialized solver payload including cost summaries and artifact paths.
    """
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{runid}:path_ce"
    StatusMessenger.publish(status_channel, f"rq:{job.id} STARTED {func_name}({runid})")

    wd = get_wd(runid)
    prep = RedisPrep.tryGetInstance(wd)
    if prep is not None:
        try:
            prep.set_rq_job_id("run_path_ce", job.id)
            prep.remove_timestamp(TaskEnum.run_path_cost_effective)
        except Exception:
            pass

    controller = PathCostEffective.getInstance(wd)
    omni = Omni.getInstance(wd)

    try:
        StatusMessenger.publish(status_channel, f"rq:{job.id} STATUS Provisioning Omni scenarios for PATH")

        if prep is not None:
            try:
                prep.remove_timestamp(TaskEnum.run_omni_scenarios)
            except Exception:
                pass

        controller.set_status("running", message="Provisioning Omni scenarios", progress=0.05)
        base_scenario = str(controller.config.get("post_fire_scenario") or PATH_CE_BASELINE_SCENARIO)

        existing = _hydrate_existing_scenarios(omni)
        required = _hydrate_required_scenarios(base_scenario)
        omni_inputs = _merge_scenario_sets(existing, required)
        omni.parse_scenarios(omni_inputs)

        StatusMessenger.publish(status_channel, f"rq:{job.id} STATUS Running Omni scenarios for PATH")
        controller.set_status("running", message="Running Omni scenarios", progress=0.2)
        omni.run_omni_scenarios()

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.run_omni_scenarios)
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f"rq:{job.id} STATUS Preparing PATH Cost-Effective inputs")
        result = controller.run()

        if prep is not None:
            try:
                prep.timestamp(TaskEnum.run_path_cost_effective)
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f"rq:{job.id} COMPLETED {func_name}({runid})")
        StatusMessenger.publish(status_channel, f"rq:{job.id} TRIGGER path_ce PATH_CE_RUN_COMPLETE")
        return result
    except Exception as exc:
        try:
            controller.set_status("failed", message=str(exc))
        except Exception:
            pass
        StatusMessenger.publish(status_channel, f"rq:{job.id} EXCEPTION {func_name}({runid})")
        raise
