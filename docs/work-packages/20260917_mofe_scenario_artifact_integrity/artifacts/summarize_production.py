"""Read-only reporter statistics and freshness checks for repaired production runs.

Writes evidence only to the explicitly supplied output directory.
Calculations match summarize_forest.py and the original reporter's columns.
"""
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

RUNS = [
    ('baseline', 'ventilated-gag', 'Unburned / baseline'),
    ('low', 'equestrian-bonheur', 'Low severity fire'),
    ('prescribed', 'neoliberal-dictate', 'Prescribed fire'),
    ('sbs', 'choice-feminist', 'Predicted soil burn severity map'),
    ('moderate', 'tactful-aging', 'Moderate severity fire'),
    ('high', 'incorporate-cerebrum', 'High severity fire'),
    ('thin30', 'acetic-surprise', '30% canopy cover thinning'),
    ('thin50', 'uncrowned-bolt', '50% canopy cover thinning'),
]
output_dir = Path(sys.argv[1])
selected = sys.argv[2] if len(sys.argv) > 2 else None
rows, sources = [], []
for order, (role, runid, label) in enumerate(RUNS, 1):
    if selected is not None and role != selected:
        continue
    root = Path('/wc1/runs') / runid[:2] / runid
    path = root / 'wepp/output/interchange/loss_pw0.hill.parquet'
    status = json.loads((output_dir / f'{role}-wepp-status.json').read_text())
    assert status['status'] == 'finished'
    started = datetime.fromisoformat(status['started_at']).replace(tzinfo=timezone.utc).timestamp()
    assert path.stat().st_mtime >= started, (role, 'stale interchange')
    frame = pd.read_parquet(path)
    assert len(frame) == 455 and frame.wepp_id.nunique() == 455
    assert set(frame.wepp_id) == set(pd.read_parquet(root / 'watershed/hillslopes.parquet').wepp_id)
    for column in ['Hillslope Area', 'Runoff Volume', 'Sediment Yield', 'Soil Loss']:
        assert frame[column].map(math.isfinite).all(), (role, column)
    assert pq.read_schema(path).metadata[b'average_years'] == b'22'
    area = frame['Hillslope Area']
    assert (area > 0).all()
    runoff = frame['Runoff Volume'] / (area * 10)
    sediment, soil_loss = frame['Sediment Yield'], frame['Soil Loss']
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
    sources.append(dict(runid=runid, file=str(path),
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        mtime=path.stat().st_mtime))
assert rows, selected
result = pd.DataFrame(rows)
stem = selected or 'all'
result.to_csv(output_dir / f'{stem}-hillslope-response-summary.csv', index=False)
(output_dir / f'{stem}-summary-sources.json').write_text(json.dumps(sources, indent=2))
print(result[['scenario', 'area_weighted_runoff_depth_mm_per_yr',
              'total_sediment_yield_tonne_per_yr']].to_string(index=False))
