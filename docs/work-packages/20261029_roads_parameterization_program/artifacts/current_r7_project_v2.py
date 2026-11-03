"""Disposable complete configured project preparation, separate from fixed replay."""
from pathlib import Path
import argparse
import json
import os
import shutil
import rebaseline_r7_seeds as seeds
from tests.roads.roads_project import inventory

SOURCE=Path('/wc1/runs/cl/clogging-starch')
ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261103/current-project-v2')
PROJECT=ROOT/'baseline'
PROTOCOL=seeds.ART/'resumption-r7-current-project-v2-protocol.md'


def snapshot(root):
    result=inventory(root,('wepp','roads','climate'))
    result.update({p.name:seeds.sha(p) for p in root.glob('*.nodb')})
    return result


def rebase(value):
    if isinstance(value,dict): return {k:rebase(v) for k,v in value.items()}
    if isinstance(value,list): return [rebase(v) for v in value]
    if isinstance(value,str) and (value==str(SOURCE) or value.startswith(str(SOURCE)+'/')):
        return str(PROJECT)+value[len(str(SOURCE)):]
    return value


def prepare():
    from wepppy.nodb.core import Wepp
    ROOT.mkdir(parents=True,exist_ok=False)
    before=snapshot(SOURCE)
    binaries={n:seeds.sha(seeds.REPO/'wepp_runner/bin'/n) for n in ('wepp_261029','wepp_261029_hill')}
    assert binaries=={'wepp_261029':seeds.EXPECTED['r7'],
        'wepp_261029_hill':'210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936'}
    seeds.save(ROOT/'preparation-declaration.json',dict(source=str(SOURCE),source_inventory=before,
        binary_hashes=binaries,script_sha256=seeds.sha(__file__),protocol_sha256=seeds.sha(PROTOCOL),
        uid=os.getuid(),gid=os.getgid(),native_execution=False,
        source_material_scope='Retained source project material files; current complete model-input preparation, not a new soil-database fetch'))
    shutil.copytree(SOURCE,PROJECT,ignore=shutil.ignore_patterns('*.log','_logs','_query_engine','export'))
    # Rebase before NoDb deserialization so logger initialization cannot touch source.
    for p in PROJECT.glob('*.nodb'):
        p.write_text(json.dumps(rebase(json.loads(p.read_text()))))
    prior=ROOT/'copied-prior-wepp';prior.mkdir()
    wepp=Wepp.getInstance(str(PROJECT))
    # Preserve every canonical clean target before the actual lifecycle reset.
    for directory in (wepp.runs_dir,wepp.output_dir,wepp.plot_dir,wepp.stats_dir,
                      wepp.fp_runs_dir,wepp.fp_output_dir):
        path=Path(directory)
        assert path.is_relative_to(PROJECT)
        if path.exists():
            destination=prior/path.relative_to(PROJECT/'wepp')
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(str(path),destination)
    wepp.ensure_bootstrap_main()
    wepp.clean()
    wepp._check_and_set_baseflow_map()
    wepp._check_and_set_phosphorus_map()
    wepp.wepp_bin='wepp_261029'
    flags={name:getattr(wepp,name) for name in ('run_baseflow','run_wepp_ui','run_pmet','run_snow','run_frost','multi_ofe')}
    wepp.prep_hillslopes(max_workers=4)
    inputs=inventory(PROJECT,('wepp/runs',))
    assert not list((PROJECT/'wepp/output').iterdir())
    for flag,name in [('run_baseflow','gwcoeff.txt'),('run_wepp_ui','wepp_ui.txt'),('run_pmet','pmetpara.txt'),('run_snow','snow.txt')]:
        assert (PROJECT/'wepp/runs'/name).exists()==flags[flag]
    assert snapshot(SOURCE)==before
    seeds.save(ROOT/'prepared.json',dict(project=str(PROJECT),flags=flags,inputs=inputs,
        source_integrity=True,native_execution=False,script_sha256=seeds.sha(__file__)))
    print('Prepared complete configured hillslope inputs; no native invocation',len(inputs),flags,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare',))
    parser.parse_args();prepare()
