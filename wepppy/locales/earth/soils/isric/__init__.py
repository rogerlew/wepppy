from owslib.wms import WebMapService

import os
from os.path import join as _join
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import logging

from datetime import datetime

from wepppy.all_your_base import isfloat
from wepppy.all_your_base.geo import GeoTransformer
from wepppy.all_your_base.geo import RasterDatasetInterpolator

from wepppy.wepp.soils import  HorizonMixin
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.nodb.status_messenger import StatusMessenger

from rosetta import Rosetta
import hashlib
import base64

from osgeo import gdal

_logger = logging.getLogger(__name__)

wrb_rat = {
 0: 'Acrisols',
 1: 'Albeluvisols',
 2: 'Alisols',
 3: 'Andosols',
 4: 'Arenosols',
 5: 'Calcisols',
 6: 'Cambisols',
 7: 'Chernozems',
 8: 'Cryosols',
 9: 'Durisols',
 10: 'Ferralsols',
 11: 'Fluvisols',
 12: 'Gleysols',
 13: 'Gypsisols',
 14: 'Histosols',
 15: 'Kastanozems',
 16: 'Leptosols',
 17: 'Lixisols',
 18: 'Luvisols',
 19: 'Nitisols',
 20: 'Phaeozems',
 21: 'Planosols',
 22: 'Plinthosols',
 23: 'Podzols',
 24: 'Regosols',
 25: 'Solonchaks',
 26: 'Solonetz',
 27: 'Stagnosols',
 28: 'Umbrisols',
 29: 'Vertisols'
}

soil_grid_proj4 = '+proj=igh +datum=WGS84 +no_defs +towgs84=0,0,0'

def adjust_to_grid(bbox, grid_size=100):
    """
    Adjusts the given bounding box coordinates to align with a 100m grid.
    """
    global soil_grid_proj4

    geo_transformer = GeoTransformer(src_epsg=4326, dst_proj4=soil_grid_proj4)
    x_min, y_min = geo_transformer.transform(bbox[0], bbox[1])
    x_max, y_max = geo_transformer.transform(bbox[2], bbox[3])

    if x_max < x_min:
        x_min, x_max = x_max, x_min

    # Adjust the minimum coordinates to the nearest lower grid boundary
    adjusted_x_min = x_min - (x_min % grid_size)
    adjusted_y_min = y_min - (y_min % grid_size)

    # Adjust the maximum coordinates to the nearest upper grid boundary
    adjusted_x_max = x_max + (grid_size - (x_max % grid_size)) % grid_size
    adjusted_y_max = y_max + (grid_size - (y_max % grid_size)) % grid_size

    width_m = adjusted_x_max - adjusted_x_min
    height_m = adjusted_y_max - adjusted_y_min

    return (adjusted_x_min, adjusted_y_min, adjusted_x_max, adjusted_y_max), (width_m/grid_size, height_m/grid_size)


isric_measures = (
    'bdod',  # Bulk density
    'cec',   # Cation exchange capacity
    'clay',  # Clay content
    'sand',  # Sand content
    'silt',  # Silt content
    'cfvo',  # Coarse fragments
    'soc',   # Soil organic carbon content
    'wv1500',  # Water content at 1500 kPa
    'wv0033',  # Water content at 33 kPa
    'wv0010'   # Water content at 10 kPa
)
isric_maps = [f'https://maps.isric.org/mapserv?map=/map/{measure}.map' for measure in isric_measures]

isric_wrb_map = 'https://maps.isric.org/mapserv?map=/map/wrb.map'

isric_depths = (
    '0-5cm',
    '5-15cm',
    '15-30cm',
    '30-60cm',
    '60-100cm',
    '100-200cm'
)

isric_conversion_factors = {
    'bdod': 100,  # Bulk density (cg/cm³)
    'cec': 10,   # Cation exchange capacity (mmol(c)/kg)
    'clay': 10,  # Clay content
    'sand': 10,  # Sand content
    'silt': 10,  # Silt content
    'cfvo': 10,  # Coarse fragments
    'soc': 10,   # Soil organic carbon content
    'wv1500': 10,  # Water content at 1500 kPa
    'wv0033': 10,  # Water content at 33 kPa
    'wv0010': 10   # Water content at 10 kPa
}

def fetch_layer(wms_url, layer, crs, adj_bbox, size, format, soils_dir, status_channel=None):
    """
    Fetch a single ISRIC soil layer.
    """
    if status_channel:
            StatusMessenger.publish(status_channel, f'    fetch_layer({layer}:{wms_url})')
    wms = WebMapService(wms_url)
    response = wms.getmap(layers=[layer],
                          srs=crs,
                          bbox=adj_bbox,
                          size=size,
                          format=format)
    filename = f'{layer}.tif'
    with open(os.path.join(soils_dir, filename), 'wb') as out:
        out.write(response.read())

def fetch_isric_soil_layers(wgs_bbox, soils_dir='./', status_channel=None):
    """
    Fetches the ISRIC soil layers for the given bounding box in parallel.
    """
    if status_channel:
         StatusMessenger.publish(status_channel, f'  fetch_isric_soil_layers({wgs_bbox})')

    global isric_maps

    adj_bbox, size = adjust_to_grid(wgs_bbox)

    crs = 'EPSG:152160'  # Coordinate Reference System
    format = 'image/tiff'  # Desired output format

    # Prepare tasks
    tasks = []
    for wms_url in isric_maps:
        wms = WebMapService(wms_url)
        for layer in wms.contents:
            if 'Q0.5' not in layer:
                continue
            task = (wms_url, layer, crs, adj_bbox, size, format, soils_dir, status_channel)
            tasks.append(task)

    # Execute tasks in parallel
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(fetch_layer, *task) for task in tasks]
        futures.append(executor.submit(fetch_isric_wrb, wgs_bbox, soils_dir, status_channel))

        pending = set(futures)
        while pending:
            done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

            if not done:
                _logger.warning('ISRIC layer retrieval still running after 60 seconds; continuing to wait.')
                continue

            for future in done:
                try:
                    future.result()
                except Exception:
                    for remaining in pending:
                        remaining.cancel()
                    raise


def fetch_isric_wrb(wgs_bbox, soils_dir='./', status_channel=None):
    """
    Fetches the ISRIC soil layers for the given bounding box.
    """
    global isric_wrb_map

    if status_channel:
         StatusMessenger.publish(status_channel, f'    fetch_isric_wrb({wgs_bbox})')

    adj_bbox, size = adjust_to_grid(wgs_bbox)

    crs = 'EPSG:152160'  # Coordinate Reference System
    _format = 'image/tiff'  # Desired output format

    wms = WebMapService(isric_wrb_map)

    # Request the map
    response = wms.getmap(layers=['MostProbable'],
                          srs=crs,
                          bbox=adj_bbox,
                          size=size,
                          format=_format)

    # Save the response to a file
    filename = 'wrb_MostProbable.tif'
    with open(_join(soils_dir, filename), 'wb') as out:
        out.write(response.read())


    # Open the GeoTIFF in update mode
    ds = gdal.Open(_join(soils_dir, filename), gdal.GA_Update)

    if ds is None:
        print("Error opening the GeoTIFF file.")
    else:
        # Assuming the RAT is to be attached to the first band
        band = ds.GetRasterBand(1)


        # Create a new GDALRasterAttributeTable
        rat = gdal.RasterAttributeTable()

        # Add columns for the RAT
        rat.CreateColumn('VALUE', gdal.GFT_Integer, gdal.GFU_Generic)
        rat.CreateColumn('RSG', gdal.GFT_String, gdal.GFU_Generic)

        # Populate the RAT with data from wrb_rat dictionary
        for value, classification in wrb_rat.items():
            idx = rat.GetRowCount()
            rat.SetValueAsInt(idx, 0, value)  # Set value in 'VALUE' column
            rat.SetValueAsString(idx, 1, classification)  # Set soil classification in 'RSG' column


        # Attach the RAT to the band
        band.SetDefaultRAT(rat)

        # Close the dataset to flush changes
        ds = None


class ISRICHorizon(HorizonMixin):
    def __init__(self, depth, horizon_d):
        self.rfg = horizon_d['cfvo']
        self.cec = horizon_d['cec']
        self.clay = horizon_d['clay']
        self.sand = horizon_d['sand']
        self.vfs = horizon_d['silt']
        self.bd = horizon_d['bdod']
        self.om = horizon_d['soc']
        self.th33 = horizon_d['wv0033']
        self.th1500 = horizon_d['wv1500']

        self.depth = float(depth.split('-')[-1].replace('cm', '')) * 10.0 # in mm


_disclaimer = '''\
# THIS FILE AND THE CONTAINED DATA IS PROVIDED BY THE UNIVERSITY OF IDAHO 
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED 
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UNIVERSITY OF IDAHO 
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHERE IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS FILE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
# '''

class ISRICSoilData:
    def __init__(self, soils_dir='./'):
        self.soils_dir = soils_dir
        self.wgs_bbox = None

    def fetch(self, wgs_bbox, status_channel=None):
        self.wgs_bbox = wgs_bbox
        fetch_isric_soil_layers(wgs_bbox, self.soils_dir, status_channel=status_channel)

    def extract_soil_data(self, lng, lat):
        global isric_measures, isric_depths, isric_conversion_factors

        if self.wgs_bbox is None:
            raise ValueError('No bounding box has been set. Please call the fetch method first.')

        soil_data = {}
        for depth in isric_depths:
            soil_data[depth] = {}
            for measure in isric_measures:
                file_path = _join(self.soils_dir, f'{measure}_{depth}_Q0.5.tif')
                if not file_path:
                    raise ValueError(f'File {file_path} does not exist. Please call the fetch method first.')

                # Create the interpolator
                interpolator = RasterDatasetInterpolator(file_path)
                value = interpolator.get_location_info(lng, lat, method='nearest')
                soil_data[depth][measure] = value / isric_conversion_factors[measure]

        return soil_data

    def get_wrb(self, lng, lat):
        file_path = _join(self.soils_dir, 'wrb_MostProbable.tif')
        interpolator = RasterDatasetInterpolator(file_path)
        value = interpolator.get_location_info(lng, lat, method='nearest')
        return wrb_rat[int(value)]

    def build_soil(self, lng, lat, soil_fn=None, res_lyr_ksat_threshold=2.0, ksflag=0, ini_sat=0.75, meta=None):
        """
        ksflag
           0 - do not use adjustments (conductivity will be held constant)
           1 - use internal adjustments
        """

        assert int(ksflag) in [0, 1]
        ksflag = int(ksflag)

        assert isfloat(ini_sat)

        build_date = datetime.now()
        soil_data = self.extract_soil_data(lng, lat)

        # create wepp soil
        wrb = self.get_wrb(lng, lat)

        ks = None
        ksat_min = 1e38
        ksat_last = None
        res_lyr_i = None
        res_lyr_ksat = None

        _log = []

        horizons = []
        for i, depth in enumerate(isric_depths):
            horizon_data = soil_data[depth]
            horizon = ISRICHorizon(depth, horizon_data)
            horizon._rosettaPredict()
            horizon._computeErodibility()
            horizon._computeAnisotropy()
            horizon._computeConductivity()
            horizon._computeAlbedo()

            _log.append(f'sand={horizon.sand}')
            _log.append(f'cec={horizon.cec}')
            _log.append(f'conductivity={horizon.conductivity}')

            _ksat = horizon.ksat
            if _ksat is None:
                continue

            if _ksat < ksat_min:
                ksat_min = _ksat

            if _ksat < res_lyr_ksat_threshold:
                res_lyr_i = i
                res_lyr_ksat = ksat_min

            ksat_last = _ksat

            horizons.append(horizon)

        if not horizons:
            return None, None, meta

        h0 = horizons[0]
        nsl = len(horizons)

        simple_texture = h0.simple_texture

        if simple_texture is None:
            return None, None, meta

        s = ['7778',
             '#',
             '#            WEPPcloud (c) University of Idaho',
             '#',
             '#  Build Date: ' + str(build_date),
             '#  Source Data: ISRIC SoilGrids',
             '#', '#']

        s.extend(_disclaimer.split('\n'))

        s.append('#')
        s.append(f'# Location: {lng}, {lat}')
        s.append('#')
        s.append('Any comments:')
        s.append(f'1 {ksflag}')

        print(wrb, simple_texture, nsl, h0.albedo, ini_sat, h0.interrill, h0.rill, h0.shear)


        s.append(f"'{wrb}'\t\t'{simple_texture}'\t"\
                 f"{nsl}\t{h0.albedo:0.4f}\t"\
                 f"{ini_sat:0.4f}\t{h0.interrill:0.2f}\t{h0.rill:0.4f}\t"\
                 f"{h0.shear:0.4f}")

        for horizon in horizons:
            s2 = '{0:>9}\t{1:>8}\t{2:>9}\t'\
                 '{3:>5}\t{4:>9}\t{5:>9}\t'\
                 '{6:>7}\t{7:>7}\t{8:>7}\t'\
                 '{9:>7}\t{10:>7}'.format(*str(horizon).split())

            s.append('\t' + s2)

        if res_lyr_i is None:
            s.append('1 10000.0 %0.5f' % ksat_last)
        else:
            s.append('1 10000.0 %0.5f' % (res_lyr_ksat * 3.6))

        mukey = short_hash_id('\n'.join(s[9:]))
        if soil_fn is None:
            soil_fn = f'{mukey}.sol'

        with open(_join(self.soils_dir, soil_fn), 'w') as fp:
            fp.write('\n'.join(s))

        with open(_join(self.soils_dir, soil_fn + '.log'), 'w') as fp:
            fp.write('\n'.join(_log))


        return mukey, SoilSummary(mukey=mukey,
                                  fname=soil_fn,
                                  soils_dir=self.soils_dir,
                                  build_date=str(build_date),
                                  desc=wrb), meta


def short_hash_id(input_string, length=8):
    """
    Generate a short hash ID from a given string.

    :param input_string: The input string to hash.
    :param length: The desired length of the short hash. Default is 8 characters.
    :return: A short hash ID of the specified length.
    """
    # Hash the input string using SHA-256
    hash_bytes = hashlib.sha256(input_string.encode('utf-8')).digest()

    # Encode the hash using Base64 to get a shorter representation
    base64_encoded = base64.urlsafe_b64encode(hash_bytes).decode('utf-8')

    # Truncate the Base64-encoded string to the desired length
    short_hash = base64_encoded.replace('_', '').replace('-', '')[:length]

    return short_hash


def _build_soil(lng, lat, soils_dir):
    os.makedirs(soils_dir, exist_ok=True)
    soil = ISRICSoilData(soils_dir)
    soil.fetch((lng-0.1, lat-0.1, lng+0.1, lat+0.1))
    ret = soil.build_soil(lng, lat, 'wepp.sol')

    if ret:
        with open(_join(soils_dir, 'wepp.sol')) as fp:
            print(fp.read())
    else:
        with open('failed.txt', 'a') as fp:
            fp.write(f'{soils_dir},{lng},{lat}\n')


if __name__ == "__main__":
    from os.path import exists as _exists
    from wepppy.climates.cligen import CligenStationsManager
    mgr = CligenStationsManager(version='ghcn')

    lng, lat, soils_dir = 87.75, 58.88, 'RSE00150200'
    soil = ISRICSoilData(soils_dir)
    soil.fetch((lng-0.1, lat-0.1, lng+0.1, lat+0.1))
    import sys
    sys.exit()

    for station in mgr.stations:
        soils_dir = station.par.replace('.par', '')
        if _exists(_join(soils_dir, 'wepp.sol')):
            continue

        print(station.par, station.longitude, station.latitude)
        _build_soil(station.longitude, station.latitude, soils_dir)
