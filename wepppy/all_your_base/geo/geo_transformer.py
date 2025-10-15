from typing import Any
import os
import pyproj


class GeoTransformer:
    """
    Transforms coordinates between different CRS using the modern pyproj API.
    This version is cross-platform, highly efficient, and robust.
    """
    def __init__(self, src_proj4=None, src_epsg=None, dst_proj4=None, dst_epsg=None):
        assert src_proj4 or src_epsg, "Must provide a source CRS"
        assert dst_proj4 or dst_epsg, "Must provide a destination CRS"

        # 1. Let pyproj parse the source and destination CRS definitions.
        # It can intelligently handle EPSG codes, proj4 strings, and other formats.
        src_crs = src_proj4 or f"EPSG:{src_epsg}"
        dst_crs = dst_proj4 or f"EPSG:{dst_epsg}"

        # 2. Create transformer objects once during initialization.
        # `always_xy=True` ensures the input and output order is always (x, y),
        # preventing common longitude/latitude mix-up errors.
        self.transformer = pyproj.Transformer.from_crs(
            pyproj.CRS(src_crs),
            pyproj.CRS(dst_crs),
            always_xy=True
        )
        self.reverse_transformer = pyproj.Transformer.from_crs(
            pyproj.CRS(dst_crs),
            pyproj.CRS(src_crs),
            always_xy=True
        )

    def transform(self, x, y):
        """
        Transforms coordinates from the source to the destination CRS.
        Handles both single points (scalars) and arrays of points efficiently.
        """
        return self.transformer.transform(x, y)

    def reverse(self, x, y):
        """
        Transforms coordinates from the destination back to the source CRS.
        """
        return self.reverse_transformer.transform(x, y)


if __name__ == "__main__":
    _dst_proj4 = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'
    _wgs_2_lcc = GeoTransformer(src_epsg=4326, dst_proj4=_dst_proj4)
    e, n = _wgs_2_lcc.transform(-117.0, 47.0)
    print(e, n)
