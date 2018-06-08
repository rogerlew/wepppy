import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import shutil

from collections import Counter

import pyproj

import numpy as np
import matplotlib.pyplot as plt

from wepppy.all_your_base import shapefile, wmesque_retrieve, wgs84_proj4, read_raster, build_mask


def px_to_utm(transform, x: int, y: int):
    e = transform[0] + transform[1] * x
    n = transform[3] + transform[5] * y
    return e, n


def px_to_lnglat(transform, x: int, y: int, utm_proj, wgs_proj):
    e, n = px_to_utm(transform, x, y)
    return pyproj.transform(utm_proj, wgs_proj, e, n)


def centroid_px(indx, indy):
    """
    given a sets of x and y indices calulates a central [x,y] index
    """
    return (int(round(float(np.mean(indx)))),
            int(round(float(np.mean(indy)))))

if __name__ == "__main__":
    cellsize = 90

    if _exists('build'):
        shutil.rmtree('build')

    os.mkdir('build')

    shp = "data/cb_2017_us_county_500k/cb_2017_us_county_500k"
    sf = shapefile.Reader(shp)
    print(sf.shapeType)
    print(sf.fields)
    header = [field[0] for field in sf.fields][1:]

    fp = open('dom_mukeys_by_county.csv', 'w')
    fpe = open('failed_counties.txt', 'w')
    for i, shape in enumerate(sf.iterShapes()):
        try:
            record = {k: v for k, v in zip(header, sf.record(i))}
            print(record)

            fips = record['AFFGEOID']

            print('setting map')
            bbox = shape.bbox
            pad = max(abs(bbox[0] - bbox[2]), abs(bbox[1] - bbox[3])) * 0.05
            map_center = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
            l, b, r, t = bbox
            bbox = [l - pad, b - pad, r + pad, t + pad]
            print(bbox)

            ssurgo_fn = _join('build', '%s.tif' % fips)

            wmesque_retrieve('ssurgo/201703', bbox,
                             ssurgo_fn, cellsize)

            mukey_map, transform, utmproj4 = read_raster(ssurgo_fn)

            utm_proj = pyproj.Proj(utmproj4)
            wgs_proj = pyproj.Proj(wgs84_proj4)
            points = [pyproj.transform(wgs_proj, utm_proj, lng, lat) for lng, lat in shape.points]
            assert len(points) > 0

            mask = build_mask(points, ssurgo_fn)

    #        plt.figure()
    #        plt.imshow(mask)
    #        plt.savefig(_join('build', 'ma_%s.png' % fips))

            indx, indy = np.where(mask == 0.0)
            assert len(indx) > 0
            assert len(indy) > 0

            incounty = mukey_map[(indx, indy)]

            c_px, c_py = centroid_px(indx, indy)
            c_lng, c_lat = px_to_lnglat(transform, c_px, c_py, utm_proj, wgs_proj)
            assert c_lng > l
            assert c_lng < r
            assert c_lat > b
            assert c_lat < t

            n = mask.shape[0]*mask.shape[1]
            print(incounty.shape, n, incounty.shape[0]/n)
            counter = Counter(incounty)
            dom_mukey = None
            for k, cnt in counter.most_common():
                if k != 0.0:
                    dom_mukey = int(k)
                    break
            print('mukey', dom_mukey)

            if dom_mukey is None:
                raise Exception('Failed to determine MUKEY')

            fp.write('{STATEFP},{COUNTYFP},{COUNTYNS},{AFFGEOID},{GEOID}'
                     ',{NAME},{LSAD},{ALAND},{AWATER},{mukey},{c_lng},{c_lat}\n'
                     .format(**record, mukey=dom_mukey, c_lng=c_lng, c_lat=c_lat))

        except:
            fpe.write('{AFFGEOID}\n'.format(**record))

    fp.close()
    fpe.close()
