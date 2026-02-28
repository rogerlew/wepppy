"""Routes for wepp blueprint extracted from app.py."""

import wepppy
import os
import pathlib
from collections import OrderedDict

from datetime import datetime
import uuid
from wepppy.weppcloud.utils.runid import generate_runid
import json
import traceback
from urllib.parse import unquote, urlsplit

import redis
from itsdangerous import BadSignature, Signer

from .._common import *  # noqa: F401,F403
from flask import current_app, session
from werkzeug.exceptions import HTTPException

import wepppy
from wepppy.all_your_base import isint
from wepppy.config.secrets import get_secret
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import get_configs
from wepppy.nodb.core import * 
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.mods.observed import Observed
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.mods.rhem import Rhem
from wepppy.nodb.mods.treatments import Treatments
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.debris_flow import DebrisFlow
from wepppy.nodb.mods.swat import Swat
from wepppy.nodb.mods.swat.print_prt import mask_to_tokens
from wepppy.nodb.mods.openet import OpenET_TS
from wepppy.nodb.mods.omni import Omni, OmniScenario
import wepppy.nodb.mods.omni as omni_mod
from wepppy.nodb.core.climate import Climate
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_relpath
from wepppy.weppcloud.routes.nodb_api.landuse_bp import build_landuse_report_context
from wepppy.weppcloud.utils.cap_guard import requires_cap
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import (
    get_wd, authorize, get_run_owners_lazy,
    is_omni_child_run,
    authorize_and_handle_with_exception_factory,
    handle_with_exception_factory
)
from wepppy.weppcloud.utils.browse_cookie import (
    browse_cookie_name,
    browse_cookie_path,
)


run_0_bp = Blueprint('run_0', __name__,
                     template_folder='templates')

SESSION_TOKEN_TTL_SECONDS = 4 * 24 * 60 * 60
SESSION_TOKEN_SCOPES = ["rq:status", "rq:enqueue", "rq:export"]
DEFAULT_BROWSE_JWT_COOKIE_NAME = "wepp_browse_jwt"
BROWSE_JWT_COOKIE_NAME_ENV = "WEPP_BROWSE_JWT_COOKIE_NAME"
DEFAULT_SITE_PREFIX = "/weppcloud"

VAPID_PUBLIC_KEY = ''
_VAPID_PATH = pathlib.Path('/workdir/weppcloud2/microservices/wepppush/vapid.json')
if _VAPID_PATH.exists():
    with _VAPID_PATH.open() as fp:
        vapid = json.load(fp)
        VAPID_PUBLIC_KEY = vapid.get('publicKey', '')

# Preflight TOC Emoji Mapping
# Maps TOC anchor hrefs to TaskEnum members for emoji display.
# TaskEnum.emoji() is the single source of truth for all task emojis.
# See docs/ui-docs/control-ui-styling/preflight_behavior.md for architecture.
TOC_TASK_ANCHOR_TO_TASK = {
    '#map': TaskEnum.fetch_dem,
    '#disturbed-sbs': TaskEnum.init_sbs_map,
    '#channel-delineation': TaskEnum.build_channels,
    '#set-outlet': TaskEnum.set_outlet,
    '#subcatchments-delineation': TaskEnum.build_subcatchments,
    '#rangeland-cover': TaskEnum.build_rangeland_cover,
    '#landuse': TaskEnum.build_landuse,
    '#climate': TaskEnum.build_climate,
    '#rap-ts': TaskEnum.fetch_rap_ts,
    '#openet-ts': TaskEnum.fetch_openet_ts,
    '#soils': TaskEnum.build_soils,
    '#treatments': TaskEnum.build_treatments,
    '#wepp': TaskEnum.run_wepp_watershed,
    '#ash': TaskEnum.run_watar,
    '#rhem': TaskEnum.run_rhem,
    '#omni-scenarios': TaskEnum.run_omni_scenarios,
    '#omni-contrasts': TaskEnum.run_omni_contrasts,
    '#observed': TaskEnum.run_observed,
    '#debris-flow': TaskEnum.run_debris,
    '#dss-export': TaskEnum.dss_export,
    '#path-cost-effective': TaskEnum.run_path_cost_effective,
    '#team': TaskEnum.project_init,  # Using project init emoji as placeholder
}

TOC_TASK_EMOJI_MAP = {anchor: task.emoji() for anchor, task in TOC_TASK_ANCHOR_TO_TASK.items()}


def _current_user_has_role(role: str) -> bool:
    has_role = getattr(current_user, "has_role", None)
    return bool(callable(has_role) and has_role(role))


def _openet_admin_enabled(*, playwright_load_all: bool) -> bool:
    return bool(playwright_load_all) or _current_user_has_role("Admin")

MOD_UI_DEFINITIONS = OrderedDict([
    ('rap_ts', {
        'label': 'RAP Time Series',
        'section_id': 'rap-ts',
        'section_class': 'wc-stack',
        'template': 'controls/rap_ts_pure.htm',
    }),
    ('openet_ts', {
        'label': 'OpenET Time Series',
        'section_id': 'openet-ts',
        'section_class': 'wc-stack',
        'template': 'controls/openet_ts_pure.htm',
    }),
    ('treatments', {
        'label': 'Treatments',
        'section_id': 'treatments',
        'section_class': 'wc-stack',
        'template': 'controls/treatments_pure.htm',
    }),
    ('ash', {
        'label': 'Ash Transport',
        'section_id': 'ash',
        'section_class': 'wc-stack',
        'template': 'controls/ash_pure.htm',
    }),
    ('omni', {
        'label': 'Omni Scenarios',
        'section_id': 'omni-wrapper',
        'section_class': 'wc-stack',
        'template': 'controls/omni_mod_pure.htm',
    }),
    ('observed', {
        'label': 'Observed Data',
        'section_id': 'observed',
        'section_class': 'wc-stack',
        'template': 'controls/observed_pure.htm',
    }),
    ('debris_flow', {
        'label': 'Debris Flow',
        'section_id': 'debris-flow',
        'section_class': 'wc-stack',
        'template': 'controls/debris_flow_pure.htm',
        'requires_power_user': True,
    }),
    ('dss_export', {
        'label': 'DSS Export',
        'section_id': 'dss-export',
        'section_class': 'wc-stack',
        'template': 'controls/dss_export_pure.htm',
    }),
    ('path_ce', {
        'label': 'PATH Cost-Effective',
        'section_id': 'path-cost-effective',
        'section_class': 'wc-stack',
        'template': 'controls/path_cost_effective_pure.htm',
    }),
])

@run_0_bp.route('/sw.js')
def service_worker():
    from flask import make_response, send_from_directory
    response = make_response(send_from_directory('static/js', 'webpush_service_worker.js'))
    response.headers['Service-Worker-Allowed'] = '/'
    return response


# Redirect to the correct to the full run path
@run_0_bp.route('/runs/<string:runid>/')
@handle_with_exception_factory
def runs0_nocfg(runid):
    run_root = pathlib.Path(get_wd(runid)).resolve()
    pup_relpath = request.args.get('pup')
    active_root = run_root

    if pup_relpath:
        pups_root = (run_root / '_pups').resolve()
        candidate = (pups_root / pup_relpath).resolve()
        try:
            candidate.relative_to(pups_root)
        except ValueError:
            abort(404)

        if not candidate.is_dir():
            abort(404)

        active_root = candidate

    try:
        ron = Ron.getInstance(str(active_root))
    except FileNotFoundError:
        abort(404)

    target_args = {'runid': runid, 'config': ron.config_stem}
    if pup_relpath:
        target_args['pup'] = pup_relpath

    next_target = _sanitize_runs0_next_target(request.args.get("next"), runid, ron.config_stem)
    if next_target:
        response = redirect(next_target)
        if _set_run_session_jwt_cookie(response, runid=runid, config=ron.config_stem):
            return response
        target_args['next'] = next_target
        return redirect(url_for_run('run_0.runs0', **target_args))

    return redirect(url_for_run('run_0.runs0', **target_args))


def _bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    token = raw.strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_site_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def _site_prefix() -> str:
    configured = current_app.config.get("SITE_PREFIX", DEFAULT_SITE_PREFIX)
    return _normalize_site_prefix(configured)


def _browse_jwt_cookie_name() -> str:
    value = (os.getenv(BROWSE_JWT_COOKIE_NAME_ENV) or "").strip()
    return value or DEFAULT_BROWSE_JWT_COOKIE_NAME


def _browse_jwt_cookie_key(runid: str, config: str) -> str:
    return browse_cookie_name(_browse_jwt_cookie_name(), runid, config)


def _browse_jwt_cookie_path(runid: str, config: str) -> str:
    return browse_cookie_path(_site_prefix(), runid, config)


def _batch_browse_compat_cookie_path() -> str:
    prefix = _site_prefix()
    return prefix or "/"


def _cookie_samesite() -> str:
    value = (os.getenv("WEPP_AUTH_SESSION_COOKIE_SAMESITE") or "lax").strip().lower()
    if value in {"lax", "strict", "none"}:
        return value
    return "lax"


def _request_is_secure() -> bool:
    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    if forwarded_proto in {"https", "http"}:
        return forwarded_proto == "https"

    forwarded_ssl = (request.headers.get("X-Forwarded-Ssl") or "").strip().lower()
    if forwarded_ssl in {"on", "off"}:
        return forwarded_ssl == "on"

    return bool(request.is_secure)


def _session_cookie_secure() -> bool:
    default_secure = _request_is_secure()
    if os.getenv("WEPP_AUTH_SESSION_COOKIE_SECURE") is None:
        return default_secure
    return _bool_env("WEPP_AUTH_SESSION_COOKIE_SECURE", default=default_secure)


def _parse_user_id(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _normalize_role_names(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        candidates = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, (list, tuple, set)):
        candidates = [str(item).strip() for item in raw if str(item).strip()]
    else:
        candidates = [str(raw).strip()] if str(raw).strip() else []

    names: list[str] = []
    seen: set[str] = set()
    for role in candidates:
        key = role.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(role)
    return names


def _session_identity_claims() -> tuple[int | None, list[str]]:
    user_id = _parse_user_id(session.get("_user_id") or session.get("user_id"))
    roles = _normalize_role_names(
        session.get("_roles_mask") or session.get("_roles") or session.get("roles")
    )
    return user_id, roles


def _owner_matches_user(owner: object, user_id: int) -> bool:
    owner_id = getattr(owner, "id", None)
    if owner_id is None:
        return False
    try:
        return int(owner_id) == int(user_id)
    except (TypeError, ValueError):
        return False


def _request_current_user_identity() -> tuple[int | None, set[str]]:
    try:
        user_obj = current_user
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:330", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None, set()

    try:
        if not bool(getattr(user_obj, "is_authenticated", False)):
            return None, set()
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:336", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None, set()

    user_id = _parse_user_id(getattr(user_obj, "id", None))
    if user_id is None:
        get_id = getattr(user_obj, "get_id", None)
        if callable(get_id):
            try:
                user_id = _parse_user_id(get_id())
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:345", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                user_id = None

    elevated_roles: set[str] = set()
    has_role = getattr(user_obj, "has_role", None)
    if callable(has_role):
        for role_name in ("Admin", "Root"):
            try:
                if has_role(role_name):
                    elevated_roles.add(role_name.lower())
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:355", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                continue

    return user_id, elevated_roles


def _authorization_runid(runid: str) -> str:
    raw = str(runid or "")
    parts = raw.split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"} and parts[-1]:
        return ";;".join(parts[:-2])
    return raw


def _session_user_authorized_for_run(runid: str, user_id: int | None, roles: list[str]) -> bool:
    auth_runid = _authorization_runid(runid)
    wd = get_wd(auth_runid, prefer_active=False)
    if Ron.ispublic(wd):
        return True

    role_set = {role.lower() for role in roles}
    fallback_user_id: int | None = None
    fallback_roles: set[str] = set()
    if user_id is None or not {"admin", "root"} & role_set:
        fallback_user_id, fallback_roles = _request_current_user_identity()
        role_set.update(fallback_roles)

    if "admin" in role_set or "root" in role_set:
        return True

    owners = get_run_owners_lazy(auth_runid)
    if not owners:
        return not auth_runid.startswith("batch;;")

    effective_user_id = user_id if user_id is not None else fallback_user_id
    if effective_user_id is None:
        return False
    return any(_owner_matches_user(owner, effective_user_id) for owner in owners)


def _resolve_session_id_from_request() -> str | None:
    sid = getattr(session, "sid", None)
    if sid:
        return str(sid)

    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    raw_cookie = request.cookies.get(cookie_name)
    if not raw_cookie:
        return None

    use_signer = current_app.config.get("SESSION_USE_SIGNER", True)
    if not use_signer:
        return str(raw_cookie)

    secret = current_app.config.get("SECRET_KEY") or get_secret("SECRET_KEY")
    if not secret:
        return None

    signer = Signer(secret, salt="flask-session", key_derivation="hmac")
    try:
        return signer.unsign(raw_cookie).decode("utf-8")
    except BadSignature:
        return None


def _store_session_marker(runid: str, session_id: str) -> None:
    key = f"auth:session:run:{runid}:{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        redis_conn.setex(key, SESSION_TOKEN_TTL_SECONDS, "1")
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _set_run_session_jwt_cookie(response, *, runid: str, config: str) -> bool:
    user_id, roles = _session_identity_claims()
    fallback_user_id: int | None = None
    fallback_roles: set[str] = set()
    if user_id is None or not roles:
        fallback_user_id, fallback_roles = _request_current_user_identity()
        if user_id is None and fallback_user_id is not None:
            user_id = fallback_user_id
        if fallback_roles:
            roles = _normalize_role_names([*roles, *sorted(fallback_roles)])

    session_id = _resolve_session_id_from_request()
    if not session_id:
        if _session_user_authorized_for_run(runid, user_id, roles):
            session_id = uuid.uuid4().hex
        else:
            return False

    if not _session_user_authorized_for_run(runid, user_id, roles):
        return False

    extra_claims: dict[str, object] = {
        "token_class": "session",
        "session_id": session_id,
        "runid": runid,
        "config": config,
        "jti": uuid.uuid4().hex,
    }
    if user_id is not None:
        extra_claims["user_id"] = user_id
    if roles:
        extra_claims["roles"] = roles

    token_payload = auth_tokens.issue_token(
        session_id,
        scopes=SESSION_TOKEN_SCOPES,
        audience="rq-engine",
        expires_in=SESSION_TOKEN_TTL_SECONDS,
        extra_claims=extra_claims,
    )
    token_value = token_payload.get("token")
    if not isinstance(token_value, str) or not token_value:
        return False

    _store_session_marker(runid, session_id)
    response.set_cookie(
        key=_browse_jwt_cookie_key(runid, config),
        value=token_value,
        max_age=SESSION_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=_session_cookie_secure(),
        samesite=_cookie_samesite(),
        path=_browse_jwt_cookie_path(runid, config),
    )
    if str(runid).startswith("batch;;"):
        response.set_cookie(
            key=_browse_jwt_cookie_name(),
            value=token_value,
            max_age=SESSION_TOKEN_TTL_SECONDS,
            httponly=True,
            secure=_session_cookie_secure(),
            samesite=_cookie_samesite(),
            path=_batch_browse_compat_cookie_path(),
        )
    return True


def _sanitize_runs0_next_target(next_value: str | None, runid: str, config: str) -> str | None:
    if not next_value:
        return None

    try:
        parsed = urlsplit(str(next_value))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:486", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None

    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path or ""
    if not path:
        return None
    if path.startswith("//"):
        return None
    if not path.startswith("/"):
        path = "/" + path.lstrip("/")
    if _path_has_unsafe_segments(path):
        return None

    run_base = f"{_site_prefix()}/runs/{runid}/"
    if not path.startswith(run_base):
        return None

    remainder = path[len(run_base):]
    if not remainder or remainder == config:
        normalized_path = f"{run_base}{config}/"
    elif remainder.startswith(f"{config}/"):
        normalized_path = f"{run_base}{remainder}"
    else:
        normalized_path = f"{run_base}{config}/{remainder.lstrip('/')}"

    expected_prefix = f"{run_base}{config}/"
    if not normalized_path.startswith(expected_prefix):
        return None

    if parsed.query:
        normalized_path = f"{normalized_path}?{parsed.query}"
    if parsed.fragment:
        normalized_path = f"{normalized_path}#{parsed.fragment}"
    return normalized_path


def _path_has_unsafe_segments(path: str) -> bool:
    normalized = path.replace("\\", "/")
    for segment in normalized.split("/"):
        if not segment:
            continue
        decoded = _fully_unquote_segment(segment).strip()
        if decoded in {".", ".."}:
            return True
        if "/" in decoded or "\\" in decoded:
            return True
    return False


def _fully_unquote_segment(segment: str, *, max_rounds: int = 8) -> str:
    decoded = str(segment)
    for _ in range(max_rounds):
        candidate = unquote(decoded)
        if candidate == decoded:
            break
        decoded = candidate
    return decoded

def _log_access(wd, current_user, ip):
    assert _exists(wd)

    fn, runid = _split(wd.rstrip('/'))
    fn = _join(fn, '.{}'.format(runid))
    with open(fn, 'a') as fp:
        email = getattr(current_user, 'email', '<anonymous>')
        fp.write('{},{},{}\n'.format(email, ip, datetime.now()))


def _build_runs0_context(runid, config, playwright_load_all):
    global VAPID_PUBLIC_KEY
    from wepppy.nodb.mods.revegetation import Revegetation
    from wepppy.wepp.soils import soilsdb
    from wepppy.wepp import management
    from wepp_runner.wepp_runner import get_linux_wepp_bin_opts
    from wepppy.wepp.management.managements import landuse_management_mapping_options
    from wepppy.weppcloud.app import db, Run

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    base_wd = str(ctx.run_root)
    ron = Ron.getInstance(wd)
    map_object_payload = ron.map.to_payload() if ron.map is not None else None
    map_object_json = json.dumps(map_object_payload, indent=2) if map_object_payload else ""

    # check config from url matches config from Ron
    if config != ron.config_stem:
        target_args = {'runid': runid, 'config': ron.config_stem}
        if ctx.pup_relpath:
            target_args['pup'] = ctx.pup_relpath
        return {'redirect': url_for_run('run_0.runs0', **target_args)}

    if ctx.pup_root and not ron.readonly:
        try:
            ron.readonly = True
        except Exception as exc:
            current_app.logger.warning('Failed to mark pup project as readonly: %s', exc)

    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    climate = Climate.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    site_prefix = current_app.config['SITE_PREFIX']

    # Browse links should follow truth-on-disk: prefer canonical WD-level sidecars,
    # fall back to legacy in-tree parquets when present, otherwise hide.
    browse_watershed_hillslopes_parquet = pick_existing_parquet_relpath(
        wd, "watershed/hillslopes.parquet"
    )
    browse_watershed_channels_parquet = pick_existing_parquet_relpath(
        wd, "watershed/channels.parquet"
    )
    browse_landuse_parquet = pick_existing_parquet_relpath(wd, "landuse/landuse.parquet")
    browse_soils_parquet = pick_existing_parquet_relpath(wd, "soils/soils.parquet")

    if watershed.delineation_backend_is_topaz:
        topaz = Topaz.getInstance(wd)
    else:
        topaz = None

    mods_list = ron.mods or []
    openet_admin_enabled = _openet_admin_enabled(playwright_load_all=playwright_load_all)
    show_openet_ts = openet_admin_enabled and ('openet_ts' in mods_list or playwright_load_all)

    observed = Observed.tryGetInstance(wd)
    rangeland_cover = RangelandCover.tryGetInstance(wd)
    rhem = Rhem.tryGetInstance(wd)
    openet_ts = OpenET_TS.tryGetInstance(wd) if show_openet_ts else None
    disturbed = Disturbed.tryGetInstance(wd)
    baer = Baer.tryGetInstance(wd) if 'baer' in ron.mods else None
    ash = Ash.tryGetInstance(wd)
    skid_trails = wepppy.nodb.mods.SkidTrails.tryGetInstance(wd)
    reveg = Revegetation.tryGetInstance(wd)
    omni = Omni.tryGetInstance(wd)
    treatments = Treatments.tryGetInstance(wd)
    redis_prep = RedisPrep.tryGetInstance(wd)
    debris_flow = DebrisFlow.tryGetInstance(wd) if 'debris_flow' in ron.mods else None
    swat = Swat.tryGetInstance(wd) if 'swat' in ron.mods else None
    swat_print_prt_rows = []
    swat_print_prt_meta = {}
    if swat is not None and swat.print_prt is not None:
        swat_print_prt_meta = {
            "nyskip": int(swat.print_prt.nyskip),
            "day_start": int(swat.print_prt.day_start),
            "yrc_start": int(swat.print_prt.yrc_start),
            "day_end": int(swat.print_prt.day_end),
            "yrc_end": int(swat.print_prt.yrc_end),
            "interval": int(swat.print_prt.interval),
        }
        try:
            rows = swat.print_prt.objects.iter_rows(swat.print_prt.object_order)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:637", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            rows = swat.print_prt.objects.iter_rows()
        for object_name, mask in rows:
            daily, monthly, yearly, avann = mask_to_tokens(int(mask))
            swat_print_prt_rows.append(
                {
                    "object": object_name,
                    "daily": daily == "y",
                    "monthly": monthly == "y",
                    "yearly": yearly == "y",
                    "avann": avann == "y",
                }
            )

    if redis_prep is not None:
        rq_job_ids = redis_prep.get_rq_job_ids()
    else:
        rq_job_ids = {}

    landuseoptions = landuse.landuseoptions
    landuse_report_context = build_landuse_report_context(landuse)
    soildboptions = soilsdb.load_db()

    critical_shear_options = management.load_channel_d50_cs()
    reveg_cover_transform_options = [
        ("", "Observed"),
        ("20-yr_Recovery.csv", "20-Year Recovery"),
        ("20-yr_PartialRecovery.csv", "20-Year Partial Recovery"),
        ("user_cover_transform", "User-Defined Transform")
    ]
    wepp_bin_options = [(opt, opt) for opt in get_linux_wepp_bin_opts()]

    _log_access(base_wd, current_user, request.remote_addr)
    timestamp = datetime.now()
    run_record = Run.query.filter(Run.runid == runid).first()
    if run_record is not None:
        run_record.last_accessed = timestamp
    else:
        Run.query.filter_by(runid=runid).update({'last_accessed': timestamp})
    db.session.commit()

    show_rap_ts = 'rap_ts' in mods_list or playwright_load_all
    show_treatments = 'treatments' in mods_list or playwright_load_all
    show_ash = 'ash' in mods_list or playwright_load_all
    is_omni_child = is_omni_child_run(runid, wd=wd, pup_relpath=ctx.pup_relpath)
    show_omni = (
        (('omni' in mods_list) or playwright_load_all)
        and ((omni is not None) or playwright_load_all)
        and not is_omni_child
    )
    show_observed = (observed is not None) or playwright_load_all
    allow_debris_flow = (
        current_user.has_role('PowerUser')
        or current_app.config.get('TEST_SUPPORT_ENABLED')
        or playwright_load_all
    )
    show_debris_flow = allow_debris_flow and (debris_flow is not None or playwright_load_all)
    show_dss_export = 'dss_export' in mods_list or playwright_load_all
    show_path_ce = 'path_ce' in mods_list or playwright_load_all

    bootstrap_admin_disabled = bool(getattr(run_record, "bootstrap_disabled", False)) if run_record else False
    bootstrap_is_anonymous = not bool(getattr(run_record, "owner_id", None)) if run_record else True
    
    omni_has_ran_scenarios = bool(omni and omni.has_ran_scenarios)
    omni_has_ran_contrasts = bool(omni and omni.has_ran_contrasts)

    mod_visibility = {
        'rap_ts': show_rap_ts,
        'openet_ts': show_openet_ts,
        'treatments': show_treatments,
        'ash': show_ash,
        'omni': show_omni,
        'observed': show_observed,
        'debris_flow': show_debris_flow,
        'dss_export': show_dss_export,
        'path_ce': show_path_ce,
    }

    context = dict(
        user=current_user,
        site_prefix=site_prefix,
        playwright_load_all=playwright_load_all,
        topaz=topaz,
        soils=soils,
        ron=ron,
        landuse=landuse,
        climate=climate,
        wepp=wepp,
        wepp_bin_options=wepp_bin_options,
        rhem=rhem,
        openet_ts=openet_ts,
        disturbed=disturbed,
        baer=baer,
        ash=ash,
        skid_trails=skid_trails,
        reveg=reveg,
        watershed=watershed,
        unitizer_nodb=unitizer,
        observed=observed,
        rangeland_cover=rangeland_cover,
        omni=omni,
        OmniScenario=OmniScenario,
        treatments=treatments,
        debris_flow=debris_flow,
        swat=swat,
        swat_print_prt_rows=swat_print_prt_rows,
        swat_print_prt_meta=swat_print_prt_meta,
        rq_job_ids=rq_job_ids,
        landuseoptions=landuseoptions,
        landcover_datasets=landuse.landcover_datasets,
        landuse_report_rows=landuse_report_context['report_rows'],
        landuse_dataset_options=landuse_report_context['dataset_options'],
        landuse_coverage_percentages=landuse_report_context['coverage_percentages'],
        landuse_management_mapping_options=landuse_management_mapping_options,
        soildboptions=soildboptions,
        critical_shear_options=critical_shear_options,
        reveg_cover_transform_options=reveg_cover_transform_options,
        climate_catalog=climate.catalog_datasets_payload(include_hidden=True),
        precisions=wepppy.nodb.unitizer.precisions,
        run_id=runid,
        runid=runid,
        config=config,
        map_object_payload=map_object_payload,
        map_object_json=map_object_json,
        toc_task_emojis=TOC_TASK_EMOJI_MAP,
        pup_relpath=ctx.pup_relpath,
        VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY,
        show_rap_ts=show_rap_ts,
        show_openet_ts=show_openet_ts,
        show_treatments=show_treatments,
        show_ash=show_ash,
        show_omni=show_omni,
        show_observed=show_observed,
        show_debris_flow=show_debris_flow,
        show_dss_export=show_dss_export,
        show_path_ce=show_path_ce,
        omni_user_defined_contrast_limit=int(getattr(omni_mod, "USER_DEFINED_CONTRAST_LIMIT", 200)),
        is_omni_child=is_omni_child,
        omni_has_ran_scenarios=omni_has_ran_scenarios,
        omni_has_ran_contrasts=omni_has_ran_contrasts,
        mod_visibility=mod_visibility,
        bootstrap_admin_disabled=bootstrap_admin_disabled,
        bootstrap_is_anonymous=bootstrap_is_anonymous,
        browse_watershed_hillslopes_parquet=browse_watershed_hillslopes_parquet,
        browse_watershed_channels_parquet=browse_watershed_channels_parquet,
        browse_landuse_parquet=browse_landuse_parquet,
        browse_soils_parquet=browse_soils_parquet,
    )
    return context

@run_0_bp.route('/runs/<string:runid>/<config>/')
@requires_cap(gate_reason="Complete verification to view this run.")
def runs0(runid, config):
    assert config is not None

    try:
        authorize(runid, config)

        # Check if migrations are needed (unless skip_migration_check is set)
        skip_migration_check = request.args.get('skip_migration_check', '').lower() in ('true', '1', 'yes')
        playwright_load_all = request.args.get('playwright_load_all', '').lower() in ('true', '1', 'yes')

        if not skip_migration_check and not playwright_load_all:
            wd = get_wd(runid)
            if _exists(wd):
                from wepppy.tools.migrations.runner import check_migrations_needed

                migration_status = check_migrations_needed(wd)
                gated_migrations = {
                    "nodb_version",
                    "watersheds",
                    "landuse_parquet",
                    "soils_parquet",
                }
                needs_migration = any(
                    entry.get("name") in gated_migrations and entry.get("would_apply")
                    for entry in migration_status.get("migrations", [])
                )
                if needs_migration:
                    # Redirect to migration page
                    return redirect(url_for_run('run_0.migration_page', runid=runid, config=config))

        context = _build_runs0_context(runid, config, playwright_load_all)
        if 'redirect' in context:
            return redirect(context['redirect'])
        return render_template('runs0_pure.htm', **context)
    except HTTPException:
        raise
    except Exception as exc:
        stacktrace = traceback.format_exc()
        # Reuse exception_factory for logging + run exception log side effects.
        exception_factory(msg=exc, stacktrace=stacktrace, runid=runid, details=stacktrace)
        return _render_run_internal_error_page(runid, config, stacktrace)


@run_0_bp.route('/runs/<string:runid>/<config>/migrate')
@authorize_and_handle_with_exception_factory
def migration_page(runid, config):
    """Display migration status page for a run that needs migrations."""
    from wepppy.tools.migrations.runner import check_migrations_needed
    from wepppy.weppcloud.app import get_run_owners
    
    wd = get_wd(runid)
    if not _exists(wd):
        abort(404)
    
    ron = Ron.getInstance(wd)
    migration_status = check_migrations_needed(wd)
    if not migration_status.get("needs_migration"):
        return redirect(url_for_run('run_0.runs0', runid=runid, config=config))
    
    # Check if user can migrate (owner or admin)
    is_owner = False
    is_admin = False
    try:
        owners = get_run_owners(runid)
        is_owner = current_user in owners if owners else True
        is_admin = current_user.has_role('Admin') if hasattr(current_user, 'has_role') else False
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:857", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        is_owner = True  # Allow if we can't determine ownership
    
    can_migrate = is_owner or is_admin
    is_readonly = ron.readonly
    
    context = {
        'runid': runid,
        'config': config,
        'ron': ron,
        'migration_status': migration_status,
        'can_migrate': can_migrate,
        'is_readonly': is_readonly,
        'is_owner': is_owner,
        'is_admin': is_admin,
        'user': current_user,
        'url_for_run': url_for_run,
    }
    return render_template('run_0/rq-migration-status.htm', **context)


@run_0_bp.route('/runs/<string:runid>/<config>/view/mod/<string:mod_name>')
@authorize_and_handle_with_exception_factory
def view_mod_section(runid, config, mod_name):
    mod_info = MOD_UI_DEFINITIONS.get(mod_name)
    if not mod_info:
        return error_factory('Unknown module')
    if mod_name == 'openet_ts' and not _openet_admin_enabled(playwright_load_all=False):
        return error_factory('OpenET Time Series is restricted to Admin users')

    context = _build_runs0_context(runid, config, playwright_load_all=False)
    if 'redirect' in context:
        return redirect(context['redirect'])

    if not context['mod_visibility'].get(mod_name):
        return error_factory('Module is not enabled for this run')

    section_inner = render_template(mod_info['template'], **context)
    section_html = render_template(
        'run_0/mod_section_wrapper.htm',
        section_id=mod_info['section_id'],
        section_class=mod_info.get('section_class', 'wc-stack'),
        section_html=section_inner,
    )
    return success_factory({
        'mod': mod_name,
        'section_id': mod_info['section_id'],
        'html': section_html,
    })

@run_0_bp.route('/create', strict_slashes=False)
@login_required
@handle_with_exception_factory
def create_index():
    try:
        rq_engine_token = _issue_rq_engine_token()
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token for create index")
        return exception_factory(f"JWT configuration error: {exc}")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:914", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory()

    configs = get_configs()
    rows = []
    create_action = "/rq-engine/create/"
    for cfg in sorted(configs):
        if cfg == '_defaults':
            continue

        variants = [
            {
                "label": cfg,
                "overrides": {},
                "config": cfg,
                "action_url": create_action,
            },
            {
                "label": f"{cfg} ned1/2016",
                "overrides": {"general:dem_db": "ned1/2016"},
                "config": cfg,
                "action_url": create_action,
            },
            {
                "label": f"{cfg} WhiteBoxTools",
                "overrides": {"watershed:delineation_backend": "wbt"},
                "config": cfg,
                "action_url": create_action,
            },
        ]
        rows.append({"config": cfg, "variants": variants})

    cap_base_url = None
    cap_asset_base_url = None
    cap_site_key = None
    if current_user.is_anonymous:
        cap_base_url = (current_app.config.get("CAP_BASE_URL") or os.getenv("CAP_BASE_URL", "/cap")).rstrip("/")
        cap_asset_base_url = (
            current_app.config.get("CAP_ASSET_BASE_URL")
            or os.getenv("CAP_ASSET_BASE_URL", f"{cap_base_url}/assets")
        ).rstrip("/")
        cap_site_key = current_app.config.get("CAP_SITE_KEY") or os.getenv("CAP_SITE_KEY", "")

    return render_template(
        "run_0/create_index.htm",
        rows=rows,
        cap_base_url=cap_base_url,
        cap_asset_base_url=cap_asset_base_url,
        cap_site_key=cap_site_key,
        rq_engine_token=rq_engine_token,
    )

def create_run_dir(current_user):
    wd = None
    dir_created = False
    while not dir_created:
        email = getattr(current_user, "email", "")
        runid = generate_runid(email)

        wd = get_wd(runid)
        if _exists(wd):
            continue

        os.makedirs(wd)
        dir_created = True

    return runid, wd


def _issue_rq_engine_token() -> str:
    subject = None
    if hasattr(current_user, "get_id"):
        subject = current_user.get_id()
    if not subject:
        subject = getattr(current_user, "id", None)
    if not subject:
        subject = getattr(current_user, "email", None)
    if not subject:
        raise RuntimeError("Unable to resolve user subject for rq-engine token")

    roles = [
        str(getattr(role, "name", role)).strip()
        for role in (getattr(current_user, "roles", None) or [])
        if str(getattr(role, "name", role)).strip()
    ]

    token_payload = auth_tokens.issue_token(
        str(subject),
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={
            "roles": roles,
            "token_class": "user",
            "email": getattr(current_user, "email", None),
            "jti": uuid.uuid4().hex,
        },
    )
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("Failed to issue rq-engine token")
    return token


def _render_run_not_found_page() -> Response:
    view_args = getattr(request, "view_args", {}) or {}
    runid = view_args.get("runid") or request.args.get("runid") or ""
    config = view_args.get("config") or request.args.get("config") or ""
    context = {
        "runid": runid,
        "config": config,
        "diff_runid": "",
        "project_href": "",
        "breadcrumbs_html": "",
        "error_message": "This run either doesn't exist or you don't have access to it.",
        "page_title": "Run Not Found",
    }
    return make_response(render_template("browse/not_found.htm", **context), 404)


def _render_run_internal_error_page(runid: str, config: str, stacktrace: str) -> Response:
    context = {
        "runid": runid,
        "config": config,
        "stacktrace": stacktrace,
    }
    return make_response(render_template("errors/run_0_internal_error.htm", **context), 500)


@run_0_bp.app_errorhandler(403)
def _runs0_forbidden(error):  # pragma: no cover - flask error hook
    return _render_run_not_found_page()


@run_0_bp.app_errorhandler(404)
def _runs0_not_found(error):  # pragma: no cover - flask error hook
    return _render_run_not_found_page()
