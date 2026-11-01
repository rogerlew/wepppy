"""Strict consumer-domain summaries and selected executed operands."""
import calendar,math,struct
from pathlib import Path
SITES={1:'HK_log',2:'lower_ratio_1',3:'lower_ratio_2',4:'lateral_ratio',5:'HK_guard'}
def read(path,layers=None,target=None):
    rows={};bad={};last=None;sequence=0;footer=None;totals=[0]*5;days=set()
    with Path(path).open() as f:
        if f.readline().strip()!='RD_SCHEMA 1':raise ValueError('Domain schema')
        for line in f:
            c=line.split()
            if not c or footer is not None:raise ValueError('Trailing/empty domain record')
            if c[0]=='RD_END':
                if len(c)!=8:raise ValueError('Domain footer shape')
                footer=list(map(int,c[1:]));continue
            if c[0]=='N':raise ValueError('Nonfinite executed operands retained; domain accounting incomplete')
            if c[0]=='B':
                if len(c)!=12:raise ValueError('Witness shape')
                key=tuple(map(int,c[1:6]));hour,seq=map(int,c[6:8]);values=list(map(float,c[8:]))
                if key in bad or seq<=sequence or not (0<=hour<=24):raise ValueError('Witness identity')
                if (key[2] in (1,5))!=(hour==0):raise ValueError('Witness clock class')
                sequence=seq;bad[key]=dict(hour=hour,sequence=seq,values=values);continue
            if c[0]!='S' or len(c)!=15:raise ValueError('Summary framing')
            key=tuple(map(int,c[1:6]));y,d,s,o,l=key;count,nb,ni=map(int,c[6:9]);v=list(map(float,c[9:]))
            if s not in SITES or o not in (1,2,3) or not 1<=l<=10 or key in rows or (last and key<=last):raise ValueError('Summary support/order')
            if not ((s in (1,5) and (y,d)==(0,0)) or (s not in (1,5) and 1<=y<=16 and 1<=d<=366 and not (d==366 and y%4))):raise ValueError('Summary calendar')
            if count<=0 or not 0<=nb<=count or not 0<=ni<=count or not all(math.isfinite(x) for x in v):raise ValueError('Summary counts/numbers')
            amin,amax,bmin,bmax,margin,frozen=v
            if amin>amax or bmin>bmax or (ni>0)!=(frozen>0):raise ValueError('Summary extrema')
            violation=(amin<=0 or amax>=1) if s==1 else bmin<=0 if s!=5 else False
            if bool(nb)!=violation:raise ValueError('Domain flag inconsistency')
            if s!=5 and margin!=(1-amax if s==1 else bmin):raise ValueError('Domain margin identity')
            rows[key]=dict(count=count,bad=nb,icy=ni,values=v);totals[s-1]+=count;days.add((y,d));last=key
    if footer!=totals+[len(rows),len(days)]:raise ValueError('Domain completeness footer')
    expected_bad={k for k,r in rows.items() if r['bad']}
    if set(bad)!=expected_bad or sequence>sum(totals):raise ValueError('Missing/orphan witness')
    for key,w in bad.items():
        a,b,c,d=w['values']
        violation=not all(math.isfinite(x) for x in w['values']) or ((a<=0 or a>=b) if key[2]==1 else b<=0)
        if not violation:raise ValueError('False domain witness')
    if layers is not None:
        expected={(y,d,2,o,l) for y in range(1,17) for d in range(1,367 if calendar.isleap(y) else 366) for o in range(1,4) for l in range(2,layers+1)}
        if {k for k in rows if k[2]==2}!=expected or any(rows[k]['count']!=24 for k in expected):raise ValueError('Full hourly lower-ratio coverage')
        init=[k for k in rows if k[2] in (1,5)]
        if len(init)!=3*layers or {(k[3],k[4]) for k in init}!={(o,l) for o in range(1,4) for l in range(1,layers+1)} or any(rows[k]['count']!=1 for k in init):raise ValueError('HK initialization coverage')
        if any(k[4]>layers or (k[2]==3 and k[4]==1) for k in rows):raise ValueError('Layer extent')
        for k,r in rows.items():
            if k[2] in (3,4) and r['count']>24:raise ValueError('Branch overcount')
    summary={str(s):dict(site=SITES[s],units='dimensionless' if s in (1,5) else 'meters',calls=totals[s-1],bad=sum(r['bad'] for k,r in rows.items() if k[2]==s),frozen_calls=sum(r['icy'] for k,r in rows.items() if k[2]==s),minimum_denominator=min((r['values'][2] for k,r in rows.items() if k[2]==s),default=None),minimum_margin=min((r['values'][4] for k,r in rows.items() if k[2]==s),default=None)) for s in SITES}
    selected={','.join(map(str,k)):r for k,r in rows.items() if target and k[0]==target[0] and k[1] in (target[1]-1,target[1])}
    return dict(passed=True,sites=summary,summary_rows=len(rows),days=len(days),witnesses={','.join(map(str,k)):v for k,v in bad.items()},selected=selected)
def detailed(path,summary,target,layers):
    rows={};seen=set();mapping={'RD_LOW1':2,'RD_LOW2':3,'RD_LAT':4}
    for line in Path(path).open():
        c=line.split()
        if not c[0].startswith('RD_'):continue
        if c[0] not in mapping or len(c)!=11:raise ValueError('Detailed domain framing')
        y,d,o,index=map(int,c[1:5]);hour,layer=divmod(index,100);values=list(map(float,c[5:]));s=mapping[c[0]]
        key=(y,d,s,o,layer);identity=key+(hour,)
        if y!=target[0] or d not in (target[1]-1,target[1]) or o not in (1,2,3) or not 1<=hour<=24 or not 1<=layer<=layers or identity in seen:raise ValueError('Detailed domain support')
        if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite detailed operands')
        if s==4:
            single=lambda v:struct.unpack('f',struct.pack('f',v))[0]
            if values[0]!=single(values[3]-values[5]) or values[1]!=single(values[4]-values[5]):raise ValueError('Lateral operand reconstruction')
        seen.add(identity);rows.setdefault(','.join(map(str,key)),[]).append(values)
    expected={k:v for k,v in summary['selected'].items() if int(k.split(',')[2]) in (2,3,4)}
    if set(rows)!=set(expected):raise ValueError('Detailed/summary support')
    for k,vals in rows.items():
        observed=[min(v[0] for v in vals),max(v[0] for v in vals),min(v[1] for v in vals),max(v[1] for v in vals)]
        if len(vals)!=expected[k]['count'] or observed!=expected[k]['values'][:4]:raise ValueError('Detailed/summary operands')
        if sum(v[2]>0 for v in vals)!=expected[k]['icy'] or max(v[2] for v in vals)!=expected[k]['values'][5] or sum(v[1]<=0 for v in vals)!=expected[k]['bad']:raise ValueError('Detailed/summary domain flags')
    return dict(passed=True,records=len(seen),groups=len(rows))
