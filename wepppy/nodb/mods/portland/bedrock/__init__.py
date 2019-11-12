import os
import csv
from os.path import join as _join
import warnings
from osgeo import ogr

from wepppy.all_your_base import RasterDatasetInterpolator

_thisdir = os.path.dirname(__file__)

"""
roger@wepp1:/usr/lib/python3/dist-packages/wepppy/nodb/mods/portland/bedrock⟫ gdal_rasterize -l Bedrock -a OBJECTID -tr 30.0 30.0 -a_nodata 0.0 -te 862644.9015748054 1331481.7965879291 977244.4967191529 1395676.03969816 -ot Byte -of GTiff -at Bedrock.shp Bedrock.tif
"""


class BullRunBedrock(object):
    def __init__(self):
        with open(_join(_thisdir, 'Bedrock_attrs.csv')) as fp:
            csv_rdr = csv.DictReader(fp)
            d = {}
            for row in csv_rdr:
                row['ksat'] = float(row['ksat'])
                row['Shape_Leng'] = float(row['Shape_Leng'])
                row['Shape_Area'] = float(row['Shape_Area'])
                row['OBJECTID'] = int(row['OBJECTID'])
                d[row['OBJECTID']] = row

            self._d = d

    def get_bedrock(self, lng, lat):
        try:
            rdi = RasterDatasetInterpolator(_join(_thisdir, 'Bedrock.tif'))
            object_id = rdi.get_location_info(lng, lat, method='nearest')

            return self._d[object_id]
        except:
            warnings.warn('failed finding bedrock {}, {}'.format(lng, lat))
            return self._d[5]


if __name__ == "__main__":
    bullrun_bedrock = BullRunBedrock()
    print(bullrun_bedrock.get_bedrock(-122.0, 45.5))
