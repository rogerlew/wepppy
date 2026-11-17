"""Validate exact project evidence; only explicit volatile metadata is normalized."""
from pathlib import Path
import hashlib,json,re
import pyarrow.parquet as pq

OUT=Path('/tmp/roads-refactor-validation/project-candidate-20261117b-comparison.json')
DESIGNS=['inslope_bd','inslope_rd','outslope_rutted','unrutted-positive','unrutted-negative']

def sha(data):return hashlib.sha256(data).hexdigest()
def digest(p):return sha(p.read_bytes())
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def normalize_bytes(data,root):
 data=data.replace(str(root).encode(),b'<ROOT>')
 # Separate worktree copies retain identical executable bytes but have distinct mtimes.
 return re.sub(rb'(?<=binary_mtime_ns=)\d+',b'<MTIME>',data)
def paths(root):
 result={}
 for sub in ['wepp/roads/runs','wepp/roads/segments','wepp/roads/output']:
  for p in (root/sub).rglob('*'):
   if p.is_file():
    key=re.sub(r'/parameterization-[^/]+/', '/parameterization-<SCRATCH>/',str(p.relative_to(root)))
    assert key not in result,key
    result[key]=p
 if root.name.endswith('unrutted-negative'):
  summary=json.loads((root/'roads.nodb').read_text())['py/state']['_last_run_summary']
  matches=[p for p in (root/'wepp/roads/history').glob('*/wepp/roads/segments/roads.segment.pass.manifest.json') if json.loads(p.read_text())==summary['segment_execution_records']]
  assert len(matches)==1,('exact failed-attempt manifest',root,len(matches))
  archive=matches[0].parents[3]
  for p in archive.rglob('*'):
   if p.is_file():
    key='failed-attempt/'+re.sub(r'/parameterization-[^/]+/', '/parameterization-<SCRATCH>/',str(p.relative_to(archive)))
    assert key not in result
    result[key]=p
 return result

def differences(a,b,path=''):
 if type(a)!=type(b):return [path+':type']
 if isinstance(a,dict):
  return [path+':keys'] if a.keys()!=b.keys() else sum((differences(a[k],b[k],path+'/'+str(k)) for k in a),[])
 if isinstance(a,list):
  return [path+':length'] if len(a)!=len(b) else sum((differences(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
 return [] if a==b else [path]

receipts=[]
for design in DESIGNS:
 roots=[Path('/wc1/runs/rq/roads-quality-'+label+'-'+design) for label in ['baseline-20261117a','candidate-20261117b']]
 manifests=[json.loads((r/'validation-artifact-manifest.json').read_text()) for r in roots]
 assert manifests[0]['native_binaries']==manifests[1]['native_binaries'],design
 allpaths=[paths(r) for r in roots]
 assert allpaths[0].keys()==allpaths[1].keys(),(design,'file membership',set(allpaths[0])^set(allpaths[1]))
 validated=set(); details=[]; problems=[]
 def compare_file(key,ps):
  a,b=[p.read_bytes() for p in ps]
  for i,p in enumerate(ps):
   rel=str(p.relative_to(roots[i]))
   if rel in manifests[i]['artifacts']:assert digest(p)==manifests[i]['artifacts'][rel],(design,rel,'manifest')
  if ps[0].suffix=='.parquet':
   x,y=[pq.read_table(p) for p in ps]
   metadata=[]
   for i,t in enumerate([x,y]):
    m=dict(t.schema.metadata or {})
    if b'source_sha256' in m:m[b'source_sha256']=canon(hash_map(json.loads(m[b'source_sha256']),i)).encode()
    metadata.append(m)
   equal=metadata[0]==metadata[1] and x.schema.equals(y.schema,check_metadata=False) and x.replace_schema_metadata(None).equals(y.replace_schema_metadata(None))
   mode='parquet schema, metadata mappings, ordered rows exact'
   detail={'rows':x.num_rows,'columns':x.num_columns}
  else:
   equal=normalize_bytes(a,roots[0])==normalize_bytes(b,roots[1]);mode='bytes except exact root and executable diagnostic mtime';detail={}
  if equal:validated.add(key)
  else:problems.append({'path':key,'type':mode})
  details.append({'path':key,'equal':equal,'raw_equal':a==b,'mode':mode,**detail})
 def hash_map(v,i):
  out={}
  for rel,h in v.items():
   ps=[r/rel for r in roots]
   assert digest(ps[i])==h,(design,rel,'linked hash')
   if rel not in validated:compare_file(rel,ps)
   assert rel in validated,(design,rel,'unproved digest normalization')
   out[rel]='<VERIFIED:'+rel+'>'
  return out
 for key in allpaths[0]:
  if not key.endswith('.json') and key not in validated:compare_file(key,[p[key] for p in allpaths])
 def clean(value,i,path):
  value=json.loads(json.dumps(value).replace(str(roots[i]),'<ROOT>'))
  if path.endswith('roads.inslope.summary.json'):value.pop('prepared_at')
  elif path.endswith('roads.parameterization.comparison.json') or path=='parameterization_comparison':
   value.pop('completed_at');value.pop('run_id');value['sources']=hash_map(value['sources'],i)
  elif path.endswith('roads.current.json'):
   assert value['parameterization_snapshot_sha256']==digest(roots[i]/'wepp/roads/output/roads.parameterization.comparison.json')
   value['parameterization_snapshot_sha256']='<VERIFIED:roads.parameterization.comparison.json>'
  elif path.endswith('roads.accounting.json'):
   raw=json.loads((roots[i]/path).read_text())
   allocation={k:raw[k] for k in ['policy','area_basis','sources','targets','inputs']}
   expected=sha(canon(allocation).encode())
   for key in ['composition_allocation_sha256','products_allocation_sha256','routed_allocation_sha256']:
    if key in value:assert value[key]==expected;value[key]='<VERIFIED:allocation>'
   for key in ['inputs','canonical_pass','products']:
    if key in value:value[key]=hash_map(value[key],i)
  return value
 for key in allpaths[0]:
  if key.endswith('.json'):
   a,b=[clean(json.loads(p[key].read_text()),i,key) for i,p in enumerate(allpaths)]
   delta=differences(a,b)
   details.append({'path':key,'equal':not delta,'mode':'JSON exact after documented verified links and volatile fields','differences':delta})
   if delta:problems.append({'path':key,'type':'JSON','differences':delta})
 summaries=[json.loads((r/'roads.nodb').read_text())['py/state']['_last_run_summary'] for r in roots]
 for i,s in enumerate(summaries):
  for key in ['completed_at','failed_at']:
   s.pop(key,None)
  if s.get('roads_report_resources'):s['roads_report_resources'].pop('generated_at',None)
  if s.get('parameterization_comparison'):s['parameterization_comparison']=clean(s['parameterization_comparison'],i,'parameterization_comparison')
  summaries[i]=json.loads(json.dumps(s).replace(str(roots[i]),'<ROOT>'))
 delta=differences(*summaries)
 if delta:problems.append({'path':'roads.nodb/_last_run_summary','type':'durable summary','differences':delta})
 receipt={'design':design,'roots':[str(r) for r in roots],'native_binaries':manifests[0]['native_binaries'],'files_compared':len(details),'raw_equal_files':sum(x.get('raw_equal',False) for x in details),'problems':problems,'details':details,'pass':not problems}
 receipts.append(receipt)
 print(design,len(details),'files','problems',json.dumps(problems),flush=True)
 OUT.write_text(json.dumps({'projects':receipts,'pass':all(r['pass'] for r in receipts)},indent=2))
assert len(receipts)==5 and all(r['pass'] for r in receipts)
