"""Accessors for the EU SoilHydroGrids rasters (interpolated soil attributes)."""

from __future__ import annotations

from os.path import exists as _exists
from os.path import join as _join
from typing import Final

from wepppy.all_your_base.geo import RasterDatasetInterpolator

_EUHYDROGRIDS_DIR: Final[str] = "/geodata/eu/eusoilhydrogrids"


class SoilHydroGrids:
    """Thin wrapper around the SoilHydroGrids GeoTIFF stack published by ESDAC."""

    def __init__(self) -> None:
        self.datasets: tuple[str, ...] = ("THS", "KS", "WP", "FC")
        self.depths: tuple[str, ...] = ("sl1", "sl2", "sl3", "sl4", "sl5", "sl6", "sl7")
        self.depth_offsets_mm: tuple[int, ...] = (0, 5, 15, 30, 60, 100, 200)

        for depth in self.depths:
            for dataset in self.datasets:
                fn = self.get_fn(dataset, depth)
                if not _exists(fn):
                    raise FileNotFoundError(fn)

    def query(self, lng: float, lat: float, dataset: str) -> dict[str, tuple[int, float | None]]:
        """Sample a SoilHydroGrids layer for each standard depth."""
        data: dict[str, tuple[int, float | None]] = {}
        for code, depth in zip(self.depths, self.depth_offsets_mm):
            rdi = RasterDatasetInterpolator(self.get_fn(dataset, code))
            data[code] = (depth, rdi.get_location_info(lng, lat, method="near"))

        return data

    @staticmethod
    def get_fn(dataset: str, depth: str) -> str:
        """Build the on-disk path for a SoilHydroGrids raster tile."""
        return _join(
            _EUHYDROGRIDS_DIR,
            f"{dataset}_{depth}/{dataset}_{depth}.tif",
        )
