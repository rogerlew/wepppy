import os
import time

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from datetime import datetime

import sys


for p in ['/home/weppdev/PycharmProjects/wepppy/wepppy/climates/cligen/county_db',
          '/home/weppdev/PycharmProjects/wepppy',
          '/home/weppdev/PycharmProjects/wepppy/venv/lib/python36.zip',
          '/home/weppdev/PycharmProjects/wepppy/venv/lib/python3.6',
          '/home/weppdev/PycharmProjects/wepppy/venv/lib/python3.6/lib-dynload',
          '/usr/lib/python3.6',
          '/home/weppdev/PycharmProjects/wepppy/venv/lib/python3.6/site-packages',
          '/snap/pycharm-professional/83/helpers/pycharm_matplotlib_backend']:
    if p not in sys.path:
        sys.path.append(p)

import shutil

from wepppy.climates.metquery_client import get_daily
from wepppy.climates.daymet_singlelocation_client import retrieve_historical_timeseries

from wepppy.climates.cligen import CligenStationsManager, ClimateFile, Cligen, build_daymet_prn, df_to_prn

if __name__ == "__main__":

    worker = None

    try:
        worker = int(sys.argv[-1])
    except:
        pass

    cligenStationsManager = CligenStationsManager(version=2015)

    start_year, end_year = 1980, 2017

    observed_data = {}
    for varname in ['prcp', 'tmin', 'tmax']:
        for year in range(start_year, end_year + 1):
            observed_data[(varname, year)] = _join('/geodata', 'daymet', varname,
                                                   'daymet_v3_{}_{}_na.nc4'.format(varname, year))

    assert _exists('par_by_county.csv')
    assert _exists('failed_counties.txt')

    _build_dir = 'observed_climates'

    if worker is not None:
        _build_dir += str(worker)

    # clean soils directory
    if _exists(_build_dir):
        shutil.rmtree(_build_dir)

    os.mkdir(_build_dir)

    # read the input table from file
    with open('par_by_county.csv') as fp:
        records = fp.readlines()

    _lookup = 'observed_climate_lookup.csv'

    if worker is not None:
        _lookup += str(worker)

    with open(_lookup, 'w') as fp:
        fp.write('AFFGEOID,par,cli,lng,lat\n')

        for i, rec in enumerate(records):
            if worker is not None:
                if i % 4 != worker:
                    continue

            STATEFP, COUNTYFP, COUNTYNS, AFFGEOID, GEOID, NAME, LSAD, ALAND, AWATER, par, c_lng, c_lat = rec.split(',')

            cli_fn = '{}.cli'.format(AFFGEOID)
            prn_fn = '{}.prn'.format(AFFGEOID)

            if _exists(_join(_build_dir, cli_fn)):
                continue

            log_fn = _join(_build_dir, '{}.log'.format(AFFGEOID))
            log_fp = open(log_fn, 'w')
            log_fp.write('Building {}\n'.format(AFFGEOID))
            log_fp.write('Started at {}\n'.format(datetime.utcnow()))

            try:
                c_lng, c_lat = float(c_lng), float(c_lat)

                log_fp.write('Fetching Station\n')
                stationMeta = cligenStationsManager.get_station_fromid(par)
                print(AFFGEOID, par, c_lng, c_lat, stationMeta)
                par_fn = stationMeta.parpath
                cligen = Cligen(stationMeta, wd=_build_dir)

                log_fp.write('Retrieving Timeseries\n')

                attempts = 0

                while attempts < 5:
                    try:
                        df = retrieve_historical_timeseries(c_lng, c_lat, start_year, end_year)
                    except:
                        time.sleep(4)
                        log_fp.write('   failed {}\n'.format(attempts))
                    attempts += 1

                log_fp.write('Building PRN\n')
                df_to_prn(df, _join(_build_dir, prn_fn), 'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)')

                log_fp.write('Running CLIGEN\n')
                cligen.run_observed(prn_fn, cli_fn=cli_fn)

                log_fp.write('Build Completed Successfully\n')
                fp.write('{},{},{},{},{}\n'.format(AFFGEOID, par_fn, cli_fn, c_lng, c_lat))

            except:
                log_fp.write('Build Failed\n')
                fp.write('{},{},{},{},{}\n'.format(AFFGEOID, None, None, None, None))

            log_fp.close()

        with open('failed_counties.txt') as fpe:
            failed_counties = fpe.readlines()
            failed_counties = [fips.strip() for fips in failed_counties]

        for fips in failed_counties:
            fp.write('{},{},{},{},{}\n'.format(fips, None, None, None, None))
