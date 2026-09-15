"""Independent Table-4 arithmetic and exact-mask check for a retained bundle."""
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rasterio

from wepppy.nodb.mods.postfire_debris_flow.results import open_results
from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import digest,write_json

TABLE4={
    'M1':{15:(-3.63,.41,.67,.70),30:(-3.61,.26,.39,.50),60:(-3.21,.17,.20,.220)},
    'M3':{15:(-3.71,.32,.33,.47),30:(-3.79,.21,.19,.36),60:(-3.46,.14,.10,.18)}}


def main():
    root,output=map(Path,sys.argv[1:])
    catalog=open_results(root,expected_manifest_sha256=digest(root/'manifest.json'))
    m=json.loads((root/'manifest.json').read_text())
    predictors={k:v['value'] for k,v in m['predictor_snapshot']['predictors'].items()}
    complete=all(v is not None for v in predictors.values())
    verified={}
    for name in ('events','design','inverse'):
        rows=pd.read_parquet(root/(name+'.parquet')).to_dict('records');available=0
        for row in rows:
            if not complete:
                assert pd.isna(row['probability'])
                assert row['status']=='unavailable'
                continue
            b,ct,cf,cs=TABLE4[m['model']][row['duration_minutes']]
            response=ct*predictors['T']+cf*predictors['F']+cs*predictors['S']
            if row['status']!='available': continue
            available+=1
            if name=='inverse':
                target=row['target_probability']
                rainfall=(math.log(target/(1-target))-b)/response
                assert math.isclose(row['rainfall_mm'],rainfall,rel_tol=2e-14,abs_tol=2e-14)
                assert math.isclose(row['intensity_mm_per_hour'],rainfall*60/row['duration_minutes'],rel_tol=2e-14)
            else:
                x=b+row['rainfall_mm']*response
                value=1/(1+math.exp(-x)) if x>=0 else math.exp(x)/(1+math.exp(x))
                assert math.isclose(row['probability'],value,rel_tol=2e-14,abs_tol=2e-14)
        verified[name]={'rows':len(rows),'available':available}
    with rasterio.open(root/'valid_mask.tif') as ds:
        mask=ds.read(1)
        assert ds.dtypes==('uint8',) and ds.nodata==255
        assert np.isin(mask,[0,1,255]).all()
        assert int((mask==1).sum())==m['coverage']['valid_cells']
        assert int((mask!=255).sum())==m['coverage']['total_cells']
    result=dict(model=m['model'],result=str(root),manifest_sha256=digest(root/'manifest.json'),
        predictors=predictors,coverage=m['coverage'],verified=verified,
        interpretation='available arithmetic verified' if complete else 'explicit unavailable predictors verified')
    write_json(output,result);print(json.dumps(result))


if __name__=='__main__':main()
