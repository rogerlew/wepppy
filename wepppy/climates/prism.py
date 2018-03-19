#!/usr/bin/python

# Copyright (c) 2016, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os

from os.path import join as _join
from os.path import exists as _exists

import math
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

import numpy as np
from scipy.optimize import fmin_slsqp

from wepppy.all_your_base import isint, clamp

# noinspection PyProtectedMember
from wepppy.climates.cligen import (
    CligenStationsManager,
    ClimateFile,
    _bin_dir,
    df_to_prn,
    par_row_formatter
)

from wepppy.webservices.cligen import _make_clinp

from wepppy.climates.daymet_singlelocation_client \
    import retrieve_historical_timeseries

from wepppy.climates.downscaled_nmme_client \
    import retrieve_rcp85_timeseries
from wepppy.climates.metquery_client import get_prism_monthly_tmin, get_prism_monthly_tmax, get_prism_monthly_ppt, \
    get_daymet_prcp_pwd, get_daymet_prcp_pww, get_daymet_prcp_skew, get_daymet_prcp_std

static_dir = None
app = Flask(__name__)

# noinspection PyPep8Naming
def prism_optimized2(par: int, years: int, lng: float, lat: float, wd: str, randseed=None, cliver=None,
                     run_opt=True, x0=None, suffix=''):
    """
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
    """

    days_in_mo = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

    if cliver is None:
        cliver = '5.3'

    # create working directory to build climate
    _uuid = str(uuid.uuid4())
    #wd = _join(static_dir, _uuid)
    #wd = os.path.abspath(wd)
    #os.mkdir(wd)

    curdir = os.path.abspath(os.curdir)
    os.chdir(wd)

    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)

    if stationMeta is None:
        return jsonify({'Error': 'cannot find par'})

    station = stationMeta.get_station()

    print('fetching monthly ppts')
    prism_ppts = get_prism_monthly_ppt(lng, lat, units='daily inch')
    print('fetching monthly tmaxs')
    prism_tmaxs = get_prism_monthly_tmax(lng, lat, units='f')
    print('fetching monthly tmin')
    prism_tmins = get_prism_monthly_tmin(lng, lat, units='f')
    print('fetching monthly prcp')
    p_stds = get_daymet_prcp_std(lng, lat, units='inch')
    print('fetching monthly prcp skew')
    p_skew = get_daymet_prcp_skew(lng, lat, units='inch')
    print('fetching monthly prcp pww')
    p_wws = get_daymet_prcp_pww(lng, lat)
    print('fetching monthly prcp pwd')
    p_wds = get_daymet_prcp_pwd(lng, lat)

    if randseed is None:
        randseed = 12345
    randseed = str(randseed)

    def opt_fun(x, *args):
        wd, station, par, randseed, cliver, prism_ppts, p_stds, p_skew, p_wws, p_wds, prism_tmaxs, prism_tmins, suffix = args

        par_fn = '{}{}.par'.format(par, suffix)
        cli_fn = '{}{}.cli'.format(par, suffix)

        if _exists(par_fn):
            os.remove(par_fn)

        if _exists(cli_fn):
            os.remove(cli_fn)

        ppts = x[:12]
#        pstds = p_stds * x[1]

        pwws = p_wws * x[12]
        pwws = [clamp(v, 0.01, 0.99) for v in pwws]

        pwds = p_wds * x[13]
        pwds = [clamp(v, 0.01, 0.99) for v in pwds]

        # p_stds = station.pstds * x[3]

        s2 = deepcopy(station)
        s2.lines[3] = ' MEAN P  ' + par_row_formatter(ppts) + '\r\n'
#        s2.lines[4] = ' S DEV P ' + par_row_formatter(pstds) + '\r\n'
        s2.lines[6] = ' P(W/W)  ' + par_row_formatter(pwws) + '\r\n'
        s2.lines[7] = ' P(W/D)  ' + par_row_formatter(pwds) + '\r\n'
        s2.lines[8] = ' TMAX AV ' + par_row_formatter(prism_tmaxs) + '\r\n'
        s2.lines[9] = ' TMIN AV ' + par_row_formatter(prism_tmins) + '\r\n'

        s2.write(par_fn)

        # create cligen input file
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

#        output = check_output(cmd, stdin=_clinp, stderr=STDOUT, timeout=3.0)
        with Popen(cmd, stdin=_clinp,  stdout=PIPE, stderr=PIPE,
                   preexec_fn=os.setsid) as process:
            try:
                output = process.communicate(timeout=2)[0]
            except TimeoutExpired:
                process.kill()
#                output = process.stdout.read()
                warnings.warn('Error running cligen')
                return 1e6

        with open("cligen.log", "wb") as fp:
            fp.write(output)

        assert _exists(cli_fn)

        cli = ClimateFile(cli_fn)

        sim_ppts = cli.header_ppts()
        if np.any(np.isnan(sim_ppts)):
            warnings.warn('Cligen failed to generate precip')
            return 1e5

        sim_nwds = cli.count_wetdays()
        nwds = station.nwds
        nwds = np.array([(v, 0.1)[float(v) == 0.0] for v in nwds])

        error = (sim_ppts - prism_ppts) / prism_ppts
        nwd_err = (sim_nwds - nwds) / nwds

        error = np.concatenate((error, nwd_err))
        error *= error
        error = math.sqrt(np.sum(error))
        print(error)

        return error

    if x0 is None:
        x0 = np.array(list(prism_ppts) + [1.0, 1.0])

    args = wd, station, par, randseed, cliver, prism_ppts, p_stds, p_skew, p_wws, p_wds, prism_tmaxs, prism_tmins, suffix

    if run_opt:
        bounds = [(0.01, 10.0) for i in range(14)]
    #    result = minimize(opt_fun, x0, args=args, bounds=bounds, tol=0.2, method='L-BFGS-B', options=dict(eps=0.1))
        result = fmin_slsqp(opt_fun, x0, args=args, bounds=bounds, epsilon=0.02, full_output=True, iprint=2)
        print(result)

        cli_fn = '{}.cli'.format(par)
        cli = ClimateFile(cli_fn)
        sim_ppts = cli.header_ppts()
        sim_nwds = cli.count_wetdays()
        print('cligen\tprism (target)\t% err\tmm err\tnwds\tstation nwds (target)')
        for s, o, d, s_nwd, o_nwd in zip(sim_ppts, prism_ppts, days_in_mo, sim_nwds, station.nwds):
            s *= d * 25.4
            o *= d * 25.4
            print('{0:02.1f}\t{1:02.1f}\t{2}\t{3}\t{4}\t{5}'
                  .format(s, o,  int(100 * (s-o)/o), round(s-o), s_nwd, o_nwd))

        #out, fx, its, lmode, smode = result

        os.chdir(curdir)
        return tuple([float(v) for v in result[0]])

    else:
        result = opt_fun(x0, *args)
        os.chdir(curdir)
        return result

# noinspection PyPep8Naming
def prism_revision(cli_fn: str, ws_lng: float, ws_lat: float, hill_lng: float, hill_lat: float, new_cli_fn: str):

    cli = ClimateFile(cli_fn)
    df = cli.as_dataframe()

    print('fetching monthly ppts')
    ws_ppts = get_prism_monthly_ppt(ws_lng, ws_lat, units='daily mm')
    print('fetching monthly tmaxs')
    ws_tmaxs = get_prism_monthly_tmax(ws_lng, ws_lat, units='c')
    print('fetching monthly tmin')
    ws_tmins = get_prism_monthly_tmin(ws_lng, ws_lat, units='c')

    print('fetching monthly ppts')
    hill_ppts = get_prism_monthly_ppt(hill_lng, hill_lat, units='daily mm')
    print('fetching monthly tmaxs')
    hill_tmaxs = get_prism_monthly_tmax(hill_lng, hill_lat, units='c')
    print('fetching monthly tmin')
    hill_tmins = get_prism_monthly_tmin(hill_lng, hill_lat, units='c')

    rev_ppt = np.zeros(df.prcp.shape)
    rev_tmax = np.zeros(df.prcp.shape)
    rev_tmin = np.zeros(df.prcp.shape)

    dates = []

    for i, (index, row) in enumerate(df.iterrows()):
        mo = int(row.mo) - 1
        rev_ppt[i] = float(row.prcp * hill_ppts[mo] / ws_ppts[mo])
        rev_tmax[i] = float(row.tmax - ws_tmaxs[mo] + hill_tmaxs[mo])
        rev_tmin[i] = float(row.tmin - ws_tmins[mo] + hill_tmins[mo])

        dates.append(tuple([int(row.year), int(row.mo), int(row.da)]))

    cli.replace_var('prcp', dates, rev_ppt)
    cli.replace_var('tmax', dates, rev_tmax)
    cli.replace_var('tmin', dates, rev_tmin)

    print('new_cli_fn: ' + new_cli_fn)

    cli.write(new_cli_fn)

if __name__ == "__main__":
    """
    <option value="48758" selected="">TAHOE CA                                 48758 0 (12.1 km)</option>
<option value="42467">DONNER MEMORIAL PK CA                    42467 0 (25.5 km)</option>
<option value="49043">TRUCKEE RS CA                            49043 0 (27.1 km)</option>
<option value="40931">BOCA CA                                  4 931 0 (34.5 km)</option>
<option value="44713">LAKE SPAULDING CA                        44713 0 (41.7 km)</option>
<option value="261485">CARSON CITY NV (42.0 km)</option>
<option value="265191">MINDEN NV (44.0 km)</option>
<option value="49105">TWIN LAKES CA                            49105 0 (46.7 km)</option>
<option value="41018">BOWMAN DAM CA                            41018 0 (52.9 km)</option>
<option value="48218">SIERRAVILLE RS CA                        48218 0 (55.4 km)</option>
    """
    wd = '/home/weppdev/PycharmProjects/wepppy/wepppy/climates/tests/wd'
#    prism_optimized2(par=106152, years=100, lng=-116, lat=47, wd=wd)

    x0 = np.array([ 0.36690092,  0.37521019,  0.31532417,  0.29125945,  0.41512125,
        0.41009472,  0.44130732,  0.46372077,  0.4256049,  0.48817581,
        0.37101017,  0.41849169,  1.75021999,  1.86826402])

    print(prism_optimized2(par=106152, years=100, lng=-116, lat=47, wd=wd, run_opt=False, x0=x0, suffix='_144'))
