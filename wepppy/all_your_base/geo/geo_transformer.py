"""Coordinate transformation utilities built around :mod:`pyproj`."""

from __future__ import annotations

from typing import Any, Tuple

import pyproj

__all__ = ['GeoTransformer']


class GeoTransformer:
    """Bidirectional transformer between two coordinate reference systems."""

    __slots__ = ('transformer', 'reverse_transformer')

    def __init__(
        self,
        src_proj4: str | None = None,
        src_epsg: int | None = None,
        dst_proj4: str | None = None,
        dst_epsg: int | None = None,
    ) -> None:
        if not (src_proj4 or src_epsg):
            raise ValueError('A source CRS must be supplied.')
        if not (dst_proj4 or dst_epsg):
            raise ValueError('A destination CRS must be supplied.')

        src_crs = src_proj4 or f'EPSG:{src_epsg}'
        dst_crs = dst_proj4 or f'EPSG:{dst_epsg}'

        self.transformer = pyproj.Transformer.from_crs(
            pyproj.CRS(src_crs),
            pyproj.CRS(dst_crs),
            always_xy=True,
        )
        self.reverse_transformer = pyproj.Transformer.from_crs(
            pyproj.CRS(dst_crs),
            pyproj.CRS(src_crs),
            always_xy=True,
        )

    def transform(self, x: Any, y: Any) -> Tuple[Any, Any]:
        """Transform coordinates from the source CRS into the destination CRS."""
        tx, ty = self.transformer.transform(x, y)
        return tx, ty

    def reverse(self, x: Any, y: Any) -> Tuple[Any, Any]:
        """Transform coordinates from the destination CRS back to the source CRS."""
        rx, ry = self.reverse_transformer.transform(x, y)
        return rx, ry
