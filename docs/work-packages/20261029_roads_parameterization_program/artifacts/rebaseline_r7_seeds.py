"""Declared exact-input r4/r7 engine comparison; never changes retained evidence."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

import combined_hydraulics_r4 as common
import audit_particle_closure_v2 as particles
import audit_pass_completeness_r7 as pass_completeness
import score_screen
import role_boundary_assessment as role
from wepppy.wepp.soils.utils import WeppSoilUtil

REPO = Path('/workdir/wepppy')
ART = REPO/'docs/work-packages/20261029_roads_parameterization_program/artifacts'
SEEDS = REPO/'out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4/attempt-u2/results.json'
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/engine-seeds-v3')
EXPECTED = {'r4':'2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48',
            'r7':'4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825'}
OUTPUTS = {f'H1.{x}.dat' for x in ('loss','soil','pass','plot','wat','element','ebe')}
sha, save = common.sha, common.save


def read(path):
    return json.loads(Path(path).read_text())


def dependencies():
    result = common.effective_dependencies()
    for path in (Path(__file__), Path(common.__file__), Path(particles.__file__),
                 Path(score_screen.__file__), Path(role.__file__), Path(pass_completeness.__file__), ART/'resumption-r7-20261103.md', ART.parent/'acceptance.md'):
        result[str(path.resolve())] = sha(path)
    return result


def verify_source(task):
    path = Path(task['source_record'])
    assert sha(path) == task['source_record_sha256'], path
    old = read(path)
    for section, directory in [('inputs','runs'),('auxiliary_inputs','runs'),('outputs','output')]:
        for name, digest in old.get(section, {}).items():
            assert sha(path.parent/directory/name) == digest, (path, name)
    for name, digest in task.get('auxiliary_inputs', {}).items():
        assert sha(Path(task['auxiliary_source_folder'])/'runs'/name) == digest
    if 'reference_record' in task:
        refpath=Path(task['reference_record'])
        assert sha(refpath)==task['reference_record_sha256']
        ref=read(refpath)
        for name,digest in ref['outputs'].items():
            assert sha(refpath.parent/'output'/name)==digest
    return old


def declare():
    ROOT.mkdir(parents=True, exist_ok=False)
    (ROOT/'bin').mkdir()
    binary4 = subprocess.check_output(['git','show','a5c40031a:wepp_runner/bin/wepp_261029'], cwd=REPO)
    assert binary4.startswith(b'\x7fELF')
    (ROOT/'bin/r4').write_bytes(binary4)
    shutil.copyfile(REPO/'wepp_runner/bin/wepp_261029', ROOT/'bin/r7')
    for version, digest in EXPECTED.items():
        p = ROOT/'bin'/version
        p.chmod(0o755)
        assert sha(p) == digest, version
    rows = read(SEEDS)
    assert len(rows) == 36 and {r['mode'] for r in rows} == {0,1}
    tasks=[]
    for row in rows:
        if row['mode'] != 0:
            continue
        source = Path(row['source_record'])
        auxiliary_folder=str(Path(row['folder'])).replace('/home/workdir/wepppy/', '/workdir/wepppy/', 1)
        source_binding = dict(row, auxiliary_source_folder=auxiliary_folder)
        old = verify_source(source_binding)
        auxiliary = row['auxiliary_inputs']
        assert set(auxiliary) == {'reference.sol'}
        assert old['binary_sha256'] == EXPECTED['r4']
        assert row['outputs'] == old['outputs'] and row['ordinary_output_parity']
        assert set(old['outputs']) == OUTPUTS
        assert set(old['inputs']) == {'p1.slp','p1.man','p1.cli','p1.sol','p1.run',
            'pmetpara.txt','gwcoeff.txt','chntyp.txt','tc.txt','snow.txt','wepp_ui.txt','chan.inp'}
        assert row['inputs'] == old['inputs']
        case=old['case']
        profile='-'.join((case['climate'],role.TEXTURES[case['soil']],case['design'],
                          case['surface'],case['traffic'],'legacy','legacy'))
        reference_path=role.REFERENCE/profile/'record.json'
        ref_record=read(reference_path)
        for name,digest in ref_record['outputs'].items():
            assert sha(reference_path.parent/'output'/name)==digest
        for name in ('p1.cli','p1.man','p1.slp'):
            assert old['inputs'][name]==ref_record['inputs'][name]
            assert sha(reference_path.parent/'runs'/name)==ref_record['inputs'][name]
        reference=ref_record['metrics']['sediment_export_kg_yr']
        assert reference >= 0
        if 'reference_kg_yr' in old:
            assert reference==old['reference_kg_yr']
        for version in EXPECTED:
            folder = ROOT/'cases'/row['stratum']/row['lane']/version
            runs = folder/'runs'; runs.mkdir(parents=True, exist_ok=False)
            (folder/'output').mkdir()
            for section in ('inputs','auxiliary_inputs'):
                for name in old.get(section, {}):
                    assert Path(name).name == name
                    shutil.copyfile(source.parent/'runs'/name, runs/name)
            for name in auxiliary:
                shutil.copyfile(Path(auxiliary_folder)/'runs'/name, runs/name)
            deck=(runs/'p1.run').read_text().splitlines()
            assert {line for line in deck if 'output/' in line} == {'../output/'+n for n in OUTPUTS}
            task = dict(case=old['case'],stratum=row['stratum'],lane=row['lane'],version=version,
                folder=str(folder),source_record=str(source),source_record_sha256=sha(source),
                inputs=old['inputs'],auxiliary_inputs=auxiliary,
                auxiliary_source_folder=auxiliary_folder,
                soil_readback=old['soil_readback'],width_m=old['width_m'],
                profile_length_m=old['profile_length_m'],reference_kg_yr=reference,
                reference_record=str(reference_path),reference_record_sha256=sha(reference_path),
                prior_outputs=old['outputs'],prior_export_kg_yr=old['metrics']['sediment_export_kg_yr'])
            common.verify_files(folder,task)
            assert WeppSoilUtil(str(runs/'p1.sol')).obj['ofes'] == task['soil_readback']
            tasks.append(task)
    assert len(tasks)==36
    declaration=dict(tasks=tasks,binaries=EXPECTED,dependencies=dependencies(),
        source_panel={'path':str(SEEDS),'sha256':sha(SEEDS)},
        source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        mode1_disposition='18 retained experimental histories inventoried only; no r7 roughness port',
        mode1_inputs=[{'stratum':r['stratum'],'lane':r['lane'],'inputs':r['inputs'],
                      'controls':r['controls'],'outputs':r['outputs']} for r in rows if r['mode']==1],
        uid=os.getuid(),gid=os.getgid(),workers=4,timeout_seconds=300,
        acceptance='r4 exact ordinary-output reproduction, unchanged copied/source inputs, fresh full-period physical/calendar/accounting and strict particle checks; no magnitude acceptance on selected seeds')
    save(ROOT/'declaration.json',declaration)
    shutil.copyfile(__file__,ROOT/'executed-driver.py')
    print('Declared 36 full-period calls; no execution', sha(ROOT/'declaration.json'),flush=True)


def execute(task):
    folder=Path(task['folder']);runs=folder/'runs';output=folder/'output'
    binary=ROOT/'bin'/task['version']
    assert not (folder/'record.json').exists() and not list(output.iterdir())
    assert sha(binary)==EXPECTED[task['version']]
    common.verify_files(folder,task)
    code=None
    with (runs/'p1.run').open() as inp, (runs/'stdout').open('w') as stdout, (runs/'stderr').open('w') as stderr:
        try:
            code=subprocess.run([str(binary)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300).returncode
        except subprocess.TimeoutExpired:
            # A timed-out native call is retained as a failed case, never retried silently.
            pass
    completed=code==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text()
    row=dict(task,binary_sha256=sha(binary),returncode=code,completed=completed,
             status='completed' if completed else 'native_failure',physical_pass=False,within=False,
             outputs={p.name:sha(p) for p in output.iterdir() if p.is_file()},
             execution_logs={n:sha(runs/n) for n in ('stdout','stderr')})
    save(folder/'native-receipt.json',row)
    if completed:
        assert set(row['outputs'])==OUTPUTS
        row['metrics']=common.c.b.parse_loss(output/'H1.loss.dat',row['width_m'])
        row['audit']=common.c.audit(folder,row['case'],row)
        stdout_text=(runs/'stdout').read_text()
        row['runtime_markers']={name: marker in stdout_text for name,marker in {
            'ui':'WEPP hourly water seepage update set (UI code)',
            'groundwater':'Gwcoeff parameters set',
            'pmet':'FAO Penman-Monteith ET Method Implemented'}.items()}
        row['snow_consumption_evidence']='Exact staged snow.txt and selected source open/read path; no native stdout marker or dynamic read trace'
        row['physical_pass']=row['audit']['physical_pass'] and all(row['runtime_markers'].values())
        value,ref=row['metrics']['sediment_export_kg_yr'],row['reference_kg_yr']
        row.update(export_kg_yr=value,meaningful=ref>1,within=(.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref)))
    common.verify_files(folder,row)
    assert sha(binary)==EXPECTED[task['version']]
    row['changed_outputs']=[n for n in sorted(OUTPUTS) if row['outputs'].get(n)!=task['prior_outputs'][n]]
    save(folder/'record.json',row)
    if completed:
        climate=read(common.c.BATCH/'inputs/manifest.json')['climates'][row['case']['climate']]
        completeness=pass_completeness.audit(folder/'record.json',climate)
        save(folder/'pass-completeness.json',completeness)
        row['pass_completeness']=completeness['passed']
        particle=particles.audit(folder/'record.json')
        save(folder/'particle-audit.json',particle)
        row['particle_pass']=particle['passed'];row['particle_flags']=particle['flags']
    print(task['version'],task['stratum'],task['lane'],completed,row['physical_pass'],row.get('particle_pass'),flush=True)
    return row


def run():
    declaration=read(ROOT/'declaration.json')
    assert declaration['dependencies']==dependencies()
    assert (os.getuid(),os.getgid())==(declaration['uid'],declaration['gid'])
    assert sha(SEEDS)==declaration['source_panel']['sha256']
    assert not (ROOT/'execution-start.json').exists()
    save(ROOT/'execution-start.json',{'declaration_sha256':sha(ROOT/'declaration.json'),'uid':os.getuid(),'gid':os.getgid()})
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(execute,declaration['tasks']))
    save(ROOT/'results.json',rows)
    for task in declaration['tasks']:
        verify_source(task)
    assert declaration['dependencies']==dependencies()
    for v,digest in EXPECTED.items(): assert sha(ROOT/'bin'/v)==digest
    summary=dict(cases=len(rows),native_pass=sum(r['completed'] for r in rows),
        physical_pass=sum(r['physical_pass'] for r in rows),particle_pass=sum(r.get('particle_pass',False) for r in rows),
        pass_completeness=sum(r.get('pass_completeness',False) for r in rows),
        r4_exact=sum(not r['changed_outputs'] for r in rows if r['version']=='r4'),
        r7_changed_outputs=sum(len(r['changed_outputs']) for r in rows if r['version']=='r7'),
        results_sha256=sha(ROOT/'results.json'),source_and_dependency_integrity=True)
    summary['seed_comparability_gate']=summary['native_pass']==summary['physical_pass']==summary['particle_pass']==summary['pass_completeness']==36 and summary['r4_exact']==18
    save(ROOT/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','run'))
    args=parser.parse_args()
    declare() if args.action=='declare' else run()
