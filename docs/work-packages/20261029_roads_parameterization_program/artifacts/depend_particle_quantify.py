from pathlib import Path
from decimal import Decimal
import json,datetime,hashlib,math
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/depend-bounded-g1')
review=json.load(open('/tmp/depend-particle-review.json'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def event(p,y,d):
 ls=p.read_text().splitlines()
 for j,l in enumerate(ls):
  f=l.split()
  if f[:3]==['EVENT',y,d]:
   raw=l+'\n'
   if len(f)<27:raw+=ls[j+1]+'\n';f+=ls[j+1].split()
   return f,raw,ls
 raise ValueError((p,y,d))
def q(token):return .5*float(Decimal(10)**Decimal(token).as_tuple().exponent)
rows=[]
for panel in review:
 for failure in review[panel]['failures']:
  rec=Path(failure[0]);r=json.loads(rec.read_text());old=Path(r['source']);y,d=failure[1][1:]
  f,raw,ls=event(rec.parent/'output/H1.pass.dat',y,d);of,oraw,ols=event(old/'output/H1.pass.dat',y,d)
  frac=list(map(float,f[20:25]));conc=list(map(float,f[15:20]));vol=float(f[7]);fsum=sum(frac);mass=vol*sum(conc)
  year0=int(ls[2].split()[1]);year=int(y);day=int(d);date=datetime.date(year,1,1)+datetime.timedelta(days=day-1)
  ey=year-year0+1
  er=next(l.split() for l in (rec.parent/'output/H1.element.dat').read_text().splitlines() if l.split()[:4]==['3',str(date.day),str(date.month),str(ey)])
  old_er=next(l.split() for l in (old/'output/H1.element.dat').read_text().splitlines() if l.split()[:4]==er[:4]);assert old_er==er
  boundary=float(er[23])*r['width_m'];btol=q(er[23])*r['width_m'];mtol=q(f[7])*sum(conc)+abs(vol)*sum(q(t) for t in f[15:20])+q(f[7])*sum(q(t) for t in f[15:20])
  rows.append(dict(panel=panel,case=r['case'],year=year,day=day,old_pass_sha256=sha(old/'output/H1.pass.dat'),candidate_pass_sha256=sha(rec.parent/'output/H1.pass.dat'),old_element_sha256=sha(old/'output/H1.element.dat'),candidate_element_sha256=sha(rec.parent/'output/H1.element.dat'),source_record_sha256=sha(old/'record.json'),candidate_record_sha256=sha(rec),old_pass_row=oraw,candidate_pass_row=raw,pass_row_exact=oraw==raw,element_row_exact=old_er==er,fraction_values=frac,fraction_sum=fsum,fraction_sum_delta=fsum-1,fraction_print_rounding_bound=sum(q(t) for t in f[20:25]),class_concentration_kg_m3=conc,runoff_volume_m3=vol,class_mass_kg=mass,boundary_mass_kg=boundary,class_minus_boundary_kg=mass-boundary,printed_mass_comparison_bound_kg=btol+mtol,boundary_element_row=' '.join(er),implied_fraction_excess_mass_kg=mass*(fsum-1)/fsum))
result=dict(rows=rows,interpretation='PASS concentrations kg/m3 per SLOSS; mass=sum(class concentration)*EVENT runoff volume. ELEMENT last-OFE SedLeave kg/m times recorded width. Printing bound sums half-last-place errors with product propagation; not a fitted tolerance. Fraction anomaly pre-exists if complete EVENT row identical. Tiny residuals near float epsilon are distinguished from substantial existing excess, not silently waived.')
Path('/tmp/depend-particle-quantification.json').write_text(json.dumps(result,indent=2)+'\n')
for row in sorted(rows,key=lambda r:abs(r['class_minus_boundary_kg']),reverse=True)[:5]:print({k:row[k] for k in ['panel','case','year','day','fraction_sum','fraction_print_rounding_bound','class_mass_kg','boundary_mass_kg','class_minus_boundary_kg','printed_mass_comparison_bound_kg','pass_row_exact']})
