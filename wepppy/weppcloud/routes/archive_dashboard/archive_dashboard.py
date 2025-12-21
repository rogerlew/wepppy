"""Routes related to archived run artifacts."""
# see docs/ui-docs/weppcloud-project-archiving.md for archive architecture

import os
import zipfile
from datetime import datetime
from glob import glob

from flask import Blueprint, jsonify, render_template
from flask_security import current_user

from wepppy.nodb.redis_prep import RedisPrep
from wepppy.weppcloud.utils.helpers import authorize, exception_factory, url_for_run

from .._run_context import load_run_context


archive_bp = Blueprint('archive', __name__, template_folder='templates')


@archive_bp.route('/runs/<string:runid>/<string:config>/rq-archive-dashboard', strict_slashes=False)
def rq_archive_dashboard(runid, config):
    try:
        authorize(runid, config)
        load_run_context(runid, config)
        return render_template('rq-archive-dashboard.htm', runid=runid, config=config, user=current_user)
    except Exception as e:
        return exception_factory(e)


@archive_bp.route('/runs/<string:runid>/<string:config>/rq-archive-dashboard/archives', strict_slashes=False)
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
        archive_job_id = prep.get_archive_job_id()

        return jsonify({
            'archives': entries,
            'in_progress': archive_job_id is not None,
            'job_id': archive_job_id,
        })
    except Exception as e:
        return exception_factory(e)
