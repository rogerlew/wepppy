import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from glob import glob

from collections import Counter
from pprint import pprint

import numpy as np

import rasterio
from rasterio import features

import geopandas as gpd

from wepppy.all_your_base.geo import raster_stacker, GeoTransformer, read_raster

from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap


sbs_dirs = glob('*/')
sbs_dirs = [d.replace('/', '') for d in sbs_dirs]


def blacklist(func):
    def func_wrapper(top):
        fns = func(top)
        if not _exists(_join(top, 'blacklist.txt')):
            return fns
        else:
            with open(_join(top, 'blacklist.txt')) as fp:
                blacklist = [L.split('#')[0].strip() for L in fp.readlines()]
            _fns = []
            for fn in fns:
                fn = _split(fn)[-1]
                if not any(bad_fn.endswith(fn) for bad_fn in blacklist):
                    _fns.append(fn)
            return _fns

    return func_wrapper

@blacklist
def find_sbs_tifs(top):
    tifs = []
    for (root, dirs, files) in os.walk(top, topdown=True):
        for name in files:
            if (name.lower().endswith('.tif') or 
                name.lower().endswith('.img') 
            ) and (
                'sbs' in name.lower() or
                'severity' in name.lower()
            ) and (
                'sbs256' not in name.lower()
            ):
                tifs.append(_join(root, name))
    return tifs

@blacklist
def find_sbs_shps(top):
    shps = []
    for (root, dirs, files) in os.walk(top, topdown=True):
        for name in files:
            if name.lower().endswith('.shp') and \
                'boundary' not in name.lower() and \
                'barc' not in name.lower():
                shps.append(_join(root, name))
    return shps



def rasterize_sbs(georef_fn, shp_fns):
    outdir, fire_fn = _split(georef_fn)
    raster = rasterio.open(georef_fn)
    proj4 = raster.crs.to_proj4()

    geom_value = []
    for shp_fn in shp_fns:
        print(shp_fn)

        c = gpd.read_file(shp_fn)

        key = None
        if 'SEVERITY' in c:
            key = 'SEVERITY'
        if 'Severity' in c:
            key = 'Severity'
        if 'SBS' in c:
            key = 'SBS'
        print('key', key)
        if key is None:
            continue

        c = c.to_crs(proj4)

        for sev_desc, geom in zip(c[key], c.geometry):
            sev_desc = sev_desc.lower()

            burn_severity = 0
            if 'low' in sev_desc:
                burn_severity = 1
            elif 'mod' in sev_desc:
                burn_severity = 2
            elif 'high' in sev_desc:
                burn_severity = 3

            geom_value.append((geom, burn_severity))

    if len(geom_value) == 0:
        return -1

    rasterized = features.rasterize(
        geom_value,
        out_shape = raster.shape,
        transform = raster.transform,
        fill = 255,
        all_touched = True,
        dtype = np.int16)

    with rasterio.open(
        f"{outdir}/sbs.tif", "w",
        driver = "GTiff",
        crs = raster.crs,
        transform = raster.transform,
        dtype = rasterio.uint8,
        count = 1,
        width = raster.width,
        height = raster.height) as dst:
        dst.write(rasterized, indexes = 1) 
        dst.write_colormap(
            1, {
              0: (0, 100, 0, 255),  # unburned
              1: (127, 255, 212, 255),  # low
              2: (255, 255, 0, 255),  # moderate
              3: (255, 0, 0, 255),  # high
              255: (255, 255, 255, 0)})  # n/a

    return 1

if __name__ == "__main__":

    targets = glob('/geodata/revegetation/rasters_na/6.2.8/*/')
    for target in targets:

        mtbs_id = target.split('/')[-2].lower()

#        if mtbs_id != 'or4211012080120120806':
#            continue

        print(target)

        nbr_fn = glob(_join(target, '*nbr*.tif'))
        assert len(nbr_fn) == 1, nbr_fn
        nbr_fn = nbr_fn[0]

        if mtbs_id in sbs_dirs:
            print(f'{mtbs_id}')
            contents = os.listdir(mtbs_id)
            pprint(contents)

            if len(contents) == 1:
                print('no sbs download link available for {mtbs_id}')
                continue

            tifs = find_sbs_tifs(mtbs_id)
            if len(tifs) > 0:
                print('tifs:', tifs)
                _sbs_fn = f'{target}/_og_warped_sbs.tif'
                raster_stacker(tifs[0], nbr_fn, _sbs_fn)
                sbs_map = SoilBurnSeverityMap(_sbs_fn)
                print('color_table', sbs_map.ct)
                sbs_map.export_4class_map(f'{target}/sbs.tif')
                data, _, _ = read_raster(f'{target}/sbs.tif')
                print('exported counts', Counter(list(data.flatten())).most_common())
                continue

            sbs_shps = find_sbs_shps(mtbs_id)
            if len(sbs_shps) > 0:
                print('shps:', sbs_shps)
                rasterize_sbs(nbr_fn, sbs_shps)
                data, _, _ = read_raster(f'{target}/sbs.tif')
                print(Counter(list(data.flatten())).most_common())

        else:
            print(f'no sbs data downloaded for {mtbs_id}')

