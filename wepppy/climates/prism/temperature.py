"""ADR-0092: repair only temperature inversions introduced by spatialization."""
import logging

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


def log_temperature_revision(source, output, diagnostics):
    logging.getLogger(__name__).info(
        'status=complete source=%s output=%s method=%s corrected_days=%s '
        'maximum_inversion_c=%s maximum_adjustment_c=%s',
        source, output, diagnostics['method'], diagnostics['corrected_days'],
        diagnostics['maximum_inversion_c'], diagnostics['maximum_adjustment_c'],
    )
