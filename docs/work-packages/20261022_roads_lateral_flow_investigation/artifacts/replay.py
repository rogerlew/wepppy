"""Isolated native aggregation experiments; never writes to the incident run."""
from pathlib import Path
import hashlib
import json
import tempfile
import numpy as np
import pyarrow.parquet as pq
import wepppyo3.wepp_interchange as native
import wepppyo3.wepp_interchange.wepp_interchange_rust as binary

root = Path('/wc1/runs/cl/clogging-starch')
base = root/'wepp/output/interchange'
roads = root/'wepp/roads/output/interchange'
scratch = Path(tempfile.mkdtemp(prefix='roads-lateral-', dir='/workdir/wepppy-scratch'))
opts = json.loads((root/'wepp.nodb').read_text())['py/state']['baseflow_opts']
ids = sorted(pq.read_table(base/'H.pass.parquet', columns=['wepp_id']).column(0).unique().to_pylist())
metrics = ['Area','Lateral Flow','Runoff','Percolation','Baseflow','runvol']
result = {'scratch':str(scratch),'native_binary':binary.__file__, 'native_sha256':hashlib.sha256(Path(binary.__file__).read_bytes()).hexdigest(),'baseflow_opts':opts,'cases':{}}
cases = [('baseline',base,base,None),('original_roads',roads,roads,None),('roads_pass_baseline_wat',roads,base,None),('combined_hills_only_baseline_wat',roads,base,ids)]
for name, ps, ws, selected in cases:
 out=scratch/(name+'.parquet')
 native.totalwatsed3_to_parquet(str(ps/'H.pass.parquet'),str(ws/'H.wat.parquet'),str(out),opts['gwstorage'],opts['bfcoeff'],opts['dscoeff'],1,0,wepp_ids=selected)
 d=pq.read_table(out).to_pandas()
 item={'annual':d.groupby('year')[[m for m in metrics if m!='Area']].sum().reset_index().to_dict('records'),'area':float(d.Area.iloc[0]),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
 if name in ['baseline','original_roads']:
  orig=pq.read_table(ps/'totalwatsed3.parquet').to_pandas()
  item['max_abs_difference_from_retained']={c:float(np.max(np.abs(d[c].to_numpy()-orig[c].to_numpy()))) for c in metrics}
 result['cases'][name]=item
# Isolate volume counted as both standalone segment and combined hillslope.
b=pq.read_table(base/'H.pass.parquet').to_pandas()
r=pq.read_table(roads/'H.pass.parquet').to_pandas()
keys=['year','sim_day_index']
bs=b.groupby(keys).runvol.sum()
combined=r[r.wepp_id.isin(ids)].groupby(keys).runvol.sum()
segments=r[~r.wepp_id.isin(ids)].groupby(keys).runvol.sum()
residual=combined-bs-segments
result['double_count_check']={'max_daily_abs_residual_m3':float(residual.abs().max()),'baseline_total_m3':float(bs.sum()),'combined_hills_total_m3':float(combined.sum()),'standalone_segments_total_m3':float(segments.sum())}
print(json.dumps(result,indent=2))
