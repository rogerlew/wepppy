"""Routes for user blueprint extracted from app.py."""

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.routing import BuildError

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
from wepppy.weppcloud.utils import auth_tokens

from concurrent.futures import ThreadPoolExecutor, as_completed


user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)

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

PROFILE_TOKEN_TTL_SECONDS = 90 * 24 * 60 * 60
PROFILE_TOKEN_SCOPES = (
    'runs:read',
    'queries:validate',
    'queries:execute',
    'rq:status',
    'rq:enqueue',
    'rq:export',
)
PROFILE_TOKEN_AUDIENCES = ('rq-engine', 'query-engine')
PROFILE_USER_TOKEN_MINT_ALLOWED_ROLES = ('Admin', 'PowerUser', 'Dev', 'Root')
PROFILE_USER_TOKEN_MINT_ALLOWED_ROLE_SET = frozenset(
    role.casefold() for role in PROFILE_USER_TOKEN_MINT_ALLOWED_ROLES
)


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


def _claim_names(raw_values: Any) -> List[str]:
    if raw_values is None:
        return []
    if hasattr(raw_values, 'all') and callable(raw_values.all):
        try:
            raw_values = raw_values.all()
        except SQLAlchemyError:
            logger.warning(
                "user._claim_names: failed to evaluate dynamic relationship via .all(); defaulting to empty list",
                exc_info=True,
            )
            raw_values = []

    names: List[str] = []
    for value in raw_values:
        candidate = getattr(value, 'name', value)
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            names.append(text)
    return sorted(set(names), key=str.casefold)


def _current_user_groups() -> List[str]:
    groups = getattr(current_user, 'groups', None)
    return _claim_names(groups)


def _current_user_roles() -> List[str]:
    roles = getattr(current_user, 'roles', None)
    return _claim_names(roles)


def _can_mint_profile_user_token(role_names: Optional[List[str]] = None) -> bool:
    if role_names is None:
        role_names = _current_user_roles()
    return any(
        role.casefold() in PROFILE_USER_TOKEN_MINT_ALLOWED_ROLE_SET
        for role in role_names
    )


def _is_admin_runs_viewer() -> bool:
    return bool(current_user.has_role('Admin') or current_user.has_role('Root'))


def _normalize_alias(raw_alias: Optional[str]) -> Optional[str]:
    if raw_alias is None:
        return None
    alias = str(raw_alias).strip()
    return alias or None


def _resolve_runs_user_id(raw_alias: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    viewer_user_id = getattr(current_user, 'id', None)
    alias = _normalize_alias(raw_alias)
    if not _is_admin_runs_viewer() or alias is None:
        return viewer_user_id, None

    from sqlalchemy import func
    from wepppy.weppcloud.app import User

    user = None
    if alias.isdigit():
        user = User.query.filter(User.id == int(alias)).first()

    if user is None:
        user = User.query.filter(func.lower(User.email) == alias.lower()).first()

    if user is None:
        return None, alias

    return user.id, None


@user_bp.route('/profile', strict_slashes=False)
@login_required
def profile():
    try:
        role_names = _current_user_roles()
        try:
            reset_browser_state_endpoint = url_for('weppcloud_site.reset_browser_state')
        except BuildError:
            reset_browser_state_endpoint = None

        try:
            login_url = url_for('security.login')
        except BuildError:
            login_url = '/login'

        return render_template(
            'user/profile.html',
            user=current_user,
            can_mint_profile_token=_can_mint_profile_user_token(role_names),
            reset_browser_state_endpoint=reset_browser_state_endpoint,
            reset_browser_state_login_url=login_url,
        )
    except Exception:
        return exception_factory()


@user_bp.route('/profile/mint-token', methods=['POST'])
@login_required
def mint_profile_token():
    try:
        user_id = getattr(current_user, 'id', None)
        if user_id is None:
            return error_factory('Current user is missing an id.', status_code=400)

        email = str(getattr(current_user, 'email', '') or '').strip()
        if not email:
            return error_factory('Current user is missing an email address.', status_code=400)

        role_names = _current_user_roles()
        if not _can_mint_profile_user_token(role_names):
            allowed_roles = ', '.join(PROFILE_USER_TOKEN_MINT_ALLOWED_ROLES)
            return error_factory(
                f'Minting user tokens requires one of these roles: {allowed_roles}.',
                status_code=403,
            )
        group_names = _current_user_groups()
        result = auth_tokens.issue_token(
            str(user_id),
            scopes=PROFILE_TOKEN_SCOPES,
            audience=PROFILE_TOKEN_AUDIENCES,
            expires_in=PROFILE_TOKEN_TTL_SECONDS,
            extra_claims={
                'token_class': 'user',
                'email': email,
                'roles': role_names,
                'groups': group_names,
            },
        )
        claims = result.get('claims', {})
        response = success_factory(
            {
                'token': result.get('token'),
                'token_class': 'user',
                'audience': claims.get('aud'),
                'scopes': list(PROFILE_TOKEN_SCOPES),
                'expires_at': claims.get('exp'),
                'issued_at': claims.get('iat'),
                'expires_in': PROFILE_TOKEN_TTL_SECONDS,
            }
        )
        response.headers['Cache-Control'] = 'no-store'
        return response
    except Exception as exc:
        return error_factory(str(exc), status_code=500)


@user_bp.route("/runs/users", strict_slashes=False)
@login_required
@roles_accepted('Admin', 'Root')
def runs_users():
    from sqlalchemy import func
    from wepppy.weppcloud.app import User, db

    try:
        records: List[Dict[str, Any]] = []
        users = User.query.order_by(func.lower(User.email).asc(), User.id.asc()).all()
        for user in users:
            email = (getattr(user, 'email', None) or '').strip()
            first = (getattr(user, 'first_name', None) or '').strip()
            last = (getattr(user, 'last_name', None) or '').strip()
            name = ' '.join(part for part in (first, last) if part).strip()
            display_name = name or email or f'User {user.id}'
            if email and name:
                label = f'{name} <{email}>'
            elif email:
                label = email
            else:
                label = display_name

            records.append(
                {
                    "alias": str(user.id),
                    "id": user.id,
                    "email": email,
                    "name": name,
                    "display_name": display_name,
                    "label": label,
                    "search_index": f'{name} {email}'.strip().lower(),
                }
            )

        return jsonify(users=records, total=len(records))
    except Exception:
        return exception_factory()
    finally:
        db.session.remove()


def _build_meta(wd, attrs: dict):
    try:
        ron = Ron.load_detached(wd)
    except FileNotFoundError:
        # Boundary: keep list endpoints stable when runs are partially created.
        logger.info(
            "user._build_meta: ron.nodb missing for runid=%s config=%s wd=%s; skipping run",
            attrs.get("runid"),
            attrs.get("config"),
            wd,
        )
        return None
    except Exception:
        # Boundary: never 500 runs list endpoints for per-run load failures.
        logger.warning(
            "user._build_meta: failed to load Ron for runid=%s config=%s wd=%s; skipping run",
            attrs.get("runid"),
            attrs.get("config"),
            wd,
            exc_info=True,
        )
        return None

    meta = dict(
        name=ron.name,
        scenario=ron.scenario,
        readonly=ron.readonly,
    )
    meta.update(attrs)

    return meta


def _build_map_meta(wd, attrs: dict):
    try:
        ron = Ron.load_detached(wd)
    except FileNotFoundError:
        # Boundary: keep list endpoints stable when runs are partially created.
        logger.info(
            "user._build_map_meta: ron.nodb missing for runid=%s config=%s wd=%s; skipping run",
            attrs.get("runid"),
            attrs.get("config"),
            wd,
        )
        return None
    except Exception:
        # Boundary: never 500 runs list endpoints for per-run load failures.
        logger.warning(
            "user._build_map_meta: failed to load Ron for runid=%s config=%s wd=%s; skipping run",
            attrs.get("runid"),
            attrs.get("config"),
            wd,
            exc_info=True,
        )
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
        requested_alias = request.args.get('alias')
        selected_user_id, missing_alias = _resolve_runs_user_id(requested_alias)
        if missing_alias is not None and _is_admin_runs_viewer():
            return error_factory(f"user alias '{missing_alias}' not found", status_code=404)

        format_param = (request.args.get('format') or request.args.get('fomat') or '').lower()
        if format_param == 'json':
            base_query = _runs_query_for_user(selected_user_id).order_by(
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
            is_admin_runs_viewer=_is_admin_runs_viewer(),
            selected_alias=_normalize_alias(requested_alias),
            current_user_alias=str(getattr(current_user, 'id', '')) if getattr(current_user, 'id', None) is not None else '',
        )
    except Exception:
        return exception_factory()


@user_bp.route("/runs/catalog", strict_slashes=False)
@login_required
def runs_catalog():
    try:
        sort_param = _normalize_sort_param(request.args.get('sort'))
        direction_param = _normalize_direction(request.args.get('direction') or request.args.get('order'))
        is_desc = direction_param == 'desc'
        requested_alias = request.args.get('alias')
        selected_user_id, missing_alias = _resolve_runs_user_id(requested_alias)
        if missing_alias is not None and _is_admin_runs_viewer():
            return error_factory(f"user alias '{missing_alias}' not found", status_code=404)
        runs_all = _collect_run_rows(_runs_query_for_user(selected_user_id))

        metas = _collect_metas_for_runs(runs_all)
        metas = _sort_metas(metas, sort_param, is_desc)
        return jsonify(
            runs=metas,
            sort=sort_param,
            direction=direction_param,
            total=len(metas),
        )
    except Exception:
        return exception_factory()

@user_bp.route("/runs/map-data", strict_slashes=False)
@login_required
def runs_map_data():
    try:
        from wepppy.weppcloud.app import Run
        requested_alias = request.args.get('alias')
        selected_user_id, missing_alias = _resolve_runs_user_id(requested_alias)
        if missing_alias is not None and _is_admin_runs_viewer():
            return error_factory(f"user alias '{missing_alias}' not found", status_code=404)
        query = _runs_query_for_user(selected_user_id).order_by(
            Run.last_modified.desc().nullslast(),
            Run.id.desc(),
        )
        run_rows = _collect_run_rows(query)
        metas = _collect_map_metas_for_runs(run_rows)
        return jsonify(runs=metas)
    except Exception:
        return exception_factory()
