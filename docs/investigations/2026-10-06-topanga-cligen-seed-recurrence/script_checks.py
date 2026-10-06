"""Focused checks for study analysis and event screening on the real runtime."""
from types import SimpleNamespace
import pandas as pd
from analyze import wilson
from pairing import pair_events
from study import cli_rows, ROOT

lo,hi=wilson(0,100)
assert lo < 1e-15 and 0.036 < hi < 0.038
lo,hi=wilson(100,100)
assert 0.962 < lo < 0.964 and abs(hi-1)<1e-15
lo,hi=wilson(50,100)
assert abs(lo+hi-1)<1e-15 and 0.40<lo<0.41
row={'year':1986,'day':46,'ofe':1,'ordinal':1,'runoff_post_m':0.04,
     'surdra_raw_m':0.001,'surdra_realized_m':0.001,'added_rate_m_s':1e-7,
     'forcing_mode':1,'solver':'APPMTH','peak_m_s':1e-6}
a=pd.DataFrame([row]);b=pd.DataFrame([{**row,'peak_m_s':3e-6}])
trial=SimpleNamespace(trial_id='test',scenario='test',hillslope_id=106,family='ksat',direction='plus')
p=pair_events(a,b,trial)
assert p.iloc[0].peak_gt25pct_runoff_lt5pct and p.iloc[0].peak_twofold
# Binary-exact operands distinguish >25% from >=25%, and <5% from <=5%.
base={**row,'peak_m_s':1.0,'runoff_post_m':20.0}
trial_base=pd.DataFrame([base])
for peak,runoff,expected in [(1.25,20.0,False),(1.250001,20.0,True),(1.5,21.0,False),(1.5,20.999,True)]:
    result=pair_events(trial_base,pd.DataFrame([{**base,'peak_m_s':peak,'runoff_post_m':runoff}]),trial)
    assert bool(result.iloc[0].peak_gt25pct_runoff_lt5pct)==expected
b=pd.DataFrame([{**row,'day':47}])
p=pair_events(a,b,trial)
assert len(p)==2 and p.event_presence_changed.all()
assert p.peak_m_s_baseline.isna().sum()==1 and p.peak_m_s_mutant.isna().sum()==1
assert not p.peak_gt25pct_runoff_lt5pct.any()
_,_,data=cli_rows(ROOT/'inputs/ksat20/p106.cli')
assert len(data)==16437
print('PASS Wilson endpoints/symmetry, paired anomaly flags, absent-event semantics, full climate date coverage')
