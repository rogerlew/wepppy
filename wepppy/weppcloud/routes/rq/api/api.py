import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import awesome_codename

from flask_login import login_required
import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify, send_file

from flask_security import current_user

from werkzeug.utils import secure_filename

from wepppy.weppcloud.utils.helpers import get_wd, success_factory, error_factory, exception_factory
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

from ..._common import roles_required

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


def _parse_map_change(form):

    center = form.get('map_center', None)
    zoom = form.get('map_zoom', None)
    bounds = form.get('map_bounds', None)
    mcl = form.get('mcl', None)
    csa = form.get('csa', None)
    wbt_fill_or_breach = form.get('wbt_fill_or_breach', None)
    wbt_blc_dist = form.get('wbt_blc_dist', None)
    set_extent_mode = form.get('set_extent_mode', 0)
    map_bounds_text = form.get('map_bounds_text', '')

    if center is None or zoom is None or bounds is None \
            or mcl is None or csa is None:
        error = error_factory('Expecting center, zoom, bounds, mcl, and csa')
        return error, None
    try:
        center = [float(v) for v in center.split(',')]
        zoom = float(zoom)
        extent = [float(v) for v in bounds.split(',')]
        assert len(extent) == 4
        l, b, r, t = extent
        assert l < r and b < t, (l, b, r, t)
    except Exception:
        error = exception_factory('Could not parse center, zoom, and/or bounds')
        return error, None

    try:
        mcl = float(mcl)
    except Exception:
        error = exception_factory('Could not parse mcl')
        return error, None

    try:
        csa = float(csa)
    except Exception:
        error = exception_factory('Could not parse csa')
        return error, None

    return None,  [extent, center, zoom, mcl, csa, wbt_fill_or_breach, wbt_blc_dist, set_extent_mode, map_bounds_text]


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
        error, args = _parse_map_change(request.form)

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
    try:
        outlet_lng = float(request.form.get('longitude', None))
        outlet_lat = float(request.form.get('latitude', None))
    except Exception:
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

    pkcsa = request.form.get('pkcsa', None)
    try:
        pkcsa = float(pkcsa)
    except:
        pass

    clip_hillslope_length = request.form.get('clip_hillslope_length', None)
    try:
        clip_hillslope_length = float(clip_hillslope_length)
    except:
        pass

    clip_hillslopes = request.form.get('clip_hillslopes', 'off')
    try:
        clip_hillslopes = clip_hillslopes.lower().startswith('on')
    except:
        pass

    walk_flowpaths = request.form.get('walk_flowpaths', 'off')
    try:
        walk_flowpaths = walk_flowpaths.lower().startswith('on')
    except:
        pass

    mofe_target_length = request.form.get('mofe_target_length', None)
    try:
        mofe_target_length = float(mofe_target_length)
    except:
        pass

    mofe_buffer = request.form.get('mofe_buffer', 'off')
    try:
        mofe_buffer = mofe_buffer.lower().startswith('on')
    except:
        pass

    bieger2015_widths = request.form.get('bieger2015_widths', 'off')
    try:
        bieger2015_widths = bieger2015_widths.lower().startswith('on')
    except:
        pass

    mofe_buffer_length = request.form.get('mofe_buffer_length', None)
    try:
        mofe_buffer_length = float(mofe_buffer_length)
    except:
        pass

    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        wepp = Watershed.getInstance(wd)

        if clip_hillslopes is not None:
            watershed.clip_hillslopes = clip_hillslopes

        if walk_flowpaths is not None:
            watershed.walk_flowpaths = walk_flowpaths

        if clip_hillslope_length is not None:
            watershed.clip_hillslope_length = clip_hillslope_length

        if mofe_target_length is not None:
            watershed.mofe_target_length = mofe_target_length

        if mofe_buffer is not None:
            watershed.mofe_buffer = mofe_buffer

        if mofe_buffer_length is not None:
            watershed.mofe_buffer_length = mofe_buffer_length

        if bieger2015_widths is not None:
            watershed.bieger2015_widths = bieger2015_widths

        if watershed.run_group == 'batch':
            return success_factory('Set watershed inputs for batch processing')
        
        try:    
            prep = RedisPrep.getInstance(wd)
            prep.remove_timestamp(TaskEnum.abstract_watershed)
            prep.remove_timestamp(TaskEnum.build_subcatchments)

            with _redis_conn() as redis_conn:
                q = Queue(connection=redis_conn)
                job = q.enqueue_call(build_subcatchments_and_abstract_watershed_rq, (runid,), timeout=TIMEOUT)
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

#        for k,v in request.form.items():
#            print(f'{k}={v}')
#[Fri Apr 25 12:13:11.207539 2025] [wsgi:error] [pid 2459502:tid 137065371985600] [remote 192.168.1.1:26513] landuse_mode=4
#[Fri Apr 25 12:13:11.207675 2025] [wsgi:error] [pid 2459502:tid 137065371985600] [remote 192.168.1.1:26513] landuse_db=locales/earth/C3Slandcover/2020
#[Fri Apr 25 12:13:11.207702 2025] [wsgi:error] [pid 2459502:tid 137065371985600] [remote 192.168.1.1:26513] landuse_management_mapping_selection=disturbed

        mofe_buffer_selection = request.form.get('mofe_buffer_selection', None)
        try:
            mofe_buffer_selection = int(mofe_buffer_selection)
        except:
            pass

        if mofe_buffer_selection is not None:
            landuse.mofe_buffer_selection = mofe_buffer_selection

        if 'disturbed' in landuse.mods:
            disturbed = Disturbed.getInstance(wd)
            burn_shrubs = request.form.get('burn_shrubs', 'off')
            if burn_shrubs.lower().startswith('on'):
                disturbed.burn_shrubs = True
            else:
                disturbed.burn_shrubs = False

            burn_grass = request.form.get('burn_grass', 'off')
            if burn_grass.lower().startswith('on'):
                disturbed.burn_grass = True
            else:
                disturbed.burn_grass = False

        # get mapping selection for user-defined landuse
        mapping = request.form.get('landuse_management_mapping_selection', None)

        # check for file for mode 4, mode is set asynchronously
        if landuse.mode == LanduseMode.UserDefined:
            from wepppy.all_your_base.geo import raster_stacker
            watershed = Watershed.getInstance(wd)

            if mapping is None:
                return error_factory('landuse_management_mapping_selection must be provided')
            else:
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
        climate.parse_inputs(request.form)
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
def api_post_dss_export_rq(runid, config):

    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    try:
        dss_export_mode = request.form.get('dss_export_mode', None)
        if dss_export_mode is not None:
            dss_export_mode = int(dss_export_mode)
    except:
        dss_export_mode = None

    try:
        dss_excluded_channel_orders = []
        for i in range(1, 6):
            if request.form.get(f'dss_export_exclude_order_{i}') == 'on':
                dss_excluded_channel_orders.append(i)
    except:
        dss_excluded_channel_orders = None

    try:
        dss_export_channel_ids = request.form.get('dss_export_channel_ids', None)
        if dss_export_channel_ids is not None:
            dss_export_channel_ids = [int(i) for i in dss_export_channel_ids.split(',')]
    except:
        dss_export_channel_ids = None


    if dss_export_mode == 2:
        dss_export_channel_ids = []

        watershed = Watershed.getInstance(wd)
        for chn_id, chn_summary in watershed.chns_summary.items():
            order = int(chn_summary['order'])
            if order in dss_excluded_channel_orders:
                continue
            dss_export_channel_ids.append(int(chn_id))

    with wepp.locked():
        if dss_export_mode is not None:
            wepp._dss_export_mode = dss_export_mode
        if dss_excluded_channel_orders is not None:
            wepp._dss_excluded_channel_orders = dss_excluded_channel_orders
        if dss_export_channel_ids is not None:
            wepp._dss_export_channel_ids = dss_export_channel_ids
    
    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_wepp_hillslopes)
        prep.remove_timestamp(TaskEnum.run_wepp_watershed)

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

    try:
        wepp.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing wepp inputs', runid=runid)

    soils = Soils.getInstance(wd)

    try:
        clip_soils = request.form.get('clip_soils') == 'on'
    except:
        clip_soils = None

    if clip_soils is not None:
        soils.clip_soils = clip_soils

    try:
        clip_soils_depth = int(request.form.get('clip_soils_depth'))
    except:
        clip_soils_depth = None

    if clip_soils_depth is not None:
        soils.clip_soils_depth = clip_soils_depth

    watershed = Watershed.getInstance(wd)

    try:
        clip_hillslopes = request.form.get('clip_hillslopes') == 'on'
    except:
        clip_hillslopes = None

    if clip_hillslopes is not None:
        watershed.clip_hillslopes = clip_hillslopes

    try:
        clip_hillslope_length = int(request.form.get('clip_hillslope_length'))
    except:
        clip_hillslope_length = None

    if clip_hillslope_length is not None:
        watershed.clip_hillslope_length = clip_hillslope_length

    try:
        initial_sat = float(request.form.get('initial_sat'))
    except:
        initial_sat = None

    if initial_sat is not None:
        soils.initial_sat = initial_sat

    try:
        reveg_scenario = request.form.get('reveg_scenario', None)
    except:
        reveg_scenario = None

    if reveg_scenario is not None:
        from wepppy.nodb.mods.revegetation import Revegetation
        reveg = Revegetation.getInstance(wd)
        reveg.load_cover_transform(reveg_scenario)

    try:
        prep_details_on_run_completion = request.form.get('prep_details_on_run_completion') == 'on'
    except:
        prep_details_on_run_completion = None

    try:
        arc_export_on_run_completion = request.form.get('arc_export_on_run_completion') == 'on'
    except:
        arc_export_on_run_completion = None

    try:
        legacy_arc_export_on_run_completion = request.form.get('legacy_arc_export_on_run_completion') == 'on'
    except:
        legacy_arc_export_on_run_completion = None

    try:
        dss_export_on_run_completion = request.form.get('dss_export_on_run_completion') == 'on'
    except:
        dss_export_on_run_completion = None


    try:
        dss_export_exclude_orders = []
        for i in range(1, 6):
            if request.form.get(f'dss_export_exclude_order_{i}') == 'on':
                dss_export_exclude_orders.append(i)
    except:
        dss_export_exclude_orders = None

    with wepp.locked():
        if prep_details_on_run_completion is not None:
            wepp._prep_details_on_run_completion = prep_details_on_run_completion

        if arc_export_on_run_completion is not None:
            wepp._arc_export_on_run_completion = arc_export_on_run_completion

        if legacy_arc_export_on_run_completion is not None:
            wepp._legacy_arc_export_on_run_completion = legacy_arc_export_on_run_completion

        if dss_export_on_run_completion is not None:
            wepp._dss_export_on_run_completion = dss_export_on_run_completion

        if dss_export_exclude_orders is not None:
            wepp._dss_export_exclude_orders = dss_export_exclude_orders

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_wepp_hillslopes)
        prep.remove_timestamp(TaskEnum.run_wepp_watershed)

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
        # Ensure the _limbo directory exists
        limbo_dir = _join(wd, 'omni', '_limbo')
        os.makedirs(limbo_dir, exist_ok=True)

        # Parse the scenarios JSON from FormData
        if 'scenarios' not in request.form:
            return exception_factory('Missing scenarios data', runid=runid)
        
        scenarios_data = json.loads(request.form['scenarios'])
        if not isinstance(scenarios_data, list):
            return exception_factory('Scenarios data must be a list', runid=runid)

        # Process each scenario and handle file uploads
        parsed_inputs = []
        for idx, scenario in enumerate(scenarios_data):
            scenario_type = scenario.get('type')

            # Map scenario type to OmniScenario enum
            scenario_enum = OmniScenario.parse(scenario_type)

            # Handle file uploads for SBS Map scenario
            # place the maps in {wd}/omni/.limbo/{idx:02d} so they are available for Omni
            scenario_params = scenario.copy()
            if scenario_enum == OmniScenario.SBSmap:
                file_key = f'scenarios[{idx}][sbs_file]'
                if file_key not in request.files:
                    return exception_factory(f'Missing SBS file for scenario {idx}', runid=runid)

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
                    return error_factory(f'Invalid SBS file for scenario {idx}: {exc}')

                scenario_params['sbs_file_path'] = str(upload_path)

            parsed_inputs.append((scenario_enum, scenario_params))

        # Pass the parsed scenarios to omni.parse_inputs
        omni.parse_scenarios(parsed_inputs)

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
        # Ensure the _limbo directory exists
        limbo_dir = _join(wd, 'omni', '_limbo')
        os.makedirs(limbo_dir, exist_ok=True)

        # Parse the scenarios JSON from FormData
        if 'scenarios' not in request.form:
            return exception_factory('Missing scenarios data', runid=runid)
        
        scenarios_data = json.loads(request.form['scenarios'])
        if not isinstance(scenarios_data, list):
            return exception_factory('Scenarios data must be a list', runid=runid)

        # Process each scenario and handle file uploads
        parsed_inputs = []
        for idx, scenario in enumerate(scenarios_data):
            scenario_type = scenario.get('type')

            # Map scenario type to OmniScenario enum
            scenario_enum = OmniScenario.parse(scenario_type)

            # Handle file uploads for SBS Map scenario
            # place the maps in {wd}/omni/.limbo/{idx:02d} so they are available for Omni
            scenario_params = scenario.copy()
            if scenario_enum == OmniScenario.SBSmap:
                file_key = f'scenarios[{idx}][sbs_file]'
                if file_key not in request.files:
                    return exception_factory(f'Missing SBS file for scenario {idx}', runid=runid)

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
                    return error_factory(f'Invalid SBS file for scenario {idx}: {exc}')

                scenario_params['sbs_file_path'] = str(upload_path)

            parsed_inputs.append((scenario_enum, scenario_params))

        # Pass the parsed scenarios to omni.parse_inputs
        omni.parse_scenarios(parsed_inputs)

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
        form = request.form

        # ash_depth_mode
        mode_raw = form.get('ash_depth_mode')
        if mode_raw is None:
            return exception_factory("ash_depth_mode is required (1=depths, 2=loads)", runid=runid)
        try:
            ash_depth_mode = int(mode_raw)
        except ValueError:
            return exception_factory("ash_depth_mode must be an integer (1 or 2)", runid=runid)
        if ash_depth_mode not in (0, 1, 2):
            return exception_factory("ash_depth_mode must be 0, 1, or 2", runid=runid)

        fire_date = form.get('fire_date')

        # Gather numeric fields
        def _req_float(name):
            v = form.get(name)
            if v is None:
                raise KeyError(name)
            try:
                return float(v)
            except ValueError:
                raise ValueError(name)

        if ash_depth_mode == 1:
            try:
                ini_black_ash_depth_mm = _req_float('ini_black_depth')
                ini_white_ash_depth_mm = _req_float('ini_white_depth')
            except KeyError as k:
                return exception_factory(f"Missing field: {k.args[0]} when ash_depth_mode=1", runid=runid)
            except ValueError as k:
                return exception_factory(f"Field must be numeric: {k.args[0]}", runid=runid)
        elif ash_depth_mode == 0:
            # mode 2: convert loads to depths using bulk densities
            required = ('ini_black_load', 'ini_white_load', 'field_black_bulkdensity', 'field_white_bulkdensity')
            missing = [n for n in required if form.get(n) is None]
            if missing:
                return exception_factory(f"Missing fields for ash_depth_mode=2: {', '.join(missing)}", runid=runid)
            try:
                ini_black_ash_depth_mm = float(form['ini_black_load']) / float(form['field_black_bulkdensity'])
                ini_white_ash_depth_mm = float(form['ini_white_load']) / float(form['field_white_bulkdensity'])
            except ValueError:
                return exception_factory('All mode 2 fields must be numeric"', runid=runid)
            except ZeroDivisionError:
                return exception_factory('Bulk density cannot be zero"', runid=runid)
        else:  # ash_depth_mode == 2
            ini_black_ash_depth_mm = 3.0  # dummy values, will be replaced by ash load map
            ini_white_ash_depth_mm = 3.0  # dummy values, will be replaced by ash load map

        # Parse and persist other inputs
        ash = Ash.getInstance(wd)
        ash.parse_inputs(dict(form))

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
        
        # remember mode for the view
        ash.ash_depth_mode = ash_depth_mode

        # RQ job
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

    except Exception as e:
        return exception_factory('Error Running Ash Transport', runid=runid)


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_debris_flow', methods=['POST'])
def api_run_debris_flow(runid, config):

    try:
        wd = get_wd(runid)
        
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_debris)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_debris_flow_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_debris_flow_rq', job.id)

    except Exception:
        return exception_factory('Error Running Debris Flow', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_rhem_rq', methods=['POST'])
def api_run_rhem(runid, config):
    try:
        wd = get_wd(runid)
        
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_rhem)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_rhem_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_rhem_rq', job.id)

    except Exception:
        return exception_factory('Error Running RHEM', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/acquire_rap_ts', methods=['POST'])
def api_rap_ts_acquire(runid, config):
    try:
        wd = get_wd(runid)
        
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.fetch_rap_ts)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(fetch_and_analyze_rap_ts_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('fetch_and_analyze_rap_ts_rq', job.id)

    except Exception:
        return exception_factory('Error Running RAP_TS', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


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

            new_wd = get_wd(new_runid)
            if _exists(new_wd):
                continue

            if has_archive(runid):
                continue

            dir_created = True

        assert not _exists(new_wd), new_wd

        # add run to database
        if not current_user.is_anonymous:
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
