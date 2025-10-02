import wepppy
from wepppy.nodb import Ron, Watershed

import json
import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import numpy as np

import pyproj
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

cfg = "disturbed9002.cfg"
pad = 0.02

watersheds_fns =[ 'GIS_data/WA/WA_drinking_water_source_areas_less_than_130mi2.json',
                  'GIS_data/OR/OR_drinking_water_source_areas_less_than_130mi2.json' ]


with open('failed_delineation.txt') as fp:
    failed = [runid.strip() for runid in fp.readlines()]

skip_failed = True

defs = {
  '24roses-OR_West_Fall_Creek' : {
    'extent': [-123.96861117193043, 45.43158802270279, -123.90698473760426, 45.4748184445437],
    'outlet': [-123.95692245508418, 45.44197092858651]
  }
}

def _sanitize_name(name):
    return name.replace('.', ' ') \
               .replace('/', ' ') \
               .replace('#', '') \
               .replace('&', '') \
               .replace(';', '') \
               .replace('  ', ' ') \
               .replace('"', '') \
               .replace("'", '') \
               .strip()


def _determine_outlet(uparea_fn, ws_mask_fn):
    with rasterio.open(uparea_fn) as uparea, rasterio.open(ws_mask_fn) as ws_mask:
        uparea_data = uparea.read(1)
        ws_mask_data = ws_mask.read(1)

        assert uparea.transform == ws_mask.transform, "The rasters are not aligned"
        assert uparea.shape == ws_mask.shape, "The rasters do not have the same shape"

        masked_uparea = np.where(ws_mask_data == 1, uparea_data, np.nan)
        assert np.sum(masked_uparea > 0), masked_uparea

        max_index = np.nanargmax(masked_uparea)
        row, col = np.unravel_index(max_index, masked_uparea.shape)
        e, n = rasterio.transform.xy(uparea.transform, row, col)
        transformer = pyproj.Transformer.from_crs(uparea.crs, "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(e, n)
    return lon, lat #, masked_uparea[row, col]



failed_fp = open('failed_delineation.txt', 'a')

for watersheds_fn in watersheds_fns:
    state = _split(watersheds_fn)[1][:2]

    with open(watersheds_fn) as fp:
        watersheds = json.load(fp)

    for watershed in watersheds['features']:
        props = watershed['properties']
        geometry = watershed['geometry']

        label = props.get('SrcName', None)
        pws_id = props.get('PwsId', None)

        if label is None:
            label = props.get('Src_label', None)
            pws_id = props.get('PWS_ID', None)

        SrcName = f'{pws_id}_{label}'

        name = _sanitize_name(SrcName)
        runid = f'24roses-{state}_{name.replace(" ", "_")}'
        wd = _join(f'/geodata/weppcloud_runs/{runid}')

        print(state, name, wd)

        if _exists(_join(wd, 'watershed/network.txt')):
            continue

        if skip_failed:
            if runid in failed:
                continue

        if _exists(wd):
            shutil.rmtree(wd)

        os.makedirs(wd)
        Ron(wd, cfg)

        _geometry = shape(geometry)

        _def = defs.get(runid, None)
        extent = None
        if _def is not None:
            extent = _def.get('extent', None)

        if extent is None:
            l, b, r, t = _geometry.bounds
            extent = [l-pad, b-pad, r+pad, t+pad]

        print(extent)
        l, b, r, t = extent

        map_center = (l + r) / 2.0, (b + t) / 2.0
        map_zoom = 11
        ron = Ron.getInstance(wd)
        ron.set_map(extent, map_center, zoom=map_zoom)
        ron.fetch_dem()

        watershed = Watershed.getInstance(wd)
        watershed.build_channels()

        uparea_fn = watershed.uparea_fn
        ws_mask_fn = watershed.bound_fn

        outlet = None
        if _def is not None:
            outlet = _def.get('outlet')

        if outlet is None:
            outlet = _determine_outlet(uparea_fn, ws_mask_fn)

        watershed.set_outlet(*outlet)
        try:
            watershed.build_subcatchments()
        except wepppy.topo.topaz.topaz.WatershedBoundaryTouchesEdgeError:
            failed_fp.write(f'{runid}\n')
            continue

        watershed.abstract_watershed()
