
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
        lines = [L for L in lines if not L.startswith('#')]

        assert int(lines[1]) == 1, 'expecting 1 ofe'

        azm, fwidth = [float(x) for x in lines[2].split()]

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

        self.fname = fname
        self.hillslope_model = polycurve(distances, slopes)
        self.length = length
        self.nSegments = nSegments
        self.distances = distances
        self.slopes = slopes
        self.azm = azm
        self.fwidth = fwidth

    @property
    def slope_scalar(self):
        x = np.array(self.distances)
        dy = np.array(self.slopes)
        dy_ = np.array([np.mean(dy[i:i + 2]) for i in range(len(dy) - 1)])

        # calculate the positions, assume top of hillslope is 0 y
        y = [0]
        for i in range(len(dy) - 1):
            step = x[i + 1] - x[i]
            y.append(y[-1] - step * dy_[i])

        return -y[-1]

    def _determine_segments(self, d0, dend):
        i = 0
        for d in self.distances:
            if d0 < d < dend:
                i += 1

        return i + 2

    def _find_points(self, d0, dend, nSegments):
        distances = np.linspace(d0, dend, nSegments)
        slopes = self.hillslope_model(distances)

        return distances, slopes

    def segmented_multiple_ofe(self, 
        dst_fn=None, 
        target_length=50,
        apply_buffer=False,
        buffer_length=15,
        min_length=10):

        nSegments = self.nSegments
        distances = self.distances
        slopes = self.slopes
        length = self.length
        azm = self.azm
        fwidth = self.fwidth

        if apply_buffer:
            r_distances = length * (distances[-1] - np.array(distances[::-1]))
            buffer_nsegments = np.argmin(np.abs(r_distances - 
                                                buffer_length)) + 1
            actual_buffer_length = r_distances[buffer_nsegments-1]

            n_mofes = int(round((length - actual_buffer_length) / target_length))
            if n_mofes == 0:
                brks = [0, nSegments-1]

            else:
                brks = [v for v in np.round(
                       np.linspace(0, nSegments-buffer_nsegments, n_mofes+1))]
                brks.append(nSegments-1) 
                brks = np.array(brks, dtype=int)

        else:
            n_mofes = int(round(length / target_length))
            if n_mofes == 0:
                n_mofes = 1

            brks = np.array(np.round(np.linspace(0, nSegments-1, n_mofes+1)), dtype=int) 
       

        n_mofes = len(brks) - 1
 
        s = []
        for i in range(n_mofes):
            i0 = brks[i]
            iend = brks[i+1]

            d0 = distances[i0]
            dend = distances[iend]
            drange = dend - d0

            slplen = length * drange

            if min_length is not None:
                if slplen < min_length:
                    slplen = min_length

            points = iend - i0
            if points == 0:
                continue

            s.append(f'{points} {slplen}')

            _distance_p = (np.array(distances[i0:iend]) - d0) / drange
            _slopes = np.array( slopes[i0:iend])
            s.append(' '.join(f'{_d}, {_s}' for _d, _s in zip(_distance_p, slopes)))

        n_mofes = int(len(s) / 2)

        s = ['97.5',
             str(n_mofes), 
             f'{azm} {fwidth}'] + s

        s = '\n'.join(s)
        if dst_fn is None:
            dst_fn = self.fname.replace('.slp', '.mofe.slp')

        with open(dst_fn, 'w') as pf:
            pf.write(s)

        return n_mofes

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


