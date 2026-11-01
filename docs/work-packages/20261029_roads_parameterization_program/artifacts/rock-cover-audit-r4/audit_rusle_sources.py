"""Read-only provenance inventory and actual-function synthetic controls; no model run."""
import argparse, ast, hashlib, json
from pathlib import Path
from typing import Any
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    root=args.repo.resolve();args.out.mkdir(parents=True,exist_ok=False);bindings={}
    def bind(p):
        p=p.resolve();s=p.stat();d=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=s.st_size,mtime_ns=s.st_mtime_ns);bindings[str(p)]=d;return p.read_text()
    c=root/'wepppy/nodb/mods/rusle/c_integration.py';k=root/'wepppy/nodb/mods/rusle/k_integration.py'
    ct=bind(c);kt=bind(k)
    for rel in ['wepppy/nodb/core/soils.py','wepppy/soils/ssurgo/ssurgo.py','wepppy/locales/earth/soils/isric/__init__.py','docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md','docs/adrs/ADR-0004-rusle-scenario-sbs-surface-rock-partition.md','wepppy/nodb/mods/rusle/specification.md']:bind(root/rel)
    # Compile exact AST function bodies, injecting only I/O boundary seams and dependencies.
    names={'_load_cfvo_surface_proxy_from_raster','_mean_bare_rap_0_1','_resolve_rock_fraction_auto','_mean_lookup_bare_0_1','_resolve_rock_fraction_auto_for_scenario_sbs'}
    env=dict(np=np,Any=Any,_join=lambda a,b:str(Path(a)/b),_exists=lambda p:p.endswith('cfvo_0-5cm_Q0.5.tif'),CFVO_TOP_LAYER_CANDIDATES=('polaris/cfvo_mean_0_5.tif','soils/cfvo_0-5cm_Q0.5.tif'),CFVO_SCALE_DIVISOR_IF_PERMILLE=10.)
    for text,nset in [(ct,names),(kt,{'_normalize_cfvo_to_volpct'})]:
        nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name in nset]
        assert {n.name for n in nodes}==nset
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<bound-source-functions>','exec'),env)
    controls=[]
    for label,raw in [('low_soilgrids',[20.,80.]),('at_boundary_soilgrids',[100.]),('above_boundary_soilgrids',[101.]),('zero',[0.]),('nonfinite',[float('nan')])]:
        data=np.array(raw);env['_aligned_band']=lambda p,profile:data
        proxy,report=env['_load_cfvo_surface_proxy_from_raster'](wd='/synthetic',dem_profile={},valid_mask=np.ones(data.shape,dtype=bool))
        normalized,kreport=env['_normalize_cfvo_to_volpct'](data,assume_soilgrids_per_mille=True)
        expected=float(np.mean(data[np.isfinite(data)])/1000.) if np.any(np.isfinite(data)) else None
        controls.append(dict(label=label,raw=[None if not np.isfinite(x) else x for x in raw],c_proxy=proxy,k_volpct_mean=float(np.nanmean(normalized)) if np.any(np.isfinite(normalized)) else None,expected_soilgrids_proxy=expected,c_report=report,k_report=kreport))
    assert controls[0]['c_proxy']==.5 and controls[0]['expected_soilgrids_proxy']==.05
    assert controls[1]['c_proxy']==1. and np.isclose(controls[2]['c_proxy'],.101,rtol=0,atol=1e-15)
    assert controls[3]['c_proxy']==0. and controls[4]['c_proxy'] is None
    # Ratio-of-means is a run-level scalar; it does not retain local rock/bare co-location.
    env['_load_cosurffrags_surface_proxy_from_soils_parquet']=lambda wd:(.2,{'status':'available','source_kind':'synthetic'})
    normalizations=[]
    for raw in ([20.,80.],[0.,0.],[10.,10.]):
        bare=np.array(raw);mask=np.ones(bare.shape,dtype=bool)
        rap=env['_resolve_rock_fraction_auto'](wd='/synthetic',dem_profile={},valid_mask=mask,bare_ground_pct=bare)
        sbs=env['_resolve_rock_fraction_auto_for_scenario_sbs'](wd='/synthetic',dem_profile={},valid_mask=mask,bare_lookup_0_1=bare/100.)
        assert rap['effective']==sbs['effective']
        normalizations.append(dict(bare_percent=raw,proxy_total_surface=.2,effective=rap['effective'],implied_local_added_cover=(bare/100.*rap['effective']).tolist()))
    assert normalizations[0]['effective']==.4 and normalizations[1]['effective']==0. and normalizations[2]['effective']==1.
    decl=root/'out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4/attempt-u2/execution-declaration.json'
    tasks=json.loads(bind(decl))['tasks'];assert len(tasks)==36
    allowed={'1718465','1718494','1856573','2711184'};assert {t['case']['soil'] for t in tasks}==allowed
    candidates=['soils/soils.parquet','polaris/cfvo_mean_0_5.tif','soils/cfvo_0-5cm_Q0.5.tif','rusle/manifest.json']
    artifacts=[]
    for t in tasks:
        record=Path(t['source_record']);bind(record)
        assert bindings[str(record.resolve())]['sha256']==t['source_record_sha256']
        # Both retained native history and its direct source-record case root, not an inferred project watershed.
        for kind,folder in [('history',Path(t['folder'])),('source_case',record.parent)]:
            artifacts.append(dict(stratum=t['stratum'],lane=t['lane'],mode=t['mode'],scope=kind,root=str(folder),candidates={p:(folder/p).exists() for p in candidates}))
    hits=[]
    needles=('cosurffrags','sfragcov','surface_rock_cover_pct','surface_rock_cover_percent')
    for p in sorted((root/'wepppy').rglob('*.py')):
        if p.is_symlink():continue
        text=p.read_text(errors='replace')
        if any(x in text for x in needles):
            hits.append(str(p.relative_to(root)));bind(p)
    assert hits==['wepppy/nodb/mods/rusle/c_integration.py']
    for p,d in bindings.items():
        path=Path(p);s=path.stat();assert dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=s.st_size,mtime_ns=s.st_mtime_ns)==d
    result=dict(passed=True,scope='actual source function arithmetic with injected raster I/O; not end-to-end or selected-case execution',controls=controls,normalization_controls=normalizations,selected_artifact_checks=artifacts,python_producer_name_search_hits=hits,bindings=bindings,reader_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.out/'source-audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('PASS: 5 unit controls, 3 normalization controls, 72 selected artifact scopes; nonmutation verified')

if __name__=='__main__':main()
