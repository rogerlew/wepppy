"""Read-only Daymet provenance and previous-assessment comparison."""
import io,json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
import requests
O=Path(__file__).resolve().parent
R=Path('/wc1/runs/th/thespian-cleanness');M=R/'postfire_debris_flow'
ID='8190121c8a4b45e1952861e74d909693'
ids={'synthetic_PRISM':'0a34c96cd0dc4e6bb7bb7780d8f8915b','GridMET':'f493a714df9d4fbfbfd4370c46ad54f8','Daymet':ID}
owner=json.loads((R/'climate.nodb').read_text())['py/state']
cli=pd.read_parquet(R/'climate/wepp_cli.parquet')
cli.index=pd.to_datetime(dict(year=cli.year.astype(int),month=cli.month.astype(int),day=cli.day_of_month.astype(int)))
source=pd.read_parquet(R/'climate/daymet_1980-2024.parquet')
assert cli.index.equals(source.index)
prn=pd.read_csv(R/'climate/ws.prn',sep=r'\s+',header=None,names=['month','day','year','prcp_hundredths_in','tmax_F','tmin_F'])
assert np.array_equal(source['prcp(mm/day)'],prn.prcp_hundredths_in)
assert np.array_equal(source['tmax(degc)'],prn.tmax_F)
assert np.array_equal(source['tmin(degc)'],prn.tmin_F)
# df_to_prn mutates its input; build_observed_daymet subsequently overwrites
# the parquet with these PRN units while leaving original column labels.
recovered=source['prcp(mm/day)']*.254
window=cli.loc['2021-08-05':'2021-08-12'].copy()
window['date']=window.index.strftime('%Y-%m-%d')
window['saved_daymet_column_value']=source['prcp(mm/day)']
window['recovered_daymet_mm']=recovered
lon,lat=json.loads((R/'watershed.nodb').read_text())['py/state']['_centroid']['py/tuple']
url=f'https://daymet.ornl.gov/single-pixel/api/data?lat={lat}&lon={lon}&year=2021'
raw=O/'daymet_publisher_2021.csv'
if not raw.exists():
 response=requests.get(url,timeout=120);response.raise_for_status();raw.write_text(response.text)
lines=raw.read_text().splitlines();start=next(i for i,l in enumerate(lines) if l.lower().startswith('year,'))
fresh=pd.read_csv(io.StringIO('\n'.join(lines[start:])))
fresh.columns=[c.replace(' ','') for c in fresh.columns]
fresh.index=pd.to_datetime(fresh.year.astype(int).astype(str)+'-'+fresh.yday.astype(int).astype(str),format='%Y-%j')
window['publisher_daymet_mm']=fresh['prcp(mm/day)']
cols=['date','publisher_daymet_mm','saved_daymet_column_value','recovered_daymet_mm','prcp','peak_intensity_15','peak_intensity_30','peak_intensity_60']
window[cols].to_csv(O/'august_2021_daily.csv',index=False)
quantized=np.round(fresh['prcp(mm/day)']/25.4*100)
assert np.array_equal(quantized,source.loc['2021','prcp(mm/day)'])
events=pd.read_parquet(M/'events.parquet');rows=events[(events.year==2021)&(events.month==8)&events.day_of_month.between(5,12)]
rows.to_csv(O/'august_2021_events.csv',index=False)
frames=[];manifests={};inverse={}
for label,i in ids.items():
 root=M/'attempts'/i/'results'
 df=pd.read_parquet(root/'design.parquet');df['climate']=label;frames.append(df)
 manifests[label]=json.loads((root/'manifest.json').read_text())
 inverse[label]=pd.read_parquet(root/'inverse.parquet')
design=pd.concat(frames,ignore_index=True);design.to_csv(O/'design_comparison.csv',index=False)
comparison={label:{'predictors_identical':m['predictor_snapshot']['predictors']==manifests['Daymet']['predictor_snapshot']['predictors'],'coverage_identical':m['coverage']==manifests['Daymet']['coverage'],'inverse_identical':inverse[label].equals(inverse['Daymet'])} for label,m in manifests.items()}
assert all(all(v.values()) for v in comparison.values())
result={'attempts':ids,'catalog_id':owner['_catalog_id'],'mode_value':owner['_climate_mode'],'period':[str(cli.index.min()),str(cli.index.max())],'days':len(cli),'wet_days':int((cli.prcp>0).sum()),'quality_guard_warning':owner.get('_observed_quality_guard_summary_warning'),'silent_pass':owner.get('_silent_pass_observed_quality_guard'),'adjust_mx_pt5':owner.get('_adjust_mx_pt5'),'source_parquet_units':'precipitation hundredths of inches; temperatures Fahrenheit; original column labels incorrectly retained','prn_matches_saved_source':True,'recovered_daily_vs_cli_max_abs_mm':float(np.max(np.abs(recovered-cli.prcp))),'publisher_query':url,'publisher_2021_quantized_matches_retained_source':True,'publisher_raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'publisher_2021_vs_cli_max_abs_mm':float(np.max(np.abs(fresh['prcp(mm/day)']-cli.loc['2021','prcp']))),'comparison':comparison,'window_daily':json.loads(window[cols].to_json(orient='records')),'window_events':json.loads(rows.to_json(orient='records')),'design_15':json.loads(design[design.duration_minutes==15].to_json(orient='records'))}
(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
