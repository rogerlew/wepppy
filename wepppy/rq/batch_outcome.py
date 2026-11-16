"""Attempt-bound batch result publication; see batch-outcome-contract.md."""
from __future__ import annotations

from contextlib import contextmanager
import io
import hashlib
import json
import math
import logging
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote
import zipfile

import redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.rq.submission_recovery import RqSubmissionConflict, rq_submission_lock

logger = logging.getLogger(__name__)

ROOTS = {
    'wepppy.rq.batch_rq.run_batch_rq': 'batch',
    'wepppy.rq.culvert_rq.run_culvert_batch_rq': 'culvert',
    'wepppy.rq.culvert_rq.run_culvert_batch_finalize_rq': 'culvert',
}
TERMINAL = {'finished', 'failed', 'stopped', 'canceled'}
PUBLIC = ('schema_version', 'attempt_id', 'state', 'outcome', 'total', 'succeeded',
          'failed', 'skipped', 'results_available', 'download_url', 'reason')


class BatchReconciliationUnavailable(RuntimeError):
    """A verified attempt could not be reconciled under its resource lease."""


def component(value: str) -> str:
    if (not isinstance(value, str) or not value or value in {'.', '..'}
            or '/' in value or '\\' in value or any(ord(char) < 32 for char in value)):
        raise ValueError('Invalid batch result identity')
    return value


def identity(job):
    workflow = ROOTS.get(job.func_name)
    if workflow is None or len(job.args) != 1:
        raise ValueError('Invalid batch root')
    resource = component(job.args[0])
    component(job.id)
    if workflow == 'culvert':
        from wepppy.rq.culvert_rq_helpers import _resolve_batch_root
        root = _resolve_batch_root(resource)
    else:
        from wepppy.weppcloud.utils.helpers import get_batch_root_dir
        root = Path(get_batch_root_dir()) / resource
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Invalid batch project root')
    return workflow, resource, root.resolve()


def inside(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root) or any(
        parent.is_symlink() for parent in [path, *path.parents] if parent != root and parent.is_relative_to(root)
    ):
        raise ValueError('Invalid batch artifact path')
    return path


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.working-', dir=path.parent)
    # Keep interrupted working files visible as publication diagnostics.
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_json(path):
    return json.loads(path.read_text())


@contextmanager
def lease_for(job, *, polling=False):
    workflow, resource, root = identity(job)
    try:
        with rq_submission_lock(job.connection, f'{workflow}:{resource}',
                                lifecycle_key=resource, lifecycle_type=workflow,
                                blocking_timeout=0 if polling else 10) as lease:
            yield root, lease
    except (RqSubmissionConflict, redis.RedisError, OSError) as exc:
        raise BatchReconciliationUnavailable('Batch reconciliation unavailable') from exc


def attempt_path(root, job):
    return inside(root, f'batch_results/{component(job.id)}')


def require_current(root, job):
    if read_json(inside(root, 'batch_results/current.json')).get('attempt_id') != job.id:
        raise ValueError('Superseded batch attempt')


def enroll(job, run_ids, *, model=True, watershed=True, hillslopes=False, watar=False):
    """Freeze a cohort before its dependent scientific jobs can execute."""
    workflow, resource, _ = identity(job)
    ids = [component(str(value)) for value in run_ids]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate batch cohort member')
    with lease_for(job) as (root, lease):
        job.refresh()
        if job.meta.get('cancel_requested') or status(job) in {'canceled', 'stopped'}:
            raise RuntimeError('Batch dispatch was canceled')
        directory = attempt_path(root, job)
        if (directory / 'enrollment.json').exists():
            require_current(root, job)
            prior = read_json(directory / 'enrollment.json')
            if (directory / 'summary.json').exists() or prior['members']:
                if ids and set(ids) != set(prior['members']):
                    raise ValueError('Cannot replace enrolled cohort')
                return
        enrollment = {'schema_version': 1, 'attempt_id': job.id, 'workflow': workflow,
                      'resource': resource, 'members': {rid: [] for rid in ids},
                      'model': model, 'watershed': watershed, 'hillslopes': hillslopes, 'watar': watar, 'finalizer': None}
        atomic_json(directory / 'enrollment.json', enrollment)
        lease.checkpoint()
        atomic_json(inside(root, 'batch_results/current.json'), {'attempt_id': job.id})
        job.meta['batch_outcome_enrolled'] = True
        job.meta['child_dispatch_lock_key'] = f'rq:submission:{workflow}:{resource}'
        job.result_ttl = -1
        job.failure_ttl = -1
        job.save()



def enrollment_for(root, job):
    value = read_json(attempt_path(root, job) / 'enrollment.json')
    workflow, resource, _ = identity(job)
    if (value.get('schema_version') != 1 or value.get('attempt_id') != job.id
            or value.get('workflow') != workflow or value.get('resource') != resource
            or not isinstance(value.get('members'), dict)):
        raise ValueError('Invalid batch enrollment identity')
    for rid, jobs in value['members'].items():
        component(rid)
        if not isinstance(jobs, list) or len(set(jobs)) != len(jobs):
            raise ValueError('Invalid batch execution membership')
        for jid in jobs:
            component(jid)
    for flag in ('model', 'watershed', 'hillslopes', 'watar'):
        if type(value.get(flag)) is not bool:
            raise ValueError('Invalid batch directive')
    if value.get('finalizer') is not None:
        component(value['finalizer'])
    return value

@contextmanager
def dispatch(job):
    """Serialize enrolled child creation/linkage with tree cancellation."""
    root_job = root_for_finalizer(job) if job is not None else None
    if root_job is None or not root_job.meta.get('batch_outcome_enrolled'):
        yield
        return
    with lease_for(root_job) as (root, lease):
        require_current(root, root_job)
        root_job.refresh()
        job.refresh()
        if (root_job.meta.get('cancel_requested') or job.meta.get('cancel_requested')
                or status(root_job) in {'canceled', 'stopped'} or status(job) in {'canceled', 'stopped'}):
            raise RuntimeError('Batch dispatch was canceled')
        lease.checkpoint()
        yield


def register(job, *, member=None, jobs=None, finalizer=None):
    with lease_for(job) as (root, lease):
        job.refresh()
        if job.meta.get('cancel_requested') or status(job) in {'canceled', 'stopped'}:
            raise RuntimeError('Batch dispatch was canceled')
        require_current(root, job)
        path = attempt_path(root, job) / 'enrollment.json'
        enrollment = enrollment_for(root, job)
        if (path.parent / 'summary.json').exists():
            if (member is not None and enrollment['members'].get(member) != jobs) or (finalizer is not None and enrollment['finalizer'] != finalizer):
                raise ValueError('Cannot replace committed execution identity')
            return
        if member is not None:
            if member not in enrollment['members']:
                raise ValueError('Unregistered batch member')
            enrollment['members'][member] = [component(str(value)) for value in jobs]
        if finalizer is not None:
            enrollment['finalizer'] = component(finalizer)
        lease.checkpoint()
        atomic_json(path, enrollment)


def invalidate_culvert(resource):
    """Called only under culvert admission's existing resource lease."""
    from wepppy.rq.culvert_rq_helpers import _resolve_batch_root
    root = _resolve_batch_root(component(resource)).resolve()
    path = inside(root, 'batch_results/current.json')
    if path.exists():
        atomic_json(path, {'attempt_id': None})


def status(job):
    raw = job.get_status(refresh=True)
    return str(getattr(raw, 'value', raw))


def fetch(job_id, connection):
    try:
        return Job.fetch(job_id, connection=connection)
    except NoSuchJobError:
        return None


def execution_jobs(root_job, enrollment, run_id):
    """Verify exact leaf identities and recursively registered Omni work."""
    expected_runid = f"{enrollment['workflow']};;{enrollment['resource']};;{run_id}"
    pending = list(enrollment['members'][run_id])
    seen = {}
    while pending:
        jid = pending.pop()
        if jid in seen:
            continue
        job = fetch(jid, root_job.connection)
        if job is None:
            raise LookupError('Missing batch execution identity')
        if job.func_name.startswith('wepppy.rq.omni_rq.'):
            if (job.func_name not in {'wepppy.rq.omni_rq.run_omni_scenario_rq',
                                      'wepppy.rq.omni_rq._compile_hillslope_summaries_rq',
                                      'wepppy.rq.omni_rq._finalize_omni_scenarios_rq'}
                    or job.meta.get('batch_root_job_id') != root_job.id
                    or not job.args or job.args[0] != expected_runid):
                raise ValueError('Foreign Omni execution identity')
        elif enrollment['workflow'] == 'batch':
            if job.func_name not in {'wepppy.rq.batch_rq.run_batch_hillslopes_rq',
                                     'wepppy.rq.batch_rq.run_batch_watershed_rq'}:
                raise ValueError('Foreign batch function')
            if (job.meta.get('batch_root_job_id') != root_job.id or job.meta.get('runid') != expected_runid
                    or len(job.args) != 3 or job.args[0] != enrollment['resource']
                    or str(getattr(job.args[1], 'runid', None)) != run_id):
                raise ValueError('Foreign batch execution identity')
        elif job.func_name != 'wepppy.rq.culvert_rq.run_culvert_run_rq' or tuple(job.args) != (
                expected_runid, enrollment['resource'], run_id):
            raise ValueError('Foreign culvert execution identity')
        seen[jid] = job
        pending.extend(value for key, value in job.meta.items() if key.startswith('jobs:'))
    return seen


def summary(job, enrollment, rows=(), *, state='running', reason=None):
    succeeded = sum(row['status'] == 'success' for row in rows)
    skipped = sum(row['status'] == 'skipped' for row in rows)
    failed = sum(row['status'] == 'failed' for row in rows)
    terminal = state in {'completed', 'failed'}
    available = state == 'completed' and succeeded > 0
    url = None
    if available:
        prefix = 'batch' if enrollment['workflow'] == 'batch' else 'culverts'
        url = f"/weppcloud/{prefix}/{quote(enrollment['resource'], safe='')}/download/batch_results/{quote(job.id, safe='')}/results.zip"
    return dict(schema_version=1, attempt_id=job.id, state=state,
                outcome=('partial_success' if failed else 'success') if available else ('failed' if terminal else None),
                total=len(enrollment['members']), succeeded=succeeded, failed=failed, skipped=skipped,
                results_available=available, download_url=url,
                reason=reason or ('no_usable_results' if terminal and not available else None))


def parse_output(name, data, *, culvert=False, required=False):
    if name.endswith('.parquet'):
        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(data))
        if name.endswith(('/H.loss.parquet', '/H.pass.parquet')):
            import pyarrow as pa
            required_columns = ({'wepp_id', 'Class', 'Diameter', 'Sediment Fraction'}
                                if name.endswith('/H.loss.parquet')
                                else {'wepp_id', 'event', 'year', 'julian', 'runoff', 'runvol'})
            if not required_columns.issubset(table.column_names):
                raise ValueError('Invalid hillslope result schema')
            for column in required_columns - {'event'}:
                dtype = table.schema.field(column).type
                if not (pa.types.is_integer(dtype) or pa.types.is_floating(dtype)):
                    raise ValueError('Invalid hillslope numeric field')
            if (required and table.num_rows == 0) or any(value is None or value <= 0 for value in table['wepp_id'].to_pylist()):
                raise ValueError('Missing hillslope output identity')
        if name.endswith('/loss_pw0.out.parquet'):
            if 'value' not in table.column_names or table.num_rows < 11:
                raise ValueError('Missing culvert metrics')
            frame = table.to_pandas()
            if not all(index in frame.index for index in range(11)):
                raise ValueError('Missing consumer metric labels')
            if any(value is None or not math.isfinite(float(value)) for value in frame.loc[list(range(11)), 'value']):
                raise ValueError('Invalid culvert metric')
    else:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError('Invalid result geometry object')
        if value.get('type') != 'FeatureCollection' or not isinstance(value.get('features'), list):
            raise ValueError('Invalid result geometry')
        if culvert and name.endswith('/subcatchments.WGS.geojson') and not value['features']:
            raise ValueError('Empty required result geometry')
        from shapely.geometry import shape
        from shapely.errors import ShapelyError
        for feature in value['features']:
            if not isinstance(feature, dict):
                raise ValueError('Invalid result feature object')
            if feature.get('type') != 'Feature' or not isinstance(feature.get('geometry'), dict):
                raise ValueError('Invalid result feature')
            try:
                geometry = shape(feature['geometry'])
            except (ShapelyError, KeyError) as exc:
                raise ValueError('Invalid result geometry') from exc
            if geometry.is_empty or not geometry.is_valid:
                raise ValueError('Invalid result geometry')



def read_member(root, path):
    """Open a resolved in-root file through non-symlink directory descriptors."""
    resolved = path.resolve(strict=True)
    relative = resolved.relative_to(root)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_fd = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
        with os.fdopen(file_fd, 'rb') as stream:
            return stream.read()
    finally:
        os.close(descriptor)

def output_files(root, enrollment, run_id):
    from wepppy.microservices.browse.auth import is_root_only_path
    from wepppy.microservices.browse.security import validate_raw_subpath
    run = inside(root, f'runs/{component(run_id)}')
    required = set()
    if enrollment['watershed']:
        required.add('wepp/output/interchange/loss_pw0.out.parquet')
    if enrollment.get('hillslopes') or not enrollment['watershed']:
        from wepppy.nodb.core import Climate
        climate = Climate.getInstance(str(run))
        required.add('wepp/output/interchange/H.pass.parquet' if climate.is_single_storm
                     else 'wepp/output/interchange/H.loss.parquet')
    if enrollment['workflow'] == 'culvert':
        required.update({'dem/wbt/subcatchments.WGS.geojson', 'dem/wbt/channels.WGS.geojson'})
    paths = []
    for directory, suffix in [('wepp/output/interchange', '.parquet'), ('dem/wbt', '.geojson')]:
        base = inside(run, directory)
        if not base.exists():
            continue
        for current, dirs, names in os.walk(base, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(current) / name).is_symlink()]
            for name in names:
                path = Path(current) / name
                if path.suffix != suffix:
                    continue
                rel = path.relative_to(run).as_posix()
                target = path.resolve(strict=True)
                if not target.is_relative_to(run):
                    raise ValueError('Escaping result member')
                target_rel = target.relative_to(run).as_posix()
                for candidate in (f"runs/{run_id}/{rel}", f"runs/{run_id}/{target_rel}"):
                    if validate_raw_subpath(candidate) or is_root_only_path(candidate):
                        raise ValueError('Restricted result member')
                # A scientific filename cannot disguise a log or other excluded target.
                if target.suffix != suffix or not any(target_rel.startswith(prefix + '/') for prefix in ('wepp/output/interchange', 'dem/wbt')):
                    raise ValueError('Invalid result symlink target')
                data = read_member(run, path)
                parse_output(rel, data, culvert=enrollment['workflow'] == 'culvert', required=rel in required)
                paths.append((f'runs/{run_id}/{rel}', path, hashlib.sha256(data).hexdigest()))
                required.discard(rel)
    if required:
        raise ValueError('Required result missing')
    return paths


def root_for_finalizer(job):
    if getattr(job, 'func_name', None) in ROOTS:
        return job
    root_id = job.meta.get('batch_outcome_root_id') or job.meta.get('batch_root_job_id')
    return fetch(root_id, job.connection) if root_id else None



def verify_finalizer(root_job, enrollment, finalizer):
    expected = ('wepppy.rq.batch_rq._final_batch_complete_rq' if enrollment['workflow'] == 'batch'
                else 'wepppy.rq.culvert_rq._final_culvert_batch_complete_rq')
    if root_job.id == finalizer.id and root_job.func_name == 'wepppy.rq.culvert_rq.run_culvert_batch_finalize_rq':
        return
    if (finalizer.func_name != expected or tuple(finalizer.args) != (enrollment['resource'],)
            or (finalizer.meta.get('batch_outcome_root_id') or finalizer.meta.get('batch_root_job_id')) != root_job.id):
        raise ValueError('Foreign batch finalizer')

def publish(finalizer):
    root_job = root_for_finalizer(finalizer)
    if root_job is None or not root_job.meta.get('batch_outcome_enrolled'):
        return None  # Existing retained jobs keep their legacy finalizer behavior.
    with lease_for(root_job) as (root, lease):
        require_current(root, root_job)
        directory = attempt_path(root, root_job)
        enrollment = enrollment_for(root, root_job)
        verify_finalizer(root_job, enrollment, finalizer)
        if enrollment['finalizer'] != finalizer.id:
            raise ValueError('Foreign batch finalizer')
        committed = directory / 'summary.json'
        if committed.exists():
            return committed_summary(root_job, enrollment, committed)
        root_job.refresh()
        finalizer.refresh()
        if (root_job.meta.get('cancel_requested') or finalizer.meta.get('cancel_requested')
                or status(root_job) in {'stopped', 'canceled'} or status(finalizer) in {'stopped', 'canceled'}):
            result = summary(root_job, enrollment, [{'status': 'failed'} for _ in enrollment['members']],
                             state='failed', reason='canceled')
            atomic_json(directory / 'runs.json', {'schema_version': 1, 'attempt_id': root_job.id,
                        'workflow': enrollment['workflow'], 'runs': [
                            {'run_id': rid, 'status': 'failed', 'reason': 'execution_failed'}
                            for rid in enrollment['members']]})
            atomic_json(committed, result)
            return result
        atomic_json(directory / 'status.json', {'last_observed_at': datetime.now(timezone.utc).isoformat(),
                                             'batch': summary(root_job, enrollment, state='finalizing')})
    rows, files = [], []
    observed_states = {}
    temporary = None
    for run_id in enrollment['members']:
        row = {'run_id': run_id, 'status': 'failed', 'reason': 'execution_failed'}
        try:
            jobs = execution_jobs(root_job, enrollment, run_id)
            states = [status(job) for job in jobs.values()]
            observed_states.update(zip(jobs, states))
            if any(value not in TERMINAL or (value == 'failed' and getattr(item, 'retries_left', 0))
                   for item, value in zip(jobs.values(), states)):
                raise RuntimeError('Batch execution remains active')
            returned_failure = any((item.func_name.endswith('run_batch_watershed_rq') and isinstance(item.result, (list, tuple)) and item.result[0] is False)
                                   or (item.func_name.endswith('run_culvert_run_rq') and item.result == 'failed')
                                   for item in jobs.values())
            if not jobs or returned_failure or any(value != 'finished' for value in states):
                rows.append(row)
                continue
            metadata = read_json(inside(root, f'runs/{run_id}/run_metadata.json'))
            if not isinstance(metadata, dict):
                raise ValueError('Invalid run receipt object')
            if metadata.get('rq_job_id') not in enrollment['members'][run_id]:
                raise ValueError('Stale run result receipt')
            if metadata.get('status') == 'skipped_no_outlet':
                row.update(status='skipped', reason='no_outlet')
            elif metadata.get('status') != 'success':
                pass
            elif not enrollment['model'] and not (enrollment.get('watar') and inside(root, f'runs/{run_id}/ash.nodb').is_file()):
                row.update(status='skipped', reason='no_result_outputs')
            else:
                effective = dict(enrollment)
                if enrollment.get('watar') and inside(root, f'runs/{run_id}/ash.nodb').is_file():
                    effective['watershed'] = True
                members = output_files(root, effective, run_id)
                files.extend(members)
                row.update(status='success', reason=None)
        except LookupError:
            row['reason'] = 'not_executed'
        except (OSError, ValueError, TypeError):
            logger.exception('Batch output rejected attempt=%s run=%s', root_job.id, run_id)
            row['reason'] = 'outputs_invalid'
        rows.append(row)
    manifest = {'schema_version': 1, 'attempt_id': root_job.id,
                'workflow': enrollment['workflow'], 'runs': rows}
    result = summary(root_job, enrollment, rows, state='completed')
    if result['results_available']:
        fd, temporary_name = tempfile.mkstemp(prefix='results.working-', suffix='.zip', dir=directory)
        temporary = Path(temporary_name)
        with os.fdopen(fd, 'w+b') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('runs.json', json.dumps(manifest, sort_keys=True))
            for name, path, digest in files:
                data = read_member(root, path)
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError('Result changed before archive write')
                archive.writestr(name, data)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None or json.loads(archive.read('runs.json')) != manifest:
                raise ValueError('Result archive validation failed')
            if set(archive.namelist()) != {'runs.json', *(name for name, _, _ in files)}:
                raise ValueError('Result archive membership mismatch')
            for name, _, digest in files:
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError('Result changed during publication')
                parse_output(name, data, culvert=enrollment['workflow'] == 'culvert')
    with lease_for(root_job) as (root, lease):
        require_current(root, root_job)
        if enrollment_for(root, root_job) != enrollment:
            raise ValueError('Batch enrollment changed during publication')
        if committed.exists():
            return committed_summary(root_job, enrollment, committed)
        root_job.refresh()
        finalizer.refresh()
        if (root_job.meta.get('cancel_requested') or finalizer.meta.get('cancel_requested')
                or status(root_job) in {'stopped', 'canceled'} or status(finalizer) in {'stopped', 'canceled'}):
            result = summary(root_job, enrollment, [{'status': 'failed'} for _ in enrollment['members']],
                             state='failed', reason='canceled')
        else:
            for jid, previous in observed_states.items():
                current = fetch(jid, root_job.connection)
                if current is None or status(current) != previous:
                    raise RuntimeError('Batch source execution changed during publication')
            if temporary is not None:
                os.replace(temporary, directory / 'results.zip')
        if result['reason'] == 'canceled':
            manifest['runs'] = [{'run_id': rid, 'status': 'failed', 'reason': 'execution_failed'}
                                for rid in enrollment['members']]
        atomic_json(directory / 'runs.json', manifest)
        lease.checkpoint()
        atomic_json(committed, result)
        return result


def committed_summary(job, enrollment, committed):
    result = read_json(committed)
    if result.get('attempt_id') != job.id or result.get('schema_version') != 1:
        raise ValueError('Invalid committed batch identity')
    if result.get('state') not in {'completed', 'failed'}:
        raise ValueError('Invalid committed batch state')
    for key in ('total', 'succeeded', 'failed', 'skipped'):
        if type(result.get(key)) is not int or result[key] < 0:
            raise ValueError('Invalid batch count')
    if result['total'] != len(enrollment['members']) or result['total'] != sum(result[key] for key in ('succeeded', 'failed', 'skipped')):
        raise ValueError('Invalid batch partition')
    expected_available = result['state'] == 'completed' and result['succeeded'] > 0
    expected_outcome = ('partial_success' if result['failed'] else 'success') if expected_available else 'failed'
    expected_url = None
    if expected_available:
        prefix = 'batch' if enrollment['workflow'] == 'batch' else 'culverts'
        expected_url = f"/weppcloud/{prefix}/{quote(enrollment['resource'], safe='')}/download/batch_results/{quote(job.id, safe='')}/results.zip"
    if (result.get('results_available') is not expected_available or result.get('outcome') != expected_outcome
            or result.get('download_url') != expected_url or result.get('reason') not in
            {None, 'no_usable_results', 'dispatch_failed', 'finalization_failed', 'canceled', 'execution_record_missing'}):
        raise ValueError('Invalid batch public summary')
    return {key: result[key] for key in PUBLIC}

def _poll(job):
    if job.meta.get('batch_outcome_enrolled') is not True or job.func_name not in ROOTS:
        return None
    with lease_for(job, polling=True) as (root, lease):
        directory = attempt_path(root, job)
        enrollment = enrollment_for(root, job)
        committed = directory / 'summary.json'
        if committed.exists():
            # Reconstruct URLs and allowlisted fields, never return file-supplied extras.
            return committed_summary(job, enrollment, committed)
        require_current(root, job)
        missing_execution = False
        if status(job) == 'finished':
            try:
                for rid in enrollment['members']:
                    execution_jobs(job, enrollment, rid)
                reconcile_omni(job, enrollment)
            except LookupError:
                missing_execution = True
        finalizer = fetch(enrollment['finalizer'], job.connection) if enrollment['finalizer'] else None
        if finalizer is not None:
            verify_finalizer(job, enrollment, finalizer)
        reason = None
        root_status = status(job)
        if root_status in {'stopped', 'canceled'} or (root_status == 'failed' and not getattr(job, 'retries_left', 0)):
            reason = 'dispatch_failed' if root_status == 'failed' else 'canceled'
        elif missing_execution or (root_status == 'finished' and enrollment['finalizer'] and finalizer is None):
            reason = 'execution_record_missing'
        elif finalizer is not None:
            final_status = status(finalizer)
            if final_status in {'stopped', 'canceled', 'finished'} or (final_status == 'failed' and not getattr(finalizer, 'retries_left', 0)):
                reason = 'canceled' if final_status in {'stopped', 'canceled'} else 'finalization_failed'
        if reason:
            rows = [{'run_id': rid, 'status': 'failed', 'reason': 'execution_failed'}
                    for rid in enrollment['members']]
            result = summary(job, enrollment, rows, state='failed', reason=reason)
            lease.checkpoint()
            atomic_json(directory / 'runs.json', {'schema_version': 1, 'attempt_id': job.id,
                                                 'workflow': enrollment['workflow'], 'runs': rows})
            atomic_json(committed, result)
            return result
        return summary(job, enrollment, state='finalizing' if finalizer and status(finalizer) == 'started' else 'running')


def reconcile_omni(root_job, enrollment):
    """Cancel only proven blocked Omni nodes, preserving the batch finalizer."""
    if enrollment['workflow'] != 'batch' or not enrollment['finalizer']:
        return
    if root_job.meta.get('batch_pending_omni_links'):
        return
    finalizer = fetch(enrollment['finalizer'], root_job.connection)
    if finalizer is None:
        return
    if (finalizer.func_name != 'wepppy.rq.batch_rq._final_batch_complete_rq'
            or tuple(finalizer.args) != (enrollment['resource'],)
            or finalizer.meta.get('batch_root_job_id') != root_job.id):
        raise ValueError('Foreign batch finalizer identity')
    graph = {}
    for run_id in enrollment['members']:
        graph.update(execution_jobs(root_job, enrollment, run_id))
    graph[root_job.id] = root_job
    graph[finalizer.id] = finalizer
    with root_job.connection.pipeline() as pipe:
        for job in graph.values():
            pipe.watch(job.key, job.dependencies_key, job.dependents_key)
        states = {}
        dependencies = {}
        for jid, job in graph.items():
            job.refresh()
            states[jid] = status(job)
            dependencies[jid] = set(job._dependency_ids or [])
            if not dependencies[jid].issubset(graph):
                raise ValueError('Foreign batch dependency')
            dependent_ids = {item.decode() if isinstance(item, bytes) else str(item)
                             for item in pipe.smembers(job.dependents_key)}
            if not dependent_ids.issubset(graph):
                raise ValueError('Foreign batch dependent')
            stored_dependencies = {item.decode() if isinstance(item, bytes) else str(item)
                                   for item in pipe.smembers(job.dependencies_key)}
            if states[jid] == 'deferred' and stored_dependencies != dependencies[jid]:
                raise ValueError('Inconsistent batch dependencies')
            registered_children = {value for key, value in job.meta.items() if key.startswith('jobs:')}
            if not registered_children.issubset(graph):
                raise ValueError('Foreign registered batch child')
        verified = {}
        for run_id in enrollment['members']:
            verified.update(execution_jobs(root_job, enrollment, run_id))
        if set(verified) != set(graph) - {root_job.id, finalizer.id}:
            raise BatchReconciliationUnavailable('Batch graph membership changed')
        if (finalizer.func_name != 'wepppy.rq.batch_rq._final_batch_complete_rq'
                or tuple(finalizer.args) != (enrollment['resource'],)
                or finalizer.meta.get('batch_root_job_id') != root_job.id):
            raise ValueError('Foreign batch finalizer identity')
        if root_job.meta.get('batch_pending_omni_links'):
            return
        blocked = {jid for jid, state in states.items() if state in {'stopped', 'canceled'} or (state == 'failed'
                   and not getattr(graph[jid], 'retries_left', 0))}
        canceled = set()
        changed = True
        while changed:
            changed = False
            for jid, job in graph.items():
                if (states[jid] == 'deferred' and jid not in canceled
                        and job.func_name.startswith('wepppy.rq.omni_rq.')
                        and dependencies[jid] & blocked):
                    canceled.add(jid)
                    blocked.add(jid)
                    changed = True
        final_deps = dependencies[finalizer.id]
        release = (states[finalizer.id] == 'deferred' and finalizer.allow_dependency_failures
                   and all((states[jid] in TERMINAL and not (states[jid] == 'failed' and getattr(graph[jid], 'retries_left', 0)))
                           or jid in canceled for jid in final_deps))
        pipe.multi()
        for jid in canceled:
            graph[jid].cancel(pipeline=pipe, enqueue_dependents=False)
            for dependency in dependencies[jid]:
                pipe.srem(graph[dependency].dependents_key, jid)
        if release:
            from rq.registry import DeferredJobRegistry
            queue = Queue(finalizer.origin, connection=root_job.connection)
            for dependency in final_deps:
                pipe.srem(graph[dependency].dependents_key, finalizer.id)
            pipe.delete(finalizer.dependencies_key)
            DeferredJobRegistry(queue=queue).remove(finalizer, pipeline=pipe)
            queue._enqueue_job(finalizer, pipeline=pipe)
        try:
            pipe.execute()
        except redis.WatchError as exc:
            raise BatchReconciliationUnavailable('Batch graph changed during reconciliation') from exc


def observe_failure(job):
    root_id = job.meta.get('batch_root_job_id') or job.meta.get('batch_outcome_root_id')
    root = fetch(root_id, job.connection) if root_id else job
    if root is not None and root.func_name in ROOTS and root.meta.get('batch_outcome_enrolled'):
        poll(root)


def poll(job):
    try:
        result = _poll(job)
        return result
    except (OSError, ValueError, KeyError, TypeError, LookupError, redis.RedisError) as exc:
        raise BatchReconciliationUnavailable('Batch reconciliation unavailable') from exc


def _observe_project(root):
    """Reconcile an authorized normal project view; expired jobs remain historical."""
    root = Path(root).resolve()
    pointer = inside(root, 'batch_results/current.json')
    if not pointer.exists():
        return
    attempt = read_json(pointer).get('attempt_id')
    if attempt is None:
        return
    component(attempt)
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        job = fetch(attempt, connection)
        if job is None:
            return
        if identity(job)[2] != root:
            raise ValueError('Foreign project attempt')
        poll(job)


def observe_project(root):
    try:
        return _observe_project(root)
    except (OSError, ValueError, KeyError, TypeError, LookupError, redis.RedisError) as exc:
        raise BatchReconciliationUnavailable('Batch reconciliation unavailable') from exc
