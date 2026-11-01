"""Synthetic selector controls, not model histories."""
import copy,json,sys
from pathlib import Path
from select_window import select_events
expected={(o,d,1) for o in range(1,4) for d in [1,2]}
def event(tag,seq,o,d,parent=0,hour=0):
    return dict(tag=tag,seq=seq,ofe=o,year=1,day=d,parent=parent,hour=hour,nsl=1,layers={1:dict(dg=.1,frozen=.01,st=.02,dry=.1,frzw=0.)})
rows=[]
for day in [1,2]:
 for ofe in range(1,4):
  rows.append(event('DAY_WIN_GATE',len(rows)+1,ofe,day))
  if ofe==1:
   call=len(rows)+1;rows.append(event('FROST_CALL',call,ofe,day,hour=1));rows.append(event('FROST_DONE',call+1,ofe,day,parent=call,hour=1))
  rows.append(event('WB_PRE',len(rows)+1,ofe,day))
rows.append({'tag':'FOOTER'})
assert select_events(rows,expected)['selected']==[1,2]
other=copy.deepcopy(rows)
for e in other:
 if e['tag'] in ['FROST_CALL','FROST_DONE']:e['ofe']=2
# Separate direct witness: foreign completed frost cannot select OFE1.
foreign=[event('DAY_WIN_GATE',1,2,2),event('FROST_CALL',2,2,2,hour=1),event('FROST_DONE',3,2,2,parent=2,hour=1),event('DAY_WIN_GATE',4,1,2),event('WB_PRE',5,1,2),{'tag':'FOOTER'}]
assert select_events(foreign,{(1,2,1),(2,2,1)})['selected'] is None
mutants={}
mutants['missing-day']=[e for e in rows if not (e['tag']=='DAY_WIN_GATE' and e['ofe']==3 and e['day']==1)]
a=copy.deepcopy(rows);a.insert(1,copy.deepcopy(a[0]));mutants['duplicate-day']=a
a=copy.deepcopy(rows);next(e for e in a if e['tag']=='FROST_DONE')['parent']=999;mutants['parent']=a
mutants['missing-footer']=rows[:-1]
a=copy.deepcopy(rows);a.insert(-1,event('DAY_WIN_GATE',999,1,1));mutants['reversed-clock']=a
for name,values in mutants.items():
 try:select_events(values,expected)
 except ValueError:continue
 raise ValueError('Corruption accepted '+name)
with Path(sys.argv[1]).open('x') as f:json.dump(dict(passed=True,rejected=list(mutants),foreign_ofe_not_selected=True),f,indent=2);f.write('\n')
