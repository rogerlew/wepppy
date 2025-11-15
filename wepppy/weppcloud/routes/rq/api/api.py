import os
import json
import shutil


from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import awesome_codename
from typing import Any, Dict, Iterable

from flask_login import login_required
import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify, send_file

from flask_security import current_user

from werkzeug.utils import secure_filename

from wepppy.topo.peridot.flowpath import PeridotChannel
from wepppy.weppcloud.utils.helpers import get_wd, handle_with_exception_factory, success_factory, error_factory, exception_factory
from wepppy.weppcloud.utils.uploads import save_run_file, UploadError

import redis
from rq import Queue, Callback
from rq.job import Job
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

from wepppy.soils.ssurgo import NoValidSoilsException

from wepppy.nodb.core import *
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.ash_transport import Ash, AshSpatialMode
from wepppy.nodb.base import lock_statuses

from wepppy.nodb.mods.omni import Omni, OmniNoDbLockedException, OmniScenario
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.batch_runner import BatchRunner

from wepppy.rq.project_rq import (
    fetch_dem_and_build_channels_rq,
    set_outlet_rq,
    build_subcatchments_and_abstract_watershed_rq,
    build_landuse_rq, 
    build_soils_rq, 
    build_climate_rq,
    run_ash_rq,
    run_debris_flow_rq,
    run_rhem_rq,
    fetch_and_analyze_rap_ts_rq,
    fork_rq,
    archive_rq,
    restore_archive_rq
)
from wepppy.rq.wepp_rq import run_wepp_rq, post_dss_export_rq
from wepppy.rq.omni_rq import run_omni_scenarios_rq
from wepppy.rq.land_and_soil_rq import land_and_soil_rq
from wepppy.rq.batch_rq import run_batch_rq

from wepppy.topo.watershed_abstraction import (
    ChannelRoutingError,
)

from wepppy.nodb.core import *
from wepppy.all_your_base import isint, isfloat
from wepppy.weppcloud.utils.archive import has_archive
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.wepp.interchange.dss_dates import format_dss_date, parse_dss_date

from ..._common import roles_required, parse_request_payload

import inspect
import time
from rq import Queue, get_current_job

REDIS_HOST = redis_host()
RQ_DB = int(RedisDB.RQ)


def _redis_conn():
    """Create a Redis connection using the centralized configuration."""
    return redis.Redis(**redis_connection_kwargs(RedisDB.RQ))


TIMEOUT = 216_000
SBS_ALLOWED_EXTENSIONS = ("tif", "tiff", "img")
SBS_MAX_BYTES = 100 * 1024 * 1024


def _safe_int(value: Any) -> int | None:
    try:
        candidate = int(str(value))
    except (TypeError, ValueError):
        return None
    return candidate


def _dedupe_positive_ints(values: Iterable[Any]) -> list[int]:
    seen: set[int] = set()
    cleaned: list[int] = []
    for raw in values:
        numeric = _safe_int(raw)
        if numeric is None or numeric <= 0 or numeric in seen:
            continue
        seen.add(numeric)
        cleaned.append(numeric)
    return cleaned


def _coerce_omni_scenario_list(payload: Dict[str, Any], raw_json: Any) -> list[Dict[str, Any]] | None:
    if isinstance(raw_json, list):
        return raw_json

    scenarios_raw = payload.get("scenarios")
    if scenarios_raw is None:
        return None

    if isinstance(scenarios_raw, list):
        if len(scenarios_raw) == 1 and isinstance(scenarios_raw[0], str):
            scenarios_raw = scenarios_raw[0]
        else:
            return scenarios_raw  # type: ignore[return-value]

    if isinstance(scenarios_raw, dict):
        return [scenarios_raw]

    if isinstance(scenarios_raw, str):
        try:
            parsed = json.loads(scenarios_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Scenarios data must be valid JSON") from exc
        if not isinstance(parsed, list):
            raise ValueError("Scenarios data must be a list")
        return parsed

    raise ValueError("Scenarios data must be a list")


def _prepare_omni_scenarios(
    payload: Dict[str, Any],
    raw_json: Any,
    req: 'flask.Request',
    *,
    runid: str,
    config: str,
    wd: str,
) -> list[tuple[OmniScenario, Dict[str, Any]]]:
    scenarios_payload = _coerce_omni_scenario_list(payload, raw_json)
    if scenarios_payload is None:
        raise ValueError("Missing scenarios data")
    if not isinstance(scenarios_payload, list):
        raise ValueError("Scenarios data must be a list")

    os.makedirs(_join(wd, 'omni', '_limbo'), exist_ok=True)

    parsed_inputs: list[tuple[OmniScenario, Dict[str, Any]]] = []
    for idx, scenario in enumerate(scenarios_payload):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario {idx} must be an object")

        scenario_type = scenario.get("type")
        if not scenario_type:
            raise ValueError(f"Scenario {idx} is missing type")

        scenario_enum = OmniScenario.parse(scenario_type)
        scenario_params: Dict[str, Any] = dict(scenario)
        scenario_params["type"] = scenario_type

        if scenario_enum == OmniScenario.SBSmap:
            file_key = f"scenarios[{idx}][sbs_file]"
            storage = req.files.get(file_key)

            if storage and storage.filename:
                try:
                    upload_path = save_run_file(
                        runid=runid,
                        config=config,
                        form_field=file_key,
                        allowed_extensions=SBS_ALLOWED_EXTENSIONS,
                        dest_subdir=f"omni/_limbo/{idx:02d}",
                        run_root=wd,
                        overwrite=True,
                        max_bytes=SBS_MAX_BYTES,
                    )
                except UploadError as exc:
                    raise ValueError(f"Invalid SBS file for scenario {idx}: {exc}") from exc

                scenario_params["sbs_file_path"] = str(upload_path)
            elif scenario_params.get("sbs_file_path"):
                scenario_params["sbs_file_path"] = str(scenario_params["sbs_file_path"])
            else:
                raise ValueError(f"Missing SBS file for scenario {idx}")

            scenario_params.pop("sbs_file", None)

        parsed_inputs.append((scenario_enum, scenario_params))

    return parsed_inputs


rq_api_bp = Blueprint('rq_api', __name__)


def hello_world_rq(runid: str):
    print("====================================================")
    print("hello_world_rq")
    print("====================================================")
    return

    job = get_current_job()
    wd = get_wd(runid)
    func_name = inspect.currentframe().f_code.co_name
    print("====================================================")
    print(f'{func_name}: Hello {runid}')
    print("====================================================")


def report_success(job, connection, result, *args, **kwargs):
    print("====================================================")
    print("report_success")
    print("====================================================")
    print(f'Job {job.id} completed successfully')
    print(f'Result: {result}')
    return result


def report_failure(job, connection, type, value, traceback):
    print("====================================================")
    print("report_failure")
    print("====================================================")
    print(f'Job {job.id} failed')
    print(f'Type: {type}')
    print(f'Value: {value}')
    print(f'Traceback: {traceback}')
    return traceback


def report_stopped(job, connection):
    print("====================================================")
    print("report_stopped")
    print("====================================================")
    print(f'Job {job.id} stopped')
    return job.exc_info


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/hello_world', methods=['GET', 'POST'])
def hello_world(runid, config):
    """
    This is useful for debugging rq worker issues
    """
    try:
        with _redis_conn() as redis_conn:
            q = Queue('m4', connection=redis_conn)
            job = q.enqueue_call(hello_world_rq, (runid,), timeout=TIMEOUT,
              on_success=Callback(report_success),  # default callback timeout (60 seconds)
              on_failure=Callback(report_failure, timeout=10), # 10 seconds timeout
              on_stopped=Callback(report_stopped, timeout="2m")) # 2 minute timeout
    except Exception as e:
        return exception_factory('hello_world Failed', runid=runid)
    
    time.sleep(2)

    return jsonify({'Success': True, 'job_id': job.id, 'exc_info': job.exc_info, 'is_failed': job.is_failed})


@rq_api_bp.route('/batch/_/<string:batch_name>/rq/api/run-batch', methods=['POST'])
@roles_required('Admin')
def api_run_batch(batch_name: str):

    try:
        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
    except FileNotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404

    try:
        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_batch_rq, (batch_name,), timeout=TIMEOUT)
    except Exception:
        return exception_factory('Failed to enqueue batch run', runid=batch_name)

    payload = {
        'success': True,
        'job_id': job.id,
        'message': 'Batch run submitted.',
    }
    return jsonify(payload), 200


def _parse_map_change(payload: Dict[str, Any]):
    center_raw = payload.get('map_center')
    zoom_raw = payload.get('map_zoom')
    bounds_raw = payload.get('map_bounds')
    mcl_raw = payload.get('mcl')
    csa_raw = payload.get('csa')
    wbt_fill_or_breach_raw = payload.get('wbt_fill_or_breach')
    wbt_blc_dist_raw = payload.get('wbt_blc_dist')
    set_extent_mode_raw = payload.get('set_extent_mode', 0)
    map_bounds_text_raw = payload.get('map_bounds_text', '')

    if center_raw is None or zoom_raw is None or bounds_raw is None or mcl_raw is None or csa_raw is None:
        error = error_factory('Expecting center, zoom, bounds, mcl, and csa')
        return error, None

    def _as_float_sequence(value: Any, expected_len: int, label: str) -> list[float]:
        if isinstance(value, (list, tuple)):
            parts = list(value)
        elif isinstance(value, str):
            parts = [part.strip() for part in value.split(',') if part.strip()]
        else:
            raise ValueError(f'Invalid {label} payload.')
        if len(parts) != expected_len:
            raise ValueError(f'{label} must contain {expected_len} values.')
        result: list[float] = []
        for part in parts:
            try:
                result.append(float(part))
            except (TypeError, ValueError) as exc:
                raise ValueError(f'Could not parse {label}.') from exc
        return result

    def _as_float(value: Any, label: str) -> float:
        try:
            if isinstance(value, bool):
                return float(int(value))
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Could not parse {label}.') from exc

    def _as_int(value: Any, label: str) -> int:
        try:
            if isinstance(value, bool):
                return int(value)
            if value is None or value == '':
                raise ValueError(f'Missing {label}.')
            return int(float(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Could not parse {label}.') from exc

    try:
        center = _as_float_sequence(center_raw, 2, 'center')
        extent = _as_float_sequence(bounds_raw, 4, 'bounds')
        zoom = _as_float(zoom_raw, 'zoom')
        mcl = _as_float(mcl_raw, 'mcl')
        csa = _as_float(csa_raw, 'csa')

        l, b, r, t = extent
        if not (l < r and b < t):
            raise ValueError('Invalid bounds ordering.')

        set_extent_mode = _as_int(set_extent_mode_raw, 'set_extent_mode')
        if set_extent_mode not in (0, 1):
            raise ValueError('set_extent_mode must be 0 or 1.')

        if isinstance(wbt_fill_or_breach_raw, (list, tuple)):
            wbt_fill_or_breach = next((str(item) for item in wbt_fill_or_breach_raw if item not in (None, '')), None)
        elif wbt_fill_or_breach_raw in (None, ''):
            wbt_fill_or_breach = None
        else:
            wbt_fill_or_breach = str(wbt_fill_or_breach_raw)

        if wbt_blc_dist_raw in (None, '', []):
            wbt_blc_dist = None
        elif isinstance(wbt_blc_dist_raw, (list, tuple)):
            wbt_blc_dist = _as_int(wbt_blc_dist_raw[0], 'wbt_blc_dist')
        else:
            wbt_blc_dist = _as_int(wbt_blc_dist_raw, 'wbt_blc_dist')

        if isinstance(map_bounds_text_raw, (list, tuple)):
            map_bounds_text_candidates = [item for item in map_bounds_text_raw if item not in (None, '')]
            map_bounds_text = str(map_bounds_text_candidates[0]) if map_bounds_text_candidates else ''
        else:
            map_bounds_text = str(map_bounds_text_raw or '')

    except ValueError as exc:
        error = exception_factory(str(exc))
        return error, None

    return None, [extent, center, zoom, mcl, csa, wbt_fill_or_breach, wbt_blc_dist, set_extent_mode, map_bounds_text]


@rq_api_bp.route('/rq/api/landuse_and_soils', methods=['POST'])
def build_landuse_and_soils():
    uuid = None
    try:
        # assume this POST request has json data. extract extent, cfg (optional), nlcd_db (optional), ssurgo_db (optional)
        data = request.get_json()
        extent = data.get('extent', None)

        print(f'extent: {extent} {type(extent)}')
        
        if extent is None:
            return error_factory('Expecting extent')
        
        cfg = data.get('cfg', None)
        nlcd_db = data.get('nlcd_db', None)
        ssurgo_db = data.get('ssurgo_db', None)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(land_and_soil_rq, (None, extent, cfg, nlcd_db, ssurgo_db), timeout=TIMEOUT)
            uuid = job.id
    except Exception as e:
        return exception_factory('land_and_soil_rq Failed', runid=uuid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/rq/api/landuse_and_soils/<string:uuid>.tar.gz')
def download_landuse_and_soils(uuid):

    if '.' in uuid or '/' in uuid:
        return error_factory('Invalid uuid')
    
    if _exists(f'/wc1/land_and_soil_rq/{uuid}.tar.gz'):
        return send_file(f'/wc1/land_and_soil_rq/{uuid}.tar.gz', as_attachment=True, download_name=f'{uuid}.tar.gz')
    
    if _exists(f'/geodata/wc1/land_and_soil_rq/{uuid}.tar.gz'):
        return send_file(f'/geodata/wc1/land_and_soil_rq/{uuid}.tar.gz', as_attachment=True, download_name=f'{uuid}.tar.gz')
    
    return error_factory('File not found')
        

@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/fetch_dem_and_build_channels', methods=['POST'])
def fetch_dem_and_build_channels(runid, config):
    try:
        payload = parse_request_payload(request)
        error, args = _parse_map_change(payload)

        if error is not None:
            return jsonify(error)

        (extent, center, zoom,
          mcl, csa, 
          wbt_fill_or_breach, wbt_blc_dist, 
          set_extent_mode, map_bounds_text) = args
        wd = get_wd(runid)

        watershed = Watershed.getInstance(wd)
        if watershed.run_group == 'batch':
            with watershed.locked():
                watershed._mcl = mcl
                watershed._csa = csa
                watershed._set_extent_mode = int(set_extent_mode)
                watershed._map_bounds_text = map_bounds_text
                if watershed.delineation_backend_is_wbt:
                    if wbt_fill_or_breach is not None:
                        watershed._wbt_fill_or_breach = wbt_fill_or_breach
                    if wbt_blc_dist is not None:
                        watershed._wbt_blc_dist = wbt_blc_dist
    
            return success_factory('Set watershed inputs for batch processing')

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.fetch_dem)
        prep.remove_timestamp(TaskEnum.build_channels)
        
        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(fetch_dem_and_build_channels_rq, (runid, extent, center, zoom, csa, mcl, wbt_fill_or_breach, wbt_blc_dist, set_extent_mode, map_bounds_text), timeout=TIMEOUT)
            prep.set_rq_job_id('fetch_dem_and_build_channels_rq', job.id)
    except Exception as e:
        if isinstance(e, MinimumChannelLengthTooShortError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('fetch_dem_and_build_channels Failed', runid=runid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/set_outlet', methods=['POST'])
def api_set_outlet(runid, config):
    payload = parse_request_payload(request)

    def _resolve_coordinate(key: str) -> Any:
        value = payload.get(key)
        if value is not None:
            return value
        coordinates = payload.get("coordinates")
        if isinstance(coordinates, dict):
            if key in coordinates:
                return coordinates[key]
            if key == "latitude":
                return coordinates.get("lat")
            if key == "longitude":
                return coordinates.get("lng") or coordinates.get("lon")
        return None

    def _to_float(value: Any) -> float:
        if value is None:
            raise ValueError("missing coordinate")
        if isinstance(value, (list, tuple)):
            if not value:
                raise ValueError("missing coordinate")
            return _to_float(value[0])
        return float(value)

    try:
        outlet_lng = _to_float(_resolve_coordinate("longitude"))
        outlet_lat = _to_float(_resolve_coordinate("latitude"))
    except (TypeError, ValueError):
        return exception_factory('latitude and longitude must be provided as floats', runid=runid)

    try:    
        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.set_outlet)
        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(set_outlet_rq, (runid, outlet_lng, outlet_lat), timeout=TIMEOUT)
            prep.set_rq_job_id('set_outlet_rq', job.id)
    except Exception as e:
        return exception_factory('Could not set outlet', runid=runid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_subcatchments_and_abstract_watershed', methods=['POST'])
def api_build_subcatchments_and_abstract_watershed(runid, config):

    payload = parse_request_payload(
        request,
        boolean_fields=(
            "clip_hillslopes",
            "walk_flowpaths",
            "mofe_buffer",
            "bieger2015_widths",
        ),
    )

    def _to_float(value):
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return _to_float(value[0] if value else None)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_bool(value, default=None):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def _apply_watershed_updates(target: Watershed, updates: dict[str, Any]) -> None:
        if not updates:
            return
        if 'clip_hillslopes' in updates:
            target.clip_hillslopes = bool(updates['clip_hillslopes'])
        if 'walk_flowpaths' in updates:
            target.walk_flowpaths = bool(updates['walk_flowpaths'])
        if 'clip_hillslope_length' in updates:
            target.clip_hillslope_length = float(updates['clip_hillslope_length'])
        if 'mofe_target_length' in updates:
            target.mofe_target_length = float(updates['mofe_target_length'])
        if 'mofe_buffer' in updates:
            target.mofe_buffer = bool(updates['mofe_buffer'])
        if 'mofe_buffer_length' in updates:
            target.mofe_buffer_length = float(updates['mofe_buffer_length'])
        if 'bieger2015_widths' in updates:
            target.bieger2015_widths = bool(updates['bieger2015_widths'])

    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)

        updates: dict[str, Any] = {}

        if 'clip_hillslopes' in payload:
            value = _to_bool(payload.get('clip_hillslopes'))
            if value is not None:
                updates['clip_hillslopes'] = value

        if 'walk_flowpaths' in payload:
            value = _to_bool(payload.get('walk_flowpaths'))
            if value is not None:
                updates['walk_flowpaths'] = value

        if 'clip_hillslope_length' in payload:
            value = _to_float(payload.get('clip_hillslope_length'))
            if value is not None:
                updates['clip_hillslope_length'] = value

        if 'mofe_target_length' in payload:
            value = _to_float(payload.get('mofe_target_length'))
            if value is not None:
                updates['mofe_target_length'] = value

        if 'mofe_buffer' in payload:
            value = _to_bool(payload.get('mofe_buffer'))
            if value is not None:
                updates['mofe_buffer'] = value

        if 'mofe_buffer_length' in payload:
            value = _to_float(payload.get('mofe_buffer_length'))
            if value is not None:
                updates['mofe_buffer_length'] = value

        if 'bieger2015_widths' in payload:
            value = _to_bool(payload.get('bieger2015_widths'))
            if value is not None:
                updates['bieger2015_widths'] = value

        if watershed.run_group == 'batch':
            _apply_watershed_updates(watershed, updates)
            return success_factory('Set watershed inputs for batch processing')

        _apply_watershed_updates(watershed, updates)

        try:
            prep = RedisPrep.getInstance(wd)
            prep.remove_timestamp(TaskEnum.abstract_watershed)
            prep.remove_timestamp(TaskEnum.build_subcatchments)

            with _redis_conn() as redis_conn:
                q = Queue(connection=redis_conn)
                job = q.enqueue_call(
                    build_subcatchments_and_abstract_watershed_rq,
                    (runid,),
                    timeout=TIMEOUT,
                )
                prep.set_rq_job_id('build_subcatchments_and_abstract_watershed_rq', job.id)
        except Exception as e:
            if isinstance(e, WatershedBoundaryTouchesEdgeError):
                return exception_factory(e.__name__, e.__doc__, runid=runid)
            else:
                return exception_factory('Building Subcatchments Failed', runid=runid)
    except:
        return exception_factory('Building Subcatchments Failed', runid=runid)
    
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_landuse', methods=['POST'])
def api_build_landuse(runid, config):
    try:
        wd = get_wd(runid)
        landuse = Landuse.getInstance(wd)

        payload = parse_request_payload(
            request,
            boolean_fields=(
                "checkbox_burn_shrubs",
                "checkbox_burn_grass",
                "burn_shrubs",
                "burn_grass",
            ),
        )

        def _first(value):
            if isinstance(value, (list, tuple)):
                return value[0] if value else None
            return value

        try:
            landuse.parse_inputs(payload)
        except ValueError as exc:
            return exception_factory(str(exc), runid=runid)

        if 'disturbed' in landuse.mods:
            disturbed = Disturbed.getInstance(wd)
            burn_shrubs_value = payload.get('checkbox_burn_shrubs')
            if burn_shrubs_value is None:
                burn_shrubs_value = payload.get('burn_shrubs')
            disturbed.burn_shrubs = bool(burn_shrubs_value)

            burn_grass_value = payload.get('checkbox_burn_grass')
            if burn_grass_value is None:
                burn_grass_value = payload.get('burn_grass')
            disturbed.burn_grass = bool(burn_grass_value)

        mapping = _first(payload.get('landuse_management_mapping_selection'))
        if isinstance(mapping, str):
            mapping = mapping.strip() or None

        # check for file for mode 4, mode is set asynchronously
        if landuse.mode == LanduseMode.UserDefined:
            from wepppy.all_your_base.geo import raster_stacker
            watershed = Watershed.getInstance(wd)

            if mapping is None:
                return error_factory('landuse_management_mapping_selection must be provided')

            landuse.mapping = mapping

            try:
                file = request.files['input_upload_landuse']
            except Exception:
                return exception_factory('Could not find file', runid=runid)

            try:
                if file.filename == '':
                    return error_factory('no filename specified')

                filename = secure_filename(file.filename)
            except Exception:
                return exception_factory('Could not obtain filename', runid=runid)

            user_defined_fn = _join(landuse.lc_dir, f'_{filename}')
            try:
                file.save(_join(landuse.lc_dir, f'_{filename}'))
            except Exception:
                return exception_factory('Could not save file', runid=runid)

            try:
                raster_stacker(user_defined_fn, watershed.subwta, landuse.lc_fn)
            except Exception:
                return exception_factory('Failed validating file', runid=runid)

            if not _exists(landuse.lc_fn):
                return error_factory('Failed creating landuse file')

        if landuse.run_group == 'batch':
            return success_factory('Set landuse inputs for batch processing')

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_landuse_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('build_landuse_rq', job.id)
        
    except Exception as e:
        if isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Landuse Failed', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_treatments', methods=['POST'])
def api_build_treatments(runid, config):
    from wepppy.nodb.mods.treatments import Treatments, TreatmentsMode

    try:
        wd = get_wd(runid)
        treatments = Treatments.getInstance(wd)
        landuse = Landuse.getInstance(wd)

        # check for file for mode 4, mode is set asynchronously
        if treatments.mode == TreatmentsMode.UserDefinedMap:
            from wepppy.all_your_base.geo import raster_stacker
            watershed = Watershed.getInstance(wd)

            mapping = request.form.get('landuse_management_mapping_selection', None)
            if mapping is None:
                return error_factory('landuse_management_mapping_selection must be provided')
            else:
                landuse.mapping = mapping

            try:
                saved_path = save_run_file(
                    runid=runid,
                    config=config,
                    form_field='input_upload_landuse',
                    allowed_extensions=('tif', 'img'),
                    dest_subdir='',
                    run_root=landuse.lc_dir,
                    filename_transform=lambda name: '_' + name.lower(),
                    overwrite=True,
                    max_bytes=100 * 1024 * 1024,
                )
            except UploadError as exc:
                return exception_factory(str(exc), runid=runid)

            user_defined_fn = str(saved_path)

            try:
                raster_stacker(user_defined_fn, watershed.subwta, landuse.lc_fn)
            except Exception:
                return exception_factory('Failed validating file', runid=runid)

            if not _exists(landuse.lc_fn):
                return error_factory('Failed creating landuse file')

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_landuse_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('build_landuse_rq', job.id)
        
    except Exception as e:
        if isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Landuse Failed', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_soils', methods=['POST'])
def api_build_soils(runid, config):
    try:
        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_soils)

        soils = Soils.getInstance(wd)
        initial_sat = float(request.form.get('initial_sat'))
        soils.initial_sat = initial_sat

        if 'disturbed' in soils.mods:
            disturbed = Disturbed.getInstance(wd)
            disturbed.sol_ver = float(request.form.get('sol_ver'))

        if soils.run_group == 'batch':
            return success_factory('Set soils inputs for batch processing')
    
        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_soils_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('build_soils_rq', job.id)
            
    except Exception as e:
        if isinstance(e, NoValidSoilsException) or isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Soil Failed', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_climate', methods=['POST'])
def api_build_climate(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        payload = parse_request_payload(request)
        climate.parse_inputs(payload)
    except Exception:
        return exception_factory('Error parsing climate inputs', runid=runid)

    if climate.run_group == 'batch':
        return success_factory('Set climate inputs for batch processing')

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_climate)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_climate_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('build_climate_rq', job.id)
    except Exception as e:
        if isinstance(e, NoClimateStationSelectedError) or \
           isinstance(e, ClimateModeIsUndefinedError) or \
           isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Error building climate', runid=runid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/post_dss_export_rq', methods=['POST'])
@handle_with_exception_factory
def api_post_dss_export_rq(runid, config):

    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    boolean_fields = {f'dss_export_exclude_order_{i}' for i in range(1, 6)}
    payload = parse_request_payload(request, boolean_fields=boolean_fields)

    def _coerce_int_list(raw_value):
        if raw_value in (None, "", []):
            return []
        if isinstance(raw_value, (list, tuple, set)):
            iterable = raw_value
        else:
            iterable = str(raw_value).split(",")
        seen: set[int] = set()
        result: list[int] = []
        for item in iterable:
            if item in (None, ""):
                continue
            try:
                parsed = int(str(item).strip())
            except (TypeError, ValueError):
                continue
            if parsed not in seen:
                seen.add(parsed)
                result.append(parsed)
        return result

    def _first_value(raw_value):
        if isinstance(raw_value, (list, tuple, set)):
            for candidate in raw_value:
                if candidate not in (None, ""):
                    return candidate
            return None
        return raw_value

    raw_mode = payload.get('dss_export_mode')
    try:
        dss_export_mode = int(raw_mode) if raw_mode not in (None, '') else None
    except (TypeError, ValueError):
        dss_export_mode = None
    if dss_export_mode not in (None, 1, 2):
        dss_export_mode = None

    exclude_orders_payload = payload.get('dss_export_exclude_orders')
    if exclude_orders_payload is not None:
        dss_excluded_channel_orders = [
            order for order in _coerce_int_list(exclude_orders_payload)
            if 1 <= order <= 5
        ]
    else:
        dss_excluded_channel_orders = [
            order for order in range(1, 6)
            if payload.get(f'dss_export_exclude_order_{order}')
        ]

    dss_export_channel_ids_payload = payload.get('dss_export_channel_ids')
    if isinstance(dss_export_channel_ids_payload, dict):
        # Unexpected structure; ignore to avoid raising.
        dss_export_channel_ids = []
    else:
        dss_export_channel_ids = _coerce_int_list(dss_export_channel_ids_payload)

    if dss_export_mode == 2:
        watershed = Watershed.getInstance(wd)
        dss_export_channel_ids = []
        for chn_id, chn_summary in watershed.chns_summary.items():
            if isinstance(chn_summary, PeridotChannel):
                order = int(chn_summary.order)
            else:
                order = int(chn_summary['order'])

            if order in dss_excluded_channel_orders:
                continue
            
            dss_export_channel_ids.append(int(chn_id))

    # this is source of truth for channel ids to export
    dss_export_channel_ids = _dedupe_positive_ints(dss_export_channel_ids)

    try:
        start_date = parse_dss_date(_first_value(payload.get("dss_start_date")))
    except ValueError:
        return error_factory("Invalid DSS start date; use MM/DD/YYYY.")

    try:
        end_date = parse_dss_date(_first_value(payload.get("dss_end_date")))
    except ValueError:
        return error_factory("Invalid DSS end date; use MM/DD/YYYY.")

    if start_date and end_date and start_date > end_date:
        return error_factory("DSS start date must be on or before the end date.")

    with wepp.locked():
        if dss_export_mode is not None:
            wepp._dss_export_mode = dss_export_mode
        wepp._dss_excluded_channel_orders = dss_excluded_channel_orders
        wepp._dss_export_channel_ids = dss_export_channel_ids
        wepp._dss_start_date = format_dss_date(start_date)
        wepp._dss_end_date = format_dss_date(end_date)

    try:
        prep = RedisPrep.getInstance(wd)
   
        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(post_dss_export_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('post_dss_export_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_wepp', methods=['POST'])
def api_run_wepp(runid, config):

    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    boolean_fields = {
        'clip_soils',
        'clip_hillslopes',
        'prep_details_on_run_completion',
        'arc_export_on_run_completion',
        'legacy_arc_export_on_run_completion',
        'dss_export_on_run_completion',
    }
    for i in range(1, 6):
        boolean_fields.add(f'dss_export_exclude_order_{i}')

    payload = parse_request_payload(request, boolean_fields=boolean_fields)
    controller_payload: Dict[str, Any] = dict(payload)

    def pop_scalar(mapping: Dict[str, Any], key: str, default: Any = None) -> Any:
        if key not in mapping:
            return default
        value = mapping.pop(key)
        if isinstance(value, (list, tuple, set)):
            for item in value:
                if item not in (None, ''):
                    return item
            return default
        return value

    def parse_int(value):
        if value in (None, "", False):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def parse_float(value):
        if value in (None, "", False):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    soils = Soils.getInstance(wd)

    clip_soils = bool(pop_scalar(controller_payload, 'clip_soils', False))
    soils.clip_soils = clip_soils

    clip_soils_depth = parse_int(pop_scalar(controller_payload, 'clip_soils_depth'))
    if clip_soils_depth is not None:
        soils.clip_soils_depth = clip_soils_depth

    watershed = Watershed.getInstance(wd)

    clip_hillslopes = bool(pop_scalar(controller_payload, 'clip_hillslopes', False))
    watershed.clip_hillslopes = clip_hillslopes

    clip_hillslope_length = parse_int(pop_scalar(controller_payload, 'clip_hillslope_length'))

    if clip_hillslope_length is not None:
        watershed.clip_hillslope_length = clip_hillslope_length

    initial_sat = parse_float(pop_scalar(controller_payload, 'initial_sat'))

    if initial_sat is not None:
        soils.initial_sat = initial_sat

    reveg_scenario = pop_scalar(controller_payload, 'reveg_scenario', None)
    if isinstance(reveg_scenario, str):
        reveg_scenario = reveg_scenario.strip()

    if reveg_scenario is not None:
        from wepppy.nodb.mods.revegetation import Revegetation
        reveg = Revegetation.getInstance(wd)
        reveg.load_cover_transform(reveg_scenario)

    prep_details_on_run_completion = bool(pop_scalar(controller_payload, 'prep_details_on_run_completion', False))
    arc_export_on_run_completion = bool(pop_scalar(controller_payload, 'arc_export_on_run_completion', False))
    legacy_arc_export_on_run_completion = bool(pop_scalar(controller_payload, 'legacy_arc_export_on_run_completion', False))
    dss_export_on_run_completion = bool(pop_scalar(controller_payload, 'dss_export_on_run_completion', False))

    dss_export_exclude_orders = []
    for i in range(1, 6):
        if bool(pop_scalar(controller_payload, f'dss_export_exclude_order_{i}', False)):
            dss_export_exclude_orders.append(i)

    try:
        wepp.parse_inputs(controller_payload)
    except Exception:
        return exception_factory('Error parsing wepp inputs', runid=runid)

    with wepp.locked():
        wepp._prep_details_on_run_completion = prep_details_on_run_completion
        wepp._arc_export_on_run_completion = arc_export_on_run_completion
        wepp._legacy_arc_export_on_run_completion = legacy_arc_export_on_run_completion
        wepp._dss_export_on_run_completion = dss_export_on_run_completion
        wepp._dss_excluded_channel_orders = dss_export_exclude_orders

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_scenarios)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_wepp_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_wepp_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})


def _task_upload_ash_map(runid, config, file_input_id, *, required=True, overwrite=True):
    wd = get_wd(runid)
    ash = Ash.getInstance(wd)

    storage = request.files.get(file_input_id)
    if storage is None or storage.filename == '':
        if required:
            raise ValueError(f"Missing file for {file_input_id}")
        return None

    try:
        saved_path = save_run_file(
            runid=runid,
            config=config,
            form_field=file_input_id,
            allowed_extensions=("tif", "tiff", "img"),
            dest_subdir=_join("ash"),
            run_root=wd,
            overwrite=overwrite,
            max_bytes=100 * 1024 * 1024,
        )
    except UploadError as exc:
        raise ValueError(str(exc)) from exc

    return saved_path.name


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_omni', methods=['POST'])
def api_run_omni(runid, config):
    wd = get_wd(runid)
    omni = Omni.getInstance(wd)

    try:
        payload = parse_request_payload(request)
        raw_json = request.get_json(silent=True)
        parsed_inputs = _prepare_omni_scenarios(
            payload,
            raw_json,
            request,
            runid=runid,
            config=config,
            wd=wd,
        )
        omni.parse_scenarios(parsed_inputs)

    except ValueError as exc:
        return error_factory(str(exc))
    except Exception as e:
        return exception_factory(f'Error parsing omni inputs: {str(e)}', runid=runid)

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_scenarios)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_omni_scenarios_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_omni_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_omni_contrasts', methods=['POST'])
def run_omni_contrasts(runid, config):
    wd = get_wd(runid)
    omni = Omni.getInstance(wd)

    try:
        payload = parse_request_payload(request)
        raw_json = request.get_json(silent=True)
        parsed_inputs = _prepare_omni_scenarios(
            payload,
            raw_json,
            request,
            runid=runid,
            config=config,
            wd=wd,
        )
        omni.parse_scenarios(parsed_inputs)

    except ValueError as exc:
        return error_factory(str(exc))
    except Exception as e:
        return exception_factory(f'Error parsing omni inputs: {str(e)}', runid=runid)

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni_scenarios)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_omni_scenarios_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_omni_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})

@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_ash', methods=['POST'])
def api_run_ash(runid, config):
    try:
        wd = get_wd(runid)
        payload = parse_request_payload(request)

        mode_raw = payload.get('ash_depth_mode')
        if mode_raw is None:
            return exception_factory("ash_depth_mode is required (0=loads, 1=depths, 2=maps)", runid=runid)
        try:
            ash_depth_mode = int(mode_raw)
        except (TypeError, ValueError):
            return exception_factory("ash_depth_mode must be an integer (0, 1, or 2)", runid=runid)
        if ash_depth_mode not in (0, 1, 2):
            return exception_factory("ash_depth_mode must be 0, 1, or 2", runid=runid)
        payload['ash_depth_mode'] = ash_depth_mode

        fire_date = payload.get('fire_date')

        def _require_float(name):
            value = payload.get(name)
            if value is None:
                raise KeyError(name)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                raise ValueError(name)
            payload[name] = numeric
            return numeric

        if ash_depth_mode == 1:
            try:
                ini_black_ash_depth_mm = _require_float('ini_black_depth')
                ini_white_ash_depth_mm = _require_float('ini_white_depth')
            except KeyError as exc:
                missing = exc.args[0]
                return exception_factory(f"Missing field: {missing} when ash_depth_mode=1", runid=runid)
            except ValueError as exc:
                invalid = exc.args[0]
                return exception_factory(f"Field must be numeric: {invalid}", runid=runid)
        elif ash_depth_mode == 0:
            required = ('ini_black_load', 'ini_white_load', 'field_black_bulkdensity', 'field_white_bulkdensity')
            missing = [name for name in required if payload.get(name) is None]
            if missing:
                return exception_factory(f"Missing fields for ash_depth_mode=0: {', '.join(missing)}", runid=runid)
            try:
                ini_black_load = _require_float('ini_black_load')
                ini_white_load = _require_float('ini_white_load')
                field_black_bulkdensity = _require_float('field_black_bulkdensity')
                field_white_bulkdensity = _require_float('field_white_bulkdensity')
                ini_black_ash_depth_mm = ini_black_load / field_black_bulkdensity
                ini_white_ash_depth_mm = ini_white_load / field_white_bulkdensity
            except ValueError as exc:
                invalid = exc.args[0]
                return exception_factory(f"Field must be numeric: {invalid}", runid=runid)
            except ZeroDivisionError:
                return exception_factory("Bulk density cannot be zero", runid=runid)
        else:  # ash_depth_mode == 2
            ini_black_ash_depth_mm = 3.0  # placeholder; replaced by map inputs
            ini_white_ash_depth_mm = 3.0

        ash = Ash.getInstance(wd)
        ash.parse_inputs(payload)

        if ash_depth_mode == 2:
            with ash.locked():
                ash._spatial_mode = AshSpatialMode.Gridded
                try:
                    ash._ash_load_fn = _task_upload_ash_map(runid, config, 'input_upload_ash_load', required=True)
                except ValueError as exc:
                    return exception_factory(str(exc), runid=runid)

                try:
                    ash._ash_type_map_fn = _task_upload_ash_map(runid, config, 'input_upload_ash_type_map', required=False)
                except ValueError as exc:
                    return exception_factory(str(exc), runid=runid)

            if ash.ash_load_fn is None:
                return exception_factory('Expecting ashload map"', runid=runid)

        ash.ash_depth_mode = ash_depth_mode

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_watar)
        rq_timeout = globals().get('TIMEOUT', 600)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                run_ash_rq,
                (runid, fire_date, float(ini_white_ash_depth_mm), float(ini_black_ash_depth_mm)),
                timeout=rq_timeout
            )
            prep.set_rq_job_id('run_ash_rq', job.id)

        return jsonify(Success=True, job_id=job.id), 200

    except Exception:
        return exception_factory('Error Running Ash Transport', runid=runid)


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_debris_flow', methods=['POST'])
def api_run_debris_flow(runid, config):
    try:
        payload = parse_request_payload(request)

        clay_pct = payload.get('clay_pct')
        liquid_limit = payload.get('liquid_limit')
        datasource = payload.get('datasource')

        if clay_pct is not None:
            try:
                clay_pct = float(clay_pct)
            except (TypeError, ValueError):
                return exception_factory('clay_pct must be numeric', runid=runid)

        if liquid_limit is not None:
            try:
                liquid_limit = float(liquid_limit)
            except (TypeError, ValueError):
                return exception_factory('liquid_limit must be numeric', runid=runid)

        if datasource is not None:
            datasource = str(datasource).strip() or None

        wd = get_wd(runid)

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_debris)

        job_kwargs = None
        if any(value is not None for value in (clay_pct, liquid_limit, datasource)):
            job_options = {}
            if clay_pct is not None:
                job_options['clay_pct'] = clay_pct
            if liquid_limit is not None:
                job_options['liquid_limit'] = liquid_limit
            if datasource is not None:
                job_options['datasource'] = datasource
            job_kwargs = {'payload': job_options}

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                run_debris_flow_rq,
                (runid,),
                kwargs=job_kwargs,
                timeout=TIMEOUT
            )
            prep.set_rq_job_id('run_debris_flow_rq', job.id)

    except Exception:
        return exception_factory('Error Running Debris Flow', runid=runid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_rhem_rq', methods=['POST'])
def api_run_rhem(runid, config):
    try:
        wd = get_wd(runid)
        payload = parse_request_payload(
            request,
            boolean_fields=(
                "clean",
                "clean_hillslopes",
                "prep",
                "prep_hillslopes",
                "run",
                "run_hillslopes",
            ),
        )

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_rhem)

        job_kwargs = None
        if payload:
            job_kwargs = {"payload": payload}

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                run_rhem_rq,
                (runid,),
                kwargs=job_kwargs,
                timeout=TIMEOUT,
            )
            prep.set_rq_job_id('run_rhem_rq', job.id)

    except Exception:
        return exception_factory('Error Running RHEM', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/acquire_rap_ts', methods=['POST'])
def api_rap_ts_acquire(runid, config):
    try:
        raw_json = request.get_json(silent=True)
        payload = parse_request_payload(
            request,
            boolean_fields=("force_refresh",),
        )

        raw_datasets = payload.get("datasets")
        if isinstance(raw_json, dict) and raw_json.get("datasets") is not None:
            raw_datasets = raw_json.get("datasets")
        raw_schedule = payload.get("schedule")
        if isinstance(raw_json, dict) and raw_json.get("schedule") is not None:
            raw_schedule = raw_json.get("schedule")
        raw_force_refresh = payload.get("force_refresh")

        def _normalize_string_list(value):
            if value is None:
                return None
            if isinstance(value, list):
                result = []
                for item in value:
                    if item is None:
                        continue
                    text = str(item).strip()
                    if text:
                        result.append(text)
                return result
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return []
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    return [token for token in (tok.strip() for tok in stripped.split(",")) if token]
                if isinstance(parsed, list):
                    return [
                        str(item).strip()
                        for item in parsed
                        if item is not None and str(item).strip()
                    ]
                if parsed is None:
                    return []
                return [str(parsed).strip()]
            return [str(value).strip()]

        def _normalize_schedule(value):
            if value is None:
                return None
            if isinstance(value, (list, dict)):
                return value
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return []
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError("Schedule payload must be valid JSON.") from exc
                return parsed
            raise ValueError("Schedule payload must be a list, object, or JSON string.")

        datasets = _normalize_string_list(raw_datasets)
        schedule = None
        if raw_schedule is not None:
            try:
                schedule = _normalize_schedule(raw_schedule)
            except ValueError as exc:
                return exception_factory(str(exc), runid=runid)

        force_refresh = None
        if raw_force_refresh is not None:
            force_refresh = bool(raw_force_refresh)

        job_payload: Dict[str, Any] = {}
        if datasets:
            job_payload["datasets"] = datasets
        if schedule not in (None, [], {}):
            job_payload["schedule"] = schedule
        if force_refresh is not None:
            job_payload["force_refresh"] = force_refresh

        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.fetch_rap_ts)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(
                fetch_and_analyze_rap_ts_rq,
                (runid,),
                kwargs={"payload": job_payload} if job_payload else {},
                timeout=TIMEOUT
            )
            prep.set_rq_job_id('fetch_and_analyze_rap_ts_rq', job.id)

    except Exception:
        return exception_factory('Error Running RAP_TS', runid=runid)

    response_payload: Dict[str, Any] = {'Success': True, 'job_id': job.id}
    if job_payload:
        response_payload['payload'] = job_payload

    return jsonify(response_payload)


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/fork', methods=['POST'])
def api_fork(runid, config):
    from wepppy.weppcloud.app import get_run_owners
    from wepppy.weppcloud.app import user_datastore
    try:
        wd = get_wd(runid)
        
        if not _exists(wd):
            return exception_factory('Error forking project, run_id={runid} does not exist', runid=runid)
        
        undisturbify_str = request.form.get("undisturbify", "false")
        undisturbify = undisturbify_str.lower() == "true"

        print(f'undisturbify={undisturbify}')

        requested_runid = request.form.get("target_runid")
        if requested_runid:
            requested_runid = requested_runid.strip()
            if not requested_runid:
                requested_runid = None

        owners = get_run_owners(runid)
        should_abort = True

        if current_user in owners:
            should_abort = False

        if current_user.has_role('Admin'):
            should_abort = False

        if len(owners) == 0:
            should_abort = False

        else:
            ron = Ron.getInstance(wd)
            if ron.public:
                should_abort = False

        if should_abort:
            abort(404)

        dir_created = False
        while not dir_created:
            if requested_runid:
                new_runid = requested_runid
            else:
                new_runid = awesome_codename.generate_codename().replace(' ', '-')

                email = getattr(current_user, 'email', '')
                if email.startswith('rogerlew@'):
                    new_runid = 'rlew-' + new_runid
                elif email.startswith('mdobre@'):
                    new_runid = 'mdobre-' + new_runid
                elif email.startswith('srivas42@'):
                    new_runid = 'srivas42-' + new_runid
                elif request.remote_addr == '127.0.0.1':
                    new_runid = 'devvm-' + new_runid

            new_wd = get_wd(new_runid, prefer_active=False)

            if requested_runid:
                dir_created = True
            else:
                if _exists(new_wd):
                    continue
                if has_archive(runid):
                    continue
                dir_created = True

        if requested_runid:
            parent_dir = os.path.dirname(new_wd.rstrip('/'))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            if _exists(new_wd):
                shutil.rmtree(new_wd)
            os.makedirs(new_wd, exist_ok=True)
        else:
            assert not _exists(new_wd), new_wd

        # add run to database
        register_run = not new_runid.startswith('profile;;')
        if register_run and not current_user.is_anonymous:
            try:
                user_datastore.create_run(new_runid, config, current_user)
            except Exception:
                return exception_factory('Could not add run to user database')

        prep = RedisPrep.getInstance(wd)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(fork_rq, (runid, new_runid, undisturbify), timeout=TIMEOUT)
            prep.set_rq_job_id('fork_rq', job.id)

    except Exception:
        return exception_factory('Error forking project', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id, 'new_runid': new_runid, 'undisturbify': undisturbify})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/archive', methods=['POST'])
def api_archive(runid, config):
    try:
        payload = request.get_json(silent=True) or {}
        comment = payload.get('comment')
        if comment is None:
            comment = request.form.get('comment')

        if comment is not None:
            comment = comment.strip()
            if len(comment) > 40:
                comment = comment[:40]
        else:
            comment = ''

        wd = get_wd(runid)
        if not _exists(wd):
            return exception_factory(f'Project {runid} not found', runid=runid)

        locked = [name for name, state in lock_statuses(runid).items() if name.endswith('.nodb') and state]
        if locked:
            return exception_factory('Cannot archive while files are locked: ' + ', '.join(locked), runid=runid)

        prep = RedisPrep.getInstance(wd)
        existing_job_id = prep.get_archive_job_id()
        if existing_job_id:
            try:
                with _redis_conn() as redis_conn:
                    job = Job.fetch(existing_job_id, connection=redis_conn)
                    status = job.get_status(refresh=True)
            except Exception:
                status = None

            if status in ('queued', 'started', 'deferred'):
                return exception_factory('An archive job is already running for this project', runid=runid)
            else:
                prep.clear_archive_job_id()

        with _redis_conn() as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(archive_rq, (runid, comment), timeout=TIMEOUT)

        prep.set_archive_job_id(job.id)
        StatusMessenger.publish(f'{runid}:archive', f'rq:{job.id} ENQUEUED archive_rq({runid})')

        return jsonify({'Success': True, 'job_id': job.id})
    except Exception:
        return exception_factory('Error enqueueing archive job', runid=runid)


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/restore-archive', methods=['POST'])
@login_required
def api_restore_archive(runid, config):
    try:
        payload = request.get_json(silent=True) or {}
        archive_name = payload.get('archive_name') or request.form.get('archive_name')
        if not archive_name:
            return exception_factory('Missing archive_name parameter', runid=runid)

        wd = get_wd(runid)
        if not _exists(wd):
            return exception_factory(f'Project {runid} not found', runid=runid)

        locked = [name for name, state in lock_statuses(runid).items() if name.endswith('.nodb') and state]
        if locked:
            return exception_factory('Cannot restore while files are locked: ' + ', '.join(locked), runid=runid)

        archive_path = os.path.join(wd, 'archives', archive_name)
        if not os.path.exists(archive_path):
            return exception_factory(f'Archive {archive_name} not found', runid=runid)

        prep = RedisPrep.getInstance(wd)
        existing_job_id = prep.get_archive_job_id()
        if existing_job_id:
            try:
                with _redis_conn() as redis_conn:
                    job = Job.fetch(existing_job_id, connection=redis_conn)
                    status = job.get_status(refresh=True)
            except Exception:
                status = None

            if status in ('queued', 'started', 'deferred'):
                return exception_factory('An archive job is already running for this project', runid=runid)
            else:
                prep.clear_archive_job_id()

        with _redis_conn() as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(restore_archive_rq, (runid, archive_name), timeout=TIMEOUT)

        prep.set_archive_job_id(job.id)
        StatusMessenger.publish(f'{runid}:archive', f'rq:{job.id} ENQUEUED restore_archive_rq({runid}, {archive_name})')

        return jsonify({'Success': True, 'job_id': job.id})
    except Exception:
        return exception_factory('Error enqueueing restore job', runid=runid)


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/delete-archive', methods=['POST'])
@login_required
def api_delete_archive(runid, config):
    try:
        payload = request.get_json(silent=True) or {}
        archive_name = payload.get('archive_name') or request.form.get('archive_name')
        if not archive_name:
            return exception_factory('Missing archive_name parameter', runid=runid)

        wd = get_wd(runid)
        if not _exists(wd):
            return exception_factory(f'Project {runid} not found', runid=runid)

        locked = [name for name, state in lock_statuses(runid).items() if name.endswith('.nodb') and state]
        if locked:
            return exception_factory('Cannot delete while files are locked: ' + ', '.join(locked), runid=runid)

        archive_path = os.path.join(wd, 'archives', archive_name)
        if not os.path.exists(archive_path):
            return exception_factory(f'Archive {archive_name} not found', runid=runid)

        prep = RedisPrep.getInstance(wd)
        existing_job_id = prep.get_archive_job_id()
        if existing_job_id:
            try:
                with _redis_conn() as redis_conn:
                    job = Job.fetch(existing_job_id, connection=redis_conn)
                    status = job.get_status(refresh=True)
            except Exception:
                status = None

            if status in ('queued', 'started', 'deferred'):
                return exception_factory('An archive job is already running for this project', runid=runid)
            else:
                prep.clear_archive_job_id()

        os.remove(archive_path)
        StatusMessenger.publish(f'{runid}:archive', f'Archive deleted: {archive_name}')

        return jsonify({'Success': True})
    except Exception:
        return exception_factory('Error deleting archive', runid=runid)
