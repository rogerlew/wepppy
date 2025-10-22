import os
import uuid
import shutil
from datetime import datetime
from os.path import join as _join
from os.path import exists as _exists
from subprocess import Popen, PIPE
from wepppy.climates.downscaled_nmme_client import retrieve_rcp85_timeseries
from wepppy.climates.cligen import ClimateFile, CligenStationsManager, df_to_prn, _bin_dir
from wepppy.climates import cligen_client as cc

from wepppy.all_your_base import isint


def build_future_climate(lng, lat, start_year, end_year, model='GFDL-ESM2G', replace_vars=None, cli_dir='./'):

    start_year = int(start_year)
    end_year = int(end_year)

    d0 = 2006
    dend = 2099

    assert start_year >= d0
    assert start_year <= dend

    assert end_year >= d0
    assert end_year <= dend
    
    stationManager = CligenStationsManager(version=2015)
    stationmeta = stationManager.get_closest_station((lng, lat))
    par = stationmeta.par

    # create working directory to build climate
    _uuid = str(uuid.uuid4())
    wd = _join(cli_dir, _uuid)
    os.mkdir(wd)
    os.chdir(wd)

    # write par
    par_fn = par + '.par'
    shutil.copyfile(stationmeta.parpath, par_fn)

    df = retrieve_rcp85_timeseries(lng, lat, 
                                   datetime(start_year, 1, 1), 
                                   datetime(end_year, 12, 31))
    
    df.to_csv(_join(wd, 'timeseries.csv'))
    df_to_prn(df, 'input.prn', u'pr(mm)', u'tasmax(degc)', u'tasmin(degc)')
    
    # build cmd
    cli_fn = _join(wd, 'future.cli')
    cmd = [_join(_bin_dir, 'cligen532'),
           "-i%s.par" % par,
           "-Oinput.prn",
           "-o%s" % cli_fn,
           "-t6", "-I2"]
    
    # run cligen
    _log = open("cligen.log", "w")
    p = Popen(cmd, stdin=PIPE, stdout=_log, stderr=_log)
    p.wait()
    _log.close()

    assert _exists(cli_fn)

    # handle replacements

    climate = ClimateFile(cli_fn)

if __name__ == '__main__':
    build_future_climate(lng=-117, lat=46, start_year=2006, end_year=2099, model='GFDL-ESM2G', replace_vars=None, cli_dir='./')
