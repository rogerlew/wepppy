import os
import shutil

from os.path import join as _join
from os.path import exists as _exists

import time
import uuid
from subprocess import (
    Popen, PIPE, STDOUT,
    check_output, TimeoutExpired
)
from datetime import datetime

import pandas as pd

from wepppy.all_your_base import isint

# noinspection PyProtectedMember
from wepppy.climates.cligen import (
    CligenStationsManager,
    ClimateFile,
    _bin_dir,
    make_clinp,
    df_to_prn
)

from wepppy.climates.downscaled_nmme_client import retrieve_rcp85_timeseries


lat, lng = 46.0, -116.0
start_year, end_year = 2010, 2099
site_name = 'default'

# find climate station

stationManager = CligenStationsManager()
stationMeta = stationManager.get_closest_station((lng, lat))
climateStation = stationMeta.id


# get future climate data
ts_fn = f'{site_name}_ts.csv'
if _exists(ts_fn):
    df = pd.read_csv(ts_fn)
else:
    df = retrieve_rcp85_timeseries(lng, lat, 
                               datetime(start_year, 1, 1), 
                               datetime(end_year, 12, 31), verbose=True)
    df.to_csv(ts_fn)

# make prn
df_to_prn(df, 'input.prn', u'pr(mm)', u'tasmax(degc)', u'tasmin(degc)')

shutil.copyfile(stationMeta.parpath, stationMeta.par)

# build cmd
cli_fn = f"{site_name}_future.cli"
cmd = [_join(_bin_dir, 'cligen532'),
       "-i%s" % stationMeta.par,
       "-Oinput.prn",
       "-o%s" % cli_fn,
       "-t6", "-I2"]
    
# run cligen
_log = open("cligen.log", "w")
p = Popen(cmd, stdin=PIPE, stdout=_log, stderr=_log)
p.wait()
_log.close()

assert _exists(cli_fn)

climate = ClimateFile(cli_fn)

# can replace variables in climate file and rewrite 
# https://github.com/rogerlew/wepppy/blob/master/wepppy/climates/cligen/cligen.py
