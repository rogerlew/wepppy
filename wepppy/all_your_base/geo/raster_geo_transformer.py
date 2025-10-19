"""Raster projection helpers for datasets stored in UTM."""

from __future__ import annotations

from os.path import exists as _exists
from typing import Tuple, Union

import numpy as np
from numpy.typing import ArrayLike, NDArray
from osgeo import gdal, osr
import utm

from ..all_your_base import isfloat
from .geo import get_utm_zone, utm_srid

__all__ = ['UtmGeoTransformer']

gdal.UseExceptions()


class UtmGeoTransformer:
    """Utility for translating between pixel, UTM, and WGS84 coordinates."""

    def __init__(self, raster_fn: str) -> None:
        if not _exists(raster_fn):
            raise FileNotFoundError(f'raster_fn "{raster_fn}" does not exist')

        dataset = gdal.Open(raster_fn)
        if dataset is None:
            raise RuntimeError(f'Unable to open {raster_fn}')

        num_cols = dataset.RasterXSize
        num_rows = dataset.RasterYSize
        if num_cols <= 0 or num_rows <= 0:
            raise ValueError('input raster is empty')

        transform = dataset.GetGeoTransform()
        if abs(transform[1]) != abs(transform[5]):
            raise ValueError('input cells must be square')

        cellsize = abs(transform[1])
        ul_x = int(round(transform[0]))
        ul_y = int(round(transform[3]))
        lr_x = ul_x + cellsize * num_cols
        lr_y = ul_y - cellsize * num_rows

        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromWkt(dataset.GetProjectionRef())
        datum, utm_zone, hemisphere = get_utm_zone(spatial_ref)
        if utm_zone is None:
            raise ValueError('input raster is not in a UTM projection')

        band = dataset.GetRasterBand(1)
        dtype = gdal.GetDataTypeName(band.DataType)
        stats = band.GetStatistics(True, True)
        min_value, max_value = stats[0], stats[1]

        self.raster_fn = raster_fn
        self.transform = transform
        self.num_cols = num_cols
        self.num_rows = num_rows
        self.cellsize = cellsize
        self.ul_x = ul_x
        self.ul_y = ul_y
        self.lr_x = lr_x
        self.lr_y = lr_y
        self.ll_x = ul_x
        self.ll_y = int(lr_y)
        self.dtype = dtype
        self.datum = datum
        self.hemisphere = hemisphere
        self.northern = hemisphere == 'N'
        self.utm_zone = utm_zone
        self.epsg = utm_srid(utm_zone, hemisphere)
        self.srs_proj4 = spatial_ref.ExportToProj4()

        wgs_lr_y, wgs_ul_x = utm.to_latlon(
            easting=ul_x,
            northing=lr_y,
            zone_number=utm_zone,
            northern=self.northern,
        )
        wgs_ul_y, wgs_lr_x = utm.to_latlon(
            easting=lr_x,
            northing=ul_y,
            zone_number=utm_zone,
            northern=self.northern,
        )
        self.extent = wgs_ul_x, wgs_lr_y, wgs_lr_x, wgs_ul_y

        spatial_ref.MorphToESRI()
        self.srs_wkt = spatial_ref.ExportToWkt()
        self.min_value = min_value
        self.max_value = max_value

        del dataset

    def utm_to_px(
        self,
        easting: Union[float, ArrayLike],
        northing: Union[float, ArrayLike],
    ) -> Tuple[Union[int, NDArray[np.int_]], Union[int, NDArray[np.int_]]]:
        """Convert UTM coordinates into pixel indices."""
        cellsize = self.cellsize
        ul_x, ul_y = self.ul_x, self.ul_y

        if isfloat(easting):
            x = int(round((float(easting) - ul_x) / cellsize))
            y = int(round((float(northing) - ul_y) / -cellsize))
            if not (0 <= x < self.num_cols and 0 <= y < self.num_rows):
                raise ValueError('pixel indices fall outside raster bounds')
        else:
            x = np.array(
                np.round((np.asarray(easting, dtype=float) - ul_x) / cellsize),
                dtype=np.int_,
            )
            y = np.array(
                np.round((np.asarray(northing, dtype=float) - ul_y) / -cellsize),
                dtype=np.int_,
            )
        return x, y

    def lnglat_to_px(self, lng: float, lat: float) -> Tuple[int, int]:
        """Return the pixel indices for a WGS84 coordinate."""
        easting, northing, _, _ = utm.from_latlon(lat, lng, self.utm_zone)
        x = int(round((easting - self.ul_x) / self.cellsize))
        y = int(round((self.ul_y - northing) / self.cellsize))
        if not (0 <= x < self.num_cols and 0 <= y < self.num_rows):
            raise ValueError('pixel indices fall outside raster bounds')
        return x, y

    def px_to_utm(self, x: int, y: int) -> Tuple[float, float]:
        """Convert pixel indices into UTM coordinates."""
        if not (0 <= x < self.num_cols):
            raise ValueError('x index out of bounds')
        if not (0 <= y < self.num_rows):
            raise ValueError('y index out of bounds')
        easting = self.ul_x + self.cellsize * x
        northing = self.ul_y - self.cellsize * y
        return float(easting), float(northing)

    def lnglat_to_utm(self, lng: float, lat: float) -> Tuple[float, float]:
        """Convert WGS84 coordinates into UTM."""
        easting, northing, _, _ = utm.from_latlon(
            latitude=lat,
            longitude=lng,
            force_zone_number=self.utm_zone,
        )
        return float(easting), float(northing)

    def px_to_lnglat(self, x: int, y: int) -> Tuple[float, float]:
        """Convert pixel indices into WGS84 coordinates."""
        easting, northing = self.px_to_utm(x, y)
        lat, lng, _, _ = utm.to_latlon(
            easting=easting,
            northing=northing,
            zone_number=self.utm_zone,
            northern=self.northern,
        )
        return float(lng), float(lat)
