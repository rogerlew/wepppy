from __future__ import annotations

"""Rasterization utilities for SSURGO-derived attributes."""

import json
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional, Tuple, Union

import numpy as np
from osgeo import gdal, osr
from osgeo.gdalconst import GDT_Float32

spatial_vars: Tuple[str, ...] = (
    "Ksat",
    "Cly",
    "Snd",
    "OM",
    "BlkDns",
    "DpthB",
    "Hydrc",
    "Drng",
    "WTDp",
    "FldFrq",
    "WS25",
    "WS150",
    "HydGr",
    "DrngCl",
    "SolThk",
)


def classifier_factory(lookup: Mapping[str, int]) -> Callable[[Union[str, int]], int]:
    """Return a helper that maps categorical strings to numeric codes."""

    def _classifier(value: Union[str, int]) -> int:
        if value == -9999:
            return -9999
        return lookup.get(str(value), -9999)

    return _classifier


class SurgoSpatializer:
    """Generate gridded rasters from SSURGO tabular attributes."""

    def __init__(self, ssurgo_c: "SurgoSoilCollection", ssurgo_map: "SurgoMap") -> None:
        from wepppy.soils.ssurgo import SurgoMap, SurgoSoilCollection

        if not isinstance(ssurgo_c, SurgoSoilCollection):
            raise TypeError("ssurgo_c must be a SurgoSoilCollection")
        if not isinstance(ssurgo_map, SurgoMap):
            raise TypeError("ssurgo_map must be a SurgoMap")

        self.ssurgo_c = ssurgo_c
        self.ssurgo_map = ssurgo_map

    def getFirstHorizonVar(self, mukey: int, var: str) -> float:
        """Return the first-horizon value for ``var`` or ``-9999`` if missing."""
        ssurgo_c = self.ssurgo_c

        if mukey in ssurgo_c.weppSoils:
            return getattr(ssurgo_c.weppSoils[mukey].getFirstHorizon(), var, -9999)
        return -9999

    def getHorizonsVar(
        self,
        mukey: int,
        var: str,
        aggregator: Callable[[Iterable[float]], float] = np.sum,
    ) -> float:
        """Aggregate the requested horizon attribute across all horizons."""
        ssurgo_c = self.ssurgo_c

        if mukey not in ssurgo_c.weppSoils:
            return -9999

        horizons = ssurgo_c.weppSoils[mukey].horizons

        if horizons is None:
            return -9999

        values = []
        for horizon in horizons:
            if horizon is None:
                continue

            value = getattr(horizon, var, None)

            if value is None:
                continue

            values.append(value)

        if values:
            return aggregator(values)

        return -9999

    def getMajorComponentVar(
        self,
        mukey: int,
        var: str,
        classifier: Optional[Callable[[Union[str, int]], int]] = None,
    ) -> int:
        """Return (optionally classified) values drawn from the major component."""
        ssurgo_c = self.ssurgo_c

        if mukey in ssurgo_c.weppSoils:
            value = getattr(ssurgo_c.weppSoils[mukey].majorComponent, var, -9999)
            if classifier is None:
                return value

            return classifier(value)
        return -9999

    def spatialize_var(
        self,
        var: str,
        dst_fname: Union[str, Path],
        drivername: str = "GTiff",
        nodata_value: float = -9999,
    ) -> None:
        """Generate a raster for ``var`` and write it to ``dst_fname``."""
        drainage_classifier = classifier_factory(
            {"Very poorly drained": 0,
             "Poorly drained": 1,
             "Somewhat poorly drained": 2,
             "Well drained": 3,
             "Moderately well drained": 4,
             "Somewhat excessively drained": 5,
             "Excessively drained": 6})

        _spatial_vars = dict([
            ('Ksat', lambda mukey: self.getFirstHorizonVar(mukey, 'ksat_r')),
            ('Cly', lambda mukey: self.getFirstHorizonVar(mukey, 'claytotal_r')),
            ('Snd', lambda mukey: self.getFirstHorizonVar(mukey, 'sandtotal_r')),
            ('OM', lambda mukey: self.getFirstHorizonVar(mukey, 'om_r')),
            ('BlkDns', lambda mukey: self.getFirstHorizonVar(mukey, 'dbthirdbar_r')),
            ('DpthB', lambda mukey: self.getFirstHorizonVar(mukey, 'hzdepb_r')),
            ('Hydrc', lambda mukey: self.getMajorComponentVar(mukey, 'hydricrating',
                                                              classifier_factory({'No': 0, 'Yes': 1}))),
            ('Drng', lambda mukey: self.getMajorComponentVar(mukey, 'drainagecl',
                                                             drainage_classifier)),
            ('WTDp', lambda mukey: self.getMajorComponentVar(mukey, 'wtdepannmin')),
            ('FldFrq', lambda mukey: self.getMajorComponentVar(mukey, 'flodfreqdcd',
                                                               classifier_factory(
                {'None': 0, 'Rare': 1, 'Occasional': 2, 'Frequent': 3}))),
            ('WS25', lambda mukey: self.getMajorComponentVar(mukey, 'aws025wta')),
            ('WS150', lambda mukey: self.getMajorComponentVar(mukey, 'aws0150wta')),
            ('HydGr', lambda mukey: self.getMajorComponentVar(mukey, 'hydgrpdcd',
                                                              classifier_factory(
                {"A": 0, "B": 1, "A/D": 2, "C": 3, "C/D": 4, "B/D": 5, "D": 6}))),
            ('DrngCl', lambda mukey: self.getMajorComponentVar(mukey, 'drclassdcd',
                                                               drainage_classifier)),
            ('SolThk', lambda mukey: self.getHorizonsVar(mukey, 'hzdepb_r', np.sum))
        ])

        assert var in _spatial_vars

        func = _spatial_vars[var]

        ssurgo_map = self.ssurgo_map

        data, mukeys = ssurgo_map.data, ssurgo_map.mukeys
        num_cols, num_rows = data.shape
        proj, transform = ssurgo_map.proj, ssurgo_map.transform

        # create empty array to hold data
        var_r = np.ones(data.shape) * nodata_value

        # iterate over mukeys and fill data
        meta = Counter()
        for mukey in mukeys:
            indx = np.where(data == mukey)

            assert len(indx[0]) > 0

            value = func(mukey)
            var_r[indx] = value

            meta[str(value)] += len(indx[0])

        dst_path = Path(dst_fname)
        meta_path = Path(f"{dst_path}.meta")

        with meta_path.open("w", encoding="utf-8") as fid:
            fid.write(json.dumps(meta, sort_keys=True,
                                 indent=4, separators=(',', ': '),
                                 allow_nan=False))

        # create raster
        driver = gdal.GetDriverByName(drivername)
        dst = driver.Create(str(dst_path), num_cols, num_rows, 1, GDT_Float32)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        band = dst.GetRasterBand(1)
        band.WriteArray(var_r.T)
        band.SetNoDataValue(-9999)

        del dst  # Writes and closes file


if __name__ == "__main__":
    from wepppy.soils.ssurgo import SurgoMap, SurgoSoilCollection

    _map = ('tests/test_maps/ssurgo.tif')
    var = 'Cly'
    ssurgo_map = SurgoMap(_map)

    ssurgo_c = SurgoSoilCollection(ssurgo_map.mukeys)
    ssurgo_c.makeWeppSoils(horizon_defaults=None)

    spatializer = SurgoSpatializer(ssurgo_c, ssurgo_map)

    spatializer.spatialize_var(var, 'tests/test_maps/%s.tif' % var)
