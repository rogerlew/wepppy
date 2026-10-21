"""Controlled initial-groundwater normalization check with identical total area."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from audit_cases import passes
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
BIN=Path('/workdir/wepppy/wepp_runner/bin/wepp_261021_hill')
results=[]
for name in ['single','upper60','three']:
    base=ROOT/'release-matrix'/f'daily-{name}';root=ROOT/'initial-groundwater'/name
    shutil.copytree(base/'runs',root/'runs');(root/'output').mkdir()
    p=root/'runs/gwcoeff.txt';lines=p.read_text().splitlines();lines[0]='100.0 Initial groundwater storage (mm)';p.write_text('\n'.join(lines)+'\n')
    with (root/'runs/p1.run').open('rb') as inp,(root/'stdout').open('wb') as out,(root/'stderr').open('wb') as err:
        proc=subprocess.run([str(BIN)],cwd=root/'runs',stdin=inp,stdout=out,stderr=err,timeout=1800)
    assert proc.returncode==0 and 'SIMULATION SUCCESSFULLY' in (root/'stdout').read_text(errors='replace')
    p=passes(root/'output/H1.pass.dat');first=p.iloc[0]
    # Printed groundwater input is mm; the total hillslope remains 10,000 m2.
    result=dict(case=name,days=len(p),initial_depth_mm=100.,hillslope_area_m2=10000.,expected_initial_volume_m3=1000.,expected_first_baseflow_m3=40.,actual_first_baseflow_m3=float(first.baseflow),binary_sha256=hashlib.sha256(BIN.read_bytes()).hexdigest(),input_change='gwcoeff.txt initial storage only; WAT must be unchanged')
    result['wat_identical']=(root/'output/H1.wat.dat').read_bytes()==(base/'output/H1.wat.dat').read_bytes();assert result['wat_identical']
    manifest={str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for sub in ['runs','output'] for x in (root/sub).iterdir() if x.is_file()}
    (root/'file-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    results.append(result);print(result,flush=True)
(ROOT/'initial-groundwater/audit.json').write_text(json.dumps(results,indent=2)+'\n')
