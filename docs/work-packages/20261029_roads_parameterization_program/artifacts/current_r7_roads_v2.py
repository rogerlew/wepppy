"""Declared disposable Roads controller checks on the freshly executed baseline."""
from pathlib import Path
import argparse
import os
import xml.etree.ElementTree as ET
import execute_current_r7_project_v2 as baseline
from tests.roads.roads_project import DESIGNS, validate_project, verify_negative

seeds=baseline.seeds
SOURCE=baseline.PROJECT
ROOT=baseline.ROOT.parent/'current-roads-v2'
PROTOCOL=seeds.ART/'resumption-r7-current-roads-v2-protocol.md'
QA=seeds.ART/'resumption-r7-current-project-v2-native-readback.json'


def dependencies():
    result=baseline.dependencies()
    for p in (Path(__file__),PROTOCOL,seeds.REPO/'tests/roads/roads_project.py',
              seeds.REPO/'tests/roads/extract_fixture.py'):
        result[str(p)]=seeds.sha(p)
    matrix=seeds.REPO/'tests/roads/roads_matrix.py'
    result[str(matrix)]=seeds.sha(matrix)
    for path in (seeds.REPO/'wepppy/nodb/mods/roads/legacy_templates').rglob('*'):
        if path.is_file(): result[str(path)]=seeds.sha(path)
    return result


def source_snapshot():
    result=baseline.prep.snapshot(SOURCE)
    result.update(baseline.prep.inventory(SOURCE,('dem','watershed')))
    for vrt in SOURCE.rglob('*.vrt'):
        for node in ET.parse(vrt).iter('SourceFilename'):
            target=Path(node.text)
            if node.get('relativeToVRT')=='1': target=vrt.parent/target
            target=target.resolve(strict=True)
            assert target.is_relative_to(SOURCE), 'Undeclared external VRT source'
            assert str(target.relative_to(SOURCE)) in result
    return result


def declare():
    assert seeds.sha(QA)=='7cc96450086f02474dd723c2b01b3dd15bf2ec913d98c30180c29935e3f07de6'
    completed=seeds.read(baseline.ROOT/'baseline-native-completed.json')
    for name,digest in completed['outputs'].items():
        assert seeds.sha(SOURCE/name)==digest
    state=seeds.read(SOURCE/'wepp.nodb')['py/state']
    assert state['_wepp_bin']=='wepp_261029'
    ROOT.mkdir(parents=True,exist_ok=False)
    cases=[dict(name=design,design=design,negative=False,
        exclude_infeasible_unrutted=design=='outslope_unrutted') for design in DESIGNS]
    cases.append(dict(name='outslope_unrutted_negative',design='outslope_unrutted',negative=True,exclude_infeasible_unrutted=False))
    d=dict(cases=cases,source=str(SOURCE),source_inventory=source_snapshot(),
        baseline_completion_sha256=seeds.sha(baseline.ROOT/'baseline-native-completed.json'),
        baseline_readback_sha256=seeds.sha(QA),dependencies=dependencies(),
        binaries=completed['binaries'],uid=os.getuid(),gid=os.getgid(),context_concurrency=1,
        scope='Public Roads controller lifecycle/accounting only; no generated-U12 promotion or RQ/browser/catalog acceptance')
    seeds.save(ROOT/'declaration.json',d)
    print('Declared four positive controller contexts plus pinned full-upload negative',seeds.sha(ROOT/'declaration.json'),flush=True)


def run():
    d=seeds.read(ROOT/'declaration.json')
    assert d['dependencies']==dependencies()
    assert (os.getuid(),os.getgid())==(d['uid'],d['gid'])
    assert source_snapshot()==d['source_inventory']
    start=ROOT/'execution-start.json';assert not start.exists()
    seeds.save(start,dict(declaration_sha256=seeds.sha(ROOT/'declaration.json')))
    rows=[]
    for case in d['cases']:
        for name,digest in d['binaries'].items():
            assert seeds.sha(seeds.REPO/'wepp_runner/bin'/name)==digest
        dest=ROOT/case['name']
        try:
            result=validate_project(SOURCE,dest,case['design'],
                exclude_infeasible_unrutted=case['exclude_infeasible_unrutted'])
        except RuntimeError as exc:
            if not case['negative'] or 'segment execution failed for 2 segment' not in str(exc):
                raise
            result=verify_negative(SOURCE,dest)
            result['expected_exception']=str(exc)
        else:
            assert not case['negative'],'Expected negative geometry control unexpectedly completed'
        rows.append(dict(case=case,evidence=result))
        seeds.save(ROOT/(case['name']+'-receipt.json'),rows[-1])
        assert source_snapshot()==d['source_inventory']
        assert d['dependencies']==dependencies()
        print('Context completed',case['name'],'expected_negative',case['negative'],flush=True)
    for name,digest in d['binaries'].items():
        assert seeds.sha(seeds.REPO/'wepp_runner/bin'/name)==digest
    seeds.save(ROOT/'results.json',rows)
    print('Five declared contexts complete; independent outcome review pending',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','run'))
    args=parser.parse_args();{'declare':declare,'run':run}[args.action]()
