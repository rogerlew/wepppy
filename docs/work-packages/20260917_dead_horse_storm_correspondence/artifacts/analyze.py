import hashlib,json,math,io
from pathlib import Path
import pandas as pd
O=Path(__file__).resolve().parent;R=Path('/wc1/runs/th/thespian-cleanness/postfire_debris_flow')
ids={'Daymet':'8190121c8a4b45e1952861e74d909693','GridMET':'f493a714df9d4fbfbfd4370c46ad54f8'}
frames=[];checks=[]
for label,i in ids.items():
 root=R/'attempts'/i/'results';m=json.loads((root/'manifest.json').read_text());f=root/'events.parquet';h=hashlib.sha256(f.read_bytes()).hexdigest();assert h==m['tables']['events']['sha256']
 df=pd.read_parquet(f);df['date']=pd.to_datetime(dict(year=df.year,month=df.month,day=df.day_of_month));df=df[df.date.between('2021-07-25','2021-08-16')].copy();df['source']=label
 T,F,S=[m['predictor_snapshot']['predictors'][k]['value'] for k in ['T','F','S']]
 errors=[]
 for row in df.itertuples():
  b,t,fcoef,s={15:(-3.71,.32,.33,.47),30:(-3.79,.21,.19,.36),60:(-3.46,.14,.10,.18)}[row.duration_minutes]
  expected=1/(1+math.exp(-(b+row.rainfall_mm*(t*T+fcoef*F+s*S))))
  errors.append(abs(expected-row.probability))
 assert max(errors)<1e-12;frames.append(df);checks.append({'source':label,'attempt':i,'events_sha256':h,'max_probability_error':max(errors),'predictors':{'T':T,'F':F,'S':S}})
allrows=pd.concat(frames);allrows.to_csv(O/'events_context.csv',index=False)
candidate=allrows[allrows.date.between('2021-07-30','2021-08-02')];candidate.to_csv(O/'candidate_all_durations.csv',index=False)
summary=candidate[candidate.duration_minutes==15][['date','source','precipitation_mm','intensity_mm_per_hour','probability']];summary.to_csv(O/'candidate_15.csv',index=False)
raw=O.parent.parent/'20260917_dead_horse_daymet_audit/artifacts/daymet_publisher_2021.csv';lines=raw.read_text().splitlines();start=next(i for i,s in enumerate(lines) if s.startswith('year,'));pub=pd.read_csv(io.StringIO('\n'.join(lines[start:])));pub.columns=[s.replace(' ','') for s in pub.columns];pub['date']=pd.to_datetime(pub.year.astype(int).astype(str)+'-'+pub.yday.astype(int).astype(str),format='%Y-%j');pub[pub.date.between('2021-07-25','2021-08-16')][['date','prcp(mm/day)']].to_csv(O/'publisher_daily_context.csv',index=False)
result={'checks':checks,'candidate_15':json.loads(summary.to_json(orient='records',date_format='iso')),'totals_cli_mm':summary.groupby('source').precipitation_mm.sum().to_dict(),'publisher_candidate_total_mm':float(pub.loc[pub.date.between('2021-07-30','2021-08-02'),'prcp(mm/day)'].sum()),'note':'Saved CLI peaks are generated, not measured subdaily rainfall; no joint multi-day event probability is calculated.'}
(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(summary.to_string(index=False));print(result['totals_cli_mm'])
