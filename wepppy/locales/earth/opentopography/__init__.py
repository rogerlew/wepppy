import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from wepppy.all_your_base.geo import utm_raster_transform

import requests
from requests.exceptions import HTTPError

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)
load_dotenv(_join(_thisdir, '.env'))
OPENTOPOGRAPHY_API_KEY = os.environ.get('OPENTOPOGRAPHY_API_KEY', None)
assert OPENTOPOGRAPHY_API_KEY is not None, 'You must set OPENTOPOGRAPHY_API_KEY in .env file'


def opentopo_retrieve(extent, dst_fn, cellsize, dataset='SRTMGL1_E', resample='bilinear'):
    dataset = dataset.replace('opentopo://', '')

    data_dir, fname = _split(os.path.abspath(dst_fn))

    west, south, east, north = extent
    url = f'https://portal.opentopography.org/API/globaldem?demtype={dataset}&south={south}&north={north}&west={west}&east={east}&outputFormat=GTiff&API_Key={OPENTOPOGRAPHY_API_KEY}'

    src_fn = None
    try:
        # Send a GET request
        response = requests.get(url)

        # Raise an exception in case of HTTP error
        response.raise_for_status()

        # Extract filename from 'content-disposition' header
        cd = response.headers.get('content-disposition')
        if cd:
            # Split the string on "filename=" and then strip quotes and spaces
            filename = cd.split('filename=')[1].strip(' "')
        else:
            filename = 'default_filename.tif'  # Default filename if not found in header

        # Write the content to a file
        src_fn = _join(data_dir, filename)
        with open(src_fn, 'wb') as file:
            file.write(response.content)

    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'An error occurred: {err}')

    utm_raster_transform(extent, src_fn, dst_fn, cellsize, resample=resample)


if __name__ == "__main__":
    fetch_dem((-120.5, 38.5, -120.4, 38.6), 'test.tif', 30)

