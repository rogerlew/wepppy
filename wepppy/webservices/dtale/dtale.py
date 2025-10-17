"""
D-Tale Wrapper Service for WEPP Cloud
====================================

This module embeds the upstream D-Tale Flask application inside a thin wrapper that
understands WEPP Cloud run directories.  It exposes a small authenticated API for
loading tabular outputs (Parquet, CSV, TSV, Feather, Pickle) into D-Tale instances and
reuses in-memory sessions when files have not changed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
from flask import abort, jsonify, request

from dtale import global_state
from dtale.app import build_app, initialize_process_props
from dtale.views import DtaleData, build_dtypes_state, startup
from plotly import graph_objs as go

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.core.watershed import Watershed

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
DTALE_INTERNAL_TOKEN = os.getenv("DTALE_INTERNAL_TOKEN", "").strip()
if not DTALE_INTERNAL_TOKEN:
    logger.warning(
        "DTALE_INTERNAL_TOKEN is not set – falling back to in-process requests only."
    )

MAX_FILE_MB = float(os.getenv("DTALE_MAX_FILE_MB", "512"))
MAX_ROWS = int(os.getenv("DTALE_MAX_ROWS", "0"))
ALLOW_CELL_EDITS = os.getenv("DTALE_ALLOW_CELL_EDITS", "0").lower() in {"1", "true", "yes"}
DTALE_THEME = os.getenv("DTALE_THEME", "light")

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


DATASETS: dict[str, DatasetMeta] = {}
REGISTERED_GEOJSON: dict[str, str] = {}
MAP_DEFAULTS: dict[str, dict[str, object]] = {}
MAP_CHOICES: dict[str, list[tuple[str, str, str | None]]] = {}
_IDENTIFIER_STRING_ALIASES: tuple[tuple[str, str], ...] = (
    ("wepp_id", "WeppID"),
    ("topaz_id", "TopazID"),
    ("channel_id", "ChannelID"),
    ("reach_id", "ReachID"),
    ("field_id", "FieldID"),
    ("sub_field_id", "SubFieldID"),
)


def _fingerprint(path: Path) -> str:
    stats = path.stat()
    return f"{stats.st_mtime_ns}:{stats.st_size}"


def _make_dataset_id(runid: str, config: str, rel_path: str) -> str:
    raw = f"{runid}|{config}|{rel_path}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _resolve_target(runid: str, rel_path: str, *, config: str | None = None) -> tuple[Path, Path]:
    wd = Path(get_wd(runid)).resolve()
    rel_candidates: list[Path] = [Path(rel_path)]
    if config:
        rel_candidates.append(Path(config) / rel_path)

    for rel_candidate in rel_candidates:
        candidate = (wd / rel_candidate).resolve()
        if not str(candidate).startswith(str(wd)):
            abort(403, description="Path traversal detected.")
        if candidate.exists() and candidate.is_file():
            return wd, candidate

    abort(404, description="File not found.")


def _normalize_rel(rel_path: str) -> str:
    rel_path = rel_path.replace("\\", "/")
    return rel_path.lstrip("/")


def _load_geojson(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:  # pragma: no cover - defensive: invalid JSON should not crash loader
        logger.exception("Failed to parse geojson at %s", path)
    return None


def _infer_featureidkey(properties: Iterable[str], preferred: Iterable[str] | None = None) -> str | None:
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
    if dtale_custom_geojson is None:
        return (None, None)
    if not path:
        return (None, None)
    path = Path(path)
    if not path.exists() or not path.is_file():
        logger.debug("GeoJSON asset missing for %s at %s", slug, path)
        return (None, None)

    geojson_key = f"{runid}-{slug}"
    fingerprint = _fingerprint(path)
    existing_entry = next(
        (entry for entry in dtale_custom_geojson.CUSTOM_GEOJSON if entry.get("key") == geojson_key),
        None,
    )
    if REGISTERED_GEOJSON.get(geojson_key) == fingerprint and existing_entry:
        featureidkey = existing_entry.get("featureidkey")
    else:
        data = _load_geojson(path)
        if not data:
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

    if data_id:
        entry = (label or slug, geojson_key, featureidkey)
        choices = MAP_CHOICES.setdefault(data_id, [])
        if entry not in choices:
            choices.append(entry)
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

    logger.debug("Registered geojson asset %s for %s", geojson_key, runid)
    return (geojson_key, featureidkey)


def _ensure_geojson_assets(runid: str, wd: Path, data_id: str | None) -> None:
    if dtale_custom_geojson is None:
        return
    defaults_set = data_id in MAP_DEFAULTS if data_id else False
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
        nonlocal defaults_set
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
        if key and make_default or (key and not defaults_set):
            defaults_set = True
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

    if AgFields is None:
        return

    try:
        ag_fields = AgFields.tryGetInstance(str(wd), allow_nonexistent=True, ignore_lock=True)
    except Exception:  # pragma: no cover - optional module, fallthrough
        logger.debug("Unable to resolve AgFields instance for %s", runid, exc_info=True)
        return

    if not ag_fields:
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


def _read_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return _postprocess_dataframe(df)


def _read_feather(path: Path) -> pd.DataFrame:
    df = pd.read_feather(path)
    return _postprocess_dataframe(df)


def _read_csv(path: Path, *, sep: str = ",", compression: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, sep=sep, compression=compression)
    return _postprocess_dataframe(df)


def _read_pickle(path: Path) -> pd.DataFrame:
    df = pd.read_pickle(path)
    return _postprocess_dataframe(pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df)


READERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    ".parquet": _read_parquet,
    ".pq": _read_parquet,
    ".feather": _read_feather,
    ".arrow": _read_feather,
    ".csv": _read_csv,
    ".tsv": lambda p: _read_csv(p, sep="\t"),
    ".pkl": _read_pickle,
    ".pickle": _read_pickle,
}


def _load_dataframe(path: Path) -> pd.DataFrame:
    name = path.name.lower()
    if name.endswith(".csv.gz"):
        return _read_csv(path, compression="gzip")
    if name.endswith(".tsv.gz"):
        return _read_csv(path, sep="\t", compression="gzip")
    reader = READERS.get(path.suffix.lower())
    if not reader:
        abort(415, description=f"Unsupported file extension: {path.suffix or '<none>'}")
    return reader(path)


def _initialize_dtale_dataset(data_id: str, display_name: str, df: pd.DataFrame) -> DtaleData:
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


if dtale_custom_geojson is not None:
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
                    for entry in dtale_custom_geojson.CUSTOM_GEOJSON
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
                        entries = dtale_custom_geojson.CUSTOM_GEOJSON
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


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def _verify_token() -> None:
    if not DTALE_INTERNAL_TOKEN:
        return
    supplied = request.headers.get("X-DTALE-TOKEN", "")
    if supplied != DTALE_INTERNAL_TOKEN:
        abort(403, description="Forbidden.")


def _build_instance_response(data_id: str, instance: DtaleData, meta: DatasetMeta):
    url = instance.build_main_url()
    if IS_PROXY and not url.startswith("/"):
        url = f"/{url}"
    return jsonify(
        {
            "data_id": data_id,
            "url": url,
            "name": meta.name,
            "fingerprint": meta.fingerprint,
        }
    )


@app.post("/internal/load")
def load_into_dtale():
    _verify_token()
    payload = request.get_json(silent=True) or {}
    runid = payload.get("runid", "").strip()
    config = (payload.get("config") or "").strip()
    rel_path = payload.get("path", "").strip()

    if not runid or not rel_path:
        abort(400, description="Both runid and path are required.")

    rel_path = _normalize_rel(rel_path)
    wd, target = _resolve_target(runid, rel_path, config=config or None)
    if MAX_FILE_MB > 0:
        size_mb = target.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_MB:
            abort(413, description=f"File size {size_mb:.1f} MB exceeds limit ({MAX_FILE_MB:.0f} MB).")

    fingerprint = _fingerprint(target)
    data_id = _make_dataset_id(runid, config, rel_path)
    display_name = f"{runid}/{config}/{rel_path}" if config else f"{runid}/{rel_path}"
    display_name = display_name.strip("/")[:120]

    _ensure_geojson_assets(runid, wd, data_id)

    meta = DATASETS.get(data_id)
    reuse_ready = False
    if meta and meta.fingerprint == fingerprint:
        if global_state.contains(data_id):
            current_df = global_state.get_data(data_id)
            current_dtypes = global_state.get_dtypes(data_id)
            if current_df is not None and current_dtypes is not None:
                reuse_ready = True
            else:
                logger.info("Refreshing D-Tale dataset %s due to missing cached state.", data_id)
                global_state.cleanup(data_id)
        else:
            logger.info("Refreshing D-Tale dataset %s; no active state found.", data_id)
    elif meta and meta.fingerprint != fingerprint:
        logger.info("File changed, resetting cached dataset %s", data_id)
        global_state.cleanup(data_id)
        DATASETS.pop(data_id, None)

    if reuse_ready:
        logger.debug("Reusing cached D-Tale dataset %s for %s", data_id, target)
        meta.last_loaded = time.time()
        instance = DtaleData(data_id, DTALE_BASE_URL, is_proxy=IS_PROXY, app_root=APP_ROOT)
        return _build_instance_response(data_id, instance, meta)

    try:
        df = _load_dataframe(target)
    except Exception as exc:  # pragma: no cover - surface full error to caller
        logger.exception("Failed to load %s", target)
        abort(500, description=str(exc))

    if MAX_ROWS and len(df) > MAX_ROWS:
        abort(
            413,
            description=f"Row count {len(df)} exceeds limit ({MAX_ROWS}). "
            "Adjust DTALE_MAX_ROWS to override.",
        )

    instance = _initialize_dtale_dataset(data_id, display_name, df)

    DATASETS[data_id] = DatasetMeta(
        path=target,
        fingerprint=fingerprint,
        name=display_name,
        last_loaded=time.time(),
    )

    logger.info(
        "Loaded %s into D-Tale (rows=%d, cols=%d, data_id=%s)",
        target.relative_to(wd),
        len(df),
        len(df.columns),
        data_id,
    )

    return _build_instance_response(data_id, instance, DATASETS[data_id])


__all__ = ["app"]
