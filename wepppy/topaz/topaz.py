# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math
from operator import index
import os
from os.path import exists as _exists
import json
from os.path import exists
from os.path import join as _join
import sys
from subprocess import Popen, PIPE, STDOUT
import time
from glob import glob
import shutil
import warnings
import copy

from imageio import imread

from osgeo import gdal, ogr, osr
import utm

import numpy as np

from wepppy.all_your_base import isfloat, IS_WINDOWS
from wepppy.all_your_base.geo import read_arc, get_utm_zone, wgs84_proj4, utm_srid

from wepppy.watershed_abstraction import WeppTopTranslator
from wepppy.watershed_abstraction.support import (
    json_to_wgs, polygonize_netful, polygonize_bound, polygonize_subcatchments
)

os.environ["PYTHONUNBUFFERED"] = "1"

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)

# directory containing: dednm, rasbin, raspro, and rasfor
topaz_bin = _join(_thisdir, 'topaz_bin')

# directory containing INPs for topaz binaries
topaz_templates = _join(_thisdir, 'topaz_templates')

# no data value for ARC raster datasets
no_data = '0'

# template for building
arc_template = '''\
ncols    {num_cols}
nrows   {num_rows}
xllcorner  {ll_x}
yllcorner {ll_y}
cellsize   {cellsize}
nodata_value     {no_data}
{data}'''

_TIMEOUT = 60


def _str_dem_val(f):
    """
    helper function to stringify the elevation values
    """
    global no_data
    if f <= 0:
        return no_data
    return str(f)


def _cp_chmod(src, dst, mode):
    """
    helper function to copy a file and set chmod
    """
    shutil.copyfile(src, dst)

    try:
        os.chmod(dst, mode)
    except:
        pass

class TopazUnexpectedTermination(Exception):
    """
    DEDNM TERMINATED UNEXPECTEDLY, THIS GENERALLY OCCURS IF THE
    WATERSHED IS TOO BIG OR COMPLEX. TRY DELINEATING A SMALLER
    AREA OR ADJUSTING THE CSA AND MCL PARAMETERS
    """

    __name__ = 'Topaz Unexpected Termination'


class WatershedBoundaryTouchesEdgeError(Exception):
    """
    THE WATERSHED BOUNDARY TOUCHES THE EDGE OF THE DEM.
    IT IS POSSIBLE THAT THE ACTUAL WATERSHED EXTENDS BEYOND THE EDGE OF THE DEM.

    THE WATERSHED MUST BE FULLY DEFINED WITHIN THE DEM AND SHOULD GENERALLY
    NOT TOUCH THE EDGE OF THE DEM OR AN AREA OF INDETERMINATE ELEVATION.
    """

    __name__ = 'Watershed Boundary Touches Edge Error'


class MinimumChannelLengthTooShortError(Exception):
    """
    THE VALUE FOR THE MINIMUM CHANNEL LENGTH FOR A CHANNEL TO BE
    CLASSIFIED AS A CHANNEL IS TOO SHORT.

    IT MUST BE LONGER THAN 1.0 METER AND LONGER THAN A CELL SIDE
    """

    __name__ = 'Minimum Channel Length TooShort Error'


class DednmCrashedException(Exception):
    """
    dednm crashed for an unknown reason, try again
    """

    __name__ = 'Dednm Crashed Exception'


class RasbinCrashedException(Exception):
    """
    rasbin crashed for an unknown reason, try again
    """

    __name__ = 'Rasbin Crashed Exception'


class RasproCrashedException(Exception):
    """
    raspro crashed for an unknown reason, try again
    """

    __name__ = 'Raspro Crashed Exception'


class RasforCrashedException(Exception):
    """
    rasfor crashed for an unknown reason, try again
    """

    __name__ = 'Rasfor Crashed Exception'


class TopazRunner:
    """
    Object oriented abstraction for running USDA ARS Topagraphic Parameterization
    (topaz).

    For more infomation on topaz see the manual available here:
        https://www.ars.usda.gov/ARSUserFiles/30700510/TOPAZ_User-Manual2.pdf
    """
    def __init__(self, topaz_wd, dem, csa=5, mcl=60):
        """
        provide a path to a directory to store the topaz files a
        path to a dem
        """
        global no_data, topaz_bin, topaz_templates
        self.no_data = no_data
        self.csa = csa
        self.mcl = mcl
        self.outlet = None

        # check to make sure we have the necessary external resources
        assert exists(topaz_templates), 'Cannot find topaz_templates dir'
        topaz_templates = os.path.abspath(topaz_templates)

        assert exists(topaz_bin), 'Cannot find topaz_bin dir'
        topaz_bin = os.path.abspath(topaz_bin)

        assert exists(topaz_wd), 'Cannot find topaz_wd'
        self.topaz_wd = os.path.abspath(topaz_wd)

        assert exists(_join(topaz_bin, 'dednm')), 'Cannot find dednm'
        assert exists(_join(topaz_bin, 'rasbin')), 'Cannot find rasbin'
        assert exists(_join(topaz_bin, 'rasfor')), 'Cannot find rasfor'
        assert exists(_join(topaz_bin, 'raspro')), 'Cannot find raspro'

        assert exists(_join(topaz_templates, 'DNMCNT.INP.template')), 'Cannot find DNMCNT.INP.template'
        assert exists(_join(topaz_templates, 'RASFOR.INP')), 'Cannot find RASFOR.INP'
        assert exists(_join(topaz_templates, 'RASPRO.INP')), 'Cannot find RASPRO.INP'

        # verify the dem exists
        if not exists(dem):
            raise Exception('file "%s" does not exist' % dem)

        self.dem = os.path.abspath(dem)

        # parsing the dem loads attributes for the instance
        self._parse_dem()

        # if the channel dataset is found, load the channel and junction masks
        self.junction_mask = None

    def _clean_dir(self, empty_only=False):
        """
        Remove topaz related files from the working directory
        """
        wd = self.topaz_wd

        for ext in ['.OUT', '.ARC', '.INP', '.RPT', '.UNF', '.TAB', '.PRJ']:
            for fn in glob(_join(wd, '*' + ext)):
                size = os.path.getsize(fn)
                if not empty_only or size == 0:
                    try:
                        os.remove(fn)
                    except FileNotFoundError:
                        pass

    def _prep_dir(self):
        """
        copy over the topaz executables and the control files that don't need changed
        """
        wd = self.topaz_wd

        if IS_WINDOWS:
            _cp_chmod(_join(topaz_bin, 'dednm.exe'), _join(wd, 'dednm.exe'), 0o755)
            # _cp_chmod(_join(topaz_bin, 'rasbin'), _join(wd, 'rasbin'), 0o755)
            _cp_chmod(_join(topaz_bin, 'raspro.exe'), _join(wd, 'raspro.exe'), 0o755)
            _cp_chmod(_join(topaz_bin, 'rasfor.exe'), _join(wd, 'rasfor.exe'), 0o755)
        else:
            _cp_chmod(_join(topaz_bin, 'dednm'), _join(wd, 'dednm'), 0o755)
            # _cp_chmod(_join(topaz_bin, 'rasbin'), _join(wd, 'rasbin'), 0o755)
            _cp_chmod(_join(topaz_bin, 'raspro'), _join(wd, 'raspro'), 0o755)
            _cp_chmod(_join(topaz_bin, 'rasfor'), _join(wd, 'rasfor'), 0o755)

        shutil.copyfile(_join(topaz_templates, 'RASFOR.INP'), _join(wd, 'RASFOR.INP'))
        shutil.copyfile(_join(topaz_templates, 'RASPRO.INP'), _join(wd, 'RASPRO.INP'))

    def _create_dnmcnt_input(self, _pass, outlet=(2, 2)):
        """
        this creates the control file for running dednm
        _pass -> 1 is for building channels
        _pass -> 2 is for building subcatchments

        _outlet should be a tuple with x, y (row, col) pixel coordinates
        """
        assert len(outlet) == 2, 'expecting outlet to have length of two'

        with open(_join(topaz_templates, 'DNMCNT.INP.template')) as fp:
            template = fp.read()

        meta = dict(
                    utm_zone=self.utm_zone,
                    ll_x=self.ll_x,
                    ll_y=self.ll_y,
                    num_rows=self.num_rows,
                    num_cols=self.num_cols,
                    minimum_elevation=1.0,
                    maximum_elevation=9000.0,
                    no_data=self.no_data,
                    cellsize=self.cellsize,
                    orientation=0,
                    outlet_row=outlet[1]+1,
                    outlet_col=outlet[0]+1,
                    preprocessing_opt=0,
                    preprocessing_opt_par=5,
                    smoothing_weight=0,
                    smoothing_passes=2,
                    weighting_par_1=(2, 1)[_pass == 1],
                    weighting_par_2=1,
                    weighting_par_3=1,
                    partial_dem_processing_opt=(0, 2)[_pass == 1],
                    spatial_csa_par=0,
                    csa=self.csa,
                    mcl=self.mcl,
                    sbct_tab=(1, 0)[_pass == 1],
                   )

        fid = open(_join(self.topaz_wd, 'DNMCNT.INP'), 'w')
        fid.write(template.format(**meta))
        fid.close()

        return exists(_join(self.topaz_wd, 'DNMCNT.INP'))

    def _load_flow_accum(self):
        # open raster of upstream drainage area
        uparea_arc = _join(self.topaz_wd, 'UPAREA.ARC')
        data, _transform, _proj = read_arc(uparea_arc, dtype=np.float)
        self.flow_accum = data

    def _load_channel_masks(self):
        """
        Reads the channel map into memory and identifies the junctions
        to make a map of neighbor counts. The neighbor count map also
        gets stored as an attribute of the class and is put into
        CHNJNT.ARC
        """
        # open the channel map
        netful_arc = _join(self.topaz_wd, 'NETFUL.ARC')
        data, _transform, _proj = read_arc(netful_arc, dtype=np.int32)
        n, m = data.shape

        # pad the data table with a border of zeros so we can slice
        # to count the neighbors
        _data = np.zeros((n+2, m+2), dtype=np.int)
        _data[1:-1, 1:-1] = data

        # iterate and fill the mask (neighbor counts)
        mask = np.zeros((n, m), dtype=np.int)
        for i in range(1, n+1):
            for j in range(1, m+1):
                # only channel cells can have neighbors
                if _data[i, j] == 1:
                    # count number of neighbors that are channels
                    mask[i-1, j-1] = np.sum(_data[i-1:i+2, j-1:j+2]) - 1

        # save to instance
        self.channel_mask = data
        self.junction_mask = mask

        # write junction_mask to wd as CHNJNT.ARC dataset
        data_string = [' '.join(map(str, mask[:, j].flatten())) for j in range(m)]
        data_string = [' ' + row for row in data_string]
        data_string = '\n'.join(data_string)

        fname = _join(self.topaz_wd, 'CHNJNT.ARC')
        if exists(fname):
            os.remove(fname)

        with open(fname, 'w') as fp:
            fp.write(arc_template.format(num_cols=n,
                                         num_rows=m,
                                         ll_x=self.ll_x,
                                         ll_y=self.ll_y,
                                         cellsize=self.cellsize,
                                         no_data=no_data,
                                         data=data_string))

        self.create_prj(fname)

        data2, _transform2, _proj2 = read_arc(fname)
        assert data2.shape == data.shape

        return True

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

    def find_closest_da_match(self, lng, lat, da, pixelcoords=False):
        """
        find the coordinates with the closest match to the given drainage area 

        returns (x, y), distance
           where (x, y) are pixel coords and distance is the distance from the
           specified lng, lat in pixels
        """
        # print('lng, lat, da=', lng, lat, da)
        self._load_flow_accum()
        flow_acc = self.flow_accum.T #transpose to get correct orientation
        # print('shape flow ac', np.shape(flow_acc))

        # unpack variables for instance
        if self.junction_mask is None:
            self._load_channel_masks()

        # The orientation of the map is wonky in this algorithm.
        # we transpose the mask for the algorithm
        mask = self.junction_mask.T
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows

        if pixelcoords:
            x, y = lng, lat
        else:
            x, y = self.lnglat_to_pixel(lng, lat)
        
        #pull drainage area for radius around the given outlet
        r = 200
        num_cells = round(r/cellsize)

        miny = y-num_cells
        if miny<0:
            miny=0
        maxy = y+num_cells
        if maxy>num_rows:
            maxy=num_rows
        minx = x-num_cells
        if minx<0:
            minx=0
        maxx = x+num_cells
        if maxx>num_cols:
            maxx=num_cols
        

        rows = np.arange(miny,maxy)
        cols = np.arange(minx,maxx)

        it=0
        areas = np.zeros(len(rows)*len(cols))
        newrows = np.zeros(len(rows)*len(cols),dtype=int)
        newcols = np.zeros(len(rows)*len(cols),dtype=int)
        # print('np.shape(areas)', np.shape(areas))
        for r in rows:
            for c in cols:
                areas[it] = flow_acc[r,c]*(cellsize*cellsize)/1e6
                newrows[it] = r
                newcols[it] = c
                it=it+1

        
        areaslist = areas.tolist()
        rowsl = newrows.tolist()
        colsl = newcols.tolist()


        # # find the index of the closest drainage area
        # all_areas = flow_acc*(cellsize*cellsize)/1e6
        # idx = np.abs(all_areas - da).argmin()
        # # print('idx=', idx)
        # # print('flow_acc[idx]',flow_acc[idx])
        # rowcol = np.unravel_index(idx,np.shape(flow_acc))
        # print('rowcol=', rowcol)
        # print('best matching drainage area chosen from entire FA = ',flow_acc[rowcol]*(cellsize*cellsize)/1e6)

        # unpack variables for instance
        if self.junction_mask is None:
            self._load_channel_masks()

        # The orientation of the map is a wonky in this algorithm.
        # we transpose the mask for the algorithm
        mask = self.junction_mask.T


        index_min = np.argmin(abs(areaslist-da))
        _x = colsl[index_min]
        _y = rowsl[index_min]
        # print('_x', _x)
        
        print('len(areas)', len(areaslist))
        # print('areas=', areaslist)
        print('first area match = ', areaslist[index_min])
        
        
        toobig=0
        while mask[_y,_x] > 2 or toobig == 1: #if chosen outlet has more than two neighbors, find the next closest
            print('more than two neighbors, finding next closest drainage area that is smaller')
            areaold = areaslist[index_min] 
            areaslist.pop(index_min)
            rowsl.pop(index_min)
            colsl.pop(index_min)
            
            index_min = np.argmin(abs(areaslist-da))
            _x = colsl[index_min]
            _y = rowsl[index_min]
            if areaslist[index_min] > areaold:
                toobig=1
            else:
                toobig=0
            print('mask[_y,_x]=', mask[_y,_x])
            print('drainage area = ', areaslist[index_min] )

        _x = colsl[index_min]
        _y = rowsl[index_min]
        distance = math.sqrt((_x - x)**2 + (_y - y)**2)
        print('closest area match, distance in pixels = ', areaslist[index_min], distance)

        return (_x, _y), distance


    def find_closest_channel(self, lng, lat, pixelcoords=False):
        """
        find the closest channel give a lng and lat or pixel coords
        (pixelcoords=True)

        returns (x, y), distance
           where (x, y) are pixel coords and distance is the distance from the
           specified lng, lat and distance is the distance from lng, lat
           in pixels
        """

        # unpack variables for instance
        if self.junction_mask is None:
            self._load_channel_masks()

        # The orientation of the map is a wonky in this algorithm.
        # we transpose the mask for the algorithm
        mask = self.junction_mask.T
        cellsize, num_cols, num_rows = self.cellsize, self.num_cols, self.num_rows

        if pixelcoords:
            x, y = lng, lat
        else:
            x, y = self.lnglat_to_pixel(lng, lat)

        # the easy case
        if mask[y, x] == 2:
            return (x, y), 0

        # need to iterate over channel values
        _x, _y = 0, 0
        n, m = mask.shape

        # initialize distance to diagonal distance of dem in pixels
        distance = math.sqrt(num_rows ** 2 + num_cols ** 2)
        for i in range(n):
            for j in range(m):

                # we only want distance to non-junction channel cells so
                # if we don't have two neighbors we can move on
                if mask[i, j] != 2:
                    continue

                # calculate the distance
                _d = math.sqrt(abs(y - i) ** 2 + abs(x - j) ** 2)

                # if it is less than distance than store it and move on
                if _d < distance:
                    _y, _x = i, j
                    distance = _d

        return (_x, _y), distance

    def _create_dednm_input(self):
        """
        Uses gdal to extract elevation values from dem and puts them in a
        single column ascii file named DEDNM.INP for topaz
        """

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = imread(self.dem)

        data = data.flatten()
        data = np.clip(data, 1.0, 9999.0)

        dednm_inp = 'DEDNM.INP'
        fid = open(_join(self.topaz_wd, dednm_inp), 'w')
        fid.write('\n'.join(map(_str_dem_val, data)))
        fid.close()

        self.dednm_inp = dednm_inp

    def _parse_dem(self):
        """
        Uses gdal to extract elevation values from dem and puts them in a
        single column ascii file named DEDNM.INP for topaz
        """
        dem = self.dem

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
        self.utm_zone = utm_zone
        self.hemisphere = hemisphere
        self.srs_proj4 = srs.ExportToProj4()
        srs.MorphToESRI()
        self.srs_wkt = srs.ExportToWkt()
        self.minimum_elevation = minimum_elevation
        self.maximum_elevation = maximum_elevation

        del ds

    def create_prj(self, fname):
        """
        Create a PRJ for a topaz resource based on dem's projection
        """
        fname = fname.replace('.ARC', '.PRJ')

        if exists(fname):
            os.remove(fname)

        fid = open(fname, 'w')
        fid.write(self.srs_wkt)
        fid.close()

        return True

    def create_prjs(self):
        """
        Create prjs for all the .ARC files in the working directory
        """
        for fname in glob(_join(self.topaz_wd, '*.ARC')):
            self.create_prj(fname)

        return True

    def _run_subprocess(self, cmd, stdin=None, verbose=False):

        if IS_WINDOWS:
            return self._run_subprocess_win(cmd=cmd, stdin=stdin, verbose=verbose)
        else:
            return self._run_subprocess_nix(cmd=cmd, stdin=stdin, verbose=verbose)

    def _run_subprocess_win(self, cmd, stdin=None, verbose=False):
        """
        run on windows
        """

        if verbose:
            print('cmd: %s\ncwd: %s\n' % (cmd, self.topaz_wd))

        # need to use try catch to make sure we have a chance to switch the
        # working directory back
        lines = []

        p = Popen(cmd, bufsize=0, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=self.topaz_wd, universal_newlines=True)

        # on pass 2 we need to write '1' to standard input
        if stdin is not None:
            p.stdin.write(stdin)
            p.stdin.flush()

        abort_count = 0

        while p.poll() is None:
            output = p.stdout.readline()
            output = output.strip()

            if output != '':
                lines.append(output)

            if verbose:
                sys.stdout.write(output + '\n')
                sys.stdout.flush()

            # If the input dem is large it give a warning and prompts whether or not it should continue
            if 'OR  0 TO STOP PROGRAM EXECUTION.' in output:
                try:
                    outs, errs = p.communicate(input=('0\n', '0\r\n')[IS_WINDOWS], timeout=15)

                    if verbose:
                        print(outs, errs)
                except:
                    try:
                        p.kill()
                    except:
                        pass

                    lines.append('UNEXPECTED TERMINATION')
                    return [line for line in lines if line != '']

            # This comes up if the outlet isn't a channel and we are trying to build
            # subcatchments. The build_subcatchments method preprocesses the outlet
            # to find a channel, so this shouldn't happen (unless something else breaks)
            #
            # It comes up once even if the outlet is a hillslope that is why we write '1'
            # to the stdin if we are on pass 2.
            if 'ENTER 1 IF YOU WANT TO PROCEED WITH THESE VALUES' in output:
                outs, errs = p.communicate(input=('1\n', '1\r\n')[IS_WINDOWS], timeout=15)

                if verbose:
                    print(outs, errs)
                abort_count += 1

            if 'ENTER 0 IF YOU WANT TO CHANGE THESE VALUES' in output:
                outs, errs = p.communicate(input=('1\n', '1\r\n')[IS_WINDOWS], timeout=15)

                if verbose:
                    print(outs, errs)

            # This occurs if the watershed extends beyond the dem. There isn't a way
            # of checking that, and novice users have a hard time recognizing this
            # condition from the channel map
            if 'ENTER   1   TO PROCEED WITH POTENTIALLY INCOMPLETE WATERSHED.' in output:
                outs, errs = p.communicate(input=('1\n', '1\r\n')[IS_WINDOWS], timeout=15)

                if verbose:
                    print(outs, errs)
                abort_count += 1

            # if the abort count is greater than 2, then abort
            if abort_count > 2:
                p.kill()

        p.stdin.close()
        p.stdout.close()

        # return output as list of strings
        return [line for line in lines if line != '']

    def _run_subprocess_nix(self, cmd, stdin=None, verbose=False):
        """
        run on linux
        """

        if verbose:
            print('cmd: %s\ncwd: %s\n' % (cmd, self.topaz_wd))

        # need to use try catch to make sure we have a chance to switch the
        # working directory back
        lines = []

        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=self.topaz_wd)

        # on pass 2 we need to write '1' to standard input
        if stdin is not None:
            p.stdin.write(stdin.encode("utf-8"))
            p.stdin.close()

        abort_count = 0

        while p.poll() is None:
            output = p.stdout.readline().decode("utf-8")
            output = output.strip()

            if output != '':
                lines.append(output)

            if verbose:
                sys.stdout.write(output + '\n')
                sys.stdout.flush()

            # If the input dem is large it give a warning and prompts whether or not it should continue
            if 'OR  0 TO STOP PROGRAM EXECUTION.' in output:
                abort_count += 1
                try:
                    p.stdin.write(b'1')
                    p.stdin.close()
                except:
                    try:
                        p.kill()
                    except:
                        pass

                    lines.append('UNEXPECTED TERMINATION')
                    return [line for line in lines if line != '']

            # This comes up if the outlet isn't a channel and we are trying to build
            # subcatchments. The build_subcatchments method preprocesses the outlet
            # to find a channel, so this shouldn't happen (unless something else breaks)
            #
            # It comes up once even if the outlet is a hillslope that is why we write '1'
            # to the stdin if we are on pass 2.
            if 'ENTER 1 IF YOU WANT TO PROCEED WITH THESE VALUES' in output:
                abort_count += 1

            # This occurs if the watershed extends beyond the dem. There isn't a way
            # of checking that, and novice users have a hard time recognizing this
            # condition from the channel map
            if 'ENTER   1   TO PROCEED WITH POTENTIALLY INCOMPLETE WATERSHED.' in output:
                abort_count += 1

            # if the abort count is greater than 2, then abort
            if abort_count > 2:
                p.kill()

        p.stdin.close()
        p.stdout.close()

        # return output as list of strings
        return [line for line in lines if line != '']

    def _run_dednm(self, _pass=1, verbose=False):
        topaz_wd = self.topaz_wd

        if _pass == 2:
            if _exists(_join(topaz_wd, 'CATWIN.TAB')):
                os.remove(_join(topaz_wd, 'CATWIN.TAB'))
            if _exists(_join(topaz_wd, 'BOUND.OUT')):
                os.remove(_join(topaz_wd, 'BOUND.OUT'))

        if IS_WINDOWS:
            output = self._run_subprocess(_join(topaz_wd, 'dednm.exe'), (None, '1')[_pass == 2], verbose)
        else:
            output = self._run_subprocess('./dednm', (None, '1')[_pass == 2], verbose)

        with open(_join(topaz_wd, 'dednm.log'), 'w') as fp:
            fp.write('\n'.join(output))

        for i in range(len(output)-1):
            line = output[i]

            if 'UNEXPECTED TERMINATION' in line:
                raise TopazUnexpectedTermination()
            if 'THE WATERSHED BOUNDARY TOUCHES THE EDGE OF THE DEM' in line:
                raise WatershedBoundaryTouchesEdgeError()
            if 'THE VALUE FOR THE MINIMUM CHANNEL LENGTH FOR A CHANNEL TO BE' in line and \
               'CLASSIFIED AS A CHANNEL IS TOO SHORT.' in output[i+1]:
                raise MinimumChannelLengthTooShortError()

        if _pass == 1 and \
           _exists(_join(topaz_wd, 'FLOPAT.OUT')) and \
           _exists(_join(topaz_wd, 'FLOVEC.OUT')) and \
           _exists(_join(topaz_wd, 'NETFUL.OUT')) and \
           _exists(_join(topaz_wd, 'RELIEF.OUT')):
            return output

        elif (_pass == 2 and \
           _exists(_join(topaz_wd, 'CHNJNT.ARC')) and \
           _exists(_join(topaz_wd, 'CATWIN.TAB')) and \
           _exists(_join(topaz_wd, 'BOUND.OUT'))):
            return output

        raise DednmCrashedException(output)

    def _run_rasfor(self, _pass=1, verbose=False):
        topaz_wd = self.topaz_wd

        if _pass == 1:
            if _exists(_join(self.topaz_wd, 'FLOPAT.ARC')):
                os.remove(_join(self.topaz_wd, 'FLOPAT.ARC'))
            if _exists(_join(self.topaz_wd, 'FLOVEC.ARC')):
                os.remove(_join(self.topaz_wd, 'FLOVEC.ARC'))
            if _exists(_join(self.topaz_wd, 'NETFUL.ARC')):
                os.remove(_join(self.topaz_wd, 'NETFUL.ARC'))
            if _exists(_join(self.topaz_wd, 'RELIEF.ARC')):
                os.remove(_join(self.topaz_wd, 'RELIEF.ARC'))
        elif _pass == 2:
            if _exists(_join(self.topaz_wd, 'TASPEC.ARC')):
                os.remove(_join(self.topaz_wd, 'TASPEC.ARC'))
            if _exists(_join(self.topaz_wd, 'SUBWTA.ARC')):
                os.remove(_join(self.topaz_wd, 'SUBWTA.ARC'))

        if IS_WINDOWS:
            output = self._run_subprocess(_join(topaz_wd, 'rasfor.exe'), None, verbose)
        else:
            output = self._run_subprocess('./rasfor', None, verbose)

        with open(_join(self.topaz_wd, 'rasfor.log'), 'w') as fp:
            fp.write('\n'.join(output))

        if _pass == 1 and _exists(_join(self.topaz_wd, 'FLOPAT.ARC')) and \
                          _exists(_join(self.topaz_wd, 'FLOVEC.ARC')) and \
                          _exists(_join(self.topaz_wd, 'NETFUL.ARC')) and \
                          _exists(_join(self.topaz_wd, 'RELIEF.ARC')):
            return output

        elif _pass == 2 and _exists(_join(self.topaz_wd, 'TASPEC.ARC')) and \
                            _exists(_join(self.topaz_wd, 'SUBWTA.ARC')) and \
                            _exists(_join(self.topaz_wd, 'RELIEF.ARC')):
            return output

        raise RasforCrashedException(output)

    def _run_rasbin(self, verbose=False):
        topaz_wd = self.topaz_wd
        if IS_WINDOWS:
            output = self._run_subprocess(_join(topaz_wd, 'rasbin.exe'), None, verbose)
        else:
            output = self._run_subprocess('./rasbin', None, verbose)

        with open(_join(self.topaz_wd, 'rasbin.log'), 'w') as fp:
            fp.write('\n'.join(output))

        if output[-1] == 'STOP NORMAL PROGRAM TERMINATION.':
            return output

        raise RasbinCrashedException(output)

    def _run_raspro(self, verbose=False):
        topaz_wd = self.topaz_wd

        if _exists(_join(topaz_wd, 'RASPRO.RPT')):
            os.remove(_join(topaz_wd, 'RASPRO.RPT'))

        topaz_wd = self.topaz_wd
        if IS_WINDOWS:
            output = self._run_subprocess(_join(topaz_wd, 'raspro.exe'), None, verbose)
        else:
            output = self._run_subprocess('./raspro', None, verbose)

        with open(_join(self.topaz_wd, 'raspro.log'), 'w') as fp:
            fp.write('\n'.join(output))

        if _exists(_join(topaz_wd, 'UPAREA.OUT')) and \
           _exists(_join(topaz_wd, 'TSLOPE.OUT')) and \
           _exists(_join(topaz_wd, 'TASPEC.OUT')) and \
           _exists(_join(topaz_wd, 'SUBWTB.OUT')) and \
           _exists(_join(topaz_wd, 'SUBWTA.OUT')) and \
           _exists(_join(topaz_wd, 'SUBBDB.OUT')) and \
           _exists(_join(topaz_wd, 'SUBBDA.OUT')) and \
           _exists(_join(topaz_wd, 'SMOOTH.OUT')) and \
           _exists(_join(topaz_wd, 'SBCT.TAB')) and \
           _exists(_join(topaz_wd, 'RELIEF.OUT')) and \
           _exists(_join(topaz_wd, 'RASPRO.RPT')):
            return output

        # the last line of raspro sometimes gets truncated for an unknown
        # reason. In
        if output[-1] == '***** ENDING PROGRAM RASFOR.':
            return output

        raise RasproCrashedException(output)

    def _polygonize_channels(self):
        subwta_fn = _join(self.topaz_wd, "SUBWTA.ARC")

        assert _exists(subwta_fn)
        src_ds = gdal.Open(subwta_fn)
        srs = osr.SpatialReference()
        srs.ImportFromWkt(src_ds.GetProjectionRef())
        datum, utm_zone, hemisphere = get_utm_zone(srs)
        epsg = utm_srid(utm_zone, hemisphere == 'N')
        srcband = src_ds.GetRasterBand(1)
        ids = set([str(v) for v in np.array(srcband.ReadAsArray(), dtype=np.int).flatten()])
        top_sub_ids = []
        top_chn_ids = []

        for id in ids:
            if id[-1] == '0':
                continue
            if id[-1] == '4':
                top_chn_ids.append(int(id))
            else:
                top_sub_ids.append(int(id))

        translator = WeppTopTranslator(top_chn_ids=top_chn_ids,
                                       top_sub_ids=top_sub_ids)

        dst_fn = _join(self.topaz_wd, 'SUBWTA.JSON')
        assert _exists(dst_fn), "polygonize SUBWTA first"

        # remove the TopazID = 0 feature defining a bounding box
        # and the channels
        with open(dst_fn) as fp:
            js = json.load(fp)

        if "crs" not in js:
            js["crs"] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::%s" % epsg}}

        _features = []
        for f in js['features']:
            topaz_id = str(f['properties']['TopazID'])

            if topaz_id[-1] == '4':
                _features.append(f)

            wepp_id = translator.wepp(top=topaz_id)
            f['properties']['WeppID'] = wepp_id

        js['features'] = _features

        dst_fn2 = _join(self.topaz_wd, 'CHANNELS.JSON')
        with open(dst_fn2, 'w') as fp:
            json.dump(js, fp, allow_nan=False)

        # create a version in WGS 1984 (lng/lat)
        json_to_wgs(dst_fn2)

    def build_channels(self, create_channels=True):
        """
        run topaz to build the channels
        """
        csa, mcl = self.csa, self.mcl

        assert isfloat(csa), f'csa cannot be cast as float ({csa})'
        assert isfloat(mcl), f'mcl cannot be cast as float ({mcl})'

        self._clean_dir()
        self._prep_dir()

        # create additional input files not copied from templates
        self._create_dednm_input()
        self._create_dnmcnt_input(1)

        self._run_dednm()
        time.sleep(0.2)
        self._run_rasfor()
        time.sleep(0.2)
        self.create_prjs()
        self._clean_dir(True)

        if create_channels:
            src_fn = _join(self.topaz_wd, 'NETFUL.ARC')
            dst_fn = _join(self.topaz_wd, "NETFUL.JSON")
            polygonize_netful(src_fn, dst_fn)

    def create_channels_png(self):
        #
        # channel png is not actively used by the WeppCloud interace
        #
        topaz_wd = self.topaz_wd
        assert _exists(_join(topaz_wd, 'NETFUL.ARC'))

        cmd = ['gdalbuildvrt', 'NETFUL.VRT', 'NETFUL.ARC']

        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=topaz_wd)
        p.wait()

        with open(_join(topaz_wd, 'NETFUL.VRT')) as fp:
            vrt = fp.read()

        vrt = vrt.replace('  </VRTRasterBand>', """\
    <ColorTable>
      <Entry c1="0" c2="0" c3="0" c4="0"/>
      <Entry c1="0" c2="0" c3="225" c4="255"/>
    </ColorTable>
  </VRTRasterBand>""")

        with open(_join(topaz_wd, 'NETFUL.VRT'), 'w') as fp:
            fp.write(vrt)

        cmd = ['gdal_translate',
               '-ot', 'Byte',
               '-of', 'PNG',
               '-expand', 'RGBA',
               '-outsize', '200%', '200%',
               'NETFUL.VRT', 'NETFUL.PNG']
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=topaz_wd)
        p.wait()

    def build_subcatchments(self, outlet_px, polygonize_subwta=True):
        """
        run topaz to build the channels and subcatchments
        """
        topaz_wd = self.topaz_wd
        if not exists(_join(topaz_wd, 'NETFUL.OUT')):
            raise Exception('Must build_channels before building subcatchment')

        self.outlet = outlet_px

        # create additional input file specifying pass 2
        self._create_dnmcnt_input(2, outlet_px)

        # sleep seems to prevent rasfor from crashing
        self._run_dednm(_pass=2)
        time.sleep(0.2)
        self._run_raspro()
        time.sleep(0.2)
        self._run_rasfor(_pass=2)
        self.create_prjs()
        self._clean_dir(True)

        if polygonize_subwta:
            subwta_fn = _join(topaz_wd, 'SUBWTA.ARC')
            dst_fn = _join(topaz_wd, 'SUBWTA.JSON')
            dst_fn2 = _join(topaz_wd, 'SUBCATCHMENTS.JSON')
            polygonize_subcatchments(subwta_fn, dst_fn, dst_fn2)

            self._polygonize_channels()

            bound_fn = _join(topaz_wd, "BOUND.ARC")
            dst_fn = _join(topaz_wd, "BOUND.JSON")
            polygonize_bound(bound_fn, dst_fn)
