#!/usr/bin/env python3
"""Live batch-queue acceptance after the successful direct-native Omni run.

Explicit developer acceptance admission on the exact owned disposable run; not
an HTTP batch enqueue claim. No queue submission occurs until main() runs with
a passed direct manifest. No production monkeypatches or fabricated task results.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time
import traceback

from runtime_project_copy import copy_one, digest_file, inventory, verify_source, version, write_json
from runtime_omni_sbs_acceptance import code_hashes, numerical_identity, snapshot_child, validate_generation


def normalized_status(value):
    return str(getattr(value, 'value', value)).lower()


def verify_reviewed_source(manifest, *, hash_bytes, accept_operational_metadata):
    """Explicit harness-only exception; the original source baseline is immutable."""
    if not accept_operational_metadata:
        return verify_source(manifest, hash_bytes=hash_bytes)
    allowed = {'TTL', 'disturbed.log', 'ron.log', 'watershed.log'}
    source = Path(manifest['source'])
    _, files = inventory(source)  # Reject links/special files; require exact membership.
    observed = {str(path): version(info) for path, info in files}
    if set(observed) != set(manifest['source_files']):
        raise RuntimeError('Named source membership changed')
    changes, hashed_bytes = [], 0
    for relative, info in files:
        name = str(relative)
        expected = manifest['source_files'][name]
        changed = version(info) != expected['version']
        if changed and name not in allowed:
            raise RuntimeError(f'Named scientific/other source version changed: {name}')
        if name in allowed and stat.S_IMODE(info.st_mode) != expected['mode']:
            raise RuntimeError(f'Named operational source mode changed: {name}')
        if hash_bytes or changed:
            actual = digest_file(source / relative)
            if (actual['version'] != version(info) or actual['sha256'] != expected['sha256']
                    or actual['bytes'] != expected['bytes']):
                raise RuntimeError(f'Named source bytes/read generation changed: {name}')
            if name in allowed and actual['mode'] != expected['mode']:
                raise RuntimeError(f'Named operational source mode changed during read: {name}')
            hashed_bytes += info.st_size
            if changed:
                changes.append({'path': name, 'original_version': expected['version'],
                                'observed_version': actual['version'],
                                'original_and_current_sha256': actual['sha256'],
                                'mode': expected['mode']})
    _, after_files = inventory(source)
    if {str(path): version(info) for path, info in after_files} != observed:
        raise RuntimeError('Named source changed during complete verification interval')
    if any(str(path) in allowed and stat.S_IMODE(info.st_mode) != manifest['source_files'][str(path)]['mode']
           for path, info in after_files):
        raise RuntimeError('Named operational source mode changed during complete verification interval')
    return {'files': len(files), 'hashed_bytes': hashed_bytes,
            'all_original_bytes_verified': hash_bytes,
            'strict_original_versions_except_recorded_operational_paths': True,
            'operational_metadata_changes': changes,
            'whole_tree_physical_identity_unchanged': not changes,
            'review': 'runtime_omni_ttl_attribution.md and independent security disposition'}


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    from rq.job import Job
    if isinstance(value, Job):
        return {'returned_job_id': value.id}
    raise TypeError(f'Unexpected job evidence type: {type(value).__name__}')


def read_tree(root_job_id, connection, runid):
    from rq.job import Job

    records, pending = {}, [root_job_id]
    while pending:
        job_id = pending.pop()
        if job_id in records:
            raise AssertionError('Registered Omni job tree contains repeated/cyclic IDs')
        job = Job.fetch(job_id, connection=connection)
        if not job.args or job.args[0] != runid or job.origin != 'batch':
            raise AssertionError(f'Job {job_id} is not bound to the exact owned batch run')
        children = {key: str(value) for key, value in job.meta.items() if key.startswith('jobs:')}
        records[job_id] = {'function': job.func_name, 'status': normalized_status(job.get_status()),
                           'origin': job.origin, 'runid': job.args[0],
                           'worker_name': getattr(job, 'worker_name', None),
                           'started_at': str(job.started_at) if job.started_at else None,
                           'ended_at': str(job.ended_at) if job.ended_at else None,
                           'registered_children': children,
                           'declared_dependency_ids': list(job._dependency_ids or []),
                           'dependency_keys': [value.decode() if isinstance(value, bytes) else str(value)
                                               for value in job.dependency_ids],
                           'result': json_safe(job.result),
                           'signature': (job.kwargs or {}).get('signature'),
                           'exception': job.exc_info}
        pending.extend(children.values())
    return records


def await_tree(job_id, connection, runid, root, phase, deadline_seconds):
    from wepppy.rq.job_info import get_wepppy_rq_job_info, get_wepppy_rq_job_status

    deadline = time.monotonic() + deadline_seconds
    last = None
    while True:
        observed = get_wepppy_rq_job_status(job_id)
        status = normalized_status(observed['status'])
        with (root / f'{phase}-poll.jsonl').open('a') as stream:
            stream.write(json.dumps({'observed_unix': time.time(), **json_safe(observed)}) + '\n')
        key = (status, json.dumps(observed.get('progress', {}), sort_keys=True))
        if key != last:
            print(json.dumps({'phase': phase, 'root_job_id': job_id, 'status': status,
                              'progress': observed.get('progress')}), flush=True)
            last = key
        # Dispatcher registers IDs before enqueue. Missing newly registered
        # children are not success; next normal poll observes publication.
        if status in ('finished', 'failed', 'stopped', 'canceled', 'not_found'):
            write_json(root / f'{phase}-jobinfo.json', json_safe(get_wepppy_rq_job_info(job_id)))
            if status != 'finished':
                raise RuntimeError(f'Live Omni tree {job_id} ended as {status}')
            records = read_tree(job_id, connection, runid)
            write_json(root / f'{phase}-tree.json', records)
            if any(item['status'] != 'finished' or not item['started_at'] or not item['ended_at']
                   for item in records.values()):
                raise AssertionError('Aggregate success lacks all actually executed terminal tree members')
            return records
        if time.monotonic() >= deadline:
            write_json(root / f'{phase}-jobinfo.json', json_safe(get_wepppy_rq_job_info(job_id)))
            raise TimeoutError(f'Polling deadline elapsed for {job_id}; jobs were not canceled or retried')
        time.sleep(5)


def submit(prep, queue, runid, phase, manifest, manifest_path):
    from wepppy.rq.omni_rq import (run_omni_scenarios_rq, run_omni_scenario_rq,
                                   _compile_hillslope_summaries_rq, _finalize_omni_scenarios_rq)
    from wepppy.rq.submission_recovery import enqueue_tracked_rq_job
    from wepppy.nodb.redis_prep import TaskEnum

    prep.remove_timestamp(TaskEnum.run_omni_scenarios)
    phase_record = {'phase': phase, 'status': 'admitting', 'runid': runid}
    manifest['phases'].append(phase_record)
    write_json(manifest_path, manifest)

    def record_job_id(job_id):
        phase_record['job_id'] = job_id
        phase_record['status_url'] = '/rq-engine/api/jobstatus/' + job_id
        phase_record['jobinfo_url'] = '/rq-engine/api/jobinfo/' + job_id
        write_json(manifest_path, manifest)

    # Exact existing route admission helper/arguments, applied by the explicitly
    # authorized developer acceptance harness to its owned disposable batch run.
    job = enqueue_tracked_rq_job(
        queue, run_omni_scenarios_rq, prep=prep, job_key='run_omni_rq', runid=runid,
        args=(runid,), timeout=int(os.getenv('RQ_ENGINE_RQ_TIMEOUT', '216000')),
        on_job_id=record_job_id, allowed_origins=('batch',),
        allowed_workflow_funcs=(run_omni_scenario_rq, _compile_hillslope_summaries_rq,
                                _finalize_omni_scenarios_rq))
    if prep.get_rq_job_id('run_omni_rq') != job.id:
        raise AssertionError('Tracked admission receipt does not match actual queued root')
    phase_record.update(status='queued', job_id=job.id)
    write_json(manifest_path, manifest)
    return job.id, phase_record


def assert_tree_shape(records, root_job_id, *, scenario_expected, expected_sha):
    from wepppy.nodb.mods.omni.omni_sbs_freshness import receipt_from_signature

    prefix = 'wepppy.rq.omni_rq.'
    expected = {prefix + 'run_omni_scenarios_rq': 1,
                prefix + '_compile_hillslope_summaries_rq': 1,
                prefix + '_finalize_omni_scenarios_rq': 1,
                prefix + 'run_omni_scenario_rq': int(scenario_expected)}
    actual = {name: sum(item['function'] == name for item in records.values()) for name in expected}
    if actual != expected or len(records) != sum(expected.values()):
        raise AssertionError(f'Unexpected actual Omni tree functions: {actual}')
    children = records[root_job_id]['registered_children']
    if len(children) != 2 + int(scenario_expected):
        raise AssertionError('Dispatcher did not register the expected complete tree')
    for item in records.values():
        if item['function'] == prefix + 'run_omni_scenario_rq':
            receipt = receipt_from_signature(item['signature'])
            if receipt['sha256'] != expected_sha or item['result'][0] is not True:
                raise AssertionError('Actual worker did not consume the queued receipt successfully')


def compare_direct_outputs(direct_generation, child):
    import pandas as pd

    result = {}
    filenames = ('loss_pw0.out.parquet', 'loss_pw0.hill.parquet', 'loss_pw0.chn.parquet',
                 'loss_pw0.all_years.class_data.parquet', 'loss_pw0.all_years.hill.parquet')
    for filename in filenames:
        relative = Path('wepp/output/interchange') / filename
        before = pd.read_parquet(direct_generation / relative)
        after = pd.read_parquet(child / relative)
        keys = [name for name in ('year', 'wepp_id', 'topaz_id', 'chn_id', 'key') if name in before.columns]
        if keys:
            before = before.sort_values(keys).reset_index(drop=True)
            after = after.sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(before, after, check_exact=True, check_like=True)
        result[filename] = {'rows': len(after), 'columns': list(after.columns), 'exact_values_and_dtypes': True}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-manifest', required=True, help='Successful direct-native manifest on the same exclusively owned copy')
    parser.add_argument('--deadline-seconds', type=int, default=7200)
    parser.add_argument('--attempt-name', default='rq-acceptance')
    parser.add_argument('--accept-reviewed-operational-metadata', action='store_true',
                        help='Record only the four reviewed same-byte/mode source metadata exceptions')
    args = parser.parse_args()
    if args.deadline_seconds < 60:
        parser.error('--deadline-seconds must be at least60')
    repository = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repository))
    direct_path = Path(args.native_manifest).absolute()
    direct = json.loads(direct_path.read_text())
    root, project = Path(direct['root']), Path(direct['project'])
    if (direct['status'] != 'passed' or len(direct['stages']) != 2
            or root.parent != Path('/wc1/batch') or not root.name.startswith('qa-')
            or project != root / 'runs' / (root.name + '-grizzly')
            or not direct.get('canonical_fork_job_markers_reset')
            or (project / '.redisprep-run-id').exists() or (project / '.redisprep-run-id').is_symlink()):
        raise ValueError('Requires the successful uniquely namespaced direct acceptance copy with canonical fork reset')
    if not all(stage['status'] == 'passed' for stage in direct['stages']):
        raise ValueError('Both direct native generations must have passed')
    copy_manifest = json.loads(Path(direct['copy_manifest']).read_text())
    runid = copy_manifest['runid']
    if (Path(args.attempt_name).name != args.attempt_name
            or not args.attempt_name.startswith('rq-acceptance')):
        raise ValueError('Attempt name must be a single rq-acceptance-prefixed directory name')
    output = root / args.attempt_name
    if output.exists():
        raise FileExistsError('Retain prior queued attempt; do not automatically resubmit it')
    output.mkdir(mode=0o750)
    manifest_path = output / 'manifest.json'
    manifest = {'status': 'preparing', 'direct_manifest': str(direct_path), 'runid': runid,
                'project': str(project), 'phases': [], 'started_unix': time.time(),
                'module_hashes': code_hashes(repository),
                'rq_module_sha256': digest_file(repository / 'wepppy/rq/omni_rq.py')['sha256'],
                'accept_reviewed_operational_metadata': args.accept_reviewed_operational_metadata,
                'scope': 'Actual tracked developer admission plus live existing batch dispatcher/worker tree; not HTTP enqueue'}
    write_json(manifest_path, manifest)
    try:
        import redis
        from rq import Queue
        from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
        from wepppy.nodb.mods.omni.omni import Omni, _scenario_name_from_scenario_definition
        from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
        from wepppy.weppcloud.utils.helpers import get_wd

        if Path(get_wd(runid)).resolve() != project.resolve():
            raise AssertionError('Canonical live worker resolver selects a different project')
        manifest['source_preflight'] = verify_reviewed_source(
            copy_manifest, hash_bytes=False,
            accept_operational_metadata=args.accept_reviewed_operational_metadata)
        if shutil.disk_usage(root).free < 10 * 1024**3:
            raise RuntimeError('Need10GiB free for the live native generation and retained evidence')
        omni = Omni.getInstance(str(project))
        if omni.runid != runid or not omni.use_rq_job_pool_concurrency or len(omni.scenarios) != 1:
            raise AssertionError('Expected the unchanged one-scenario owner with canonical RQ concurrency enabled')
        definition = dict(omni.scenarios[0])
        upload = Path(definition['sbs_file_path'])
        if not upload.is_relative_to(project) or root.name not in upload.name or upload.exists():
            raise AssertionError('Expected the same unique, consumed, project-local SBS upload')
        scenario_name = _scenario_name_from_scenario_definition(definition)
        current_child = project / '_pups/omni/scenarios' / scenario_name
        before = numerical_identity(current_child)
        supplied = root / 'input-generation-1.tif'
        wanted_sha = digest_file(supplied)['sha256']
        if wanted_sha == direct['stages'][1]['actual']['receipt']['sha256']:
            raise AssertionError('Queued acceptance must supply a changed same-name generation')
        copy_one(supplied, upload, supplied.stat())
        old_mtime = direct['stages'][0]['input']['identity']['version'][3]
        os.utime(upload, ns=(old_mtime, old_mtime))
        manifest['upload'] = {'path': str(upload), 'sha256': wanted_sha, 'severity': 1,
                              'restored_mtime_ns': old_mtime, 'prior_severity': 3}
        prep = RedisPrep.getInstance(str(project))
        if prep.run_id != project.name:
            raise AssertionError('RedisPrep does not use the isolated expected leaf namespace')
        expected_stems = {path.stem for path in (project / 'wepp/runs').glob('p*.man')}
        expected_years = set(direct['baseline']['years'])
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
            queue = Queue('batch', connection=connection)
            job_id, phase = submit(prep, queue, runid, 'changed-upload', manifest, manifest_path)
            records = await_tree(job_id, connection, runid, output, 'changed-upload', args.deadline_seconds)
            assert_tree_shape(records, job_id, scenario_expected=True, expected_sha=wanted_sha)
            omni = Omni.getInstance(str(project))
            current_child, phase['actual'] = validate_generation(
                omni, definition, wanted_sha, 1, expected_stems, expected_years)
            after = numerical_identity(current_child)
            phase['changed_generated'] = {extension: [name for name, value in after.items()
                                                      if name.endswith('.' + extension) and name in before
                                                      and value['sha256'] != before[name]['sha256']]
                                           for extension in ('man', 'sol')}
            if not all(phase['changed_generated'].values()):
                raise AssertionError('Queued changed bytes did not propagate to management and soil outputs')
            phase['direct_same_input_parity'] = compare_direct_outputs(
                Path(direct['stages'][0]['retained_artifacts']), current_child)
            if prep[str(TaskEnum.run_omni_scenarios)] is None:
                raise AssertionError('Actual finalizer did not stamp Omni completion')
            phase.update(status='passed', tree_jobs=len(records))
            write_json(manifest_path, manifest)
            job_id, phase = submit(prep, queue, runid, 'consumed-skip', manifest, manifest_path)
            records = await_tree(job_id, connection, runid, output, 'consumed-skip', args.deadline_seconds)
            assert_tree_shape(records, job_id, scenario_expected=False, expected_sha=wanted_sha)
            omni = Omni.getInstance(str(project))
            states = [item for item in omni.scenario_run_state if item['scenario'] == scenario_name]
            if len(states) != 1 or states[0]['status'] != 'skipped' or upload.exists():
                raise AssertionError('Live consumed-source dispatcher did not skip')
            if numerical_identity(current_child) != after:
                raise AssertionError('Live skipped tree rewrote numerical artifacts')
            phase.update(status='passed', tree_jobs=len(records), state=states[0])
            write_json(manifest_path, manifest)
        snapshot = snapshot_child(current_child, output / 'generation', project)
        manifest['retained_regular_files'] = len(snapshot['files'])
        shutil.copy2(project / 'omni.nodb', output / 'parent-omni.nodb')
        manifest['source_after'] = verify_reviewed_source(
            copy_manifest, hash_bytes=True,
            accept_operational_metadata=args.accept_reviewed_operational_metadata)
        manifest['module_hashes_after'] = code_hashes(repository)
        if (manifest['module_hashes_after'] != manifest['module_hashes']
                or digest_file(repository / 'wepppy/rq/omni_rq.py')['sha256'] != manifest['rq_module_sha256']):
            raise AssertionError('Production modules changed during live RQ acceptance')
        manifest.update(status='passed', finished_unix=time.time())
        write_json(manifest_path, manifest)
        print(json.dumps({'status': 'passed', 'manifest': str(manifest_path)}), flush=True)
    except BaseException as exc:  # Acceptance boundary: retain jobs/artifacts; never retry, cancel or clear queues.
        manifest.update(status='failed', error_type=type(exc).__name__, error=str(exc),
                        traceback=traceback.format_exc(), finished_unix=time.time())
        write_json(manifest_path, manifest)
        raise


if __name__ == '__main__':
    main()
