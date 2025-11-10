"""Entry points for WEPP Cloud auxiliary web services.

The :mod:`wepppy.webservices` package hosts small Flask/FastAPI applications
that expose climate, raster, and analytics helpers (for example
``webservices.cligen`` for CLIGEN files and ``webservices.wmesque2`` for raster
tiling). Modules are intentionally separated so each service can be deployed on
its own timeline or disabled entirely inside a given stack.

Only lightweight metadata lives here; importing submodules should be done
explicitly to keep import costs predictable.
"""

__all__ = [
    "cligen",
    "elevationquery",
    "ecoregion_us",
    "geeapi",
    "inmemoryzip",
    "metquery",
    "rq_dashboard",
    "wmesque",
    "wmesque2",
]
