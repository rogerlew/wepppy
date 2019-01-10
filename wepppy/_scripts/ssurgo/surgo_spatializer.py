from wepppy.ssurgo import (
    SurgoMap,
    SurgoSoilCollection,
    SurgoSpatializer,
    spatial_vars
)

_map = 'ssurgo.tif'
ssurgo_map = SurgoMap(_map)

ssurgo_c = SurgoSoilCollection(ssurgo_map.mukeys)
ssurgo_c.makeWeppSoils(horizon_defaults=None)

for var in spatial_vars:
    print(var)
    spatializer = SurgoSpatializer(ssurgo_c, ssurgo_map)
    spatializer.spatialize_var(var, '%s.tif' % var)
