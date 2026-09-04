
import importlib
import math
import os
import stat
import tempfile
import warnings
from functools import lru_cache

import numpy as np
from scipy.interpolate import KroghInterpolator


def clip_slope_file_length(src_fn, dst_fn, clip_length):
    clip_length = float(clip_length)
    if not math.isfinite(clip_length) or clip_length <= 0.0:
        raise ValueError('clip_length must be finite and greater than zero')

    with open(src_fn) as fp:
        lines = fp.readlines()
        lines = [L for L in lines if not L.startswith('#')]

    if len(lines) < 5:
        raise ValueError('Malformed slope file: incomplete header or OFE data')

    version_parts = lines[0].split()
    if len(version_parts) != 1:
        raise ValueError('Malformed slope file: invalid version')
    try:
        version = float(version_parts[0])
    except ValueError as exc:
        raise ValueError('Malformed slope file: invalid version') from exc
    if not math.isfinite(version):
        raise ValueError('Malformed slope file: invalid version')

    try:
        n_ofes = int(lines[1])
    except ValueError as exc:
        raise ValueError('Malformed slope file: invalid OFE count') from exc
    if n_ofes < 1:
        raise ValueError('Malformed slope file: expected at least one OFE')
    if len(lines) != 3 + n_ofes * 2:
        raise ValueError('Malformed slope file: unexpected trailing or missing records')

    line2 = lines[2].strip().split()
    expected_header_fields = 3 if version_parts[0].startswith('2023') else 2
    if len(line2) != expected_header_fields:
        raise ValueError('Malformed slope file: invalid geometry header')
    aspect, fwidth = line2[0], line2[1]

    try:
        aspect_value = float(aspect)
        fwidth = float(fwidth)
        z0 = float(line2[2]) if expected_header_fields == 3 else None
    except ValueError as exc:
        raise ValueError('Malformed slope file: invalid geometry header') from exc
    if not math.isfinite(aspect_value) or (z0 is not None and not math.isfinite(z0)):
        raise ValueError('Malformed slope file: invalid geometry header')
    if not math.isfinite(fwidth) or fwidth <= 0.0:
        raise ValueError('Malformed slope file: width must be finite and greater than zero')

    original_total_length = 0.0
    clipped_total_length = 0.0
    clipped_lengths = []
    for ofe_index in range(n_ofes):
        definition_index = 3 + ofe_index * 2
        profile_index = definition_index + 1
        if profile_index >= len(lines):
            raise ValueError(f'Malformed slope file: incomplete OFE {ofe_index + 1}')

        definition = lines[definition_index].split()
        if len(definition) != 2:
            raise ValueError(f'Malformed slope file: invalid OFE {ofe_index + 1} definition')
        try:
            npts = int(definition[0])
            length = float(definition[1])
        except ValueError as exc:
            raise ValueError(f'Malformed slope file: invalid OFE {ofe_index + 1} geometry') from exc
        if npts < 2 or not math.isfinite(length) or length <= 0.0:
            raise ValueError(f'Malformed slope file: invalid OFE {ofe_index + 1} geometry')

        profile_values = lines[profile_index].replace(',', '').split()
        if len(profile_values) != npts * 2:
            raise ValueError(f'Malformed slope file: invalid OFE {ofe_index + 1} profile')
        try:
            profile = [float(value) for value in profile_values]
        except ValueError as exc:
            raise ValueError(f'Malformed slope file: invalid OFE {ofe_index + 1} profile') from exc
        if not all(math.isfinite(value) for value in profile):
            raise ValueError(f'Malformed slope file: non-finite OFE {ofe_index + 1} profile')
        distances = profile[0::2]
        if (
            not math.isclose(distances[0], 0.0, abs_tol=1e-4)
            or not math.isclose(distances[-1], 1.0, abs_tol=1e-3)
            or any(distance < 0.0 or distance > 1.0 for distance in distances)
            or any(left >= right for left, right in zip(distances, distances[1:]))
        ):
            raise ValueError(f'Malformed slope file: invalid normalized distances for OFE {ofe_index + 1}')

        clipped_length = min(length, clip_length)
        original_total_length += length
        clipped_total_length += clipped_length
        clipped_lengths.append((definition_index, definition[0], clipped_length))

    if not math.isfinite(original_total_length) or not math.isfinite(clipped_total_length):
        raise ValueError('Malformed slope file: total OFE length must be finite')
    if original_total_length <= 0.0 or clipped_total_length <= 0.0:
        raise ValueError('Malformed slope file: total OFE length must be greater than zero')

    width_scale = original_total_length / clipped_total_length
    clipped_fwidth = fwidth * width_scale
    if not math.isfinite(width_scale) or not math.isfinite(clipped_fwidth):
        raise ValueError('Malformed slope file: clipped width must be finite')
    fwidth = clipped_fwidth

    line2[0] = str(aspect)
    line2[1] = str(fwidth)
    lines[2] = ' '.join(line2) + '\n'
    for definition_index, npts_text, clipped_length in clipped_lengths:
        lines[definition_index] = f'{npts_text} {clipped_length}\n'

    dst_dir = os.path.dirname(os.path.abspath(dst_fn))
    os.makedirs(dst_dir, exist_ok=True)
    source_mode = stat.S_IMODE(os.stat(src_fn).st_mode)
    tmp_fn = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dst_dir,
            prefix=f'.{os.path.basename(dst_fn)}.',
            suffix='.tmp',
            delete=False,
        ) as fp:
            tmp_fn = fp.name
            os.fchmod(fp.fileno(), source_mode)
            fp.writelines(lines)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp_fn, dst_fn)
        tmp_fn = None
    finally:
        if tmp_fn is not None:
            try:
                os.unlink(tmp_fn)
            except FileNotFoundError:
                pass


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


@lru_cache(maxsize=1)
def _load_wepppyo3_mofe_segmenter():
    try:
        module = importlib.import_module("wepppyo3.wepp_interchange")
    except ImportError as exc:
        raise RuntimeError(
            "MOFE segmentation requires `wepppyo3.wepp_interchange`; install/update wepppyo3 to continue."
        ) from exc

    segmenter = getattr(module, "segment_single_ofe_slope", None)
    if not callable(segmenter):
        raise RuntimeError(
            "MOFE segmentation requires `wepppyo3.wepp_interchange.segment_single_ofe_slope`."
        )

    return segmenter


@lru_cache(maxsize=1)
def _load_wepppyo3_breakpoint_mofe_segmenter():
    try:
        module = importlib.import_module("wepppyo3.wepp_interchange")
    except ImportError as exc:
        raise RuntimeError(
            "Explicit-breakpoint MOFE segmentation requires `wepppyo3.wepp_interchange`; "
            "install/update wepppyo3 to continue."
        ) from exc

    segmenter = getattr(module, "segment_single_ofe_slope_at_breakpoints", None)
    if not callable(segmenter):
        raise RuntimeError(
            "Explicit-breakpoint MOFE segmentation requires "
            "`wepppyo3.wepp_interchange.segment_single_ofe_slope_at_breakpoints`."
        )

    return segmenter


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
        segmenter = _load_wepppyo3_mofe_segmenter()
        return int(
            segmenter(
                self.fname,
                dst_fn=dst_fn,
                target_length=float(target_length),
                apply_buffer=bool(apply_buffer),
                buffer_length=float(buffer_length),
                min_length=float(min_length),
                max_ofes=int(max_ofes),
            )
        )

    def segmented_multiple_ofe_at_breakpoints(
        self,
        breakpoints,
        dst_fn=None,
        target_width=None,
    ):
        """Segment this slope at explicit normalized downslope breakpoints."""
        segmenter = _load_wepppyo3_breakpoint_mofe_segmenter()
        kwargs = {"dst_fn": dst_fn}
        if target_width is not None:
            kwargs["target_width"] = float(target_width)
        return int(segmenter(self.fname, breakpoints, **kwargs))

    def segmented_multiple_ofe_legacy(self,
        dst_fn=None,
        target_length=50,
        apply_buffer=False,
        buffer_length=15,
        min_length=10,
        max_ofes=19):
        warnings.warn(
            "SlopeFile.segmented_multiple_ofe_legacy is deprecated and kept only for parity/benchmark validation; "
            "use the default wepppyo3-backed segmented_multiple_ofe production path.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._segmented_multiple_ofe_python(
            dst_fn=dst_fn,
            target_length=target_length,
            apply_buffer=apply_buffer,
            buffer_length=buffer_length,
            min_length=min_length,
            max_ofes=max_ofes,
        )

    def _segmented_multiple_ofe_python(self,
        dst_fn=None,
        target_length=50,
        apply_buffer=False,
        buffer_length=15,
        min_length=10,
        max_ofes=19):
        max_ofes = int(max_ofes)

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
            _length = (dend - d0) * length
            _distance_p = (_distance_p - d0) / (dend - d0)
            _profile = []
            for _d, _s in zip(_distance_p, _slopes):
                _d_fmt = f'{_d:.4f}'
                _s_fmt = f'{_s:.4f}'
                if _profile and _profile[-1][0] == _d_fmt:
                    # Keep the downstream point for this rounded-distance bucket.
                    # This avoids stretching the upstream slope across the segment
                    # when adjacent raw points collapse to the same x after formatting.
                    _profile[-1] = (_d_fmt, _s_fmt)
                    continue
                _profile.append((_d_fmt, _s_fmt))

            _npts = len(_profile)
            s.append(f'{_npts} {_length:.2f}')
#            s.append('# ' + ' '.join(f'{_d:.4f}, {_s:.4f}' for _d, _s in zip(_distance_p, _slopes)))

            s.append('  ' + ' '.join(f'{_d}, {_s}' for _d, _s in _profile))

        s = ['97.5',
             str(n_mofes),
             f'{azm} {fwidth}'] + s

        s = '\n'.join(s)
        if dst_fn is None:
            dst_fn = self.fname.replace('.slp', '.mofe.slp')

        with open(dst_fn, 'w') as pf:
            pf.write(s)

        return n_mofes
