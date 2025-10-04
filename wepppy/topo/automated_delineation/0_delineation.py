import wepppy
from wepppy.nodb.core import Ron, Watershed

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

cfg = "disturbed9002.cfg"  # weppcloud config
pad = 0.02                 # pad in dd for setting project extent


# input vector files
watersheds_fns =[ 'GIS_data/WA/WA_drinking_water_source_areas_less_than_130mi2.json',
                  'GIS_data/OR/OR_drinking_water_source_areas_less_than_130mi2.json' ]


# read in failed delineations
failed = []
if _exists('failed_delineation.txt'):
    with open('failed_delineation.txt') as fp:
        failed = [runid.strip() for runid in fp.readlines()]


skip_failed = True  # specifies whether to retry failed delinations


# dictionary to override the automated extent and outlet for specific watersheds 
defs = {
  '24roses-OR_West_Fall_Creek' : {
    'extent': [-123.96861117193043, 45.43158802270279, -123.90698473760426, 45.4748184445437],
    'outlet': [-123.95692245508418, 45.44197092858651]
  }
}

def _sanitize_name(name):
    """
    Sanitize the name by replacing special characters with spaces and removing unwanted characters.
    """
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
    """
    creates a raster mask from a polygon geometry (e.g a watershed boundary)
    Args:
        dem_fn (str): Path to the DEM GeoTIFF file ro use as template
        geometry (shapely.geometry): The geometry to rasterize
        dst_fn (str): Path to save the rasterized output
    """

    # Open the DEM GeoTIFF file
    with rasterio.open(dem_fn) as dem:
        # Get the metadata from the DEM
        transform = dem.transform
        crs = dem.crs  # This is the UTM CRS of the DEM
        width = dem.width
        height = dem.height
        dtype = rasterio.uint8 

    # Reproject the watershed boundary geometry from WGS84 to the UTM CRS
    project = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    geometry_utm = shapely_transform(project, geometry)

    # Create an empty raster with the same dimensions as the DEM
    raster_shape = (height, width)
    out_raster = np.zeros(raster_shape, dtype=dtype)

    # Convert geometry to the format required for `rasterize`
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
    """

    """
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


# LFG


# open the failed delineation file in append mode
failed_fp = open('failed_delineation.txt', 'a')

# loop over the input geojson files
for watersheds_fn in watersheds_fns:

    # get the state from the filename
    state = _split(watersheds_fn)[1][:2]

    # read in the geojson file
    with open(watersheds_fn) as fp:
        watersheds = json.load(fp)

    # iterate over the features in the geojson file
    for watershed in watersheds['features']:
        props = watershed['properties']
        geometry = watershed['geometry']

        # we need to determine a name for the watershed
        # this is specfic to the 24roses data inptu files
        label = props.get('SrcName', None)
        pws_id = props.get('PwsId', None)

        if label is None:
            label = props.get('Src_label', None)
            pws_id = props.get('PWS_ID', None)

        SrcName = f'{pws_id}_{label}'

        name = _sanitize_name(SrcName)

        # goal is to get this this runid. they should be unique
        runid = f'24roses-{state}_{name.replace(" ", "_")}'

        # define wd for the weppcloud run
        wd = _join(f'/geodata/weppcloud_runs/{runid}')

        print(state, name, wd)

        # check if the watershed has already been delineated and skip if it has
        if _exists(_join(wd, 'watershed/network.txt')):
            continue

        # check if the watershed has been tried
        if skip_failed:
            if runid in failed:
                continue

        # delete the project if it exits
        if _exists(wd):
            shutil.rmtree(wd)

        # create a new wepppy project
        os.makedirs(wd)
        Ron(wd, cfg)


        # get a shapely geometry object from the geojson
        _geometry = shape(geometry)

        # check to see if we have a specific extent definition for this watershed
        _def = defs.get(runid, None)
        extent = None
        if _def is not None:
            extent = _def.get('extent', None)

        # if we don't have a specific extent, we need to determine the extent from the geometry
        # from the geometry bounds and the pad parameter
        if extent is None:
            l, b, r, t = _geometry.bounds
            extent = [l-pad, b-pad, r+pad, t+pad]

        print(extent)
        l, b, r, t = extent

        # set the map parameters for the project
        map_center = (l + r) / 2.0, (b + t) / 2.0
        map_zoom = 11
        ron = Ron.getInstance(wd)
        ron.set_map(extent, map_center, zoom=map_zoom)

        # fetch the dem from wepp.cloud, the DEM source is defiend in the config file
        ron.fetch_dem()

        # get an instance of the watershed controller to run TOPAZ
        watershed = Watershed.getInstance(wd)

        # this runs TOPAZ on the DEM and creates the channels
        watershed.build_channels()

        # check for a specific outlet definition for this watershed
        outlet = None
        if _def is not None:
            outlet = _def.get('outlet')

        # if it doesn't exist, we need to determine the outlet from the UPAREA and ws_mask rasters
        if outlet is None:
            # we need a mask of where the watershed is in the DEM to determine the outlet
            uparea_fn = _join(wd, 'dem/topaz/UPAREA.ARC')
            ws_mask_fn = _join(wd, 'dem/ws_mask.tif')
            rasterize_geometry_from_geojson(uparea_fn, _geometry, ws_mask_fn)

            # find the pixel with the largest upstream area in the masked watershed
            outlet = _determine_outlet(uparea_fn, ws_mask_fn)

        # set the outlet for the watershed
        watershed.set_outlet(*outlet)
        try:
            # this runs topaz to build the subcatchments and network for the watershed
            watershed.build_subcatchments()
        except:
            failed_fp.write(f'{runid}\n')
            continue

        # this runs the watershed abstraction using PERIDOT to get abstracted hillslopes and channel profiles
        watershed.abstract_watershed()

