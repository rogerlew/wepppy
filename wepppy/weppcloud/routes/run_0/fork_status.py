"""Read and present the current fork outcome for an authorized project page."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass

import redis
from flask import abort, g, make_response, render_template, request
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from werkzeug.exceptions import HTTPException

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.weppcloud.utils.helpers import authorize, get_run_owners_lazy, get_wd, url_for_run

FORK_DESTINATION_REQUIRED_FILES = ('ron.nodb', 'wepp.nodb', 'landuse.nodb', 'soils.nodb')
_PAGE_FILES = (*FORK_DESTINATION_REQUIRED_FILES, 'climate.nodb', 'watershed.nodb')
_RECEIPT_FIELDS = ('job_id', 'source_runid', 'target_runid', 'state', 'failed_job_id')
_ACTIVE_STATES = {'planned', 'enqueued', 'running', 'waiting_finalizer'}
_FORK_FUNCTION = 'wepppy.rq.project_rq.fork_rq'
_WEPP_FUNCTION_PREFIX = 'wepppy.rq.wepp_rq.'
_FAILED_STAGES = {
    '_analyze_return_periods_rq': 'Return-period reports could not be generated.',
    '_post_gpkg_export_rq': 'Spatial results could not be exported.',
    '_post_watershed_interchange_rq': 'Watershed outputs could not be prepared for reports.',
}


@dataclass(frozen=True)
class ForkPageStatus:
    snapshot: tuple
    message: str = ''
    detail: str = ''
    simulation_finished: bool = False
    details_url: str | None = None
    console_url: str | None = None
    show_project: bool = False
    project_root: str | None = None
    failed: bool = False


def _receipt(conn, runid):
    planned = f'rq:fork:planned:{runid}'
    with conn.pipeline() as pipe:
        pipe.get(f'rq:fork:destination:{runid}')
        pipe.exists(planned)
        pipe.hmget(planned, _RECEIPT_FIELDS)
        pointer, present, fields = pipe.execute(raise_on_error=False)
    for result in (pointer, present, fields):
        if isinstance(result, redis.exceptions.ResponseError):
            if not str(result).startswith('WRONGTYPE'):
                raise result
            return '', True, (None,) * len(_RECEIPT_FIELDS)
    return pointer, bool(present), tuple(fields)


def _text(value):
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value


def _fetch_job(conn, job_id):
    if job_id:
        try:
            return Job.fetch(job_id, connection=conn)
        except NoSuchJobError:
            pass
    return None


def _source_visible(source, config):
    try:
        # Resolve the configured run rather than accepting a path from the receipt.
        if not stat.S_ISDIR(os.stat(get_wd(source, prefer_active=False, read_only=True)).st_mode):
            return False
        authorize(source, config, guard_output_scope=False)
    except (ValueError, FileNotFoundError):
        return False
    except HTTPException as exc:
        if exc.code in {401, 403, 404}:
            return False
        raise
    return True


def _has_core_files(wd):
    try:
        fd = os.open(wd, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except (FileNotFoundError, NotADirectoryError):
        return False
    try:
        for filename in _PAGE_FILES:
            info = os.stat(filename, dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
                return False
        return True
    except FileNotFoundError:
        return False
    finally:
        os.close(fd)


def _wepp_outcome(conn, root, target, failed_id):
    job_ids = {value for key, value in root.meta.items() if key.startswith('jobs:') and isinstance(value, str)}
    detail = ''
    simulation_finished = False
    for job in Job.fetch_many(sorted(job_ids), connection=conn):
        if not job or job.origin != 'default' or not job.args or job.args[0] != target:
            continue
        if not job.func_name.startswith(_WEPP_FUNCTION_PREFIX):
            continue
        name = job.func_name.removeprefix(_WEPP_FUNCTION_PREFIX)
        if name == 'run_watershed_rq' and job.get_status() == JobStatus.FINISHED:
            result = job.return_value()
            simulation_finished = simulation_finished or (
                isinstance(result, (tuple, list)) and bool(result) and result[0] is True
            )
        if job.id == failed_id and job.get_status() == JobStatus.FAILED:
            detail = _FAILED_STAGES.get(name, '')
    return detail, simulation_finished


def fork_page_status(runid, config):
    """Return status after the run route has authorized the destination."""
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
        snapshot = _receipt(conn, runid)
        pointer, present, fields = snapshot
        if pointer is None and not present:
            return ForkPageStatus(snapshot, show_project=True)

        # Reservation can register destination ownership after the route's first
        # check. A new owner list is never evidence of the viewer's admission.
        authorize(runid, config, guard_output_scope=False)
        if pointer and not present:
            legacy = _fetch_job(conn, _text(pointer))
            if (legacy and legacy.func_name == _FORK_FUNCTION and legacy.origin == 'fork-archive'
                    and len(legacy.args) >= 2 and legacy.args[1] == runid
                    and legacy.get_status(refresh=True) == JobStatus.FINISHED):
                return ForkPageStatus(snapshot, show_project=True)

        job_id, source, target, state, failed_id = map(_text, fields)
        coherent = bool(
            job_id and source and source != runid and target == runid
            and job_id == _text(pointer) and state in _ACTIVE_STATES | {'failed', 'succeeded'}
        )
        root = _fetch_job(conn, job_id) if coherent else None
        matching_root = bool(
            root and root.origin == 'fork-archive' and root.func_name == _FORK_FUNCTION
            and tuple(root.args[:2]) == (source, runid)
        )
        if coherent and state == 'succeeded' and (root is None or matching_root):
            return ForkPageStatus(snapshot, show_project=True)

        source_visible = coherent and (root is None or matching_root) and _source_visible(source, config)
        if not get_run_owners_lazy(runid) and not source_visible:
            abort(404)

        if not coherent or (root and not matching_root):
            return ForkPageStatus(snapshot, 'Project preparation status is unavailable.')

        root_status = root.get_status(refresh=True) if matching_root else None
        copied = root_status == JobStatus.FINISHED
        failed = state == 'failed' or root_status in {JobStatus.FAILED, JobStatus.CANCELED, JobStatus.STOPPED}
        wd = get_wd(runid, prefer_active=False, read_only=True) if copied else None
        show_project = bool(wd and not request.args.get('pup') and _has_core_files(wd))
        detail, simulation_finished = (
            _wepp_outcome(conn, root, runid, failed_id)
            if failed and failed_id and copied else ('', False)
        )
        if failed:
            message = (
                'The project was copied, but postprocessing failed.'
                if detail else 'Project preparation failed.'
            )
        else:
            message = 'This project is still being prepared.'

        return ForkPageStatus(
            snapshot, message, detail, simulation_finished,
            details_url=url_for_run('rq_job_dashboard.job_dashboard_route', job_id=job_id)
            if source_visible and matching_root else None,
            console_url=url_for_run('fork.rq_fork_console', runid=source, config=config)
            if source_visible and matching_root else None,
            show_project=show_project, project_root=wd if show_project else None, failed=failed,
        )


def finish_fork_page(runid, config, status, response=None):
    """Check that the observed attempt still owns the destination before release."""
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
        changed = _receipt(conn, runid) != status.snapshot
    if changed:
        # Destination ownership can also have changed with the fork reservation.
        authorize(runid, config, guard_output_scope=False)
        if not get_run_owners_lazy(runid):
            abort(404)
        status = ForkPageStatus(status.snapshot, 'Project preparation changed. Refresh to check its status.')
        response = None
    if response is not None and not status.message:
        return response
    if response is None:
        g.skip_page_query_cookie = True
        response = render_template('fork_run_status.htm', runid=runid, config=config, fork_status=status)
    response = make_response(response)
    response.headers['Cache-Control'] = 'private, no-store'
    return response
