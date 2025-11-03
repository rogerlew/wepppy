import os
import json
import io

import pathlib
from pathlib import Path
from subprocess import Popen, PIPE

from typing import Optional

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from os.path import abspath, basename

import redis

from flask import Response, abort, Blueprint, current_app, request, render_template, url_for
from flask_security import current_user

from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.weppcloudr_rq import render_deval_details_rq

from wepppy.weppcloud.utils.helpers import get_wd, exception_factory, url_for_run

from wepppy.nodb.core import Ron, Wepp, Watershed
from wepppy.query_engine.activate import activate_query_engine

from ._run_context import RunContext, load_run_context

VIZ_RSCRIPT_DIR = '/workdir/viz-weppcloud/scripts/R/'
VIZ_RMARKDOWN_DIR = '/workdir/viz-weppcloud/scripts/Rmd'
WEPPCLOUDR_DIR = '/workdir/WEPPcloudR/scripts'


weppcloudr_bp = Blueprint('weppcloud', __name__)

@weppcloudr_bp.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>/')
def viz_r(runid, config, r_format, routine):
    from wepppy.weppcloud.app import get_run_owners

    assert config is not None

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if not owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if ron.public:
        should_abort = False

    if should_abort:
        abort(404)

    viz_export_dir = _join(wd, 'export/viz')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    try:
        rpt_fn = _join(viz_export_dir, f'{routine}.htm')

        if r_format.lower() == 'r':
            rscript = _join(VIZ_RSCRIPT_DIR, f'{routine}.R')
            assert _exists(rscript)
            cmd = ['Rscript', rscript, runid]
        elif r_format.lower() == "rmd":
            rscript = _join(VIZ_RMARKDOWN_DIR, f'{routine}.Rmd')
            assert _exists(rscript)
            cmd = ['R', '-e', f'library("rmarkdown"); rmarkdown::render("{rscript}", params=list(proj_runid="{runid}"), output_file="{routine}.htm", output_dir="{viz_export_dir}")']

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
        with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
            fp.write(output.decode('utf-8'))
        with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
            fp.write(errors.decode('utf-8'))

        assert _exists(rpt_fn)
        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except:
        return exception_factory('Error running script', runid=runid)



def _weppcloudr_script_locator(routine, user=None):
    global WEPPCLOUDR_DIR 
    if user is None:
        return _join(WEPPCLOUDR_DIR, routine)
    else:
        rscript =  _join(WEPPCLOUDR_DIR, 'users', user, routine)
        assert pathlib.Path(WEPPCLOUDR_DIR) in  pathlib.Path(rscript).parents
        return rscript


@weppcloudr_bp.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>/')
def weppcloudr(runid, config, routine):
    from wepppy.weppcloud.app import get_run_owners

    assert config is not None

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if not owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if ron.public:
        should_abort = False

    if should_abort:
        abort(404)

    user = request.args.get('user', None)
    
    return weppcloudr_runner(runid, config, routine, user, ctx=ctx)


def weppcloudr_runner(runid, config, routine, user, ctx: Optional[RunContext] = None):
    from wepppy.weppcloud.app import get_file_sha1
    if ctx is None:
        ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    viz_export_dir = _join(wd, 'export/WEPPcloudR')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    sub_fn = _join(wd, 'export', 'totalwatsed2.csv')
    sub_sha = get_file_sha1(sub_fn)

    try:
        assert routine.endswith('.R') or routine.endswith('.Rmd'), routine

        r_format = routine.split('.')[-1] 
        rpt_fn = _join(viz_export_dir, f'{routine}.{sub_sha}.htm')

        if not _exists(rpt_fn):
            rscript = _weppcloudr_script_locator(routine, user=user)
            assert _exists(rscript)

            if r_format.lower() == 'r':
                cmd = ['Rscript', rscript, runid]
            elif r_format.lower() == "rmd":
                cmd = ['R', '-e', f'library("rmarkdown"); rmarkdown::render("{rscript}", params=list(proj_runid="{runid}"), output_file="{rpt_fn}", output_dir="{viz_export_dir}")']

            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, errors = p.communicate()
            output = output.decode('utf-8')
            errors = errors.decode('utf-8')
            with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
                fp.write(output)
            with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
                fp.write(errors)

        if not _exists(rpt_fn):
            return f'''
<html>
<h3>Error running script</h3>

<h5>stdout</h5>
<pre>
{output}
</pre>

<h5>stderr</h5>
<pre>
{errors}
</pre>
</html>'''

        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except:
        return exception_factory('Error running script')


def _ensure_interchange(ctx: RunContext) -> None:
    wd = str(ctx.active_root)
    try:
        activate_query_engine(wd, run_interchange=True)
    except Exception:
        current_app.logger.exception("Interchange activation failed for %s", wd)
        raise


ACTIVE_JOB_STATUSES = {'queued', 'started', 'deferred', 'scheduled'}


def _deval_output_path(ctx: RunContext, runid: str) -> Path:
    export_root = Path(ctx.active_root) / "export" / "WEPPcloudR"
    return export_root / f"deval_{runid}.htm"


def _normalize_job_key_component(value: str) -> str:
    return (
        value.replace('/', '__')
        .replace('\\', '__')
        .replace(':', '_')
        .replace(' ', '_')
    )


def _deval_job_key(ctx: RunContext) -> str:
    parts = ['deval_details']
    if ctx.pup_relpath:
        parts.append(_normalize_job_key_component(ctx.pup_relpath))
    elif ctx.config:
        parts.append(_normalize_job_key_component(ctx.config))
    return '_'.join(parts)


def _resolve_prep(ctx: RunContext) -> Optional[RedisPrep]:
    prep = RedisPrep.tryGetInstance(str(ctx.active_root))
    if prep is None:
        prep = RedisPrep.tryGetInstance(str(ctx.run_root))
    return prep


def _lookup_job_status(redis_conn: redis.Redis, job_id: str) -> str:
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return 'not_found'
    status = job.get_status()
    return status or 'unknown'


def _clear_tracked_job(prep: RedisPrep, job_key: str) -> None:
    try:
        prep.redis.hdel(prep.run_id, f"rq:{job_key}")
        prep.dump()
    except Exception:
        # Clearing the cached metadata is best-effort; failures shouldn't break the request flow.
        pass


def _enqueue_deval_job(
    ctx: RunContext,
    runid: str,
    config: str,
    *,
    skip_cache: bool,
) -> tuple[str, str]:
    job_key = _deval_job_key(ctx)
    prep = _resolve_prep(ctx)
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)

    with redis.Redis(**conn_kwargs) as redis_conn:
        existing_job_id: Optional[str] = None
        existing_status: Optional[str] = None

        if prep:
            try:
                existing_job_id = prep.get_rq_job_id(job_key)
            except Exception:
                existing_job_id = None

        if existing_job_id:
            existing_status = _lookup_job_status(redis_conn, existing_job_id)
            if existing_status in ACTIVE_JOB_STATUSES:
                return existing_job_id, existing_status
            if prep:
                _clear_tracked_job(prep, job_key)

        job_kwargs = {'skip_cache': bool(skip_cache)}

        container_name = current_app.config.get('WEPPCLOUDR_CONTAINER')
        if container_name:
            job_kwargs['container_name'] = container_name

        docker_timeout = current_app.config.get('WEPPCLOUDR_COMMAND_TIMEOUT')
        if docker_timeout:
            job_kwargs['timeout'] = docker_timeout

        job_timeout = current_app.config.get('WEPPCLOUDR_JOB_TIMEOUT', current_app.config.get('WEPPCLOUDR_TIMEOUT', 3600))

        queue = Queue(connection=redis_conn)
        job = queue.enqueue_call(
            func=render_deval_details_rq,
            args=(runid, config, str(ctx.active_root)),
            kwargs=job_kwargs,
            timeout=job_timeout,
            description=f"Render Deval-In-The-Details report for {runid}/{config}",
        )

        if prep:
            try:
                prep.set_rq_job_id(job_key, job.id)
            except Exception:
                # Persisting job metadata is best-effort.
                pass

        return job.id, 'queued'


def _determine_job(
    ctx: RunContext,
    runid: str,
    config: str,
    *,
    skip_cache: bool,
) -> tuple[Optional[str], Optional[str]]:
    job_key = _deval_job_key(ctx)
    prep = _resolve_prep(ctx)
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)

    with redis.Redis(**conn_kwargs) as redis_conn:
        job_id: Optional[str] = None
        job_status: Optional[str] = None

        if prep:
            try:
                job_id = prep.get_rq_job_id(job_key)
            except Exception:
                job_id = None

        if job_id:
            job_status = _lookup_job_status(redis_conn, job_id)
        else:
            job_status = None

        file_exists = _deval_output_path(ctx, runid).exists()

        # Skip cache requests always enqueue a fresh job unless one is already active.
        if skip_cache:
            if job_id and job_status in ACTIVE_JOB_STATUSES:
                return job_id, job_status
            return _enqueue_deval_job(ctx, runid, config, skip_cache=skip_cache)

        if file_exists:
            if job_id and job_status in ACTIVE_JOB_STATUSES:
                return job_id, job_status
            return job_id, job_status

        # No cached file; ensure a job is enqueued.
        if job_id and job_status in ACTIVE_JOB_STATUSES:
            return job_id, job_status

        if job_id and job_status not in ACTIVE_JOB_STATUSES and prep:
            _clear_tracked_job(prep, job_key)

        return _enqueue_deval_job(ctx, runid, config, skip_cache=skip_cache)


def _serve_deval_file(path: Path) -> Response:
    content = path.read_bytes()
    response = Response(content, mimetype='text/html')
    response.headers['Content-Length'] = str(len(content))
    response.headers.setdefault('Cache-Control', 'no-store, max-age=0, must-revalidate')
    response.headers.setdefault('Content-Disposition', f'inline; filename="{path.name}"')
    response.headers['X-Report-Cache'] = 'hit'
    return response


@weppcloudr_bp.route('/runs/<string:runid>/<config>/report/deval_details')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/report/deval_details/')
def deval_details(runid, config):
    ctx = load_run_context(runid, config)
    try:
        _ensure_interchange(ctx)
    except Exception:
        return exception_factory('Error preparing interchange assets', runid=runid)

    skip_cache = 'no-cache' in request.args
    output_path = _deval_output_path(ctx, runid)

    job_id, job_status = _determine_job(ctx, runid, config, skip_cache=skip_cache)

    # Serve the cached file when no active job is running (unless skip-cache was requested).
    if not skip_cache and output_path.exists() and job_status not in ACTIVE_JOB_STATUSES:
        return _serve_deval_file(output_path)

    refresh_kwargs = {'runid': runid, 'config': config}
    if ctx.pup_relpath:
        refresh_kwargs['pup'] = ctx.pup_relpath

    refresh_url = url_for_run('weppcloud.deval_details', **refresh_kwargs)
    job_status_url = url_for('rq_jobinfo.jobstatus_route', job_id=job_id) if job_id else None
    job_dashboard_url = url_for('rq_job_dashboard.job_dashboard_route', job_id=job_id) if job_id else None

    context = {
        'runid': runid,
        'config': config,
        'job_id': job_id,
        'job_status': job_status,
        'job_status_url': job_status_url,
        'job_dashboard_url': job_dashboard_url,
        'refresh_url': refresh_url,
        'skip_cache': skip_cache,
    }

    html = render_template('reports/deval_loading.htm', **context)
    response = Response(html, status=202, mimetype='text/html')
    response.headers['Cache-Control'] = 'no-store, max-age=0, must-revalidate'
    return response


@weppcloudr_bp.route('/WEPPcloudR/proxy/<routine>', methods=['GET', 'POST'])
@weppcloudr_bp.route('/WEPPcloudR/proxy/<routine>/', methods=['GET', 'POST'])
def weppcloudr_proxy(routine):
    from wepppy.weppcloud.app import user_datastore

    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')

    user = request.args.get('user', None)
    runids = request.args.get('runids', '')
    runids = runids.replace(',', ' ').split()

    try:

        ws = []
        for i, runid in enumerate(runids):
            if runid.endswith('/'):
                runid = runid[:-1]

            wd = get_wd(runid)
            try:
                ron = Ron.getInstance(wd)
                wepp = Wepp.getInstance(wd)
                watershed = Watershed.getInstance(wd)
            except:
                raise Exception('Error acquiring nodb instances from ' + wd)

            name = ron.name
            scenario = ron.scenario

            ws.append(dict(runid=runid, cfg=ron.config_stem, name=name, scenario=scenario, location_hash=ron.location_hash))

        
        js = json.dumps(ws)

    except:
        return exception_factory('Error running script')

    wd = get_wd(runids[0]) 
    viz_export_dir = _join(wd, 'export/WEPPcloudR')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    try:
        assert routine.endswith('.R') or routine.endswith('.Rmd'), routine

        # routine_stem = '.'.join(routine.split('.')[:-1]) 
        r_format = routine.split('.')[-1] 
        rpt_fn = _join(viz_export_dir, f'{routine}.htm')

        rscript = _weppcloudr_script_locator(routine, user=user)
        assert _exists(rscript)

        if r_format.lower() == 'r':
            cmd = ['Rscript', rscript, runid]
        elif r_format.lower() == "rmd":
            cmd = ['R', '-e', f'''library("rmarkdown"); rmarkdown::render("{rscript}", params=list(ws='{js}'), output_file="{rpt_fn}", output_dir="{viz_export_dir}")''']

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
        with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
            fp.write(output.decode('utf-8'))
        with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
            fp.write(errors.decode('utf-8'))

        assert _exists(rpt_fn)
        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except:
        return exception_factory('Error processing request')
    
#  R -e 'library("rmarkdown"); rmarkdown::render("03_Rmarkdown_to_generate_reports.Rmd", params=list(proj_runid="lt_202012_26_Bliss_Creek_CurCond"), output_file="rmd_rpt.htm")'
