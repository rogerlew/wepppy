"""Five-climate development transfer matrix, retained locally on forest."""
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import continuation as c
import builder_bridge as bridge
b=c.b
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261030/development-matrix-v1')


def execute(case):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    texture=bridge.TEXTURES[case['soil']]
    name='-'.join(case.values());folder=ROOT/'matrix-v1'/name
    runs,out=folder/'runs',folder/'output';runs.mkdir(parents=True);out.mkdir()
    profile='-'.join((case['climate'],texture,case['design'],case['surface'],case['traffic']))
    ref_folder=b.DEFAULT_ROOT/'validation-v4'/f'{profile}-legacy-legacy'
    reference=json.loads((ref_folder/'record.json').read_text())
    c.e.a.s.check_files(ref_folder,reference)
    for file in ('p1.sol','p1.man','p1.slp','p1.cli','p1.run'):
        shutil.copy2(ref_folder/'runs'/file,runs/file)
    shutil.copy2(runs/'p1.sol',runs/'reference.sol')
    for file in Path('/workdir/wepppy/tests/roads/data/shared').iterdir():shutil.copy2(file,runs/file.name)
    prepared={role:WeppSoilUtil(str(ROOT/'prepared'/case['soil']/f'{role}.sol')) for role in ('bare','forest')}
    transformed=bridge.inject(runs/'p1.sol',prepared,(1,2,3))
    inputs={p.name:b.digest(p) for p in runs.iterdir() if p.name!='reference.sol'}
    if b.digest(c.BINARY)!=c.SHA:raise ValueError('Binary drift')
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([str(c.BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
    record=dict(case=case,inputs=inputs,outputs={p.name:b.digest(p) for p in out.iterdir()},
                soil_readback=transformed['generated_after'],transformation=transformed,
                reference_sha256=b.digest(ref_folder/'record.json'),reference_kg_yr=reference['metrics']['sediment_export_kg_yr'])
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        record.update(status='native_failure',within=False,physical_pass=False,tail=(runs/'stdout').read_text()[-1500:])
        b.dump(folder/'failure.json',record);return record
    _,width,length=b.slope_text(case['design'])
    record.update(status='completed',width_m=width,profile_length_m=length,metrics=b.parse_loss(out/'H1.loss.dat',width))
    climate=json.loads((ROOT/'inputs/manifest.json').read_text())['climates'][case['climate']]
    record['wat_rows']=b.validate_wat(out/'H1.wat.dat',climate)
    b.dump(folder/'record.json',record)
    record['audit']=c.audit(folder,case,record)
    value=record['metrics']['sediment_export_kg_yr'];ref=record['reference_kg_yr']
    record.update(export_kg_yr=value,within=.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref),physical_pass=record['audit']['physical_pass'])
    b.dump(folder/'record.json',record);return record


def main():
    ROOT.mkdir(parents=True,exist_ok=False)
    (c.ROOT/'development-matrix-v1').symlink_to(ROOT,target_is_directory=True)
    (ROOT/'inputs').symlink_to(c.BATCH/'inputs',target_is_directory=True)
    design=json.loads((c.ROOT/'design-v2.json').read_text())
    cases=[dict(zip(('climate','soil','design','surface','traffic'),v),variant='erosion_road_cap',runtime='project') for v in itertools.product(
        ('site','birmingham','denver','flagstaff','charleston'),[r['mukey'] for r in design['development']],
        ('inbare','inveg','outrut','outunrut'),('gravel','paved'),('high','low','none'))]
    b.dump(ROOT/'declaration.json',dict(cases=cases,script_sha256=b.digest(__file__),binary_sha256=c.SHA,
        physical_acceptance_deferred='Uncapped full-day water deficit remains unresolved. This development panel cannot on its own establish final scientific acceptance.',
        limits='Matched FSWEPP geometry and outlet, fixed site sidecars; regional runtime and actual project execution remain separate requirements. Withheld materials untouched.'))
    shutil.copy2(__file__,ROOT/'executed-development-matrix.py')
    for material in design['development']:
        if b.digest(material['path'])!=material['sha256']:raise ValueError('Material drift')
        bridge.roles(material['path'],ROOT/'prepared'/material['mukey'])
    results=[]
    with ProcessPoolExecutor(max_workers=16) as pool:
        for r in pool.map(execute,cases):
            results.append(r)
            if len(results)%20==0:
                b.dump(ROOT/'partial-results.json',results)
                print(len(results),len(cases),r['case'],r['status'],flush=True)
    b.dump(ROOT/'results.json',results)
    summary=dict(cases=len(results),native_completed=sum(r['status']=='completed' for r in results),numerical_pass=sum(r['within'] for r in results),physical_pass=sum(r['physical_pass'] for r in results))
    b.dump(ROOT/'summary.json',summary);b.dump(c.HERE/'development-matrix-v1-summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
