"""Independent read-only replay of legacy EVENT particle accounting.

ELEMENT descriptors are taken from SEDOUT format1000/CONTIN format1200.
Keep the prior Decimal printing-error bounds unchanged; correct only field
boundaries. Native sources, run outputs, and the production audit are untouched.
"""
from pathlib import Path
from decimal import Decimal as D
import argparse, datetime, hashlib, json

WIDTHS = [3,3,3,5,9,9,8,8,8,6,8,8,8,7]+[9]*4+[7]*5+[9]*3
assert len(WIDTHS)==26

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def quantum(t):return D(10)**D(t).as_tuple().exponent/D(2)
def fixed(line):
    fields=[];pos=0
    for width in WIDTHS:
        fields.append(line[pos:pos+width].strip());pos+=width
    assert not line[pos:].strip(), line
    assert all(fields), line
    return fields

def audit(record):
    r=json.loads(record.read_text());base=record.parent
    pf=base/'output/H1.pass.dat';ef=base/'output/H1.element.dat'
    assert sha(pf)==r['outputs'][pf.name] and sha(ef)==r['outputs'][ef.name]
    elements={};collapsed=0
    for line in ef.read_text().splitlines()[2:]:
        f=fixed(line);key=tuple(map(int,f[:4]));assert key not in elements
        elements[key]=(f,line);collapsed+=len(line.split())!=26
    plines=pf.read_text().splitlines();first=int(plines[2].split()[1])
    width=D(str(r['width_m']));events=0;flags=[];corrected=[]
    for i,line in enumerate(plines):
        f=line.split()
        if not f or f[0]!='EVENT':continue
        offset=1
        while len(f)<27:f+=plines[i+offset].split();offset+=1
        assert len(f)==27
        events+=1;y,j=map(int,f[1:3]);dt=datetime.date(y,1,1)+datetime.timedelta(days=j-1)
        e,raw=elements[(3,dt.day,dt.month,y-first+1)]
        conc=list(map(D,f[15:20]));frac=list(map(D,f[20:25]))
        assert all(x.is_finite() and x>=0 for x in conc+frac)
        vol=D(f[7]);mass=vol*sum(conc);bulk=D(e[23])*width
        mtol=quantum(f[7])*sum(conc)+abs(vol)*sum(quantum(t) for t in f[15:20])+quantum(f[7])*sum(quantum(t) for t in f[15:20])+quantum(e[23])*width
        causes=[]
        if sum(conc) and abs(sum(frac)-1)>sum(quantum(t) for t in f[20:25]):causes.append('fraction_sum')
        if abs(mass-bulk)>mtol:causes.append('class_bulk_mass')
        if any(x>1 for x in frac):causes.append('fraction_above_one')
        row=dict(year=y,julian=j,causes=causes,class_mass_kg=str(mass),bulk_mass_kg=str(bulk),mass_bound_kg=str(mtol),SedLeave=e[23],QRain=e[24],width_m=str(width))
        if causes:flags.append(row)
        split=raw.split()
        oldbulk=D(split[23])*width
        oldtol=quantum(f[7])*sum(conc)+abs(vol)*sum(quantum(t) for t in f[15:20])+quantum(f[7])*sum(quantum(t) for t in f[15:20])+quantum(split[23])*width
        if abs(mass-oldbulk)>oldtol:
            corrected.append(dict(**row,raw_element=raw,old_whitespace_tokens=len(split),old_misread_SedLeave=split[23],old_bulk_mass_kg=str(oldbulk),EffDur=e[8],Enrich=e[9]))
    return dict(record=str(record),record_sha256=sha(record),case=r['case'],binary_sha256=r['binary_sha256'],pass_sha256=sha(pf),element_sha256=sha(ef),events=events,collapsed_element_rows=collapsed,flags=flags,formerly_mass_flagged=corrected)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--r4',type=Path,required=True);ap.add_argument('--native',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    rows=[]
    for p in sorted((a.r4/'cases').glob('*/record.json')):
        r=json.loads(p.read_text());rows.append(dict(r4=audit(p),r3=audit(Path(r['source'])/'record.json')))
    assert len(rows)==116
    counts={}
    for lane in ('r3','r4'):
        counts[lane]=dict(cases=len(rows),events=sum(r[lane]['events'] for r in rows),prior_mass_flags=sum(len(r[lane]['formerly_mass_flagged']) for r in rows),corrected_flags=sum(len(r[lane]['flags']) for r in rows),collapsed_element_rows=sum(r[lane]['collapsed_element_rows'] for r in rows))
        assert counts[lane]['prior_mass_flags']==91
    result=dict(disposition='Audit contract defect: whitespace tokenization aliases QRain as SedLeave when adjacent F7.3/F6.3 fields fill their widths; no native mass defect established by these flags',counts=counts,widths=WIDTHS,element_record_width=sum(WIDTHS),same_calendar_units_width_event_selection_and_decimal_bounds=True,script_sha256=sha(Path(__file__)),native_sha256={n:sha(a.native/'src'/n) for n in ['sedout.for','contin.for','outfil.for','sloss.for','wshpas.for']},rows=rows)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(counts))
if __name__=='__main__':main()
