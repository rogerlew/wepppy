# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import numpy as np

from wepppy.climates.cligen import (
    ClimateFile,
    par_mod,
)

from wepppy.climates.metquery_client import (
    get_prism_monthly_tmin,
    get_prism_monthly_tmax,
    get_prism_monthly_ppt
)

_rowfmt = lambda x : '\t'.join(['%0.2f' % v for v in x])


def prism_mod(par: int, years: int, lng: float, lat: float, wd: str,
              nwds_method='', randseed=None, cliver=None, suffix='', logger=None):

    return par_mod(par=par, years=years, lng=lng, lat=lat, wd=wd, monthly_dataset='prism',
                   nwds_method=nwds_method, randseed=randseed, cliver=cliver, suffix=suffix,
                   logger=logger)


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
