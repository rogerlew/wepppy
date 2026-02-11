from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import json
from flask import send_from_directory
from flask_security import current_user

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


def _is_same_origin_post() -> bool:
    origin = request.headers.get("Origin", "").strip()
    if origin:
        return origin.rstrip("/") == request.host_url.rstrip("/")

    referer = request.headers.get("Referer", "").strip()
    if not referer:
        return True

    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return False
    referer_origin = f"{parsed.scheme}://{parsed.netloc}"
    return referer_origin.rstrip("/") == request.host_url.rstrip("/")


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
    except:
        pass

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
