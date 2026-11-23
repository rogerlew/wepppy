"""Sample monthly E-OBS fields without interpolating missing observations."""

from math import floor, isfinite

import numpy as np
from osgeo import gdal, osr
from scipy.interpolate import RectBivariateSpline


# v19.0e preprocessing scaled the stored sentinel but left its metadata raw.
EOBS_LEGACY_NODATA = {
    'eu/e-obs/rr/mean': -999.9,
    'eu/e-obs/tn/mean': -99.99,
    'eu/e-obs/tx/mean': -99.99,
}


class EobsSampleError(ValueError):
    def __init__(self, code: str, month: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.month = month


def _pixel_location(dataset: gdal.Dataset, lng: float, lat: float) -> tuple[float, float]:
    target = dataset.GetSpatialRef()
    transform = dataset.GetGeoTransform(can_return_null=True)
    inverse = gdal.InvGeoTransform(transform) if transform is not None else None
    if target is None or inverse is None:
        raise RuntimeError('Invalid E-OBS raster georeferencing')

    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    east, north, _ = osr.CoordinateTransformation(source, target).TransformPoint(lng, lat)
    x, y = gdal.ApplyGeoTransform(inverse, east, north)
    return x, y


def _bilinear(
    data: np.ndarray, valid: np.ndarray, x: float, y: float, month: int,
) -> float:
    # Shift from pixel corners to sample centers. Coordinates are window-relative.
    center_x, center_y = x - 0.5, y - 0.5
    left, top = floor(center_x), floor(center_y)
    total = weight_sum = 0.0
    height, width = data.shape
    for row in range(max(0, top), min(height, top + 2)):
        for col in range(max(0, left), min(width, left + 2)):
            if valid[row, col]:
                weight = (1 - abs(center_x - col)) * (1 - abs(center_y - row))
                total += float(data[row, col]) * weight
                weight_sum += weight
    if weight_sum <= 0:
        raise EobsSampleError('eobs_coverage_unavailable', month)
    return total / weight_sum


def sample_eobs_monthly(fname: str, dataset_id: str, lng: float, lat: float) -> list[float]:
    """Use legacy cubic on valid stencils and masked bilinear at covered gaps."""
    dataset = gdal.Open(fname, gdal.GA_ReadOnly)
    if dataset is None or dataset.RasterCount != 12:
        raise RuntimeError('Expected twelve E-OBS monthly raster bands')

    x, y = _pixel_location(dataset, lng, lat)
    width, height = dataset.RasterXSize, dataset.RasterYSize
    if not (0 <= x < width and 0 <= y < height):
        raise EobsSampleError('eobs_coverage_unavailable')

    window_width, window_height = min(width, 5), min(height, 5)
    left = min(max(round(x) - 3, 0), width - window_width)
    top = min(max(round(y) - 3, 0), height - window_height)
    containing_col, containing_row = floor(x) - left, floor(y) - top
    legacy_nodata = EOBS_LEGACY_NODATA[dataset_id]
    rainfall = dataset_id == 'eu/e-obs/rr/mean'
    minimum_source_value = 0.0 if rainfall else -273.15

    result = []
    for month in range(1, 13):
        band = dataset.GetRasterBand(month)
        data = band.ReadAsArray(left, top, window_width, window_height)
        if data is None or data.shape != (window_height, window_width):
            raise RuntimeError(f'Cannot read E-OBS raster band {month}')

        valid = np.isfinite(data) & (data >= minimum_source_value)
        valid &= (data != -9999) & (data != legacy_nodata)
        nodata = band.GetNoDataValue()
        if nodata is not None:
            valid &= data != nodata
        if not valid[containing_row, containing_col]:
            raise EobsSampleError('eobs_coverage_unavailable', month)

        if data.shape == (5, 5) and valid.all():
            # Match the regular-grid FITPACK calculation used by interp2d.
            columns = np.arange(left, left + 5)
            rows = np.arange(top, top + 5)
            spline = RectBivariateSpline(columns, rows, data.T)
            value = float(spline(x, y)[0, 0])
        else:
            value = _bilinear(data, valid, x - left, y - top, month)
        if not isfinite(value) or (not rainfall and value < minimum_source_value):
            raise EobsSampleError('eobs_invalid_sample', month)
        result.append(value)
    return result
