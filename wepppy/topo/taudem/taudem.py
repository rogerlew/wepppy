
import os
import shutil
import subprocess
import inspect
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from osgeo import gdal, osr
import utm

import warnings

import numpy as np

from wepppy.all_your_base import (
    isfloat,
    NCPU
)

from wepppy.all_your_base.geo import read_tif, utm_srid, GeoTransformer, wgs84_proj4, get_utm_zone

_USE_MPI = True
_DEBUG = False

if NCPU > 4:
    NCPU = 4

# This also assumes that MPICH2 is properly installed on your machine and that TauDEM command line executables exist
# MPICH2.  Obtain from http://www.mcs.anl.gov/research/projects/mpich2/
# Install following instructions at http://hydrology.usu.edu/taudem/taudem5.0/downloads.html.
# It is important that you install this from THE ADMINISTRATOR ACCOUNT.

# TauDEM command line executables.

_thisdir = os.path.dirname(__file__)
_taudem_bin = _join(_thisdir, 'bin/linux/20201107/')


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


class TauDEMRunner:
    """
    Object oriented abstraction for running TauDEM

    For more infomation on taudem see the manual available here:
        https://hydrology.usu.edu/taudem/taudem5/documentation.html
    """
    def __init__(self, wd, dem, vector_ext='geojson'):
        """
        provide a path to a directory to store the taudem files a
        path to a dem
        """

        # verify the dem exists
        if not _exists(wd):
            raise Exception('working directory "%s" does not exist' % wd)

        self.wd = wd

        # verify the dem exists
        if not _exists(dem):
            raise Exception('file "%s" does not exist' % dem)

        self._dem_ext = _split(dem)[-1].split('.')[-1]
        shutil.copyfile(dem, self._z)

        self._vector_ext = vector_ext

        self.user_outlet = None
        self.outlet = None
        self._scratch = {}
        self._parse_dem()

    def _parse_dem(self):
        """
        reads metadata from the dem to get the projection, transform, bounds, resolution, and size
        """
        dem = self._z

        # open the dataset
        ds = gdal.Open(dem)

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

    def data_fetcher(self, band, dtype=None):
        if dtype is None:
            dtype = np.int16

        if band not in self._scratch:
            _band = getattr(self, '_' + band)
            self._scratch[band], _, _ = read_tif(_band, dtype=dtype)

        data = self._scratch[band]
        assert data.shape == (self.num_cols, self.num_rows), (data.shape, self.num_cols, self.num_rows)
        return data

    def get_elevation(self, easting, northing):
        z_data = self.data_fetcher('z', dtype=np.float64)
        x, y = self.utm_to_px(easting, northing)

        return z_data[x, y]

    def utm_to_px(self, easting, northing):
        """
        return the utm coords from pixel coords
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        if isfloat(easting):
            x = int(round((easting - ul_x) / cellsize))
            y = int(round((northing - ul_y) / -cellsize))

            assert 0 <= y < num_rows, (y, (num_rows, num_cols))
            assert 0 <= x < num_cols, (x, (num_rows, num_cols))
        else:
            x = np.array(np.round((np.array(easting) - ul_x) / cellsize), dtype=np.int64)
            y = np.array(np.round((np.array(northing) - ul_y) / -cellsize), dtype=np.int64)

        return x, y

    def lnglat_to_px(self, long, lat):
        """
        return the x,y pixel coords of long, lat
        """

        # unpack variables for instance
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows
        ul_x, ul_y, lr_x, lr_y = self.ul_x, self.ul_y, self.lr_x, self.lr_y

        # find easting and northing
        x, y, _, _ = utm.from_latlon(lat, long, self.utm_zone)

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

    def px_to_utm(self, x, y):
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

    def lnglat_to_utm(self, long, lat):
        """
        return the utm coords from lnglat coords
        """
        wgs2proj_transformer = GeoTransformer(src_proj4=wgs84_proj4, dst_proj4=self.srs_proj4)
        return wgs2proj_transformer.transform(long, lat)

    def px_to_lnglat(self, x, y):
        """
        return the long/lat (WGS84) coords from pixel coords
        """
        easting, northing = self.px_to_utm(x, y)
        proj2wgs_transformer = GeoTransformer(src_proj4=self.srs_proj4, dst_proj4=wgs84_proj4)
        return proj2wgs_transformer.transform(easting, northing)

    # dem
    @property
    def _z(self):
        return _join(self.wd, 'dem.%s' % self._dem_ext)

    @property
    def _z_args(self):
        return ['-z', self._z]

    # fel
    @property
    def _fel(self):
        return _join(self.wd, 'fel.tif')

    @property
    def _fel_args(self):
        return ['-fel', self._fel]

    # point
    @property
    def _fd8(self):
        return _join(self.wd, 'd8_flow.tif')

    @property
    def _fd8_args(self):
        return ['-p', self._fd8]

    _p_args = _fd8_args

    # slope d8
    @property
    def _sd8(self):
        return _join(self.wd, 'd8_slope.tif')

    @property
    def _sd8_args(self):
        return ['-sd8', self._sd8]

    # area d8
    @property
    def _ad8(self):
        return _join(self.wd, 'd8_area.tif')

    @property
    def _ad8_args(self):
        return ['-ad8', self._ad8]

    # stream raster
    @property
    def _src(self):
        return _join(self.wd, 'src.tif')

    @property
    def _src_args(self):
        return ['-src', self._src]

    # pk stream reaster
    @property
    def _pksrc(self):
        return _join(self.wd, 'pksrc.tif')

    @property
    def _pksrc_args(self):
        return ['-src', self._pksrc]

    # net
    @property
    def _net(self):
        return _join(self.wd, 'net.%s' % self._vector_ext)

    @property
    def _net_args(self):
        return ['-net', self._net]

    # user outlet
    @property
    def _uo(self):
        return _join(self.wd, 'user_outlet.%s' % self._vector_ext)

    @property
    def _uo_args(self):
        return ['-o', self._uo]

    # outlet
    @property
    def _o(self):
        return _join(self.wd, 'outlet.%s' % self._vector_ext)

    @property
    def _o_args(self):
        return ['-o', self._o]

    # stream source
    @property
    def _ss(self):
        return _join(self.wd, 'ss.tif')

    @property
    def _ss_args(self):
        return ['-ss', self._ss]

    # ssa
    @property
    def _ssa(self):
        return _join(self.wd, 'ssa.tif')

    @property
    def _ssa_args(self):
        return ['-ssa', self._ssa]

    # drop
    @property
    def _drp(self):
        return _join(self.wd, 'drp.csv')

    @property
    def _drp_args(self):
        return ['-drp', self._drp]

    # tree
    @property
    def _tree(self):
        return _join(self.wd, 'tree.tsv')

    @property
    def _tree_args(self):
        return ['-tree', self._tree]

    # coord
    @property
    def _coord(self):
        return _join(self.wd, 'coord.tsv')

    @property
    def _coord_args(self):
        return ['-coord', self._coord]

    # order
    @property
    def _ord(self):
        return _join(self.wd, 'order.tif')

    @property
    def _ord_args(self):
        return ['-ord', self._ord]

    # watershed
    @property
    def _w(self):
        return _join(self.wd, 'watershed.tif')

    @property
    def _w_args(self):
        return ['-w', self._w]

    # gord
    @property
    def _gord(self):
        return _join(self.wd, 'gord.tif')

    @property
    def _gord_args(self):
        return ['-gord', self._gord]

    # plen
    @property
    def _plen(self):
        return _join(self.wd, 'plen.tif')

    @property
    def _plen_args(self):
        return ['-plen', self._plen]

    # tlen
    @property
    def _tlen(self):
        return _join(self.wd, 'tlen.tif')

    @property
    def _tlen_args(self):
        return ['-tlen', self._tlen]

    # dinf angle
    @property
    def _dinf_angle(self):
        return _join(self.wd, 'dinf_angle.tif')

    @property
    def _dinf_angle_args(self):
        return ['-ang', self._dinf_angle]

    # dinf slope
    @property
    def _dinf_slope(self):
        return _join(self.wd, 'dinf_slope.tif')

    @property
    def _dinf_slope_args(self):
        return ['-slp', self._dinf_slope]

    # dinf contributing area
    @property
    def _dinf_sca(self):
        return _join(self.wd, 'dinf_sca.tif')

    @property
    def _dinf_sca_args(self):
        return ['-sca', self._dinf_sca]

    # dinf distance down output
    @property
    def _dinf_dd_horizontal(self):
        return _join(self.wd, 'dinf_dd_horizontal.tif')

    @property
    def _dinf_dd_vertical(self):
        return _join(self.wd, 'dinf_dd_vertical.tif')

    @property
    def _dinf_dd_surface(self):
        return _join(self.wd, 'dinf_dd_surface.tif')

    # subprocess methods

    @property
    def _mpi_args(self):
        if _USE_MPI:
            return ['mpiexec', '-n', NCPU]
        else:
            return []

    def _sys_call(self, cmd, verbose=True, intent_in=None, intent_out=None):
        # verify inputs exist
        if intent_in is not None:
            for product in intent_in:
                assert _exists(product), product

        # delete outputs if they exist
        if intent_out is not None:
            for product in intent_out:
                if _exists(product):
                    os.remove(product)

        cmd = [str(v) for v in cmd]

#        if not _exists('/usr/lib/libgdal.so.20'):
#            cmd.extend(['-env', 'LD_LIBRARY_PATH', os.path.abspath(_join(_thisdir, 'bin/linux/lib'))])

        caller = inspect.stack()[1].function
        log = _join(self.wd, caller + '.log')
        _log = open(log, 'w')

        if verbose:
            print(caller, cmd)

        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=_log, stderr=_log,
                             env={'LD_LIBRARY_PATH': os.path.abspath(_join(_thisdir, 'bin/linux/lib'))})
        p.wait()
        _log.close()

        if intent_out is None:
            return

        for product in intent_out:
            if not _exists(product):
                raise Exception('{} Failed: {} does not exist. See {}'.format(caller, product, log))

            if product.endswith('.tif'):
                p = subprocess.Popen(['gdalinfo', product, '-stats'], shell=True,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     close_fds=True)
                stdout = p.stdout.read().decode('utf-8')

                if 'no valid pixels found in sampling' in stdout:
                    raise Exception('{} Failed: {} does not contain any valid pixels.'.format(caller, product))

        if not _DEBUG:
            os.remove(log)

    @property
    def __pitremove(self):
        return self._mpi_args + [_join(_taudem_bin, 'pitremove')]

    @property
    def __d8flowdir(self):
        return self._mpi_args + [_join(_taudem_bin, 'd8flowdir')]

    @property
    def __aread8(self):
        return self._mpi_args + [_join(_taudem_bin, 'aread8')]

    @property
    def __gridnet(self):
        return self._mpi_args + [_join(_taudem_bin, 'gridnet')]

    @property
    def __threshold(self):
        return self._mpi_args + [_join(_taudem_bin, 'threshold')]

    @property
    def __moveoutletstostrm(self):
        return self._mpi_args + [_join(_taudem_bin, 'moveoutletstostrm')]

    @property
    def __peukerdouglas(self):
        return self._mpi_args + [_join(_taudem_bin, 'peukerdouglas')]

    @property
    def __dropanalysis(self):
        return self._mpi_args + [_join(_taudem_bin, 'dropanalysis')]

    @property
    def __streamnet(self):
        return self._mpi_args + [_join(_taudem_bin, 'streamnet')]

    @property
    def __gagewatershed(self):
        return self._mpi_args + [_join(_taudem_bin, 'gagewatershed')]

    @property
    def __dinfflowdir(self):
        return self._mpi_args + [_join(_taudem_bin, 'dinfflowdir')]

    @property
    def __areadinf(self):
        return self._mpi_args + [_join(_taudem_bin, 'areadinf')]

    @property
    def __dinfdistdown(self):
        return self._mpi_args + [_join(_taudem_bin, 'dinfdistdown')]

    # TauDEM wrapper methods

    def run_pitremove(self):
        """
        This function takes as input an elevation data grid and outputs a hydrologically correct elevation grid file
        with pits filled, using the flooding algorithm.

        in: dem
        out: fel
        """
        self._sys_call(self.__pitremove + self._z_args + self._fel_args,
                       intent_in=(self._z,),
                       intent_out=(self._fel,))

    def run_d8flowdir(self):
        """
        This function takes as input the hydrologically correct elevation grid and outputs D8 flow direction and slope
        for each grid cell. In flat areas flow directions are assigned away from higher ground and towards lower ground
        using the method of Garbrecht and Martz (Garbrecht and Martz, 1997).

        in: fel
        out: point, slope_d8
        """
        self._sys_call(self.__d8flowdir + self._fel_args + self._p_args + self._sd8_args,
                       intent_in=(self._fel,),
                       intent_out=(self._sd8, self._fd8))

    def run_aread8(self, no_edge_contamination_checking=False):
        """
        This function takes as input a D8 flow directions file and outputs the contributing area. The result is the
        number of grid cells draining through each grid cell. The optional command line argument for the outlet
        shapefile results in only the area contributing to outlet points in the shapefile being calculated. The optional
        weight grid input results in the output being the accumulation (sum) of the weights from upstream grid cells
        draining through each grid cell. By default the program checks for edge contamination. The edge contamination
        checking may be overridden with the optional command line.

        in: point
        out: area_d8
        """
        self._sys_call(self.__aread8 + self._p_args + self._ad8_args + ([], ['-nc'])[no_edge_contamination_checking],
                       intent_in=(self._fd8,),
                       intent_out=(self._ad8,))

    def run_gridnet(self):
        """
        in: p
        out: gord, plen, tlen
        """
        self._sys_call(self.__gridnet + self._p_args + self._gord_args + self._plen_args + self._tlen_args,
                       intent_in=(self._fd8,),
                       intent_out=(self._gord, self._plen, self._tlen))

    def _run_threshold(self, ssa, src, threshold=1000):
        """
        This function operates on any grid and outputs an indicator (1,0) grid of grid cells that have values >= the
        input threshold. The standard use is to threshold an accumulated source area grid to determine a stream raster.
        There is an option to include a mask input to replicate the functionality for using the sca file as an edge
        contamination mask. The threshold logic should be src = ((ssa >= thresh) & (mask >=0)) ? 1:0

        in: ssa
        out: src
        """
        self._sys_call(self.__threshold + ['-ssa', ssa, '-src', src, '-thresh', threshold],
                       intent_in=(ssa,),
                       intent_out=(src,))

    def run_src_threshold(self, threshold=10):
        self._run_threshold(ssa=self._ad8, src=self._src, threshold=threshold)

    def _make_outlet_geojson(self, lng=None, lat=None, dst=None, easting=None, northing=None):
        assert dst is not None

        if lng is not None and lat is not None:
            easting, northing = self.lnglat_to_utm(long=lng, lat=lat)

        assert isfloat(easting), easting
        assert isfloat(northing), northing

        with open(dst, 'w') as fp:
            fp.write(_outlet_template_geojson
                     .format(epsg=self.epsg, easting=easting, northing=northing))

        assert _exists(dst), dst
        return dst

    def _make_multiple_outlets_geojson(self, dst, en_points_dict):
        points = []
        for id, (easting, northing) in en_points_dict.items():
            points.append(_point_template_geojson
                          .format(id=id, easting=easting, northing=northing))

        with open(dst, 'w') as fp:
            fp.write(_multi_outlet_template_geojson
                     .format(epsg=self.epsg, points=',\n'.join(points)))

        assert _exists(dst), dst
        return dst

    def run_moveoutletstostrm(self, lng, lat):
        """
        This function finds the closest channel location to the requested location

        :param lng: requested longitude
        :param lat: requested latitude
        """
        self.user_outlet = lng, lat
        self._make_outlet_geojson(lng=lng, lat=lat, dst=self._uo)
        self._sys_call(self.__moveoutletstostrm + self._p_args + self._src_args + ['-o', self._uo] + ['-om', self._o],
                       intent_in=(self._fd8, self._src, self._uo),
                       intent_out=(self._o,))

        with open(self._o) as fp:
            js = json.load(fp)
            if js['features'][0]['properties']['Dist_moved'] == -1:
                warnings.warn('Outlet location did not move')

            o_e, o_n = js['features'][0]['geometry']['coordinates']

        proj2wgs_transformer = GeoTransformer(src_proj4=self.srs_proj4, dst_proj4=wgs84_proj4)
        self.outlet = proj2wgs_transformer.transform(x=o_e, y=o_n)

    def run_peukerdouglas(self, center_weight=0.4, side_weight=0.1, diagonal_weight=0.05):
        """
        This function operates on an elevation grid and outputs an indicator (1,0) grid of upward curved grid cells
        according to the Peuker and Douglas algorithm. This is to be based on code in tardemlib.cpp/source.

        in: fel
        out: ss
        """
        self._sys_call(self.__peukerdouglas + self._fel_args + self._ss_args +
                       ['-par', center_weight, side_weight, diagonal_weight],
                       intent_in=(self._fel,),
                       intent_out=(self._ss,))

    @property
    def drop_analysis_threshold(self):
        """
        Reads the drop table and extracts the optimal value

        :return: optimimum threshold value from drop table
        """
        with open(self._drp) as fp:
            lines = fp.readlines()

        last = lines[-1]

        assert 'Optimum Threshold Value:' in last, '\n'.join(lines)
        return float(last.replace('Optimum Threshold Value:', '').strip())

    def run_peukerdouglas_stream_delineation(self, threshmin=5, threshmax=500, nthresh=10, steptype=0, threshold=None):
        """

        :param threshmin:
        :param threshmax:
        :param nthresh:
        :param steptype:
        :param threshold:

        in: p, o, ss
        out:
        """
        self._sys_call(self.__aread8 + self._p_args + self._o_args + ['-ad8', self._ssa] + ['-wg', self._ss],
                       intent_in=(self._fd8, self._o, self._ss),
                       intent_out=(self._ssa,))

        self._sys_call(self.__dropanalysis + self._p_args + self._fel_args +
                       self._ad8_args + self._ssa_args + self._drp_args +
                       self._o_args + ['-par', threshmin, threshmax, nthresh, steptype],
                       intent_in=(self._fd8, self._fel, self._ad8, self._o, self._ssa),
                       intent_out=(self._drp,))

        if threshold is None:
            threshold = self.drop_analysis_threshold

        self._run_threshold(self._ssa, self._pksrc, threshold=threshold)

    def run_streamnet(self, single_watershed=False):
        """
        in: fel, p, ad8, pksrc, o
        out: w, ord, tree, net, coors
        """
        self._sys_call(self.__streamnet + self._fel_args + self._p_args + self._ad8_args +
                       self._pksrc_args + self._o_args + self._ord_args + self._tree_args + self._net_args +
                       self._coord_args + self._w_args + ([], ['-sw'])[single_watershed],
                       intent_in=(self._fel, self._fd8, self._ad8, self._pksrc, self._o),
                       intent_out=(self._w, self._ord, self._tree, self._net, self._coord))

    def _run_gagewatershed(self, **kwargs):
        """
        in: p
        out: gw
        """
        lng = kwargs.get('lng', None)
        lat = kwargs.get('lat', None)
        easting = kwargs.get('easting', None)
        northing = kwargs.get('northing', None)
        outlets_fn = kwargs.get('outlets_fn', None)
        dst = kwargs.get('dst', None)

        if outlets_fn is None:
            point = self._make_outlet_geojson(lng=lng, lat=lat, easting=easting, northing=northing, dst=dst[:-4] + '.geojson')
            self._sys_call(self.__gagewatershed + self._p_args + ['-o', point] + ['-gw', dst],
                           intent_in=(point, self._fd8),
                           intent_out=(dst,))
        else:
            self._sys_call(self.__gagewatershed + self._p_args + ['-o', outlets_fn] + ['-gw', dst],
                           intent_in=(outlets_fn, self._fd8),
                           intent_out=(dst,))

    def run_dinfflowdir(self):
        """
        in: fel
        out: dinf_angle, dinf_slope
        """
        self._sys_call(self.__dinfflowdir + self._fel_args + self._dinf_angle_args + self._dinf_slope_args,
                       intent_in=(self._fel,),
                       intent_out=(self._dinf_angle, self._dinf_slope))

    def run_areadinf(self):
        """
        in: dinf_angle
        out: dinf_sca
        """
        self._sys_call(self.__areadinf + self._dinf_angle_args + self._o_args + self._dinf_sca_args,
                       intent_in=(self._o, self._dinf_angle),
                       intent_out=(self._dinf_sca,))

    def run_dinfdistdown(self, no_edge_contamination_checking=False):
        """

        in: dinf_angle, fel,
        out: dinf_dd_horizontal, dinf_dd_vertical, dinf_dd_surface
        """
        # method_statistic:
        #     ave = average of flowpath, min = minimum length of flowpath, max = maximum length of flowpath
        method_statistic = 'ave'

        # method_type:
        #     h = horizontal, v = vertical, p = Pythagoras, s = surface

        for method_type in ['horizontal', 'vertical', 'surface']:
            dst = _join(self.wd, 'dinf_dd_%s.tif' % method_type)

            self._sys_call(self.__dinfdistdown + self._dinf_angle_args + self._fel_args + self._pksrc_args +
                           ['-dd', dst] + ['-m', method_statistic, method_type[0]] +
                           ([], ['-nc'])[no_edge_contamination_checking],
                           intent_in=(self._dinf_angle, self._fel, self._pksrc),
                           intent_out=(dst,))

    @property
    def cellsize2(self):
        return self.cellsize ** 2

    @property
    def network(self):
        with open(self._net) as fp:
            js = json.load(fp)

        network = {}

        for feature in js['features']:
            tau_id = feature['properties']['WSNO']
            uslinkn01 = feature['properties']['USLINKNO1']
            uslinkn02 = feature['properties']['USLINKNO2']
            enz_coords = feature['geometry']['coordinates']
            bottom = enz_coords[0][0], enz_coords[0][1]
            top = enz_coords[-1][0], enz_coords[-1][1]

            links = [v for v in [uslinkn01, uslinkn02] if v != -1]
            network[tau_id] = dict(links=links, top=top, bottom=bottom)

        return network

    @property
    def outlet_tau_id(self):
        with open(self._net) as fp:
            js = json.load(fp)

        for feature in js['features']:
            tau_id = feature['properties']['WSNO']
            dslinkn0 = feature['properties']['DSLINKNO']

            if dslinkn0 == -1:
                return tau_id
