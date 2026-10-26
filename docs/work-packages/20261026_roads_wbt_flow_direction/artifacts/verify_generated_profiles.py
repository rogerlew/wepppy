"""Read actual generated profiles and native calendars from the isolated replay."""
from pathlib import Path
import hashlib
import json
import math
import pyarrow.parquet as pq
import numpy as np

base = Path('/wc1/ablation/20261026_roads_wbt_flow_direction')
root = base / 'candidate'
summary = json.loads((base / 'run-summary.json').read_text())
validation = json.loads((base / 'validation.json').read_text())
records = {r['segment_id']:r for r in summary['segment_execution_records'] if r['status']=='completed'}
output = root / 'wepp/roads/output/interchange'
water = pq.read_table(output / 'H.wat.parquet').to_pandas()
passes = pq.read_table(output / 'H.pass.parquet').to_pandas()
readback = {}
for name in validation['recovered']:
    r = records[name]
    number = r['segment_run_id']
    slope = root / f'wepp/roads/runs/p{number}.slp'
    lines = slope.read_text().splitlines()
    assert int(lines[1]) == 2
    width = float(lines[2].split()[1])
    road_length = float(lines[3].split()[1])
    buffer_length = float(lines[5].split()[1])
    buffer_slope = float(lines[6].split()[-1])
    assert math.isclose(width,r['road_width_m'],abs_tol=.00051)
    assert math.isclose(road_length,r['segment_length_m'],abs_tol=.00051)
    assert math.isclose(buffer_length,r['trace_path_length_m'],abs_tol=.00051)
    assert math.isclose(buffer_slope,r['buffer_slope_fraction'],abs_tol=.00000051)
    hill_water = water[water['wepp_id']==number]
    hill_pass = passes[passes['wepp_id']==number]
    assert hill_pass['sim_day_index'].nunique()==5844
    assert hill_water['sim_day_index'].nunique()==5844
    for frame in (hill_water, hill_pass):
        # Native scientific values must be finite; nullable metadata is separate.
        for column in ('runvol','Runoff','P','Dp','latqcc','Ep','Es','Er'):
            if column in frame:
                assert np.isfinite(frame[column].to_numpy()).all(), (name,column)
    readback[name] = dict(run_id=number,width_m=width,road_length_m=road_length,
        buffer_length_m=buffer_length,buffer_slope=buffer_slope,
        slope_sha256=hashlib.sha256(slope.read_bytes()).hexdigest(),
        water_rows=len(hill_water),pass_rows=len(hill_pass),days=5844)
(base / 'profile-readback.json').write_text(json.dumps(readback,indent=2)+'\n')
print(json.dumps(readback,indent=2))
