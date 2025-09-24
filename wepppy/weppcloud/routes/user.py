"""Routes for user blueprint extracted from app.py."""

from pathlib import Path
import wepppy
from datetime import datetime
from ._common import *  # noqa: F401,F403

from wepppy.nodb import (
    Ash,
    Disturbed,
    Landuse,
    Observed,
    RangelandCover,
    Rhem,
    Ron,
    Soils,
    Topaz,
    Treatments,
    Unitizer,
    Watershed,
    Wepp,
)
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.climate import Climate

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED


user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', strict_slashes=False)
@login_required
def profile():
    try:
        return render_template('user/profile.html', user=current_user)
    except:
        return exception_factory()

def _build_meta(wd, attrs: dict):
        try:
            ron = Ron.getInstance(wd)
        except:
            return None

        meta = dict(name=ron.name,
                    scenario=ron.scenario,
                    w3w=ron.w3w,
                    readonly=ron.readonly)
        meta.update(attrs)

        return meta


@user_bp.route("/runs", strict_slashes=False)
@login_required
def runs():
    try:
        from wepppy.weppcloud.app import runs_users, Run
        page     = request.args.get('page', 1, type=int)
        per_page = 100

        # Query & order by the DB column:
        pagination = (
            Run.query
            .join(runs_users)                  # make sure to filter by current_user
            .filter(runs_users.c.user_id == current_user.id)
            .order_by(Run.last_modified.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        # Only build RON-meta for this page’s runs:
        items   = pagination.items     # list of Run objects
        metas   = []

        max_workers = max(min(10, len(items)), 1)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(_build_meta, r.wd, {
                    "owner":        r.owner,
                    "runid":        r.runid,
                    "date_created": r.date_created,
                    "last_modified":r.last_modified,
                    "owner_id":     r.owner_id,
                    "config":       r.config,
                })
                for r in items
            ]

            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=10, return_when=FIRST_COMPLETED)

                if not done:
                    # If this fires frequently we may need to tune the 10s threshold; keep an eye on I/O latency in prod.
                    current_app.logger.warning('runs() metadata build still pending after 10 seconds; continuing to wait.')
                    continue

                for future in done:
                    try:
                        m = future.result()
                    except Exception:
                        for remaining in pending:
                            remaining.cancel()
                        raise

                    if m:
                        metas.append(m)

        # metas roughly in DB order already
        return render_template(
            "user/runs2.html",
            user=current_user,
            user_runs=metas,
            pagination=pagination,
            show_owner=False,
        )
    except:
        return exception_factory()

