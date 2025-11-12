from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json
from flask import send_from_directory
from flask_security import current_user

from ._common import *  # noqa: F401,F403
from wepppy.weppcloud.utils.helpers import exception_factory, handle_with_exception_factory


weppcloud_site_bp = Blueprint('weppcloud_site', __name__)

_ACCESS_LOG_ENV_KEY = 'WEPP_ACCESS_LOG_PATH'
_ACCESS_LOG_DEFAULT = '/geodata/weppcloud_runs/access.csv'
_RUN_LOCATIONS_FILENAME = 'runid-locations.json'
_LANDING_STATIC_DIRNAME = 'ui-lab'
_BOOL_TRUE = {'1', 'true', 'yes', 'y', 'on'}


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _BOOL_TRUE


def _parse_timestamp(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _derive_run_name(runid: str) -> str:
    slug = runid.strip().split('/')[-1]
    slug = slug.lstrip('.')
    if not slug:
        return runid
    return slug.replace('-', ' ')


def _resolve_access_log_path() -> Path:
    override = os.environ.get(_ACCESS_LOG_ENV_KEY)
    configured = current_app.config.get(_ACCESS_LOG_ENV_KEY)
    resolved = override or configured or _ACCESS_LOG_DEFAULT
    return Path(resolved)


def _resolve_run_locations_path() -> Path:
    static_dir = Path(current_app.static_folder)
    static_dir.mkdir(parents=True, exist_ok=True)
    return static_dir / _RUN_LOCATIONS_FILENAME


def _resolve_landing_static_root() -> Path:
    return Path(current_app.static_folder) / _LANDING_STATIC_DIRNAME


def _resolve_landing_static_asset(*parts: str) -> Path:
    return _resolve_landing_static_root().joinpath(*parts)


def _build_run_location_dataset(source_path: Path) -> List[Dict[str, Any]]:
    if not source_path.exists():
        return []

    dedup: Dict[str, Dict[str, Any]] = {}

    try:
        fp = source_path.open()
    except OSError:
        return []

    with fp:
        reader = csv.DictReader(fp)
        for row in reader:
            runid = (row.get('runid') or '').strip()
            if not runid:
                continue

            lon = _parse_float(row.get('centroid_longitude'))
            lat = _parse_float(row.get('centroid_latitude'))
            if lon is None or lat is None:
                continue

            timestamp = _parse_timestamp(row.get('date'))
            record = dedup.get(runid)

            base_payload = {
                'runid': runid,
                'run_name': _derive_run_name(runid),
                'coordinates': [lon, lat],
                'config': row.get('config'),
                'year': _parse_int(row.get('year')),
                'has_sbs': _parse_bool(row.get('has_sbs')),
                'hillslopes': _parse_int(row.get('hillslopes')),
                'ash_hillslopes': _parse_int(row.get('ash_hillslopes')),
            }

            if record is None:
                base_payload.update({
                    'access_count': 1,
                    '_last_accessed': timestamp,
                })
                dedup[runid] = base_payload
                continue

            record['access_count'] += 1
            if timestamp and (record['_last_accessed'] is None or timestamp > record['_last_accessed']):
                record.update(base_payload)
                record['_last_accessed'] = timestamp

    dataset: List[Dict[str, Any]] = []
    for record in dedup.values():
        last_accessed = record.pop('_last_accessed', None)
        record['last_accessed'] = last_accessed.isoformat() if isinstance(last_accessed, datetime) else None
        dataset.append(record)

    dataset.sort(
        key=lambda entry: entry['last_accessed'] or '',
        reverse=True,
    )
    return dataset


def _write_run_locations_file(dest: Path, dataset: List[Dict[str, Any]]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_name(dest.name + '.tmp')
    with tmp_path.open('w') as handle:
        json.dump(dataset, handle, indent=2)
    tmp_path.replace(dest)


def _load_or_refresh_run_locations(force: bool = False) -> List[Dict[str, Any]]:
    source_path = _resolve_access_log_path()
    output_path = _resolve_run_locations_path()

    needs_refresh = force or not output_path.exists()
    if not needs_refresh and source_path.exists():
        try:
            needs_refresh = source_path.stat().st_mtime > output_path.stat().st_mtime
        except OSError:
            needs_refresh = True

    if needs_refresh:
        dataset = _build_run_location_dataset(source_path)
        _write_run_locations_file(output_path, dataset)
        return dataset

    try:
        with output_path.open() as handle:
            cached = json.load(handle)
            if isinstance(cached, list):
                return cached
    except (OSError, json.JSONDecodeError):
        pass

    dataset = _build_run_location_dataset(source_path)
    _write_run_locations_file(output_path, dataset)
    return dataset


@weppcloud_site_bp.route('/')
def index():
    runs_counter = Counter()
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = Counter(json.load(fp))
    except:
        pass

    try:
        return render_template('index.htm', user=current_user, runs_counter=runs_counter)
    except Exception:
        return exception_factory()


@weppcloud_site_bp.route('/about/', strict_slashes=False)
@handle_with_exception_factory
def about():
    return render_template('about.htm', user=current_user)


@weppcloud_site_bp.route('/landing/', strict_slashes=False)
@handle_with_exception_factory
def landing():
    try:
        _load_or_refresh_run_locations(force=True)
    except Exception:
        current_app.logger.exception('Failed to refresh landing run locations')

    vite_index = _resolve_landing_static_asset('index.html')
    if vite_index.exists():
        return send_from_directory(vite_index.parent, vite_index.name)

    return render_template('landing.htm', user=current_user)


@weppcloud_site_bp.route('/landing/run-locations.json', strict_slashes=False)
@handle_with_exception_factory
def landing_run_locations():
    dataset = _load_or_refresh_run_locations()
    return jsonify(dataset)


@weppcloud_site_bp.route('/landing/assets/<path:asset_path>', strict_slashes=False)
@handle_with_exception_factory
def landing_static_assets(asset_path: str):
    assets_root = _resolve_landing_static_asset('assets')
    if not assets_root.exists():
        abort(404)
    return send_from_directory(assets_root, asset_path)


@weppcloud_site_bp.route('/landing/vite.svg', strict_slashes=False)
@handle_with_exception_factory
def landing_static_vite_icon():
    icon_path = _resolve_landing_static_asset('vite.svg')
    if not icon_path.exists():
        abort(404)
    return send_from_directory(icon_path.parent, icon_path.name)
