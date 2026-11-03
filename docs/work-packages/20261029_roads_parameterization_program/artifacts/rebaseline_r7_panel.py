"""Conditional exact-input r7 replay of the frozen 840-case development panel."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import os
import shutil
import rebaseline_r7_seeds as seeds

ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261103/panel840-v1')
SEED_ROOT=seeds.ROOT
PANEL=seeds.REPO/'out/roads-parameterization-program-20261031/param-sign-u12-combined/roads-results.json'
PROTOCOL=seeds.ART/'resumption-r7-panel-protocol.md'


def dependencies():
    result=seeds.dependencies()
    for p in (Path(__file__),PROTOCOL):
        result[str(p.resolve())]=seeds.sha(p)
    return result


def declare():
    gate=seeds.read(SEED_ROOT/'summary.json')
    assert gate['seed_comparability_gate']
    assert gate['results_sha256']==seeds.sha(SEED_ROOT/'results.json')
    ROOT.mkdir(parents=True,exist_ok=False)
    (ROOT/'bin').mkdir()
    shutil.copyfile(SEED_ROOT/'bin/r7',ROOT/'bin/r7')
    (ROOT/'bin/r7').chmod(0o755)
    assert seeds.sha(ROOT/'bin/r7')==seeds.EXPECTED['r7']
    rows=seeds.read(PANEL)
    assert len(rows)==840
    tasks=[]
    for row in rows:
        source=Path(row['folder'])/'record.json'
        old=seeds.verify_source(dict(source_record=str(source),source_record_sha256=seeds.sha(source)))
        assert old==row and old['binary_sha256']==seeds.EXPECTED['r4']
        case=old['case']
        assert case['variant']=='erosion_road_cap' and case['runtime']=='project'
        assert case['soil'] in seeds.role.TEXTURES
        profile='-'.join((case['climate'],seeds.role.TEXTURES[case['soil']],case['design'],case['surface'],case['traffic'],'legacy','legacy'))
        refpath=seeds.role.REFERENCE/profile/'record.json'
        ref=seeds.read(refpath)
        for name in ('p1.cli','p1.slp','p1.man'):
            assert old['inputs'][name]==ref['inputs'][name]
            assert seeds.sha(refpath.parent/'runs'/name)==ref['inputs'][name]
        assert set(old['outputs'])==seeds.OUTPUTS
        assert set(old['inputs'])==set(seeds.read(SEED_ROOT/'declaration.json')['tasks'][0]['inputs'])
        folder=ROOT/'cases'/'-'.join(case.values())
        runs=folder/'runs';runs.mkdir(parents=True,exist_ok=False)
        (folder/'output').mkdir()
        auxiliary={'reference.sol':seeds.sha(source.parent/'runs/reference.sol')}
        for name in [*old['inputs'],*auxiliary]:
            assert Path(name).name==name
            shutil.copyfile(source.parent/'runs'/name,runs/name)
        task=dict(case=case,stratum='development',lane='modern',version='r7',folder=str(folder),
            source_record=str(source),source_record_sha256=seeds.sha(source),inputs=old['inputs'],
            auxiliary_inputs=auxiliary,auxiliary_source_folder=str(source.parent),
            soil_readback=old['soil_readback'],width_m=old['width_m'],profile_length_m=old['profile_length_m'],
            reference_kg_yr=ref['metrics']['sediment_export_kg_yr'],reference_record=str(refpath),
            reference_record_sha256=seeds.sha(refpath),prior_outputs=old['outputs'],
            prior_export_kg_yr=old['metrics']['sediment_export_kg_yr'])
        seeds.verify_source(task)
        seeds.common.verify_files(folder,task)
        assert seeds.WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']==task['soil_readback']
        deck=(runs/'p1.run').read_text().splitlines()
        assert {line for line in deck if 'output/' in line}=={'../output/'+n for n in seeds.OUTPUTS}
        tasks.append(task)
    assert len({t['folder'] for t in tasks})==840
    declaration=dict(tasks=tasks,dependencies=dependencies(),binary_sha256=seeds.EXPECTED['r7'],
        seed_summary_sha256=seeds.sha(SEED_ROOT/'summary.json'),source_panel_sha256=seeds.sha(PANEL),
        uid=os.getuid(),gid=os.getgid(),workers=8,timeout_seconds=300,
        auxiliary_note='Unconsumed historical reference.sol newly hash-bound from each retained source folder; not a native input.',
        scope='Frozen conditioned U12 panel, current engine only; no current-producer/default/withheld/UI claim')
    seeds.save(ROOT/'declaration.json',declaration)
    shutil.copyfile(__file__,ROOT/'executed-panel-driver.py')
    print('Declared840; no native execution',seeds.sha(ROOT/'declaration.json'),flush=True)


def execute(task):
    seeds.ROOT=ROOT  # Explicit declared evidence root; seeds uses the same r7 hash.
    return seeds.execute(task)


def run():
    d=seeds.read(ROOT/'declaration.json')
    assert d['dependencies']==dependencies()
    assert d['source_panel_sha256']==seeds.sha(PANEL)
    assert d['seed_summary_sha256']==seeds.sha(SEED_ROOT/'summary.json')
    assert (os.getuid(),os.getgid())==(d['uid'],d['gid'])
    assert not (ROOT/'execution-start.json').exists()
    seeds.save(ROOT/'execution-start.json',dict(declaration_sha256=seeds.sha(ROOT/'declaration.json'),uid=os.getuid(),gid=os.getgid()))
    with ProcessPoolExecutor(max_workers=d['workers']) as pool:
        rows=list(pool.map(execute,d['tasks']))
    seeds.save(ROOT/'results.json',rows)
    for task in d['tasks']:
        seeds.verify_source(task)
    assert d['dependencies']==dependencies()
    assert seeds.sha(ROOT/'bin/r7')==seeds.EXPECTED['r7']
    summary=dict(cases=len(rows),native_pass=sum(r['completed'] for r in rows),
        physical_pass=sum(r['physical_pass'] for r in rows),particle_pass=sum(r.get('particle_pass',False) for r in rows),
        pass_completeness=sum(r.get('pass_completeness',False) for r in rows),
        results_sha256=seeds.sha(ROOT/'results.json'),source_and_dependency_integrity=True)
    seeds.save(ROOT/'summary.json',summary)
    print(summary,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','run'))
    args=parser.parse_args()
    declare() if args.action=='declare' else run()
