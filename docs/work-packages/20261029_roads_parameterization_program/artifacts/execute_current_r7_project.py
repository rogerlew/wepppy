"""Declare then execute the fully prepared disposable baseline before Roads."""
from pathlib import Path
import argparse
import os
import subprocess
import current_r7_project as prep
from wepppy.nodb.core import Wepp

seeds=prep.seeds
ROOT=prep.ROOT
PROJECT=prep.PROJECT


def dependencies():
    paths=[Path(__file__),Path(prep.__file__),prep.PROTOCOL]
    # Capture actual owned producer/runner/report source, including lazy imports.
    paths.extend((seeds.REPO/'wepppy').rglob('*.py'))
    paths.extend((seeds.REPO/'wepp_runner').rglob('*.py'))
    paths.extend((seeds.REPO/'wepppy/nodb/configs').rglob('*.cfg'))
    paths.extend((seeds.REPO/'wepppy/weppcloud/feature_registry').glob('*.yaml'))
    return {str(p):seeds.sha(p) for p in paths if p.is_file()} | seeds.dependencies()


def check_inputs(inputs):
    for name,digest in inputs.items():
        assert seeds.sha(PROJECT/name)==digest,name


def declare():
    path=ROOT/'baseline-execution-declaration.json'
    assert not path.exists()
    prepared=seeds.read(ROOT/'prepared.json')
    check_inputs(prepared['inputs'])
    assert not list((PROJECT/'wepp/output').iterdir())
    wepp=Wepp.getInstance(str(PROJECT))
    assert wepp.wepp_bin=='wepp_261029'
    wepp.prep_watershed()
    check_inputs(prepared['inputs'])
    inputs=prep.inventory(PROJECT,('wepp/runs',))
    runs=[name for name in inputs if name.endswith('.run') and not name.endswith('/pw0.run')]
    assert len(runs)==66 and 'wepp/runs/pw0.run' in inputs
    original=seeds.read(ROOT/'preparation-declaration.json')
    assert prep.snapshot(prep.SOURCE)==original['source_inventory']
    seeds.save(path,dict(inputs=inputs,dependencies=dependencies(),prepared_sha256=seeds.sha(ROOT/'prepared.json'),
        binaries=original['binary_hashes'],uid=os.getuid(),gid=os.getgid(),hillslopes=66,watersheds=1,
        workers=4,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=seeds.REPO,text=True).strip()))
    print('Declared66 hillslopes+1watershed; no native invocation',seeds.sha(path),flush=True)


def amend():
    oldpath=ROOT/'baseline-execution-declaration-v2.json'
    assert seeds.sha(oldpath)=='ecf3e84a60551c92cae0e5f1783c2a7f8701ed3bf18a788a50af752af78d550b'
    d=seeds.read(oldpath)
    current=dependencies()
    changed={name for name in d['dependencies'] if d['dependencies'][name]!=current.get(name)}
    assert changed=={str(Path(__file__))}
    check_inputs(d['inputs'])
    assert not list((PROJECT/'wepp/output').iterdir())
    path=ROOT/'baseline-execution-declaration-v3.json'
    assert not path.exists()
    wepp=Wepp.getInstance(str(PROJECT))
    d.update(dependencies=current,predecessor_sha256=seeds.sha(oldpath),
        nodb={p.name:seeds.sha(p) for p in PROJECT.glob('*.nodb')},flags=flags(wepp),
        amendment='Bind copied NoDb settings and owned config files before native invocation; v1/v2 never executed')
    seeds.save(path,d)
    print('Amended baseline declaration; no native invocation',seeds.sha(path),flush=True)


def flags(wepp):
    return {name:getattr(wepp,name) for name in ('wepp_bin','run_baseflow','run_wepp_ui','run_pmet','run_snow','run_frost','multi_ofe','run_wepp_watershed','delete_after_interchange')}


def run():
    d=seeds.read(ROOT/'baseline-execution-declaration-v3.json')
    assert d['dependencies']==dependencies()
    assert d['prepared_sha256']==seeds.sha(ROOT/'prepared.json')
    assert (os.getuid(),os.getgid())==(d['uid'],d['gid'])
    check_inputs(d['inputs'])
    for name,digest in d['binaries'].items():
        assert seeds.sha(seeds.REPO/'wepp_runner/bin'/name)==digest
    assert {p.name:seeds.sha(p) for p in PROJECT.glob('*.nodb')}==d['nodb']
    start=ROOT/'baseline-execution-start.json'
    assert not start.exists()
    seeds.save(start,dict(declaration_sha256=seeds.sha(ROOT/'baseline-execution-declaration-v3.json')))
    wepp=Wepp.getInstance(str(PROJECT))
    assert flags(wepp)==d['flags'] and wepp.wepp_bin=='wepp_261029'
    wepp.run_hillslopes(max_workers=d['workers'])
    check_inputs(d['inputs'])
    # Match rq stage_post's required boundary; raw PASS remains for routing.
    from wepppy.wepp.interchange import run_wepp_hillslope_interchange
    climate=wepp.climate_instance
    assert not climate.is_single_storm and wepp.run_wepp_watershed
    run_wepp_hillslope_interchange(wepp.output_dir,pass_family=wepp.pass_family,
        start_year=climate.calendar_start_year,run_loss_interchange=True,
        run_soil_interchange=True,run_wat_interchange=True,delete_after_interchange=False)
    assert flags(wepp)==d['flags'] and wepp.wepp_bin=='wepp_261029'
    wepp.run_watershed()
    check_inputs(d['inputs'])
    assert d['dependencies']==dependencies()
    original=seeds.read(ROOT/'preparation-declaration.json')
    assert prep.snapshot(prep.SOURCE)==original['source_inventory']
    seeds.save(ROOT/'baseline-native-completed.json',dict(outputs=prep.inventory(PROJECT,('wepp/output',)),
        input_integrity=True,source_integrity=True,independent_artifact_readback='pending',
        binaries={n:seeds.sha(seeds.REPO/'wepp_runner/bin'/n) for n in d['binaries']}))
    print('Configured baseline native workflow completed; independent readback pending',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','amend','run'))
    args=parser.parse_args();{'declare':declare,'amend':amend,'run':run}[args.action]()
