"""Routes for user blueprint extracted from app.py."""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import wepppy
from datetime import datetime
from ._common import *  # noqa: F401,F403

from wepppy.nodb.core import *
from wepppy.nodb.mods.observed import Observed
from wepppy.nodb.mods.treatments import Treatments
from wepppy.nodb.unitizer import Unitizer

from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.mods.rhem import Rhem

from concurrent.futures import ThreadPoolExecutor, as_completed


user_bp = Blueprint('user', __name__)

DEFAULT_SORT_FIELD = 'last_modified'
DEFAULT_SORT_DIRECTION = 'desc'

SORT_ALIASES = {
    'project_name': 'name',
    'project': 'name',
    'projectname': 'name',
    'name': 'name',
    'scenario': 'scenario',
    'run_id': 'runid',
    'runid': 'runid',
    'config': 'config',
    'creation_date': 'date_created',
    'created': 'date_created',
    'datecreated': 'date_created',
    'date_created': 'date_created',
    'last_modified': 'last_modified',
    'modified': 'last_modified',
    'lastmodified': 'last_modified',
}

DB_SORT_FIELDS = {'runid', 'config', 'date_created', 'last_modified'}


class SimplePagination:
    """Small pagination helper mirroring Flask-SQLAlchemy's API surface."""

    __slots__ = ('page', 'per_page', 'total')

    def __init__(self, page: int, per_page: int, total: int):
        self.page = page
        self.per_page = per_page
        self.total = total

    @property
    def pages(self) -> int:
        if self.per_page <= 0:
            return 0
        return math.ceil(self.total / self.per_page) if self.total else 0

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        total_pages = self.pages
        return bool(total_pages and self.page < total_pages)

    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None


def _normalize_sort_param(raw_value: Optional[str]) -> str:
    if not raw_value:
        return DEFAULT_SORT_FIELD
    normalized = raw_value.strip().lower().replace(' ', '_').replace('-', '_')
    return SORT_ALIASES.get(normalized, DEFAULT_SORT_FIELD)


def _normalize_direction(raw_value: Optional[str]) -> str:
    if not raw_value:
        return DEFAULT_SORT_DIRECTION
    value = raw_value.strip().lower()
    return 'asc' if value == 'asc' else 'desc'


def _collect_metas_for_runs(runs) -> List[dict]:
    """Build metadata payloads for the provided runs in parallel."""
    if not runs:
        return []

    metas: List[Optional[dict]] = [None] * len(runs)
    max_workers = max(min(10, len(runs)), 1)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _build_meta,
                run.wd,
                {
                    "owner": run.owner,
                    "runid": run.runid,
                    "date_created": run.date_created,
                    "last_modified": run.last_modified,
                    "owner_id": run.owner_id,
                    "config": run.config,
                },
            ): idx
            for idx, run in enumerate(runs)
        }

        try:
            for future in as_completed(futures):
                idx = futures[future]
                meta = future.result()
                metas[idx] = meta
        except Exception:
            for future in futures:
                future.cancel()
            raise

    return [meta for meta in metas if meta]


def _meta_sort_key(field: str):
    """Generate a key function for sorting metadata dictionaries."""

    def _key(meta: dict):
        value = meta.get(field, "")
        if isinstance(value, str):
            return value.casefold()
        return value or ""

    return _key


def _slice_for_page(items: List[dict], page: int, per_page: int):
    total = len(items)
    if per_page <= 0:
        per_page = total or 1

    total_pages = math.ceil(total / per_page) if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    if page < 1:
        page = 1 if total_pages else 1

    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], SimplePagination(page, per_page, total)


def _pagination_payload(pagination) -> Dict[str, Any]:
    return {
        "page": getattr(pagination, "page", 1),
        "per_page": getattr(pagination, "per_page", 0),
        "total": getattr(pagination, "total", 0),
        "pages": getattr(pagination, "pages", 0),
        "has_prev": getattr(pagination, "has_prev", False),
        "has_next": getattr(pagination, "has_next", False),
        "prev_num": getattr(pagination, "prev_num", None),
        "next_num": getattr(pagination, "next_num", None),
    }

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
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        if per_page <= 0:
            per_page = 100

        sort_param = _normalize_sort_param(request.args.get('sort'))
        direction_param = _normalize_direction(request.args.get('direction') or request.args.get('order'))
        is_desc = direction_param == 'desc'

        base_query = (
            Run.query
            .join(runs_users)
            .filter(runs_users.c.user_id == current_user.id)
        )

        pagination = None
        metas = []

        if sort_param in DB_SORT_FIELDS:
            column = getattr(Run, sort_param)
            order_expr = column.desc() if is_desc else column.asc()
            secondary_expr = Run.id.desc() if is_desc else Run.id.asc()
            query = base_query.order_by(order_expr, secondary_expr)
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            metas = _collect_metas_for_runs(pagination.items)
        else:
            runs_all = base_query.all()
            metas_all = _collect_metas_for_runs(runs_all)
            metas_all.sort(key=_meta_sort_key(sort_param), reverse=is_desc)
            metas, pagination = _slice_for_page(metas_all, page, per_page)

        format_param = (request.args.get('format') or request.args.get('fomat') or '').lower()
        if format_param == 'json':
            return jsonify(
                metas=metas,
                pagination=_pagination_payload(pagination),
                sort=sort_param,
                direction=direction_param,
                per_page=per_page,
            )

        return render_template(
            "user/runs2.html",
            user=current_user,
            user_runs=metas,
            pagination=pagination,
            show_owner=False,
            sort=sort_param,
            direction=direction_param,
            per_page=per_page,
        )
    except:
        return exception_factory()
