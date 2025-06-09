from os.path import join as _join, exists, split as _split
import os
import sys
import rasterio

from collections import deque
import math
from osgeo import gdal, osr
import utm
from wepppy.all_your_base.geo import get_utm_zone, utm_srid

from wepppy.topo.watershed_abstraction.support import (
    cummnorm_distance, compute_direction, representative_normalized_elevations,
    weighted_slope_average, rect_to_polar, write_slp, HillSummary, ChannelSummary, CentroidSummary,
    slp_asp_color, polygonize_netful, polygonize_bound, polygonize_subcatchments, json_to_wgs
)

sys.path.append('/Users/roger/src/whitebox-tools/WBT/')
from whitebox_tools import WhiteboxTools

_outlet_template_geojson = """{{
"type": "FeatureCollection",
"name": "Outlet",
"crs": {{ "type": "name", "properties": {{ "name": "urn:ogc:def:crs:EPSG::{epsg}" }} }},
"features": [
{{ "type": "Feature", "properties": {{ "Id": 0 }}, 
   "geometry": {{ "type": "Point", "coordinates": [ {easting}, {northing} ] }} }}
]
}}"""

_multi_outlet_template_geojson = """{{
"type": "FeatureCollection",
"name": "Outlets",
"crs": {{ "type": "name", "properties": {{ "name": "urn:ogc:def:crs:EPSG::{epsg}" }} }},
"features": [
{points}
]
}}"""

_point_template_geojson = """{{ "type": "Feature", "properties": {{ "Id": {id} }}, 
   "geometry": {{ "type": "Point", "coordinates": [ {easting}, {northing} ] }} }}"""


def isfloat(value):
    """
    Check if a value can be converted to a float.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def remove_if_exists(fn):
    """
    Remove a file if it exists.
    """
    if exists(fn):
        os.remove(fn)


class WhiteboxToolsTopazEmulator:
    def __init__(self, dem_fn, wbt_wd, verbose=False):
        dem_fn = os.path.abspath(dem_fn)
        if not exists(dem_fn):
            raise FileNotFoundError(f"DEM file does not exist: {dem_fn}")

        self._parse_dem(dem_fn)

        self.wbt_wd = os.path.abspath(wbt_wd)
        if not exists(self.wbt_wd):
            os.makedirs(self.wbt_wd)

        self.verbose = verbose

        self.mcl = None  # Minimum Channel Length
        self.csa = None  # Channel Source Area
        self._wbt = None

        self._outlet = None  # Outlet object

    @property
    def wbt(self):
        """
        Returns the WhiteboxTools instance.
        """
        if self._wbt is None:
            self._wbt = WhiteboxTools()
            self._wbt.verbose = self.verbose
        return self._wbt

    @property
    def dem(self):
        if not exists(self._dem):
            raise FileNotFoundError(f"DEM file does not exist: {self._dem}")
        return self._dem

    @property
    def relief(self):
        """
        Returns the path to the relief file. 
        """
        return _join(self.wbt_wd, 'relief.tif')

    @property
    def flovec(self):
        """
        Returns the path to the d8 flow vector file.
        64	128	1
        32	0	2
        16	8	4

        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#d8pointer
        """
        return _join(self.wbt_wd, 'flovec.tif')

    @property
    def floaccum(self):
        """
        Returns the path to the d8 flow accumulation file.

        Units: number of inflowing grid cells
        """
        return _join(self.wbt_wd, 'floaccum.tif')

    @property
    def netful0(self):
        """
        Returns the path to the stream network file before applying short stream removal.
        """
        return _join(self.wbt_wd, 'netful0.tif')

    @property
    def netful(self):
        """
        Returns the path to the stream network file.
        """
        return _join(self.wbt_wd, 'netful.tif')
    
    @property
    def netful_json(self):
        """
        Returns the path to the stream network file in JSON format.
        """
        return _join(self.wbt_wd, 'netful.json')
    
    @property
    def netful_wgs_json(self):
        """
        Returns the path to the stream network file in WGS84 JSON format.
        """
        return _join(self.wbt_wd, 'netful.WGS.json')
    
    @property
    def chnjnt(self):
        """
        Returns the path to the stream junction file.
        """
        return _join(self.wbt_wd, 'chnjnt.tif')

    @property
    def outlet_geojson(self):
        """
        Returns the path to the outlet geojson file.
        """
        return _join(self.wbt_wd, 'outlet.geojson')
    
    @property
    def bounds(self):
        """
        Returns the path to the bounds raster file.

        1 for the watershed area, nodata outside.
        """
        return _join(self.wbt_wd, 'bounds.tif')
    
    @property
    def aspect(self):
        """
        Returns the path to the aspect raster file.
        """
        return _join(self.wbt_wd, 'aspect.tif')
    
    @property
    def discha(self):
        """
        Returns the path to the distannce to channel raster file.
        """
        return _join(self.wbt_wd, 'discha.tif')
    
    @property
    def fvslop(self):
        """
        Returns the path to the flow vector slope file.
        """
        return _join(self.wbt_wd, 'fvslop.tif')
    
    @property
    def netw0(self):
        """
        Returns the path to the netw file 0. this is the netful masked to the watershed bounds.
        """
        return _join(self.wbt_wd, 'netw0.tif')

    def _parse_dem(self, dem_fn):
        """
        Uses gdal to extract elevation values from dem and puts them in a
        single column ascii file named DEDNM.INP for topaz
        """
        # open the dataset
        ds = gdal.Open(dem_fn)

        # read and verify the num_cols and num_rows
        num_cols = ds.RasterXSize
        num_rows = ds.RasterYSize

        if num_cols <= 0 or num_rows <= 0:
            raise Exception('input is empty')

        # read and verify the _transform
        _transform = ds.GetGeoTransform()

        if abs(_transform[1]) != abs(_transform[5]):
            raise Exception('input cells are not square')

        cellsize = abs(_transform[1])
        ul_x = int(round(_transform[0]))
        ul_y = int(round(_transform[3]))

        lr_x = ul_x + cellsize * num_cols
        lr_y = ul_y - cellsize * num_rows

        ll_x = int(ul_x)
        ll_y = int(lr_y)

        # read the projection and verify dataset is in utm
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())

        datum, utm_zone, hemisphere = get_utm_zone(srs)
        if utm_zone is None:
            raise Exception('input is not in utm')

        # get band
        band = ds.GetRasterBand(1)

        # get band dtype
        dtype = gdal.GetDataTypeName(band.DataType)

        if 'float' not in dtype.lower():
            raise Exception('dem dtype does not contain float data')

        # extract min and max elevation
        stats = band.GetStatistics(True, True)
        minimum_elevation = stats[0]
        maximum_elevation = stats[1]

        # store the relevant variables to the class
        self._dem = dem_fn
        self.transform = _transform
        self.num_cols = num_cols
        self.num_rows = num_rows
        self.cellsize = cellsize
        self.ul_x = ul_x
        self.ul_y = ul_y
        self.lr_x = lr_x
        self.lr_y = lr_y
        self.ll_x = ll_x
        self.ll_y = ll_y
        self.datum = datum
        self.hemisphere = hemisphere
        self.epsg = utm_srid(utm_zone, hemisphere == 'N')
        self.utm_zone = utm_zone
        self.srs_proj4 = srs.ExportToProj4()
        srs.MorphToESRI()
        self.srs_wkt = srs.ExportToWkt()
        self.minimum_elevation = minimum_elevation
        self.maximum_elevation = maximum_elevation

        del ds

    def _create_relief(self, fill_or_breach='fill'):
        """
        Create a relief file from the DEM using WBT using either fill or breach method.
        """
        relief_fn = self.relief

        remove_if_exists(relief_fn)

        if fill_or_breach == 'fill':
            self.wbt.fill_depressions(dem=self.dem, output=relief_fn)
        elif fill_or_breach == 'breach':
            self.wbt.breach_depressions(dem=self.dem, output=relief_fn)
        else:
            raise ValueError(
                "fill_or_breach must be either 'fill' or 'breach'")

        if not exists(relief_fn):
            raise Exception(f"Relief file was not created: {relief_fn}")

        if self.verbose:
            print(f"Relief file created successfully: {relief_fn}")

    def _create_flow_vector(self):
        """
        Create a flow vector file from the relief file using WBT.
        """
        relief_fn = self.relief

        if not exists(relief_fn):
            raise FileNotFoundError(f"Relief file does not exist: {relief_fn}")

        flovec_fn = self.flovec

        remove_if_exists(flovec_fn)

        self.wbt.d8_pointer(dem=relief_fn, output=flovec_fn, esri_pntr=False)

        if not exists(flovec_fn):
            raise Exception(f"Flow vector file was not created: {flovec_fn}")

        if self.verbose:
            print(f"Flow vector file created successfully: {flovec_fn}")

    def _create_flow_accumulation(self):
        """
        Create a flow accumulation file from the flow vector file using WBT.
        """
        flovec_fn = self.flovec

        if not exists(flovec_fn):
            raise FileNotFoundError(
                f"Flow vector file does not exist: {flovec_fn}")

        floaccum_fn = self.floaccum

        remove_if_exists(floaccum_fn)

        self.wbt.d8_flow_accumulation(i=flovec_fn,
                                      output=floaccum_fn,
                                      out_type="cells",
                                      log=False,
                                      clip=False,
                                      pntr=True,
                                      esri_pntr=False)

        if not exists(floaccum_fn):
            raise Exception(
                f"Flow accumulation file was not created: {floaccum_fn}")

        if self.verbose:
            print(
                f"Flow accumulation file created successfully: {floaccum_fn}")

    def _extract_streams(self):
        """
        Extract streams from the flow accumulation file using WBT.

        csa:
            Channel Source Area threshold for stream extraction in ha

        mcl:
            Minimum Channel Length for stream extraction in m
        """

        if self.csa is None or self.mcl is None:
            raise ValueError(
                "csa and mcl must be set before extracting streams")

        floaccum_fn = self.floaccum

        if not exists(floaccum_fn):
            raise FileNotFoundError(
                f"Flow accumulation file does not exist: {floaccum_fn}")

        netful0_fn = self.netful0

        remove_if_exists(netful0_fn)

        threshold = self.csa * 10000.0  # Convert ha to m^2
        threshold = threshold / (self.cellsize * self.cellsize)

        self.wbt.extract_streams(floaccum_fn, netful0_fn, threshold=threshold)

        if not exists(netful0_fn):
            raise Exception(
                f"Stream network file 0 was not created: {netful0_fn}")

        if self.verbose:
            print(f"Stream network file 0 created successfully: {netful0_fn}")

        netful_fn = self.netful
        remove_if_exists(netful_fn)
        self.wbt.remove_short_streams(
            d8_pntr=self.flovec, 
            streams=netful0_fn, 
            output=netful_fn,
            min_length=self.mcl,
            esri_pntr=False)
        
    def _identify_stream_junctions(self):
        """
        Identify stream junctions from the stream network file using WBT.
        """
        netful_fn = self.netful

        if not exists(netful_fn):
            raise FileNotFoundError(f"Stream network file does not exist: {netful_fn}")

        chnjnt_fn = self.chnjnt

        remove_if_exists(chnjnt_fn)

        self.wbt.stream_junction_identifier(
            d8_pntr=self.flovec, 
            streams=self.netful, 
            output=chnjnt_fn)

        if not exists(chnjnt_fn):
            raise Exception(f"Stream junction file was not created: {chnjnt_fn}")

        if self.verbose:
            print(f"Stream junction file created successfully: {chnjnt_fn}")
        
    def delineate_channels(self, csa=5.0, mcl=60.0, fill_or_breach='fill'):
        """
        Delineate channels from the DEM using WBT.
        """
        self.mcl = mcl
        self.csa = csa

        self._create_relief(fill_or_breach)
        self._create_flow_vector()
        self._create_flow_accumulation()
        self._extract_streams()
        self._identify_stream_junctions()

        polygonize_netful(self.netful, self.netful_json)
        json_to_wgs(self.netful_json)

    def _make_outlet_geojson(self, lng=None, lat=None, dst=None, easting=None, northing=None):
        assert dst is not None

        if lng is not None and lat is not None:
            easting, northing = self.lnglat_to_utm(long=lng, lat=lat)

        assert isfloat(easting), easting
        assert isfloat(northing), northing

        with open(dst, 'w') as fp:
            fp.write(_outlet_template_geojson
                     .format(epsg=self.epsg, easting=easting, northing=northing))

        assert exists(dst), dst
        return dst

    def _make_multiple_outlets_geojson(self, dst, en_points_dict):
        points = []
        for id, (easting, northing) in en_points_dict.items():
            points.append(_point_template_geojson
                          .format(id=id, easting=easting, northing=northing))

        with open(dst, 'w') as fp:
            fp.write(_multi_outlet_template_geojson
                     .format(epsg=self.epsg, points=',\n'.join(points)))

        assert exists(dst), dst
        return dst

        
    def set_outlet(self, lng, lat, pixelcoords=False):
        from wepppy.nodb.watershed import Outlet

        (x, y), distance = self.find_closest_channel2(lng, lat, pixelcoords=pixelcoords)
        _lng, _lat = self.pixel_to_lnglat(x, y)

        _e, _n = self.pixel_to_utm(x, y)
        self._make_outlet_geojson(easting=_e, northing=_n, dst=self.outlet_geojson)

        self._outlet = Outlet(requested_loc=(lng, lat), actual_loc=(_lng, _lat),
                              distance_from_requested=distance, pixel_coords=(x, y))
        
        return self._outlet

    def find_closest_channel2(self, lng, lat, pixelcoords=False):
        """
        Find the closest channel given a lng and lat or pixel coords (pixelcoords=True).

        Returns (x, y), distance
        where (x, y) are pixel coords and distance is the distance from the
        specified lng, lat in pixels.
        """

        # Unpack variables for instance

        chnjnt_fn = self.chnjnt

        with rasterio.open(chnjnt_fn) as src:
            junction_mask = src.read(1)

        num_cols, num_rows = self.num_cols, self.num_rows

        if pixelcoords:
            x, y = lng, lat
        else:
            x, y = self.lnglat_to_pixel(lng, lat)

        # Early return if the starting pixel is already a channel
        if junction_mask[x, y] == 1:
            return (x, y), 0

        # Spiral out from the starting point
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        queue = deque([(x, y, 0)])
        visited = set((x, y))

        while queue:
            cx, cy, dist = queue.popleft()

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy

                if 0 <= nx < num_cols and 0 <= ny < num_rows and (nx, ny) not in visited:
                    if junction_mask[ny, nx] == 1:
                        return (nx, ny), math.sqrt((nx - x) ** 2 + (ny - y) ** 2)
                    visited.add((nx, ny))
                    queue.append((nx, ny, dist + 1))

        return None, math.inf
    
    def lnglat_to_pixel(self, lng, lat):
        """
        return the x,y pixel coords of lng, lat
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        # find easting and northing
        x, y, _, _ = utm.from_latlon(lat, lng, self.utm_zone)
        x, y = float(x), float(y)

        # assert this makes sense with the stored extent
        assert round(x) >= round(ul_x), (x, ul_x)
        assert round(x) <= round(lr_x), (x, lr_x)
        assert round(y) >= round(lr_y), (y, lr_y)
        assert round(y) <= round(y), (y, ul_y)

        # determine pixel coords
        _x = int(round((x - ul_x) / cellsize))
        _y = int(round((ul_y - y) / cellsize))

        # sanity check on the coords
        assert 0 <= _x < num_cols, str(x)
        assert 0 <= _y < num_rows, str(y)

        return _x, _y
    
    def pixel_to_utm(self, x, y):
        """
        return the utm coords from pixel coords
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        assert 0 <= x < num_cols
        assert 0 <= y < num_rows

        easting = ul_x + cellsize * x
        northing = ul_y - cellsize * y

        return easting, northing
    
    def pixel_to_lnglat(self, x, y):
        """
        return the lng/lat (WGS84) coords from pixel coords
        """
        easting, northing = self.pixel_to_utm(x, y)
        lat, lng = utm.to_latlon(easting=easting, northing=northing,
                             zone_number=self.utm_zone, northern=self.hemisphere == 'N')
        lng, lat = float(lng), float(lat)
        return lng, lat
    
    def _create_bounds(self):
        """
        Create a bounds raster from the DEM using WBT.
        """
        bounds_fn = self.bounds

        remove_if_exists(bounds_fn)

        self.wbt.watershed(
            d8_pntr=self.flovec, 
            pour_pts=self.outlet_geojson, 
            output=self.bounds)

        if not exists(bounds_fn):
            raise Exception(f"Bounds file was not created: {bounds_fn}")

        if self.verbose:
            print(f"Bounds file created successfully: {bounds_fn}")

        return bounds_fn
    
    def _create_aspect(self):
        """
        Create an aspect raster from the DEM using WBT.
        """
        aspect_fn = self.aspect

        remove_if_exists(aspect_fn)

        self.wbt.aspect(dem=self.dem, output=aspect_fn)

        if not exists(aspect_fn):
            raise Exception(f"Aspect file was not created: {aspect_fn}")

        if self.verbose:
            print(f"Aspect file created successfully: {aspect_fn}")

        return aspect_fn
    
    def _create_flow_vector_slope(self):
        """
        Create a flow vector slope raster from the flow vector file using WBT.
        """
        fvslop_fn = self.fvslop

        remove_if_exists(fvslop_fn)

        self.wbt.slope(
            dem=self.dem, 
            output=fvslop_fn
        )

        if not exists(fvslop_fn):
            raise Exception(f"Flow vector slope file was not created: {fvslop_fn}")

        if self.verbose:
            print(f"Flow vector slope file created successfully: {fvslop_fn}")

        return fvslop_fn
    
    def _create_netw0(self):
        """
        Create a netw0 raster from the stream network and bounds using WBT.
        This is the stream network masked to the watershed bounds.
        """
        netw0_fn = self.netw0

        remove_if_exists(netw0_fn)

        self.wbt.clip_raster_to_raster(
            i=self.netful, 
            mask=self.bounds, 
            output=netw0_fn
        )

        if not exists(netw0_fn):
            raise Exception(f"Netw0 file was not created: {netw0_fn}")

        if self.verbose:
            print(f"Netw0 file created successfully: {netw0_fn}")

        return netw0_fn

    def _create_distance_to_channel(self):
        """
        Create a distance to channel raster from the stream network using WBT.
        """
        discha_fn = self.discha

        remove_if_exists(discha_fn)

        self.wbt.downslope_distance_to_stream(
            dem=self.dem, 
            streams=self.netw0, 
            output=discha_fn
        )

        if not exists(discha_fn):
            raise Exception(f"Distance to channel file was not created: {discha_fn}")

        if self.verbose:
            print(f"Distance to channel file created successfully: {discha_fn}")

        return discha_fn
    
    def delineate_subcatchments(self):
        """
        Delineate subcatchments from the stream network and outlet.
        """
        
        self._create_bounds()
        self._create_aspect()
        self._create_flow_vector_slope()
        self._create_netw0()
        self._create_distance_to_channel()



if __name__ == "__main__":

    dem = '/Users/roger/src/wepppy/tests/wbt/supine-disputant/dem/dem.tif' 
    wbt_wd = '/Users/roger/src/wepppy/tests/wbt/supine-disputant/dem/wbt'
    verbose = True
    csa = 10.0
    mcl = 100.0
    fill_or_breach = 'fill'  # or 'breach'

    emulator = WhiteboxToolsTopazEmulator(dem, wbt_wd, verbose=verbose)
    emulator.delineate_channels(csa=csa,
                                mcl=mcl,
                                fill_or_breach=fill_or_breach)
    
    outlet = [-116.43008003513219, 45.93324289199021]
    emulator.set_outlet(outlet[0], outlet[1], pixelcoords=False)
    print(f"Outlet set at: {emulator._outlet.actual_loc} with distance {emulator._outlet.distance_from_requested} pixels from requested location {emulator._outlet.requested_loc}")
    
    emulator.delineate_subcatchments()

# Example usage:    
# (wepppy310-env) roger@m4air32:/Users/roger/src/wepppy/wepppy/topo/wbt$ python3 wbt_topaz_emulator.py  /Users/roger/src/wepppy/tests/wbt/supine-disputant/dem/dem.tif /Users/roger/src/wepppy/tests/wbt/supine-disputant/dem/wbt --csa 10 --mcl 100 --verbose