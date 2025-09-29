import inspect
import os
import socket
import time
from copy import deepcopy
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import redis
from rq import Queue, get_current_job

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.mods.omni.omni import (
    _hash_file_sha1,
    _scenario_name_from_scenario_definition,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except Exception:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 43_200


def _scenario_payload_for_job(scenario_def: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deepcopy with the ``type`` coerced to ``OmniScenario`` so workers match expectations."""
    payload = deepcopy(scenario_def)
    scenario_type = payload.get('type')

    if isinstance(scenario_type, OmniScenario):
        return payload

    if scenario_type is None:
        raise ValueError('scenario_def is missing required key "type"')

    if isinstance(scenario_type, int):
        payload['type'] = OmniScenario(scenario_type)
    else:
        payload['type'] = OmniScenario.parse(scenario_type)

    return payload


class OmniLockTimeout(Exception):
    pass


@contextmanager
def _locked_with_retry(omni: Omni, timeout: float = 30.0, poll_interval: float = 0.5):
    """Acquire the Omni lock, retrying until timeout elapses."""
    deadline = time.time() + timeout
    while True:
        try:
            omni.lock()
            break
        except NoDbAlreadyLockedError as exc:
            if time.time() >= deadline:
                raise OmniLockTimeout(
                    f"Timed out waiting for Omni lock after {timeout}s"
                ) from exc
            time.sleep(poll_interval)
        except Exception:
            raise

    try:
        yield
    except Exception:
        omni.unlock()
        raise
    else:
        omni.dump_and_unlock()


def _update_dependency_state(
    omni: Omni,
    scenario_name: str,
    dependency_entry: Dict[str, Any],
    run_state_entry: Dict[str, Any],
) -> None:
    """Persist dependency metadata and run state for a scenario within one lock."""
    with _locked_with_retry(omni):
        dependency_tree = dict(getattr(omni, '_scenario_dependency_tree', {}) or {})
        dependency_tree[scenario_name] = dependency_entry
        omni._scenario_dependency_tree = dependency_tree

        run_states = list(getattr(omni, '_scenario_run_state', []) or [])
        run_states.append(run_state_entry)
        omni._scenario_run_state = run_states


def run_omni_scenario_rq(
    runid: str,
    scenario: Dict[str, Any],
    *,
    dependency_target: Optional[str] = None,
    dependency_path: Optional[str] = None,
    signature: Optional[str] = None,
    run_state_reason: str = 'dependency_changed',
):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        start_ts = time.time()

        omni = Omni.getInstance(wd)

        scenario_payload = _scenario_payload_for_job(scenario)
        scenario_enum = scenario_payload['type']

        scenario_name = _scenario_name_from_scenario_definition(scenario_payload)

        dependency_target_key = dependency_target
        dependency_loss_path = dependency_path
        scenario_signature = signature

        if dependency_target_key is None or dependency_loss_path is None or scenario_signature is None:
            dependency_target_raw = omni._scenario_dependency_target(scenario_enum, scenario_payload)
            dependency_target_key = omni._normalize_scenario_key(dependency_target_raw)
            dependency_loss_path = omni._loss_pw0_path_for_scenario(dependency_target_raw)
            scenario_signature = omni._scenario_signature(scenario_payload)

        omni.run_omni_scenario(scenario_payload)

        dependency_sha1 = _hash_file_sha1(dependency_loss_path)
        timestamp = time.time()

        dependency_entry = {
            'dependency_target': dependency_target_key,
            'dependency_path': dependency_loss_path,
            'dependency_sha1': dependency_sha1,
            'signature': scenario_signature,
            'timestamp': timestamp,
        }
        run_state_entry = {
            'scenario': scenario_name,
            'status': 'executed',
            'reason': run_state_reason,
            'dependency_target': dependency_target_key,
            'dependency_path': dependency_loss_path,
            'dependency_sha1': dependency_sha1,
            'timestamp': timestamp,
        }

        _update_dependency_state(omni, scenario_name, dependency_entry, run_state_entry)

        elapsed = time.time() - start_ts
        status = True
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} COMPLETED {func_name}({runid}) -> ({status}, {elapsed:.3f})',
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED')
        return status, elapsed

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def run_omni_scenarios_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        omni = Omni.getInstance(wd)

        if not omni.use_rq_job_pool_concurrency:
            omni.run_omni_scenarios()

            try:
                prep = RedisPrep.getInstance(wd)
                prep.timestamp(TaskEnum.run_omni)
            except FileNotFoundError:
                pass

            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END BROADCAST')
            return None

        if not omni.scenarios:
            omni.logger.info('  run_omni_scenarios: No scenarios to run')
            raise Exception('No scenarios to run')

        dependency_tree = dict(omni.scenario_dependency_tree)
        run_states: List[Dict[str, Any]] = []
        omni.scenario_run_state = run_states

        active_scenarios: set[str] = set()
        processed_scenarios: set[str] = set()

        stage1_tasks: List[Dict[str, Any]] = []
        stage2_tasks: List[Dict[str, Any]] = []

        def dependency_info(scenario_enum: OmniScenario, scenario_def: Dict[str, Any]):
            scenario_name = _scenario_name_from_scenario_definition(scenario_def)
            active_scenarios.add(scenario_name)
            dependency_target = omni._scenario_dependency_target(scenario_enum, scenario_def)
            dependency_path = omni._loss_pw0_path_for_scenario(dependency_target)
            dependency_hash = _hash_file_sha1(dependency_path)
            signature_value = omni._scenario_signature(scenario_def)
            previous = dependency_tree.get(scenario_name)
            up_to_date = (
                previous is not None
                and previous.get('dependency_sha1') == dependency_hash
                and previous.get('signature') == signature_value
            )
            target_key = omni._normalize_scenario_key(dependency_target)
            return scenario_name, target_key, dependency_path, dependency_hash, signature_value, up_to_date

        # pass 1 scenarios: dependent on base scenario
        for scenario_def in omni.scenarios:
            scenario_payload = _scenario_payload_for_job(scenario_def)
            scenario_enum = scenario_payload['type']
            if scenario_enum == OmniScenario.Mulch:
                continue

            if (
                omni.base_scenario != OmniScenario.Undisturbed
                and scenario_enum in (OmniScenario.Thinning, OmniScenario.PrescribedFire)
            ):
                continue

            (
                scenario_name,
                target_key,
                dependency_path,
                dependency_hash,
                signature_value,
                up_to_date,
            ) = dependency_info(scenario_enum, scenario_payload)
            processed_scenarios.add(scenario_name)

            if up_to_date:
                omni.logger.info(f'  run_omni_scenarios: {scenario_name} dependency unchanged, skipping')
                ts = time.time()
                dependency_tree[scenario_name] = {
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'signature': signature_value,
                    'timestamp': ts,
                }
                omni.scenario_dependency_tree = dependency_tree
                run_states.append({
                    'scenario': scenario_name,
                    'status': 'skipped',
                    'reason': 'dependency_unchanged',
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'timestamp': ts,
                })
                omni.scenario_run_state = run_states
                continue

            omni.logger.info(f'  run_omni_scenarios: queue {scenario_name}')
            stage1_tasks.append(
                {
                    'scenario_def': scenario_payload,
                    'scenario_name': scenario_name,
                    'target_key': target_key,
                    'dependency_path': dependency_path,
                    'signature': signature_value,
                }
            )

        # pass 2 scenarios: dependent on pass 1 results
        for scenario_def in omni.scenarios:
            scenario_payload = _scenario_payload_for_job(scenario_def)
            scenario_enum = scenario_payload['type']
            scenario_name = _scenario_name_from_scenario_definition(scenario_payload)
            if scenario_name in processed_scenarios:
                continue

            (
                scenario_name,
                target_key,
                dependency_path,
                dependency_hash,
                signature_value,
                up_to_date,
            ) = dependency_info(scenario_enum, scenario_payload)
            processed_scenarios.add(scenario_name)

            if up_to_date:
                omni.logger.info(f'  run_omni_scenarios: {scenario_name} dependency unchanged, skipping')
                ts = time.time()
                dependency_tree[scenario_name] = {
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'signature': signature_value,
                    'timestamp': ts,
                }
                omni.scenario_dependency_tree = dependency_tree
                run_states.append({
                    'scenario': scenario_name,
                    'status': 'skipped',
                    'reason': 'dependency_unchanged',
                    'dependency_target': target_key,
                    'dependency_path': dependency_path,
                    'dependency_sha1': dependency_hash,
                    'timestamp': ts,
                })
                omni.scenario_run_state = run_states
                continue

            omni.logger.info(f'  run_omni_scenarios: queue {scenario_name}')
            stage2_tasks.append(
                {
                    'scenario_def': scenario_payload,
                    'scenario_name': scenario_name,
                    'target_key': target_key,
                    'dependency_path': dependency_path,
                    'signature': signature_value,
                }
            )

        stale = set(dependency_tree.keys()) - active_scenarios
        for scenario_name in stale:
            dependency_tree.pop(scenario_name, None)
        omni.scenario_dependency_tree = dependency_tree

        stage1_jobs = []
        stage2_jobs = []

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)

            for task in stage1_tasks:
                child_job = q.enqueue_call(
                    func=run_omni_scenario_rq,
                    args=[runid, task['scenario_def']],
                    kwargs={
                        'dependency_target': task['target_key'],
                        'dependency_path': task['dependency_path'],
                        'signature': task['signature'],
                    },
                    timeout=TIMEOUT,
                )
                job.meta[f"jobs:0,scenario:{task['scenario_name']}"] = child_job.id
                stage1_jobs.append(child_job)
                job.save()

            depends_on_stage2 = stage1_jobs if stage1_jobs else None
            for task in stage2_tasks:
                child_job = q.enqueue_call(
                    func=run_omni_scenario_rq,
                    args=[runid, task['scenario_def']],
                    kwargs={
                        'dependency_target': task['target_key'],
                        'dependency_path': task['dependency_path'],
                        'signature': task['signature'],
                    },
                    timeout=TIMEOUT,
                    depends_on=depends_on_stage2,
                )
                job.meta[f"jobs:1,scenario:{task['scenario_name']}"] = child_job.id
                stage2_jobs.append(child_job)
                job.save()

            compile_depends = stage2_jobs or stage1_jobs
            compile_job = q.enqueue_call(
                func=_compile_hillslope_summaries_rq,
                args=[runid],
                timeout=TIMEOUT,
                depends_on=compile_depends if compile_depends else None,
            )
            job.meta['jobs:2,func:_compile_hillslope_summaries_rq'] = compile_job.id
            job.save()

            final_depends: List[Any] = [compile_job]
            final_job = q.enqueue_call(
                func=_finalize_omni_scenarios_rq,
                args=[runid],
                timeout=TIMEOUT,
                depends_on=final_depends,
            )
            job.meta['jobs:3,func:_finalize_omni_scenarios_rq'] = final_job.id
            job.save()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        return final_job

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _compile_hillslope_summaries_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        omni = Omni.getInstance(wd)
        omni.compile_hillslope_summaries()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _finalize_omni_scenarios_rq(runid: str):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_omni)
        except FileNotFoundError:
            pass

        if send_discord_message is not None:
            try:
                send_discord_message(
                    f':crystal_ball: Omni scenarios completed for {runid} on {_hostname}'
                )
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END BROADCAST')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
