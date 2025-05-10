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

from wepppy.nodb import Landuse, Soils, Ron, LanduseMode, SoilsMode
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.nodb.status_messenger import StatusMessenger

from uuid import uuid4

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
    send_discord_message = None


_hostname = socket.gethostname()

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

TIMEOUT = 43_200

def land_and_soil_rq(runid, extent, cfg, nlcd_db, ssurgo_db):
    print(f'land_and_soil_rq(extent={extent}, cfg={cfg}, nlcd_db={nlcd_db}, ssurgo_db={ssurgo_db})')

    status_channel = 'land_and_soil_rq:-'
    func_name = inspect.currentframe().f_code.co_name
    job = get_current_job()
    uuid = job.id

    try:

        if cfg is None:
            cfg = 'disturbed9002'
        
        config = f'{cfg}.cfg'
        center = [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2]
        status_channel = f'land_and_soil_rq:{job.id}'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({uuid})')
        t0 = time.time()

        if _exists('/wc1/land_and_soil_rq/'):
            wd = f'/wc1/land_and_soil_rq/{uuid}'
        else:
            wd = f'/geodata/wc1/land_and_soil_rq/{uuid}'

        StatusMessenger.publish(status_channel, f'Creating wd {wd}')
        if not _exists(wd):
            os.makedirs(wd)
        else:
            shutil.rmtree(wd)
            os.makedirs(wd)

        StatusMessenger.publish(status_channel, f'Initializing project')
        ron = Ron(wd, config)
        ron.set_map(extent, center, zoom=12)

        StatusMessenger.publish(status_channel, f'Building Landuse')
        landuse = Landuse.getInstance(wd)
        landuse.mode = LanduseMode.SpatialAPI
        if nlcd_db is not None:
            landuse.nlcd_db = nlcd_db
        landuse.build()

        StatusMessenger.publish(status_channel, f'Building Soils')
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode.SpatialAPI
        if ssurgo_db is not None:
            soils.ssurgo_db = ssurgo_db
        soils.build()

        # tar the wd
        tarfile = f'{wd}.tar.gz'
        if _exists(tarfile):
            os.remove(tarfile)
        
        cmd = ['tar', '-I', 'pigz', '-cf', tarfile, wd]
        StatusMessenger.publish(status_channel, f'Creating tar archive')
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise RuntimeError(f'Error creating tar file: {tarfile}, {p.returncode}: {err.decode()}')

        status = True
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({uuid}) -> ({status}, {time})')
        return tarfile, time.time() - t0
    
    except Exception:
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({uuid})')
        raise
