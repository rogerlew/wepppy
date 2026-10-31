from pathlib import Path
import json,hashlib,collections
W=Path('/workdir/wepppy');P=W/'out/roads-parameterization-program-20261031';A=W/'docs/work-packages/20261029_roads_parameterization_program/artifacts';C=P/'param-sign-u12-combined'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def key(r):return tuple(r[k] for k in ('climate','soil','design','surface','traffic'))
refs={key(r['case']):r['reference_kg_yr'] for r in json.loads((W/'out/roads-native-funding-20261031/r3-matrix840/magnitude-scores.json').read_text())}
rows=json.loads((C/'roads-results.json').read_text());fails=[];groups=collections.Counter()
for r in rows:
 ref=refs[key(r['case'])];v=r['metrics']['sediment_export_kg_yr'];within=.1<=v/ref<=10 if ref>1 else v<=max(1,10*ref)
 if within:continue
 folder=Path(r['folder']);assert r['binary_sha256']=='2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48'
 for n,h in r['outputs'].items():assert sha(folder/'output'/n)==h
 group=('meaningful_low' if v<ref/10 else 'meaningful_high') if ref>1 else 'small_exceedance';groups[group]+=1
 fails.append(dict(case=r['case'],group=group,reference_kg_yr=ref,export_kg_yr=v,record_sha256=sha(folder/'record.json'),sediment_boundaries=r['audit']['sediment']['ofes'],water_boundaries=r['audit']['water']['ofes']))
result=dict(engine='wepp_261029 revision4',groups=dict(groups),failed_cases=fails,scope='Rehashed failed-case native outputs; existing accepted audit values. Net OFE boundary exchange is not tagged particle provenance.')
(A/'revision4-residual-attribution.json').write_text(json.dumps(result,indent=2)+'\n')
print(groups)
for group in groups:
 rs=[r for r in fails if r['group']==group]
 print(group, 'surfaces',dict(collections.Counter(r['case']['surface'] for r in rs)), 'designs',dict(collections.Counter(r['case']['design'] for r in rs)))
for r in sorted([r for r in fails if r['group']=='small_exceedance'],key=lambda r:r['export_kg_yr'],reverse=True)[:8]:
 print(r['case'],r['reference_kg_yr'],r['export_kg_yr'],[o['boundary_kg_yr'] for o in r['sediment_boundaries']],[o['net_kg_yr'] for o in r['sediment_boundaries']])
