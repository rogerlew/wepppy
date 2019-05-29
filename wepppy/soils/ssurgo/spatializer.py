import json
from collections import Counter

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import (
    GDT_Float32
)

spatial_vars = ('Ksat', 'Cly', 'Snd', 'OM', 'BlkDns', 'DpthB',
                'Hydrc', 'Drng', 'WTDp', 'FldFrq', 'WS25', 'WS150',
                'HydGr', 'DrngCl', 'SolThk')

def classifier_factory(lookup):
    return lambda x: (lookup.get(x, -9999), -9999)[x == -9999]


class SurgoSpatializer(object):
    def __init__(self, ssurgo_c, ssurgo_map):
        from wepppy.soils.ssurgo import SurgoMap, SurgoSoilCollection

        assert isinstance(ssurgo_c, SurgoSoilCollection)
        assert isinstance(ssurgo_map, SurgoMap)

        self.ssurgo_c = ssurgo_c
        self.ssurgo_map = ssurgo_map

    def getFirstHorizonVar(self, mukey, var):
        ssurgo_c = self.ssurgo_c

        if mukey in ssurgo_c.weppSoils:
            return getattr(ssurgo_c.weppSoils[mukey].getFirstHorizon(), var, -9999)
        return -9999

    def getHorizonsVar(self, mukey, var, aggregator=np.sum):
        ssurgo_c = self.ssurgo_c

        if mukey not in ssurgo_c.weppSoils:
            return -9999

        horizons = ssurgo_c.weppSoils[mukey].horizons

        if horizons is None:
            return -9999

        x = []
        for h in ssurgo_c.weppSoils[mukey].horizons:
            if h is None:
                continue

            v = getattr(h, var, None)

            if v is None:
                continue

            x.append(v)

        if len(x) > 0:
            return aggregator(x)

        return -9999

    def getMajorComponentVar(self, mukey, var, classifier=None):
        ssurgo_c = self.ssurgo_c

        if mukey in ssurgo_c.weppSoils:
            x = getattr(ssurgo_c.weppSoils[mukey].majorComponent, var, -9999)
            if classifier is None:
                return x

            return classifier(x)
        return -9999

    def spatialize_var(self, var, dst_fname, drivername='GTiff', nodata_value=-9999):
        """
        Creates a raster of the variable specified by var
        """
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

        with open(dst_fname + '.meta', 'w') as fid:
            fid.write(json.dumps(meta, sort_keys=True,
                                 indent=4, separators=(',', ': ')))

        # create raster
        driver = gdal.GetDriverByName(drivername)
        dst = driver.Create(dst_fname, num_cols, num_rows, 1, GDT_Float32)

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
