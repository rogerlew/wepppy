"""Embedded D-Tale service tailored for WEPP Cloud run directories.

`wepppy.webservices.dtale` wires the upstream `dtale` Flask application into the
WEPPpy deployment so analysts can explore run outputs without leaving the
browser. The wrapper:

* resolves run-scoped file paths (`/runs/<runid>/<config>/...`) and guards
  against traversal attacks
* converts a range of tabular formats (Parquet, CSV/TSV, Feather, Pickle) into
  pandas DataFrames with canonical identifier aliases (`TopazID`, `field_id`, …)
* multiplexes datasets in-process by hashing the resolved path so that repeated
  requests reuse cached D-Tale sessions when the underlying file has not
  changed
* registers run-aware GeoJSON overlays (watershed subcatchments, channels,
  optional AgFields boundaries) so the D-Tale choropleth editor exposes useful
  defaults

Deployment knobs are driven by environment variables (`HOST`, `PORT`,
`DTALE_BASE_URL`, `DTALE_INTERNAL_TOKEN`, `DTALE_MAX_FILE_MB`, `DTALE_MAX_ROWS`,
etc.). The Flask app exposes two routes:

* ``GET /health`` – liveness check returning ``{"status": "ok"}``
* ``POST /internal/load`` – authenticated endpoint that loads a file into
  D-Tale and returns the dataset ID plus viewer URL
* ``GET /dtale/access/<ticket>`` – short-lived private-resource launch that
  establishes a scoped, HttpOnly viewer cookie

Clients must supply ``X-DTALE-TOKEN`` when `DTALE_INTERNAL_TOKEN` is configured.
The loader also requires its trusted caller to state `resource_public`. Private
tables are hidden from anonymous grid, export, name, enumeration and derived
dataset paths; public tables retain ordinary anonymous downstream access.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import duckdb
import pandas as pd
import pyarrow.parquet as pq
from flask import abort, g, has_request_context, jsonify, redirect, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from dtale import global_state
from dtale.app import build_app, initialize_process_props
import dtale.views as dtale_views
from dtale.views import DtaleData, build_dtypes_state, startup
from plotly import graph_objs as go

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.config.secrets import get_secret
from wepppy.all_your_base.file_digest import sha256_file
from wepppy.microservices.parquet_filters import (
    CompiledParquetFilter,
    ParquetFilterError,
    compile_filter_payload_for_path,
    count_rows as count_filtered_parquet_rows,
)
from wepppy.nodb.core.watershed import Watershed
from wepppy.nodb.base import NoDbBase

try:
    from wepppy.nodb.mods.ag_fields.ag_fields import AgFields
except ImportError:  # pragma: no cover - optional module
    AgFields = None

try:
    from dtale.dash_application import custom_geojson as dtale_custom_geojson
    from dtale.dash_application import dcc as dtale_dcc
    from dtale.dash_application import charts as dtale_charts
except ImportError:  # pragma: no cover - custom geojson shipped in dtale>=1.8.17
    dtale_custom_geojson = None
    dtale_dcc = None
    dtale_charts = None

logger = logging.getLogger(__name__)


def _clean_prefix(value: str | None) -> str | None:
    """Normalize a URL prefix by stripping slashes and returning ``None`` when blank."""
    if not value:
        return None
    stripped = value.strip()
    if not stripped or stripped == "/":
        return None
    return "/" + stripped.strip("/")


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9010"))

# Ensure the embedded D-Tale app believes it is running on our fixed host/port.
initialize_process_props(host=HOST, port=PORT)

SITE_PREFIX = _clean_prefix(os.getenv("SITE_PREFIX"))
APP_ROOT = SITE_PREFIX
IS_PROXY = APP_ROOT is not None

DTALE_BASE_URL = os.getenv("DTALE_BASE_URL", f"http://{HOST}:{PORT}")
DTALE_INTERNAL_TOKEN = (get_secret("DTALE_INTERNAL_TOKEN") or "").strip()
if not DTALE_INTERNAL_TOKEN:
    logger.warning(
        "DTALE_INTERNAL_TOKEN is not set – falling back to in-process requests only."
    )

MAX_FILE_MB = float(os.getenv("DTALE_MAX_FILE_MB", "512"))
MAX_ROWS = int(os.getenv("DTALE_MAX_ROWS", "0"))
ALLOW_CELL_EDITS = os.getenv("DTALE_ALLOW_CELL_EDITS", "0").lower() in {"1", "true", "yes"}
DTALE_THEME = os.getenv("DTALE_THEME", "light")
BROWSE_PARQUET_FILTERS_ENABLED = os.getenv("BROWSE_PARQUET_FILTERS_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
DTALE_PRIVATE_ACCESS_TTL_SECONDS = int(os.getenv("DTALE_PRIVATE_ACCESS_TTL_SECONDS", "3600"))
DTALE_PRIVATE_LAUNCH_TTL_SECONDS = int(os.getenv("DTALE_PRIVATE_LAUNCH_TTL_SECONDS", "60"))

global_state.set_app_settings(
    {
        "hide_shutdown": True,
        "hide_header_editor": True,
        "theme": DTALE_THEME,
    }
)


@dataclass
class DatasetMeta:
    path: Path
    fingerprint: str
    name: str
    last_loaded: float
    resolved_path: Path | None = None
    runid: str = ""
    config: str = ""
    resource_public: bool = False


@dataclass(frozen=True)
class ViewerCapability:
    scope: str
    runid: str
    claims: dict[str, Any]
    feature_id: str | None
    expires_at: float


DATASETS: dict[str, DatasetMeta] = {}
DATASET_ACCESS_SCOPES: dict[str, frozenset[str]] = {}
VIEWER_CAPABILITIES: dict[str, ViewerCapability] = {}
LAZY_PARQUET_DATASETS: dict[str, "LazyParquetDtaleInstance"] = {}
REGISTERED_GEOJSON: dict[str, str] = {}
MAP_DEFAULTS: dict[str, dict[str, object]] = {}
MAP_CHOICES: dict[str, list[tuple[str, str, str | None]]] = {}
GEOJSON_ACCESS_SCOPES: dict[str, frozenset[str]] = {}
_IDENTIFIER_STRING_ALIASES: tuple[tuple[str, str], ...] = (
    ("wepp_id", "WeppID"),
    ("topaz_id", "TopazID"),
    ("channel_id", "ChannelID"),
    ("reach_id", "ReachID"),
    ("field_id", "FieldID"),
    ("sub_field_id", "SubFieldID"),
)


def _fingerprint(path: Path) -> str:
    """Observe source bytes without treating metadata as content identity."""
    try:
        return sha256_file(path)
    except OSError as exc:
        raise _SourceChangedError(_SOURCE_CHANGED_MESSAGE) from exc


_SOURCE_CHANGED_MESSAGE = "The source file changed or is unavailable. Reopen this dataset from browse."


class _SourceChangedError(RuntimeError):
    """The accepted dataset generation cannot serve this read."""


def _resolve_source_path(path: Path) -> Path:
    try:
        return path.resolve()
    except (OSError, RuntimeError) as exc:
        # Python 3.12 reports a symlink-resolution loop as RuntimeError.
        raise _SourceChangedError(_SOURCE_CHANGED_MESSAGE) from exc


def _verify_source(path: Path, fingerprint: str, resolved_path: Path) -> None:
    current_path = _resolve_source_path(path)
    if current_path != resolved_path or _fingerprint(path) != fingerprint:
        raise _SourceChangedError(_SOURCE_CHANGED_MESSAGE)


def _is_parquet_path(path: Path) -> bool:
    """Return True when ``path`` is a Parquet variant supported by D-Tale."""
    return path.suffix.lower() in {".parquet", ".geoparquet", ".pq"}


def _quote_identifier(name: str) -> str:
    """Quote a DuckDB identifier while preserving unusual WEPP artifact names."""
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _make_dataset_id(runid: str, config: str, rel_path: str) -> str:
    """Derive a short dataset identifier from run context and relative path."""
    raw = f"{runid}|{config}|{rel_path}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _access_serializer(*, launch: bool) -> URLSafeTimedSerializer:
    if not DTALE_INTERNAL_TOKEN:
        abort(503, description="Private D-Tale access is not configured.")
    salt = "weppcloud-dtale-private-launch-v1" if launch else "weppcloud-dtale-private-session-v1"
    return URLSafeTimedSerializer(DTALE_INTERNAL_TOKEN, salt=salt)


def _scope_cookie_name(scope: str) -> str:
    digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()[:16]
    return f"wepp_dtale_private_{digest}"


def _resource_is_public(runid: str, config: str) -> bool:
    if config == "culvert-batch":
        return False
    authorization_runid = f"batch;;{runid};;_base" if config == "batch" else runid
    try:
        wd = get_wd(authorization_runid, prefer_active=False)
    except (FileNotFoundError, OSError, RuntimeError, TypeError):
        return False
    return NoDbBase.ispublic(wd)


def _effective_access_scopes(data_id: str) -> frozenset[str]:
    scopes = DATASET_ACCESS_SCOPES.get(data_id, frozenset())
    if scopes:
        return scopes
    meta = DATASETS.get(data_id)
    if meta is not None and meta.resource_public and not _resource_is_public(meta.runid, meta.config):
        scopes = frozenset({data_id})
        DATASET_ACCESS_SCOPES[data_id] = scopes
    return scopes


def _cookie_path() -> str:
    return f"{APP_ROOT or ''}/dtale" or "/dtale"


def _has_scope_access(scope: str) -> bool:
    token = request.cookies.get(_scope_cookie_name(scope), "")
    if not token:
        return False
    try:
        payload = _access_serializer(launch=False).loads(
            token,
            max_age=DTALE_PRIVATE_ACCESS_TTL_SECONDS,
        )
    except (BadSignature, SignatureExpired):
        return False
    if not isinstance(payload, dict) or payload.get("scope") != scope:
        return False
    capability_id = payload.get("capability")
    if not isinstance(capability_id, str):
        return False
    return _reauthorize_private_scope(scope, capability_id)


def _reauthorize_private_scope(scope: str, capability_id: str) -> bool:
    capability = VIEWER_CAPABILITIES.get(capability_id)
    if capability is None or capability.scope != scope:
        return False
    if time.time() >= capability.expires_at:
        VIEWER_CAPABILITIES.pop(capability_id, None)
        return False
    try:
        from wepppy.microservices.rq_engine.auth import require_current_claims

        require_current_claims(capability.claims)
        if capability.feature_id:
            from wepppy.microservices.rq_engine.feature_access import require_feature_access

            require_feature_access(
                capability.claims,
                capability.feature_id,
                operation="inspect",
                protected_read=True,
            )
        else:
            from wepppy.microservices.rq_engine.auth import authorize_run_access

            authorize_run_access(capability.claims, capability.runid, operation="inspect")
    except Exception as exc:  # broad-except: boundary contract; authorization adapters expose service-specific errors
        logger.info("Private D-Tale reauthorization denied for %s: %s", scope, exc)
        return False
    return True


def _require_dataset_access(data_id: object) -> None:
    if not has_request_context() or request.path.startswith("/internal/"):
        return
    scopes = _effective_access_scopes(str(data_id))
    if scopes and not all(_has_scope_access(scope) for scope in scopes):
        abort(403, description="Private D-Tale dataset access required.")


def _request_private_scopes() -> frozenset[str]:
    referenced: set[str] = set()
    id_fields = {"dataid", "dataids", "leftdataid", "rightdataid", "sourceid"}

    def collect(value: object, *, reference: bool = False) -> None:
        known_data_ids = DATASET_ACCESS_SCOPES.keys() | DATASETS.keys()
        if isinstance(value, str):
            if reference and value in known_data_ids:
                referenced.add(value)
                return
            try:
                decoded = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                decoded = None
            if decoded is not None and decoded != value:
                collect(decoded, reference=reference)
            elif reference and "," in value:
                for item in value.split(","):
                    collect(item.strip(), reference=True)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                normalized_key = str(key).replace("_", "").replace("-", "").lower()
                collect(item, reference=normalized_key in id_fields)
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                collect(item, reference=reference)
            return
        if reference and isinstance(value, int) and not isinstance(value, bool):
            normalized_value = str(value)
            if normalized_value in known_data_ids:
                referenced.add(normalized_value)

    collect(request.view_args or {})
    collect(request.args.to_dict(flat=False))
    collect(request.form.to_dict(flat=False))
    if request.is_json:
        collect(request.get_json(silent=True))
    if request.endpoint == "dtale.view_main_by_name":
        data_name = (request.view_args or {}).get("data_name")
        if data_name:
            collect(_ORIGINAL_GLOBAL_STATE_GET_DATA_ID_BY_NAME(data_name))

    scopes: set[str] = set()
    for data_id in referenced:
        _require_dataset_access(data_id)
        scopes.update(DATASET_ACCESS_SCOPES.get(data_id, frozenset()))
    return frozenset(scopes)


_ORIGINAL_GLOBAL_STATE_ITEMS = getattr(global_state.items, "_wepppy_original", global_state.items)
_ORIGINAL_GLOBAL_STATE_KEYS = getattr(global_state.keys, "_wepppy_original", global_state.keys)
_ORIGINAL_GLOBAL_STATE_GET_DATA_ID_BY_NAME = getattr(
    global_state.get_data_id_by_name,
    "_wepppy_original",
    global_state.get_data_id_by_name,
)
_ORIGINAL_GLOBAL_STATE_CLEANUP = getattr(
    global_state.cleanup,
    "_wepppy_original",
    global_state.cleanup,
)


def _visible_data_id(data_id: object) -> bool:
    scopes = _effective_access_scopes(str(data_id))
    return not scopes or all(_has_scope_access(scope) for scope in scopes)


def _guarded_global_items():
    if not has_request_context() or request.path.startswith("/internal/"):
        return _ORIGINAL_GLOBAL_STATE_ITEMS()
    return [(key, value) for key, value in _ORIGINAL_GLOBAL_STATE_ITEMS() if _visible_data_id(key)]


def _guarded_global_keys():
    if not has_request_context() or request.path.startswith("/internal/"):
        return _ORIGINAL_GLOBAL_STATE_KEYS()
    return [key for key in _ORIGINAL_GLOBAL_STATE_KEYS() if _visible_data_id(key)]


def _guarded_data_id_by_name(data_name: str):
    data_id = _ORIGINAL_GLOBAL_STATE_GET_DATA_ID_BY_NAME(data_name)
    if data_id is not None and not _visible_data_id(data_id):
        return None
    return data_id


def _guarded_global_cleanup(data_id: object) -> None:
    normalized_id = str(data_id)
    _ORIGINAL_GLOBAL_STATE_CLEANUP(data_id)
    _remove_dataset_geojson_provenance(normalized_id)
    LAZY_PARQUET_DATASETS.pop(normalized_id, None)
    DATASETS.pop(normalized_id, None)
    DATASET_ACCESS_SCOPES.pop(normalized_id, None)
    _prune_viewer_capabilities(scope=normalized_id)


_guarded_global_items._wepppy_original = _ORIGINAL_GLOBAL_STATE_ITEMS
_guarded_global_keys._wepppy_original = _ORIGINAL_GLOBAL_STATE_KEYS
_guarded_data_id_by_name._wepppy_original = _ORIGINAL_GLOBAL_STATE_GET_DATA_ID_BY_NAME
_guarded_global_cleanup._wepppy_original = _ORIGINAL_GLOBAL_STATE_CLEANUP
global_state.items = _guarded_global_items
global_state.keys = _guarded_global_keys
global_state.get_data_id_by_name = _guarded_data_id_by_name
global_state.cleanup = _guarded_global_cleanup


def _resolve_target(runid: str, rel_path: str, *, config: str | None = None) -> tuple[Path, Path]:
    """Resolve ``rel_path`` inside the run directory, enforcing traversal safety."""
    if config == "culvert-batch":
        culverts_root = Path(os.getenv("CULVERTS_ROOT", "/wc1/culverts")).resolve()
        wd = _resolve_root_child(culverts_root, runid, "culvert batch")
        rel_candidates = [Path(rel_path)]
    elif config == "batch":
        batch_root = Path(os.getenv("BATCH_RUNNER_ROOT", "/wc1/batch")).resolve()
        wd = _resolve_root_child(batch_root, runid, "batch")
        rel_candidates = [Path(rel_path)]
    else:
        wd = Path(get_wd(runid)).resolve()
        rel_candidates = [Path(rel_path)]
        if config:
            rel_candidates.append(Path(config) / rel_path)

    if not wd.exists():
        abort(404, description="Run root not found.")

    for rel_candidate in rel_candidates:
        candidate = Path(os.path.abspath(str(wd / rel_candidate)))
        try:
            common = os.path.commonpath([str(wd), str(candidate)])
        except ValueError:
            abort(403, description="Path traversal detected.")
        if common != str(wd):
            abort(403, description="Path traversal detected.")
        if candidate.exists() and candidate.is_file():
            return wd, candidate

    abort(404, description="File not found.")


def _resolve_root_child(root: Path, value: str, label: str) -> Path:
    if not value or value in (".", ".."):
        abort(400, description=f"Invalid {label} identifier.")
    value_path = Path(value)
    if len(value_path.parts) != 1 or value_path.name != value:
        abort(400, description=f"Invalid {label} identifier.")
    root_path = Path(os.path.abspath(str(root)))
    candidate = Path(os.path.abspath(str(root_path / value)))
    try:
        common = os.path.commonpath([str(root_path), str(candidate)])
    except ValueError:
        abort(403, description="Path traversal detected.")
    if common != str(root_path):
        abort(403, description="Path traversal detected.")
    return candidate


def _normalize_rel(rel_path: str) -> str:
    """Convert ``rel_path`` to a forward-slash, root-less representation."""
    rel_path = rel_path.replace("\\", "/")
    return rel_path.lstrip("/")


def _load_geojson(path: Path) -> dict | None:
    """Return parsed GeoJSON from ``path`` or ``None`` if parsing fails."""
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:  # pragma: no cover - defensive: invalid JSON should not crash loader
        logger.exception("Failed to parse geojson at %s", path)
    return None


def _infer_featureidkey(properties: Iterable[str], preferred: Iterable[str] | None = None) -> str | None:
    """Pick a feature identifier column from ``properties`` using preferred aliases."""
    prop_set = set(properties)
    candidates: list[str] = []
    if preferred:
        candidates.extend([c for c in preferred if c])
    candidates.extend(
        [
            "wepp_id",
            "WeppID",
            "field_id",
            "FieldID",
            "sub_field_id",
            "SubFieldID",
            "topaz_id",
            "TopazID",
            "channel_id",
            "ChannelID",
            "reach_id",
            "ReachID",
            "id",
            "ID",
        ]
    )
    for candidate in candidates:
        if candidate in prop_set:
            return candidate
    return None


def _register_geojson_asset(
    runid: str,
    slug: str,
    path: Path | str | None,
    *,
    data_id: str | None = None,
    label: str | None = None,
    preferred_keys: Iterable[str] | None = None,
    make_default: bool = False,
    loc_candidates: Iterable[str] | None = None,
    property_aliases: Iterable[tuple[str, str]] | None = None,
) -> tuple[str | None, str | None]:
    """Register a GeoJSON overlay with D-Tale, returning the key and feature id."""
    if dtale_custom_geojson is None:
        return (None, None)
    geojson_key = f"{runid}-{slug}"
    if not path:
        _remove_geojson_asset(geojson_key)
        return (None, None)
    path = Path(path)
    try:
        resolved_path = _resolve_source_path(path)
        fingerprint = _fingerprint(path)
    except (OSError, _SourceChangedError):
        logger.debug("GeoJSON asset unavailable for %s at %s", slug, path, exc_info=True)
        _remove_geojson_asset(geojson_key)
        return (None, None)

    existing_entry = next(
        (entry for entry in dtale_custom_geojson.CUSTOM_GEOJSON if entry.get("key") == geojson_key),
        None,
    )
    if REGISTERED_GEOJSON.get(geojson_key) == fingerprint and existing_entry:
        featureidkey = existing_entry.get("featureidkey")
    else:
        data = _load_geojson(path)
        if not data:
            _remove_geojson_asset(geojson_key)
            return (None, None)
        try:
            _verify_source(path, fingerprint, resolved_path)
        except _SourceChangedError:
            logger.debug("GeoJSON asset changed during load: %s", path, exc_info=True)
            _remove_geojson_asset(geojson_key)
            return (None, None)

        properties: list[str] = []
        record = {
            "key": geojson_key,
            "data": data,
            "filename": path.name,
            "time": pd.Timestamp("now"),
            "type": data.get("type"),
            "label": label or slug.replace("_", " ").title(),
            "_fingerprint": fingerprint,
            "loc_candidates": tuple(loc_candidates or ()),
        }

        if record["type"] == "FeatureCollection":
            features = data.get("features") or []
            if features:
                props = features[0].get("properties") or {}
                properties = sorted(props.keys())
                if property_aliases:
                    alias_pairs = list(property_aliases)
                    for feature in features:
                        props = feature.get("properties") or {}
                        for requested_src, alias in alias_pairs:
                            src_key = next(
                                (key for key in props.keys() if key.lower() == requested_src.lower()),
                                None,
                            )
                            if src_key is not None and alias not in props:
                                src_value = props[src_key]
                                props[alias] = "" if src_value is None else str(src_value)
                            elif alias in props and props[alias] is not None:
                                props[alias] = str(props[alias])
                        for key, value in list(props.items()):
                            if value is not None and not isinstance(value, str):
                                props[key] = str(value)
                        feature["properties"] = props
                    if features:
                        properties = sorted({
                            key for feature in features for key in (feature.get("properties") or {}).keys()
                        })
                if properties:
                    record["properties"] = properties

        featureidkey = _infer_featureidkey(properties, preferred_keys) if properties else None
        if featureidkey:
            record["featureidkey"] = featureidkey

        dtale_custom_geojson.CUSTOM_GEOJSON = [
            entry for entry in dtale_custom_geojson.CUSTOM_GEOJSON if entry.get("key") != geojson_key
        ]
        dtale_custom_geojson.CUSTOM_GEOJSON.append(record)
        REGISTERED_GEOJSON[geojson_key] = fingerprint
        existing_entry = record

    # The upstream overlay record is shared across datasets; keep all of its
    # choice/default references on the same feature-ID schema.
    for related_id, choices in list(MAP_CHOICES.items()):
        matching = [entry for entry in choices if entry[1] == geojson_key]
        if matching:
            MAP_CHOICES[related_id] = [entry for entry in choices if entry[1] != geojson_key] + [
                (matching[0][0], geojson_key, featureidkey)
            ]
    for defaults in MAP_DEFAULTS.values():
        if defaults.get("geojson") == geojson_key:
            defaults["featureidkey"] = featureidkey or "id"
            defaults["loc_candidates"] = tuple(loc_candidates or ())
    if data_id:
        entry = (label or slug, geojson_key, featureidkey)
        choices = [choice for choice in MAP_CHOICES.get(data_id, []) if choice[1] != geojson_key]
        MAP_CHOICES[data_id] = [*choices, entry]
        defaults = MAP_DEFAULTS.get(data_id)
        if make_default or defaults is None:
            MAP_DEFAULTS[data_id] = {
                "map_type": "choropleth",
                "loc_mode": "geojson-id",
                "geojson": geojson_key,
                "featureidkey": featureidkey or "id",
                "loc_candidates": tuple(loc_candidates or ()),
            }

    return (geojson_key, featureidkey)

def _remove_geojson_asset(geojson_key: str) -> None:
    """Drop only the unavailable overlay and references to it."""
    REGISTERED_GEOJSON.pop(geojson_key, None)
    GEOJSON_ACCESS_SCOPES.pop(geojson_key, None)
    if dtale_custom_geojson is not None:
        dtale_custom_geojson.CUSTOM_GEOJSON = [
            entry for entry in dtale_custom_geojson.CUSTOM_GEOJSON
            if entry.get("key") != geojson_key
        ]
    records = dtale_custom_geojson.CUSTOM_GEOJSON if dtale_custom_geojson is not None else []
    for data_id, choices in list(MAP_CHOICES.items()):
        retained = [entry for entry in choices if entry[1] != geojson_key]
        if retained:
            MAP_CHOICES[data_id] = retained
        else:
            MAP_CHOICES.pop(data_id, None)
    for data_id, defaults in list(MAP_DEFAULTS.items()):
        if defaults.get("geojson") == geojson_key:
            MAP_DEFAULTS.pop(data_id)
            for _, key, featureidkey in MAP_CHOICES.get(data_id, []):
                record = next((entry for entry in records if entry.get("key") == key), None)
                if record is not None:
                    MAP_DEFAULTS[data_id] = {
                        "map_type": "choropleth", "loc_mode": "geojson-id",
                        "geojson": key, "featureidkey": featureidkey or "id",
                        "loc_candidates": record.get("loc_candidates", ()),
                    }
                    break


def _remove_dataset_geojson_provenance(data_id: str) -> None:
    candidate_keys = {entry[1] for entry in MAP_CHOICES.pop(data_id, [])}
    MAP_DEFAULTS.pop(data_id, None)
    for geojson_key, scopes in list(GEOJSON_ACCESS_SCOPES.items()):
        if data_id in scopes:
            _remove_geojson_asset(geojson_key)
            candidate_keys.discard(geojson_key)
    referenced_keys = {
        entry[1]
        for choices in MAP_CHOICES.values()
        for entry in choices
    }
    for geojson_key in candidate_keys - referenced_keys:
        if geojson_key not in GEOJSON_ACCESS_SCOPES:
            _remove_geojson_asset(geojson_key)


def _ensure_geojson_assets(runid: str, wd: Path, data_id: str | None) -> None:
    """Populate default GeoJSON overlays for the given run/dataset combo."""
    if dtale_custom_geojson is None:
        return
    def _register(
        slug: str,
        path: Path | str | None,
        *,
        label: str | None = None,
        preferred_keys: Iterable[str] | None = None,
        make_default: bool = False,
        loc_candidates: Iterable[str] | None = None,
        property_aliases: Iterable[tuple[str, str]] | None = None,
    ):
        defaults_set = data_id in MAP_DEFAULTS if data_id else False
        key, featureidkey = _register_geojson_asset(
            runid,
            slug,
            path,
            data_id=data_id,
            label=label,
            preferred_keys=preferred_keys,
            make_default=make_default or not defaults_set,
            loc_candidates=loc_candidates,
            property_aliases=property_aliases,
        )
        return key, featureidkey

    watershed = None
    try:
        watershed = Watershed.getInstance(str(wd))
    except Exception:  # pragma: no cover - best effort; missing state should not block loads
        logger.debug("Unable to resolve watershed geojson assets for %s", runid, exc_info=True)

    if watershed:
        _register(
            "subcatchments",
            watershed.subwta_shp,
            label="Subcatchments",
            preferred_keys=("wepp_id", "TopazID"),
            make_default=True,
            loc_candidates=("topaz_id", "TopazID", "wepp_id", "WeppID"),
            property_aliases=(("WeppID", "wepp_id"), ("TopazID", "topaz_id")),
        )
        _register(
            "channels",
            watershed.channels_shp,
            label="Channels",
            preferred_keys=("wepp_id", "TopazID", "channel_id", "ReachID"),
            loc_candidates=(
                "channel_id",
                "ChannelID",
                "reach_id",
                "ReachID",
                "wepp_id",
                "WeppID",
                "TopazID",
            ),
            property_aliases=(
                ("WeppID", "wepp_id"),
                ("TopazID", "topaz_id"),
                ("ChannelID", "channel_id"),
            ),
        )
    else:
        _remove_geojson_asset(f"{runid}-subcatchments")
        _remove_geojson_asset(f"{runid}-channels")

    if AgFields is None:
        _remove_geojson_asset(f"{runid}-ag-fields-boundaries")
        _remove_geojson_asset(f"{runid}-ag-fields-subfields")
        return

    try:
        ag_fields = AgFields.tryGetInstance(str(wd), allow_nonexistent=True, ignore_lock=True)
    except Exception:  # pragma: no cover - optional module, fallthrough
        logger.debug("Unable to resolve AgFields instance for %s", runid, exc_info=True)
        _remove_geojson_asset(f"{runid}-ag-fields-boundaries")
        _remove_geojson_asset(f"{runid}-ag-fields-subfields")
        return

    if not ag_fields:
        _remove_geojson_asset(f"{runid}-ag-fields-boundaries")
        _remove_geojson_asset(f"{runid}-ag-fields-subfields")
        return

    # Canonical boundary file (fields.WGS.geojson)
    if ag_fields.field_boundaries_geojson:
        boundary_path = Path(ag_fields.ag_fields_dir) / ag_fields.field_boundaries_geojson
        _register(
            "ag-fields-boundaries",
            boundary_path,
            label="Ag Fields (Fields)",
            preferred_keys=("field_id", "field_name"),
            loc_candidates=("field_id", "FieldID", "field_name", "FieldName", "wepp_id", "WeppID"),
            property_aliases=(
                ("FieldID", "field_id"),
                ("FieldName", "field_name"),
                ("WeppID", "wepp_id"),
            ),
        )
    else:
        _remove_geojson_asset(f"{runid}-ag-fields-boundaries")

    _register(
        "ag-fields-subfields",
        getattr(ag_fields, "sub_fields_wgs_geojson", None),
        label="Ag Fields (Subfields)",
        preferred_keys=("sub_field_id", "wepp_id", "field_id"),
        loc_candidates=(
            "sub_field_id",
            "SubFieldID",
            "field_id",
            "FieldID",
            "wepp_id",
            "WeppID",
        ),
        property_aliases=(
            ("SubFieldID", "sub_field_id"),
            ("FieldID", "field_id"),
            ("WeppID", "wepp_id"),
        ),
    )


def _postprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, dtypes, and identifier aliases for D-Tale."""
    df.columns = [str(col) for col in df.columns]
    try:
        df = df.convert_dtypes(dtype_backend="numpy_nullable")
    except TypeError:
        df = df.convert_dtypes()
    for source, alias in _IDENTIFIER_STRING_ALIASES:
        if source in df.columns and alias not in df.columns:
            try:
                df[alias] = df[source].astype("string")
            except Exception:
                df[alias] = df[source].astype(str)
    return df


def _read_feather(path: Path) -> pd.DataFrame:
    """Read a Feather/Arrow file into a post-processed DataFrame."""
    df = pd.read_feather(path)
    return _postprocess_dataframe(df)


def _read_csv(path: Path, *, sep: str = ",", compression: str | None = None) -> pd.DataFrame:
    """Load CSV/TSV data with optional compression and post-process the frame."""
    df = pd.read_csv(path, sep=sep, compression=compression)
    return _postprocess_dataframe(df)


def _read_pickle(path: Path) -> pd.DataFrame:
    """Load a pickle payload and coerce it into a DataFrame when necessary."""
    df = pd.read_pickle(path)
    return _postprocess_dataframe(pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df)


READERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    ".feather": _read_feather,
    ".arrow": _read_feather,
    ".csv": _read_csv,
    ".tsv": lambda p: _read_csv(p, sep="\t"),
    ".pkl": _read_pickle,
    ".pickle": _read_pickle,
}


def _load_dataframe(path: Path) -> pd.DataFrame:
    """Dispatch to the appropriate reader for ``path`` based on suffix."""
    name = path.name.lower()
    if name.endswith(".csv.gz"):
        return _read_csv(path, compression="gzip")
    if name.endswith(".tsv.gz"):
        return _read_csv(path, sep="\t", compression="gzip")
    reader = READERS.get(path.suffix.lower())
    if not reader:
        abort(415, description=f"Unsupported file extension: {path.suffix or '<none>'}")
    return reader(path)


class LazyParquetDtaleInstance:
    """Page a Parquet file for D-Tale without retaining a full pandas DataFrame."""

    def __init__(
        self,
        path: Path,
        *,
        compiled_filter: CompiledParquetFilter | None = None,
    ) -> None:
        self.path = Path(path)
        self.compiled_filter = compiled_filter
        self._source_path = _resolve_source_path(self.path)
        self._source_fingerprint = _fingerprint(self.path)
        try:
            self._schema = pq.read_schema(self.path)
        finally:
            self._assert_current()
        self._base_columns = [field.name for field in self._schema]
        self._rows: int | None = None
        self._base_df: pd.DataFrame | None = None

    def _assert_current(self) -> None:
        _verify_source(self.path, self._source_fingerprint, self._source_path)

    @property
    def base_columns(self) -> list[str]:
        return list(self._base_columns)

    @property
    def alias_to_source(self) -> dict[str, str]:
        return {
            alias: source
            for source, alias in _IDENTIFIER_STRING_ALIASES
            if source in self._base_columns
        }

    def rows(self, **kwargs) -> int:
        if kwargs:
            unsupported = ", ".join(sorted(kwargs))
            raise ValueError(f"Unsupported lazy parquet row-count options: {unsupported}")
        self._assert_current()
        if self._rows is None:
            try:
                if self.compiled_filter is None:
                    metadata = pq.ParquetFile(self.path).metadata
                    rows = int(metadata.num_rows)
                else:
                    rows = count_filtered_parquet_rows(self.path, self.compiled_filter)
            finally:
                self._assert_current()
            self._rows = rows
        return self._rows

    @property
    def base_df(self) -> pd.DataFrame:
        if self._base_df is None:
            self._base_df = self.load_data(row_range=[0, 1], columns=self._base_columns)
        else:
            self._assert_current()
        return self._base_df

    @property
    def is_large(self) -> bool:
        return self.rows() > 1_000_000 or len(self._base_columns) > 50

    @property
    def data(self) -> pd.DataFrame:
        raise RuntimeError("Lazy parquet datasets cannot be loaded as full pandas DataFrames.")

    def _resolve_columns_to_read(self, columns: Iterable[str] | None) -> list[str]:
        if not columns:
            return self.base_columns

        alias_to_source = self.alias_to_source
        resolved: list[str] = []
        for column in columns:
            source = column if column in self._base_columns else alias_to_source.get(column)
            if source and source not in resolved:
                resolved.append(source)
        return resolved or self.base_columns

    def _resolve_sort_terms(self, sort: list[Any] | None) -> list[str]:
        if not sort:
            return []
        alias_to_source = self.alias_to_source
        terms: list[str] = []
        for item in sort:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            column = str(item[0])
            direction = str(item[1]).upper()
            if direction not in {"ASC", "DESC"}:
                continue
            source = column if column in self._base_columns else alias_to_source.get(column)
            if source:
                terms.append(f"{_quote_identifier(source)} {direction}")
        return terms

    def _select_sql(
        self,
        columns: list[str],
        *,
        row_range: list[int] | tuple[int, int] | None,
        sort: list[Any] | None,
    ) -> tuple[str, list[Any]]:
        select_list = ", ".join(_quote_identifier(column) for column in columns)
        sql = f"SELECT {select_list} FROM read_parquet(?)"
        params: list[Any] = [str(self.path)]
        if self.compiled_filter is not None:
            sql = f"{sql} WHERE {self.compiled_filter.where_sql}"
            params.extend(self.compiled_filter.params)
        sort_terms = self._resolve_sort_terms(sort)
        if sort_terms:
            sql = f"{sql} ORDER BY {', '.join(sort_terms)}"
        if row_range is not None:
            start = max(int(row_range[0]), 0)
            end = max(int(row_range[1]), start)
            sql = f"{sql} LIMIT ? OFFSET ?"
            params.extend([end - start, start])
        return sql, params

    def load_data(
        self,
        row_range: list[int] | tuple[int, int] | None = None,
        columns: Iterable[str] | None = None,
        sort: list[Any] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        if kwargs:
            unsupported = ", ".join(sorted(kwargs))
            raise ValueError(f"Unsupported lazy parquet load options: {unsupported}")
        columns_to_read = self._resolve_columns_to_read(columns)
        sql, params = self._select_sql(columns_to_read, row_range=row_range, sort=sort)
        self._assert_current()
        try:
            with duckdb.connect() as conn:
                df = conn.execute(sql, params).fetchdf()
        finally:
            self._assert_current()
        df = _postprocess_dataframe(df)
        if columns:
            ordered_columns = [column for column in columns if column in df.columns]
            if ordered_columns:
                df = df[ordered_columns]
        return df


def _initialize_lazy_parquet_dataset(
    data_id: str,
    display_name: str,
    path: Path,
    *,
    compiled_filter: CompiledParquetFilter | None = None,
) -> DtaleData:
    """Create a D-Tale shell backed by lazy Parquet page reads."""
    lazy_instance = LazyParquetDtaleInstance(path, compiled_filter=compiled_filter)
    sample_df = lazy_instance.base_df
    instance = startup(
        url=DTALE_BASE_URL,
        data=sample_df,
        data_id=data_id,
        name=display_name,
        ignore_duplicate=True,
        allow_cell_edits=False,
        force_save=True,
        app_root=APP_ROOT,
        is_proxy=IS_PROXY,
        hide_header_editor=True,
        lock_header_menu=True,
    )
    LAZY_PARQUET_DATASETS[data_id] = lazy_instance
    try:
        dtypes_state = build_dtypes_state(sample_df)
    except (AttributeError, TypeError, ValueError):
        logger.exception("Failed to build lazy parquet dtype state for %s", data_id)
    else:
        for col in dtypes_state:
            if col["index"] >= 100:
                col["visible"] = False
        global_state.set_dtypes(data_id, dtypes_state)
    return instance


def _initialize_dtale_dataset(data_id: str, display_name: str, df: pd.DataFrame) -> DtaleData:
    """Create or reuse a D-Tale instance for ``data_id`` and seed global state."""
    instance = startup(
        url=DTALE_BASE_URL,
        data=df,
        data_id=data_id,
        name=display_name,
        ignore_duplicate=True,
        allow_cell_edits=ALLOW_CELL_EDITS,
        force_save=True,
        app_root=APP_ROOT,
        is_proxy=IS_PROXY,
    )

    if global_state.get_data(data_id) is None:
        global_state.set_data(data_id, df)

    if global_state.get_dtypes(data_id) is None:
        try:
            fallback_dtypes = build_dtypes_state(df)
        except Exception:  # pragma: no cover - defensive fallback
            logger.exception("Failed to build fallback dtype state for %s", data_id)
        else:
            global_state.set_dtypes(data_id, fallback_dtypes)

    return instance


def _discard_dataset(data_id: str) -> None:
    global_state.cleanup(data_id)
    LAZY_PARQUET_DATASETS.pop(data_id, None)
    DATASETS.pop(data_id, None)
    DATASET_ACCESS_SCOPES.pop(data_id, None)
    _prune_viewer_capabilities(scope=data_id)


def _set_dataset_access_scopes(data_id: str, scopes: frozenset[str]) -> None:
    if scopes:
        DATASET_ACCESS_SCOPES[data_id] = scopes
    else:
        DATASET_ACCESS_SCOPES.pop(data_id, None)


def _prune_viewer_capabilities(*, scope: str | None = None) -> None:
    now = time.time()
    for capability_id, capability in list(VIEWER_CAPABILITIES.items()):
        if capability.expires_at <= now or capability.scope == scope:
            VIEWER_CAPABILITIES.pop(capability_id, None)


if dtale_custom_geojson is not None:
    _ORIGINAL_GET_CUSTOM_GEOJSON = getattr(
        dtale_custom_geojson.get_custom_geojson,
        "_wepppy_original",
        dtale_custom_geojson.get_custom_geojson,
    )

    def _geojson_resource_is_visible(geojson_key: str) -> bool:
        explicit_scopes = GEOJSON_ACCESS_SCOPES.get(geojson_key, frozenset())
        if explicit_scopes and (
            not has_request_context()
            or not all(_has_scope_access(scope) for scope in explicit_scopes)
        ):
            return False
        associated_ids = {
            data_id
            for data_id, choices in MAP_CHOICES.items()
            if any(entry[1] == geojson_key for entry in choices)
        }
        if not associated_ids:
            return True
        for data_id in associated_ids:
            meta = DATASETS.get(data_id)
            if meta is not None and meta.resource_public and _resource_is_public(meta.runid, meta.config):
                continue
            if not has_request_context() or meta is None or not _visible_data_id(data_id):
                return False
        return True

    def _get_visible_custom_geojson(geojson_id=None):
        if geojson_id is None:
            return [
                entry
                for entry in dtale_custom_geojson.CUSTOM_GEOJSON
                if _geojson_resource_is_visible(entry.get("key", ""))
            ]
        entry = _ORIGINAL_GET_CUSTOM_GEOJSON(geojson_id)
        if entry is None or not _geojson_resource_is_visible(geojson_id):
            return None
        return entry

    _get_visible_custom_geojson._wepppy_original = _ORIGINAL_GET_CUSTOM_GEOJSON
    dtale_custom_geojson.get_custom_geojson = _get_visible_custom_geojson

    def _add_uniquely_keyed_geojson(geojson_key, geojson):
        suffix = 0
        while _ORIGINAL_GET_CUSTOM_GEOJSON(f"{geojson_key}{suffix or ''}"):
            suffix += 1
        unique_key = f"{geojson_key}{suffix + 1 if suffix else ''}"
        geojson["key"] = unique_key
        dtale_custom_geojson.CUSTOM_GEOJSON.append(geojson)
        return unique_key

    dtale_custom_geojson.add_custom_geojson = _add_uniquely_keyed_geojson

    _ORIGINAL_LOAD_GEOJSON = getattr(
        dtale_custom_geojson.load_geojson,
        "_wepppy_original",
        dtale_custom_geojson.load_geojson,
    )

    def _load_scoped_geojson(contents, filename):
        geojson_key = _ORIGINAL_LOAD_GEOJSON(contents, filename)
        if geojson_key and has_request_context():
            private_scopes = {
                scope
                for scopes in DATASET_ACCESS_SCOPES.values()
                for scope in scopes
                if _has_scope_access(scope)
            }
            if private_scopes:
                GEOJSON_ACCESS_SCOPES[geojson_key] = frozenset(private_scopes)
        return geojson_key

    _load_scoped_geojson._wepppy_original = _ORIGINAL_LOAD_GEOJSON
    dtale_custom_geojson.load_geojson = _load_scoped_geojson

    from dtale.dash_application.layout import layout as dtale_layout

    if not getattr(dtale_layout.charts_layout, "_wepppy_patched", False):
        _ORIGINAL_CHARTS_LAYOUT = dtale_layout.charts_layout
        _ORIGINAL_BUILD_GEOJSON_UPLOAD = dtale_custom_geojson.build_geojson_upload

        def _charts_layout_with_defaults(df, settings, **inputs):
            merged_inputs = dict(inputs)
            data_id = merged_inputs.get("data_id")
            defaults = None
            if data_id is not None:
                dtale_custom_geojson.ACTIVE_DATA_ID = data_id
                defaults = MAP_DEFAULTS.get(data_id)
            if defaults:
                for key in ("map_type", "loc_mode", "geojson", "featureidkey"):
                    value = defaults.get(key)
                    if value is not None:
                        merged_inputs.setdefault(key, value)
                loc_candidates = defaults.get("loc_candidates") or ()
                if not merged_inputs.get("loc"):
                    for candidate in loc_candidates:
                        if candidate in df.columns:
                            merged_inputs["loc"] = candidate
                            break
            map_val = merged_inputs.get("map_val")
            if map_val and map_val not in df.columns:
                merged_inputs["map_val"] = None
            try:
                return _ORIGINAL_CHARTS_LAYOUT(df, settings, **merged_inputs)
            finally:
                dtale_custom_geojson.ACTIVE_DATA_ID = None

        def _build_geojson_upload_with_defaults(loc_mode, geojson_key=None, featureidkey=None):
            active_id = getattr(dtale_custom_geojson, "ACTIVE_DATA_ID", None)
            defaults = MAP_DEFAULTS.get(active_id, {}) if active_id else {}
            if loc_mode == "geojson-id":
                geojson_key = defaults.get("geojson", geojson_key)
                featureidkey = defaults.get("featureidkey", featureidkey)

            components = _ORIGINAL_BUILD_GEOJSON_UPLOAD(loc_mode, geojson_key, featureidkey)

            relevant_keys: list[str] = []
            label_lookup: dict[str, str] = {}
            feature_lookup: dict[str, str | None] = {}
            if active_id and active_id in MAP_CHOICES:
                for label, key, fid in MAP_CHOICES[active_id]:
                    relevant_keys.append(key)
                    label_lookup[key] = label
                    feature_lookup[key] = fid
            elif active_id:
                relevant_keys = [
                    entry.get("key", "")
                    for entry in dtale_custom_geojson.get_custom_geojson()
                    if entry.get("key", "").startswith(f"{active_id}-")
                ]

            def _update_dropdown(node):
                if hasattr(node, "children"):
                    children = node.children
                    if isinstance(children, list):
                        for child in children:
                            _update_dropdown(child)
                    elif children is not None:
                        _update_dropdown(children)
                if dtale_dcc is not None and isinstance(node, dtale_dcc.Dropdown):
                    if node.id == "geojson-dropdown":
                        entries = dtale_custom_geojson.get_custom_geojson()
                        if relevant_keys:
                            entries = [entry for entry in entries if entry.get("key") in relevant_keys]
                        node.options = [
                            {
                                "label": label_lookup.get(entry.get("key"), entry.get("label", entry.get("key"))),
                                "value": entry.get("key"),
                            }
                            for entry in entries
                        ]
                        if loc_mode == "geojson-id" and defaults.get("geojson"):
                            node.value = defaults["geojson"]
                    elif node.id == "featureidkey-dropdown":
                        if defaults.get("featureidkey"):
                            node.value = defaults["featureidkey"]
                        elif defaults.get("geojson") in feature_lookup and feature_lookup[defaults["geojson"]]:
                            node.value = feature_lookup[defaults["geojson"]]

            for component in components:
                _update_dropdown(component)
            return components

        dtale_layout.charts_layout = _charts_layout_with_defaults
        dtale_layout.charts_layout._wepppy_patched = True
        dtale_custom_geojson.build_geojson_upload = _build_geojson_upload_with_defaults
        dtale_custom_geojson.build_geojson_upload._wepppy_patched = True
        dtale_custom_geojson.ACTIVE_DATA_ID = None

    if not getattr(dtale_layout.build_map_options, "_wepppy_patched", False):
        _ORIGINAL_BUILD_MAP_OPTIONS = dtale_layout.build_map_options

        def _build_map_options_with_candidates(df, type="choropleth", loc=None, lat=None, lon=None, map_val=None):
            if df is None:
                return [], [], [], []
            loc_opts, lat_opts, lon_opts, val_opts = _ORIGINAL_BUILD_MAP_OPTIONS(
                df, type=type, loc=loc, lat=lat, lon=lon, map_val=map_val
            )
            active_id = getattr(dtale_custom_geojson, "ACTIVE_DATA_ID", None)
            defaults = MAP_DEFAULTS.get(active_id, {}) if active_id else {}
            if defaults:
                candidates = defaults.get("loc_candidates") or ()
                existing_values = {opt.get("value") for opt in loc_opts}
                for candidate in candidates:
                    if candidate in df.columns and candidate not in existing_values:
                        loc_opts.append(dtale_layout.build_option(candidate))
            return loc_opts, lat_opts, lon_opts, val_opts

        dtale_layout.build_map_options = _build_map_options_with_candidates
        dtale_layout.build_map_options._wepppy_patched = True

    if dtale_charts is not None and not getattr(dtale_charts.build_choropleth, "_wepppy_patched", False):
        _ORIGINAL_BUILD_CHOROPLETH = dtale_charts.build_choropleth

        def _ensure_geo_layout(layout_obj):
            if layout_obj.geo is None:
                layout_obj.update(geo=dict())
            return layout_obj.geo

        def _ensure_mapbox_layout(layout_obj):
            if layout_obj.mapbox is None:
                layout_obj.update(mapbox=dict())
            return layout_obj.mapbox

        def _build_choropleth_with_fitbounds(inputs, raw_data, layout):
            props = dtale_charts.get_map_props(inputs)
            if props.loc_mode == "geojson-id":
                geo_layout = _ensure_geo_layout(layout)
                geo_layout.fitbounds = "locations"
            return _ORIGINAL_BUILD_CHOROPLETH(inputs, raw_data, layout)

        dtale_charts.build_choropleth = _build_choropleth_with_fitbounds
        dtale_charts.build_choropleth._wepppy_patched = True

    if dtale_charts is not None and not getattr(dtale_charts.build_scattergeo, "_wepppy_patched", False):
        _ORIGINAL_BUILD_SCATTERGEO = dtale_charts.build_scattergeo

        def _build_scattergeo_with_fitbounds(inputs, raw_data, layout):
            props = dtale_charts.get_map_props(inputs)
            if props.loc_mode == "geojson-id":
                geo_layout = _ensure_geo_layout(layout)
                geo_layout.fitbounds = "locations"
            return _ORIGINAL_BUILD_SCATTERGEO(inputs, raw_data, layout)

        dtale_charts.build_scattergeo = _build_scattergeo_with_fitbounds
        dtale_charts.build_scattergeo._wepppy_patched = True

    if dtale_charts is not None and not getattr(dtale_charts.build_mapbox, "_wepppy_patched", False):
        _ORIGINAL_BUILD_MAPBOX = dtale_charts.build_mapbox

        def _build_mapbox_with_fitbounds(inputs, raw_data, layout):
            mapbox_layout = _ensure_mapbox_layout(layout)
            mapbox_layout.fitbounds = "locations"
            return _ORIGINAL_BUILD_MAPBOX(inputs, raw_data, layout)

        dtale_charts.build_mapbox = _build_mapbox_with_fitbounds
        dtale_charts.build_mapbox._wepppy_patched = True


app = build_app(reaper_on=False, app_root=APP_ROOT)


@app.errorhandler(_SourceChangedError)
def _source_changed_response(error):
    return jsonify({
        "error": {"code": "changed_source", "message": str(error)},
        "description": str(error),
    }), 409


def _format_lazy_rows(
    data_id: str,
    lazy_instance: LazyParquetDtaleInstance,
    ids: list[str] | None,
) -> tuple[dict[int, dict[str, object]], int]:
    curr_settings = global_state.get_settings(data_id) or {}
    curr_locked = curr_settings.get("locked", [])
    params = dtale_views.retrieve_grid_params(request)
    sort = params.get("sort")
    if curr_settings.get("sortInfo") != sort:
        curr_settings = dict(curr_settings)
        if sort is not None:
            curr_settings["sortInfo"] = sort
        else:
            curr_settings.pop("sortInfo", None)
        global_state.set_settings(data_id, curr_settings)
    col_types = global_state.get_dtypes(data_id) or []
    visible_col_types = [c for c in col_types if c.get("visible", True)]
    visible_columns = [c["name"] for c in visible_col_types]
    columns_to_load = list(dict.fromkeys(curr_locked + visible_columns))
    formatter = dtale_views.grid_formatter(
        visible_col_types,
        nan_display=curr_settings.get("nanDisplay", "nan"),
    )
    total = lazy_instance.rows()

    results: dict[int, dict[str, object]] = {}
    if total == 0 or ids is None:
        return results, total

    for sub_range_value in ids:
        sub_range = list(map(int, sub_range_value.split("-")))
        if len(sub_range) == 1:
            start = sub_range[0]
            end = start
        else:
            start, end = sub_range
        if start >= total:
            continue
        bounded_end = total - 1 if end >= total else end
        data = lazy_instance.load_data(
            row_range=[start, bounded_end + 1],
            columns=columns_to_load,
            sort=sort,
        )
        data, _ = dtale_views.format_data(data)
        data = data[curr_locked + [c for c in data.columns if c not in curr_locked]]
        formatted_rows = formatter.format_dicts(data.itertuples())
        for row_index, row in zip(range(start, bounded_end + 1), formatted_rows):
            results[row_index] = dtale_views.dict_merge({dtale_views.IDX_COL: row_index}, row)
    return results, total


def _lazy_parquet_get_data(data_id: str):
    lazy_instance = LAZY_PARQUET_DATASETS.get(data_id)
    if lazy_instance is None:
        return _ORIGINAL_DTALE_GET_DATA(data_id)

    export = dtale_views.get_bool_arg(request, "export")
    ids = dtale_views.get_json_arg(request, "ids")
    if export:
        abort(501, description="Lazy parquet D-Tale export is not supported; use browse CSV export.")
    if not export and ids is None:
        return jsonify({})

    try:
        results, total = _format_lazy_rows(data_id, lazy_instance, ids)
    except _SourceChangedError as exc:
        # Upstream grid transport discards non-2xx bodies; use its visible
        # error envelope without returning successful row data.
        return jsonify({"success": False, "error": str(exc), "code": "changed_source"})
    return_data = {
        "results": results,
        "columns": [
            {"name": dtale_views.IDX_COL, "dtype": "int64", "visible": True},
            *global_state.get_dtypes(data_id),
        ],
        "total": total,
        "final_query": None,
    }
    return jsonify(return_data)


_ORIGINAL_DTALE_GET_DATA = app.view_functions.get("dtale.get_data")
if _ORIGINAL_DTALE_GET_DATA is not None and not getattr(_ORIGINAL_DTALE_GET_DATA, "_wepppy_patched", False):
    _lazy_parquet_get_data._wepppy_patched = True
    app.view_functions["dtale.get_data"] = _lazy_parquet_get_data


@app.route("/health")
def health():
    """Return a simple liveness payload for monitoring."""
    return jsonify({"status": "ok"})


@app.before_request
def _authorize_private_dataset_request():
    if request.path == "/health" or request.path.startswith("/internal/") or request.path.startswith("/dtale/access/"):
        return None
    g.dtale_existing_ids = set(_ORIGINAL_GLOBAL_STATE_KEYS())
    g.dtale_private_scopes = _request_private_scopes()
    return None


@app.after_request
def _propagate_private_dataset_scope(response):
    existing = getattr(g, "dtale_existing_ids", None)
    scopes = getattr(g, "dtale_private_scopes", frozenset())
    if existing is not None and scopes:
        for data_id in set(_ORIGINAL_GLOBAL_STATE_KEYS()) - existing:
            DATASET_ACCESS_SCOPES[str(data_id)] = frozenset(scopes)
    return response


@app.get("/dtale/access/<ticket>")
def private_dataset_access(ticket: str):
    try:
        payload = _access_serializer(launch=True).loads(
            ticket,
            max_age=DTALE_PRIVATE_LAUNCH_TTL_SECONDS,
        )
    except SignatureExpired:
        abort(410, description="Private D-Tale launch expired; reopen it from browse.")
    except BadSignature:
        abort(403, description="Invalid private D-Tale launch.")
    if not isinstance(payload, dict):
        abort(403, description="Invalid private D-Tale launch.")
    data_id = str(payload.get("data_id") or "")
    scope = str(payload.get("scope") or "")
    capability_id = str(payload.get("capability") or "")
    if not data_id or scope not in DATASET_ACCESS_SCOPES.get(data_id, frozenset()):
        abort(403, description="Private D-Tale dataset is unavailable.")
    if not capability_id or not _reauthorize_private_scope(scope, capability_id):
        abort(403, description="Private D-Tale authorization is no longer valid.")

    session_token = _access_serializer(launch=False).dumps(
        {"scope": scope, "capability": capability_id}
    )
    target = DtaleData(data_id, DTALE_BASE_URL, is_proxy=IS_PROXY, app_root=APP_ROOT).build_main_url()
    if IS_PROXY and not target.startswith("/"):
        target = f"/{target}"
    response = redirect(target, code=303)
    response.set_cookie(
        _scope_cookie_name(scope),
        session_token,
        max_age=DTALE_PRIVATE_ACCESS_TTL_SECONDS,
        secure=request.headers.get("X-Forwarded-Proto", request.scheme).lower() == "https",
        httponly=True,
        samesite="Lax",
        path=_cookie_path(),
    )
    return response


def _verify_token() -> None:
    """Abort requests when the ``X-DTALE-TOKEN`` does not match configuration."""
    if not DTALE_INTERNAL_TOKEN:
        return
    supplied = request.headers.get("X-DTALE-TOKEN", "")
    if supplied != DTALE_INTERNAL_TOKEN:
        abort(403, description="Forbidden.")


def _build_instance_response(
    data_id: str,
    instance: DtaleData,
    meta: DatasetMeta,
    *,
    access_claims: dict[str, Any] | None = None,
    feature_id: str | None = None,
):
    """Serialize a D-Tale instance into the JSON envelope expected by clients."""
    url = instance.build_main_url()
    if IS_PROXY and not url.startswith("/"):
        url = f"/{url}"
    scopes = _effective_access_scopes(data_id)
    if scopes:
        if len(scopes) != 1:
            abort(500, description="Unexpected private D-Tale scope composition.")
        scope = next(iter(scopes))
        if access_claims is None:
            abort(500, description="Private D-Tale authorization is unavailable.")
        _prune_viewer_capabilities()
        capability_id = secrets.token_urlsafe(24)
        VIEWER_CAPABILITIES[capability_id] = ViewerCapability(
            scope=scope,
            runid=meta.runid,
            claims=dict(access_claims),
            feature_id=feature_id,
            expires_at=time.time() + DTALE_PRIVATE_ACCESS_TTL_SECONDS,
        )
        ticket = _access_serializer(launch=True).dumps(
            {"data_id": data_id, "scope": scope, "capability": capability_id}
        )
        url = f"{APP_ROOT or ''}/dtale/access/{ticket}"
    return jsonify(
        {
            "data_id": data_id,
            "url": url,
            "name": meta.name,
            "fingerprint": meta.fingerprint,
        }
    )


def _parquet_filter_error_response(err: ParquetFilterError):
    return jsonify(err.to_payload()), err.status_code


@app.post("/internal/load")
def load_into_dtale():
    """Load the requested run-relative file into D-Tale and return viewer metadata."""
    _verify_token()
    payload = request.get_json(silent=True) or {}
    runid = payload.get("runid", "").strip()
    config = (payload.get("config") or "").strip()
    rel_path = payload.get("path", "").strip()
    raw_pqf_value = payload.get("pqf")
    resource_public = payload.get("resource_public", False)
    access_claims = payload.get("access_claims")
    feature_id = payload.get("feature_id")

    if not runid or not rel_path:
        abort(400, description="Both runid and path are required.")
    if not isinstance(resource_public, bool):
        abort(400, description="resource_public must be a boolean.")
    if resource_public and not _resource_is_public(runid, config):
        abort(409, description="Resource visibility changed; reopen from browse.")
    if not resource_public and not isinstance(access_claims, dict):
        abort(400, description="Private D-Tale loads require verified access claims.")
    if feature_id is not None and feature_id not in {"batch_runner", "culvert_runner"}:
        abort(400, description="Invalid private D-Tale feature scope.")

    if raw_pqf_value is None:
        raw_pqf = None
    elif isinstance(raw_pqf_value, str):
        raw_pqf = raw_pqf_value.strip() or None
    else:
        return _parquet_filter_error_response(
            ParquetFilterError(
                "Invalid parquet filter payload.",
                details="Filter payload field 'pqf' must be a string.",
            )
        )

    rel_path = _normalize_rel(rel_path)
    wd, target = _resolve_target(runid, rel_path, config=config or None)
    try:
        resolved_target = _resolve_source_path(target)
        size_mb = target.stat().st_size / (1024 * 1024)
    except OSError as exc:
        raise _SourceChangedError(_SOURCE_CHANGED_MESSAGE) from exc
    if MAX_FILE_MB > 0:
        if size_mb > MAX_FILE_MB:
            abort(413, description=f"File size {size_mb:.1f} MB exceeds limit ({MAX_FILE_MB:.0f} MB).")

    parquet_filter_active = (
        BROWSE_PARQUET_FILTERS_ENABLED
        and bool(raw_pqf)
        and target.suffix.lower() in {".parquet", ".geoparquet", ".pq"}
    )
    filter_cache_scope = raw_pqf if parquet_filter_active else ""
    dataset_scope = f"{rel_path}::pqf::{filter_cache_scope}" if filter_cache_scope else rel_path

    fingerprint = _fingerprint(target)
    data_id = _make_dataset_id(runid, config, dataset_scope)
    if not resource_public and not DTALE_INTERNAL_TOKEN:
        abort(503, description="Private D-Tale access is not configured.")
    desired_access_scopes = frozenset() if resource_public else frozenset({data_id})
    display_name = f"{runid}/{config}/{rel_path}" if config else f"{runid}/{rel_path}"
    if parquet_filter_active:
        filter_label = hashlib.sha1(raw_pqf.encode("utf-8")).hexdigest()[:8] if raw_pqf else "unknown"
        display_name = f"{display_name} [filtered {filter_label}]"
    display_name = display_name.strip("/")[:120]

    _ensure_geojson_assets(runid, wd, data_id)

    meta = DATASETS.get(data_id)
    reuse_ready = False
    if meta and meta.fingerprint == fingerprint and meta.resolved_path == resolved_target and meta.path == target:
        lazy_instance = LAZY_PARQUET_DATASETS.get(data_id)
        if lazy_instance is not None and global_state.get_dtypes(data_id) is not None:
            reuse_ready = True
        elif global_state.contains(data_id):
            current_df = global_state.get_data(data_id)
            current_dtypes = global_state.get_dtypes(data_id)
            if current_df is not None and current_dtypes is not None:
                reuse_ready = True
            else:
                logger.info("Refreshing D-Tale dataset %s due to missing cached state.", data_id)
                global_state.cleanup(data_id)
                LAZY_PARQUET_DATASETS.pop(data_id, None)
        else:
            logger.info("Refreshing D-Tale dataset %s; no active state found.", data_id)
    elif meta:
        logger.info("File changed, resetting cached dataset %s", data_id)
        _discard_dataset(data_id)

    if reuse_ready:
        logger.debug("Reusing cached D-Tale dataset %s for %s", data_id, target)
        meta.last_loaded = time.time()
        meta.runid = runid
        meta.config = config
        meta.resource_public = resource_public
        _set_dataset_access_scopes(data_id, desired_access_scopes)
        instance = DtaleData(data_id, DTALE_BASE_URL, is_proxy=IS_PROXY, app_root=APP_ROOT)
        return _build_instance_response(
            data_id,
            instance,
            meta,
            access_claims=access_claims,
            feature_id=feature_id,
        )

    is_parquet_target = _is_parquet_path(target)
    if is_parquet_target:
        try:
            compiled = None
            if parquet_filter_active:
                compiled = compile_filter_payload_for_path(target, raw_pqf)
            instance = _initialize_lazy_parquet_dataset(
                data_id,
                display_name,
                target,
                compiled_filter=compiled,
            )
            lazy_rows = LAZY_PARQUET_DATASETS[data_id].rows()
            lazy_columns = len(LAZY_PARQUET_DATASETS[data_id].base_df.columns)
            _verify_source(target, fingerprint, resolved_target)
        except _SourceChangedError:
            _discard_dataset(data_id)
            raise
        except ParquetFilterError as err:
            _discard_dataset(data_id)
            _verify_source(target, fingerprint, resolved_target)
            return _parquet_filter_error_response(err)
        except (duckdb.Error, OSError, ValueError) as exc:
            _discard_dataset(data_id)
            _verify_source(target, fingerprint, resolved_target)
            logger.exception("Failed to lazily load parquet %s", target)
            abort(500, description=str(exc))

        if MAX_ROWS and lazy_rows > MAX_ROWS:
            global_state.cleanup(data_id)
            LAZY_PARQUET_DATASETS.pop(data_id, None)
            abort(
                413,
                description=f"Row count {lazy_rows} exceeds limit ({MAX_ROWS}). "
                "Adjust DTALE_MAX_ROWS to override.",
            )

        DATASETS[data_id] = DatasetMeta(
            path=target,
            fingerprint=fingerprint,
            name=display_name,
            last_loaded=time.time(),
            resolved_path=resolved_target,
            runid=runid,
            config=config,
            resource_public=resource_public,
        )
        _set_dataset_access_scopes(data_id, desired_access_scopes)

        logger.info(
            "Registered lazy parquet %s in D-Tale (rows=%d, cols=%d, data_id=%s)",
            target.relative_to(wd),
            lazy_rows,
            lazy_columns,
            data_id,
        )

        return _build_instance_response(
            data_id,
            instance,
            DATASETS[data_id],
            access_claims=access_claims,
            feature_id=feature_id,
        )

    try:
        df = _load_dataframe(target)
    except ParquetFilterError as err:
        _verify_source(target, fingerprint, resolved_target)
        return _parquet_filter_error_response(err)
    except Exception as exc:  # pragma: no cover - surface full error to caller
        _verify_source(target, fingerprint, resolved_target)
        logger.exception("Failed to load %s", target)
        abort(500, description=str(exc))

    _verify_source(target, fingerprint, resolved_target)
    if MAX_ROWS and len(df) > MAX_ROWS:
        abort(
            413,
            description=f"Row count {len(df)} exceeds limit ({MAX_ROWS}). "
            "Adjust DTALE_MAX_ROWS to override.",
        )

    try:
        instance = _initialize_dtale_dataset(data_id, display_name, df)
    except Exception:  # broad-except: boundary contract; clean third-party partial state, then propagate
        logger.exception("Failed to initialize D-Tale dataset %s", data_id)
        _discard_dataset(data_id)
        raise

    DATASETS[data_id] = DatasetMeta(
        path=target,
        fingerprint=fingerprint,
        name=display_name,
        last_loaded=time.time(),
        resolved_path=resolved_target,
        runid=runid,
        config=config,
        resource_public=resource_public,
    )
    _set_dataset_access_scopes(data_id, desired_access_scopes)

    logger.info(
        "Loaded %s into D-Tale (rows=%d, cols=%d, data_id=%s)",
        target.relative_to(wd),
        len(df),
        len(df.columns),
        data_id,
    )

    return _build_instance_response(
        data_id,
        instance,
        DATASETS[data_id],
        access_claims=access_claims,
        feature_id=feature_id,
    )


__all__ = ["app"]
