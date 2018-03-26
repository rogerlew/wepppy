import numpy as np
from scipy import interpolate

from osgeo import gdal
from osgeo.gdalconst import *

class PlotFile(object):
    def __init__(self, fn):

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        lines = ' '.join(lines[4:])
        data = np.fromstring(lines, sep=' ')
        data = data.reshape((100, 3)).T

        self.distance_downslope = data[0, :]
        self.distance_p = data[0, :] / data[0, -1]
        self.elevation = data[1, :]
        self.soil_loss = data[2, :]

    def interpolate(self, d):
        f = interpolate.interp1d([0.0] + self.distance_p.tolist(),
                                 [0.0] + self.soil_loss.tolist())
        return f(d)


if __name__ == "__main__":
    from pprint import pprint
    fn = '/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/flow_22_1.plot.dat'
    PlotFile(fn)
