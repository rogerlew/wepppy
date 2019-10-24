import os
from os.path import exists as _exists
from os.path import join as _join

import shutil
from glob import glob
from datetime import date, datetime, timedelta
import numpy as np

from wepppy.all_your_base import c_to_f
from wepppy.climates.cligen import CligenStationsManager, Cligen

def read_livneh_datafn(fn, start_date='1-1-1915'):

    prcp, tmax, tmin, ws, dates = [], [], [], [], []
    mo, da, yr = [int(v) for v in start_date.split('-')]
    t0 = date(yr, mo, da)

    with open(fn) as fp:
        for i, line in enumerate(fp.readlines()):
            _prcp, _tmax, _tmin, _ws = [float(v) for v in line.split()]
            prcp.append(_prcp)
            tmax.append(_tmax)
            tmin.append(_tmin)
            ws.append(_ws)
            dates.append(t0 + timedelta(i))

    return prcp, tmax, tmin, ws, dates


def build_prn(prcp, tmin, tmax, dates, prn_fn, start_year=None, end_year=None):

    if start_year is not None:
        start_year = date(int(start_year), 1, 1)

    if end_year is not None:
        end_year = date(int(end_year), 12, 31)

    prcp = np.array(prcp)
    prcp /= 25.4
    prcp *= 100.0
    prcp = np.round(prcp)

    tmax = np.array(tmax)
    tmax = np.round(c_to_f(tmax))

    tmin = np.array(tmin)
    tmin = np.round(c_to_f(tmin))

    fp = open(prn_fn, 'w')

    for i, (prcp, tmin, tmax, _date) in enumerate(zip(prcp, tmin, tmax, dates)):
        if start_year is not None:
            if _date < start_year:
                continue

        if end_year is not None:
            if _date > end_year:
                continue

        fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                 .format(_date.month, _date.day, _date.year, int(prcp), int(tmax), int(tmin)))

    fp.close()


station_manager = CligenStationsManager()


if __name__ == "__main__":
    climatestation = '353770'
    station_meta = station_manager.get_station_fromid(climatestation)
    print(station_meta.desc)

    data_fns = glob('data*')

    build_dir = 'build'

    if _exists(build_dir):
        shutil.rmtree(build_dir)

    os.mkdir(build_dir)

    for fn in data_fns:
        lat, lng = fn.split('_')[1:]
        lat = float(lat)
        lng = float(lng)
        print(fn, lat, lng)

        prcp, tmax, tmin, ws, dates = read_livneh_datafn(fn)

        prn_fn = _join(build_dir, fn + '.prn')

        build_prn(prcp=prcp, tmin=tmin, tmax=tmax, dates=dates, prn_fn=prn_fn, start_year=1990)

        cligen = Cligen(station_meta, wd=build_dir)
        cligen.run_observed(prn_fn=fn + '.prn', cli_fn=fn + '.cli')

        #results = station_manager \
        #    .get_stations_heuristic_search((lng, lat), 10)

        #print(results)

        #/geodata/weppcloud_runs/CurCond4.1.3b_Watershed_1/climate/102_48758.prn