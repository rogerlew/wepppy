"""Compare release sources to retained build tree, accounting for make's sizing swap."""
import hashlib
import json
from pathlib import Path
import subprocess

repo='/workdir/wepp-forest'
release='f24c957e3633898e0fd4cbbea5ae08c781f29dba'
root=Path('/workdir/wepp-forest-holdouts/20261006-surface-return.6SeF9A')
b=root/'baseline/src'; c=root/'candidate/src'
tracked=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',release,'src'],text=True).splitlines()
checks=[]
for name in tracked:
    relative=Path(name).relative_to('src')
    if relative.suffix not in ['.for','.inc','.f90'] and relative.name!='makefile':continue
    # make wepp_hill swaps these four root includes; watershed originals are saved.
    actual=relative
    if str(relative) in ['pmxelm.inc','pmxhil.inc','pmxpln.inc','pntype.inc']:
        actual=Path('includes_watershed')/relative
    original=subprocess.check_output(['git','-C',repo,'show',release+':'+name])
    observed=(b/actual).read_bytes() if (b/actual).exists() else b''
    checks.append({'file':name,'retained_path':str(actual),'equal':original==observed,
                   'release_sha256':hashlib.sha256(original).hexdigest(),
                   'retained_sha256':hashlib.sha256(observed).hexdigest()})
names=sorted({p.relative_to(d) for d in [b,c] for p in d.rglob('*') if p.is_file() and (p.suffix in ['.for','.inc','.f90'] or p.name=='makefile')})
diff=[str(n) for n in names if not (b/n).exists() or not (c/n).exists() or (b/n).read_bytes()!=(c/n).read_bytes()]
r={'release_commit':release,'release_vs_retained_baseline_files':checks,
   'release_vs_retained_baseline_differences':[v['file'] for v in checks if not v['equal']],
   'baseline_vs_corrected_source_differences':diff,
   'note':'Root capacity includes normalized to includes_watershed after make wepp_hill swaps them. Compiler/build provenance remains a separate limitation.'}
Path('/workdir/warming-rrinit-legacy-20261006/source-audit.json').write_text(json.dumps(r,indent=2)+'\n')
print({k:v for k,v in r.items() if k!='release_vs_retained_baseline_files'})
