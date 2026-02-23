from collections import Counter
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import json
from flask import send_from_directory, session
from flask_security import current_user
from werkzeug.routing import BuildError

from ._common import *  # noqa: F401,F403
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import exception_factory, handle_with_exception_factory
from wepppy.weppcloud.utils.rq_engine_token import issue_user_rq_engine_token


weppcloud_site_bp = Blueprint('weppcloud_site', __name__)

_ACCESS_LOG_ENV_KEY = 'WEPP_ACCESS_LOG_PATH'
_ACCESS_LOG_DEFAULTS = [
    '/geodata/weppcloud_runs/access.csv',
    '/wc1/geodata/weppcloud_runs/access.csv',
]
_RUN_LOCATIONS_FILENAME = 'runid-locations.json'
_LANDING_STATIC_DIRNAME = 'ui-lab'


def _issue_rq_engine_token() -> str | None:
    return issue_user_rq_engine_token(current_user)


def _normalized_origin(value: str) -> tuple[str, str, int] | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    if not scheme or not host:
        return None
    port = parsed.port
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
        else:
            return None
    return scheme, host, int(port)


def _allowed_origin_set() -> set[tuple[str, str, int]]:
    origins: set[tuple[str, str, int]] = set()

    def _add(candidate: str) -> None:
        normalized = _normalized_origin(candidate)
        if normalized is not None:
            origins.add(normalized)

    _add(request.host_url)
    _add(f"{request.scheme}://{request.host}")

    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
    if forwarded_proto and request.host:
        _add(f"{forwarded_proto}://{request.host}")
    if forwarded_host:
        _add(f"{forwarded_proto or request.scheme}://{forwarded_host}")

    external_host = (
        current_app.config.get("OAUTH_REDIRECT_HOST")
        or current_app.config.get("EXTERNAL_HOST")
        or ""
    )
    external_scheme = (current_app.config.get("OAUTH_REDIRECT_SCHEME") or request.scheme or "").strip().lower()
    if external_host:
        _add(f"{external_scheme}://{external_host}")

    return origins


def _is_same_origin_post() -> bool:
    allowed_origins = _allowed_origin_set()
    origin = request.headers.get("Origin", "").strip()
    if origin:
        normalized_origin = _normalized_origin(origin)
        return normalized_origin in allowed_origins

    referer = request.headers.get("Referer", "").strip()
    if not referer:
        return False

    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return False
    referer_origin = f"{parsed.scheme}://{parsed.netloc}"
    normalized_referer_origin = _normalized_origin(referer_origin)
    return normalized_referer_origin in allowed_origins


@weppcloud_site_bp.route('/api/auth/rq-engine-token', methods=['POST'])
def issue_rq_engine_token():
    if current_user.is_anonymous:
        response = error_factory('Authentication required.')
        response.status_code = 401
        return response
    if not _is_same_origin_post():
        response = error_factory('Cross-origin request blocked.')
        response.status_code = 403
        return response

    try:
        token = _issue_rq_engine_token()
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token via API")
        response = error_factory(f"JWT configuration error: {exc}")
        response.status_code = 500
        return response
    except Exception:
        current_app.logger.exception("Failed to issue rq-engine token via API")
        response = error_factory("Failed to issue rq-engine token.")
        response.status_code = 500
        return response

    return jsonify({"token": token})


@weppcloud_site_bp.route('/api/auth/session-heartbeat', methods=['POST'])
def session_heartbeat():
    if current_user.is_anonymous:
        response = error_factory('Authentication required.')
        response.status_code = 401
        return response
    if not _is_same_origin_post():
        response = error_factory('Cross-origin request blocked.')
        response.status_code = 403
        return response

    heartbeat_at = int(time.time())
    session["_heartbeat_ts"] = heartbeat_at
    session.modified = True
    return jsonify({"ok": True, "heartbeat_at": heartbeat_at})


def _normalized_cookie_path(value: Optional[str]) -> str:
    path = str(value or "").strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def _path_variants(value: Optional[str]) -> list[str]:
    candidates: list[str] = []
    raw = str(value or "").strip()
    if raw:
        candidates.append(raw)
    normalized = _normalized_cookie_path(value)
    candidates.append(normalized)
    if normalized != "/":
        candidates.append(f"{normalized}/")

    variants: list[str] = []
    for candidate in candidates:
        normalized_candidate = _normalized_cookie_path(candidate)
        if normalized_candidate not in variants:
            variants.append(normalized_candidate)
        if (
            normalized_candidate != "/"
            and not normalized_candidate.endswith("/")
            and f"{normalized_candidate}/" not in variants
        ):
            variants.append(f"{normalized_candidate}/")
    return variants


def _normalized_cookie_domain(value: Optional[str]) -> Optional[str]:
    token = str(value or "").strip().lower()
    if not token:
        return None
    if ":" in token:
        token = token.split(":", 1)[0].strip()
    if not token:
        return None
    return token


def _domain_variants(configured_domain: Optional[str]) -> list[Optional[str]]:
    variants: list[Optional[str]] = []

    def _add(value: Optional[str]) -> None:
        normalized = _normalized_cookie_domain(value)
        if not normalized:
            return
        base = normalized.lstrip(".")
        for candidate in (base, f".{base}"):
            if candidate and candidate not in variants:
                variants.append(candidate)

    _add(configured_domain)
    _add(request.host)
    _add(current_app.config.get("OAUTH_REDIRECT_HOST"))
    _add(current_app.config.get("EXTERNAL_HOST"))

    variants.append(None)
    return variants


def _cookie_clear_targets(
    configured_path: Optional[str],
    configured_domain: Optional[str],
) -> list[tuple[str, Optional[str]]]:
    targets: list[tuple[str, Optional[str]]] = []
    path_values = [
        configured_path,
        current_app.config.get("APPLICATION_ROOT"),
        "/",
    ]

    path_variants: list[str] = []
    for path_value in path_values:
        for variant in _path_variants(path_value):
            if variant not in path_variants:
                path_variants.append(variant)

    for path in path_variants:
        for domain in _domain_variants(configured_domain):
            target = (path, domain)
            if target not in targets:
                targets.append(target)
    return targets


def _clear_reset_browser_state_cookies(response) -> list[dict[str, Optional[str]]]:
    session_cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    remember_cookie_name = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    cookie_specs = [
        (
            session_cookie_name,
            current_app.config.get("SESSION_COOKIE_PATH"),
            current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
        (
            remember_cookie_name,
            current_app.config.get("REMEMBER_COOKIE_PATH"),
            current_app.config.get("REMEMBER_COOKIE_DOMAIN")
            or current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
        (
            "csrf_token",
            current_app.config.get("SESSION_COOKIE_PATH"),
            current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
        (
            "csrftoken",
            current_app.config.get("SESSION_COOKIE_PATH"),
            current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
    ]

    cleared: list[dict[str, Optional[str]]] = []
    seen_names: set[str] = set()
    for cookie_name, cookie_path, cookie_domain in cookie_specs:
        normalized_name = str(cookie_name or "").strip()
        if not normalized_name or normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)
        for path, domain in _cookie_clear_targets(cookie_path, cookie_domain):
            response.delete_cookie(normalized_name, path=path, domain=domain)
            cleared.append(
                {
                    "name": normalized_name,
                    "path": path,
                    "domain": domain,
                }
            )
    return cleared

@weppcloud_site_bp.route('/api/auth/reset-browser-state', methods=['POST'])
def reset_browser_state():
    if current_user.is_anonymous:
        response = error_factory('Authentication required.')
        response.status_code = 401
        return response
    if not _is_same_origin_post():
        response = error_factory('Cross-origin request blocked.')
        response.status_code = 403
        return response

    session_key_count = len(list(session.keys()))
    session.clear()
    session.modified = True

    try:
        login_url = url_for('security.login')
    except BuildError:
        login_url = '/login'

    response = jsonify(
        {
            "ok": True,
            "login_url": login_url,
            "cleared_session_keys": session_key_count,
            "message": "Browser state reset. Continue by signing in again.",
        }
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    _clear_reset_browser_state_cookies(response)
    return response


def _resolve_access_log_path() -> Path:
    override = os.environ.get(_ACCESS_LOG_ENV_KEY)
    configured = current_app.config.get(_ACCESS_LOG_ENV_KEY)
    if override:
        return Path(override)
    if configured:
        return Path(configured)

    for candidate in _ACCESS_LOG_DEFAULTS:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path
    # Fall back to the first entry so downstream callers still receive a Path
    return Path(_ACCESS_LOG_DEFAULTS[0])


def _resolve_run_locations_path() -> Path:
    """Return a writable path for the run-locations cache file.

    Uses the same directory as the access log (typically /geodata/weppcloud_runs/)
    since that location is writable in production. Falls back to /tmp if the
    access log directory doesn't exist.
    """
    access_log_dir = _resolve_access_log_path().parent
    if access_log_dir.exists():
        return access_log_dir / _RUN_LOCATIONS_FILENAME
    # Fallback to /tmp for environments where geodata isn't mounted
    fallback = Path('/tmp')
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / _RUN_LOCATIONS_FILENAME


def _resolve_landing_static_root() -> Path:
    return Path(current_app.static_folder) / _LANDING_STATIC_DIRNAME


def _resolve_landing_static_asset(*parts: str) -> Path:
    return _resolve_landing_static_root().joinpath(*parts)


def _load_or_refresh_run_locations(force: bool = False) -> List[Dict[str, Any]]:
    output_path = _resolve_run_locations_path()

    if force and not output_path.exists():
        current_app.logger.warning(
            "Run locations cache missing at %s; waiting for compile_dot_logs.",
            output_path,
        )
    try:
        with output_path.open() as handle:
            cached = json.load(handle)
            if isinstance(cached, list):
                return cached
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _build_landing_state() -> Dict[str, Any]:
    user_info: Dict[str, Any] = {
        'is_authenticated': bool(getattr(current_user, 'is_authenticated', False)),
        'email': getattr(current_user, 'email', None),
        'name': getattr(current_user, 'name', None),
    }
    return {'user': user_info}


def _render_ui_lab_index_with_state(index_path: Path) -> Optional['flask.Response']:
    try:
        html = index_path.read_text(encoding='utf-8')
    except OSError:
        return None

    state_json = json.dumps(_build_landing_state())
    injection = f'<script>window.__WEPP_STATE__ = {state_json};</script>'
    if '</head>' in html:
        html = html.replace('</head>', f'{injection}</head>', 1)
    else:
        html = injection + html

    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response


def _landing_assets_dir() -> Path:
    return _resolve_landing_static_asset('assets')


def _render_landing_page(variant: str = 'light') -> 'flask.Response':
    """Render landing page.

    Args:
        variant: 'light' for flat governmental style, 'dark' for aurora/glassmorphism style
    """
    try:
        _load_or_refresh_run_locations()
    except Exception:
        current_app.logger.exception('Failed to refresh landing run locations')

    index_file = 'index-light.html' if variant == 'light' else 'index.html'
    vite_index = _resolve_landing_static_asset(index_file)
    if vite_index.exists():
        rendered = _render_ui_lab_index_with_state(vite_index)
        if rendered is not None:
            return rendered

    return render_template('landing.htm', user=current_user)


@weppcloud_site_bp.route('/')
@handle_with_exception_factory
def index():
    return _render_landing_page('light')


@weppcloud_site_bp.route('/interfaces/', strict_slashes=False)
def interfaces():
    runs_counter = Counter()
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = Counter(json.load(fp))
    except (OSError, json.JSONDecodeError) as exc:
        current_app.logger.debug("Failed to load runs_counter.json for interfaces: %s", exc)
    except Exception:
        current_app.logger.exception("Unexpected error loading runs_counter.json for interfaces")

    try:
        cap_base_url = (current_app.config.get('CAP_BASE_URL') or os.getenv('CAP_BASE_URL', '/cap')).rstrip('/')
        cap_asset_base_url = (
            current_app.config.get('CAP_ASSET_BASE_URL')
            or os.getenv('CAP_ASSET_BASE_URL', f'{cap_base_url}/assets')
        ).rstrip('/')
        cap_site_key = current_app.config.get('CAP_SITE_KEY') or os.getenv('CAP_SITE_KEY', '')
        rq_engine_token = _issue_rq_engine_token()
        return render_template(
            'interfaces.htm',
            user=current_user,
            runs_counter=runs_counter,
            cap_base_url=cap_base_url,
            cap_asset_base_url=cap_asset_base_url,
            cap_site_key=cap_site_key,
            rq_engine_token=rq_engine_token,
        )
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token for interfaces")
        return exception_factory(f"JWT configuration error: {exc}")
    except Exception:
        return exception_factory()


@weppcloud_site_bp.route('/cap/verify', methods=['POST'])
@handle_with_exception_factory
def cap_verify():
    from wepppy.weppcloud.utils.cap_guard import mark_cap_verified
    from wepppy.weppcloud.utils.cap_verify import CapVerificationError, verify_cap_token

    payload = request.get_json(silent=True) or {}
    cap_token = (request.form.get('cap_token') or payload.get('cap_token') or '').strip()
    if not cap_token:
        response = error_factory('CAPTCHA token is required.')
        response.status_code = 403
        return response

    try:
        verification = verify_cap_token(cap_token)
    except CapVerificationError as exc:
        current_app.logger.error("CAPTCHA verification error from %s: %s", request.remote_addr, exc)
        return exception_factory('CAPTCHA verification failed.')

    if not verification.get('success'):
        current_app.logger.warning(
            "CAPTCHA rejected from %s (errors=%s)",
            request.remote_addr,
            verification.get('error-codes'),
        )
        response = error_factory('CAPTCHA verification failed.')
        response.status_code = 403
        return response

    mark_cap_verified()
    return jsonify({})


def _landing_run_locations_response() -> 'flask.Response':
    dataset = _load_or_refresh_run_locations()
    return jsonify(dataset)


@weppcloud_site_bp.route('/landing/', strict_slashes=False)
@handle_with_exception_factory
def landing():
    return _render_landing_page('light')


@weppcloud_site_bp.route('/landing/light/', strict_slashes=False)
@handle_with_exception_factory
def landing_light():
    """Render the light-themed (governmental aesthetic) landing page variant."""
    return _render_landing_page('light')


@weppcloud_site_bp.route('/landing/dark/', strict_slashes=False)
@handle_with_exception_factory
def landing_dark():
    """Render the dark-themed (aurora/glassmorphism) landing page variant."""
    return _render_landing_page('dark')


@weppcloud_site_bp.route('/landing/run-locations.json', strict_slashes=False)
@handle_with_exception_factory
def landing_run_locations():
    return _landing_run_locations_response()


@weppcloud_site_bp.route('/run-locations.json', strict_slashes=False)
@handle_with_exception_factory
def landing_run_locations_root():
    return _landing_run_locations_response()


def _get_mimetype_for_asset(asset_path: str) -> Optional[str]:
    """Return explicit MIME type for assets that Safari may reject otherwise."""
    if asset_path.endswith('.js'):
        return 'application/javascript'
    if asset_path.endswith('.mjs'):
        return 'application/javascript'
    if asset_path.endswith('.css'):
        return 'text/css'
    if asset_path.endswith('.json'):
        return 'application/json'
    return None


@weppcloud_site_bp.route('/landing/assets/<path:asset_path>', strict_slashes=False)
@handle_with_exception_factory
def landing_static_assets(asset_path: str):
    assets_root = _landing_assets_dir()
    if not assets_root.exists():
        abort(404)
    mimetype = _get_mimetype_for_asset(asset_path)
    if mimetype:
        return send_from_directory(assets_root, asset_path, mimetype=mimetype)
    return send_from_directory(assets_root, asset_path)


@weppcloud_site_bp.route('/assets/<path:asset_path>', strict_slashes=False)
@handle_with_exception_factory
def landing_static_assets_root(asset_path: str):
    return landing_static_assets(asset_path)


@weppcloud_site_bp.route('/landing/vite.svg', strict_slashes=False)
@handle_with_exception_factory
def landing_static_vite_icon():
    icon_path = _resolve_landing_static_asset('vite.svg')
    if not icon_path.exists():
        abort(404)
    return send_from_directory(icon_path.parent, icon_path.name)


@weppcloud_site_bp.route('/vite.svg', strict_slashes=False)
@handle_with_exception_factory
def landing_static_vite_icon_root():
    return landing_static_vite_icon()
