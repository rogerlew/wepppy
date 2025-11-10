"""High-level helpers for working with the E-OBS climate dataset.

The public entry points in this package wrap :mod:`wepppy.climates.cligen`
utilities so WEPP runs can be parameterized using European observation grids
without having to manage the raw NetCDF assets directly.
"""

from .eobs import eobs_mod

__all__ = ("eobs_mod",)
