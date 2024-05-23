import shutil
from glob import glob

from os.path import join as _join
from os.path import exists as _exists

from functools import wraps
from subprocess import Popen, PIPE, call

from rq import Queue, get_current_job
from redis import Redis

from wepppy.weppcloud.utils.helpers import get_wd

from wepp_runner import (
    run_ss_batch_hillslope,
    run_hillslope,
    run_flowpath,
    run_watershed,
    run_ss_batch_watershed,
)

from wepppy.nodb import Wepp, Watershed, Climate, ClimateMode

from wepppy.nodb.status_messenger import StatusMessenger

from wepppy.export.prep_details import (
    export_channels_prep_details,
    export_hillslopes_prep_details
)


REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9


def compress_fn(fn):
    if _exists(fn):
        p = call('gzip %s -f' % fn, shell=True)
        assert _exists(fn + '.gz')

# turtles, turtles all the way down...

def run_ss_batch_hillslope_rq(runid, wepp_id, wepp_bin=None, ss_batch_id=None):
    job = get_current_job()
    wd = get_wd(runid)
    runs_dir = _join(wd, 'wepp/runs')
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running run_ss_batch_hillslope({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
    status, wepp_id, time = run_ss_batch_hillslope(wepp_id, runs_dir, wepp_bin=wepp_bin, ss_batch_id=ss_batch_id, status_channel=status_channel)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed run_ss_batch_hillslope({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id}) -> ({status}, {time})')
    return status, time

def run_hillslope_rq(runid, wepp_id, wepp_bin=None):
    wd = get_wd(runid)
    runs_dir = _join(wd, 'wepp/runs')
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running run_hillslope({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin})')
    status, wepp_id, time = run_hillslope(wepp_id, runs_dir, wepp_bin=wepp_bin)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed run_hillslope({runid}, wepp_id={wepp_id}, wepp_bin={wepp_bin}) -> ({status}, {time})')
    return status, time

def run_flowpath_rq(runid, flowpath, wepp_bin=None):
    wd = get_wd(runid)
    runs_dir = _join(wd, 'wepp/runs')
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running run_hillslope({runid}, flowpath={flowpath}, wepp_bin={wepp_bin})')
    status, flowpath, time = run_flowpath(flowpath, runs_dir, wepp_bin=wepp_bin, status_channel=status_channel)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed run_hillslope({runid}, flowpath={flowpath}, wepp_bin={wepp_bin}) -> ({status}, {time})')
    return status, time

def run_watershed_rq(runid, wepp_bin=None):
    wd = get_wd(runid)
    runs_dir = _join(wd, 'wepp/runs')
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running run_watershed({runid}, wepp_bin={wepp_bin})')
    status, time = run_watershed(runs_dir, wepp_bin=wepp_bin)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed run_watershed({runid}, wepp_bin={wepp_bin}) -> ({status}, {time})')
    return status, time

def run_ss_batch_watershed_rq(runid, wepp_bin=None, ss_batch_id=None):
    wd = get_wd(runid)
    runs_dir = _join(wd, 'wepp/runs')
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running run_ss_batch_watershed({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id})')
    status, time = run_ss_batch_watershed(runs_dir, wepp_bin=wepp_bin, ss_batch_id=ss_batch_id, status_channel=status_channel)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed run_ss_batch_watershed({runid}, wepp_bin={wepp_bin}, ss_batch_id={ss_batch_id}) -> ({status}, {time})')
    return status, time


# the main turtle

def run_wepp_rq(runid):
    job = get_current_job()

    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    if wepp.islocked():
        raise Exception(f'{runid} is locked')

    #
    # Prep Hillslopes
    wepp.prep_hillslopes()

    # lock to prevent simultaneous running of the same project
    wepp.lock()

    #
    # Run Hillslopes
    wepp.log('Running Hillslopes\n')
    watershed = Watershed.getInstance(self.wd)
    translator = watershed.translator_factory()
    climate = Climate.getInstance(self.wd)
    runs_dir = os.path.abspath(self.runs_dir)
    fp_runs_dir = wepp.fp_runs_dir
    wepp_bin = wepp.wepp_bin

    wepp.log('    wepp_bin:{}'.format(wepp_bin))

    # everything below here is asyncronous performed by workers
    with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
        q = Queue(connection=redis_conn)

        jobs0_hillslopes = []

        sub_n = watershed.sub_n
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
                ss_n = len(climate.ss_batch_storms)
                for d in climate.ss_batch_storms:
                    ss_batch_id = d['ss_batch_id']
                    ss_batch_key = d['ss_batch_key']
                    wepp.log(f'  submitting topaz={topaz_id} (hill {i+1} of {sub_n}, ss {ss_batch_id} of {ss_n}).\n')
                    wepp_id = translator.wepp(top=int(topaz_id))
                    _job = q.enqueue_call(
                               func=run_ss_batch_hillslope_rq,
                               args=[runid, wepp_id],
                               kwargs=dict(wepp_bin=wepp_bin, ss_batch_id=ss_batch_id),
                               timeout=600)

                    job.meta[f'jobs:0,func:run_ss_batch_hillslope_rq,ss_batch_id:{ss_batch_id},hill:{topaz_id}'] = _job.id
                    jobs0_hillslopes.append(_job)
        else:
            for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
                wepp.log(f'  submitting topaz={topaz_id} (hill {i+1} of {sub_n})')
                wepp_id = translator.wepp(top=int(topaz_id))
                _job = q.enqueue_call(
                           func=run_hillslope_rq,
                           args=[runid, wepp_id],
                           kwargs=dict(wepp_bin=wepp_bin),
                           timeout=600)
                job.meta[f'jobs:0,func:run_hillslope_rq,hill:{topaz_id}'] = _job.id
                jobs0_hillslopes.append(_job)

        #
        # TODO: flowpaths would go here
        # watershed would not be dependent on flowpaths

        #
        # Prep Watershed
        _job = q.enqueue_call(_prep_watershed_rq, ('runid',))
        job.meta[f'jobs:0,func:_prep_watershed_rq,hill:{topaz_id}'] = _job.id
        jobs0_hillslopes.append(_job)

        #
        # Run Watershed
        wepp.log(f'Running Watershed wepp_bin:{self.wepp_bin}... ')

        jobs1_watersheds = []
        if climate.climate_mode == ClimateMode.SingleStormBatch:

            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']
                ss_batch_id = d['ss_batch_id']

                _job = q.enqueue_call(
                           func=run_ss_batch_watershed_rq,
                           args=[runid],
                           kwargs=dict(wepp_bin=wepp_bin, ss_batch_id=ss_batch_id),
                           timeout='1h',
                           depends_on=jobs0_hillslopes)
                job.meta[f'jobs:1,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}'] = _job.id
                jobs1_watershed.append(_job)

        else:
            _job = q.enqueue_call(
                       func=run_watershed_rq(
                       args=[runid],
                       kwargs=dict(wepp_bin=wepp_bin),
                       timeout='4h',
                       depends_on=jobs0_hillslopes)
            job.meta[f'jobs:1,func:run_watershed_rq'] = _job.id
            jobs1_watershed.append(_job)

        job2_on_run_completed = q.enqueue_call(_post_unlock_wepp_rq, (run_id,), depends_on=jobs1_watersheds)
        job.meta['jobs:2,func:_post_unlock_wepp_rq'] = job2_running_complete.id

        jobs3_post = []
        post_jobs.append(q.enqueue_call(_post_run_cleanup_out_rq, (runid,) depends_on=job2_on_run_completed)
        if wepp.prep_details_on_run_completion:
            _job = q.enqueue_call(_post_prep_details_rq, (runid,) depends_on=job2_on_run_completed)
            job.meta['jobs:3,func:_post_prep_details_rq'] = _job.id
            jobs3_post.append(_job)

        if not climate.is_single_storm:
            _job = q.enqueue_call(_post_run_wepp_post_rq, (runid,) depends_on=job2_on_run_completed)
            job.meta['jobs:3,func:_post_run_wepp_post_rq'] = _job.id
            jobs3_post.append(_job)

        _job = q.enqueue_call(_post_compress_pass_pw0_rq, (runid,) depends_on=job2_on_run_completed)
        job.meta['jobs:3,func:_post_compress_pass_pw0_rq'] = _job.id
        jobs3_post.append(_job)

        _job = q.enqueue_call(_post_compress_soil_pw0_rq, (runid,) depends_on=job2_on_run_completed)
        if wepp.legacy_arc_export_on_run_completion:
            _job = q.enqueue_call(_post_legacy_arc_export_rq, (runid,) depends_on=job2_on_run_completed)
            job.meta['jobs:3,func:_post_legacy_arc_export_rq'] = _job.id
            jobs3_post.append(_job)

        if wepp.arc_export_on_run_completion:
            _job = q.enqueue_call(_post_gpkg_export_rq, (runid,) depends_on=job2_on_run_completed)
            job.meta['jobs:3,func:_post_gpkg_export_rq'] = _job.id
            jobs3_post.append(_job)

        _job = q.enqueue_call(_post_make_loss_grid_rq, (runid,) depends_on=job2_on_run_completed)
        job.meta['jobs:3,func:_post_make_loss_grid_rq'] = _job.id
        jobs3_post.append(_job)

        job4_finalfinal = q.enqueue_call(_log_complete_rq, (runid,) depends_on=jobs3_post)
        job.meta['jobs:4,func:_log_complete_rq'] = _job.id

        job.save()


def _prep_watershed_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _prep_watershed_rq({runid})')
    wepp = Wepp.getInstance(wd)
    wepp.prep_watershed()
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _prep_watershed_rq({runid})')


def _post_unlock_wepp_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_unlock_wepp_rq({runid})')

    # manual unlock to avoid deserialization
    lock_fn = _join(wd, 'wepp.nodb.lock')
    if exists(lock_fn):
        os.remove(lock_fn)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_unlock_wepp_rq({runid})')


def _post_run_cleanup_out_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_run_cleanup_out_rq({runid})')

    climate = Climate.getInstance(wd)

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

    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_run_cleanup_out_rq({runid})')


def _post_prep_details_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_prep_details_rq({runid})')
    export_channels_prep_details(wd)
    export_hillslopes_prep_details(wd)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_prep_details_rq({runid})')


def _post_run_wepp_post_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_run_wepp_post_rq({runid})')
    wepppost = WeppPost.getInstance(wd)
    wepppost.run_post()
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_run_wepp_post_rq({runid})')


def _post_compress_pass_pw0_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_compress_pass_pw0_rq({runid})')
    target = _join(wd, 'wepp/output/pass_pw0.txt'
    if _exists(target):
        compress_fn(target)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_compress_pass_pw0_rq({runid})')


def _post_compress_soil_pw0_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_compress_soil_pw0_rq({runid})')
    target = _join(wd, 'wepp/output/soil_pw0.txt'
    compress_fn(target)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_compress_soil_pw0_rq({runid})')


def _post_legacy_arc_export_rq(runid):
    from wepppy.export import  legacy_arc_export
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_legacy_arc_export_rq({runid})')
    legacy_arc_export(wd)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_legacy_arc_export_rq({runid})')


def _post_gpkg_export_rq(runid):
    from wepppy.export.gpkg_export import gpkg_export
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_gpkg_export_rq({runid})')
    gpkg_export(wd)
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_gpkg_export_rq({runid})')


def _post_make_loss_grid_rq(runid)
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _post_make_loss_grid_rq({runid})')
    wepp = Wepp.getInstance(wd)
    wepp.make_loss_grid()
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _post_make_loss_grid_rq({runid})')


def _log_complete_rq(runid):
    wd = get_wd(runid)
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} running _log_complete_rq({runid})')
    status_channel = f'{runid}:wepp'
    StatusMessenger.publish(status_channel, f'rq:{job.id} completed _log_complete_rq({runid})')

    try:
        prep = Prep.getInstance(wd)
        prep.timestamp('run_wepp')
    except FileNotFoundError:
        pass

    ron = Ron.getInstance(wd)
    name = ron.name
    scenario = ron.scenario
    runid = ron.runid
    config = ron.config_stem

    link = runid
    if name or scenario:
        if name and scenario:
            link = f'{name} - {scenario} _{runid}_'
        elif name:
            link = f'{name} _{runid}_'
        else:
            link = f'{scenario} _{runid}_'

    send_discord_message(f':fireworks: [{link}](https://wepp.cloud/weppcloud/runs/{runid}/{config}/)')

