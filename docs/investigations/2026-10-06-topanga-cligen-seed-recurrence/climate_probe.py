"""Check observed CLIGEN reproduction before any seed inference."""
from pathlib import Path
import json
import shutil
import subprocess
import numpy as np

root = Path('/home/workdir/topanga-seed-recurrence-20261006/bundle')
out = root / 'climate-probe'
out.mkdir(exist_ok=False)
for name in ('ws.prn', 'ca041484.par'):
    shutil.copy2(root/'climate-source'/name, out/name)
cmd=[str(root/'bin/cligen532'), '-ica041484.par','-Ows.prn','-owepp.cli','-t6','-I2']
with (out/'cligen.log').open('wb') as log:
    p=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert p.returncode == 0
def rows(path):
    return np.array([[float(x) for x in l.split()] for l in path.read_text().splitlines()[15:] if l.strip()])
new=rows(out/'wepp.cli')
fields=['day','month','year','prcp','dur','tp','ip','tmax','tmin','rad','wind','wdir','tdew']
report={'command':cmd,'shape':list(new.shape),'comparisons':{}}
for label,path in [('watershed',root/'climate-source/wepp.cli'),('ksat_fixture',root/'inputs/ksat20/p106.cli'),('cover_fixture',root/'inputs/cover90/p106.cli')]:
    old=rows(path)
    assert old.shape==new.shape
    report['comparisons'][label]={name:{'differing_rows':int(np.count_nonzero(old[:,i]!=new[:,i])),'max_abs_difference':float(np.max(np.abs(old[:,i]-new[:,i])))} for i,name in enumerate(fields)}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
