"""Routes related to archived run artifacts."""
# see docs/ui-docs/weppcloud-project-archiving.md for archive architecture

import os
import zipfile
from datetime import datetime
from glob import glob

import redis

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from flask_security import current_user
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.weppcloud.utils.helpers import authorize, exception_factory, url_for_run

from .._run_context import load_run_context


archive_bp = Blueprint('archive', __name__, template_folder='templates')


_RUNNING_ARCHIVE_JOB_STATUSES = {'queued', 'started', 'deferred', 'scheduled'}


def _resolve_archive_job_state(prep: RedisPrep) -> tuple[bool, str | None]:
    archive_job_id = prep.get_archive_job_id()
    if not archive_job_id:
        return False, None

    status = None
    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            job = Job.fetch(archive_job_id, connection=redis_conn)
            status = job.get_status(refresh=True)
    except NoSuchJobError:
        status = None
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py:43", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return True, archive_job_id

    if status in _RUNNING_ARCHIVE_JOB_STATUSES:
        return True, archive_job_id

    prep.clear_archive_job_id()
    return False, None


@archive_bp.route('/runs/<string:runid>/<string:config>/rq-archive-dashboard', strict_slashes=False)
@login_required
def rq_archive_dashboard(runid, config):
    try:
        authorize(runid, config)
        load_run_context(runid, config)
        return render_template('rq-archive-dashboard.htm', runid=runid, config=config, user=current_user)
    except Exception as e:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py:60", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(e)


@archive_bp.route('/runs/<string:runid>/<string:config>/rq-archive-dashboard/archives', strict_slashes=False)
@login_required
def rq_archive_list(runid, config):
    authorize(runid, config)
    try:
        ctx = load_run_context(runid, config)
        wd = str(ctx.active_root)
        archives_dir = os.path.join(wd, 'archives')
        os.makedirs(archives_dir, exist_ok=True)

        entries = []
        pattern = os.path.join(archives_dir, '*.zip')
        for path in sorted(glob(pattern), reverse=True):
            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue

            rel_name = os.path.basename(path)
            comment = ''
            try:
                with zipfile.ZipFile(path) as zf:
                    raw_comment = zf.comment or b''
                    comment = raw_comment.decode('utf-8', errors='replace').strip()
            except (zipfile.BadZipFile, OSError):
                comment = ''

            modified_str = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            entries.append({
                'name': rel_name,
                'comment': comment,
                'size': stat.st_size,
                'modified': modified_str,
                'download_url': url_for_run(
                    'download.download_with_subpath',
                    runid=runid,
                    config=config,
                    subpath=f'archives/{rel_name}',
                )
            })

        prep = RedisPrep.getInstance(wd)
        in_progress, archive_job_id = _resolve_archive_job_state(prep)

        return jsonify({
            'archives': entries,
            'in_progress': in_progress,
            'job_id': archive_job_id,
        })
    except Exception as e:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py:113", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(e)
