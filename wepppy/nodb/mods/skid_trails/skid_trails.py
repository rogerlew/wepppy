# non-standard

# wepppy

# wepppy submodules
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase

from wepppy.all_your_base.geo import read_raster, get_utm_zone, utm_srid

#import cv2

# standard library
import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split
from subprocess import Popen, PIPE
import shutil

import rasterio
from rasterio import features
import geopandas as gpd

import json
# non-standard
import jsonpickle

from operator import itemgetter
from osgeo import gdal, osr

from wepppy.all_your_base import NumpyEncoder
from wepppy.all_your_base.geo import GeoTransformer

import numpy as np

class skid_trailsNoDbLockedException(Exception):
    pass


def convert_to_geojson(skidtrails):
    # Start with an empty FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # Convert each trail to a LineString feature
    for i, trail in enumerate(skidtrails):
        # Extract the coordinates for the LineString
        coordinates = [point['wgs'] for point in trail]

        # Create a LineString feature for this trail
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties":
                {"ID": i,
                 "start_px": trail[0]["indx"],
                 "end_px": trail[-1]["indx"],
                 "n": len(trail),
                 "start_z": trail[0]["elevation"],
                 "end_z": trail[-1]["elevation"],
                 }
        }

        # Add the feature to the collection
        geojson["features"].append(feature)

    return json.dumps(geojson, indent=4, cls=NumpyEncoder)

def unmasked_neighbors(a, indx, subwta, _transform, geo_transformer, channels):
    """
    looks at neibers of a[indx] and identifies the neighbors that are skid trials. Returns the unmasked neighbores in
     descending elevation
    :param a:
    :param indx:
    :param subwta:
    :param _transform:
    :param geo_transformer:
    :param channels:
    :return:
    """

    px, py = indx
    mask = a.mask
    w, h = mask.shape

    _unmasked = []

    # west
    if px > 0:
        if not mask[px - 1, py]:
            _unmasked.append(dict(direction='west', indx=(px - 1, py)))
    # east
    if px < w - 1:
        if not mask[px + 1, py]:
            _unmasked.append(dict(direction='east', indx=(px + 1, py)))

    # north
    if py > 0:
        if not mask[px, py - 1]:
            _unmasked.append(dict(direction='north', indx=(px, py - 1)))

    # south
    if py < h - 1:
        if not mask[px, py + 1]:
            _unmasked.append(dict(direction='south', indx=(px, py + 1)))

    # northwest
    if px > 0 and py > 0:
        if not mask[px - 1, py - 1]:
            _unmasked.append(dict(direction='northwest', indx=(px - 1, py - 1)))

    # southeast
    if px < w - 1 and py < h - 1:
        if not mask[px + 1, py + 1]:
            _unmasked.append(dict(direction='southeast', indx=(px + 1, py + 1)))

    # northeast
    if px < w - 1 and py > 0:
        if not mask[px + 1, py - 1]:
            _unmasked.append(dict(direction='northeast', indx=(px + 1, py - 1)))

    # southwest
    if px > 0 and py < h - 1:
        if not mask[px - 1, py + 1]:
            _unmasked.append(dict(direction='southwest', indx=(px - 1, py + 1)))

    for i in range(len(_unmasked)):
        px, py = _unmasked[i]['indx']
        _unmasked[i].update(dict(elevation=a[px, py],
                                 wgs=geo_transformer.transform(_transform[0] + _transform[1] * px,
                                                               _transform[3] + _transform[5] * py),
                                 is_channel=channels[px, py] == 1,
                                 topaz_id=subwta[px, py]))

    return sorted(_unmasked, key=itemgetter('elevation'), reverse=True)


def n_neighbors(a, indx):
    px, py = indx
    mask = a.mask
    w, h = mask.shape

    if px > 0:
        px0 = px - 1
    else:
        px0 = px

    if px < w - 1:
        pxend = px + 1
    else:
        pxend = w - 2

    if py > 0:
        py0 = py - 1
    else:
        py0 = py

    if py < h - 1:
        pyend = py + 1
    else:
        pyend = h - 2

    return np.sum(np.logical_not(a.mask[px0:pxend, py0:pyend]))


class SkidTrails(NoDbBase, LogMixin):
    __name__ = 'skid_trails'

    def __init__(self, wd, cfg_fn):
        super(SkidTrails, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            skid_trails_dir = self.skid_trails_dir
            if not _exists(skid_trails_dir):
                os.mkdir(skid_trails_dir)

            _skid_trails_map = self.config_get_path('skid_trails', 'skid_trails_map')

            if _skid_trails_map is not None:
                if _skid_trails_map.startswith('static/'):

                    from wepppy.weppcloud.app import _thisdir
                    _skid_trails_map = _join(_thisdir, _skid_trails_map)

                assert _exists(_skid_trails_map), _skid_trails_map
                _, _fn = _split(_skid_trails_map)
                shutil.copyfile(_skid_trails_map, _join(skid_trails_dir , _fn))
                self._skid_trial_fn = _fn

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def skid_trails_path(self):
        if self._skid_trial_fn is None:
            return None

        return _join(self.skid_trails_dir, self._skid_trial_fn)

    @property
    def skid_trails_raster(self):
        return _join(self.skid_trails_dir, 'skid.tif')

    def rasterize_skid_trails(self):
        from wepppy.nodb import Watershed
        watershed = Watershed.getInstance(self.wd)

        # Load the DEM and the skid trails
        with rasterio.open(watershed.dem_fn) as dem:
            dem_meta = dem.meta

        # Read skid trails shapefile using GeoPandas
        skid_trails = gpd.read_file(self.skid_trails_path)

        # Check if both CRS are same if not reproject
        if skid_trails.crs != dem_meta['crs']:
            skid_trails = skid_trails.to_crs(dem_meta['crs'])

        # Create a empty numpy array of same shape as DEM
        skid_trails_raster = np.zeros((dem_meta['height'], dem_meta['width']), dtype=rasterio.uint8)

        # Rasterize the shapefile
        skid_trails_raster = features.rasterize(skid_trails.geometry,
                                                out=skid_trails_raster,
                                                transform=dem_meta['transform'],
                                                fill=0,
                                                all_touched=True,
                                                dtype=rasterio.uint8)

        # Write the new raster to disk
        with rasterio.open(self.skid_trails_raster, 'w', **dem_meta) as dst:
            dst.write(skid_trails_raster, 1)

        assert _exists(self.skid_trails_raster)

    def walk_skid_trails(self):

        from wepppy.nodb import Watershed
        wd = self.wd

        watershed = Watershed.getInstance(wd)

        # read the bounds geotiff (0 outside of sub-basin, 1 inside of sub-basin)
        bound, _transform, _proj = read_raster(watershed.bound)

        # read the channels map
        channels,  _transform, _proj = read_raster(watershed.netful)

        # read the subcatchments map
        subwta,  _transform, _proj = read_raster(watershed.subwta)

        # read the rasterized skid_trials map. 0 outside of skid trails, 1 on skid trails
        skid, _transform, _proj = read_raster(self.skid_trails_raster)

        # set skid pixels outside of sub-basin to 0
        skid[np.where(bound == 0)] = 0

        # read in the dem
        dem, _transform, _proj = read_raster(watershed.dem_fn)
        dem[np.where(bound == 0)] = 0

        geo_transformer = GeoTransformer(src_proj4=_proj, dst_epsg=4326)

        # mask the dem with the skid trails
        a = np.ma.masked_array(dem, mask=np.logical_not(skid))

        skidtrails = []
        while np.prod(a.shape) > np.sum(a.mask):
            trail = []

            # find origin

            # find all the end points
            indxs = np.where(np.logical_not(a.mask))
            end_points = []
            for px, py in zip(*indxs):
                len_unmasked = n_neighbors(a, (px, py))
                if len_unmasked == 1:  # found all end points
                    end_points.append(
                        dict(indx=(px, py),
                             elevation=a[px, py]))

            # origin is the highest elevation
            origin = sorted(end_points, key=itemgetter('elevation'), reverse=True)

            if len(origin) > 0:
                origin = origin[0]
            else:
                break

            max_elev = origin['elevation']
            px, py = indx = origin['indx'] # the highest endpoint
            a.mask[indx] = True # mask the origin pixel

            # add the origin to the trail
            trail.append(dict(direction='origin', indx=indx, elevation=max_elev,
                              wgs=geo_transformer.transform(_transform[0] + _transform[1] * px,
                                                            _transform[3] + _transform[5] * py),
                              is_channel=channels[px, py] == 1))

            # walk down the trail
            stop = False
            while not stop:
                # find unmasked neighbors
                _unmasked = unmasked_neighbors(a, indx, subwta, _transform, geo_transformer, channels)
                len_unmasked = len(_unmasked)

                # no neighbors are skid trails
                if len_unmasked == 0:
                    print('s', _unmasked, len_unmasked, np.prod(a.shape), np.sum(a.mask))
                    stop = True
                    a.mask[indx] = True

                # one neighbor is skid trail
                elif len_unmasked == 1:
                    trail.append(_unmasked[0])
                    print(trail[-1])

                    # pop skid pixel
                    indx = _unmasked[0]['indx']
                    a.mask[indx] = True

                elif len_unmasked > 1:
                    print('s', _unmasked, len_unmasked, np.prod(a.shape), np.sum(a.mask))
                    trail.append(_unmasked[0])

                    # pop skid pixel with highest elevation
                    indx = _unmasked[0]['indx']
                    a.mask[indx] = True
                    stop = True

            print(trail)
            skidtrails.append(trail)

        js = convert_to_geojson(self.skidtrails)
        with open(_join(self.skid_trails_dir, 'skid_trails0.geojson'), 'w') as fp:
            fp.write(js)

        self.lock()

        try:
            self.skidtrails = skidtrails
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def skid_trails_dir(self):
        return _join(self.wd, 'skid_trails')

    def clean(self):
        skid_trails_dir = self.skid_trails_dirinterpolate_slp

        if _exists(skid_trails_dir):
            shutil.rmtree(skid_trails_dir, ignore_errors=True)

        os.mkdir(skid_trails_dir)


    @property
    def runs_dir(self):
        return _join(self.wd, 'skid_trails', 'runs')

    @property
    def output_dir(self):
        return _join(self.wd, 'skid_trails', 'output')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.runs_dir, 'status.log'))

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        with open(_join(wd, 'skid_trails.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, SkidTrails)

        if _exists(_join(wd, 'READONLY')):
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            if not db.islocked():
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return SkidTrails.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)
    
    @property
    def _nodb(self):
        return _join(self.wd, 'skid_trails.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'skid_trails.nodb.lock')
