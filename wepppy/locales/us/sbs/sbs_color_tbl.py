from osgeo import gdal

import os
from os.path import join as _join
from pprint import pprint
from collections import Counter
import numpy as np


def get_color_table(fn):
    ds = gdal.Open(fn)
    band = ds.GetRasterBand(1)
    data = list(band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize).flatten())
    counts = Counter(data).most_common()
    ct = band.GetRasterColorTable()
    if ct is None:
        return counts, None
    d = []
    for i in range(ct.GetCount()):
        entry = ct.GetColorEntry(i)
        d.append(entry)

    return counts, d


if __name__ == "__main__":
    top = '.'
    for (root, dirs, files) in os.walk(top, topdown=True):
        for name in files:
            if (
                name.lower().endswith('.tif') or 
                name.lower().endswith('.img')
               ) and (
                'sbs' in name.lower() or
                'severity' in name.lower()
               ):
                fn = _join(root, name)
                print(fn)
                counts, tbl = get_color_table(fn)
                pprint(counts)
                pprint(tbl)
                print()
    
