#!/usr/bin/python

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os

from os.path import join as _join
from os.path import exists as _exists

import time
import uuid
from subprocess import (
    Popen, PIPE, STDOUT,
    check_output, TimeoutExpired
)
from datetime import datetime
import warnings
from copy import deepcopy
from flask import Flask, jsonify, request, Response

from wepppy.all_your_base import isint

# noinspection PyProtectedMember
from wepppy.climates.cligen import (
    CligenStationsManager,
    ClimateFile,
    _bin_dir,
    df_to_prn
)
                                    
from wepppy.climates.daymet_singlelocation_client \
    import retrieve_historical_timeseries
                                    
from wepppy.climates.downscaled_nmme_client \
    import retrieve_rcp85_timeseries
from wepppy.climates.metquery_client import get_prism_monthly_tmin, get_prism_monthly_tmax, get_prism_monthly_ppt, \
    get_daymet_prcp_pwd, get_daymet_prcp_pww, get_daymet_prcp_skew, get_daymet_prcp_std

static_dir = None
app = Flask(__name__)


def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """

    # noinspection PyBroadException
    try:
        return float(x)
    except Exception:
        return None


# noinspection PyPep8Naming
@app.route('/findstation', methods=['GET', 'POST'])
@app.route('/findstation/', methods=['GET', 'POST'])
def findstation():
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/findstation/?lng=-117&lat=47
    https://wepp1.nkn.uidaho.edu/webservices/cligen/findstation/?lng=-117&lat=47&method=heuristic_search
    https://wepp1.nkn.uidaho.edu/webservices/cligen/findstation/?lng=-117&lat=47&method=closest
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        lat = request.args.get('lat', None)
        lng = request.args.get('lng', None)
        method = request.args.get('method', None)
    else:  # POST
        d = request.get_json()
        lat = d.get('lat', None)
        lng = d.get('lng', None)
        method = d.get('method', None)

    if lat is None or lng is None:
        return jsonify({'Error': 'lat, lng, must be supplied'})

    lat = safe_float_parse(lat)
    lng = safe_float_parse(lng)

    if lat is None:
        return jsonify({'Error': 'could not parse lat'})

    if lng is None:
        return jsonify({'Error': 'could not parse lng'})

    if method is None:
        method = 'closest'

    stationManager = CligenStationsManager()
    if method == 'heuristic_search':
        stationMeta = stationManager.get_station_heuristic_search([lng, lat])
        return jsonify(stationMeta.as_dict())

    elif method == 'closest':
        stationMeta = stationManager.get_closest_station([lng, lat])
        return jsonify(stationMeta.as_dict())

    return jsonify({'Error': 'method must be heuristic_search or closest'})


# noinspection PyPep8Naming
def _fetch_par_contents(par, _request):
    """
    returns the contents of a par file
    """

    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)
   
    if stationMeta is None:
        return jsonify({'Error': 'cannot find par'})

    if _request.method == 'GET':
        d = _request.args
    else:  # POST
        d = _request.get_json()
        
    lat = d.get('lat', None)
    lng = d.get('lng', None)
    p_mean = d.get('p_mean', None)
    p_std = d.get('p_std', None)
    p_skew = d.get('p_skew', None)
    p_ww = d.get('p_ww', None)
    p_wd = d.get('p_wd', None)
    tmax = d.get('tmax', None)
    tmin = d.get('tmin', None)
    dewpoint = d.get('dewpoint', None)
    solrad = d.get('solrad', None)

    lat = safe_float_parse(lat)
    lng = safe_float_parse(lng)

    if lat is None and lng is None:
        result = open(stationMeta.parpath).read()
    else:
        station = stationMeta.get_station()
        localized = station.localize(lng, lat, p_mean, p_std, p_skew, p_ww, p_wd,
                                     tmax, tmin, dewpoint, solrad)
        result = ''.join(localized.lines)

    return result


# noinspection PyPep8Naming
@app.route('/fetchstationmeta/<par>', methods=['GET', 'POST'])
@app.route('/fetchstationmeta/<par>/', methods=['GET', 'POST'])
def fetchstationmeta(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/fetchstationmeta/106152
    """

    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)
   
    if stationMeta is None:
        return jsonify({'Error': 'cannot find par'})

    return jsonify(stationMeta.as_dict(include_monthlies=True))


@app.route('/fetchpar/<par>', methods=['GET', 'POST'])
@app.route('/fetchpar/<par>/', methods=['GET', 'POST'])
def fetchpar(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/fetchpar/106152
    https://wepp1.nkn.uidaho.edu/webservices/cligen/fetchpar/106152/?lng=-116&lat=47&p_mean=prism&p_std=daymet&p_wd=daymet&p_ww=daymet&tmax=prism&tmin=prism&dewpoint=prism&solrad=daymet
    """

    # noinspection PyBroadException
    try:
        result = _fetch_par_contents(par, request)
    except Exception:
        return jsonify({'Error': 'Could not build par contents'})

    r = Response(response=result, status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r


def _make_clinp(wd, cliver, years, cli_fn, par_fn):
    """
    makes an input file that is passed as stdin to cligen
    """
    clinp = _join(wd, "clinp.txt")
    fp = open(clinp, "w")

    if cliver in ["5.2", "5.3"]:
        fp.write("5\n1\n{years}\n{cli_fn}\nn\n\n"
                 .format(years=years, cli_fn=cli_fn))
    else:
        fp.write("\n{par_fn}\nn\n5\n1\n{years}\n{cli_fn}\nn\n\n"
                 .format(par_fn=par_fn, years=years, cli_fn=cli_fn))

    fp.close()

    assert _exists(clinp)


@app.route('/single_year/<par>', methods=['GET', 'POST'])
@app.route('/single_year/<par>/', methods=['GET', 'POST'])
def single_year_route(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/single_year/106152/?years=1
    https://wepp1.nkn.uidaho.edu/webservices/cligen/single_year/106152/?lng=-116&lat=47&p_mean=prism&p_std=daymet&p_wd=daymet&p_ww=daymet&tmax=prism&tmin=prism&dewpoint=prism&solrad=daymet
    """
    return _multiple_year(par, request, singleyearmode=True)


@app.route('/multiple_year/<par>', methods=['GET', 'POST'])
@app.route('/multiple_year/<par>/', methods=['GET', 'POST'])
def multiple_year_route(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/multiple_year/106152/?years=1
    https://wepp1.nkn.uidaho.edu/webservices/cligen/multiple_year/106152/?years=1&lng=-116&lat=47&p_mean=prism&p_std=daymet&p_wd=daymet&p_ww=daymet&tmax=prism&tmin=prism&dewpoint=prism&solrad=daymet
    https://wepp1.nkn.uidaho.edu/webservices/cligen/multiple_year/106152/?years=1&lng=-116&lat=47&p_mean=prism&p_std=daymet&p_wd=daymet&p_ww=daymet&tmax=prism&tmin=prism&dewpoint=prism&solrad=daymet&returnjson=True
    """
    
    return _multiple_year(par, request)


def _multiple_year(par, _request, singleyearmode=False):

    if _request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if _request.method == 'GET':
        d = _request.args
    else:  # POST
        d = _request.get_json()
    
    years = d.get('years', None)
    cliver = d.get('cliver', None)
    returnjson = d.get('returnjson', False)
    randseed = d.get('randseed', None)
    returnjson = bool(returnjson)
           
    if singleyearmode:
        years = 1

    if not isint(years):
        return jsonify({'Error': 'years as an integer is required "%s"' % years})

    if cliver is None:
        cliver = '5.3'

    # create working directory to build climate
    _uuid = str(uuid.uuid4())
    wd = _join(static_dir, _uuid)
    os.mkdir(wd)
    os.chdir(wd)

    # write par
    par_fn = par + '.par'
    par_contents = _fetch_par_contents(par, _request)

    with open(par_fn, 'w') as fp:
        fp.write(par_contents)

    # create cligen input file
    cli_fn = par + '.cli'
    _make_clinp(wd, cliver, years, cli_fn, par_fn)

    # build cmd
    if cliver == "4.3":
        cmd = [_join(_bin_dir, 'cligen43')]
    elif cliver == "5.2":
        cmd = [_join(_bin_dir, 'cligen52'), "-i%s" % par_fn]
    else:
        cmd = [_join(_bin_dir, 'cligen53'), "-i%s" % par_fn]
        
    if randseed is not None:
        cmd.append('-r%s' % randseed)

    # run cligen
    _clinp = open("clinp.txt")
    _log = open("cligen.log", "w")
    p = Popen(cmd, stdin=_clinp, stdout=_log, stderr=_log)
    p.wait()
    _clinp.close()
    _log.close()

    if not _exists(cli_fn):
        return jsonify({'Error': 'Error running cligen',
                        'cmd': cmd,
                        'wd': wd})

    with open(cli_fn) as fp:
        cli_contents = fp.read()

    if returnjson:
        with open("clinp.txt") as fp:
            clinp_contents = fp.read()

        cli = ClimateFile(cli_fn)
        monthlies = cli.calc_monthlies()

        return jsonify({'par_fn': par_fn,
                        'par_contents': par_contents,
                        'cli_fn': cli_fn,
                        'cli_contents': cli_contents,
                        'randseed': randseed,
                        'cmd': cmd,
                        'clinp': clinp_contents,
                        'monthlies': monthlies})
    
    else:
        r = Response(response=cli_contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r

import math
from wepppy.climates.cligen import par_row_formatter
from wepppy.all_your_base import clamp
from scipy.optimize import fmin_slsqp, minimize
import numpy as np


def _make_single_storm_clinp(wd, cli_fn, par_fn, cliver, kwds):
    """
    makes an input file that is passed as stdin to cligen
    """
    clinp = _join(wd, "clinp.txt")
    fid = open(clinp, "w")

    if cliver == "4.3":
        fid.write("\n{par_fn}\nn\n".format(par_fn=par_fn))

    storm_date = kwds.get('storm_date', None)
    storm_date = storm_date.split('-')
    storm_date = ' '.join(storm_date)

    design_storm_amount_inches = kwds.get('design_storm_amount_inches', None)

    duration_of_storm_in_hours = kwds.get('duration_of_storm_in_hours', None)

    time_to_peak_intensity_pct = kwds.get('time_to_peak_intensity_pct')
    time_to_peak_intensity_pct = float(time_to_peak_intensity_pct) * 0.01

    max_intensity_inches_per_hour = kwds.get('max_intensity_inches_per_hour', None)

    fid.write("4\n{storm_date}\n"
              "{design_storm_amount_inches}\n"
              "{duration_of_storm_in_hours}\n"
              "{time_to_peak_intensity_pct}\n"
              "{max_intensity_inches_per_hour}\n"
              "{cli_fn}\n"
              "n\n\n".format(cli_fn=cli_fn,
                             storm_date=storm_date,
                             design_storm_amount_inches=design_storm_amount_inches,
                             duration_of_storm_in_hours=duration_of_storm_in_hours,
                             time_to_peak_intensity_pct=time_to_peak_intensity_pct,
                             max_intensity_inches_per_hour=max_intensity_inches_per_hour))
    fid.close()

    assert _exists(clinp)


@app.route('/selected_single_storm/<par>', methods=['GET', 'POST'])
@app.route('/selected_single_storm/<par>/', methods=['GET', 'POST'])
def single_storm(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/selected_single_storm/106152/?storm_date=6-10-2014&design_storm_amount_inches=6.3&duration_of_storm_in_hours=4&time_to_peak_intensity_pct=40&max_intensity_inches_per_hour=3.0&cliver=4.3
    https://wepp1.nkn.uidaho.edu/webservices/cligen/selected_single_storm/106152/?storm_date=6-10-2014&design_storm_amount_inches=6.3&duration_of_storm_in_hours=4&time_to_peak_intensity_pct=40&max_intensity_inches_per_hour=3.0&cliver=5.3
    https://wepp1.nkn.uidaho.edu/webservices/cligen/selected_single_storm/106152/?storm_date=6-10-2014&design_storm_amount_inches=6.3&duration_of_storm_in_hours=4&time_to_peak_intensity_pct=40&max_intensity_inches_per_hour=3.0&cliver=5.3&returnjson=True
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        d = request.args
    else:  # POST
        d = request.get_json()

    cliver = d.get('cliver', None)
    if cliver is None:
        cliver = '5.3'

    returnjson = d.get('returnjson', False)
    returnjson = bool(returnjson)
    
    if 'storm_date' not in d or \
       'design_storm_amount_inches' not in d or \
       'duration_of_storm_in_hours' not in d or \
       'time_to_peak_intensity_pct' not in d or \
       'max_intensity_inches_per_hour' not in d:
        return jsonify({'Error': 'need storm_date, ' 
                        'design_storm_amount_inches, '
                        'duration_of_storm_in_hours, ' 
                        'time_to_peak_intensity_pct, ' 
                        ' and max_intensity_inches_per_hour'})

    # create working directory to build climate
    _uuid = str(uuid.uuid4())
    wd = _join(static_dir, _uuid)
    os.mkdir(wd)
    os.chdir(wd)

    # write par
    par_fn = par + '.par'
    par_contents = _fetch_par_contents(par, request)

    with open(_join(wd, par_fn), 'w') as fp:
        fp.write(par_contents)

    # create cligen input file
    cli_fn = 'wepp.cli'

    # noinspection PyBroadException
    try:
        _make_single_storm_clinp(wd, cli_fn, par_fn, cliver, d)
    except Exception:
        jsonify({'Error': 'Could not build cligen input file. Check input parameters'})

    # build cmd
    if cliver == "5.3":
        cmd = [_join(_bin_dir, 'cligen53'), "-i%s" % par_fn]
    elif cliver == "5.2":
        cmd = [_join(_bin_dir, 'cligen52'), "-i%s" % par_fn]
    else:
        cmd = [_join(_bin_dir, 'cligen43')]

    # run cligen
    _clinp = open("clinp.txt")
    output = check_output(cmd, stdin=_clinp, stderr=STDOUT, timeout=3.0)
    with open("cligen.log", "wb") as fp:
        fp.write(output)

    assert _exists(cli_fn)

    with open(cli_fn) as fp:
        cli_contents = fp.read()

    if returnjson:
        with open("clinp.txt") as fp:
            clinp_contents = fp.read()
            
        return jsonify({'par_fn': par_fn,
                        'par_contents': par_contents,
                        'cli_fn': cli_fn,
                        'cli_contents': cli_contents,
                        'cmd': cmd,
                        'clinp': clinp_contents})
    
    else:
        r = Response(response=cli_contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r


# noinspection PyPep8Naming
@app.route('/observed_daymet/<par>', methods=['GET', 'POST'])
@app.route('/observed_daymet/<par>/', methods=['GET', 'POST'])
def observed_daymet(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/observed_daymet/106152/?lng=-116&lat=46.5&start_year=1984&end_year=1988
    https://wepp1.nkn.uidaho.edu/webservices/cligen/observed_daymet/106152/?lng=-116&lat=46.5&start_year=1984&end_year=1988&returnjson=True
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        d = request.args
    else:  # POST
        d = request.get_json()

#    cliver = d.get('cliver', None)
#    if cliver is None:
#        cliver = '5.3'

    start_year = d.get('start_year', None)
    end_year = d.get('end_year', None)
    
    if not isint(start_year) or not isint(end_year):
        return jsonify({'Error': 'start_year and end_year must be supplied as integers. %s' % str(d)})

    start_year = int(start_year)
    end_year = int(end_year)

    d0 = 1980
    dend = int(time.strftime("%Y"))-1

    # noinspection PyBroadException
    try:
        assert start_year >= d0
        assert start_year <= dend

        assert end_year >= d0
        assert end_year <= dend
    except Exception:
        return jsonify({'Error': 'start_year and end_year must be between 1980 and 2017'})
        
    lng = d.get('lng', None)
    lat = d.get('lat', None)

    returnjson = d.get('returnjson', False)
    returnjson = bool(returnjson)
    
    # create working directory to build climate
    _uuid = str(uuid.uuid4())
    wd = _join(static_dir, _uuid)
    os.mkdir(wd)
    os.chdir(wd)

    # write par
    par_fn = par + '.par'
    par_contents = _fetch_par_contents(par, request)

    with open(_join(wd, par_fn), 'w') as fp:
        fp.write(par_contents)

    # find station
    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)

    if stationMeta is None:
        return jsonify({'Error': 'cannot find par'})

    if lng is None and lat is None:
        lng = stationMeta.longitude
        lat = stationMeta.latitude
        
    df = retrieve_historical_timeseries(lng, lat, start_year, end_year)
    
    df.to_csv('timeseries.csv')
    df_to_prn(df, 'input.prn', 'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)')
    
    # build cmd
    cli_fn = "observed.cli"
    cmd = [_join(_bin_dir, 'cligen53'),
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

    # replace 
    c = 1.0 / (41840.0 / 1000000.0)
    dayl = df['dayl(s)']
    srad = df['srad(W/m^2)']
    srld = dayl * srad / 1000000  # Daily total radiation (MJ/m2/day)
    srld *= c
    climate = ClimateFile(cli_fn)
    climate.replace_var('rad', df.index, srld)
    climate.write("observed2.cli")
        
    if returnjson:
        with open('timeseries.csv') as fp:
            ts_contents = fp.read()
            
        with open('input.prn') as fp:
            prn_contents = fp.read()
                
        return jsonify({'par_fn': par_fn,
                        'par_contents': par_contents,
                        'cli_fn': par + '.cli',
                        'cli_contents': climate.contents,
                        'cmd': cmd,
                        'timeseries': ts_contents,
                        'metadata': 'Observed data from Daymet',
                        'prn': prn_contents})
    
    else:
        r = Response(response=climate.contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r


# noinspection PyPep8Naming
@app.route('/future_rcp85/<par>', methods=['GET', 'POST'])
@app.route('/future_rcp85/<par>/', methods=['GET', 'POST'])
def future_rcp85(par):
    """
    https://wepp1.nkn.uidaho.edu/webservices/cligen/future_rcp85/106152/?lng=-116&lat=46.5&start_year=2010&end_year=2020
    https://wepp1.nkn.uidaho.edu/webservices/cligen/future_rcp85/106152/?lng=-116&lat=46.5&start_year=2010&end_year=2020&returnjson=True
    """
    if request.method not in ['GET', 'POST']:
        return jsonify({'Error': 'Expecting GET or POST'})

    if request.method == 'GET':
        d = request.args
    else:  # POST
        d = request.get_json()

#    cliver = d.get('cliver', None)
#    if cliver is None:
#        cliver = '5.3'

    start_year = d.get('start_year', None)
    end_year = d.get('end_year', None)
    
    if not isint(start_year) or not isint(end_year):
        return jsonify({'Error': 'start_year and end_year must be supplied as integers. %s' % str(d)})

    start_year = int(start_year)
    end_year = int(end_year)

    d0 = 2006
    dend = 2099

    assert start_year >= d0
    assert start_year <= dend

    assert end_year >= d0
    assert end_year <= dend
    
    lng = d.get('lng', None)
    lat = d.get('lat', None)

    returnjson = d.get('returnjson', False)
    returnjson = bool(returnjson)
    
    # create working directory to build climate
    _uuid = str(uuid.uuid4())
    wd = _join(static_dir, _uuid)
    os.mkdir(wd)
    os.chdir(wd)

    # write par
    par_fn = par + '.par'
    par_contents = _fetch_par_contents(par, request)

    with open(_join(wd, par_fn), 'w') as fp:
        fp.write(par_contents)

    # find station
    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)

    if stationMeta is None:
        return jsonify({'Error': 'cannot find par'})

    if lng is None and lat is None:
        lng = stationMeta.longitude
        lat = stationMeta.latitude
        
    df = retrieve_rcp85_timeseries(lng, lat, 
                                   datetime(start_year, 1, 1), 
                                   datetime(end_year, 12, 31))
    
    df.to_csv('timeseries.csv')
    df_to_prn(df, 'input.prn', u'pr(mm)', u'tasmax(degc)', u'tasmin(degc)')
    
    # build cmd
    cli_fn = "future.cli"
    cmd = [_join(_bin_dir, 'cligen53'),
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

    # -- no replacements are made --    
    
    climate = ClimateFile(cli_fn)

    if returnjson:
        with open('timeseries.csv') as fp:
            ts_contents = fp.read()
            
        with open('input.prn') as fp:
            prn_contents = fp.read()
                
        return jsonify({'par_fn': par_fn,
                        'par_contents': par_contents,
                        'cli_fn': cli_fn,
                        'cli_contents': climate.contents,
                        'cmd': cmd,
                        'timeseries': ts_contents,
                        'metadata': 'Observed data from Daymet',
                        'prn': prn_contents})
    
    else:
        r = Response(response=climate.contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r


if __name__ == "__main__":
    static_dir = os.path.abspath('tests/cligen')

#    import sys
#    sys.exit()

    # TAHOE
#    prism_optimized2(par=49105, years=100, lng=-120.07926310342026, lat=38.92748089665569)

    #  BETATAKIN AZ
#    prism_optimized2(par=20750, years=100, lng=-110.3350738205662, lat=36.57180756866028)

    # HOOD RIVER EXP STA OR
#    prism_optimized2(par=354003, years=100, lng=-121.8621, lat=45.6436)
