from __future__ import annotations

"""RQ orchestration for Omni scenario execution and dependent post-processing."""

import inspect
import json
import os
import socket
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

import redis
from rq import Queue, get_current_job
from rq.job import Job

from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.rq.exception_logging import with_exception_logging

from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.mods.omni.omni import (
    _hash_file_sha1,
    _scenario_name_from_scenario_definition,
)
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.wepp_rq_stage_helpers import (
    NODIR_RECOVERY_ROOTS as _NODIR_RECOVERY_ROOTS,
    recover_mixed_nodir_roots as _recover_mixed_nodir_roots_impl,
)

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except ImportError:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST: str = redis_host()
RQ_DB: int = int(RedisDB.RQ)

TIMEOUT: int = 43_200


def _recover_mixed_nodir_roots(
    wd: str,
    *,
    roots: tuple[str, ...] = _NODIR_RECOVERY_ROOTS,
) -> tuple[str, ...]:
    return _recover_mixed_nodir_roots_impl(wd, roots=roots)


def _scenario_payload_for_job(scenario_def: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deepcopy with the ``type`` coerced to ``OmniScenario`` for workers."""
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
    """Raised when Omni lock acquisition exceeds retry attempts."""


def _update_dependency_state(
    omni: Omni,
    scenario_name: str,
    dependency_entry: Dict[str, Any],
    run_state_entry: Dict[str, Any],
) -> None:
    """Persist dependency and run state metadata with retry semantics."""

    from wepppy.nodb.base import NoDbAlreadyLockedError
    
    max_tries = 5
    for attempt in range(max_tries):
        try:
            omni = Omni.getInstance(omni.wd)
            with omni.locked():
                omni.scenario_dependency_tree[scenario_name] = dependency_entry
                omni.scenario_run_state.append(run_state_entry)

        except NoDbAlreadyLockedError:
            if attempt + 1 == max_tries:
                raise OmniLockTimeout('max retries exceeded')
            time.sleep(1.0)
        else:
            break


def _update_contrast_dependency_state(
    omni: Omni,
    contrast_name: str,
    dependency_entry: Dict[str, Any],
) -> None:
    """Persist contrast dependency metadata with retry semantics."""

    from wepppy.nodb.base import NoDbAlreadyLockedError

    max_tries = 5
    for attempt in range(max_tries):
        try:
            omni = Omni.getInstance(omni.wd)
            with omni.locked():
                omni.contrast_dependency_tree[contrast_name] = dependency_entry

        except NoDbAlreadyLockedError:
            if attempt + 1 == max_tries:
                raise OmniLockTimeout('max retries exceeded')
            time.sleep(1.0)
        else:
            break


@with_exception_logging
def run_omni_scenario_rq(
    runid: str,
    scenario: Dict[str, Any],
    *,
    dependency_target: Optional[str] = None,
    dependency_path: Optional[str] = None,
    signature: Optional[str] = None,
    run_state_reason: str = 'dependency_changed',
) -> Tuple[bool, float]:
    """Run a single Omni scenario, updating dependency metadata upon completion."""
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
        return status, elapsed

    except Exception as exc:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:190", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        try:
            payload = {
                "type": type(exc).__name__,
                "message": str(exc),
                "scenario": locals().get("scenario_name"),
                "scenario_type": str(locals().get("scenario_enum")) if locals().get("scenario_enum") is not None else None,
                "dependency_target": locals().get("dependency_target_key"),
                "dependency_path": locals().get("dependency_loss_path"),
            }
            StatusMessenger.publish(
                status_channel,
                f'rq:{job.id} EXCEPTION_JSON {json.dumps(payload)}',
            )
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:205", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            pass
        raise


@with_exception_logging
def run_omni_contrast_rq(
    runid: str,
    contrast_id: int,
) -> Tuple[bool, float]:
    """Run a single Omni contrast, emitting completion triggers for reporting."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni_contrasts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        start_ts = time.time()

        omni = Omni.getInstance(wd)
        contrast_names = omni.contrast_names or []
        if contrast_id < 1 or contrast_id > len(contrast_names):
            raise ValueError(f'Contrast id {contrast_id} is out of range')
        contrast_name = contrast_names[contrast_id - 1]
        if not contrast_name:
            raise ValueError(f'Contrast id {contrast_id} is skipped')

        omni.run_omni_contrast(contrast_id, rq_job_id=job.id)

        elapsed = time.time() - start_ts
        status = True
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} COMPLETED {func_name}({runid}) -> ({status}, {elapsed:.3f})',
        )
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} TRIGGER omni_contrasts OMNI_CONTRAST_RUN_TASK_COMPLETED',
        )
        return status, elapsed

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:246", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def run_omni_scenarios_rq(runid: str) -> Optional[Job]:
    """Coordinate Omni scenario execution, optionally leveraging worker concurrency."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        recovered_roots = _recover_mixed_nodir_roots(wd)
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            StatusMessenger.publish(
                status_channel,
                f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}",
            )

        for root in ('climate', 'watershed', 'landuse', 'soils'):
            nodir_resolve(wd, root, view='effective')

        omni = Omni.getInstance(wd)

        if not omni.use_rq_job_pool_concurrency:
            omni.run_omni_scenarios()

            try:
                prep = RedisPrep.getInstance(wd)
                prep.timestamp(TaskEnum.run_omni_scenarios)
            except FileNotFoundError:
                pass

            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END_BROADCAST')
            return None

        if not omni.scenarios:
            omni.logger.info('  run_omni_scenarios: No scenarios to run')
            raise Exception('No scenarios to run')

        dependency_tree = dict(omni.scenario_dependency_tree)
        run_states: List[Dict[str, Any]] = []
        omni.scenario_run_state = run_states

        active_scenarios: Set[str] = set()
        processed_scenarios: Set[str] = set()

        stage1_tasks: List[Dict[str, Any]] = []
        stage2_tasks: List[Dict[str, Any]] = []
        scenarios_ran_count = 0

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

        # stage 1 scenarios: dependent on base scenario
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
            scenarios_ran_count += 1

        # stage 2 scenarios: dependent on stage 1 results
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
            scenarios_ran_count += 1

        if scenarios_ran_count == 0:
            omni.logger.info('  run_omni_scenarios: All scenarios up to date, nothing to run')

        stale = set(dependency_tree.keys()) - active_scenarios
        for scenario_name in stale:
            dependency_tree.pop(scenario_name, None)
        omni.scenario_dependency_tree = dependency_tree

        stage1_jobs: List[Job] = []
        stage2_jobs: List[Job] = []

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)

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

            compile_depends: List[Job] = stage2_jobs or stage1_jobs
            compile_job = q.enqueue_call(
                func=_compile_hillslope_summaries_rq,
                args=[runid],
                timeout=TIMEOUT,
                depends_on=compile_depends if compile_depends else None,
            )
            job.meta['jobs:2,func:_compile_hillslope_summaries_rq'] = compile_job.id
            job.save()

            final_depends: List[Job] = [compile_job]
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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:492", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def run_omni_contrasts_rq(runid: str) -> Optional[Job]:
    """Run Omni contrasts and emit completion triggers for the contrast UI."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni_contrasts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        recovered_roots = _recover_mixed_nodir_roots(wd)
        if recovered_roots:
            recovered_txt = ", ".join(recovered_roots)
            StatusMessenger.publish(
                status_channel,
                f"Recovered mixed NoDir roots before {func_name}({runid}): {recovered_txt}",
            )

        omni = Omni.getInstance(wd)
        contrast_names = omni.contrast_names or []
        if not contrast_names:
            omni.logger.info('  run_omni_contrasts: No contrasts to run')
            if omni.contrast_dependency_tree:
                omni.contrast_dependency_tree = {}
            omni._clean_stale_contrast_runs([])
            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni_contrasts END_BROADCAST')
            return None

        active_ids: List[int] = []
        active_contrasts: Set[str] = set()
        run_ids: List[int] = []
        landuse_cache: Dict[str, Optional[Dict[int, Optional[str]]]] = {}
        skipped_landuse: Set[str] = set()
        for contrast_id, contrast_name in enumerate(contrast_names, start=1):
            if not contrast_name:
                continue
            active_ids.append(contrast_id)
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
                skipped_landuse.add(contrast_name)
                continue
            sidecar_path = omni._contrast_sidecar_path(contrast_id)
            if not os.path.isfile(sidecar_path):
                omni.logger.info(
                    "  run_omni_contrasts: Missing sidecar for contrast_id=%s, skipping.",
                    contrast_id,
                )
                continue
            run_status = omni._contrast_run_status(contrast_id, contrast_name)
            if run_status == 'up_to_date':
                omni.logger.info(
                    '  run_omni_contrasts: %s up-to-date, skipping',
                    contrast_name,
                )
                continue
            if run_status == "in_progress":
                omni.logger.info(
                    "  run_omni_contrasts: %s already running, skipping",
                    contrast_name,
                )
                continue
            run_ids.append(contrast_id)

        if not active_ids:
            omni.logger.info('  run_omni_contrasts: No contrasts to run')
            if omni.contrast_dependency_tree:
                omni.contrast_dependency_tree = {}
            omni._clean_stale_contrast_runs(active_ids)
            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni_contrasts END_BROADCAST')
            return None

        dependency_tree = dict(omni.contrast_dependency_tree)
        for contrast_name in skipped_landuse:
            dependency_tree.pop(contrast_name, None)
        stale = set(dependency_tree.keys()) - active_contrasts
        for contrast_name in stale:
            dependency_tree.pop(contrast_name, None)
        omni.contrast_dependency_tree = dependency_tree
        omni._clean_stale_contrast_runs(active_ids)

        if not run_ids:
            omni.logger.info('  run_omni_contrasts: All contrasts up to date, nothing to run')
            StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
            StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni_contrasts END_BROADCAST')
            return None

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue("batch", connection=redis_conn)
            contrast_jobs: List[Job] = []
            batch_depends: Optional[List[Job]] = None
            batch_size = omni.contrast_batch_size
            if batch_size < 1:
                batch_size = 1
            for start in range(0, len(run_ids), batch_size):
                batch_jobs: List[Job] = []
                for contrast_id in run_ids[start:start + batch_size]:
                    child_job = q.enqueue_call(
                        func=run_omni_contrast_rq,
                        args=[runid, contrast_id],
                        timeout=TIMEOUT,
                        depends_on=batch_depends,
                    )
                    job.meta[f'jobs:contrast:{contrast_id}'] = child_job.id
                    batch_jobs.append(child_job)
                    contrast_jobs.append(child_job)
                    job.save()
                batch_depends = batch_jobs

            final_job = q.enqueue_call(
                func=_finalize_omni_contrasts_rq,
                args=[runid],
                timeout=TIMEOUT,
                depends_on=batch_depends,
            )
            job.meta['jobs:finalize:_finalize_omni_contrasts_rq'] = final_job.id
            job.save()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        return final_job

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:623", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _finalize_omni_contrasts_rq(runid: str) -> None:
    """Finalize Omni contrasts, stamping Redis prep state and notifying subscribers."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni_contrasts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_omni_contrasts)
        except FileNotFoundError:
            pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni_contrasts END_BROADCAST')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:647", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def delete_omni_contrasts_rq(runid: str) -> None:
    """Delete Omni contrasts and clear prep state."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni_contrasts'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        omni = Omni.getInstance(wd)
        omni.clear_contrasts()

        try:
            prep = RedisPrep.getInstance(wd)
            prep.remove_timestamp(TaskEnum.run_omni_contrasts)
        except FileNotFoundError:
            pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni_contrasts END_BROADCAST')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:673", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _compile_hillslope_summaries_rq(runid: str) -> None:
    """Compile Omni hillslope summaries after scenario execution."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        omni = Omni.getInstance(wd)
        omni.compile_hillslope_summaries()
        omni.compile_channel_summaries()
        omni.scenarios_report()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:694", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


@with_exception_logging
def _finalize_omni_scenarios_rq(runid: str) -> None:
    """Finalize Omni processing, stamping Redis prep state and notifying subscribers."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:omni'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_omni_scenarios)
        except FileNotFoundError:
            pass

        if send_discord_message is not None:
            try:
                send_discord_message(
                    f':crystal_ball: Omni scenarios completed for {runid} on {_hostname}'
                )
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:720", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni OMNI_SCENARIO_RUN_TASK_COMPLETED')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END_BROADCAST')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/omni_rq.py:727", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
