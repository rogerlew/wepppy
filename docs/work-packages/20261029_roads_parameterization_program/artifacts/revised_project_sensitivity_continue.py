"""Additive continuation after unused matrix helper drift stopped the study."""
import argparse
import os
from pathlib import Path
import revised_project_sensitivity as study

ROOT=study.ROOT
DECLARATION=ROOT/'continuation-declaration.json'


def bindings():
    return study.dependencies() | {str(Path(__file__)):study.seeds.sha(__file__)}


def check_first():
    root=ROOT/'w4-f30'
    receipt=study.seeds.read(ROOT/'w4-f30-readback.json')
    for name,value in receipt['input_output_hashes'].items():
        assert study.seeds.sha(root/name)==value, name
    assert study.inventory(root,('wepp/runs','wepp/output'))==study.seeds.read(root/'baseline-before.json')


def declare():
    assert not DECLARATION.exists()
    old=study.seeds.read(ROOT/'declaration.json')
    current=study.dependencies()
    delta={k:dict(before=old['dependencies'].get(k),after=current.get(k))
           for k in set(current)|set(old['dependencies']) if current.get(k)!=old['dependencies'].get(k)}
    assert set(delta)=={'/workdir/wepppy/tests/roads/roads_matrix.py'}, delta
    assert study.prior.source_snapshot()==old['source_inventory']
    check_first()
    first=ROOT/'w4-f30-readback.json'
    assert study.seeds.read(first)['case']==study.CASES[0]
    assert not any((ROOT/case['name']).exists() for case in study.CASES[1:])
    study.seeds.save(DECLARATION,dict(prior_declaration_sha256=study.seeds.sha(ROOT/'declaration.json'),
        first_receipt_sha256=study.seeds.sha(first), first_completion_sha256=study.seeds.sha(ROOT/'w4-f30-completed.json'),
        dependency_stop_log_sha256=study.seeds.sha(ROOT/'dependency-stop.log'),
        dependency_delta=delta, dependencies=bindings(), remaining=study.CASES[1:],
        reason='Matrix helper changed outside project execution path; preserve first context, resume three undeployed disposable contexts',
        uid=os.getuid(),gid=os.getgid()))


def run():
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    d=study.seeds.read(DECLARATION); old=study.seeds.read(ROOT/'declaration.json')
    assert bindings()==d['dependencies']
    assert (os.getuid(),os.getgid())==(d['uid'],d['gid'])
    mask=os.umask(0);os.umask(mask);assert oct(mask)==old['umask']
    assert study.seeds.sha(ROOT/'declaration.json')==d['prior_declaration_sha256']
    assert study.seeds.sha(ROOT/'w4-f30-readback.json')==d['first_receipt_sha256']
    assert study.prior.source_snapshot()==old['source_inventory']
    check_first()
    start=ROOT/'continuation-start.json';assert not start.exists()
    study.seeds.save(start,dict(declaration_sha256=study.seeds.sha(DECLARATION)))
    for case in d['remaining']:
        assert bindings()==d['dependencies']
        for name,value in old['binaries'].items(): assert study.seeds.sha(study.seeds.REPO/'wepp_runner/bin'/name)==value
        root,controller=study.clone(case)
        controller.prepare_segments();assert not lifecycle.available(root)
        result=controller.run_roads_wepp();assert result['status']=='completed'
        study.seeds.save(ROOT/(case['name']+'-completed.json'),dict(case=case,summary=result))
        study.read_case(case)
        assert bindings()==d['dependencies']
        print('Completed',case['name'],flush=True)
    check_first()
    rows=[study.seeds.read(ROOT/(case['name']+'-readback.json')) for case in study.CASES]
    study.compare_results(rows)
    assert not (ROOT/'results.json').exists()
    study.seeds.save(ROOT/'results.json',rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','run'))
    args=parser.parse_args();{'declare':declare,'run':run}[args.action]()
