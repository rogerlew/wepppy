import os
from os.path import join as _join
import dotenv
import requests
import pandas as pd
import duckdb
from wepppy.weppcloud.utils.helpers import get_wd


dotenv.load_dotenv()

WC_TOKEN = os.getenv("WC_TOKEN")
API_BASE = "http://climatena-ca.bearhive.duckdns.org" # os.getenv("API_BASE")

def unpack_csv(csv_txt):
    """
    Unpack the CSV text into a DataFrame.
    """
    prefixes = {'Tmax': 'C', 'Tmin': 'C', 'Tave': 'C', 'PPT': 'mm', 'RH': 'pct'}

    from io import StringIO
    csv_data = StringIO(csv_txt)
    df = pd.read_csv(csv_data, sep=",")
    
    months   = [f"{m:02d}" for m in range(1, 13)]

    out = {}
    for _, row in df.iterrows():
        key = (row["id1"], row["id2"])
        out[key] = { f'{p} ({units})': row[[f"{p}{m}" for m in months]].tolist()
            for p, units in prefixes.items() }
    return out


def query_monthlies(locations, model='na'):
    """
    Query the monthlies for a list of locations.
    """

    global WC_TOKEN

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {WC_TOKEN}'
    }
    url = f"{API_BASE}/{model}/query"
    payload = {
        "locations": locations,
        "normal": "Normal_1991_2020.nrm",
        "mode": "M"
    }

    response = requests.post(url, headers=headers, json=payload, timeout=1200)
   
    # get filename from re
    print(f"responseheader: {response.headers}")

    if response.status_code != 200:
        raise Exception(f"Error querying monthlies: {response.status_code} - {response.text}")
    
    return unpack_csv(response.text)

def query_hillslopes_monthlies(runid, cap=20):
    wd = get_wd(runid)
    hillslopes_parquet = _join(wd, "watershed/hillslopes.parquet")

    hillslopes = []
    with duckdb.connect() as con:
        # lazy load self._sub_area_lookup with duckdb
        result = con.execute(f"SELECT topaz_id, centroid_lon, centroid_lat, elevation FROM read_parquet('{hillslopes_parquet}')").fetchall()
        for i, row in enumerate(result):
            hillslopes.append(dict(id1=runid, id2=str(row[0]), lat=row[2], long=row[1], elev=row[3]))
    monthlies = query_monthlies(hillslopes)    
    return monthlies


if __name__ == "__main__":
    from time import time
    t0 = time()
    monthlies = query_hillslopes_monthlies('featured-reach', cap=2000)
    t1 = time() - t0
    print(f"Time: {t1:.5f} seconds {len(monthlies)} locations, {t1/len(monthlies):.6f} seconds per location")
    print()
        
    import sys
    sys.exit()
    locations = [
    {
        "id1": "string",
        "id2": "1",
        "lat": 45.5,
        "long": -117,
        "elev": 500,
    },
        {
        "id1": "string",
        "id2": "2",
        "lat": 45.7,
        "long": -117,
        "elev": 550,
    }
    ]
    monthlies = query_monthlies(locations)
    from pprint import pprint
    pprint(monthlies)

    result = query_climatena_hillslopes(runid, cap=20, period="Normal_1961_1990.nrm", var_type="M")
    if result:
        logger.info(f"ClimateNA API response: {result}")
