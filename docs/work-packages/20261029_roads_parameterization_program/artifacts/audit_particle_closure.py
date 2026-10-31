"""Audit PASS class normalization and mass against terminal ELEMENT export.

Decimal arithmetic avoids flagging binary floating-point subtraction of printed
values. Bounds are sums/products of half-last-printed-place intervals, not fitted
tolerances. Positive EVENT records use SLOSS's concentration and WSHPAS's total
runoff volume; tiny SUBEVENT/no-event exports remain outside this EVENT audit.
"""
from pathlib import Path
from decimal import Decimal
import argparse,datetime,hashlib,json
D=Decimal

def quantum(token):return D(10)**D(token).as_tuple().exponent/D(2)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def audit(record):
    r=json.loads(record.read_text());folder=record.parent
    p=folder/'output/H1.pass.dat';e=folder/'output/H1.element.dat'
    assert digest(p)==r['outputs'][p.name] and digest(e)==r['outputs'][e.name]
    lines=p.read_text().splitlines();first=int(lines[2].split()[1]);width=D(str(r['width_m']))
    elements={tuple(map(int,f[:4])):f for line in e.read_text().splitlines()[2:] if (f:=line.split())}
    rows=positive=0;flags=[]
    for j,line in enumerate(lines):
        f=line.split()
        if not f or f[0]!='EVENT':continue
        offset=1
        while len(f)<27:f+=lines[j+offset].split();offset+=1
        assert len(f)==27
        rows+=1;conc=list(map(D,f[15:20]));frac=list(map(D,f[20:25]))
        assert all(x.is_finite() and x>=0 for x in conc+frac)
        has_sediment=bool(sum(conc))
        positive+=int(has_sediment);y,day=map(int,f[1:3]);date=datetime.date(y,1,1)+datetime.timedelta(days=day-1)
        er=elements[(3,date.day,date.month,y-first+1)]
        fsum=sum(frac);ftol=sum(quantum(t) for t in f[20:25]);vol=D(f[7]);mass=vol*sum(conc)
        boundary=D(er[23])*width
        mtol=quantum(f[7])*sum(conc)+abs(vol)*sum(quantum(t) for t in f[15:20])+quantum(f[7])*sum(quantum(t) for t in f[15:20])+quantum(er[23])*width
        causes=[]
        if has_sediment and abs(fsum-1)>ftol:causes.append('fraction_sum')
        if abs(mass-boundary)>mtol:causes.append('class_bulk_mass')
        if any(x>1 for x in frac):causes.append('fraction_above_one')
        if causes:flags.append(dict(year=y,julian=day,causes=causes,fraction_sum=str(fsum),fraction_bound=str(ftol),class_mass_kg=str(mass),bulk_mass_kg=str(boundary),mass_bound_kg=str(mtol),pass_tokens=f,element_tokens=er))
    return dict(case=r['case'],record=str(record),record_sha256=digest(record),pass_sha256=digest(p),element_sha256=digest(e),events=rows,positive_events=positive,flags=flags,passed=not flags)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--pattern',default='seed-*/*/record.json');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    rows=[audit(p) for p in sorted(args.root.glob(args.pattern))]
    assert rows
    result=dict(cases=len(rows),events=sum(r['events'] for r in rows),positive_events=sum(r['positive_events'] for r in rows),flagged_cases=sum(not r['passed'] for r in rows),flagged_events=sum(len(r['flags']) for r in rows),rows=rows,script_sha256=digest(Path(__file__)))
    args.output.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'},flush=True)
if __name__=='__main__':main()
