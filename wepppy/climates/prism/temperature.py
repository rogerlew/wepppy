"""ADR-0092: repair only temperature inversions introduced by spatialization."""
import logging
from pathlib import Path

import numpy as np


def validate_source_temperatures(tmax, tmin, *normals):
    """Source defects must not be mistaken for introduced spatial inversions."""
    if not all(np.isfinite(np.asarray(values, dtype=float)).all()
               for values in (tmax, tmin, *normals)):
        raise ValueError('PRISM source temperatures and normals must be finite')
    if np.any(np.asarray(tmin) > np.asarray(tmax)):
        raise ValueError('PRISM source Tmin exceeds Tmax')


def repair_temperature_ordering(tmax, tmin):
    """Return repaired copies and pre-serialization correction diagnostics."""
    upper, lower = np.array(tmax, dtype=float), np.array(tmin, dtype=float)
    if upper.shape != lower.shape or not np.isfinite(upper).all() or not np.isfinite(lower).all():
        raise ValueError('PRISM adjusted temperatures must have matching shapes and be finite')
    inverted = lower > upper
    with np.errstate(over="ignore"):
        maximum = float(np.max(lower[inverted] - upper[inverted])) if inverted.any() else 0.0
    if not np.isfinite(maximum):
        raise ValueError('PRISM inversion magnitude must be finite')
    maximum_adjustment = 0.0
    if inverted.any():
        midpoint = upper[inverted] / 2 + lower[inverted] / 2
        maximum_adjustment = float(max(np.max(np.abs(midpoint - upper[inverted])),
                                       np.max(np.abs(midpoint - lower[inverted]))))
        upper[inverted] = midpoint
        lower[inverted] = midpoint
    return upper, lower, dict(method='midpoint_if_inverted', corrected_days=int(inverted.sum()),
                             maximum_inversion_c=maximum, maximum_adjustment_c=maximum_adjustment)


def start_temperature_revision(source, output):
    """Retain an incomplete diagnostic beside the normal output artifact."""
    path = Path(str(output) + '.temperature-ordering.log')
    path.write_text(f'status=working source={str(source)!r} output={str(output)!r}\n')
    return path


def complete_temperature_revision(path, diagnostics):
    """Call only after the climate writer/readback has succeeded."""
    message = 'status=complete ' + ' '.join(f'{key}={diagnostics[key]}' for key in (
        'method', 'corrected_days', 'maximum_inversion_c', 'maximum_adjustment_c'))
    with Path(path).open('a') as stream:
        stream.write(message + '\n')
    logging.getLogger(__name__).info('%s %s', path, message)
