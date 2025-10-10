"""
Compatibility module that re-exports the in-repo f_esri helpers.
"""

from wepppy.f_esri import (
    FEsriError,
    c2c_gpkg_to_gdb,
    gpkg_to_gdb,
    has_f_esri,
)

__all__ = [
    "FEsriError",
    "c2c_gpkg_to_gdb",
    "gpkg_to_gdb",
    "has_f_esri",
]
