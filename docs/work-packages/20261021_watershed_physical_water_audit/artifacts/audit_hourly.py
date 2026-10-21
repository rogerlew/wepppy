"""Compare independently observed unallocated infiltration with soil screens."""
import json
from pathlib import Path
import pandas as pd
from audit_cases import wat,metrics
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
results=[]
for name in ['hourly-single','hourly-upper60','hourly-three']:
    root=ROOT/'hourly-observer/on'/name
    parity=json.loads((root/'parity.json').read_text());assert parity['success'] and not parity['differences']
    h=pd.read_csv(root/'runs/water_audit_hourly.txt',sep=r'\s+',names=['year','day','ofe','hour','input','remaining'])
    assert not h.duplicated(['year','day','ofe','hour']).any()
    assert h.groupby(['year','day','ofe']).size().eq(24).all()
    rem=h.groupby(['year','day','ofe']).remaining.sum()*1000
    w=wat(ROOT/'release-matrix'/name/'output/H1.wat.dat').set_index(['year','day','ofe']).sort_index()
    assert w.index.equals(rem.index)
    w['remaining_mm']=rem
    w['screen_mm']=w.P+w.Irr+w.UpStrmQ+w.SubRIn-w.Ep-w.Es-w.Er-w.Dp-w.QOFE-w.latqcc-w.Tile-(w.SoilWaterTotal+w.Snow).groupby(level='ofe').diff()
    w['corrected_screen_mm']=w.screen_mm-w.remaining_mm
    rows=[]
    for i,g in w.groupby(level='ofe'):
        valid=g.dropna(subset=['screen_mm'])
        rows.append(dict(ofe=int(i),raw_screen_mm=metrics(valid.screen_mm),remainder_mm=metrics(valid.remaining_mm),screen_after_measured_remainder_mm=metrics(valid.corrected_screen_mm)))
    total_area=w.groupby(level='ofe').Area.first().sum()
    result=dict(case=name,ofes=rows,unallocated_m3=float((w.remaining_mm*w.Area/1000).sum()),unallocated_hillslope_mm_per_year=float((w.remaining_mm*w.Area).sum()/total_area/44),max_hour_remainder_mm=float(h.remaining.abs().max()*1000))
    results.append(result);print(json.dumps(result,indent=2),flush=True)
    w.to_csv(root/'hourly-water-ledger.csv')
(ROOT/'hourly-observer/audit.json').write_text(json.dumps(results,indent=2)+'\n')
