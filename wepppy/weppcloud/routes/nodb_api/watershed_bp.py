"""Routes for watershed blueprint extracted from app.py."""

import math
from pathlib import Path
from typing import Any, Mapping

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron, Watershed
from wepppy.topo.wbt import TerrainConfig, TerrainProcessor, TerrainProcessorRuntimeError
from wepppy.topo.watershed_abstraction import ChannelRoutingError
from wepppy.weppcloud.utils.helpers import authorize, authorize_and_handle_with_exception_factory
from wepppy.weppcloud.utils.cap_guard import requires_cap

watershed_bp = Blueprint('watershed', __name__)

@watershed_bp.route('/runs/<string:runid>/<config>/query/delineation_pass')
@watershed_bp.route('/runs/<string:runid>/<config>/query/delineation_pass/')
@authorize_and_handle_with_exception_factory
def query_topaz_pass(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    has_channels = watershed.has_channels
    has_subcatchments = watershed.has_subcatchments

    if not has_channels:
        return jsonify(0)

    if has_channels and not has_subcatchments:
        return jsonify(1)

    if has_channels and has_subcatchments:
        return jsonify(2)

    return None


@watershed_bp.route('/runs/<string:runid>/<config>/resources/channels.json')
@authorize_and_handle_with_exception_factory
def resources_channels_geojson(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    fn = watershed.channels_shp

    js = json.load(open(fn))
    ron = Ron.getInstance(wd)
    name = ron.name

    if name.strip() == '':
        js['name'] = runid
    else:
        js['name'] = name

    return jsonify(js)

@watershed_bp.route('/runs/<string:runid>/<config>/query/extent')
@watershed_bp.route('/runs/<string:runid>/<config>/query/extent/')
@authorize_and_handle_with_exception_factory
def query_extent(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Ron.getInstance(wd).extent)


@watershed_bp.route('/runs/<string:runid>/<config>/report/channel')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view watershed reports.")
def report_channel(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return render_template('reports/channel.htm', 
                           runid=runid, config=config,
                           map=Ron.getInstance(wd).map)


@watershed_bp.route('/runs/<string:runid>/<config>/query/outlet')
@watershed_bp.route('/runs/<string:runid>/<config>/query/outlet/')
@authorize_and_handle_with_exception_factory
def query_outlet(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Watershed.getInstance(wd)
                        .outlet
                        .as_dict())


@watershed_bp.route('/runs/<string:runid>/<config>/report/outlet')
@watershed_bp.route('/runs/<string:runid>/<config>/report/outlet/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view watershed reports.")
def report_outlet(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return render_template('reports/outlet.htm', runid=runid, config=config,
                           outlet=Watershed.getInstance(wd).outlet,
                           ron=Ron.getInstance(wd))


@watershed_bp.route('/runs/<string:runid>/<config>/query/has_dem')
@watershed_bp.route('/runs/<string:runid>/<config>/query/has_dem/')
@authorize_and_handle_with_exception_factory
def query_has_dem(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Ron.getInstance(wd).has_dem)


@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/subcatchments')
@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_watershed_summary_subcatchments(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Watershed.getInstance(wd).subs_summary)


@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/channels')
@watershed_bp.route('/runs/<string:runid>/<config>/query/watershed/channels/')
@authorize_and_handle_with_exception_factory
def query_watershed_summary_channels(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return jsonify(Watershed.getInstance(wd).chns_summary)


@watershed_bp.route('/runs/<string:runid>/<config>/report/subcatchments')
@watershed_bp.route('/runs/<string:runid>/<config>/report/subcatchments/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view watershed reports.")
def query_watershed_summary(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    return render_template('reports/subcatchments.htm', runid=runid, config=config,
                            user=current_user,
                            watershed=Watershed.getInstance(wd))

@watershed_bp.route('/runs/<string:runid>/<config>/tasks/abstract_watershed/', methods=['GET', 'POST'])
@authorize_and_handle_with_exception_factory
def task_abstract_watershed(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    watershed.abstract_watershed()
    return success_factory()


@watershed_bp.route('/runs/<string:runid>/<config>/tasks/sub_intersection/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def sub_intersection(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    extent = request.json.get('extent', None)
    ron = Ron.getInstance(wd)
    _map = ron.map
    subwta_fn = Watershed.getInstance(wd).subwta
    raw_ids = _map.raster_intersection(extent, raster_fn=subwta_fn, discard=(0,))

    cleaned_ids = []
    seen = set()
    for value in raw_ids:
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric) or numeric < 1:
            continue
        integer_id = int(numeric)
        if integer_id < 1 or integer_id in seen:
            continue
        seen.add(integer_id)
        cleaned_ids.append(integer_id)

    return jsonify(cleaned_ids)


_TERRAIN_CONFIG_FILENAME = "terrain_processor_config.json"
_TERRAIN_LAST_RESULT_FILENAME = "terrain_processor_last_result.json"
_TERRAIN_BOOLEAN_FIELDS = {"smooth", "blc_fill", "enforce_culverts"}


def _terrain_workspace(wd: str) -> Path:
    workspace = Path(wd) / "dem" / "wbt" / "terrain_processor"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _terrain_config_path(wd: str) -> Path:
    return _terrain_workspace(wd) / _TERRAIN_CONFIG_FILENAME


def _terrain_last_result_path(wd: str) -> Path:
    return _terrain_workspace(wd) / _TERRAIN_LAST_RESULT_FILENAME


def _default_terrain_config_payload() -> dict[str, Any]:
    return TerrainConfig().to_dict()


def _read_json_mapping(path: Path, *, default: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise TerrainProcessorRuntimeError(
            f"Expected JSON object in {path}",
            code="invalid_terrain_state_payload",
            context={"path": str(path)},
        )
    return dict(payload)


def _write_json_mapping(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(dict(payload), fp, indent=2, sort_keys=True)
        fp.write("\n")


def _build_terrain_config(payload: Mapping[str, Any]) -> TerrainConfig:
    defaults = _default_terrain_config_payload()
    unknown_keys = sorted(set(payload.keys()) - set(defaults.keys()))
    if unknown_keys:
        raise TerrainProcessorRuntimeError(
            "Unknown TerrainProcessor config keys were provided",
            code="invalid_terrain_config_keys",
            context={"unknown_keys": unknown_keys},
        )

    merged = dict(defaults)
    merged.update(dict(payload))

    highway_filter = merged.get("osm_highway_filter")
    if highway_filter is None:
        merged["osm_highway_filter"] = tuple(defaults["osm_highway_filter"])
    else:
        if not isinstance(highway_filter, (list, tuple)):
            raise TerrainProcessorRuntimeError(
                "osm_highway_filter must be a list/tuple of highway tags",
                code="invalid_terrain_config_value",
                context={"field": "osm_highway_filter"},
            )
        merged["osm_highway_filter"] = tuple(str(item) for item in highway_filter)

    outlets = merged.get("outlets")
    if outlets in (None, ""):
        merged["outlets"] = None
    else:
        if not isinstance(outlets, (list, tuple)):
            raise TerrainProcessorRuntimeError(
                "outlets must be a list of coordinate pairs",
                code="invalid_terrain_config_value",
                context={"field": "outlets"},
            )
        normalized_outlets: list[tuple[float, float]] = []
        for outlet in outlets:
            if not isinstance(outlet, (list, tuple)) or len(outlet) != 2:
                raise TerrainProcessorRuntimeError(
                    "Each outlet must contain exactly two coordinates",
                    code="invalid_terrain_config_value",
                    context={"field": "outlets"},
                )
            normalized_outlets.append((float(outlet[0]), float(outlet[1])))
        merged["outlets"] = tuple(normalized_outlets)

    for optional_path_key in ("roads_path", "culvert_path"):
        if merged.get(optional_path_key) in {"", None}:
            merged[optional_path_key] = None

    if merged.get("aoi_wgs84_geojson") in ("", None):
        merged["aoi_wgs84_geojson"] = None

    return TerrainConfig(**merged)


def _load_terrain_config_payload(wd: str) -> dict[str, Any]:
    return _read_json_mapping(
        _terrain_config_path(wd),
        default=_default_terrain_config_payload(),
    )


def _save_terrain_config_payload(wd: str, payload: Mapping[str, Any]) -> None:
    _write_json_mapping(_terrain_config_path(wd), payload)


def _load_terrain_last_result_payload(wd: str) -> dict[str, Any] | None:
    path = _terrain_last_result_path(wd)
    if not path.exists():
        return None
    return _read_json_mapping(path)


def _save_terrain_last_result_payload(wd: str, payload: Mapping[str, Any]) -> None:
    _write_json_mapping(_terrain_last_result_path(wd), payload)


def _relative_to_workspace(workspace: Path, artifact_path: str | None) -> str | None:
    if not artifact_path:
        return None
    try:
        relative = Path(artifact_path).resolve().relative_to(workspace.resolve())
    except ValueError:
        return None
    return str(relative)


def _terrain_artifact_url(runid: str, config: str, relative_path: str | None) -> str | None:
    if relative_path is None:
        return None
    return url_for(
        "watershed.resources_terrain_processor_artifact",
        runid=runid,
        config=config,
        artifact_relpath=relative_path,
    )


def _decorate_manifest_entries(
    *,
    runid: str,
    config: str,
    workspace: Path,
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for entry in entries:
        layer = dict(entry)
        relative_path = _relative_to_workspace(workspace, str(layer.get("path", "")))
        layer["relative_path"] = relative_path
        layer["url"] = _terrain_artifact_url(runid, config, relative_path)
        decorated.append(layer)
    return decorated


def _decorate_artifacts_by_phase(
    *,
    runid: str,
    config: str,
    workspace: Path,
    artifacts_by_phase: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, dict[str, Any]]]:
    decorated: dict[str, dict[str, dict[str, Any]]] = {}
    for phase_name, artifact_map in artifacts_by_phase.items():
        phase_payload: dict[str, dict[str, Any]] = {}
        for artifact_name, artifact_path in artifact_map.items():
            relative_path = _relative_to_workspace(workspace, artifact_path)
            phase_payload[artifact_name] = {
                "path": artifact_path,
                "relative_path": relative_path,
                "url": _terrain_artifact_url(runid, config, relative_path),
            }
        decorated[phase_name] = phase_payload
    return decorated


def _load_manifest_entries(manifest_path: str | None) -> list[dict[str, Any]]:
    if not manifest_path:
        return []
    path = Path(manifest_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise TerrainProcessorRuntimeError(
            "visualization manifest must contain a list of entries",
            code="invalid_visualization_manifest",
            context={"manifest_path": manifest_path},
        )
    return [dict(entry) for entry in entries if isinstance(entry, dict)]


def _load_ui_payload(workspace: Path) -> dict[str, Any] | None:
    path = workspace / "visualization" / "visualization_ui_payload.json"
    if not path.exists():
        return None
    payload = _read_json_mapping(path)
    return payload


def _build_terrain_run_payload(
    *,
    runid: str,
    config: str,
    workspace: Path,
    run_result: Any,
) -> dict[str, Any]:
    manifest_entries = _load_manifest_entries(run_result.visualization_manifest_path)
    decorated_entries = _decorate_manifest_entries(
        runid=runid,
        config=config,
        workspace=workspace,
        entries=manifest_entries,
    )
    ui_payload = _load_ui_payload(workspace)
    if ui_payload is not None:
        layers = ui_payload.get("layers", [])
        if isinstance(layers, list):
            decorated_layers = _decorate_manifest_entries(
                runid=runid,
                config=config,
                workspace=workspace,
                entries=[dict(layer) for layer in layers if isinstance(layer, dict)],
            )
            ui_payload = dict(ui_payload)
            ui_payload["layers"] = decorated_layers

    current_dem_relative = _relative_to_workspace(workspace, run_result.current_dem_path)
    basin_summaries = [
        {
            "basin_id": int(summary.basin_id),
            "parent_basin_id": summary.parent_basin_id,
            "outlet_x": float(summary.outlet_x),
            "outlet_y": float(summary.outlet_y),
            "area": summary.area,
            "stream_order": summary.stream_order,
        }
        for summary in run_result.basin_summaries
    ]

    return {
        "executed_phases": list(run_result.executed_phases),
        "invalidated_phases": list(run_result.invalidated_phases),
        "helper_invalidated_phases": list(run_result.helper_invalidated_phases),
        "changed_config_keys": list(run_result.changed_config_keys),
        "current_dem_path": run_result.current_dem_path,
        "current_dem_relative_path": current_dem_relative,
        "current_dem_url": _terrain_artifact_url(runid, config, current_dem_relative),
        "artifacts_by_phase": _decorate_artifacts_by_phase(
            runid=runid,
            config=config,
            workspace=workspace,
            artifacts_by_phase=run_result.artifacts_by_phase,
        ),
        "visualization_manifest_path": run_result.visualization_manifest_path,
        "visualization_manifest": {"entries": decorated_entries},
        "visualization_ui_payload": ui_payload,
        "provenance": list(run_result.provenance),
        "basin_summaries": basin_summaries,
    }


@watershed_bp.route('/runs/<string:runid>/<config>/query/terrain_processor/config')
@watershed_bp.route('/runs/<string:runid>/<config>/query/terrain_processor/config/')
@authorize_and_handle_with_exception_factory
def query_terrain_processor_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    payload = _load_terrain_config_payload(wd)
    return jsonify({"config": payload})


@watershed_bp.route('/runs/<string:runid>/<config>/tasks/set_terrain_processor_config/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def set_terrain_processor_config(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    payload = request.get_json(silent=True)
    if payload is None:
        payload = parse_request_payload(request, boolean_fields=_TERRAIN_BOOLEAN_FIELDS)
    if not isinstance(payload, dict):
        return error_factory(
            "TerrainProcessor config payload must be a JSON object",
            code="invalid_terrain_config_payload",
            status_code=400,
        )
    current_payload = _load_terrain_config_payload(wd)
    current_payload.update(payload)

    try:
        terrain_config = _build_terrain_config(current_payload)
    except TerrainProcessorRuntimeError as exc:
        return error_factory(exc.message, code=exc.code, details=exc.context)

    normalized = terrain_config.to_dict()
    _save_terrain_config_payload(wd, normalized)
    return success_factory({"config": normalized})


@watershed_bp.route('/runs/<string:runid>/<config>/tasks/run_terrain_processor/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def run_terrain_processor(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    payload = request.get_json(silent=True)
    if payload is None:
        payload = parse_request_payload(request, boolean_fields=_TERRAIN_BOOLEAN_FIELDS)
    if not isinstance(payload, dict):
        return error_factory(
            "TerrainProcessor run payload must be a JSON object",
            code="invalid_terrain_run_payload",
            status_code=400,
        )
    config_override = payload.get("config")
    if isinstance(config_override, Mapping):
        update_payload = dict(config_override)
    elif payload:
        update_payload = dict(payload)
    else:
        update_payload = {}

    current_payload = _load_terrain_config_payload(wd)
    current_payload.update(update_payload)

    try:
        terrain_config = _build_terrain_config(current_payload)
        normalized_config = terrain_config.to_dict()
        _save_terrain_config_payload(wd, normalized_config)

        processor = TerrainProcessor(
            wbt_wd=str(_terrain_workspace(wd)),
            dem_path=Ron.getInstance(wd).dem_fn,
            config=terrain_config,
        )
        run_result = processor.run()
        result_payload = _build_terrain_run_payload(
            runid=runid,
            config=config,
            workspace=_terrain_workspace(wd),
            run_result=run_result,
        )
        _save_terrain_last_result_payload(wd, result_payload)
    except TerrainProcessorRuntimeError as exc:
        return error_factory(exc.message, code=exc.code, details=exc.context)

    return success_factory(result_payload)


@watershed_bp.route('/runs/<string:runid>/<config>/query/terrain_processor/last_result')
@watershed_bp.route('/runs/<string:runid>/<config>/query/terrain_processor/last_result/')
@authorize_and_handle_with_exception_factory
def query_terrain_processor_last_result(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    payload = _load_terrain_last_result_payload(wd)
    return jsonify({"result": payload})


@watershed_bp.route('/runs/<string:runid>/<config>/query/terrain_processor/manifest')
@watershed_bp.route('/runs/<string:runid>/<config>/query/terrain_processor/manifest/')
@authorize_and_handle_with_exception_factory
def query_terrain_processor_manifest(runid: str, config: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    payload = _load_terrain_last_result_payload(wd)
    if payload is None:
        return jsonify({"manifest": {"entries": []}, "ui_payload": None})

    manifest_payload = payload.get("visualization_manifest", {"entries": []})
    ui_payload = payload.get("visualization_ui_payload")
    return jsonify({"manifest": manifest_payload, "ui_payload": ui_payload})


@watershed_bp.route('/runs/<string:runid>/<config>/resources/terrain_processor/<path:artifact_relpath>')
@authorize_and_handle_with_exception_factory
def resources_terrain_processor_artifact(runid: str, config: str, artifact_relpath: str) -> Response:
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    workspace = _terrain_workspace(wd).resolve()
    target_path = (workspace / artifact_relpath).resolve()

    try:
        target_path.relative_to(workspace)
    except ValueError:
        abort(404)
    if not target_path.exists() or not target_path.is_file():
        abort(404)

    return send_file(str(target_path))
