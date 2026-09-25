"""Compare accepted climate rerun, not an observed storm calibration."""
import json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
O=Path(__file__).resolve().parent
R=Path('/wc1/runs/th/thespian-cleanness'); M=R/'postfire_debris_flow'
old='0a34c96cd0dc4e6bb7bb7780d8f8915b'; new='f493a714df9d4fbfbfd4370c46ad54f8'
def manifest(i):return json.loads((M/'attempts'/i/'results/manifest.json').read_text())
a,b=manifest(old),manifest(new)
cli=pd.read_parquet(R/'climate/wepp_cli.parquet');grid=pd.read_parquet(R/'climate/gridmet_1980-2025.parquet')
cli.index=pd.to_datetime(dict(year=cli.year.astype(int),month=cli.month.astype(int),day=cli.day_of_month.astype(int)))
assert cli.index.equals(grid.index)
window=cli.loc['2021-08-05':'2021-08-12'].copy()
window['date']=window.index.strftime('%Y-%m-%d');window['gridmet_daily_mm']=grid['pr(mm/day)']
cols=['date','gridmet_daily_mm','prcp','peak_intensity_15','peak_intensity_30','peak_intensity_60']
window[cols].to_csv(O/'august_2021_daily.csv',index=False)
events=pd.read_parquet(M/'events.parquet'); rows=events[(events.year==2021)&(events.month==8)&events.day_of_month.between(5,12)]
rows.to_csv(O/'august_2021_events.csv',index=False)
designs={i:pd.read_parquet(M/'attempts'/i/'results/design.parquet') for i in [old,new]}
joined=designs[old].merge(designs[new],on=['return_interval_years','duration_minutes'],suffixes=('_old','_new'))
joined.to_csv(O/'design_comparison.csv',index=False)
result={'old_attempt':old,'new_attempt':new,'old_identity':a['identity'],'new_identity':b['identity'],'predictors_identical':a['predictor_snapshot']['predictors']==b['predictor_snapshot']['predictors'],'coverage_identical':a['coverage']==b['coverage'],'predictor_artifact_hashes_identical':a['predictor_snapshot']['artifacts_sha256']==b['predictor_snapshot']['artifacts_sha256'],'inverse_rows_identical':pd.read_parquet(M/'attempts'/old/'results/inverse.parquet').equals(pd.read_parquet(M/'inverse.parquet')),'gridmet_daily_vs_cli_max_abs_difference_mm':float(np.max(np.abs(grid['pr(mm/day)'].to_numpy()-cli.prcp.to_numpy()))),'period':[str(cli.index.min()),str(cli.index.max())],'window_daily':json.loads(window[cols].to_json(orient='records')),'window_event_rows':json.loads(rows.to_json(orient='records')),'design_15':json.loads(joined[joined.duration_minutes==15].to_json(orient='records'))}
assert result['predictors_identical'] and result['coverage_identical'] and result['inverse_rows_identical']
(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
