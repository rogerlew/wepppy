import os
import json
import io
from contextlib import ExitStack
from functools import wraps

import pathlib
import signal
import time
import stat
from pathlib import Path
from subprocess import PIPE, Popen, TimeoutExpired
from urllib.parse import quote

from typing import Optional

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from os.path import abspath, basename

import redis

from flask import Response, abort, Blueprint, current_app, has_app_context, request, render_template, url_for
from flask_security import current_user
from werkzeug.exceptions import HTTPException

from rq import Queue, Retry
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.weppcloudr_rq import render_deval_details_rq
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.submission_recovery import (
    RqSubmissionConflict,
    checkpoint_run_lifecycle,
    prepare_redisprep_job_id,
    rq_submission_lock,
)
from wepppy.rq.weppcloudr_backends import RenderRequest, validate_request

from wepppy.weppcloud.utils.helpers import (
    authorize,
    authorize_and_handle_with_exception_factory,
    exception_factory,
    get_wd,
    run_lifecycle_mutation,
    url_for_run,
)
from wepppy.weppcloud.utils.cap_guard import requires_cap

from wepppy.nodb.core import Ron, Wepp, Watershed
from wepppy.query_engine.activate import activate_query_engine

from ._run_context import RunContext, load_run_context

VIZ_RSCRIPT_DIR = '/workdir/viz-weppcloud/scripts/R/'
VIZ_RMARKDOWN_DIR = '/workdir/viz-weppcloud/scripts/Rmd'
WEPPCLOUDR_DIR = '/workdir/WEPPcloudR/scripts'
R_PROXY_RMD_RENDER_EXPR = (
    'args <- commandArgs(TRUE); '
    'if (length(args) != 4) stop("expected 4 args"); '
    'input_file <- args[1]; '
    'ws_json <- args[2]; '
    'output_file <- args[3]; '
    'output_dir <- args[4]; '
    'ws <- jsonlite::fromJSON(ws_json, simplifyVector = FALSE); '
    'rmarkdown::render(input_file, params=list(ws=ws), output_file=output_file, output_dir=output_dir)'
)
VIZ_RMD_RENDER_EXPR = (
    'args <- commandArgs(TRUE); '
    'if (length(args) != 4) stop("expected 4 args"); '
    'rmarkdown::render(args[1], params=list(proj_runid=args[2]), '
    'output_file=args[3], output_dir=args[4])'
)


def _viz_rmd_command(rscript: str, runid: str, routine: str, output_dir: str) -> list[str]:
    return [
        'R',
        '-e',
        f'library("rmarkdown"); {VIZ_RMD_RENDER_EXPR}',
        '--args',
        rscript,
        runid,
        f'{routine}.htm',
        output_dir,
    ]


weppcloudr_bp = Blueprint('weppcloud', __name__)


def _fence_public_run_mutation(func):
    @wraps(func)
    def wrapper(runid, config, *args, **kwargs):
        authorize(runid, config)
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            try:
                with rq_submission_lock(
                    redis_conn,
                    f"{runid}:weppcloudr-render:request",
                    lifecycle_key=runid,
                ):
                    return func(runid, config, *args, **kwargs)
            except RqSubmissionConflict as exc:
                return exception_factory(str(exc), runid=runid, status_code=409)
    return wrapper


def _run_render_process(cmd, runids):
    process = Popen(cmd, stdout=PIPE, stderr=PIPE, start_new_session=True)
    max_runtime = int(
        current_app.config.get("WEPPCLOUDR_INTERACTIVE_MAX_RUNTIME", 600)
        if has_app_context()
        else 600
    )
    deadline = time.monotonic() + max(1, max_runtime)
    while True:
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutExpired(cmd, max_runtime)
            output, errors = process.communicate(timeout=min(10, remaining))
            break
        except TimeoutExpired:
            if time.monotonic() >= deadline:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.communicate(timeout=5)
                except TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                raise RuntimeError("Interactive render exceeded its time limit")
            try:
                for runid in runids:
                    checkpoint_run_lifecycle(runid)
            except RqSubmissionConflict:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.communicate(timeout=5)
                except TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                raise
    for runid in runids:
        checkpoint_run_lifecycle(runid)
    return output, errors

@weppcloudr_bp.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>/')
@_fence_public_run_mutation
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
            cmd = _viz_rmd_command(rscript, runid, routine, viz_export_dir)

        output, errors = _run_render_process(cmd, (runid,))
        with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
            fp.write(output.decode('utf-8'))
        with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
            fp.write(errors.decode('utf-8'))

        assert _exists(rpt_fn)
        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except Exception:  # broad-except: boundary contract
        current_app.logger.exception(
            "viz_r failed runid=%s config=%s r_format=%s routine=%s",
            runid,
            config,
            r_format,
            routine,
        )
        return exception_factory('Error running script', runid=runid)



def _normalize_user_segment(user: Optional[str]) -> Optional[str]:
    if user is None:
        return None
    user_str = str(user).strip()
    if not user_str or user_str in {'.', '..'}:
        raise ValueError("Invalid user path segment")
    if Path(user_str).name != user_str:
        raise ValueError("Invalid user path segment")
    if '/' in user_str or '\\' in user_str:
        raise ValueError("Invalid user path segment")
    return user_str


def _normalize_routine_name(routine: str) -> str:
    routine_str = str(routine).strip()
    if not routine_str:
        raise ValueError("Routine is required")
    if Path(routine_str).name != routine_str:
        raise ValueError("Invalid routine name")
    if '/' in routine_str or '\\' in routine_str:
        raise ValueError("Invalid routine name")
    return routine_str


def _weppcloudr_script_locator(routine, user=None):
    global WEPPCLOUDR_DIR
    base_dir = Path(WEPPCLOUDR_DIR).resolve()
    routine_name = _normalize_routine_name(routine)
    user_segment = _normalize_user_segment(user)
    if user_segment is None:
        candidate = base_dir / routine_name
    else:
        candidate = base_dir / 'users' / user_segment / routine_name
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        raise ValueError("Routine path escapes WEPPcloudR directory")
    return str(resolved)


def _parse_proxy_runids(values: list[str]) -> list[str]:
    runids: list[str] = []
    for value in values:
        for token in str(value).replace(',', ' ').split():
            runid = token.strip()
            if runid.endswith('/'):
                runid = runid[:-1]
            if runid:
                runids.append(runid)
    if not runids:
        raise ValueError("runids query parameter is required and must be non-empty")
    return runids


@weppcloudr_bp.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>/')
@_fence_public_run_mutation
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
        routine = _normalize_routine_name(routine)
        assert routine.endswith('.R') or routine.endswith('.Rmd'), routine

        r_format = routine.split('.')[-1] 
        rpt_fn = _join(viz_export_dir, f'{routine}.{sub_sha}.htm')

        if not _exists(rpt_fn):
            rscript = _weppcloudr_script_locator(routine, user=user)
            assert _exists(rscript)

            if r_format.lower() == 'r':
                cmd = ['Rscript', rscript, runid]
            elif r_format.lower() == "rmd":
                cmd = [
                    'R',
                    '-e',
                    (
                        'library("rmarkdown"); '
                        'rmarkdown::render('
                        'commandArgs(TRUE)[1], '
                        'params=list(proj_runid=commandArgs(TRUE)[2]), '
                        'output_file=commandArgs(TRUE)[3], '
                        'output_dir=commandArgs(TRUE)[4]'
                        ')'
                    ),
                    '--args',
                    rscript,
                    runid,
                    rpt_fn,
                    viz_export_dir,
                ]

            output, errors = _run_render_process(cmd, (runid,))
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

    except Exception:  # broad-except: boundary contract
        current_app.logger.exception(
            "weppcloudr_runner failed runid=%s config=%s routine=%s user=%s",
            runid,
            config,
            routine,
            user,
        )
        return exception_factory('Error running script')


def _ensure_interchange(ctx: RunContext, runid: str) -> None:
    wd = str(ctx.active_root)
    try:
        activate_query_engine(
            wd,
            run_interchange=True,
            mutation_checkpoint=lambda: checkpoint_run_lifecycle(runid),
        )
    except Exception:  # broad-except: boundary contract
        current_app.logger.exception("Interchange activation failed for %s", wd)
        raise


ACTIVE_JOB_STATUSES = {'queued', 'started', 'scheduled'}


def _deval_output_path(ctx: RunContext, runid: str) -> Path:
    active_root = Path(ctx.active_root).resolve()
    export_parent = active_root / "export"
    export_root = export_parent / "WEPPcloudR"
    for component in (export_parent, export_root):
        if component.is_symlink():
            abort(404, description="DEVAL report path is invalid")
    try:
        export_root.resolve().relative_to(active_root)
    except ValueError:
        abort(404, description="DEVAL report path is invalid")
    output_path = export_root / f"deval_{runid}.htm"
    if output_path.is_symlink():
        abort(404, description="DEVAL report path is invalid")
    return output_path


def _normalize_job_key_component(value: str) -> str:
    return quote(value, safe="")


def _deval_job_key(ctx: RunContext) -> str:
    parts = ['deval_details', _normalize_job_key_component(ctx.config)]
    if ctx.pup_relpath:
        parts.append(_normalize_job_key_component(ctx.pup_relpath))
    return ':'.join(parts)


def _resolve_prep(ctx: RunContext) -> Optional[RedisPrep]:
    return RedisPrep.tryGetInstance(str(ctx.run_root))


def _lookup_job_status(
    redis_conn: redis.Redis,
    job_id: str,
    runid: str,
    config: str,
    active_root: Path,
) -> str:
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return 'not_found'
    expected_func = (
        f"{render_deval_details_rq.__module__}."
        f"{render_deval_details_rq.__name__}"
    )
    args = tuple(job.args or ())
    backend = current_app.config.get(
        'WEPPCLOUDR_EXECUTION_BACKEND',
        os.getenv('WEPPCLOUDR_EXECUTION_BACKEND', 'docker-exec'),
    ) if has_app_context() else os.getenv('WEPPCLOUDR_EXECUTION_BACKEND', 'docker-exec')
    expected_origin = (
        (current_app.config.get('WEPPCLOUDR_K8S_QUEUE') if has_app_context() else None)
        or os.getenv('WEPPCLOUDR_K8S_QUEUE', 'weppcloudr')
        if backend == 'kubernetes-job'
        else 'default'
    )
    if (
        job.func_name != expected_func
        or str(getattr(job, 'origin', 'default')) != str(expected_origin)
        or len(args) < 3
        or args[:3] != (runid, config, str(active_root))
    ):
        return 'foreign'
    status = job.get_status()
    return status or 'unknown'


def _clear_tracked_job(prep: RedisPrep, job_key: str) -> None:
    try:
        prep.redis.hdel(prep.run_id, f"rq:{job_key}")
        prep.dump()
    except Exception:  # broad-except: boundary contract
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/weppcloudr.py:331", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
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
    if prep is None:
        raise RuntimeError("DEVAL submission receipt storage is unavailable")
    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)

    with redis.Redis(**conn_kwargs) as redis_conn, rq_submission_lock(
        redis_conn, f"{runid}:deval:request", lifecycle_key=runid
    ) as lease:
        existing_job_id: Optional[str] = None
        existing_status: Optional[str] = None

        if prep:
            existing_job_id = prep.get_rq_job_id(job_key)

        if existing_job_id:
            existing_status = _lookup_job_status(
                redis_conn,
                existing_job_id,
                runid,
                config,
                ctx.active_root,
            )
            if existing_status in ACTIVE_JOB_STATUSES:
                return existing_job_id, existing_status
        backend = current_app.config.get(
            'WEPPCLOUDR_EXECUTION_BACKEND',
            os.getenv('WEPPCLOUDR_EXECUTION_BACKEND', 'docker-exec'),
        )
        if backend not in {'docker-exec', 'kubernetes-job'}:
            raise RuntimeError(f"Unknown WEPPcloudR execution backend: {backend!r}")

        job_kwargs = {
            'skip_cache': bool(skip_cache),
            'run_root': str(ctx.run_root),
            'backend': backend,
        }

        container_name = current_app.config.get('WEPPCLOUDR_CONTAINER')
        if container_name:
            job_kwargs['container_name'] = container_name

        docker_timeout = current_app.config.get('WEPPCLOUDR_COMMAND_TIMEOUT')
        if docker_timeout:
            job_kwargs['timeout'] = docker_timeout

        if backend == 'kubernetes-job':
            k8s_options = {
                'control_plane_url': current_app.config.get(
                    'WEPPCLOUDR_K8S_CONTROL_PLANE_URL'
                ) or os.getenv('WEPPCLOUDR_K8S_CONTROL_PLANE_URL'),
                'control_plane_token_file': current_app.config.get(
                    'WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE'
                ) or os.getenv('WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE'),
                'control_plane_namespace': current_app.config.get(
                    'WEPPCLOUDR_K8S_NAMESPACE'
                ) or os.getenv('WEPPCLOUDR_K8S_NAMESPACE'),
                'renderer_image_digest': current_app.config.get('WEPPCLOUDR_K8S_IMAGE')
                or os.getenv('WEPPCLOUDR_K8S_IMAGE'),
                'deployment_revision': current_app.config.get(
                    'WEPPCLOUDR_DEPLOYMENT_REVISION'
                ) or os.getenv('WEPPCLOUDR_DEPLOYMENT_REVISION'),
            }
            job_kwargs.update(
                (key, value) for key, value in k8s_options.items() if value is not None
            )

        job_timeout = current_app.config.get('WEPPCLOUDR_JOB_TIMEOUT', current_app.config.get('WEPPCLOUDR_TIMEOUT', 3600))

        if backend == 'kubernetes-job':
            active_deadline = int(
                current_app.config.get('WEPPCLOUDR_K8S_ACTIVE_DEADLINE')
                or os.getenv('WEPPCLOUDR_K8S_ACTIVE_DEADLINE', '600')
            )
            terminal_budget = int(
                current_app.config.get('WEPPCLOUDR_K8S_TERMINAL_BUDGET')
                or os.getenv('WEPPCLOUDR_K8S_TERMINAL_BUDGET', '120')
            )
            if active_deadline <= 0 or terminal_budget <= 0:
                raise RuntimeError('WEPPcloudR Kubernetes timeouts must be positive')
            if int(job_timeout) < active_deadline + terminal_budget:
                raise RuntimeError(
                    'WEPPCLOUDR_JOB_TIMEOUT must be at least the Kubernetes active '
                    'deadline plus terminal budget'
                )
            job_kwargs['timeout'] = active_deadline + terminal_budget

        queue_name = current_app.config.get('WEPPCLOUDR_K8S_QUEUE') or os.getenv(
            'WEPPCLOUDR_K8S_QUEUE', 'weppcloudr'
        )
        queue = (
            Queue(name=queue_name, connection=redis_conn)
            if backend == 'kubernetes-job'
            else Queue(connection=redis_conn)
        )
        job_id = new_rq_job_id()
        enqueue_options = {'job_id': job_id}
        if backend == 'kubernetes-job':
            request_snapshot = RenderRequest(
                schema_version=1,
                rq_job_id=job_id,
                runid=runid,
                config=config,
                run_root=str(ctx.run_root),
                active_root=str(ctx.active_root),
                skip_cache=bool(skip_cache),
                correlation_id=job_id,
                deployment_revision=str(job_kwargs.get('deployment_revision') or ''),
                renderer_image_digest=str(job_kwargs.get('renderer_image_digest') or ''),
            )
            validate_request(request_snapshot)
            enqueue_options = {
                'job_id': job_id,
                'meta': {
                    'render_backend': 'kubernetes-job',
                    'render_request_digest': request_snapshot.digest,
                    'render_cleanup_state': 'not-created',
                    'cancel_requested': False,
                },
            }
        if prep:
            prepare_redisprep_job_id(
                prep,
                job_key=job_key,
                replacement_job_id=job_id,
                connection=redis_conn,
                runid=runid,
                expected_root_module=render_deval_details_rq.__module__,
                expected_root_func_name=(
                    f"{render_deval_details_rq.__module__}.{render_deval_details_rq.__qualname__}"
                ),
                allowed_origins=(str(queue.name),),
                association=lambda candidate: (
                    str(candidate.func_name)
                    == f"{render_deval_details_rq.__module__}.{render_deval_details_rq.__qualname__}"
                    and str(candidate.origin) == str(queue.name)
                    and tuple(candidate.args or ())
                    == (runid, config, str(ctx.active_root))
                ),
                lease_checkpoint=lease.checkpoint,
            )
        lease.checkpoint()
        job = queue.enqueue_call(
            func=render_deval_details_rq,
            args=(runid, config, str(ctx.active_root)),
            kwargs=job_kwargs,
            timeout=job_timeout,
            retry=(Retry(max=3, interval=[10, 30, 60]) if backend == 'kubernetes-job' else None),
            description=f"Render Deval-In-The-Details report for {runid}/{config}",
            **enqueue_options,
        )

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
            except Exception:  # broad-except: boundary contract
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/weppcloudr.py:413", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                job_id = None

        if job_id:
            job_status = _lookup_job_status(
                redis_conn,
                job_id,
                runid,
                config,
                ctx.active_root,
            )
            if job_status in {'foreign', 'not_found'}:
                job_id = None
                job_status = None
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

        return _enqueue_deval_job(ctx, runid, config, skip_cache=skip_cache)


def _serve_deval_file(path: Path, active_root: Path) -> Response:
    root_fd = os.open(active_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        export_fd = os.open(
            "export", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
        try:
            report_fd = os.open(
                "WEPPcloudR",
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=export_fd,
            )
            try:
                artifact_fd = os.open(
                    path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=report_fd
                )
                try:
                    if not stat.S_ISREG(os.fstat(artifact_fd).st_mode):
                        abort(404, description="DEVAL report artifact is not regular")
                    with os.fdopen(artifact_fd, "rb", closefd=False) as artifact:
                        content = artifact.read()
                finally:
                    os.close(artifact_fd)
            finally:
                os.close(report_fd)
        finally:
            os.close(export_fd)
    finally:
        os.close(root_fd)
    response = Response(content, mimetype='text/html')
    response.headers['Content-Length'] = str(len(content))
    response.headers.setdefault('Cache-Control', 'no-store, max-age=0, must-revalidate')
    response.headers.setdefault('Content-Disposition', f'inline; filename="{path.name}"')
    response.headers['X-Report-Cache'] = 'hit'
    return response


@weppcloudr_bp.route('/runs/<string:runid>/<config>/report/deval_details')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/report/deval_details/')
@requires_cap(gate_reason="Complete verification to view report details.")
@authorize_and_handle_with_exception_factory
@run_lifecycle_mutation
def deval_details(runid, config):
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    try:
        checkpoint_run_lifecycle(runid)
        _ensure_interchange(ctx, runid)
    except Exception:  # broad-except: boundary contract
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/weppcloudr.py:461", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error preparing interchange assets', runid=runid)

    skip_cache = 'no-cache' in request.args
    output_path = _deval_output_path(ctx, runid)

    job_id, job_status = _determine_job(ctx, runid, config, skip_cache=skip_cache)

    # Serve the cached file when no active job is running (unless skip-cache was requested).
    if not skip_cache and output_path.exists() and job_status not in ACTIVE_JOB_STATUSES:
        return _serve_deval_file(output_path, ctx.active_root)

    refresh_kwargs = {'runid': runid, 'config': config}
    if ctx.pup_relpath:
        refresh_kwargs['pup'] = ctx.pup_relpath

    refresh_url = url_for_run('weppcloud.deval_details', **refresh_kwargs)
    job_dashboard_url = url_for('rq_job_dashboard.job_dashboard_route', job_id=job_id) if job_id else None

    context = {
        'runid': runid,
        'config': config,
        'job_id': job_id,
        'job_status': job_status,
        'job_dashboard_url': job_dashboard_url,
        'refresh_url': refresh_url,
        'skip_cache': skip_cache,
    }

    html = render_template('reports/deval_loading.htm', **context)
    response = Response(html, status=202, mimetype='text/html')
    response.headers['Cache-Control'] = 'no-store, max-age=0, must-revalidate'
    return response


def _fence_proxy_run_mutations(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            runids = _parse_proxy_runids(request.args.getlist('runids'))
            for runid in runids:
                authorize(runid, '__weppcloudr_proxy__')
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn, ExitStack() as stack:
                for runid in sorted(runids):
                    stack.enter_context(
                        rq_submission_lock(
                            redis_conn,
                            f"{runid}:weppcloudr-proxy:request",
                            lifecycle_key=runid,
                        )
                    )
                return func(*args, **kwargs)
        except ValueError as exc:
            return exception_factory(str(exc), status_code=400)
        except RqSubmissionConflict as exc:
            return exception_factory(str(exc), status_code=409)

    return wrapper


@weppcloudr_bp.route('/WEPPcloudR/proxy/<routine>', methods=['GET', 'POST'])
@weppcloudr_bp.route('/WEPPcloudR/proxy/<routine>/', methods=['GET', 'POST'])
@_fence_proxy_run_mutations
def weppcloudr_proxy(routine):
    if not current_user.is_authenticated:
        abort(401, description="Authentication required")

    runids_raw = request.args.getlist('runids')
    try:
        runids = _parse_proxy_runids(runids_raw)
    except ValueError as exc:
        abort(400, description=str(exc))

    from wepppy.weppcloud.app import user_datastore
    if not current_user.roles:
        user_datastore.add_role_to_user(current_user.email, 'User')

    user = request.args.get('user', None)

    try:

        ws = []
        for runid in runids:
            wd = get_wd(runid)
            try:
                ron = Ron.getInstance(wd)
                wepp = Wepp.getInstance(wd)
                watershed = Watershed.getInstance(wd)
            except Exception as exc:  # broad-except: boundary contract
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/weppcloudr.py:521", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                raise RuntimeError(f"Error acquiring nodb instances from {wd}") from exc

            name = ron.name
            scenario = ron.scenario

            ws.append(dict(runid=runid, cfg=ron.config_stem, name=name, scenario=scenario, location_hash=ron.location_hash))

        
        js = json.dumps(ws)

    except HTTPException:
        raise
    except Exception:  # broad-except: boundary contract
        current_app.logger.exception(
            "weppcloudr_proxy setup failed routine=%s user=%s runids=%s",
            routine,
            user,
            runids,
        )
        return exception_factory('Error running script')

    wd = get_wd(runids[0]) 
    viz_export_dir = _join(wd, 'export/WEPPcloudR')
    for runid in runids:
        checkpoint_run_lifecycle(runid)
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
            cmd = [
                'R',
                '-e',
                R_PROXY_RMD_RENDER_EXPR,
                '--args',
                rscript,
                js,
                rpt_fn,
                viz_export_dir,
            ]

        output, errors = _run_render_process(cmd, runids)
        with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
            fp.write(output.decode('utf-8'))
        with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
            fp.write(errors.decode('utf-8'))

        assert _exists(rpt_fn)
        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except HTTPException:
        raise
    except Exception:  # broad-except: boundary contract
        current_app.logger.exception(
            "weppcloudr_proxy request failed routine=%s user=%s runids=%s",
            routine,
            user,
            runids,
        )
        return exception_factory('Error processing request')
    
#  R -e 'library("rmarkdown"); rmarkdown::render("03_Rmarkdown_to_generate_reports.Rmd", params=list(proj_runid="lt_202012_26_Bliss_Creek_CurCond"), output_file="rmd_rpt.htm")'
