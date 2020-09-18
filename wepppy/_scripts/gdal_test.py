from osgeo import gdal
gdal.UseExceptions()

import numpy as np

raster_fn = '/geodata/Holden_WRF_atlas/precip_max_12hour_1982-2011.tif'
ds = gdal.Open(raster_fn)
assert ds is not None

transform = ds.GetGeoTransform()
band = ds.GetRasterBand(1)
data = np.array(band.ReadAsArray(), dtype=np.int)

print(data[:10, :10])
