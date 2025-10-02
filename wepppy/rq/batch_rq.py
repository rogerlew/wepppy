import inspect
import os
import shutil
import socket
import time
import json
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from copy import deepcopy
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import redis
from rq import Queue, get_current_job

from wepppy.weppcloud.utils.helpers import get_wd

from wepppy.nodb.base import NoDbAlreadyLockedError, clear_nodb_file_cache, clear_locks
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.topo.watershed_collection import  WatershedFeature
try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except Exception:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 43_200

def run_batch_rq(batch_name: str):
    try:
        job = get_current_job()
        job_id = job.id if job is not None else 'N/A'
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{batch_name}:batch'

        if job is not None:
            job.meta['runid'] = batch_name
            job.save()

        StatusMessenger.publish(status_channel, f'rq:{job_id} STARTED {func_name}({batch_name})')

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)
        watershed_collection = batch_runner.get_watershed_collection()

        template_state = batch_runner.runid_template_state or {}
        template = template_state.get('template')
        summary = template_state.get('summary') or {}

        if not template:
            raise ValueError('Batch run requires a validated run ID template.')

        if template_state.get('status') != 'ok' or not summary.get('is_valid', False):
            raise ValueError('Run ID template validation is not in an OK state.')

        resource_checksum = template_state.get('resource_checksum')
        if resource_checksum and resource_checksum != watershed_collection.checksum:
            raise ValueError('Watershed GeoJSON has changed since template validation; re-validate before running.')

        watershed_collection.runid_template = template
        watershed_features = list(watershed_collection)
        if not watershed_features:
            raise ValueError('No watershed features available to enqueue.')

        watershed_jobs = []
        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            q = Queue(connection=redis_conn)

            for wf in watershed_features:
                runid = wf.runid
                child_job = q.enqueue_call(
                    func=run_batch_watershed_rq,
                    args=[batch_name, wf],
                    timeout=TIMEOUT,
                )
                child_job.meta['runid'] = runid
                child_job.save()
                if job is not None:
                    job.meta[f'jobs:0,runid:{runid}'] = child_job.id
                    job.save()
                watershed_jobs.append(child_job)

            final_job = q.enqueue_call(
                func=_final_batch_complete_rq,
                args=[batch_name],
                timeout=TIMEOUT,
                depends_on=watershed_jobs if watershed_jobs else None,
            )
            final_job.meta['runid'] = batch_name
            final_job.save()
            if job is not None:
                job.meta['jobs:1,func:_final_batch_complete_rq'] = final_job.id
                job.save()

        StatusMessenger.publish(status_channel, f'rq:{job_id} COMPLETED {func_name}({batch_name})')
        return final_job

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job_id} EXCEPTION {func_name}({batch_name})')
        raise


def run_batch_watershed_rq(
    batch_name: str,
    watershed_feature: WatershedFeature,
):
    try:
        from wepppy.nodb.ron import Ron
        from wepppy.nodb.watershed import Watershed
        from wepppy.nodb.landuse import Landuse
        from wepppy.nodb.soils import Soils
        from wepppy.nodb.mods.rap.rap_ts import RAP_TS
        from wepppy.nodb.wepp import Wepp

        job = get_current_job()
        _runid = watershed_feature.runid
        runid = f'batch;;{batch_name};;{_runid}'
        runid_wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{batch_name}:batch'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        start_ts = time.time()

        batch_runner = BatchRunner.getInstanceFromBatchName(batch_name)

        # begin refactor for BatchRunner.run_watershed(watershed_feature)
        base_wd = batch_runner.base_wd

        assert runid.startswith('batch'), f"runid must start with 'batch', got: {runid}"
        assert batch_name in runid, f"batch_name ({batch_name}) must be in accessor of runid, got: {runid}"

        # copy base project to runid_wd
        if os.path.exists(runid_wd):
            shutil.rmtree(runid_wd)
        shutil.copytree(base_wd, runid_wd)

        # for nodb files set ['py/state']['wd'] to runid_wd
        for nodb_fn in glob(_join(runid_wd, '*.nodb')):

            with open(nodb_fn, 'r') as fp:
                d = json.load(fp)

            d['py/state']['wd'] = runid_wd

            with open(nodb_fn, 'w') as fp:
                json.dump(d, fp)
                fp.flush()                 # flush Python’s userspace buffer
                os.fsync(fp.fileno())      # fsync forces kernel page-cache to disk
        
        clear_nodb_file_cache(runid)
        try:
            cleared = clear_locks(runid)
            if cleared:
                StatusMessenger.publish(status_channel, f'rq:{job.id} INFO cleared stale locks {cleared}')
        except RuntimeError:
            pass

        if batch_runner.is_task_enabled(TaskEnum.fetch_dem):
            pad = 0.02  # degrees
            bbox = watershed_feature.get_padded_bbox(pad=pad)
            ron = Ron.getInstance(runid_wd)
            map_center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            ron.set_map(bbox, center=map_center, zoom=11)
            ron.fetch_dem()
            
        if batch_runner.is_task_enabled(TaskEnum.build_channels):
            watershed = Watershed.getInstance(runid_wd)
            watershed.build_channels()

        if batch_runner.is_task_enabled(TaskEnum.find_outlet):
            watershed = Watershed.getInstance(runid_wd)
            watershed.find_outlet(watershed_feature)

        if batch_runner.is_task_enabled(TaskEnum.build_subcatchments):
            watershed = Watershed.getInstance(runid_wd)
            watershed.build_subcatchments()

        if batch_runner.is_task_enabled(TaskEnum.abstract_watershed):
            watershed = Watershed.getInstance(runid_wd)
            watershed.abstract_watershed()

        if batch_runner.is_task_enabled(TaskEnum.build_landuse):
            landuse = Landuse.getInstance(runid_wd)
            landuse.build()

        if batch_runner.is_task_enabled(TaskEnum.build_soils):
            soils = Soils.getInstance(runid_wd)
            soils.build()

        if batch_runner.is_task_enabled(TaskEnum.build_climate):
            from wepppy.nodb.climate import Climate
            climate = Climate.getInstance(runid_wd)
            climate.build()

        rap_ts = RAP_TS.tryGetInstance(runid_wd)
        if rap_ts and batch_runner.is_task_enabled(TaskEnum.fetch_rap_ts):
            rap_ts.acquire_rasters(start_year=climate.observed_start_year,
                                end_year=climate.observed_end_year)
            rap_ts.analyze()

        # make sure wepp tasks follow wepp_rq routing, but don't
        # branch to separate jobs
        if batch_runner.is_task_enabled(TaskEnum.run_wepp_hillslopes):
            wepp = Wepp.getInstance(runid_wd)
            wepp.prep_hillslopes()
            wepp.run_hillslopes()

        if batch_runner.is_task_enabled(TaskEnum.run_wepp_watershed):
            wepp = Wepp.getInstance(runid_wd)
            wepp.prep_watershed()
            wepp.run_watershed()

        # if wepp was ran do the post wepp tasks that are performed in wepp_rq
        # end refactor


        elapsed = time.time() - start_ts
        status = True
        StatusMessenger.publish(
            status_channel,
            f'rq:{job.id} COMPLETED {func_name}({runid}) -> ({status}, {elapsed:.3f})',
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_WATERSHED_TASK_COMPLETED')
        return status, elapsed

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise

def _final_batch_complete_rq(batch_name: str):
    job = get_current_job()
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f'{batch_name}:batch'

    try:
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({batch_name})')

        BatchRunner.getInstanceFromBatchName(batch_name)

        if send_discord_message is not None:
            try:
                send_discord_message(f':herb: Batch {batch_name} completed on {_hostname}')
            except Exception:
                pass

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({batch_name})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch BATCH_RUN_COMPLETED')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER batch END_BROADCAST')
        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER omni END_BROADCAST')

    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({batch_name})')
        raise
