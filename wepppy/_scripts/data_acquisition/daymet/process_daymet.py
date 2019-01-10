import os
import sys
import shutil
import math
import warnings
from time import time, sleep

from copy import deepcopy

import netCDF4
import numpy as np
from numpy import logical_not as _not
from numpy import logical_and as _and

from osgeo import gdal, osr
from osgeo.gdalconst import *


def determine_month(day):
    """
    returns 0-indexed month given a 0-indexed day
    """
    d = int(math.ceil(day)) % 365

    for i, m in enumerate([31, 59, 90, 120, 151, 181,
                           212, 243, 273, 304, 334, 365]):
        if d < m:
            return i


def dump_tif(data, fname, wkt, transform, mask=None, nodata=None):
    if hasattr(data, "mask"):
        mask = data.mask

    elif mask is not False and mask is not None:
        assert mask.shape == data.shape
        data[np.where(mask)] = nodata

    data = np.array(data)

    n, m = data.shape
    # initialize raster
    driver = gdal.GetDriverByName("GTiff")
    dst = driver.Create(fname, n, m,
                        1, GDT_Float32)

    dst.SetProjection(wkt)
    dst.SetGeoTransform(transform)
    band = dst.GetRasterBand(1)
    band.WriteArray(data.T)

    if nodata != None:
        band.SetNoDataValue(float(nodata))

    dst = None  # Writes and closes file


def dump_npy(data, npy):
    """
    Save {data} to npy file
    """
    npytmp = npy + '.tmp'
    if os.path.exists(npy):
        if os.path.exists(npy):
            shutil.move(npy, npytmp)

    np.save(npy, np.array(data))
    shutil.rmtree(npytmp)


class RunningPrecipNumWet:
    """
    x = np.array([[0,0],
                  [0,0], # D -> D
                  [3,3], # D -> W
                  [3,3], # W -> W
                  [0,0]  # W - D
                 ])

    y = x > 0
    pprint( y)

    markov = RunningPrecipMarkov((2,))

    for i in xrange(x.shape[0]):
        print i, y[i]
        markov.push(y[i])

    markov.brk()
    for i in xrange(x.shape[0]):
        print i, y[i]
        markov.push(y[i])

    print 'dd', markov.p_dd()
    print 'dw', markov.p_dw()
    print 'ww', markov.p_ww()
    print 'wd', markov.p_wd()
    """

    def __init__(self, shape):
        self.shape = shape
        self.n = 0
        self._nwds = np.zeros(shape, np.int32)

    def push(self, x):
        shape = self.shape
        assert shape == x.shape
        self.n += 1
        self._nwds += x > 0.0

    def nwds(self):
        return np.array(self._nwds, dtype=np.float32) / (float(self.n))


class RunningPrecipMarkov:
    """
    x = np.array([[0,0],
                  [0,0], # D -> D
                  [3,3], # D -> W
                  [3,3], # W -> W
                  [0,0]  # W - D
                 ])

    y = x > 0
    pprint( y)

    markov = RunningPrecipMarkov((2,))

    for i in xrange(x.shape[0]):
        print i, y[i]
        markov.push(y[i])

    markov.brk()
    for i in xrange(x.shape[0]):
        print i, y[i]
        markov.push(y[i])

    print 'dd', markov.p_dd()
    print 'dw', markov.p_dw()
    print 'ww', markov.p_ww()
    print 'wd', markov.p_wd()
    """

    def __init__(self, shape):
        self.shape = shape

        self.n = 0
        self.last = None
        self.dd = np.zeros(shape, np.int32)
        self.dw = np.zeros(shape, np.int32)
        self.ww = np.zeros(shape, np.int32)
        self.wd = np.zeros(shape, np.int32)

    def brk(self):
        self.last = None
        self.n -= 1

    def push(self, x):
        shape = self.shape
        last = self.last
        assert shape == x.shape
        self.n += 1

        if last is not None:
            self.dd += _and(_not(last), _not(x))
            self.dw += _and(_not(last), x)
            self.ww += _and(last, x)
            self.wd += _and(last, _not(x))

        self.last = x

    def p_dd(self):
        return np.array(self.dd, dtype=np.float32) / (float(self.n) - 1.0)

    def p_dw(self):
        return np.array(self.dw, dtype=np.float32) / (float(self.n) - 1.0)

    def p_ww(self):
        return np.array(self.ww, dtype=np.float32) / (float(self.n) - 1.0)

    def p_wd(self):
        return np.array(self.wd, dtype=np.float32) / (float(self.n) - 1.0)


class _RunningSkew:
    """
    skewness sample estimate is based on the
    cumulants calculated from the raw moments.

    G_1 = \frac{\sqrt{N(N-1)}}{N-2} \frac{k_3}{k_2^{3/2}},
    where {k_3} and {k_2} are the 3rd and 2nd order cumulants
    respectively.

    see also:
        http://mathworld.wolfram.com/Skewness.html
        http://mathworld.wolfram.com/RawMoment.html
        http://mathworld.wolfram.com/Cumulant.html
        http://www.tc3.edu/instruct/sbrown/stat/shape.htm#SkewnessCompute
    """

    def __init__(self, shape):
        self.s1 = np.zeros(shape)
        self.s2 = np.zeros(shape)
        self.s3 = np.zeros(shape)
        self.n = 0

    def push(self, value):
        v = deepcopy(value)
        self.s1 += v
        v *= deepcopy(value)
        self.s2 += v
        v *= value[:]
        self.s3 += v
        self.n += 1

    def __call__(self):
        if self.n < 3:
            raise Exception("Can't calculate skew with less than 3 obs")

        n = float(self.n)

        # calculate unbiased raw moments
        m1 = self.s1 / self.n
        m2 = self.s2 / self.n
        m3 = self.s3 / self.n

        # from the raw moments calculate cumulants
        k1 = m1
        k2 = m2 - np.power(m1, 2.0)
        k3 = 2.0 * np.power(m1, 3.0) - 3.0 * m1 * m2 + m3

        num = math.sqrt(n * (n - 1.0))
        num /= (n - 2.0)
        num *= k3

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            den = np.power(k2, 1.5)
            return num / den


class RunningStats:
    # Based on http://www.johndcook.com/standard_deviation.html
    # extended to 2d numpy arrays by Roger Lew

    def __init__(self, shape):
        self.shape = shape

        self.n = 0
        self.old_m = np.zeros(shape)
        self.new_m = np.zeros(shape)
        self.old_s = np.zeros(shape)
        self.new_s = np.zeros(shape)

        self._skew = _RunningSkew(shape)

    def clear(self):
        self.n = 0

    def push(self, x):
        shape = self.shape

        assert shape == x.shape

        self.n += 1

        if self.n == 1:
            self.old_m = self.new_m = x
            self.old_s = np.zeros(shape)
        else:
            self.new_m = self.old_m + (x - self.old_m) / self.n
            self.new_s = self.old_s + (x - self.old_m) * (x - self.new_m)

            self.old_m = self.new_m[:]
            self.old_s = self.new_s[:]

        self._skew.push(x)

    def mean(self):
        return self.new_m if self.n else np.zeros(self.shape)

    def var(self):
        return self.new_s / (self.n - 1.0) if self.n > 1 else np.zeros(self.shape)

    def std(self):
        return np.sqrt(self.var())

    def skew(self):
        return self._skew()


def process(args):
    t0 = time()

    month, varname, pp_stats, pp_markov, pp_nwd = args

    assert month in range(12)
    assert pp_markov in [0, 1]

    # load all of the data files as multifile dataset
    ds = netCDF4.MFDataset('daymet*.nc4')

    # determine transform
    v = ds.variables['lambert_conformal_conic']
    x = [ds.variables['x'][0],
         ds.variables['x'][1],
         ds.variables['x'][-1]]
    y = [ds.variables['y'][0],
         ds.variables['y'][1],
         ds.variables['y'][-1]]
    transform = [x[0], x[1] - x[0], 0.0, y[0], 0.0, y[1] - y[0]]

    # generated by pycrs using parameters from nc4
    wkt = """\
PROJCS["Unknown", 
    GEOGCS["Unknown", 
        DATUM["Unknown", 
            SPHEROID["Unknown", 6378137.0, 298.257223985]], 
        PRIMEM["Greenwich", 0], 
        UNIT["Degree", 0.0174532925199], 
        AXIS["Lon", EAST], 
        AXIS["Lat", NORTH]], 
    PROJECTION["Lambert_Conformal_Conic_2SP"], 
    PARAMETER["Central_Meridian", -100.0], 
    PARAMETER["Latitude_Of_Origin", 42.5], 
    PARAMETER["Standard_Parallel_1", 25.0], 
    PARAMETER["Standard_Parallel_2", 60.0], 
    UNIT["Meter", 1.0], 
    AXIS["X", EAST], 
    AXIS["Y", NORTH]]"""

    # pull out variable of interest
    var = ds.variables[varname]
    shape = (var.shape[1], var.shape[2])

    # determine number of days
    ndays = ds.variables['time'].shape[0]
    assert ndays % 365 == 0

    if pp_stats:
        running = RunningStats(shape)

    if pp_markov:
        running_pp = RunningPrecipMarkov(shape)

    if pp_nwd:
        running_nwd = RunningPrecipNumWet(shape)

    # loop over the days
    fn = '{x}/%s_{x}_%02i.tif' % (varname, month + 1)
    for i in xrange(ndays):

        # record daily values
        data = var[i, :, :]
        mask = data.mask

        # write condition
        if i > 0 and i % 365 == 0:
            elapsed = time() - t0
            remaining = i / elapsed * (ndays - i)
            print
            '\nelapsed', elapsed, ' remaining ', remaining

            if pp_stats:
                dump_tif(running.mean().T, fn.format(x='mean'),
                         wkt, transform, nodata=var.missing_value)
                dump_tif(running.std().T, fn.format(x='std'),
                         wkt, transform, nodata=var.missing_value)
                dump_tif(running.skew().T, fn.format(x='skew'),
                         wkt, transform, nodata=var.missing_value)

            if pp_markov:
                dump_tif(running_pp.p_ww().T, fn.format(x='pww'),
                         wkt, transform, mask=mask.T, nodata=var.missing_value)
                dump_tif(running_pp.p_wd().T, fn.format(x='pwd'),
                         wkt, transform, mask=mask.T, nodata=var.missing_value)
                running_pp.brk()

            if pp_nwd:
                dump_tif(running_nwd.nwds().T, fn.format(x='nwds'),
                         wkt, transform, mask=mask.T, nodata=var.missing_value)

        # if day isn't for the month we are processing we can continue
        if determine_month(i) != month:
            continue

        _min, _max = np.min(data), np.max(data)
        if _max > 1000:
            print
            i, _min, _max

        sys.stdout.write('0123456789ABCDEF'[month])

        if pp_stats:
            running.push(data)

        if pp_markov:
            running_pp.push(data)

        if pp_nwd:
            running_nwd.push(data)


if __name__ == "__main__":
    """

    from pprint import pprint
    from numpy import random

    shape = (10,10)
    runner = RunningStats(shape)

    for i in xrange(1000):
        data = random.normal(50, 2.5, shape)
        runner.push(data)

    pprint( runner.mean() )
    pprint( runner.std() )
    pprint( runner.skew() )

    x = np.array([[0,0],
                  [0,0], # D -> D
                  [3,3], # D -> W
                  [3,3], # W -> W
                  [0,0]  # W - D
                 ])

    y = x > 0
    pprint( y)

    markov = RunningPrecipMarkov((2,))

    for i in xrange(x.shape[0]):
        print i, y[i]
        markov.push(y[i])

    markov.brk()
    for i in xrange(x.shape[0]):
        print i, y[i]
        markov.push(y[i])

    print 'dd', markov.p_dd()
    print 'dw', markov.p_dw()
    print 'ww', markov.p_ww()
    print 'wd', markov.p_wd()
    """
    from multiprocessing import Pool
    from optparse import OptionParser

    parser = OptionParser(usage="usage: [options] varname")
    parser.add_option("-n", "--ncpu", type="int", dest="ncpu", default=1,
                      help="cpu pool size")
    parser.add_option("-s", "--pp_stats",
                      action="store_true", dest="pp_stats", default=False,
                      help="calculate PP stats")
    parser.add_option("-m", "--pp_markov",
                      action="store_true", dest="pp_markov", default=False,
                      help="calculate PP transitions")
    parser.add_option("-w", "--pp_nwd",
                      action="store_true", dest="pp_nwd", default=False,
                      help="calculate PP num wet days")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit()

    varname = args[0]

    print(options.ncpu, options.pp_markov, varname)

    xs = []
    if options.pp_stats:
        xs.extend(['mean', 'std', 'skew'])
    if options.pp_markov:
        xs.extend(['pwd', 'pww'])
    if options.pp_nwd:
        xs.extend(['nwds'])

    for x in xs:
        if os.path.exists(x):
            shutil.rmtree(x)
            sleep(1)
        os.mkdir(x)

    #    process([0, varname, options.pp_markov])
    pool = Pool(processes=options.ncpu)
    pool.map(process, [[i, varname, options.pp_stats, options.pp_markov, options.pp_nwd] for i in range(12)])