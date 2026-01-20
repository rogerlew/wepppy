"""Routes for user blueprint extracted from app.py."""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import wepppy
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


def _runs_query_for_user(user_id: Optional[int]):
    from wepppy.weppcloud.app import Run, runs_users
    query = Run.query
    if user_id is not None:
        query = query.join(runs_users).filter(runs_users.c.user_id == user_id)
    return query


def _owner_email_map(runs: List[Any]) -> Dict[str, str]:
    from wepppy.weppcloud.app import User
    owner_ids = {str(run.owner_id) for run in runs if run.owner_id}
    if not owner_ids:
        return {}
    owner_ints: List[int] = []
    for raw in owner_ids:
        try:
            owner_ints.append(int(raw))
        except (TypeError, ValueError):
            continue
    if not owner_ints:
        return {}
    owners = User.query.filter(User.id.in_(owner_ints)).all()
    return {str(owner.id): owner.email for owner in owners}


def _run_row_from_run(run: Any, owner_email: Optional[str]) -> Dict[str, Any]:
    runid = run.runid
    return {
        "wd": get_wd(runid),
        "owner": owner_email or "<anonymous>",
        "runid": runid,
        "date_created": run.date_created,
        "last_modified": run.last_modified,
        "owner_id": run.owner_id,
        "config": run.config,
    }


def _collect_run_rows(query) -> List[Dict[str, Any]]:
    from wepppy.weppcloud.app import db
    try:
        runs = query.all()
        owner_emails = _owner_email_map(runs)
        rows = [
            _run_row_from_run(run, owner_emails.get(str(run.owner_id)))
            for run in runs
        ]
    finally:
        db.session.remove()
    return rows


def _paginate_run_rows(query, page: int, per_page: int):
    from wepppy.weppcloud.app import db
    try:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        runs = list(pagination.items)
        owner_emails = _owner_email_map(runs)
        rows = [
            _run_row_from_run(run, owner_emails.get(str(run.owner_id)))
            for run in runs
        ]
    finally:
        db.session.remove()
    return rows, pagination


def _run_meta_inputs(run: Any) -> tuple[str, Dict[str, Any]]:
    if isinstance(run, dict):
        runid = run.get("runid")
        wd = run.get("wd") or (get_wd(runid) if runid else None)
        attrs = {
            "owner": run.get("owner") or "<anonymous>",
            "runid": runid,
            "date_created": run.get("date_created"),
            "last_modified": run.get("last_modified"),
            "owner_id": run.get("owner_id"),
            "config": run.get("config"),
        }
        return wd, attrs

    owner = getattr(run, "owner", None)
    if not owner:
        owner = getattr(run, "owner_email", None) or "<anonymous>"
    wd = getattr(run, "wd", None) or get_wd(run.runid)
    attrs = {
        "owner": owner,
        "runid": run.runid,
        "date_created": run.date_created,
        "last_modified": run.last_modified,
        "owner_id": run.owner_id,
        "config": run.config,
    }
    return wd, attrs


def _run_map_inputs(run: Any) -> tuple[str, Dict[str, Any]]:
    if isinstance(run, dict):
        runid = run.get("runid")
        wd = run.get("wd") or (get_wd(runid) if runid else None)
        attrs = {
            "runid": runid,
            "config": run.get("config"),
        }
        return wd, attrs

    wd = getattr(run, "wd", None) or get_wd(run.runid)
    attrs = {
        "runid": run.runid,
        "config": run.config,
    }
    return wd, attrs


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
                *_run_meta_inputs(run),
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


def _sort_metas(metas: List[dict], field: str, is_desc: bool) -> List[dict]:
    """Sort metadata dictionaries while keeping None values at the end."""
    if not metas:
        return []

    def _sort_value(meta: dict):
        value = meta.get(field)
        if isinstance(value, str):
            return value.casefold()
        return value

    non_null = [meta for meta in metas if meta.get(field) is not None]
    nulls = [meta for meta in metas if meta.get(field) is None]
    non_null.sort(key=_sort_value, reverse=is_desc)
    return [*non_null, *nulls]


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
            ron = Ron.load_detached(wd)
        except:
            return None

        meta = dict(name=ron.name,
                    scenario=ron.scenario,
                    readonly=ron.readonly)
        meta.update(attrs)

        return meta


def _build_map_meta(wd, attrs: dict):
        try:
            ron = Ron.load_detached(wd)
        except:
            return None

        map_center = None
        map_zoom = None
        if ron.map is not None:
            map_center = ron.map.center
            map_zoom = ron.map.zoom

        meta = dict(
            runid=attrs.get("runid"),
            config=attrs.get("config"),
            name=ron.name,
            scenario=ron.scenario,
            readonly=ron.readonly,
            map_center=map_center,
            map_zoom=map_zoom,
        )
        return meta


def _collect_map_metas_for_runs(runs) -> List[dict]:
    """Build map metadata payloads for the provided runs in parallel."""
    if not runs:
        return []

    metas: List[Optional[dict]] = [None] * len(runs)
    max_workers = max(min(10, len(runs)), 1)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _build_map_meta,
                *_run_map_inputs(run),
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


@user_bp.route("/runs", strict_slashes=False)
@login_required
def runs():
    try:
        from wepppy.weppcloud.app import Run
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        if per_page <= 0:
            per_page = 25

        sort_param = _normalize_sort_param(request.args.get('sort'))
        direction_param = _normalize_direction(request.args.get('direction') or request.args.get('order'))
        is_desc = direction_param == 'desc'

        format_param = (request.args.get('format') or request.args.get('fomat') or '').lower()
        if format_param == 'json':
            base_query = _runs_query_for_user(current_user.id).order_by(
                Run.last_modified.desc().nullslast(),
                Run.id.desc(),
            )

            pagination = None
            metas = []

            if sort_param in DB_SORT_FIELDS:
                column = getattr(Run, sort_param)
                query = base_query.order_by(None)

                if sort_param in {'last_modified', 'date_created'}:
                    order_expr = column.desc().nullslast() if is_desc else column.asc().nullslast()
                else:
                    order_expr = column.desc() if is_desc else column.asc()

                secondary_expr = Run.id.desc() if is_desc else Run.id.asc()
                query = query.order_by(order_expr, secondary_expr)
                run_rows, pagination = _paginate_run_rows(query, page, per_page)
                metas = _collect_metas_for_runs(run_rows)
            else:
                run_rows = _collect_run_rows(base_query)
                metas_all = _collect_metas_for_runs(run_rows)
                metas_all = _sort_metas(metas_all, sort_param, is_desc)
                metas, pagination = _slice_for_page(metas_all, page, per_page)

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
            user_runs=[],
            pagination=None,
            show_owner=False,
            sort=sort_param,
            direction=direction_param,
            per_page=per_page,
        )
    except:
        return exception_factory()


@user_bp.route("/runs/catalog", strict_slashes=False)
@login_required
def runs_catalog():
    try:
        sort_param = _normalize_sort_param(request.args.get('sort'))
        direction_param = _normalize_direction(request.args.get('direction') or request.args.get('order'))
        is_desc = direction_param == 'desc'

        scope = (request.args.get('scope') or '').lower()
        if scope == 'all' and (current_user.has_role('Admin') or current_user.has_role('Root')):
            runs_all = _collect_run_rows(_runs_query_for_user(None))
        else:
            runs_all = _collect_run_rows(_runs_query_for_user(current_user.id))

        metas = _collect_metas_for_runs(runs_all)
        metas = _sort_metas(metas, sort_param, is_desc)
        return jsonify(
            runs=metas,
            sort=sort_param,
            direction=direction_param,
            total=len(metas),
        )
    except:
        return exception_factory()

@user_bp.route("/runs/map-data", strict_slashes=False)
@login_required
def runs_map_data():
    try:
        from wepppy.weppcloud.app import Run
        scope = (request.args.get('scope') or '').lower()
        if scope == 'all' and (current_user.has_role('Admin') or current_user.has_role('Root')):
            query = _runs_query_for_user(None).order_by(
                Run.last_modified.desc().nullslast(),
                Run.id.desc(),
            )
        else:
            query = _runs_query_for_user(current_user.id).order_by(
                Run.last_modified.desc().nullslast(),
                Run.id.desc(),
            )
        run_rows = _collect_run_rows(query)
        metas = _collect_map_metas_for_runs(run_rows)
        return jsonify(runs=metas)
    except:
        return exception_factory()
