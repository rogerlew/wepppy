import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify
from werkzeug.utils import secure_filename

from utils.helpers import get_wd, success_factory, error_factory, exception_factory

import redis
from rq import Queue
from rq.job import Job

from wepppy.soils.ssurgo import NoValidSoilsException

from wepppy.nodb import Wepp, Soils, Watershed, Climate, Disturbed, Landuse, Ron, Ash, AshSpatialMode
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
    fetch_and_analyze_rap_ts_rq
)
from wepppy.rq.wepp_rq import run_wepp_rq

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


REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

rq_api_bp = Blueprint('rq_api', __name__)

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
            job = q.enqueue_call(fetch_dem_and_build_channels_rq, (runid, extent, center, zoom, csa, mcl))
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
            job = q.enqueue_call(set_outlet_rq, (runid, outlet_lng, outlet_lat))
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
                job = q.enqueue_call(build_subcatchments_and_abstract_watershed_rq, (runid,))
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
    mofe_buffer_selection = request.form.get('mofe_buffer_selection', None)
    try:
        mofe_buffer_selection = int(mofe_buffer_selection)
    except:
        pass

    try:
        wd = get_wd(runid)
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)

        landuse = Landuse.getInstance(wd)

        if mofe_buffer_selection is not None:
            landuse.mofe_buffer_selection = mofe_buffer_selection

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(build_landuse_rq, (runid,))
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
            job = q.enqueue_call(build_soils_rq, (runid,))
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
            job = q.enqueue_call(build_climate_rq, (runid,))
            prep.set_rq_job_id('build_climate_rq', job.id)
    except Exception as e:
        if isinstance(e, NoClimateStationSelectedError) or \
           isinstance(e, ClimateModeIsUndefinedError) or \
           isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Error building climate', runid=runid)

    return jsonify({'Success': True, 'job_id': job.id})


@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/run_wepp', methods=['POST'])
def api_run_wepp(runid, config):

    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    try:
        wepp.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing climate inputs', runid=runid)

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
        wepp.lock()
        if prep_details_on_run_completion is not None:
            wepp._prep_details_on_run_completion = prep_details_on_run_completion

        if arc_export_on_run_completion is not None:
            wepp._arc_export_on_run_completion = arc_export_on_run_completion

        if legacy_arc_export_on_run_completion is not None:
            wepp._legacy_arc_export_on_run_completion = legacy_arc_export_on_run_completion

        wepp.dump_and_unlock()
    except:
        wepp.unlock('-f')
        return exception_factory()

    try:
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.run_wepp)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(run_wepp_rq, (runid,))
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
            job = q.enqueue_call(run_ash_rq, (runid, fire_date, float(ini_white_ash_depth_mm), float(ini_black_ash_depth_mm)))
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
            job = q.enqueue_call(run_debris_flow_rq, (runid,))
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
            job = q.enqueue_call(run_rhem_rq, (runid,))
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
            job = q.enqueue_call(fetch_and_analyze_rap_ts_rq, (runid,))
            prep.set_rq_job_id('fetch_and_analyze_rap_ts_rq', job.id)

    except Exception:
        return exception_factory('Error Running RAP_TS', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})
