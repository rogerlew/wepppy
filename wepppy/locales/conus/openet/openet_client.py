import requests
import os
from os.path import join as _join
from os.path import exists as _exists
from datetime import date
import json

import numpy as np

_thisdir = os.path.dirname(__file__)

with open(os.path.join(_thisdir, '.env')) as fp:
    API_KEY = fp.read().strip()

header = {"Authorization": API_KEY}

def fetch_monthly_point_timeseries(lon: float, lat: float, start_date: date, end_date: date, variable='ET'):
    global header

    args = {
        "date_range": [
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        ],
        "interval": "monthly",
        "geometry": [
            lon,
            lat
        ],
        "model": "Ensemble",
        "variable": variable,
        "reference_et": "gridMET",
        "units": "mm",
        "file_format": "JSON"
    }

    resp = requests.post(
        headers=header,
        json=args,
        url="https://openet-api.org/raster/timeseries/point",
        timeout=60
    )

    if resp.status_code != 200:
        print(resp.text)

    return resp.json()


def fetch_monthly_polygon_timeseries(coordinates: list, start_date: date, end_date: date, variable='ET'):
    global header

    # flatten coordinates to list of lon,lat using numpy
    geometry = np.array(coordinates).flatten().tolist()

    args = {
        "date_range": [
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        ],
        "interval": "monthly",
        "geometry": geometry,
        "model": "Ensemble",
        "reducer": "mean",
        "variable": variable,
        "reference_et": "gridMET",
        "units": "mm",
        "file_format": "JSON"
    }

    # query the api, verbose

    resp = requests.post(
        headers=header,
        json=args,
        url="https://openet-api.org/raster/timeseries/polygon",
        timeout=60
    )

    if resp.status_code != 200:
        print(resp.text)

    return resp.json()


def fetch_monthly_multipolygon_timeseries(geojson_fn: str, start_date: date, end_date: date, variable='ET', properties_key='TopazID', outdir='./'):
    global header

    # use fetch_monthly_polygon_timeseries method to query the api
    with open(geojson_fn) as fp:
        geojson = json.load(fp)

    features = geojson['features']
    d = {} # dictionary to store results by properties_key
    for feature in features:
        properties = feature['properties']
        out_fn = _join(outdir, f"openet-{properties[properties_key]}.json")
        if _exists(out_fn):
            print(f"Skipping {properties[properties_key]}")
            continue

        coordinates = feature['geometry']['coordinates']
        try:
            result = fetch_monthly_polygon_timeseries(coordinates, start_date, end_date, variable)
            d[properties[properties_key]] = result
            
            with open(out_fn, 'w') as fp:
                json.dump(result, fp)

        except Exception as e:
            print(f"Error fetching {properties[properties_key]}: {e}")

    with open(_join(outdir, 'openet.json'), 'w') as fp:
        json.dump(d, fp)

    return d


def _test_fetch_monthly_point_timeseries():
    js = fetch_monthly_point_timeseries(lon=-117.0, lat=47.0, start_date=date(2019,1,1), end_date=date(2024,6,30), variable='ET')
    print(js)


def _test_fetch_monthly_polygon_timeseries():
    coordinates = [
          [
            [
              -105.80453420153871,
              33.49700722498243
            ],
            [
              -105.80453169877966,
              33.49673666204813
            ],
            [
              -105.8042087640977,
              33.496738758489066
            ],
            [
              -105.80421126585242,
              33.497009321444764
            ],
            [
              -105.80453420153871,
              33.49700722498243
            ]
          ]
        ]
    js = fetch_monthly_polygon_timeseries(coordinates=coordinates, start_date=date(2019,1,1), end_date=date(2023,12,21), variable='ET')
    print(js)


def _test_fetch_monthly_multipolygon_timeseries():
    js = fetch_monthly_multipolygon_timeseries(geojson_fn='/geodata/weppcloud_runs/mdobre-anadromous-cartridge/dem/topaz/SUBCATCHMENTS.WGS.JSON', start_date=date(2019,1,1), end_date=date(2023,12,21), variable='ET', properties_key='TopazID', outdir='/geodata/weppcloud_runs/mdobre-anadromous-cartridge/openet')
    print(js)


if __name__ == "__main__":
    #_test_fetch_monthly_point_timeseries()
    #_test_fetch_monthly_polygon_timeseries()
    _test_fetch_monthly_multipolygon_timeseries()