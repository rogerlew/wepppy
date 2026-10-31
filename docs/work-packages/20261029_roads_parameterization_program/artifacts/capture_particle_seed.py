from pathlib import Path
import hashlib,json,tarfile
A=Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts')
P=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
name='site-1718465-outunrut-gravel-low-erosion_road_cap-project'
folders={'seed':P/'downstream-hydraulics-r3/cases/buffer_cap'/name,'control':Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-matrix840/matrix-v1')/name}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt={'status':'observation fixture; no repair accepted','event':{'year':2012,'julian':302},'cases':{}}
archive=A/'particle-closure-inputs.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for lane,folder in folders.items():
  r=json.loads((folder/'record.json').read_text())
  for fn,digest in r['inputs'].items():
   p=folder/'runs'/fn;assert sha(p)==digest;tar.add(p,arcname=lane+'/runs/'+fn)
  receipt['cases'][lane]={'source':str(folder),'record_sha256':sha(folder/'record.json'),'case':r['case'],'inputs':r['inputs'],'outputs':r['outputs'],'binary_sha256':r['binary_sha256']}
receipt['fixture_sha256']=sha(archive)
(A/'particle-closure-fixture.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(archive.stat().st_size)
