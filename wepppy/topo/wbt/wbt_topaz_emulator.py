from os.path import join as _join, split as _split
import os
import sys
import rasterio

from collections import deque
import math
from osgeo import gdal, osr
import utm
from os.path import exists as _exists
import numpy as np
import pandas as pd
import json
import inspect

from wepppy.all_your_base.geo import get_utm_zone, utm_srid

from wepppy.topo.watershed_abstraction.support import (
    cummnorm_distance,
    compute_direction,
    representative_normalized_elevations,
    weighted_slope_average,
    rect_to_polar,
    write_slp,
    HillSummary,
    ChannelSummary,
    CentroidSummary,
    slp_asp_color,
    polygonize_netful,
    polygonize_bound,
    polygonize_subcatchments,
    json_to_wgs,
)

sys.path.append("/Users/roger/src/whitebox-tools/WBT/")
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
    if _exists(fn):
        os.remove(fn)


class WhiteboxToolsTopazEmulator:
    def __init__(self, wbt_wd, dem_fn=None, verbose=True, raise_on_error=True, logger=None):
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(wbt_wd={wbt_wd}, dem_fn={dem_fn}, verbose={verbose}, raise_on_error={raise_on_error})"
            )

        if dem_fn is not None:
            dem_fn = os.path.abspath(dem_fn)
            if not _exists(dem_fn):
                raise FileNotFoundError(f"DEM file does not exist: {dem_fn}")

            self._parse_dem(dem_fn, logger=logger)

        self.wbt_wd = os.path.abspath(wbt_wd)
        if not _exists(self.wbt_wd):
            os.makedirs(self.wbt_wd)

        self.verbose = verbose

        self.mcl = None  # Minimum Channel Length
        self.csa = None  # Channel Source Area
        self._wbt_runner = None  # WhiteboxTools instance 
        self._raise_on_error = raise_on_error

        self._outlet = None  # Outlet object

    @property
    def raise_on_error(self):
        """
        Returns whether to raise an error on failure.
        """
        return self._raise_on_error

    @raise_on_error.setter
    def raise_on_error(self, value: bool):
        """
        Sets whether to raise an error on failure.
        """
        
        if not isinstance(value, bool):
            raise ValueError("raise_on_error must be a boolean value")
        self._raise_on_error = value

    @property
    def wbt(self):
        """
        Returns the WhiteboxTools instance.
        """
        if self._wbt_runner is None:
            self._wbt_runner = WhiteboxTools(verbose=self.verbose, raise_on_error=self.raise_on_error)

        return self._wbt_runner

    @property
    def dem(self):
        if not _exists(self._dem):
            raise FileNotFoundError(f"DEM file does not exist: {self._dem}")
        return self._dem

    @property
    def relief(self):
        """
        Returns the path to the relief file.
        """
        return _join(self.wbt_wd, "relief.tif")

    @property
    def flovec(self):
        """
        Returns the path to the d8 flow vector file.
        64	128	1
        32	0	2
        16	8	4

        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#d8pointer
        """
        return _join(self.wbt_wd, "flovec.tif")

    @property
    def floaccum(self):
        """
        Returns the path to the d8 flow accumulation file.

        Units: number of inflowing grid cells
        """
        return _join(self.wbt_wd, "floaccum.tif")

    @property
    def netful0(self):
        """
        Returns the path to the stream network file before applying short stream removal.
        """
        return _join(self.wbt_wd, "netful0.tif")

    @property
    def netful(self):
        """
        Returns the path to the stream network file.
        """
        return _join(self.wbt_wd, "netful.tif")

    @property
    def netful_json(self):
        """
        Returns the path to the stream network file in JSON format.
        """
        return _join(self.wbt_wd, "netful.json")

    @property
    def netful_wgs_json(self):
        """
        Returns the path to the stream network file in WGS84 JSON format.
        """
        return _join(self.wbt_wd, "netful.WGS.json")

    @property
    def chnjnt(self):
        """
        Returns the path to the stream junction file.
        """
        return _join(self.wbt_wd, "chnjnt.tif")

    @property
    def outlet_geojson(self):
        """
        Returns the path to the outlet geojson file.
        """
        return _join(self.wbt_wd, "outlet.geojson")

    @property
    def bound(self):
        """
        Returns the path to the bound raster file.

        1 for the watershed area, nodata outside.
        """
        return _join(self.wbt_wd, "bound.tif")

    @property
    def bound_json(self):
        """
        Returns the path to the bound raster file in JSON format.
        """
        return _join(self.wbt_wd, "bound.geojson")
    
    @property
    def bound_wgs_json(self):
        """
        Returns the path to the bound raster file in WGS84 JSON format.
        """
        return _join(self.wbt_wd, "bound.WGS.geojson")

    @property
    def aspect(self):
        """
        Returns the path to the aspect raster file.
        """
        return _join(self.wbt_wd, "taspec.tif")

    @property
    def discha(self):
        """
        Returns the path to the distannce to channel raster file.
        """
        return _join(self.wbt_wd, "discha.tif")

    @property
    def fvslop(self):
        """
        Returns the path to the flow vector slope file.
        """
        return _join(self.wbt_wd, "fvslop.tif")

    @property
    def netw0(self):
        """
        Returns the path to the netw file 0. this is the netful masked to the watershed bound.
        """
        return _join(self.wbt_wd, "netw0.tif")

    @property
    def strahler(self):
        """
        Returns the path to the Strahler order raster file.
        """
        return _join(self.wbt_wd, "strahler.tif")

    @property
    def subwta(self):
        """
        Returns the path to the subcatchments raster file.
        """
        return _join(self.wbt_wd, "subwta.tif")

    @property
    def netw_tab(self):
        """
        Returns the path to the netw table file.
        """
        return _join(self.wbt_wd, "netw.tsv")

    def _parse_dem(self, dem_fn, logger=None):
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}({dem_fn})")
        # open the dataset
        ds = gdal.Open(dem_fn)

        # read and verify the num_cols and num_rows
        num_cols = ds.RasterXSize
        num_rows = ds.RasterYSize  # this is correct

        if num_cols <= 0 or num_rows <= 0:
            raise Exception("input is empty")

        # read and verify the _transform
        #  0,        1,            2,          3,        4,          5
        # (x_origin, x_pixel_size, x_rotation, y_origin, y_rotation, y_pixel_size)
        _transform = ds.GetGeoTransform()

        if abs(_transform[1]) != abs(_transform[5]):
            raise Exception("input cells are not square")

        cellsize = abs(_transform[1])
        ul_x = float(_transform[0])  # easting, correct
        ul_y = float(_transform[3])  # northing, correct

        lr_x = ul_x + cellsize * num_cols  # correct
        lr_y = ul_y - cellsize * num_rows  # correct

        ll_x = float(ul_x)  # correct
        ll_y = float(lr_y)  # correct

        ur_x = float(lr_x)
        ur_y = float(ul_y)

        # read the projection and verify dataset is in utm
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())

        datum, utm_zone, hemisphere = get_utm_zone(srs)
        if utm_zone is None:
            raise Exception("input is not in utm")

        # get band
        band = ds.GetRasterBand(1)

        # get band dtype
        dtype = gdal.GetDataTypeName(band.DataType)

        if "float" not in dtype.lower():
            raise Exception("dem dtype does not contain float data")

        # extract min and max elevation
        stats = band.GetStatistics(True, True)
        minimum_elevation = stats[0]
        maximum_elevation = stats[1]

        # store the relevant variables to the class
        self._dem = dem_fn
        self.transform = [float(x) for x in _transform]
        self.num_cols = int(num_cols)
        self.num_rows = int(num_rows)
        self.cellsize = float(cellsize)
        self.ul_x = float(ul_x)
        self.ul_y = float(ul_y)
        self.ur_x = float(ur_x)
        self.ur_y = float(ur_y)
        self.lr_x = float(lr_x)
        self.lr_y = float(lr_y)
        self.ll_x = float(ll_x)
        self.ll_y = float(ll_y)
        self.datum = datum
        self.hemisphere = hemisphere
        self.epsg = utm_srid(utm_zone, hemisphere == "N")
        self.utm_zone = utm_zone
        self.srs_proj4 = srs.ExportToProj4()
        srs.MorphToESRI()
        self.srs_wkt = srs.ExportToWkt()
        self.minimum_elevation = float(minimum_elevation)
        self.maximum_elevation = float(maximum_elevation)

        del ds

    def _create_relief(self, fill_or_breach="fill", blc_dist=None, logger=None):
        """
        Create a relief file from the DEM using WBT using either fill or breach method.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(fill_or_breach={fill_or_breach}, blc_dist={blc_dist})"
            )
        if blc_dist is None:
            blc_dist = 1000

        relief_fn = self.relief

        remove_if_exists(relief_fn)

        if fill_or_breach == "fill":
            ret = self.wbt.fill_depressions(dem=self.dem, output=relief_fn)
        elif fill_or_breach == "breach":
            ret = self.wbt.breach_depressions(dem=self.dem, output=relief_fn)
        elif fill_or_breach == "breach_least_cost":
            ret = self.wbt.breach_depressions_least_cost(dem=self.dem, output=relief_fn, dist=int(blc_dist))
        else:
            raise ValueError("fill_or_breach must be either 'fill', 'breach' or 'breach_least_cost'")

        if not _exists(relief_fn):
            raise Exception(f"Relief file was not created: {relief_fn}, ret = {ret}")

        if self.verbose:
            print(f"Relief file created successfully: {relief_fn}")

    def _create_flow_vector(self, logger=None):
        """
        Create a flow vector file from the relief file using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        relief_fn = self.relief

        if not _exists(relief_fn):
            raise FileNotFoundError(f"Relief file does not exist: {relief_fn}")

        flovec_fn = self.flovec

        remove_if_exists(flovec_fn)

        self.wbt.d8_pointer(dem=relief_fn, output=flovec_fn, esri_pntr=False)

        if not _exists(flovec_fn):
            raise Exception(f"Flow vector file was not created: {flovec_fn}")

        if self.verbose:
            print(f"Flow vector file created successfully: {flovec_fn}")

    def _create_flow_accumulation(self, logger=None):
        """
        Create a flow accumulation file from the flow vector file using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        flovec_fn = self.flovec

        if not _exists(flovec_fn):
            raise FileNotFoundError(f"Flow vector file does not exist: {flovec_fn}")

        floaccum_fn = self.floaccum

        remove_if_exists(floaccum_fn)

        self.wbt.d8_flow_accumulation(
            i=flovec_fn,
            output=floaccum_fn,
            out_type="cells",
            log=False,
            clip=False,
            pntr=True,
            esri_pntr=False,
        )

        if not _exists(floaccum_fn):
            raise Exception(f"Flow accumulation file was not created: {floaccum_fn}")

        if self.verbose:
            print(f"Flow accumulation file created successfully: {floaccum_fn}")

    def _extract_streams(self, logger=None):
        """
        Extract streams from the flow accumulation file using WBT.

        csa:
            Channel Source Area threshold for stream extraction in ha

        mcl:
            Minimum Channel Length for stream extraction in m
        """

        if self.csa is None or self.mcl is None:
            raise ValueError("csa and mcl must be set before extracting streams")

        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(csa={self.csa}, mcl={self.mcl})"
            )

        floaccum_fn = self.floaccum

        if not _exists(floaccum_fn):
            raise FileNotFoundError(
                f"Flow accumulation file does not exist: {floaccum_fn}"
            )

        netful0_fn = self.netful0

        remove_if_exists(netful0_fn)

        threshold = self.csa * 10000.0  # Convert ha to m^2
        threshold = threshold / (self.cellsize * self.cellsize)

        self.wbt.extract_streams(floaccum_fn, netful0_fn, threshold=threshold)

        if not _exists(netful0_fn):
            raise Exception(f"Stream network file 0 was not created: {netful0_fn}")

        if self.verbose:
            print(f"Stream network file 0 created successfully: {netful0_fn}")

        netful_fn = self.netful
        remove_if_exists(netful_fn)
        self.wbt.remove_short_streams(
            d8_pntr=self.flovec,
            streams=netful0_fn,
            output=netful_fn,
            min_length=self.mcl,
            esri_pntr=False,
        )

    def _identify_stream_junctions(self, logger=None):
        """
        Identify stream junctions from the stream network file using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        netful_fn = self.netful

        if not _exists(netful_fn):
            raise FileNotFoundError(f"Stream network file does not exist: {netful_fn}")

        chnjnt_fn = self.chnjnt

        remove_if_exists(chnjnt_fn)

        self.wbt.stream_junction_identifier(
            d8_pntr=self.flovec, streams=self.netful, output=chnjnt_fn
        )

        if not _exists(chnjnt_fn):
            raise Exception(f"Stream junction file was not created: {chnjnt_fn}")

        if self.verbose:
            print(f"Stream junction file created successfully: {chnjnt_fn}")

    def delineate_channels(self, csa=5.0, mcl=60.0, fill_or_breach="fill", blc_dist=None, logger=None):
        """
        Delineate channels from the DEM using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(csa={csa}, mcl={mcl}, fill_or_breach={fill_or_breach}, blc_dist={blc_dist})"
            )
        self.mcl = mcl
        self.csa = csa

        self._create_relief(fill_or_breach, blc_dist=blc_dist, logger=logger)
        self._create_flow_vector(logger=logger)
        self._create_flow_accumulation(logger=logger)
        self._extract_streams(logger=logger)
        self._identify_stream_junctions(logger=logger)

        polygonize_netful(self.netful, self.netful_json)
        json_to_wgs(self.netful_json)

    def _make_outlet_geojson(self, dst=None, easting=None, northing=None, logger=None):
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(dst={dst}, easting={easting}, northing={northing})"
            )
        assert dst is not None

        assert isfloat(easting), easting
        assert isfloat(northing), northing

        with open(dst, "w") as fp:
            fp.write(
                _outlet_template_geojson.format(
                    epsg=self.epsg, easting=easting, northing=northing
                )
            )

        assert _exists(dst), dst
        return dst

    def _make_multiple_outlets_geojson(self, dst, en_points_dict, logger=None):
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            count = len(en_points_dict) if en_points_dict is not None else 0
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(dst={dst}, points={count})"
            )
        points = []
        for id, (easting, northing) in en_points_dict.items():
            points.append(
                _point_template_geojson.format(
                    id=id, easting=easting, northing=northing
                )
            )

        with open(dst, "w") as fp:
            fp.write(
                _multi_outlet_template_geojson.format(
                    epsg=self.epsg, points=",\n".join(points)
                )
            )

        assert _exists(dst), dst
        return dst

    def set_outlet(self, lng, lat, pixelcoords=False, logger=None):
        from wepppy.nodb.watershed import Outlet

        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(lng={lng}, lat={lat}, pixelcoords={pixelcoords})"
            )

        (x, y), distance = self.find_closest_channel2(
            lng, lat, pixelcoords=pixelcoords, logger=logger
        )
        _lng, _lat = self.pixel_to_lnglat(x, y, logger=logger)

        _e, _n = self.pixel_to_utm(x, y, logger=logger)
        self._make_outlet_geojson(
            easting=_e, northing=_n, dst=self.outlet_geojson, logger=logger
        )

        self._outlet = Outlet(
            requested_loc=(lng, lat),
            actual_loc=(_lng, _lat),
            distance_from_requested=distance,
            pixel_coords=(x, y),
        )

        return self._outlet

    def set_outlet_from_geojson(self, geojson_path=None, logger=None):
        """Populate ``self._outlet`` based on a GeoJSON file produced by ``find_outlet``.

        Parameters
        ----------
        geojson_path : str, optional
            Path to the GeoJSON file. Defaults to :attr:`outlet_geojson`.
        logger : logging.Logger, optional
            Logger used to record debug information.
        """

        from wepppy.nodb.watershed import Outlet

        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(geojson_path={geojson_path})"
            )

        path = geojson_path or self.outlet_geojson

        if not _exists(path):
            raise FileNotFoundError(f"Outlet GeoJSON not found: {path}")

        with open(path) as fp:
            data = json.load(fp)

        features = data.get("features") or []
        if not features:
            raise ValueError(f"Outlet GeoJSON contains no features: {path}")

        feature = features[0]
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if len(coords) < 2:
            raise ValueError(f"Outlet GeoJSON feature missing coordinates: {path}")

        easting, northing = coords[:2]

        properties = feature.get("properties") or {}
        col = properties.get("column")
        row = properties.get("row")

        if col is None or row is None:
            # column / row are 0-based indices in the GeoJSON
            # Fall back to computing them from the transform if missing.
            gt = self.transform
            det = gt[1] * gt[5] - gt[2] * gt[4]
            if det == 0:
                raise ValueError("Cannot derive pixel coordinates from GeoTransform")

            # Inverse affine transform.
            col = (gt[5] * (easting - gt[0]) - gt[2] * (northing - gt[3])) / det
            row = (gt[1] * (northing - gt[3]) - gt[4] * (easting - gt[0])) / det

        col = int(round(col))
        row = int(round(row))

        lat, lng = utm.to_latlon(
            easting=easting,
            northing=northing,
            zone_number=self.utm_zone,
            northern=self.hemisphere == "N",
        )
        lng, lat = float(lng), float(lat)

        outlet = Outlet(
            requested_loc=(lng, lat),
            actual_loc=(lng, lat),
            distance_from_requested=0.0,
            pixel_coords=(col, row),
        )

        self._outlet = outlet
        return outlet

    def find_closest_channel2(self, lng, lat, pixelcoords=False, logger=None):
        """
        Find the closest channel given a lng and lat or pixel coords (pixelcoords=True).

        Returns (x, y), distance
        where (x, y) are pixel coords and distance is the distance from the
        specified lng, lat in pixels.
        """

        # Unpack variables for instance

        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(lng={lng}, lat={lat}, pixelcoords={pixelcoords})"
            )

        chnjnt_fn = self.chnjnt

        with rasterio.open(chnjnt_fn) as src:
            junction_mask = src.read(1)

        num_cols, num_rows = self.num_cols, self.num_rows

        if pixelcoords:
            x, y = lng, lat
        else:
            x, y = self.lnglat_to_pixel(lng, lat, logger=logger)

        # Early return if the starting pixel is already a channel
        if junction_mask[y, x] == 1:
            return (x, y), 0

        # Spiral out from the starting point
        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]
        queue = deque([(x, y, 0)])
        visited = {(x, y)}

        while queue:
            cx, cy, dist = queue.popleft()

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy

                if (
                    0 <= nx < num_cols
                    and 0 <= ny < num_rows
                    and (nx, ny) not in visited
                ):
                    if junction_mask[ny, nx] == 1:
                        return (nx, ny), math.sqrt((nx - x) ** 2 + (ny - y) ** 2)
                    visited.add((nx, ny))
                    queue.append((nx, ny, dist + 1))

        return None, math.inf

    def lnglat_to_pixel(self, lng, lat, logger=None):
        """
        return the x,y pixel coords of lng, lat
        """

        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}(lng={lng}, lat={lat})")

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
        assert round(y) <= round(ul_y), (y, ul_y)

        # determine pixel coords
        _x = int(round((x - ul_x) / cellsize))
        _y = int(round((ul_y - y) / cellsize))

        # sanity check on the coords
        assert 0 <= _x < num_cols, f"{_x} not in range 0 to {num_cols}"
        assert 0 <= _y < num_rows, f"{_y} not in range 0 to {num_rows}"

        return _x, _y

    def pixel_to_utm(self, col, row, centre=True, logger=None):
        """
        Convert a raster (col,row) index to UTM easting / northing
        using the GeoTransform stored in ``self.transform``.

        Parameters
        ----------
        col, row : int
            Pixel indices (0-based).
        centre : bool, default True
            If True, returns the centre of the cell; if False, the
            upper-left (GDAL) corner.

        Returns
        -------
        (easting, northing) : tuple[float, float]
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                f"WhiteBoxToolsTopazEmulator.{func_name}(col={col}, row={row}, centre={centre})"
            )

        gt = self.transform  # (x0, dx, rx, y0, ry, dy)
        off = 0.5 if centre else 0.0  # shift to cell centre if requested

        easting = gt[0] + gt[1] * (col + off) + gt[2] * (row + off)
        northing = gt[3] + gt[4] * (col + off) + gt[5] * (row + off)
        return easting, northing

    def pixel_to_lnglat(self, x, y, logger=None):
        """
        return the lng/lat (WGS84) coords from pixel coords
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}(x={x}, y={y})")

        easting, northing = self.pixel_to_utm(x, y, logger=logger)
        lat, lng = utm.to_latlon(
            easting=easting,
            northing=northing,
            zone_number=self.utm_zone,
            northern=self.hemisphere == "N",
        )
        lng, lat = float(lng), float(lat)
        return lng, lat

    def _create_bound(self, logger=None):
        """
        Create a bound raster from the DEM using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        bound_fn = self.bound

        remove_if_exists(bound_fn)

        self.wbt.watershed(
            d8_pntr=self.flovec, pour_pts=self.outlet_geojson, output=self.bound
        )

        if not _exists(bound_fn):
            raise Exception(f"bound file was not created: {bound_fn}")

        if self.verbose:
            print(f"bound file created successfully: {bound_fn}")

        return bound_fn

    def _create_aspect(self, logger=None):
        """
        Create an aspect raster from the DEM using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        aspect_fn = self.aspect

        remove_if_exists(aspect_fn)

        self.wbt.aspect(dem=self.dem, output=aspect_fn)

        if not _exists(aspect_fn):
            raise Exception(f"Aspect file was not created: {aspect_fn}")

        if self.verbose:
            print(f"Aspect file created successfully: {aspect_fn}")

        return aspect_fn

    def _create_flow_vector_slope(self, logger=None):
        """
        Create a flow vector slope raster from the flow vector file using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        fvslop_fn = self.fvslop

        remove_if_exists(fvslop_fn)

        self.wbt.slope(dem=self.dem, output=fvslop_fn, units='ratio')

        if not _exists(fvslop_fn):
            raise Exception(f"Flow vector slope file was not created: {fvslop_fn}")

        if self.verbose:
            print(f"Flow vector slope file created successfully: {fvslop_fn}")

        return fvslop_fn

    def _create_netw0(self, logger=None):
        """
        Create a netw0 raster from the stream network and bound using WBT.
        This is the stream network masked to the watershed bound.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        netw0_fn = self.netw0

        remove_if_exists(netw0_fn)

        self.wbt.clip_raster_to_raster(i=self.netful, mask=self.bound, output=netw0_fn)

        if not _exists(netw0_fn):
            raise Exception(f"Netw0 file was not created: {netw0_fn}")

        if self.verbose:
            print(f"Netw0 file created successfully: {netw0_fn}")

        return netw0_fn

    def _create_distance_to_channel(self, logger=None):
        """
        Create a distance to channel raster from the stream network using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        discha_fn = self.discha

        remove_if_exists(discha_fn)

        self.wbt.downslope_distance_to_stream(
            dem=self.dem, streams=self.netw0, output=discha_fn
        )

        if not _exists(discha_fn):
            raise Exception(f"Distance to channel file was not created: {discha_fn}")

        if self.verbose:
            print(f"Distance to channel file created successfully: {discha_fn}")

        return discha_fn

    def _create_strahler_order(self, logger=None):
        """
        Create a Strahler order raster from the stream network using WBT.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        strahler_fn = self.strahler

        remove_if_exists(strahler_fn)

        self.wbt.strahler_stream_order(
            d8_pntr=self.flovec, streams=self.netw0, output=strahler_fn
        )

        if not _exists(strahler_fn):
            raise Exception(f"Strahler order file was not created: {strahler_fn}")

        if self.verbose:
            print(f"Strahler order file created successfully: {strahler_fn}")

        return strahler_fn

    def _create_subcatchments(self, logger=None):
        """
        Create subcatchments from the stream network.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")
        subwta_fn = self.subwta
        remove_if_exists(subwta_fn)

        self.wbt.hillslopes_topaz(
            dem=self.relief,
            d8_pntr=self.flovec,
            streams=self.netw0,
            pour_pts=self.outlet_geojson,
            watershed=self.bound,
            chnjnt=self.chnjnt,
            subwta=subwta_fn,
            order=self.strahler,
            netw=self.netw_tab,
        )

        if not _exists(subwta_fn):
            raise Exception(f"Subcatchments file was not created: {subwta_fn}")

        if self.verbose:
            print(f"Subcatchments file created successfully: {subwta_fn}")

        return subwta_fn

    @property
    def subwta_json(self):
        """
        Returns the path to the subcatchments file in JSON format.
        """
        return _join(self.wbt_wd, "subwta.geojson")

    @property
    def subcatchments_json(self):
        """
        Returns the path to the subcatchments file in WGS84 JSON format.
        """
        return _join(self.wbt_wd, "subcatchments.geojson")

    @property
    def subcatchments_wgs_json(self):
        """
        Returns the path to the subcatchments file in WGS84 JSON format.
        """
        return _join(self.wbt_wd, "subcatchments.WGS.geojson")
    
    @property
    def channels_json(self):
        """
        Returns the path to the channels file in JSON format.
        """
        return _join(self.wbt_wd, "channels.geojson")
    
    @property
    def channels_wgs_json(self):
        """
        Returns the path to the channels file in WGS84 JSON format.
        """
        return _join(self.wbt_wd, "channels.WGS.geojson")

    def delineate_subcatchments(self, logger=None):
        """
        Delineate subcatchments from the stream network and outlet.
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")

        self._create_bound(logger=logger)
        self._create_aspect(logger=logger)
        self._create_flow_vector_slope(logger=logger)
        self._create_netw0(logger=logger)
        self._create_strahler_order(logger=logger)
        self._create_distance_to_channel(logger=logger)
        self._create_subcatchments(logger=logger)
        polygonize_subcatchments(self.subwta, self.subwta_json, self.subcatchments_json)
        self._polygonize_channels(logger=logger)

    def _read_chn_order_from_netw_tab(self, logger=None):
        """
        returns a dictionary of topaz ids strings and their order
        """
        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")

        tbl = pd.read_table(self.netw_tab)

        # tbl columns: id	topaz_id	ds_x	ds_y	us_x	us_y	inflow0_id	inflow1_id	inflow2_id	length_m	ds_z	us_z	drop_m	order	areaup	is_headwater	is_outlet
        return dict(zip([str(v) for v in tbl["topaz_id"]], 
                        [int(v) for v in tbl["order"]]))

    def _polygonize_channels(self, logger=None):
        from wepppy.topo.watershed_abstraction import WeppTopTranslator

        if logger is not None:
            func_name = inspect.currentframe().f_code.co_name
            logger.info(f"WhiteBoxToolsTopazEmulator.{func_name}()")

        subwta_fn = self.subwta

        chn_order_dict = self._read_chn_order_from_netw_tab(logger=logger)

        assert _exists(subwta_fn)
        src_ds = gdal.Open(subwta_fn)
        srs = osr.SpatialReference()
        srs.ImportFromWkt(src_ds.GetProjectionRef())
        datum, utm_zone, hemisphere = get_utm_zone(srs)
        epsg = utm_srid(utm_zone, hemisphere == "N")
        srcband = src_ds.GetRasterBand(1)
        ids = set(
            [str(v) for v in np.array(srcband.ReadAsArray(), dtype=np.int32).flatten() if v > 0]
        )
        top_sub_ids = []
        top_chn_ids = []

        for id in ids:
            if id[-1] == "4":
                top_chn_ids.append(int(id))
            else:
                top_sub_ids.append(int(id))

        translator = WeppTopTranslator(top_chn_ids=top_chn_ids, top_sub_ids=top_sub_ids)

        subwta_json = self.subwta_json
        assert _exists(subwta_json), "polygonize SUBWTA first"

        # remove the TopazID = 0 feature defining a bounding box
        # and the channels
        with open(subwta_json) as fp:
            js = json.load(fp)

        if "crs" not in js:
            js["crs"] = {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:EPSG::%s" % epsg},
            }

        _features = []
        for f in js["features"]:
            topaz_id = str(f["properties"]["TopazID"])

            if topaz_id[-1] != "4":
                continue

            wepp_id = translator.wepp(top=topaz_id)
            f["properties"]["WeppID"] = wepp_id

            # get order from somewhere and add it to the properties
            f["properties"]["Order"] = chn_order_dict[str(topaz_id)]

            _features.append(f)

        js["features"] = _features

        dst_fn2 = self.channels_json
        with open(dst_fn2, "w") as fp:
            json.dump(js, fp, allow_nan=False)

        # create a version in WGS 1984 (lng/lat)
        json_to_wgs(dst_fn2)
        assert _exists(self.channels_wgs_json), "failed to create WGS84 channels JSON"


if __name__ == "__main__":

    dem = "/Users/roger/src/wepppy/tests/wbt/rlew-intercontinental-prawn/dem/dem.tif"
    wbt_wd = "/Users/roger/src/wepppy/tests/wbt/rlew-intercontinental-prawn/dem/wbt"
    # outlet = [-116.43008003513219, 45.93324289199021]
    outlet = [-120.16561014556784, 39.10885618748438]
    verbose = False
    csa = 4.0
    mcl = 60.0
    fill_or_breach = "breach"

    emulator = WhiteboxToolsTopazEmulator(dem, wbt_wd, verbose=verbose)
    emulator.delineate_channels(csa=csa, mcl=mcl, fill_or_breach=fill_or_breach)

    emulator.set_outlet(outlet[0], outlet[1], pixelcoords=False)
    print(
        f"Outlet set at: {emulator._outlet.actual_loc} with distance {emulator._outlet.distance_from_requested} pixels from requested location {emulator._outlet.requested_loc}"
    )

    emulator.delineate_subcatchments()

# Example usage:
# (wepppy310-env) roger@m4air32:/Users/roger/src/wepppy/wepppy/topo/wbt$ python3 wbt_topaz_emulator.py  /Users/roger/src/wepppy/tests/wbt/supine-disputant/dem/dem.tif /Users/roger/src/wepppy/tests/wbt/supine-disputant/dem/wbt --csa 10 --mcl 100 --verbose
