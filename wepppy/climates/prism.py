# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
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
              nwds_method='', randseed=None, cliver=None, suffix='', logger=None):
    """

    :param par:
    :param years:
    :param lng:
    :param lat:
    :param wd:
    :param nwds_method: '' or 'daymet' (daymet is experimental)
    :param randseed:
    :param cliver:
    :param suffix:
    :param logger:
    :return:
    """

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
            if nwd > days - 0.25:
                nwd = days - 0.25

            nwds[i] = nwd

        pw = nwds / days_in_mo

        assert np.all(pw >= 0.0)
        assert np.all(pw <= 1.0), pw

        ratio = station.pwds / station.pwws
        p_wws = 1.0 / (1.0 - ratio + ratio / pw)
        p_wds = ((p_wws - 1.0) * pw) / (pw - 1.0)

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

        logger.log('p(w|w) and p(w|d)\n')
        logger.log('Station p(w|w) : %s\n' % _rowfmt(station.pwws))
        logger.log('Cligen p(w|w)  : %s\n' % _rowfmt(p_wws))
        logger.log('Station p(w|d) : %s\n' % _rowfmt(station.pwds))
        logger.log('Cligen p(w|d)  : %s\n' % _rowfmt(p_wds))

        logger.log('Daily P for day precipitation occurs\n')
        logger.log('Station : %s\n' % _rowfmt(station.ppts))
        logger.log('Target  : %s\n' % _rowfmt(daily_ppts))

    os.chdir(curdir)

    return cli.calc_monthlies()


# noinspection PyPep8Naming
def prism_revision(cli_fn: str, ws_lng: float, ws_lat: float,
                   hill_lng: float, hill_lat: float, new_cli_fn: None):

    if new_cli_fn is None:
        assert cli_fn.endswith('.cli'), cli_fn
        new_cli_fn = cli_fn.replace('.cli', '_revised.cli')

    cli = ClimateFile(cli_fn)
    df = cli.as_dataframe()

    ws_ppts = get_prism_monthly_ppt(ws_lng, ws_lat, units='daily mm')
    ws_tmaxs = get_prism_monthly_tmax(ws_lng, ws_lat, units='c')
    ws_tmins = get_prism_monthly_tmin(ws_lng, ws_lat, units='c')

    hill_ppts = get_prism_monthly_ppt(hill_lng, hill_lat, units='daily mm')
    hill_tmaxs = get_prism_monthly_tmax(hill_lng, hill_lat, units='c')
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

    cli.write(new_cli_fn)
    monthlies = cli.calc_monthlies()

    return new_cli_fn, monthlies

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
