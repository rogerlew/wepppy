"""Read back every source-qualified UM1 summary row in an archive-restored copy."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from wepppy.nodb.mods.roads import Roads

root = Path('/workdir/wepppy/tests/wepp/interchange/fixtures/roads-accounting-scratch/um1-restored')
original = Path('/wc1/runs/cl/clogging-starch')
folder = root/'wepp/roads/output/interchange'
relative = 'wepp/roads/output/interchange/roads_segment_loss_summary.parquet'
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
protected = [p for p in root.glob('wepp/**/*.parquet') if str(p.relative_to(root)) != relative]
protected += list(root.glob('wepp/**/*.pass.dat'))
before = {str(p.relative_to(root)):digest(p) for p in protected}
original_before = {str(p.relative_to(original)):digest(p) for p in original.glob('wepp/**/*.parquet')}
controller = Roads.getInstance(str(root))
result_path = controller._build_roads_segment_loss_summary_parquet(interchange_dir=folder)
assert result_path == relative
actual = pd.read_parquet(root/result_path).set_index('segment_run_id').sort_index()
assert len(actual) == 34
source = pd.read_parquet(original/'wepp/roads/output/interchange/H.pass.parquet')
source = source[source.wepp_id.isin(actual.index)].copy()
source['sediment_yield_kg'] = source.runvol*source[[f'sedcon_{i}' for i in range(1,6)]].sum(axis=1)
expected = source.groupby('wepp_id')[['runvol','sbrunv','gwbfv','tdet','tdep','sediment_yield_kg']].sum()/16
for field, output in zip(expected.columns,['runoff_volume_m3','subrunoff_volume_m3','baseflow_volume_m3','soil_loss_kg','sediment_deposition_kg','sediment_yield_kg']):
    np.testing.assert_allclose(actual[output],expected[field],rtol=1e-10,atol=1e-9)
water = pd.read_parquet(original/'wepp/roads/output/interchange/H.wat.parquet')
area = water[['wepp_id','ofe_id','Area']].drop_duplicates().groupby('wepp_id').Area.sum()
np.testing.assert_allclose(actual.modeled_area_m2,area.loc[actual.index],rtol=1e-12)
assert actual.sediment_leaving_buffer_kg.isna().all()
assert (actual.profile_scope == 'road').all()
assert all(digest(root/p)==h for p,h in before.items())
assert all(digest(original/p)==h for p,h in original_before.items())
metadata = pq.read_schema(root/relative).metadata
receipt = {'root':str(root),'summary_sha256':digest(root/relative),'rows':len(actual),
    'sediment_kg_per_year':actual.sediment_yield_kg.sum(),'runoff_m3_per_year':actual.runoff_volume_m3.sum(),
    'source_900001_sediment_kg_per_year':actual.loc[900001,'sediment_yield_kg'],
    'modeled_area_m2':actual.modeled_area_m2.sum(),'all_source_rows_verified':True,
    'protected_scratch_artifacts':len(before),'original_parquets_unchanged':len(original_before),
    'policy':metadata[b'roads_segment_summary_policy'].decode(),'uid':os.getuid(),'gid':os.getgid()}
Path('/tmp/roads-segment-um1-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2),flush=True)
