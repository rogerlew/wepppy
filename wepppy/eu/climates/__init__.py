"""European climate dataset integrations used by WEPPpy.

The :mod:`wepppy.eu.climates` namespace groups loaders for region-specific
datasets (for example the E-OBS gridded observations) that plug into the
standard CLIGEN/WEPP workflow. Packages under this namespace typically expose
helpers that wrap :func:`wepppy.climates.cligen.par_mod` so callers can request
consistent precipitation and temperature statistics without duplicating boiler
plate code.
"""

from . import eobs

__all__ = ("eobs",)
