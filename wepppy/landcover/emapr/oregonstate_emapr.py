"""Download utilities for the OSU eMapR biomass/canopy/vote datasets."""

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import utm
import subprocess
import os
from enum import IntEnum
from glob import glob
import math

import numpy as np
import rasterio

from wepppy.all_your_base.geo import read_raster

IS_WINDOWS = os.name == 'nt'

_thisdir = os.path.dirname(__file__)

DEFAULT_VERSION = 'v1'


OSUeMapR_Measures = (
    ('biomass', 'median'),
    ('biomass', 'stdv'),
    ('canopy',  'mean'),
    ('canopy',  'oob_rmse'),
    ('landcover', 'vote'),
    ('landcover', 'oob_rate')
)


def _parse_meta(fn):
    """Return (version, measure, statistic, year) extracted from ``fn``."""
    head, tail = _split(fn)
    tokens = tail.replace('_emapr_', '')\
                 .replace('oob_', 'oob-')\
                 .replace('.tif', '')\
                 .split('_')

    # version, measure, statistic, year = tokens
    assert len(tokens) == 4, tokens

    return tuple(t.replace('-', '_') for t in  tokens)


class OSUeMapR(object):
    """Manages local eMapR datasets cropped to a bounding box."""

    def __init__(self, wd='.', bbox=None, cellsize=30, version=DEFAULT_VERSION):
        """Initialize the downloader/cache with target directory and extent."""
        self.wd = wd
        if bbox is not None:
            bbox = [float(v) for v in bbox]

        self.bbox = bbox
        self.ds = {}
        self.cellsize = cellsize
        self.proj4 = None
        self.version = version

        emapr_fns = glob(_join(wd, f'_emapr_{version}*.tif'))
        for emapr_fn in emapr_fns:
            version, measure, statistic, year = _parse_meta(emapr_fn)
            self.ds[(measure, statistic, year)] = emapr_fn

    def retrieve(self, years, measures=None):
        """Download/crop the requested ``years``/``measures`` into ``self.wd``."""
        if measures is None:
            measures = OSUeMapR_Measures

        cellsize = self.cellsize
        bbox = [float(v) for v in self.bbox]
        version = self.version

        ul_x, ul_y, utm_number, utm_letter = utm.from_latlon(bbox[3], bbox[0])
        lr_x, lr_y, _, _ = utm.from_latlon(bbox[1], bbox[2], 
                                       force_zone_number=utm_number)
        proj4 = "+proj=utm +zone={zone} +{hemisphere} +datum=WGS84 +ellps=WGS84" \
            .format(zone=utm_number, hemisphere=('south', 'north')[bbox[3] > 0])

        for measure, statistic in measures:
            for year in years:
                dst_fn = _join(self.wd, f'_emapr_{version}_{measure}_{statistic}_{year}.tif')

                cmd = ['gdalwarp', 
                       '-co', 'compress=lzw', 
                       '-co', 'tiled=yes', 
                       '-co', 'bigtiff=yes',
                       '-t_srs', proj4,
                       '-te', str(ul_x), str(lr_y), str(lr_x), str(ul_y),
                       '-r', 'near',
                       '-tr', str(cellsize), str(cellsize),
                       f'/vsicurl/https://wepp.cloud/geodata/emapr/{version}/{measure}/{statistic}/{year}/.vrt',
                       dst_fn]

                if _exists(dst_fn):
                    os.remove(dst_fn)

                # run command, check_output returns standard output
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, errors = p.communicate(input=('0\n', '0\r\n')[IS_WINDOWS], timeout=15)

                if not _exists(dst_fn):
                    raise Exception((cmd, output, errors))

                self.ds[(measure, statistic, year)] = dst_fn

        self.proj4 = proj4
        self.ul_x, self.ul_y = ul_x, ul_y
        self.lr_x, self.lr_y = lr_x, lr_y

    def get_dataset(self, measure, statistic, year):
        """Return an ``OSUeMapR_Dataset`` representing the requested layer."""
        key = measure, statistic, year
        if key not in self.ds:
            self.retrieve([year], [(measure, statistic)])

        return OSUeMapR_Dataset(self.ds[key])

    def _attribution(self):
        """Copy the attribution README into the working directory if missing."""
        readme_txt = _join(self.wd, 'emapr_readme.txt')
        if not _exists(readme_txt):
            os.copyfile(_join(_thisdir, 'emapr_readme.txt', readme_txt))


class OSUeMapR_Dataset(object):
    """Thin wrapper around an eMapR GeoTIFF stacked product."""

    def __init__(self, fn):
        """Open ``fn`` with rasterio and parse its metadata tuple."""
        assert _exists(fn)

        self.version, self.measure, self.statistic, self.year = _parse_meta(fn)
        self.ds = rasterio.open(fn)    
        
    @property
    def shape(self):
        """Return the (rows, cols) shape of the raster."""
        return self.ds.read(1).T.shape

    def get_band(self):
        """Return the first band as a masked array, or None if not available."""
        try:
            data =  self.ds.read(1).T
        except IndexError:
            return None
        return np.ma.masked_values(data, 65535)

    def _get_median(self, indices):
        """Return the masked-median for the pixel subset ``indices``."""
        data = self.get_band()
        if data is None:
            return

        x = data[indices]

        retval = float(np.ma.median(x))
        if math.isnan(retval):
            return None

        return retval

    def spatial_aggregation(self, subwta_fn):
        """Aggregate median values per subcatchment ID stored in ``subwta_fn``."""
        assert _exists(subwta_fn)
        subwta, transform, proj = read_raster(subwta_fn, dtype=np.int32)
        assert self.shape == subwta.shape

        _ids = sorted(list(set(subwta.flatten())))

        domlc_d = {}
        for _id in _ids:
            if _id == 0:
                continue
            _id = int(_id)
            indices = np.where(subwta == _id)
            dom = self._get_median(indices)

            domlc_d[str(_id)] = dom
        return domlc_d

    def spatial_stats(self, bound_fn):
        """Return stats (count, mean, std) for pixels within ``bound_fn`` mask."""
        assert _exists(bound_fn)
        bounds, transform, proj = read_raster(bound_fn, dtype=np.int32)
        indices = np.where(bounds == 1)

        data = self.get_band()
        if data is None:
            return  

        x = data[indices]

        return dict(num_pixels=len(indices[0]),
                    valid_pixels=len(indices[0]) - np.sum(x.mask),
                    mean=np.mean(x),
                    std=np.std(x),
                    units='%')


if __name__ == "__main__":
    bbox = [-114.63661319270066,45.41139471986449,-114.60663682475024,45.43207316134328]
    rap = RangelandAnalysisPlatformV2(wd='test', bbox=bbox)
    rap_ds = rap.get_dataset(2020)
    litter = rap_ds.get_band(RAP_Band.LITTER)
    print(litter)
     

    rap = RangelandAnalysisPlatformV3(wd='test', bbox=bbox)
    rap_ds = rap.get_dataset(2020)
    litter = rap_ds.get_band(RAP_Band.LITTER)
    print(litter)
     
