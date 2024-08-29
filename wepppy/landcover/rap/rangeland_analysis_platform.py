from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
import utm
import subprocess
import os
from enum import IntEnum
from glob import glob
import math

from collections import Counter

import numpy as np
import rasterio
from osgeo import gdal

from wepppy.all_your_base.geo import read_raster

IS_WINDOWS = os.name == 'nt'

_thisdir = os.path.dirname(__file__)

DEFAULT_VERSION = 'v3'


class RangelandAnalysisPlatform(object):
    def __init__(self, wd='.', bbox=None, cellsize=30, version=DEFAULT_VERSION):
        self.wd = wd
        if bbox is not None:
            bbox = [float(v) for v in  bbox]

        self.bbox = bbox

        self.ds = {}
        self.cellsize = cellsize
        self.proj4 = None
        self.version = version

        rap_fns = glob(_join(wd, f'_rap_{version}*.tif'))
        for rap_fn in rap_fns:
            head, tail = _split(rap_fn)
            year = int(tail.replace(f'_rap_{version}_', '').replace('.tif', ''))
            self.ds[year] = rap_fn

    def retrieve(self, years):
        cellsize = self.cellsize
        bbox = self.bbox
        version = self.version

        ul_x, ul_y, utm_number, utm_letter = utm.from_latlon(bbox[3], bbox[0])
        lr_x, lr_y, _, _ = utm.from_latlon(bbox[1], bbox[2],
                                           force_zone_number=utm_number)
        proj4 = "+proj=utm +zone={zone} +{hemisphere} +datum=WGS84 +ellps=WGS84" \
            .format(zone=utm_number, hemisphere=('south', 'north')[bbox[3] > 0])

        for year in years:
            year = str(year)
            dst_fn = _join(self.wd, f'_rap_{version}_{year}.tif')
            max_retries = 3
            retries = 0
            success = False

            while retries < max_retries and not success:
                cmd = ['gdalwarp',
                       '-co', 'compress=lzw',
                       '-co', 'tiled=yes',
                       '-co', 'bigtiff=yes',
                       '-t_srs', proj4,
                       '-te', str(ul_x), str(lr_y), str(lr_x), str(ul_y),
                       '-r', 'near',
                       '-tr', str(cellsize), str(cellsize),
                       f'/vsicurl/http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-cover/{version}/vegetation-cover-{version}-{year}.tif',
                       dst_fn]

                if _exists(dst_fn):
                    os.remove(dst_fn)

                # Run command
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, errors = p.communicate(input=('0\n', '0\r\n')[IS_WINDOWS], timeout=15)

                if _exists(dst_fn) and self.validate_raster(dst_fn):
                    success = True
                else:
                    retries += 1
                    print(f"Validation failed for year {year}, retrying... ({retries}/{max_retries})")

                if retries == max_retries and not success:
                    raise Exception(f"Failed to retrieve valid data for year {year} after {max_retries} retries.")

            self.ds[year] = dst_fn

        self.proj4 = proj4
        self.ul_x, self.ul_y = float(ul_x), float(ul_y)
        self.lr_x, self.lr_y = float(lr_x), float(lr_y)

        return retries
        
    def validate_raster(self, filename):
        """
        Validates if the raster file contains non-zero, non-masked data.
        
        :param filename: Path to the raster file.
        :return: True if the raster contains valid data, False otherwise.
        """
        try:
            dataset = gdal.Open(filename, gdal.GA_ReadOnly)
            if not dataset:
                return False
            
            band = dataset.GetRasterBand(1)
            if not band:
                return False
            
            # Read the data as a NumPy array
            data = band.ReadAsArray()
            
            # Check if there are any non-zero, non-masked values
            if np.any(data):
                return True
            else:
                return False
        except Exception as e:
            print(f"Error validating raster {filename}: {e}")
            return False
        finally:
            if dataset:
                dataset = None

    def get_dataset_fn(self, year):
        year = str(year)
        if year not in self.ds:
            self.retrieve([year])

        return self.ds[year]

    def get_dataset(self, year):
        fn = self.get_dataset_fn(year)
        return RangelandAnalysisPlatformDataset(fn)

    def _attribution(self):
        readme_txt = _join(self.wd, 'rap_readme.txt')
        if not _exists(readme_txt):
            os.copyfile(_join(_thisdir, 'rap_readme.txt', readme_txt))


class RangelandAnalysisPlatformV2(RangelandAnalysisPlatform):
    def __init__(self, wd='.', bbox=None, cellsize=30):
        super(RangelandAnalysisPlatformV2, self).__init__(wd=wd, bbox=bbox, cellsize=cellsize, version='v2')


class RangelandAnalysisPlatformV3(RangelandAnalysisPlatform):
    def __init__(self, wd='.', bbox=None, cellsize=30):
        super(RangelandAnalysisPlatformV3, self).__init__(wd=wd, bbox=bbox, cellsize=cellsize, version='v3')


class RAP_Band(IntEnum):
    ANNUAL_FORB_AND_GRASS = 1
    BARE_GROUND = 2
    LITTER = 3
    PERENNIAL_FORB_AND_GRASS = 4
    SHRUB = 5
    TREE = 6
    ANNUAL_FORB_AND_GRASS_UNCERTAINTY = 7
    BARE_GROUND_UNCERTAINTY = 8
    LITTER_UNCERTAINTY = 9
    PERRENIAL_FORB_AND_GRASS_UNCERTAINTY = 10
    SHRUB_UNCERTAINTY = 11
    TREE_UNCERTAINTY = 12


class RangelandAnalysisPlatformDataset(object):
    def __init__(self, fn):
        self.ds = rasterio.open(fn)

    @property
    def shape(self):
        return self.ds.read(RAP_Band.TREE).T.shape

    def get_band(self, band: RAP_Band):
        try:
            data =  self.ds.read(band).T
        except IndexError:
            return None
        return np.ma.masked_values(data, 65535)

    def spatial_stats(self, band: RAP_Band, bound_fn):
        assert _exists(bound_fn)
        bounds, transform, proj = read_raster(bound_fn, dtype=np.int32)
        indices = np.where(bounds == 1)

        data = self.get_band(band)
        if data is None:
            return

        x = data[indices]

        return dict(num_pixels=len(indices[0]),
                    valid_pixels=len(indices[0]) - np.sum(x.mask),
                    mean=np.mean(x),
                    std=np.std(x),
                    units='%')

RangelandAnalysisPlatformV2Dataset = RangelandAnalysisPlatformDataset
RangelandAnalysisPlatformV3Dataset = RangelandAnalysisPlatformDataset


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


