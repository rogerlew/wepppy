"""Run a declared synthetic serializer/consumer fixture in a fresh private root."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def f32(x): return struct.unpack('f', struct.pack('f', x))[0]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path.cwd());ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();repo=a.repo.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    probe=repo/'out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe'
    original=probe/'cases/small_paved_dry_legacy/modern/O4'
    binary=probe/'build/src/wepp'
    assert sha(binary)=='5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1'
    built=json.loads((probe/'build-receipt.json').read_text())
    for name,saved in built['inventory'].items():assert sha(probe/'build'/name)==saved['sha256'],name
    declaration=json.loads((original/'execution-declaration.json').read_text())
    runs=a.out/'runs';runs.mkdir();(a.out/'output').mkdir()
    before={}
    for name,saved in declaration['inputs'].items():
        p=original/'runs'/name;stat=p.stat();before[name]=(sha(p),stat.st_size,stat.st_mtime_ns)
        assert before[name][0]==saved['sha256']
        shutil.copy2(p,runs/name)
    fixture=repo/'out/rock-representation-20261031/generated-artifacts-v1/soil/rock.sol'
    lines=fixture.read_text().splitlines();index=lines.index('1 0')
    # Complete generated one-OFE block includes its restrictive-layer record.
    (runs/'p1.sol').write_text('\n'.join(lines[:index]+['3 0']+lines[index+1:]*3)+'\n')
    inputs={p.name:sha(p) for p in runs.iterdir() if p.is_file()}
    changed=[n for n in inputs if inputs[n]!=before[n][0]];assert changed==['p1.sol']
    evidence=dict(native_binary_sha256=sha(binary),build_members_verified=len(built['inventory']),
                  input_hashes=inputs,changed_inputs=changed,generated_soil_sha256=sha(fixture),
                  full_period_years=16,historical_outputs_copied=False,
                  purpose='synthetic serializer/native consumer evidence, not candidate parameterization')
    (a.out/'pre-execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
    with (runs/'p1.run').open('rb') as stdin,(runs/'stdout').open('xb') as stdout,(runs/'stderr').open('xb') as stderr:
        result=subprocess.run([str(binary)],cwd=runs,stdin=stdin,stdout=stdout,stderr=stderr,
                              env={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran'},timeout=300)
    evidence['returncode']=result.returncode
    evidence['completion']='WEPP COMPLETED' in (runs/'stdout').read_text()
    (a.out/'execution-result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    assert result.returncode==0 and evidence['completion']
    rows={}
    for line in (runs/'storage-init.txt').read_text().splitlines():
        cols=line.split();assert len(cols)==10
        vals=list(map(float,cols[4:]));assert all(math.isfinite(x) for x in vals)
        key=(int(cols[2]),int(cols[3]));rows.setdefault(key,{})[cols[0]]=vals
    checks=[]
    for (ofe,layer),tags in sorted(rows.items()):
        w=tags['SO_SCON_INPUT'][4];por,air,fine,rho,*_=tags['SO_SCON_PORE']
        assert abs(w-.338)<1e-6
        rock_mass=f32(w*rho)
        expected=f32(1-f32(rock_mass/f32(rock_mass+f32(2650*f32(1-w)))))
        assert fine==expected
        checks.append(dict(ofe=ofe,layer=layer,rfg_mass_fraction=w,density_kg_m3=rho,
                           actual_fine_fraction=fine,expected_float32_fine_fraction=expected,
                           interpreted_rock_volume_fraction=1-fine))
    assert {r['ofe'] for r in checks}=={1,2,3}
    outputfiles=list((a.out/'output').glob('*'));assert len(outputfiles)==7
    for p in outputfiles:
        assert p.stat().st_size>0
        assert not any(t.lower() in {'nan','inf','-inf','+inf'} for t in p.read_text().split())
    for name,saved in before.items():
        p=original/'runs'/name;stat=p.stat();assert saved==(sha(p),stat.st_size,stat.st_mtime_ns)
    evidence.update(passed=True,initialization_layers=checks,original_inputs_unchanged=True,
                    output_hashes={p.name:sha(p) for p in outputfiles},
                    limitation='No full water/particle closure or field-validity claim')
    (a.out/'receipt.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS native generated-soil readback',len(checks),'layers')


if __name__=='__main__':main()
