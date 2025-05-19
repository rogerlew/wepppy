import shutil
from glob import glob

import socket
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import inspect
import time

from functools import wraps
from subprocess import Popen, PIPE, call

import redis
from rq import Queue, get_current_job

from wepppy.weppcloud.utils.helpers import get_wd

from wepp_runner import (
    run_ss_batch_hillslope,
    run_hillslope,
    run_flowpath,
    run_watershed,
    run_ss_batch_watershed,
)

from wepppy.nodb import Disturbed, Ron, Wepp, Watershed, Climate, ClimateMode, WeppPost
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.nodb.status_messenger import StatusMessenger

from wepppy.export.prep_details import (
    export_channels_prep_details,
    export_hillslopes_prep_details
)

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 43_200

def compress_fn(fn):
    if _exists(fn):
        p = call('gzip %s -f' % fn, shell=True)
        assert _exists(fn + '.gz')

# turtles, turtles all the way down...

def run_ss_batch_hillslope_rq(runid, wepp_id, wepp_bin=None, ss_batch_id=None):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
        status, wepp_id, time = run_ss_batch_hillslope(wepp_id, runs_dir, wepp_bin=wepp_bin, ss_batch_id=ss_batch_id, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id}) -> ({status}, {time})')
        return status, time
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
        raise

def run_hillslope_rq(runid, wepp_id, wepp_bin=None):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin})')
        status, wepp_id, time = run_hillslope(wepp_id, runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}) -> ({status}, {time})')
        return status, time
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin})')
        raise

def run_flowpath_rq(runid, flowpath, wepp_bin=None):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, flowpath={flowpath}, wepp_bin={wepp_bin})')
        status, flowpath, time = run_flowpath(flowpath, runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, flowpath={flowpath}, wepp_bin={wepp_bin}) -> ({status}, {time})')
        return status, time
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, flowpath={flowpath}, wepp_bin={wepp_bin})')
        raise

def run_watershed_rq(runid, wepp_bin=None):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_bin={wepp_bin})')
        status, time = run_watershed(runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_bin={wepp_bin}) -> ({status}, {time})')
        return status, time
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_bin={wepp_bin})')
        raise

def run_ss_batch_watershed_rq(runid, wepp_bin=None, ss_batch_id=None):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        runs_dir = _join(wd, 'wepp/runs')
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
        status, time = run_ss_batch_watershed(runs_dir, wepp_bin=wepp_bin, ss_batch_id=ss_batch_id, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id}) -> ({status}, {time})')
        return status, time
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
        raise


# the main turtle

def run_wepp_rq(runid):
    try:
        job = get_current_job()
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if wepp.islocked():
            raise Exception(f'{runid} is locked')

        # send feedback to user
        wepp.log('Running Wepp\n')

        wepp.clean()
        
        # quick prep operations that require locking
        wepp._check_and_set_baseflow_map()
        wepp._check_and_set_phosphorus_map()

        # lock wepp
        # Nothing beyond this point should require writing to nodb
        wepp.lock()

        #
        # Run Hillslopes
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        climate = Climate.getInstance(wd)
        runs_dir = os.path.abspath(wepp.runs_dir)
        fp_runs_dir = wepp.fp_runs_dir
        wepp_bin = wepp.wepp_bin

        wepp.log('    wepp_bin:{}'.format(wepp_bin))

        # everything below here is asyncronous performed by workers
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)

            # jobs:0
            jobs0_hillslopes_prep = []

            if wepp.multi_ofe:
                job_prep_soils = q.enqueue_call(_prep_multi_ofe_rq, (runid,), timeout='1h')
                job.meta['jobs:0,func:_prep_multi_ofe_rq'] = job_prep_soils.id
                jobs0_hillslopes_prep.append(job_prep_soils)
                job.save()
            else:
                _job = q.enqueue_call(_prep_slopes_rq, (runid,), timeout='1h')
                job.meta['jobs:0,func:_prep_slopes_rq'] = _job.id
                jobs0_hillslopes_prep.append(_job)
                job.save()

                _job = q.enqueue_call(_prep_managements_rq, (runid,), timeout='1h')
                job.meta['jobs:0,func:_prep_managements_rq'] = _job.id
                jobs0_hillslopes_prep.append(_job)
                job.save()

                job_prep_soils = q.enqueue_call(_prep_soils_rq, (runid,), timeout='1h')
                job.meta['jobs:0,func:_prep_soils_rq'] = job_prep_soils.id
                jobs0_hillslopes_prep.append(job_prep_soils)
                job.save()

            _job = q.enqueue_call(_prep_climates_rq, (runid,), timeout='1h')
            job.meta['jobs:0,func:_prep_climates_rq'] = _job.id
            jobs0_hillslopes_prep.append(_job)
            job.save()

            job_prep_remaining = q.enqueue_call(_prep_remaining_rq, (runid,), timeout='1h', depends_on=jobs0_hillslopes_prep)
            job.meta['jobs:0,func:_prep_remaining_rq'] = job_prep_remaining.id
            job.save()

            # jobs:1

            jobs1_hillslopes = q.enqueue_call(_run_hillslopes_rq, (runid,), timeout=TIMEOUT, depends_on=job_prep_remaining)
            job.meta['jobs:1,func:run_hillslopes_rq'] = jobs1_hillslopes.id
            job.save()

            #
            # Prep Watershed
            job2_watershed_prep = q.enqueue_call(_prep_watershed_rq, (runid,),
                                  timeout=TIMEOUT,
                                  depends_on=jobs1_hillslopes)
            job.meta[f'jobs:2,func:_prep_watershed_rq'] = job2_watershed_prep.id

            job2_totalwatsed2 = None
            job2_post_dss_export = None
            if not climate.is_single_storm:
                job2_totalwatsed2 = q.enqueue_call(_build_totalwatsed2_rq, (runid,),  timeout=TIMEOUT, depends_on=jobs1_hillslopes)
                job.meta['jobs:2,func:_build_totalwatsed2_rq'] = job2_totalwatsed2.id
                job.save()

                if wepp.dss_export_on_run_completion:
                    job2_post_dss_export = q.enqueue_call(post_dss_export_rq, (runid,),  timeout=TIMEOUT, depends_on=jobs1_hillslopes)
                    job.meta['jobs:2,func:_post_dss_export_rq'] = job2_post_dss_export.id
                    job.save()


            jobs2_flowpaths = None
            if wepp.run_flowpaths:
                jobs2_flowpaths = q.enqueue_call(_run_flowpaths_rq, (runid,), timeout=TIMEOUT, depends_on=job_prep_remaining)
                job.meta['jobs:2,func:run_flowpaths_rq'] = jobs2_flowpaths.id
                job.save()

            #
            # Run Watershed
            wepp.log(f'Running Watershed wepp_bin:{wepp_bin}... ')

            # jobs:3
            jobs3_watersheds = []
            if climate.climate_mode == ClimateMode.SingleStormBatch:

                for d in climate.ss_batch_storms:
                    ss_batch_key = d['ss_batch_key']
                    ss_batch_id = d['ss_batch_id']

                    _job = q.enqueue_call(
                            func=run_ss_batch_watershed_rq,
                            args=[runid],
                            kwargs=dict(wepp_bin=wepp_bin, ss_batch_id=ss_batch_id),
                            timeout=TIMEOUT,
                            depends_on=job2_watershed_prep)
                    job.meta[f'jobs:3,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}'] = _job.id
                    jobs3_watersheds.append(_job)
                    job.save()

            else:
                _job = q.enqueue_call(
                        func=run_watershed_rq,
                        args=[runid],
                        kwargs=dict(wepp_bin=wepp_bin),
                        timeout=TIMEOUT,
                        depends_on=job2_watershed_prep)
                job.meta[f'jobs:3,func:run_watershed_rq'] = _job.id
                jobs3_watersheds.append(_job)
                job.save()

            # jobs:4
            job4_on_run_completed = q.enqueue_call(_post_unlock_wepp_rq, (runid,), depends_on=jobs3_watersheds)
            job.meta['jobs:4,func:_post_unlock_wepp_rq'] = job4_on_run_completed.id
            job.save()

            # jobs:5
            jobs5_post = []

            _job = q.enqueue_call(_post_run_cleanup_out_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
            job.meta['jobs:5,func:_post_run_cleanup_out_rq'] = _job.id
            jobs5_post.append(_job)
            job.save()

            if wepp.prep_details_on_run_completion:
                _job = q.enqueue_call(_post_prep_details_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
                job.meta['jobs:5,func:_post_prep_details_rq'] = _job.id
                jobs5_post.append(_job)
                job.save()

            if not climate.is_single_storm:
                _job = q.enqueue_call(_post_run_wepp_post_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
                job.meta['jobs:5,func:_post_run_wepp_post_rq'] = _job.id
                jobs5_post.append(_job)
                job.save()
                
                _job = q.enqueue_call(_run_hillslope_watbal_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
                job.meta['jobs:5,func:_run_hillslope_watbal_rq'] = _job.id
                jobs5_post.append(_job)
                job.save()

                _job = q.enqueue_call(_post_make_loss_grid_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
                job.meta['jobs:5,func:_post_make_loss_grid_rq'] = _job.id
                jobs5_post.append(_job)
                job.save()
                
                _job = q.enqueue_call(_analyze_return_periods_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
                job.meta['jobs:5,func:_analyze_return_periods_rq'] = _job.id
                jobs5_post.append(_job)
                job.save()

            _job = q.enqueue_call(_post_compress_pass_pw0_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
            job.meta['jobs:5,func:_post_compress_pass_pw0_rq'] = _job.id
            jobs5_post.append(_job)
            job.save()

            _job = q.enqueue_call(_post_compress_soil_pw0_rq, (runid,),  timeout=TIMEOUT, depends_on=job4_on_run_completed)
            job.meta['jobs:5,func:_post_compress_soil_pw0_rq'] = _job.id
            jobs5_post.append(_job)
            job.save()

            jobs51_post = []
            if wepp.legacy_arc_export_on_run_completion:
                _job = q.enqueue_call(_post_legacy_arc_export_rq, (runid,), timeout=TIMEOUT, depends_on=jobs5_post)
                job.meta['jobs:5,func:_post_legacy_arc_export_rq'] = _job.id
                jobs51_post.append(_job)
                job.save()

            if wepp.arc_export_on_run_completion:
                _job = q.enqueue_call(_post_gpkg_export_rq, (runid,),  timeout=TIMEOUT, depends_on=jobs5_post)
                job.meta['jobs:5,func:_post_gpkg_export_rq'] = _job.id
                jobs51_post.append(_job)
                job.save()

            if job2_totalwatsed2 is not None:
                jobs51_post.append(job2_totalwatsed2)

            if job2_post_dss_export is not None:
                jobs51_post.append(job2_post_dss_export)

            if jobs2_flowpaths is not None:
                jobs51_post.append(jobs2_flowpaths)

            # jobs:5
            if len(jobs51_post) > 0:
                job6_finalfinal = q.enqueue_call(_log_complete_rq, (runid,), depends_on=jobs51_post)
            else:
                job6_finalfinal = q.enqueue_call(_log_complete_rq, (runid,), depends_on=jobs5_post)
                
            job.meta['jobs:6,func:_log_complete_rq'] = job6_finalfinal.id
            job.save()
         
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def _prep_multi_ofe_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_multi_ofe(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _prep_slopes_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_slopes(translator, watershed.clip_hillslopes, watershed.clip_hillslope_length)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _run_hillslopes_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.run_hillslopes()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _run_flowpaths_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.prep_and_run_flowpaths()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _prep_managements_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_managements(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _prep_soils_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_soils(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _prep_climates_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp._prep_climates(translator)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _prep_remaining_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()

        reveg = False
        disturbed = Disturbed.getInstance(wepp.wd, allow_nonexistent=True)
        if disturbed is not None:
            if disturbed.sol_ver == 9005.0:
                reveg = True

        wepp._make_hillslope_runs(translator, reveg=reveg)

        if wepp.run_frost:
            wepp._prep_frost()
        else:
            wepp._remove_frost()

        wepp._prep_phosphorus()

        if wepp.run_baseflow:
            wepp._prep_baseflow()
        else:
            wepp._remove_baseflow()

        if wepp.run_wepp_ui:
            wepp._prep_wepp_ui()
        else:
            wepp._remove_wepp_ui()

        if wepp.run_pmet:
            wepp._prep_pmet()
        else:
            wepp._remove_pmet()

        if wepp.run_snow:
            wepp._prep_snow()
        else:
            wepp._remove_snow()

        if reveg:
            wepp._prep_revegetation()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _prep_watershed_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_unlock_wepp_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        # manual unlock to avoid deserialization
        lock_fn = _join(wd, 'wepp.nodb.lock')
        if _exists(lock_fn):
            os.remove(lock_fn)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_run_cleanup_out_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_id = d['ss_batch_id']

                wepp.log('    moving .out files...')
                for fn in glob(_join(wepp.runs_dir, '*.out')):
                    dst_path = _join(wepp.output_dir, ss_batch_key, _split(fn)[1])
                    shutil.move(fn, dst_path)
                wepp.log_done()
        else:
            wepp.log('    moving .out files...')
            for fn in glob(_join(wepp.runs_dir, '*.out')):
                dst_path = _join(wepp.output_dir, _split(fn)[1])
                shutil.move(fn, dst_path)
            wepp.log_done()

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _analyze_return_periods_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.export_return_periods_tsv_summary(meoization=True)
        wepp.export_return_periods_tsv_summary(meoization=True, extraneous=True)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def _build_totalwatsed2_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp._build_totalwatsed2()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _run_hillslope_watbal_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp._run_hillslope_watbal()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_prep_details_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        export_channels_prep_details(wd)
        export_hillslopes_prep_details(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_run_wepp_post_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        time.sleep(1)
        wepppost = WeppPost.getInstance(wd)
        wepppost.run_post()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_compress_pass_pw0_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        target = _join(wd, 'wepp/output/pass_pw0.txt')
        if _exists(target):
            compress_fn(target)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_compress_soil_pw0_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        target = _join(wd, 'wepp/output/soil_pw0.txt')
        compress_fn(target)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_legacy_arc_export_rq(runid):
    try:
        from wepppy.export import  legacy_arc_export
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        legacy_arc_export(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_gpkg_export_rq(runid):
    try:
        from wepppy.export.gpkg_export import gpkg_export
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        gpkg_export(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def post_dss_export_rq(runid):
    try:
        from wepppy.wepp.out import totalwatsed_partitioned_dss_export
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:dss_export'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        
        totalwatsed_partitioned_dss_export(wd, wepp.dss_export_channel_ids, status_channel=status_channel)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.dss_export)
        except FileNotFoundError:
            pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   dss_export DSS_EXPORT_TASK_COMPLETED')
        
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise



def _post_make_loss_grid_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.make_loss_grid()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _log_complete_rq(runid):
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_wepp)
        except FileNotFoundError:
            pass

        ron = Ron.getInstance(wd)
        name = ron.name
        scenario = ron.scenario
        config = ron.config_stem

        link = runid
        if name or scenario:
            if name and scenario:
                link = f'{name} - {scenario} _{runid}_'
            elif name:
                link = f'{name} _{runid}_'
            else:
                link = f'{scenario} _{runid}_'

        if send_discord_message is not None:
            send_discord_message(f':fireworks: [{link}](https://wepp.cloud/weppcloud/runs/{runid}/{config}/)')

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   wepp WEPP_RUN_TASK_COMPLETED')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
