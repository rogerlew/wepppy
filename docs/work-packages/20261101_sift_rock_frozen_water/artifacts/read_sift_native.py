"""Observe three actual SIFT soils in fresh complete native histories."""
import argparse
import calendar
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def validate(root, expected_mass):
    rows={}
    for line in (root/'runs/storage-init.txt').read_text().splitlines():
        cols=line.split()
        if len(cols)!=10:raise ValueError('Initialization row shape')
        values=list(map(float,cols[4:]))
        if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite initialization')
        key=(int(cols[2]),int(cols[3]));tags=rows.setdefault(key,{})
        if cols[0] in tags:raise ValueError('Duplicate initialization tag')
        tags[cols[0]]=values
    if set(rows)!={(ofe,layer) for ofe in range(1,4) for layer in range(1,11)}:
        raise ValueError('Incomplete native layers')
    checks=[]
    for (ofe,layer),tags in sorted(rows.items()):
        w=tags['SO_SCON_INPUT'][4]
        por,air,fine,rho,*_=tags['SO_SCON_PORE']
        ul,ul_por,dry,dg,st,depth=tags['SO_SCON_UL']
        if abs(w-expected_mass/100)>1e-6:raise ValueError('Native mass mismatch')
        rock_mass=f32(w*rho)
        expected=f32(1-f32(rock_mass/f32(rock_mass+f32(2650*f32(1-w)))))
        if fine!=expected:raise ValueError('Native CPM mismatch')
        denominator=por*fine*dg
        if not math.isfinite(denominator) or denominator<=0:raise ValueError('Invalid SAT denominator')
        saturation=(st+dry*dg)/denominator
        if not math.isfinite(saturation) or abs(saturation-.75)>2e-6:raise ValueError('Native initial SAT mismatch')
        checks.append(dict(ofe=ofe,layer=layer,mass_fraction=w,density_kg_m3=rho,
            fine_fraction=fine,expected_float32_fine_fraction=expected,
            reconstructed_initial_sat=saturation,cumulative_depth_m=depth))
    outputs=sorted((root/'output').iterdir())
    expected_outputs={'H1.'+suffix+'.dat' for suffix in ['ebe','element','loss','pass','plot','soil','wat']}
    if {p.name for p in outputs}!=expected_outputs:raise ValueError('Output inventory mismatch')
    for path in outputs:
        if not path.stat().st_size:raise ValueError('Empty output')
        for token in path.read_text().split():
            if '*' in token and set(token)=={'*'}:raise ValueError('Numeric output overflow')
            try:value=float(token.replace('D','E'))
            except ValueError:continue
            if not math.isfinite(value):raise ValueError('Nonfinite output')
    keys=set();depths=set()
    for line in (root/'output/H1.wat.dat').read_text().splitlines():
        cols=line.split()
        if len(cols)!=25 or not cols[0].isdigit():continue
        ofe,day,year=map(int,cols[:3]);key=(ofe,day,year)
        if key in keys:raise ValueError('Duplicate daily key')
        keys.add(key);depths.add(float(cols[21]))
    # The fixed 16-year runtime uses simulation years 1..16, with every fourth year leap.
    expected_keys={(ofe,day,year) for ofe in range(1,4) for year in range(1,17)
                   for day in range(1,367 if calendar.isleap(year) else 366)}
    if keys!=expected_keys or depths!={1800.}:raise ValueError('Incomplete calendar or depth cap mismatch')
    return dict(initialization_layers=checks,water_daily_rows=len(keys),complete_daily_keys=True,
                native_profile_depth_mm=1800,output_hashes={p.name:sha(p) for p in outputs})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--fixtures',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.repo=a.repo.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    probe=a.repo/'out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe'
    original=probe/'cases/small_paved_dry_legacy/modern/O4';binary=probe/'build/src/wepp'
    if sha(binary)!='5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1':raise ValueError('Observer drift')
    built=json.loads((probe/'build-receipt.json').read_text())
    for name,saved in built['inventory'].items():
        if sha(probe/'build'/name)!=saved['sha256']:raise ValueError('Build inventory drift: '+name)
    declaration=json.loads((original/'execution-declaration.json').read_text());before={}
    for name,saved in declaration['inputs'].items():
        path=original/'runs'/name;stat=path.stat();before[name]=(sha(path),stat.st_size,stat.st_mtime_ns)
        if before[name][0]!=saved['sha256']:raise ValueError('Original input drift: '+name)
    fixtures=json.loads((a.fixtures/'receipt.json').read_text());results=[]
    if [(f['name'],f['source_volume_percent'],f['density'],f['emitted_mass_percent'],f['native_capped_mass_percent']) for f in fixtures['cases']]!=[('zero',0.,1.3,0.,0.),('normal',20.,1.3,33.8,33.8),('high',80.,1.3,89.1,85.)]:
        raise ValueError('Fixture inventory or declared values mismatch')
    for key,path in [('builder_source_sha256','wepppy/locales/canada/bc/soils/sift/sift.py'),('test_helper_sha256','tests/locales/canada/bc/soils/test_sift_rock_basis.py')]:
        if fixtures[key]!=sha(a.repo/path):raise ValueError('Fixture producer source drift')
    for fixture in fixtures['cases']:
        root=a.out/fixture['name'];runs=root/'runs';runs.mkdir(parents=True);(root/'output').mkdir()
        for name in before:shutil.copy2(original/'runs'/name,runs/name)
        source=root/'source';source.mkdir()
        for name in ['rock.json','rock.sol']:
            path=a.fixtures/fixture['name']/name
            if sha(path)!=fixture['files'][name]:raise ValueError('Generated fixture drift: '+name)
            shutil.copy2(path,source/name)
        soil=source/'rock.sol'
        if sha(soil)!=fixture['files']['rock.sol']:raise ValueError('Generated fixture drift')
        lines=soil.read_text().splitlines();index=lines.index('1 0')
        (runs/'p1.sol').write_text('\n'.join(lines[:index]+['3 0']+lines[index+1:]*3)+'\n')
        inputs={p.name:sha(p) for p in runs.iterdir() if p.is_file()}
        changed=[n for n in inputs if inputs[n]!=before[n][0]]
        if changed!=['p1.sol']:raise ValueError('Unexpected runtime mutation')
        evidence=dict(fixture=fixture,native_binary_sha256=sha(binary),build_members_verified=len(built['inventory']),
            input_hashes=inputs,changed_inputs=changed,full_period_years=16,historical_outputs_copied=False,
            producer_receipt_sha256=sha(a.fixtures/'receipt.json'),
            runner_sha256=sha(Path(__file__)),declaration_sha256=sha(Path(__file__).with_name('sift-native-declaration.md')))
        (root/'pre-execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
        with (runs/'p1.run').open('rb') as stdin,(runs/'stdout').open('xb') as stdout,(runs/'stderr').open('xb') as stderr:
            try:
                result=subprocess.run([str(binary)],cwd=runs,stdin=stdin,stdout=stdout,stderr=stderr,
                    env={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran'},timeout=300)
                evidence.update(returncode=result.returncode,status='completed')
            except subprocess.TimeoutExpired:
                evidence.update(returncode=None,status='timeout')
        evidence['completion']='WEPP COMPLETED' in (runs/'stdout').read_text()
        (root/'execution-result.json').write_text(json.dumps(evidence,indent=2)+'\n')
        try:
            if evidence['returncode']!=0 or not evidence['completion']:raise ValueError('Native execution failed')
            evidence.update(validate(root,fixture['native_capped_mass_percent']),passed=True)
        except (ValueError, KeyError, OSError) as error:
            evidence.update(passed=False,validation_error=str(error))
        (root/'receipt.json').write_text(json.dumps(evidence,indent=2)+'\n');results.append(evidence)
    for name,saved in before.items():
        path=original/'runs'/name;stat=path.stat()
        if saved!=(sha(path),stat.st_size,stat.st_mtime_ns):raise ValueError('Historical input changed')
    receipt=dict(cases=results,original_inputs_unchanged=True,
        limitation='Synthetic BCSLF records; no deployed geodatabase, retention validation, or water-budget closure claim')
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'passed':sum(r['passed'] for r in results)}))
    if not all(r['passed'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
