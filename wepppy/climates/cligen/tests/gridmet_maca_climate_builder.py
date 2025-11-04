import os
import uuid
import shutil
from datetime import datetime
from os.path import join as _join
from os.path import exists as _exists
from subprocess import Popen, PIPE
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from typing import TYPE_CHECKING

CLIGEN_MISSING_MESSAGE = (
    "The cligen package is required for gridmet MACA climate building. "
    "Install cligen to enable this functionality."
)


try:
    from cligen import ClimateFile, CligenStationsManager, df_to_prn, _bin_dir
    _CLIGEN_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    _CLIGEN_IMPORT_ERROR = exc

    if TYPE_CHECKING:  # pragma: no cover - type checker hint only
        from cligen import ClimateFile, CligenStationsManager  # type: ignore

    def _raise_missing_cligen() -> None:
        raise ModuleNotFoundError(CLIGEN_MISSING_MESSAGE) from exc

    class _MissingBinDir:
        def __fspath__(self) -> str:
            _raise_missing_cligen()

    ClimateFile = None  # type: ignore[assignment]
    CligenStationsManager = None  # type: ignore[assignment]

    def df_to_prn(*args, **kwargs):  # type: ignore[override]
        _raise_missing_cligen()

    _bin_dir = _MissingBinDir()  # type: ignore[assignment]


def _require_cligen() -> None:
    if _CLIGEN_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(CLIGEN_MISSING_MESSAGE) from _CLIGEN_IMPORT_ERROR


def _require_pandas() -> None:
    if _PANDAS_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(
            "pandas is required for gridmet MACA climate building."
        ) from _PANDAS_IMPORT_ERROR

from datetime import datetime
import requests

try:
    import pandas as pd
    _PANDAS_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    pd = None  # type: ignore[assignment]
    _PANDAS_IMPORT_ERROR = exc



IS_WINDOWS = os.name == 'nt'


def try_parse(f):
    if isinstance(f, (int, float)):
        return f

    # noinspection PyBroadException
    try:
        ff = float(f)
        # noinspection PyBroadException
        try:
            fi = int(f)
            return fi
        except Exception:
            return ff
    except Exception:
        return f

def isint(x):
    # noinspection PyBroadException
    try:
        return float(int(x)) == float(x)
    except Exception:
        return False

def isfloat(f):
    # noinspection PyBroadException
    try:
        float(f)
        return True
    except Exception:
        return False
    
def parse_datetime(x):
    """
    parses x in yyyy-mm-dd, yyyy-mm-dd, yyyy/mm/dd, or yyyy mm dd
    to datetime object.
    """
    if isinstance(x, datetime):
        return x
        
    ymd = x.split('-')
    if len(ymd) != 3:
        ymd = x.split('/')
    if len(ymd) != 3:
        ymd = x.split('.')
    if len(ymd) != 3:
        ymd = x.split()
    
    y, m, d = ymd
    y = int(y)
    m = int(m)
    d = int(d)
    
    return datetime(y, m, d)

        
variables_d = {'pr': 'precipitation',
               'tasmax': 'air_temperature',
               'tasmin': 'air_temperature',
               'rsds': 'surface_downwelling_shortwave_flux_in_air',
               'uas': 'eastward_wind',
               'vas': 'northward_wind',
               'huss': 'specific_humidity'}
        
_url_template = \
    'https://climate-dev.nkn.uidaho.edu/Services/get-netcdf-data/'\
    '?decimal-precision=8'\
    '&request-JSON=True'\
    '&lat={lat}'\
    '&lon={lng}'\
    '&positive-east-longitude=True'\
    '&data-path=http://thredds.northwestknowledge.net:8080/thredds/dodsC/'\
    'agg_macav2metdata_{variable_name}_{model}_r1i1p1_{scenario}_CONUS_daily.nc'\
    '&variable={variable}'\
    '&variable-name={variable_name}'\
    '&start-date={start_date}'\
    '&end-date={end_date}'


def _retrieve(lng, lat, start_date, end_date, model, scenario, variable_name, verbose=False):
    global variables_d
        
    # validate input parameters
    assert isfloat(lng)
    assert isfloat(lat)
    
    start_date = parse_datetime(start_date)
    end_date = parse_datetime(end_date)
    
 #   assert model in ['GFDL-ESM2G', 'GFDL-ESM2M']
    
    assert scenario in ["rcp45_2006_2099",
                        "rcp85_2006_2099",
                        "historical_1950_2005"]
                        
    if scenario == "historical_1950_2005":
        d0 = datetime(1950, 1, 1)
        dend = datetime(2005, 12, 31)
    else:
        d0 = datetime(2006, 1, 1)
        dend = datetime(2099, 12, 31)
    
    assert start_date >= d0
    assert start_date <= dend
    
    assert end_date >= d0
    assert end_date <= dend
    
    start_date = start_date.strftime('%Y-%m-%d')
    end_date = end_date.strftime('%Y-%m-%d')
    
    assert variable_name in variables_d
    
    # build url for query
    url = _url_template.format(lat=lat, lng=lng, 
                               start_date=start_date, end_date=end_date, 
                               model=model, scenario=scenario,
                               variable=variables_d[variable_name], 
                               variable_name=variable_name)

    if verbose:
        print(url)

    # query server
    referer = 'https://wepp1.nkn.uidaho.edu'
    s = requests.Session()
    r = s.get(url,  headers={'referer': referer})
    
    if r.status_code != 200:
        raise Exception("Encountered error retrieving "
                        "from downscaledForecast server.\n%s" % url)
        
    # process returned data
    data = r.json()['data'][0]
    assert u'yyyy-mm-dd' in data

    df = pd.DataFrame()
    for k in data:
        if k in [u'lat_lon', u'metadata']:
            continue

        if k == u'yyyy-mm-dd':
            year_month_day = [row.split('-') for row in data[k]]
            df['year'] = [row[0] for row in year_month_day]
            df['month'] = [row[1] for row in year_month_day]
            df['day'] = [row[2] for row in year_month_day]
            df['date'] = data[k]

        elif variable_name in k:
            df[k] = [try_parse(v) for v in data[k]]

    df.set_index(pd.DatetimeIndex(df['date']))
    return df


def retrieve_timeseries(lng, lat, start_date, end_date,
                        model='GFDL-ESM2G', scenario='rcp85_2006_2099', verbose=True):
    _require_pandas()

    result = None
    for variable_name in variables_d:
        df = _retrieve(lng, lat, start_date, end_date, 
                       model, scenario, variable_name, verbose=verbose)
        
        if result is None:
            result = df
        else:
            result = pd.merge(result, df)
    
    if u'tasmin(K)' in result:
        result[u'tasmin(degc)'] = result[u'tasmin(K)'] - 273.15
        
    if u'tasmax(K)' in result:
        result[u'tasmax(degc)'] = result[u'tasmax(K)'] - 273.15

    for key in [u'month_x', u'month_y', u'day_x', u'day_y', u'year_x', u'year_y']:
        if key in result:
            del result[key]

    # Convert the 'date' column to datetime format and set as index
    result['date'] = pd.to_datetime(df['date'])
    result.set_index('date', inplace=True)
    return result

def build_climate(lng, lat, start_date, end_date, model, scenario, identifier=None, cli_dir='./'):
    _require_cligen()

    stationManager = CligenStationsManager(version=2015)
    stationmeta = stationManager.get_closest_station((lng, lat))
    par = stationmeta.par

    # create working directory to build climate
    if identifier is None:
        identifier = str(uuid.uuid4())

    wd = _join(cli_dir, identifier)
        
    if not _exists(wd):
        os.mkdir(wd)

    os.chdir(wd)

    # write par
    par_fn = par + '.par'
    shutil.copyfile(stationmeta.parpath, par_fn)

    df = retrieve_timeseries(lng, lat, 
                             start_date, 
                             end_date,
                             model, scenario)
    
    df.to_csv(_join(wd, f'{model}_{scenario}_timeseries.csv'))
    df_to_prn(df, f'{model}_{scenario}_input.prn', u'pr(mm)', u'tasmax(degc)', u'tasmin(degc)')
    
    # build cmd
    cli_fn = _join(wd, f'{model}_{scenario}.cli')
    cmd = [_join(_bin_dir, ('cligen532', 'cligen532.exe')[IS_WINDOWS]),
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

def process_location(location, models, scenarios):
    for model in models:
        for scenario_d in scenarios:
            scenario = scenario_d['scenario']
            y0, yend = scenario_d['y0'], scenario_d['yend']
            start_date = datetime(int(y0), 1, 1)
            end_date = datetime(int(yend), 12, 31)

            print(model, scenario, start_date, end_date, location)
            lng = location['lng']
            lat = location['lat']
            identifier = location['identifier']

            build_climate(lng, lat, start_date, end_date, model=model, scenario=scenario, identifier=identifier)

if __name__ == '__main__':
    from time import time

    models = ('bcc-csm1-1', 'bcc-csm1-1-m', 'BNU-ESM', 'CanESM2', 'CCSM4', 'CNRM-CM5', 'CSIRO-Mk3-6-0',
              'GFDL-ESM2G', 'GFDL-ESM2M', 'HadGEM2-CC365', 'HadGEM2-ES365', 'inmcm4', 'IPSL-CM5A-MR', 'IPSL-CM5A-LR',
              'IPSL-CM5B-LR', 'MIROC5', 'MIROC-ESM', 'MIROC-ESM-CHEM', 'MRI-CGCM3', 'NorESM1-M')

    scenarios = ({"scenario": "historical_1950_2005", 
                  "y0": 1990, 
                  "yend": 2005},
                  {"scenario": "rcp85_2006_2099", 
                  "y0": 2006, 
                  "yend": 2099})

    locations = [
        {'lng': -117, 'lat': 46.73, 'identifier': "Moscow"},
    ]

    num_workers = 4  # Parameter to control the number of workers

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_location, location, models, scenarios) for location in locations]
        
        pending = set(futures)
        while pending:
            done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

            if not done:
                print('gridmet_maca_climate_builder still processing after 10 seconds; continuing to wait.')
                continue

            for future in done:
                future.result()
