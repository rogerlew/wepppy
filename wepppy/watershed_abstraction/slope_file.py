
import numpy as np
from scipy.interpolate import KroghInterpolator


def polycurve(x, dy):
    #
    # Calculate the y positions from the derivatives
    #

    # for each segment calculate the average gradient from the derivatives at each point
    dy = np.array(dy)
    dy_ = np.array([np.mean(dy[i:i + 2]) for i in range(len(dy) - 1)])

    # calculate the positions, assume top of hillslope is 0 y
    y = [0]
    for i in range(len(dy) - 1):
        step = x[i + 1] - x[i]
        y.append(y[-1] - step * dy_[i])
    y = np.array(y)

    assert len(dy) == len(y), '%i, %i, %i' % (len(x), len(dy), len(y))
    assert dy.shape == y.shape, '%i, %i' % (dy.shape, y.shape)

    xi_k = np.repeat(x, 2)
    yi_k = np.ravel(np.dstack((y, -1 * dy)))

    #
    # Return the model
    #
    return KroghInterpolator(xi_k, yi_k)


class SlopeFile(object):
    def __init__(self, fname):
        fid = open(fname)
        lines = fid.readlines()

        assert int(lines[1]), 'expecting 1 ofe'

        nSegments, length = lines[3].split()
        nSegments = int(nSegments)
        length = float(length)

        distances, slopes = [], []

        row = lines[4].replace(',', '').split()
        row = [float(v) for v in row]
        assert len(row) == nSegments * 2, row
        for i in range(nSegments):
            distances.append(row[i * 2])
            slopes.append(row[i * 2 + 1])

        fid.close()

        self.hillslope_model = polycurve(distances, slopes)
        self.length = length
        self.nSegments = nSegments
        self.distances = distances
        self.slopes = slopes

    def _determine_segments(self, d0, dend):
        i = 0
        for d in self.distances:
            print(d0, d, dend)
            if d0 < d < dend:
                i += 1

        return i + 2

    def _find_points(self, d0, dend, nSegments):
        distances = np.linspace(d0, dend, nSegments)
        slopes = self.hillslope_model(distances)

        return distances, slopes

    def make_multiple_ofe(self, breaks, normalized=True):
        if not normalized:
            breaks = breaks/self.length

        for brk in breaks:
            assert brk > 0.0
            assert brk < 1.0

        ofes = []

        d0 = 0.0
        dend = None
        for brk in breaks:
            dend = brk
            nSegments = self._determine_segments(d0, dend)
            ofes.append(self._find_points(d0, dend, nSegments))

            d0 = brk

        dend = 1.0
        nSegments = self._determine_segments(d0, dend)
        ofes.append(self._find_points(d0, dend, nSegments))

        print(ofes)


