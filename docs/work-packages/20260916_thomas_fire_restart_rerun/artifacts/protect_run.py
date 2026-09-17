"""Retain immutable before/after evidence for the authorized named acceptance."""
from pathlib import Path
import hashlib,json,sys,zipfile
root=Path('/wc1/runs/ne/nervous-mesquite')
out=Path(__file__).parent
protected={}
for name in ('dem','watershed','soils','climate','disturbed','landuse','rusle','polaris'):
    folder=root/name
    for path in sorted(folder.rglob('*')) if folder.is_dir() else []:
        if path.is_file() and not path.is_symlink():
            protected[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    path=root/(name+'.nodb')
    if path.is_file():protected[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
for name in ('ron.nodb',):
    path=root/name
    protected[name]=hashlib.sha256(path.read_bytes()).hexdigest()
if sys.argv[1]=='before':
    attempts={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (root/'postfire_debris_flow').rglob('*') if p.is_file() and not p.is_symlink()}
    (out/'nervous_protected_before.json').write_text(json.dumps(protected,indent=2)+'\n')
    (out/'nervous_attempts_before.json').write_text(json.dumps(attempts,indent=2)+'\n')
    (out/'nervous_state_before.nodb').write_bytes((root/'postfire_debris_flow.nodb').read_bytes())
    print('Captured',len(protected),'protected inputs and',len(attempts),'prior module records')
else:
    before=json.loads((out/'nervous_protected_before.json').read_text())
    changed=[p for p in before.keys()|protected.keys() if before.get(p)!=protected.get(p)]
    old=json.loads((out/'nervous_attempts_before.json').read_text())
    replaced=[p for p,h in old.items() if '/attempts/' in p and (not (root/p).is_file() or hashlib.sha256((root/p).read_bytes()).hexdigest()!=h)]
    metadata_only=[]
    archive=json.loads((out/'baseline_archive.json').read_text())['path']
    with zipfile.ZipFile(archive) as z:
        for name in changed:
            if name.endswith('.nodb'):
                previous=json.loads(z.read(name))['py/state'];current=json.loads((root/name).read_text())['py/state']
                keys=[k for k in previous.keys()|current.keys() if previous.get(k)!=current.get(k)]
                if keys==['_nodb_mtime']:metadata_only.append(name)
    scientific_changes=[name for name in changed if name not in metadata_only]
    result={'protected_files':len(before),'byte_changes':changed,'serialization_timestamp_only':metadata_only,
            'scientific_changes':scientific_changes,'prior_module_files':len(old),'replaced_attempt_files':replaced}
    (out/'nervous_preservation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));assert not scientific_changes and not replaced
