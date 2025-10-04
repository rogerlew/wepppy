import wepppy
from wepppy.nodb.core import Ron, Watershed
from glob import glob

import json
import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import numpy as np


from datetime import datetime

import pyproj
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform


import wepppy
from wepppy.nodb.core import *
from wepppy.nodb.mods.locations import LakeTahoe

from os.path import join as _join
from os.path import abspath
from wepppy.nodb.mods.locations.lt.selectors import *
from wepppy.wepp.out import TotalWatSed2
from wepppy.wepp.management import pmetpara_prep
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()

def log_print(msg):
    global wd

    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))



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


def rasterize_geometry_from_geojson(dem_fn, geometry, dst_fn):
    # Open the DEM GeoTIFF file
    with rasterio.open(dem_fn) as dem:
        # Get the metadata from the DEM
        transform = dem.transform
        crs = dem.crs  # This is the UTM CRS of the DEM
        width = dem.width
        height = dem.height
        dtype = rasterio.uint8  # Adjust the dtype as needed

    # Reproject the geometry from WGS84 to the UTM CRS
    project = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    geometry_utm = shapely_transform(project, geometry)

    # Create an empty raster with the same dimensions as the DEM
    raster_shape = (height, width)
    out_raster = np.zeros(raster_shape, dtype=dtype)

    # Convert geometry to the format required for rasterize
    shapes = [(geometry_utm, 1)]

    # Rasterize the geometry
    rasterized = rasterize(
        shapes,
        out_shape=raster_shape,
        transform=transform,
        fill=0,
        dtype=dtype,
    )

    # Save the rasterized output to the specified file
    with rasterio.open(
        dst_fn,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(rasterized, 1)

    print(f"Rasterized geometry saved to {dst_fn}")


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

blacklist = [v.strip() for v in open('blacklist').readlines()]
print(blacklist)

failed_fp = open('failed_delineation.txt', 'a')

gpkg_files = []

for watersheds_fn in watersheds_fns:
    state = _split(watersheds_fn)[1][:2]

    with open(watersheds_fn) as fp:
        watersheds = json.load(fp)

    for watershed in watersheds['features']:
        props = watershed['properties']
        
        if 'Area' in props:
            shape_area_m2 = props['Area']
        elif 'Shape_Area' in props:
            shape_area_m2 = props['Shape_Area']
        else:
            shape_area_m2 = None
            
        geometry = watershed['geometry']

        label = props.get('SrcName', None)
        pws_id = props.get('PwsId', None)

        if label is None:
            label = props.get('Src_label', None)
            pws_id = props.get('PWS_ID', None)

        SrcName = f'{pws_id}_{label}'

        name = _sanitize_name(SrcName)
        runid = f'24roses-{state}_{name.replace(" ", "_")}'

        if runid in blacklist:
            continue

        wd = _join(f'/geodata/weppcloud_runs/{runid}')

        print(state, name, wd)
        
        bound_fn = _join(wd, 'dem/topaz/BOUND.WGS.JSON')
        
        if not _exists(bound_fn):
            continue

        gpkg_files.append((runid, bound_fn, shape_area_m2))
        

print (gpkg_files)

# combine shp_fns geojson files into a single geodataframe
import geopandas as gpd
import pandas as pd
import fiona

# Create an empty list to store GeoDataFrames
gdfs = []

# Loop through each file and read all layers
for (run_id, file, shape_area_m2) in gpkg_files:
    
    # Use fiona to list all the layers in the current GeoPackage
    layers = fiona.listlayers(file)
    for layer in layers:
        
        gdf = gpd.read_file(file, layer=layer)
        # remove all features in the gdf except the first
        gdf = gdf.head(1)
        
        gdf['run_id'] = run_id
        gdf['shape_area_m2'] = shape_area_m2
        gdfs.append(gdf)
        

# Concatenate all GeoDataFrames into a single one
combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

# Save the combined GeoDataFrame to a new GeoPackage
combined_gdf.to_file("combined_bounds.gpkg", layer='combined_layer', driver="GPKG")
