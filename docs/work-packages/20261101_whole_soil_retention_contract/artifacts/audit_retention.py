"""Actual Horizon + 7778 serialization; explicitly controlled single-horizon context."""
import argparse,copy,hashlib,inspect,json,math,platform
from pathlib import Path
import rosetta
import wepppy.soils.ssurgo.ssurgo as ss
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.wepp.soils import horizon_boundary,horizon_mixin,rock_fragments

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def finite(x):return isinstance(x,(int,float)) and math.isfinite(x)
def cpm(w,bd):return (2.65*(1-w))/(w*bd+2.65*(1-w))
def synthetic():
 base=dict(hzname='A',hzdepb_r=30.,hzdept_r=0.,hzthk_r=30.,dbthirdbar_r=1.3,ksat_r=12.,sandtotal_r=55.,claytotal_r=20.,om_r=2.,cec7_r=10.,fraggt10_r=0.,frag3to10_r=0.,desgnmaster='A',sieveno10_r=70.,wthirdbar_r=30.,wfifteenbar_r=10.,sandvf_r=5.,ll_r=None)
 rows=[]
 for w in (0.,10.,30.,49.9,50.,50.1,70.,85.,95.):
  for bd in (1.,1.3,1.6):rows.append((f'mass{w}-density{bd}',dict(base,sieveno10_r=100-w,dbthirdbar_r=bd)))
 for name,change in [('missing-density',{'dbthirdbar_r':None}),('missing-FC',{'wthirdbar_r':None}),('missing-WP',{'wfifteenbar_r':None}),('missing-both',{'wthirdbar_r':None,'wfifteenbar_r':None}),('invalid-pair',{'sieveno10_r':50.,'wthirdbar_r':70.,'wfifteenbar_r':40.}),('zero-retention',{'wthirdbar_r':0.,'wfifteenbar_r':0.})]:rows.append((name,dict(base,**change)))
 return rows

def run(source,out):
 out.mkdir();raw=json.loads(source.read_text());cases=[]
 if len(raw)!=39 or len({x['chkey'] for x in raw})!=39:raise ValueError('Source identity/count drift')
 for row in raw:
  layer={k:(float(v) if v is not None and k.endswith('_r') and k not in ('desgnmaster',) else v) for k,v in row.items()}
  cases.append(('source-'+row['chkey'],'current-SDA-horizon',layer))
 for i,(name,layer) in enumerate(synthetic()):cases.append((name,'synthetic',dict(layer,chkey=str(900000001+i),cokey='9000000',mukey='9000000')))
 sources=[Path(__file__),Path(ss.__file__),Path(horizon_boundary.__file__),Path(horizon_mixin.__file__),Path(rock_fragments.__file__),Path(inspect.getfile(WeppSoilUtil))]
 deps={str(p):sha(p) for p in sources};rp=Path(rosetta.__file__).parent
 deps.update({str(p):sha(p) for p in rp.rglob('*') if p.is_file() and '__pycache__' not in str(p)})
 save(out/'declaration.json',dict(source=str(source),source_sha256=sha(source),dependencies=deps,python=platform.python_version(),cases=[dict(id=n,kind=k,source=x) for n,k,x in cases],scope='Actual Horizon and write7778 in controlled single-horizon context; no profile selection/native run'))
 results=[]
 for name,kind,layer in cases:
  dest=out/name;dest.mkdir();record=dict(id=name,kind=kind,source=copy.deepcopy(layer));save(dest/'source.json',record)
  # Context labels have no retention or numeric material role.
  data=dict(layer,texture='retention-audit',reskind=None,fragvol_r=None)
  try:h=ss.Horizon(str(layer['chkey']),data,defaults={})
  except (ValueError,TypeError,ZeroDivisionError) as error:
   record.update(status='construction-unavailable',error_type=type(error).__name__,error=str(error));save(dest/'readback.json',record);results.append(record);continue
  record['prepared']=dict(mass_percent=h.smr,density=h.dbthirdbar_r,fc=h.field_cap,wp=h.wilt_pt,valid=bool(h.valid()),notes=h.horizon_build_notes)
  pair_sanitized=any('sanitized' in n for n in h.horizon_build_notes)
  record['final_branches']={field:('rosetta-pair-sanitization' if pair_sanitized else 'source-capped-mass' if finite(layer.get(src)) and finite(h.smr) else 'rosetta-missing-source-or-rock') for field,src in [('fc','wthirdbar_r'),('wp','wfifteenbar_r')]}
  w=h.smr/100 if finite(h.smr) else None;bd=layer.get('dbthirdbar_r')
  if w is not None and 0<=w<1 and finite(bd) and bd>0:
   share=cpm(w,bd);den=1-min(.5,w);record['source_basis_diagnostic']=dict(cpm_at_source_density=share,existing_mass_complement=den,CPM_only_ratio_to_source=share/den,volume_inverse_fc=None if not finite(layer.get('wthirdbar_r')) else layer['wthirdbar_r']/100/share,volume_inverse_wp=None if not finite(layer.get('wfifteenbar_r')) else layer['wfifteenbar_r']/100/share,assumption='Nonporous fragments, additive volumes, source density treated as fine-earth density; not a proposed final native law')
  if not h.valid() or not finite(h.smr):
   record['status']='serialization-unavailable';save(dest/'readback.json',record);results.append(record);continue
  soil=ss.WeppSoil.__new__(ss.WeppSoil);soil.log=[];soil.mukey=int(layer['mukey']);soil.description='# Controlled retention audit: '+name;soil.num_ofes=1;soil.ksflag=0;soil.is_urban=False;soil.is_water=False;soil.initial_sat=.75;soil.majorComponent=ss.MajorComponent(dict(muname='controlled single horizon',albedodry_r=.16));soil.horizons=[h];soil.horizons_mask=[1];soil.num_layers=1;soil.res_lyr_i=None;soil.res_lyr_ksat=None
  soil.write(wd=str(dest),fname='audit.sol',overwrite=False,version='7778');file=dest/'audit.sol';parsed=WeppSoilUtil(str(file)).obj;ofe=parsed['ofes'][0];emitted=ofe['horizons']
  for e in emitted:
   for key,value,precision in [('fc',h.field_cap,4),('wp',h.wilt_pt,4),('bd',h.dbthirdbar_r,2),('rfg',h.smr,2)]:
    if float(e[key])!=float(f'{value:.{precision}f}'):raise ValueError('Serialized numeric drift '+name+key)
  depths=[float(e['solthk']) for e in emitted]
  if 200. not in depths or depths!=sorted(set(depths)):raise ValueError('Boundary/depth support')
  e=emitted[0];share=cpm(min(.85,float(e['rfg'])/100),float(e['bd']))
  record.update(status='serialized',artifact_sha256=sha(file),emitted=emitted,emitted_cap_projection=dict(cpm=share,fc_CPM_only=float(e['fc'])*share,wp_CPM_only=float(e['wp'])*share,source_native_density_equal_assumption=True,native_executed=False),artifact_CRLF=(b'\r\n' in file.read_bytes()))
  save(dest/'readback.json',record);results.append(record)
 if sha(source)!=json.loads((out/'declaration.json').read_text())['source_sha256']:raise ValueError('Source mutated')
 if any(sha(p)!=digest for p,digest in deps.items()):raise ValueError('Dependency changed')
 save(out/'receipt.json',dict(passed=True,results=results,source_unchanged=True,dependencies_unchanged=True))
 print({s:sum(r['status']==s for r in results) for s in {r['status'] for r in results}})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.source,a.out)
