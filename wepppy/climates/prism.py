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

import math
from subprocess import (
    Popen, PIPE, TimeoutExpired
)

import warnings
from copy import deepcopy

import numpy as np
from scipy.optimize import fmin_slsqp, minimize, fmin_l_bfgs_b

from wepppy.all_your_base import clamp

# noinspection PyProtectedMember
from wepppy.climates.cligen import (
    CligenStationsManager,
    ClimateFile,
    _bin_dir,
    par_row_formatter
)

from wepppy.webservices.cligen import _make_clinp

from wepppy.climates.metquery_client import get_prism_monthly_tmin, get_prism_monthly_tmax, get_prism_monthly_ppt, \
    get_daymet_prcp_pwd, get_daymet_prcp_pww, get_daymet_prcp_skew, get_daymet_prcp_std

_rowfmt = lambda x : '\t'.join(['%0.2f' % v for v in x])


def prism_mod(par: int, years: int, lng: float, lat: float, wd: str,
              nwds_method='Daymet', randseed=None, cliver=None, suffix='', logger=None):

    days_in_mo = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

    # determine which version of cligen to use
    if cliver is None:
        cliver = '5.3'

    # change to the working directory
    assert _exists(wd)

    try:
        curdir = os.path.abspath(os.curdir)
    except FileNotFoundError:
        curdir = '../'

    os.chdir(wd)

    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)

    if stationMeta is None:
        raise Exception('Cannot find station')

    station = stationMeta.get_station()
    par_monthlies = station.ppts * station.nwds

    if logger is not None:
        logger.log('  prism_mod:fetching climates...')

    prism_ppts = get_prism_monthly_ppt(lng, lat, units='inch')
    prism_tmaxs = get_prism_monthly_tmax(lng, lat, units='f')
    prism_tmins = get_prism_monthly_tmin(lng, lat, units='f')
    #        p_stds = get_daymet_prcp_std(lng, lat, units='inch')
    #        p_skew = get_daymet_prcp_skew(lng, lat, units='inch')

    # calculate number of wet days
    if nwds_method.lower() == 'daymet':
        p_wws = get_daymet_prcp_pww(lng, lat)
        p_wds = get_daymet_prcp_pwd(lng, lat)
        nwds = days_in_mo * (p_wds / (1.0 - p_wws + p_wds))

    else:
        station_nwds = days_in_mo * (station.pwds / (1.0 - station.pwws + station.pwds))
        delta = prism_ppts / par_monthlies

        nwds = [float(v)for v in station_nwds]

        # clamp between 50% and 200% of original value
        # and between 0.1 days and the number of days in the month
        for i, (d, nwd, days) in enumerate(zip(delta, nwds, days_in_mo)):
            print(d, nwd, days)

            if d > 1.0:
                nwd *= 1.0 + (d - 1.0) / 2.0
            else:
                nwd *= 1.0 - (1.0 - d) / 2.0

            if nwd < station_nwds[i] / 2.0:
                nwd = station_nwds[i] / 2.0
            if nwd < 0.1:
                nwd = 0.1
            if nwd > station_nwds[i] * 2.0:
                nwd = station_nwds[i] * 2.0
            if nwd > days - 0.1:
                nwd = days - 0.1

            nwds[i] = nwd

        pw = nwds / days_in_mo

        assert np.all(pw >= 0.0)
        assert np.all(pw <= 1.0), pw
#        ratio = station.pwds / station.pwws
#        p_wws = 1.0 / (1.0 - ratio + ratio / pw)
#        p_wds = p_wws * ratio

        # ratio = p_wds / (1 - p_wws + p_wds)
        # y = x * z

        p_wds = -pw / (pw - 2.0)
        p_wws = 1.0 / (2.0 - pw)

    if logger is not None:
        logger.log_done()

    if randseed is None:
        randseed = 12345
    randseed = str(randseed)

    daily_ppts = prism_ppts / nwds  # in inches / day

    # build par file
    par_fn = '{}{}.par'.format(par, suffix)

    if _exists(par_fn):
        os.remove(par_fn)

    # p_stds = station.pstds * x[3]

    s2 = deepcopy(station)
    s2.lines[3] = ' MEAN P  ' + par_row_formatter(daily_ppts) + '\r\n'
    #        s2.lines[4] = ' S DEV P ' + par_row_formatter(pstds) + '\r\n'
    s2.lines[6] = ' P(W/W)  ' + par_row_formatter(p_wws) + '\r\n'
    s2.lines[7] = ' P(W/D)  ' + par_row_formatter(p_wds) + '\r\n'
    s2.lines[8] = ' TMAX AV ' + par_row_formatter(prism_tmaxs) + '\r\n'
    s2.lines[9] = ' TMIN AV ' + par_row_formatter(prism_tmins) + '\r\n'

    s2.write(par_fn)

    # run cligen
    cli_fn = '{}{}.cli'.format(par, suffix)

    if _exists(cli_fn):
        os.remove(cli_fn)

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
    process = Popen(cmd, stdin=_clinp, stdout=PIPE, stderr=PIPE,
                    preexec_fn=os.setsid)

    output = process.stdout.read()

    with open("cligen.log", "wb") as fp:
        fp.write(output)

    assert _exists(cli_fn)

    cli = ClimateFile(cli_fn)

    sim_ppts = cli.header_ppts() * days_in_mo
    if np.any(np.isnan(sim_ppts)):
        raise Exception('Cligen failed to produce precipitation')

    sim_nwds = cli.count_wetdays()

    if logger is not None:
        logger.log('Monthly Mean P (in)\n')
        logger.log('Station : %s\n' % _rowfmt(par_monthlies))
        logger.log('PRISM   : %s\n' % _rowfmt(prism_ppts))
        logger.log('Cligen  : %s\n' % _rowfmt(sim_ppts))

        logger.log('Monthly number wet days\n')
        logger.log('Station : %s\n' % _rowfmt(station.nwds))
        logger.log('Target  : %s\n' % _rowfmt(nwds))
        logger.log('Cligen  : %s\n' % _rowfmt(sim_nwds))

        logger.log('Daily P for day precipitation occurs\n')
        logger.log('Station : %s\n' % _rowfmt(station.ppts))
        logger.log('Target  : %s\n' % _rowfmt(daily_ppts))

    os.chdir(curdir)

    return cli.calc_monthlies()

# noinspection PyPep8Naming
def prism_optimized2(par: int, years: int, lng: float, lat: float, wd: str, randseed=None, cliver=None,
                     run_opt=True, x0=None, suffix='', logger=None):
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

    curdir = os.path.abspath(os.curdir)
    os.chdir(wd)

    stationManager = CligenStationsManager()
    stationMeta = stationManager.get_station_fromid(par)

    if stationMeta is None:
        raise Exception('Cannot find station')

    station = stationMeta.get_station()

    if logger is not None:
        logger.log('  prism_opt2:fetching climates...')

    prism_ppts = get_prism_monthly_ppt(lng, lat, units='daily inch')
    prism_tmaxs = get_prism_monthly_tmax(lng, lat, units='f')
    prism_tmins = get_prism_monthly_tmin(lng, lat, units='f')
    p_stds = get_daymet_prcp_std(lng, lat, units='inch')
    p_skew = get_daymet_prcp_skew(lng, lat, units='inch')
    p_wws = get_daymet_prcp_pww(lng, lat)
    p_wds = get_daymet_prcp_pwd(lng, lat)

    if logger is not None:
        logger.log_done()

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

        return error

    if x0 is None:
        x0 = np.array(list(prism_ppts) + [1.0, 1.0])

    args = wd, station, par, randseed, cliver, \
           prism_ppts, p_stds, p_skew, p_wws, p_wds, prism_tmaxs, prism_tmins, suffix

    if run_opt:
        if logger is not None:
            logger.log('  prism_opt2:running optimization...')

        bounds = [(0.01, 10.0) for i in range(14)]
#        result = minimize(opt_fun, x0, args=args, bounds=bounds, tol=0.2, method='L-BFGS-B', options=dict(eps=0.1))
        result = fmin_slsqp(opt_fun, x0, args=args, bounds=bounds, epsilon=0.001, full_output=True, iprint=2)

        if logger is not None:
            logger.log_done()
            logger.log(str(result) + '\n\n')

        cli_fn = '{}.cli'.format(par)
        cli = ClimateFile(cli_fn)
        sim_ppts = cli.header_ppts()
        sim_nwds = cli.count_wetdays()

        if logger is not None:
            logger.log('Optimization Summary\n')
            logger.log('cligen\tprism (target)\t% err\tmm err\tnwds\tstation nwds (target)\n')
            for s, o, d, s_nwd, o_nwd in zip(sim_ppts, prism_ppts, days_in_mo, sim_nwds, station.nwds):
                s *= d * 25.4
                o *= d * 25.4
                logger.log('{0:02.1f}\t{1:02.1f}\t{2:02.1f}\t{3:02.1f}\t{4}\t{5}\n'
                           .format(s, o,  int(100 * (s-o)/o), round(s-o), s_nwd, o_nwd))

        #out, fx, its, lmode, smode = result

        os.chdir(curdir)
        return tuple([float(v) for v in result[0]])

    else:
        if logger is not None:
            logger.log('  prism_opt2:no opt build...')

        result = opt_fun(x0, *args)
        os.chdir(curdir)

        if logger is not None:
            logger.log_done()

        return result

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
