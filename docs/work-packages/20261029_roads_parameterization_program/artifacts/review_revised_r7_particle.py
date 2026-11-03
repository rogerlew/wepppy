from pathlib import Path
import hashlib, json, subprocess, struct, importlib.util, tarfile
from fractions import Fraction as F
from decimal import Decimal
root=Path('/wc1/runs/ro/roads-parameterization-program-20261103/particle-observation-r7-v3')
art=Path('/home/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((root/'declaration.json').read_text()); r=json.loads((root/'result.json').read_text())
m=json.loads((root/'retention-manifest.json').read_text())
for p,h in m.items(): assert sha(root/p)==h,p
assert hashlib.sha256(subprocess.check_output(['git','-C','/workdir/wepp-forest-release-20261009','archive',d['source_commit'],'src','fpm-src'])).hexdigest()==r['source_archive_sha256']==sha(root/'source.tar')
assert sha(root/'declaration.json')==r['declaration_sha256']
assert sha(root/'source-record.json')==d['source_record_sha256']
assert sha(root/'helper.py')==d['helper_sha256']
assert sha(root/'trace.txt')==r['trace_sha256']
for name,key in [('wepp_261029','installed_sha256'),('wepp_261029_hill','hill_sha256')]: assert sha(Path('/home/workdir/wepppy/wepp_runner/bin')/name)==d[key]
with tarfile.open(root/'source.tar') as tar:
    for name in ['enrich.for','sloss.for']:
        assert tar.extractfile('src/'+name).read()==(root/(name+'.original')).read_bytes()
for lane in r['results']:
    p=root/lane['lane']
    assert sha(root/('wepp-'+lane['lane']))==lane['binary_sha256']
    for name,h in d['inputs'].items(): assert sha(p/'runs'/name)==h
    for name,h in d['expected_outputs'].items(): assert sha(p/'output'/name)==h==lane['outputs'][name]
rows=[x.split() for x in (root/'trace.txt').read_text().splitlines()]
f32=lambda x:struct.unpack('<f',struct.pack('<f',float(x)))[0]
cls,final=rows
assert cls[:5]==['PM_CLASS','2003','29','3','3'] and final[:4]==['PM_FINAL','2003','29','3']
loads=[f32(x) for x in cls[6:11]]; total=f32(cls[5]); fs=[f32(x) for x in final[5:]]
s=0.
for x in loads:s=f32(s+x)
assert s==total and all(x>=2**-126 for x in loads)
assert [f32(x/total) for x in loads]==fs==r['final_fractions']
u=F(1,2**24); g4=4*u/(1-4*u); bound=(g4+u)/(1-g4)
excess=sum(map(F,fs))-1
assert abs(excess)<=bound and float(excess)==r['fraction_excess']
spec=importlib.util.spec_from_file_location('audit',art/'audit_particle_closure_v2.py'); audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
record=Path('/wc1/runs/ro/roads-parameterization-program-20261103/panel840-v1/cases')/d['case']/'record.json'
a=audit.audit(record)
assert not a['passed'] and len(a['flags'])==1 and a['flags'][0]['causes']==['fraction_sum']
flag=a['flags'][0]; tokens=flag['pass_tokens'][20:25]; errs=[F(Decimal(t))-F(v) for t,v in zip(tokens,fs)]
assert all(abs(e)<=F(audit.quantum(t)) for e,t in zip(errs,tokens))
assert sum(F(Decimal(t)) for t in tokens)-1==excess+sum(errs)
print(json.dumps({'retention_files':len(m),'declaration_sha256':sha(root/'declaration.json'),'result_sha256':sha(root/'result.json'),'archive_matches_git':True,'input_output_hashes_match':True,'normalization_excess':float(excess),'derived_bound':float(bound),'print_decomposition_exact':True,'strict_audit_passed':a['passed'],'flag_count':len(a['flags']),'reviewed_disposition_sha256':sha(art/'revised-r7-particle-disposition.json')},indent=2))
