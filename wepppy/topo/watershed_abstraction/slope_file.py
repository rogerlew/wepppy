
import numpy as np
from scipy.interpolate import KroghInterpolator


def clip_slope_file_length(src_fn, dst_fn, clip_length):
    with open(src_fn) as fp:
        lines = fp.readlines()
        lines = [L for L in lines if not L.startswith('#')]

    line2 = lines[2].strip().split()
    aspect, fwidth = line2[0], line2[1]
    npts, length = lines[3].split()

    fwidth = float(fwidth)
    length = float(length)
    area = fwidth * length

    if length > clip_length:
        length = clip_length
        fwidth = area / length

    line2[0] = str(aspect)
    line2[1] = str(fwidth)
    lines[2] = ' '.join(line2) + '\n'
    lines[3] = f'{npts} {length}\n'

    with open(dst_fn, 'w') as fp:
        fp.writelines(lines)


def mofe_distance_fractions(fname):
    with open(fname) as fp:
        lines = fp.readlines()
        lines = [L for L in lines if not L.startswith('#')]

    n_ofes = int(lines[1])

    lengths = [0.0]
    tot_length = 0.0
    for i in range(n_ofes):
        ofe_def = lines[3 + i * 2]
        npts, length = ofe_def.split()
        length = float(length)
        lengths.append(length)
        tot_length += length

    return np.cumsum(lengths) / tot_length


class SlopeFile(object):
    def __init__(self, fname, z0=10000):
        with open(fname) as fp:
            lines = fp.readlines()
            lines = [L for L in lines if not L.startswith('#')]

        n_ofes = int(lines[1])
        assert n_ofes == 1, 'expecting 1 ofe'

        if lines[0].startswith('2023'):
            azm, fwidth, z0 = [float(x) for x in lines[2].split()]
        else:
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

        distances_m = [d * length for d in distances]
        relative_elevs = [z0]
        for i in range(1, nSegments):
            dx = distances_m[i] - distances_m[i - 1]
            relative_elevs.append(relative_elevs[-1] + dx * slopes[i - 1])

        self.fname = fname
        self.length = length
        self.resolution = np.min(np.diff(distances))
        self.nSegments = nSegments
        self.distances = np.array(distances)
        self.slopes = np.array(slopes)
        self.azm = azm
        self.fwidth = fwidth
        self.relative_elevs = np.array(relative_elevs)

    def interp_slope(self, d):
        idx = np.searchsorted(self.distances, np.clip(0.0, 1.0, d))
        return self.slopes[idx]

    def slope_of_segment(self, d0=0.0, dend=1.0):
        x0 = d0 * self.length
        y0 = np.interp(x0, self.distances, self.relative_elevs)

        xend = dend * self.length
        yend = np.interp(xend, self.distances, self.relative_elevs)

        return (yend - y0) / (xend - x0)

    @property
    def slope_scalar(self):
        return self.slope_of_segment()

    def segmented_multiple_ofe(self,
        dst_fn=None,
        target_length=50,
        apply_buffer=False,
        buffer_length=15,
        min_length=10,
        max_ofes=19):

        length = self.length
        azm = self.azm
        fwidth = self.fwidth

        d_d = [0.0] # fraction of ofe segment
        n_mofes = None
        if apply_buffer:
            if length <= buffer_length:
                n_mofes = 1
                buffer_length = length
            elif length <= buffer_length + target_length:
                n_mofes = 2
            else:
                n_mofes = int(round((length - buffer_length) / target_length)) + 1
                assert n_mofes >= 2

            n_buffer = 1
            d_buffer = buffer_length / length
            d_d.append(d_buffer)

        else:
            n_mofes = int(round(length / target_length))
            buffer_length = 0.0
            n_buffer = 0
            d_buffer = 0.0

        if n_mofes == 0:
            n_mofes = 1

        if n_mofes > max_ofes:
            n_mofes = max_ofes

        if n_mofes - n_buffer == 0:
            ofe_length = 0.0
        else:
            ofe_length = (length - buffer_length) / (n_mofes - n_buffer)

        # add non-buffer segments to d_d
        _d_d = ofe_length / length
        for i in range(n_mofes - n_buffer):
            d_d.append(_d_d)

        d_d = np.cumsum(d_d)

        assert abs(d_d[-1] - 1.0) < 0.0001, (d_d, dst_fn, n_mofes, self.fname)
        assert len(d_d) == n_mofes + 1, (len(d_d), n_mofes + 1)

        s = []
        for i in range(n_mofes):
            d0 = d_d[i]
            dend = d_d[i+1]

            _distance_p = [d0]
            for _d in self.distances:
                if d0 < _d < dend:
                    _distance_p.append(_d)

            if round(_distance_p[-1], 4) < round(dend, 4):
                _distance_p.append(dend)

            _slopes = self.interp_slope(_distance_p)

            _npts = len(_slopes)
            _length = (dend - d0) * length
            s.append(f'{_npts} {_length:.2f}')
#            s.append('# ' + ' '.join(f'{_d:.4f}, {_s:.4f}' for _d, _s in zip(_distance_p, _slopes)))

            _distance_p = (_distance_p - d0) / (dend - d0)
            _profile = []
            _d_old = -1.0
            for _d, _s in zip(_distance_p, _slopes):
                assert _d > _d_old, (_d, _d_old, _distance_p, _slopes)
                _d_old = _d
                _profile.append(f'{_d:.4f}, {_s:.4f}')

            s.append('  ' + ' '.join(_profile))

        s = ['97.5',
             str(n_mofes),
             f'{azm} {fwidth}'] + s

        s = '\n'.join(s)
        if dst_fn is None:
            dst_fn = self.fname.replace('.slp', '.mofe.slp')

        with open(dst_fn, 'w') as pf:
            pf.write(s)

        return n_mofes
