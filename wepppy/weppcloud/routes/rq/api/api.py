import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import awesome_codename

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify, send_file

from flask_security import current_user

from werkzeug.utils import secure_filename

from wepppy.weppcloud.utils.helpers import get_wd, success_factory, error_factory, exception_factory

import redis
from rq import Queue, Callback
from rq.job import Job

from wepppy.soils.ssurgo import NoValidSoilsException

from wepppy.nodb import Wepp, Soils, Watershed, Climate, Disturbed, Landuse, Ron, Ash, AshSpatialMode, Omni, LanduseMode, OmniScenario
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

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
    fork_rq
)
from wepppy.rq.wepp_rq import run_wepp_rq, post_dss_export_rq
from wepppy.rq.omni_rq import run_omni_rq
from wepppy.rq.land_and_soil_rq import land_and_soil_rq

from wepppy.topo.watershed_abstraction import (
    ChannelRoutingError,
)

from wepppy.topo.topaz import (
    WatershedBoundaryTouchesEdgeError,
    MinimumChannelLengthTooShortError
)

from wepppy.nodb.climate import (
    Climate,
    ClimateStationMode,
    NoClimateStationSelectedError,
    ClimateModeIsUndefinedError
)

from wepppy.nodb.watershed import (
    Watershed,
    WatershedNotAbstractedError
)

from wepppy.all_your_base import isint, isfloat

from wepppy.weppcloud.utils.archive import has_archive

from wepppy.nodb.status_messenger import StatusMessenger

import inspect
import time
from rq import Queue, get_current_job

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 216_000

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
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue('m4', connection=redis_conn)
            job = q.enqueue_call(hello_world_rq, (runid,), timeout=TIMEOUT,
              on_success=Callback(report_success),  # default callback timeout (60 seconds)
              on_failure=Callback(report_failure, timeout=10), # 10 seconds timeout
              on_stopped=Callback(report_stopped, timeout="2m")) # 2 minute timeout
    except Exception as e:
        return exception_factory('hello_world Failed', runid=runid)
    
    time.sleep(2)

    return jsonify({'Success': True, 'job_id': job.id, 'exc_info': job.exc_info, 'is_failed': job.is_failed})


def _parse_map_change(form):

    center = form.get('map_center', None)
    zoom = form.get('map_zoom', None)
    bounds = form.get('map_bounds', None)
    mcl = form.get('mcl', None)
    csa = form.get('csa', None)

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

    return None,  [extent, center, zoom, mcl, csa]


@rq_api_bp.route('/rq/api/landuse_and_soils', methods=['POST'])
def build_landuse_and_soils():
    uuid = None
    try:
        # assume this POST request has json data. extract extent, cfg (optional), nlcd_db (optional), ssurgo_db (optional)
        data = request.get_json()
        extent = data.get('extent', None)

        print(f'extent: {extent}')
        
        if extent is None:
            return error_factory('Expecting extent')
        
        cfg = data.get('cfg', None)
        nlcd_db = data.get('nlcd_db', None)
        ssurgo_db = data.get('ssurgo_db', None)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(land_and_soil_rq, (extent, cfg, nlcd_db, ssurgo_db), timeout=TIMEOUT)
            uuid = job.id
    except Exception as e:
        return exception_factory('land_and_soil_rq Failed', runid=uuid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/rq/api/landuse_and_soils/{uuid}')
def download_landuse_and_soils(uuid):

    if '.' in uuid or '/' in uuid:
        return error_factory('Invalid uuid')
    
    if _exists(f'/wc1/land_and_soil_rq/{uuid}.tar.gz'):
        return send_file(f'/wc1/land_and_soil_rq/{uuid}.tar.gz', as_attachment=True)
        

@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/fetch_dem_and_build_channels', methods=['POST'])
def fetch_dem_and_build_channels(runid, config):
    try:
        error, args = _parse_map_change(request.form)

        if error is not None:
            return jsonify(error)

        extent, center, zoom, mcl, csa = args

        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.fetch_dem)
        prep.remove_timestamp(TaskEnum.build_channels)
        
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(fetch_dem_and_build_channels_rq, (runid, extent, center, zoom, csa, mcl), timeout=TIMEOUT)
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
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        try:    
            prep = RedisPrep.getInstance(wd)
            prep.remove_timestamp(TaskEnum.abstract_watershed)
            prep.remove_timestamp(TaskEnum.build_subcatchments)

            with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_climate)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

    wepp.lock()

    try:
        if dss_export_mode is not None:
            wepp._dss_export_mode = dss_export_mode
        if dss_excluded_channel_orders is not None:
            wepp._dss_excluded_channel_orders = dss_excluded_channel_orders
        if dss_export_channel_ids is not None:
            wepp._dss_export_channel_ids = dss_export_channel_ids
        wepp.dump_and_unlock()
    except Exception:
        wepp.unlock('-f')
        return exception_factory('Error setting dss export mode', runid=runid)
    
    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_wepp)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

    try:
        wepp.lock()
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

        wepp.dump_and_unlock()
    except:
        wepp.unlock('-f')
        return exception_factory()

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_wepp)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_wepp_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_wepp_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})


def _task_upload_ash_map(wd, request, file_input_id):
    ash = Ash.getInstance(wd)

    file = request.files[file_input_id]
    if file.filename == '':
        return None

    filename = secure_filename(file.filename)
    file.save(_join(ash.ash_dir, filename))

    return filename


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_omni', methods=['POST'])
def api_run_omni(runid, config):
    wd = get_wd(runid)
    omni = Omni.getInstance(wd)

    try:
        # Ensure the .limbo directory exists
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
            if not scenario_type:
                continue  # Skip invalid scenarios

            # Map scenario type to OmniScenario enum
            scenario_enum = OmniScenario.parse(scenario_type)

            # Handle file uploads for SBS Map scenario
            # place the maps in {wd}/omni/.limbo/{idx:02d} so they are available for Omni
            scenario_params = scenario.copy()
            if scenario_enum == OmniScenario.SBSmap:
                file_key = f'scenarios[{idx}][sbs_file]'
                if file_key not in request.files:
                    return exception_factory(f'Missing SBS file for scenario {idx}', runid=runid)

                file = request.files[file_key]
                if file.filename == '':
                    return error_factory('No filename specified for SBS file')

                # Securely save the file to wd/omni/.limbo/SBSmap
                filename = secure_filename(file.filename)
                scenario_dir = os.path.join(limbo_dir, f'{idx:02d}')
                os.makedirs(scenario_dir, exist_ok=True)
                file_path = os.path.join(scenario_dir, filename)
                file.save(file_path)

                # Update scenario params with the file path
                scenario_params['sbs_file_path'] = file_path

            parsed_inputs.append((scenario_enum, scenario_params))

        # Pass the parsed scenarios to omni.parse_inputs
        omni.parse_scenarios(parsed_inputs)

    except Exception as e:
        return exception_factory(f'Error parsing omni inputs: {str(e)}', runid=runid)

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_omni)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_omni_rq, (runid,), timeout=TIMEOUT)
            prep.set_rq_job_id('run_omni_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_ash', methods=['POST'])
def api_run_ash(runid, config):
    # get working dir of original directory
    wd = get_wd(runid)

    #return jsonify(request.form)
    '''
    {
      "ash_depth_mode": "1", 
      "field_black_bulkdensity": "0.31", 
      "field_white_bulkdensity": "0.14", 
      "fire_date": "8/13", 
      "ini_black_depth": "15", 
      "ini_black_load": "1.55", 
      "ini_white_depth": "15", 
      "ini_white_load": "0.7000000000000001"
    }
    '''

    fire_date = request.form.get('fire_date', None)
    ash_depth_mode = request.form.get('ash_depth_mode', None)
    ini_black_ash_depth_mm = request.form.get('ini_black_depth', None)
    ini_white_ash_depth_mm = request.form.get('ini_white_depth', None)
    ini_black_ash_load_kgm2 = request.form.get('ini_black_load', None)
    ini_white_ash_load_kgm2 = request.form.get('ini_white_load', None)
    field_black_ash_bulkdensity = request.form.get('field_black_bulkdensity', None)
    field_white_ash_bulkdensity = request.form.get('field_white_bulkdensity', None)

    try:
        assert isint(ash_depth_mode), ash_depth_mode

        if int(ash_depth_mode) == 1:
            assert isfloat(ini_black_ash_depth_mm), ini_black_ash_depth_mm
            assert isfloat(ini_white_ash_depth_mm), ini_white_ash_depth_mm
        else:
            assert isfloat(ini_black_ash_load_kgm2), ini_black_ash_load_kgm2
            assert isfloat(ini_white_ash_load_kgm2), ini_white_ash_load_kgm2
            assert isfloat(field_black_ash_bulkdensity), field_black_ash_bulkdensity
            assert isfloat(field_white_ash_bulkdensity), field_white_ash_bulkdensity

            ini_black_ash_depth_mm = float(ini_black_ash_load_kgm2) / float(field_black_ash_bulkdensity)
            ini_white_ash_depth_mm = float(ini_white_ash_load_kgm2) / float(field_white_ash_bulkdensity)

        ash = Ash.getInstance(wd)

        if request.method == 'POST':
            ash.parse_inputs(dict(request.form))
            ash = Ash.getInstance(wd)

        if int(ash_depth_mode) == 2:
          
            ash.lock()

            try:
                ash._spatial_mode = AshSpatialMode.Gridded
                ash._ash_load_fn = _task_upload_ash_map(wd, request, 'input_upload_ash_load')
                ash._ash_type_map_fn = _task_upload_ash_map(wd, request, 'input_upload_ash_type_map')
                ash.dump_and_unlock()
            except Exception:
                ash.unlock('-f')
                raise

            if ash.ash_load_fn is None:
                raise Exception('Expecting ashload map')

        ash.ash_depth_mode = 1

        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_watar)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_ash_rq, (runid, fire_date, float(ini_white_ash_depth_mm), float(ini_black_ash_depth_mm)), timeout=TIMEOUT)
            prep.set_rq_job_id('run_ash_rq', job.id)

    except Exception as e:
        return exception_factory('Error Running Ash Transport', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_debris_flow', methods=['POST'])
def api_run_debris_flow(runid, config):

    try:
        wd = get_wd(runid)
        
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_debris)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
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

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(fork_rq, (runid, new_runid, undisturbify), timeout=TIMEOUT)
            prep.set_rq_job_id('fork_rq', job.id)

    except Exception:
        return exception_factory('Error forking project', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id, 'new_runid': new_runid, 'undisturbify': undisturbify})


