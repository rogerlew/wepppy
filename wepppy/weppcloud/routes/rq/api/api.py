import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify

from utils.helpers import get_wd, htmltree, error_factory, exception_factory

import redis
from rq import Queue
from rq.job import Job

from wepppy.nodb import Wepp, Soils, Watershed
from wepppy.nodb.redis_prep import RedisPrep

from wepppy.rq.wepp_rq import run_wepp_rq

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

rq_api_bp = Blueprint('rq_api', __name__)


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
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue(run_wepp_rq, runid)
            prep = RedisPrep.getInstance(wd)
            prep.remove_timestamp('run_wepp')
            prep.set_rq_job_id('run_wepp_rq', job.id)
    except Exception:
        return exception_factory()

    return jsonify({'Success': True, 'job_id': job.id})

