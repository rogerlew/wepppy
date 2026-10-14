"""Parse fresh native output through the production interchange/report reader."""
from pathlib import Path
import json
import sys
import hashlib
import numpy as np
import pandas as pd
from osgeo import gdal
from wepppy.nodb.core import Soils
from wepppy.wepp.interchange.hill_loss_interchange import run_wepp_hillslope_loss_interchange
from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange, load_hill_wat_dataframe

project=Path(sys.argv[1])
evidence=json.loads((project/'wmesque-acceptance.json').read_text())
hill=int(evidence['execution'][1]);output=project/'wepp/output'
inputs = project / 'wepp/runs'
evidence['prepared_inputs'] = {
    ext: (inputs / f'p{hill}.{ext}').stat().st_size
    for ext in ('slp', 'sol', 'man', 'cli', 'run')}
assert all(evidence['prepared_inputs'].values())
evidence['prepared_input_sha256'] = {
    ext: hashlib.sha256((inputs / f'p{hill}.{ext}').read_bytes()).hexdigest()
    for ext in evidence['prepared_inputs']}
rasters = {label: Path(evidence[label]['path']) for label in ('dem', 'landuse')}
rasters['soil_build'] = Path(Soils.getInstance(str(project)).ssurgo_fn)
rasters.update({name: project / 'climate' / f'{name}.tif' for name in ('ppt', 'tmin', 'tmax')})
evidence['consumed_rasters'] = {}
for label, path in rasters.items():
    raster = gdal.Open(str(path))
    assert raster is not None and raster.RasterCount > 0
    band = raster.GetRasterBand(1)
    provenance = json.loads(Path(str(path)+'.meta').read_text())
    evidence['consumed_rasters'][label] = {
        'path': str(path), 'shape': [raster.RasterYSize, raster.RasterXSize],
        'bands': raster.RasterCount, 'transform': list(raster.GetGeoTransform()),
        'projection': raster.GetProjection(), 'dtype': gdal.GetDataTypeName(band.DataType),
        'nodata': band.GetNoDataValue(), 'range': list(band.ComputeRasterMinMax()),
        'endpoint': provenance['wmesque_retrieve']['wmesque_endpoint'],
        'revision': provenance.get('wmesque', {}).get('revision')}
loss=run_wepp_hillslope_loss_interchange(output,expected_hillslopes=1)
run_wepp_hillslope_wat_interchange(output,expected_hillslopes=1)
frame=load_hill_wat_dataframe(output,hill)
required=['P','Q','Ep','Es','Er','Dp','Area','SoilWaterTotal']
assert len(frame)>0 and np.isfinite(frame[required]).all().all()
assert (frame['Area']>0).all() and (frame[['P','Q']]>=0).all().all()
loss_frame=pd.read_parquet(loss)
assert len(loss_frame)==5 and np.isfinite(loss_frame.select_dtypes(include='number')).all().all()
frame.head(10).to_csv(project/'wmesque-output-readback.csv',index=False)
evidence['output_readback']={'loss_rows':len(loss_frame),'daily_water_rows':len(frame),
    'required_numeric_finite':True,'optional_null_counts':frame.select_dtypes(include='number').isna().sum().loc[lambda x:x>0].to_dict(),
    'sample_csv':str(project/'wmesque-output-readback.csv')}
(project/'wmesque-acceptance.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence['output_readback'],indent=2))
