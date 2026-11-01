"""Independent read-only native REAL reconstruction at retained INFPAR clock."""
import argparse,csv,hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]
ACCEPTED=BASE/'buffer-roughness-hillslope-response-r4/attempt-u2'
PACKET=Path('/home/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def f(x):return struct.unpack('f',struct.pack('f',x))[0]
def unique(rows,tag,index=None):
 r=[x for x in rows if x['tag']==tag and (index is None or x['index']==index)]
 if len(r)!=1:raise ValueError((tag,index,len(r)))
 return r[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--accepted',type=Path,required=True);ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 accepted=a.accepted;packet=a.packet;out=a.out;out.mkdir(parents=True,exist_ok=False)
 bindings={}
 def bind(p):
  st=p.stat();bindings[str(p)]={'sha256':sha(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
  return p
 manifest=json.loads(bind(packet/'manifest.json').read_text());assert sha(packet/'manifest.json')=='a31ace8d9c7f866e607dedff7162ad0dc6ba69ed9495a2896ef6ade5ddfafbc1'
 assert sha(packet/'initial-layers.csv')==manifest['files']['initial-layers.csv']
 bind(accepted/'build/src/infpar.for')
 initial={}
 for r in csv.DictReader(bind(packet/'initial-layers.csv').open()):
  k=(r['stratum'],r['lane'],int(r['mode']),int(r['ofe']),int(r['layer']))
  assert k not in initial;initial[k]=r
 declaration=json.loads(bind(accepted/'execution-declaration.json').read_text())
 rows=[]
 for task in declaration['tasks']:
  p=bind(Path(task['folder'])/'observations/buffer-observation.txt');groups={}
  record=json.loads(bind(Path(task['folder'])/'record.json').read_text());assert sha(p)==record['observer_files']['buffer-observation.txt'],'accepted trace drift'
  for line,text in enumerate(p.read_text().splitlines(),1):
   t=text.split();tag=t[0];year,day,ofe,ix=map(int,t[1:5]);vals=list(map(float,t[5:]));assert len(vals)==6
   groups.setdefault((year,day,ofe),[]).append(dict(tag=tag,index=ix,v=vals,line=line))
  for (year,day,ofe),g in groups.items():
   if not ofe:continue
   obs=unique(g,'BP_INFPAR');ww=[unique(g,'BP_SOIL_W',i) for i in (1,2)];kk=[unique(g,'BP_SOIL_K',i) for i in (1,2)]
   assert all(obs['line']<r['line'] for r in ww+kk),'SOIL epoch ordering'
   totaldepth=ww[1]['v'][5];assert totaldepth==f(ww[0]['v'][4]+ww[1]['v'][4])
   avpor=avcpm=avdry=f(0)
   for i,(w,k) in enumerate(zip(ww,kk),1):
    weight=f(w['v'][4]/totaldepth);cpm=float(initial[task['stratum'],task['lane'],task['mode'],ofe,i]['fine_earth_factor'])
    avpor=f(avpor+f(k['v'][2]*weight));avdry=f(avdry+f(w['v'][3]*weight));avcpm=f(avcpm+f(cpm*weight))
   avpor=max(0.,min(1.,avpor))
   raw=f(f(f(ww[0]['v'][0]+ww[1]['v'][0])/totaldepth)+avdry)
   first=raw>avpor;afterfirst=f(avpor*f(.98)) if first else raw
   ceiling=f(avpor*avcpm);second=afterfirst>=ceiling;aftersecond=f(ceiling*f(.99)) if second else afterfirst
   theta=f(ceiling-aftersecond)
   rows.append(dict(stratum=task['stratum'],lane=task['lane'],mode=task['mode'],year=year,day=day,ofe=ofe,infpar_line=obs['line'],soil_snapshot_line=ww[0]['line'],depth_m=totaldepth,avpor=avpor,observed_avpor=obs['v'][4],avcpm=avcpm,raw_avsat=raw,after_first_avsat=afterfirst,bulk_ceiling=ceiling,after_second_avsat=aftersecond,dtheta=theta,observed_dtheta=obs['v'][3],first_branch_reconstructed=first,second_branch_reconstructed=second,avpor_exact=avpor==obs['v'][4],dtheta_exact=theta==obs['v'][3]))
 assert len(rows)==216,len(rows)
 with (out/'infpar.csv').open('w',newline='') as s:
  w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 for path,v in bindings.items():
  p=Path(path);st=p.stat();assert {'sha256':sha(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}==v
 receipt={'passed':all(r['avpor_exact'] and r['dtheta_exact'] for r in rows),'groups':len(rows),'avpor_exact':sum(r['avpor_exact'] for r in rows),'dtheta_exact':sum(r['dtheta_exact'] for r in rows),'first_branch_reconstructed':sum(r['first_branch_reconstructed'] for r in rows),'second_branch_reconstructed':sum(r['second_branch_reconstructed'] for r in rows),'table_sha256':sha(out/'infpar.csv'),'script_sha256':sha(Path(__file__)),'bindings':bindings,'scope':'SOIL/INFPAR clock; native float32 arithmetic reconstruction, not directly logged branch bit and not GRNA snapshot. Mean(POR)*mean(CPM) preserved.'}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print({k:v for k,v in receipt.items() if k!='bindings'})
if __name__=='__main__':main()
