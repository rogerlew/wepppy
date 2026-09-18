"""Reproduce the reporter's hillslope statistics from fresh WEPP interchange."""
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROLES = ['baseline', 'low', 'prescribed', 'sbs', 'moderate', 'high', 'thin30', 'thin50']
LABELS = ['Unburned / baseline', 'Low severity fire', 'Prescribed fire',
          'Predicted soil burn severity map', 'Moderate severity fire',
          'High severity fire', '30% canopy cover thinning', '50% canopy cover thinning']
rows, sources = [], []
for order, (role, label) in enumerate(zip(ROLES, LABELS), 1):
    run = Path('/wc1/runs/mo') / ('mofe-0918-' + role)
    path = run / 'wepp/output/interchange/loss_pw0.hill.parquet'
    status = json.loads(Path(f'/tmp/mofe-{role}-wepp-status.json').read_text())
    assert status['status'] == 'finished'
    started = datetime.fromisoformat(status['started_at']).replace(tzinfo=timezone.utc).timestamp()
    assert path.stat().st_mtime >= started, (role, 'stale interchange output')
    frame = pd.read_parquet(path)
    assert len(frame) == 455 and frame.wepp_id.nunique() == 455
    expected_ids = pd.read_parquet(run / 'watershed/hillslopes.parquet')['wepp_id']
    assert set(frame.wepp_id) == set(expected_ids), (role, 'hillslope ID mismatch')
    for column in ['Hillslope Area', 'Runoff Volume', 'Sediment Yield', 'Soil Loss']:
        assert frame[column].map(math.isfinite).all(), (role, column, 'non-finite metric')
    assert pq.read_schema(path).metadata[b'average_years'] == b'22'
    area = frame['Hillslope Area']
    assert (area > 0).all()
    runoff = frame['Runoff Volume'] / (area * 10)
    sediment = frame['Sediment Yield']
    soil_loss = frame['Soil Loss']
    row = dict(scenario=label, hillslope_count=len(frame), area_ha=area.sum(),
               area_weighted_runoff_depth_mm_per_yr=frame['Runoff Volume'].sum()/(area.sum()*10),
               total_runoff_volume_m3_per_yr_estimated=frame['Runoff Volume'].sum(),
               total_sediment_yield_tonne_per_yr=sediment.sum()/1000,
               total_soil_loss_tonne_per_yr=soil_loss.sum()/1000,
               zero_runoff_hillslopes=int((runoff == 0).sum()),
               negligible_runoff_hillslopes_lt_1_mm_yr=int((runoff < 1).sum()),
               zero_sediment_hillslopes=int((sediment == 0).sum()),
               negligible_sediment_hillslopes_lt_1_kg_yr=int((sediment < 1).sum()))
    for name, values in {
        'runoff_depth_mm_per_yr': runoff, 'runoff_volume_m3_per_yr': frame['Runoff Volume'],
        'sediment_yield_kg_per_yr': sediment, 'sediment_yield_density_kg_ha_yr': sediment/area,
        'soil_loss_kg_per_yr': soil_loss, 'soil_loss_density_kg_ha_yr': soil_loss/area,
    }.items():
        stats = dict(min=values.min(), q1=values.quantile(.25), median=values.median(),
                     mean=values.mean(), std=values.std(), q3=values.quantile(.75),
                     iqr=values.quantile(.75)-values.quantile(.25),
                     p95=values.quantile(.95), max=values.max())
        row.update({name+'_'+key: value for key, value in stats.items()})
    row['scenario_order'] = order
    rows.append(row)
    sources.append(dict(runid=run.name, file=str(path),
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        mtime=path.stat().st_mtime))
result = pd.DataFrame(rows)
output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp')
result.to_csv(output_dir / 'mofe-forest-hillslope-response-summary.csv', index=False)
(output_dir / 'mofe-forest-summary-sources.json').write_text(json.dumps(sources, indent=2))
print(result[['scenario', 'area_weighted_runoff_depth_mm_per_yr',
              'total_sediment_yield_tonne_per_yr']].to_string(index=False))
