"""Actual mod dataset and projected-extent acquisition through forest/master list."""
import json
import os
from pathlib import Path
import numpy as np
from osgeo import gdal
from wepppy.all_your_base.geo.webclients.wmesque import wmesque_retrieve
root=Path('/wc1/wmesque-acceptance-2zkjanwa')
os.environ['WMESQUE_ENDPOINTS']=json.dumps(['http://wmesque2:8030','https://wepp.cloud/webservices/wmesque2'])
source=gdal.Open(str(root/'live-nlcd.tif'));transform=source.GetGeoTransform()
left,top=transform[0],transform[3];right=left+source.RasterXSize*transform[1];bottom=top+source.RasterYSize*transform[5]
projected=root/'projected-nlcd.tif'
wmesque_retrieve('nlcd/2019',[left,bottom,right,top],str(projected),30,extent_crs='EPSG:32611')
actual=gdal.Open(str(projected));np.testing.assert_array_equal(actual.ReadAsArray(),source.ReadAsArray())
canopy=root/'treecanopy.tif'
wmesque_retrieve('nlcd_treecanopy/2016',[-116.41414278909173,45.24670016201569,-116.33870536206356,45.29989121596863],str(canopy),30)
canopy_ds=gdal.Open(str(canopy));assert canopy_ds is not None
result={'projected_nlcd_pixel_parity':True,'canopy_shape':[canopy_ds.RasterYSize,canopy_ds.RasterXSize],
        'canopy_range':canopy_ds.GetRasterBand(1).ComputeRasterMinMax(),
        'canopy_endpoint':json.loads(Path(str(canopy)+'.meta').read_text())['wmesque_retrieve']['wmesque_endpoint']}
(root/'mod-projected-evidence.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
