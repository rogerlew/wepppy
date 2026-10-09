#!/usr/bin/env python3
"""Bounded RRINIT grid using the canonical Disturbed matrix and released WEPP."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from wepppy.wepp.management import Management
from wepppyo3 import wepp_interchange as native

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MATRIX = REPO/'tests/disturbed'
ROOT = Path('/wc1/holdouts/rrinit-261009-sensitivity-20261009')
BINARY = REPO/'wepp_runner/bin/wepp_261009_hill'
SHA = '37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228'
LEVELS = [.006, .01, .02, .04]
spec = importlib.util.spec_from_file_location('rrinit_matrix', MATRIX/'test_disturbed_matrix.py')
matrix = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = matrix
spec.loader.exec_module(matrix)


def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(p, value):
    temp = p.with_suffix(p.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temp.replace(p)


def manifest(directory):
    return {p.name:sha(p) for p in sorted(directory.iterdir()) if p.is_file()}


def prepare():
    assert sha(BINARY) == SHA
    ROOT.mkdir(parents=True, exist_ok=False)
    shutil.copy2(BINARY, ROOT/'wepp_hill')
    shutil.copy2(__file__, ROOT/'runner.py')
    soil_dir = REPO/'wepppy/wepp/soils/soilsdb/data/Forest'
    man_dir = REPO/'wepppy/wepp/management/data'
    lookup_path = REPO/'wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv'
    lookup = matrix.read_disturbed_land_soil_lookup(str(lookup_path))
    plan = []
    for texture in matrix.TEXTURES:
        for vegetation in matrix.VEG_TYPES:
            for severity in matrix.SEVERITIES:
                wid = matrix.generate_wepp_id(texture, severity, vegetation)
                runs = ROOT/'prepared'/f'H{wid:03d}'/'runs'
                runs.mkdir(parents=True)
                matrix.stage_shared_inputs(runs)
                matrix.prepare_slope(wid, MATRIX/'data/canonical_slope.slp', runs)
                matrix.prepare_climate(wid, MATRIX/'data/mckenzie_2000_2099.cli', runs)
                matrix.prepare_management(wid, vegetation, severity, man_dir, runs, 100)
                matrix.prepare_soil_9002(wid, texture, vegetation, severity, soil_dir, lookup, runs)
                matrix.create_run_file(wid, 100, runs)
                m = Management.load(None, f'p{wid}.man', str(runs), None)
                assert len(m.inis)==1 and m.inis[0].landuse==1
                initial = m.inis[0].data.rrinit
                save(runs.parent/'inputs.json', manifest(runs))
                for profile in ['steep', 'gentle']:
                    for rr in sorted(set(LEVELS+[initial])):
                        plan.append(dict(case=f'{profile}/H{wid:03d}_rr{rr:.5f}', id=wid,
                            texture=texture, vegetation=vegetation, severity=severity,
                            profile=profile, rrinit_m=rr, reference_rrinit_m=initial,
                            reference=rr==initial))
                print(f'PREPARED {wid} {texture} {vegetation} severity={severity}', flush=True)
    assert len(plan)==896
    save(ROOT/'plan.json', plan)
    source_paths = [MATRIX/'data/canonical_slope.slp', MATRIX/'data/mckenzie_2000_2099.cli',
                    MATRIX/'data/mckenzie_2000_2099.json', lookup_path]
    source_paths += list(soil_dir/name for name in matrix.CANONICAL_SOILS.values())
    source_paths += [man_dir/name for name in sorted(set(matrix.MANAGEMENT_FILES.values()))]
    shared = REPO/'tests/wepp_runner/fixtures/hillslope_smoke/runs'
    source_paths += [shared/n for n in ('wepp_ui.txt','snow.txt','pmetpara.txt','gwcoeff.txt','chan.inp','chntyp.txt')]
    save(ROOT/'identity.json', dict(binary_sha256=SHA, binary_source=str(BINARY),
        native_sha256=sha(Path(native.wepp_interchange_rust.__file__)),
        inputs={str(p.relative_to(REPO)):sha(p) for p in source_paths},
        climate=json.loads((MATRIX/'data/mckenzie_2000_2099.json').read_text()),
        scope='RRINIT only within each class/texture/profile; 100 synthetic years; no default changes'))


def stage(trial):
    source = ROOT/'prepared'/f'H{trial["id"]:03d}'/'runs'
    expected = json.loads((source.parent/'inputs.json').read_text())
    assert manifest(source)==expected
    case = ROOT/'cases'/trial['case']
    runs = case/'runs'
    shutil.copytree(source, runs)
    (case/'output').mkdir()
    wid = trial['id']
    m = Management.load(None, f'p{wid}.man', str(runs), None)
    base_text = str(m)
    m.inis[0].data.rrinit = trial['rrinit_m']
    (runs/f'p{wid}.man').write_text(str(m))
    check = Management.load(None, f'p{wid}.man', str(runs), None)
    assert check.inis[0].data.rrinit == trial['rrinit_m']
    check.inis[0].data.rrinit = trial['reference_rrinit_m']
    assert str(check)==base_text, 'Non-RR management change'
    if trial['profile']=='gentle':
        p = runs/f'p{wid}.slp'
        lines = p.read_text().splitlines()
        length = lines[3].split()[1]
        lines[3] = f'2 {length}'
        lines[4] = '0.0, 0.2 1.0, 0.2'
        p.write_text('\n'.join(lines)+'\n')
    changed = {n for n,h in manifest(runs).items() if expected[n]!=h}
    allowed = {f'p{wid}.man'} | ({f'p{wid}.slp'} if trial['profile']=='gentle' else set())
    assert changed <= allowed, changed
    save(case/'inputs.json', manifest(runs))
    return case


def summarize(case, trial):
    wid = trial['id']; output = case/'output'; cli = case/'runs'/f'p{wid}.cli'
    kwargs = dict(version_major=1, version_minor=0)
    p = pd.DataFrame(native.hillslope_pass_to_columns(str(output/f'H{wid}.pass.dat'), **kwargs))
    e = pd.DataFrame(native.hillslope_ebe_to_columns(str(output/f'H{wid}.ebe.dat'), start_year=2000, **kwargs))
    s = pd.DataFrame(native.hillslope_soil_to_columns(str(output/f'H{wid}.soil.dat'), start_year=2000, **kwargs))
    for frame in (p,e,s):
        assert np.isfinite(frame.select_dtypes(include='number')).all().all()
        assert not frame.duplicated(['year','julian']).any()
    assert len(p)==36525 and len(s)==36525
    assert set(p.year)==set(s.year)==set(range(2000,2100))
    e.to_parquet(case/'events.parquet',index=False,compression='zstd')
    p.loc[p.event.eq('EVENT')].to_parquet(case/'peaks.parquet',index=False,compression='zstd')
    s[['year','julian','Rough','Keff','Ki','Kr','Tauc']].to_parquet(case/'soil.parquet',index=False,compression='zstd')
    rr = s.Rough.to_numpy()/1000
    first = s.year.eq(2000).to_numpy()
    peak = p.loc[p.event.eq('EVENT'),'peakro'].to_numpy()
    return_rows = []
    for line in (output/f'H{wid}.pass.dat').read_text().splitlines():
        if line.startswith('SRC3 '):
            fields=line.split()
            if fields[3]=='1':
                return_rows.append(float(fields[6]))
    return dict(**trial, daily_records=len(p), event_records=len(e),
        runoff_mm=float(e['Runoff'].sum()), sediment_kg_m=float(e['Sed.Del'].sum()),
        interrill_kg_m2=float(e['IR-det'].sum()),
        mean_detachment_kg_m2=float(e['Av-det'].sum()),
        mean_deposition_kg_m2=float(e['Av-dep'].sum()),
        peak_max_m3_s=float(peak.max()) if len(peak) else 0.,
        peak_p95_m3_s=float(np.quantile(peak,.95)) if len(peak) else 0.,
        pass_surface_m3=float(p.runvol.sum()), pass_lateral_m3=float(p.sbrunv.sum()),
        pass_drain_m3=float(p.drrunv.sum()), pass_baseflow_m3=float(p.gwbfv.sum()),
        return_events=len(return_rows), return_component_m3=sum(return_rows),
        rough_min_m=float(rr.min()), rough_max_m=float(rr.max()),
        rough_median_m=float(np.median(rr)),
        rough_first_year_median_m=float(np.median(rr[first])),
        rough_later_median_m=float(np.median(rr[~first])),
        rif_zero_days=int((rr>=1.14/23).sum()),
        first_year_runoff_mm=float(e.loc[e.year.eq(2000),'Runoff'].sum()),
        first_year_sediment_kg_m=float(e.loc[e.year.eq(2000),'Sed.Del'].sum()))


def run_case(trial):
    path = ROOT/'cases'/trial['case']
    if (path/'receipt.json').exists():
        record=json.loads((path/'receipt.json').read_text())
        assert record['success'] and record['binary_sha256']==SHA
        assert record['outputs']==manifest(path/'output')
        if not (path/'summary.json').exists():
            save(path/'summary.json',summarize(path,trial))
        return json.loads((path/'summary.json').read_text())
    case=stage(trial); wid=trial['id']; started=time.monotonic()
    with (case/'runs'/f'p{wid}.run').open('rb') as inp, (case/'stdout.log').open('wb') as out, (case/'stderr.log').open('wb') as err:
        process=subprocess.run([str(ROOT/'wepp_hill')],cwd=case/'runs',stdin=inp,stdout=out,stderr=err,timeout=1200)
    text=(case/'stdout.log').read_text(); stderr=(case/'stderr.log').read_text()
    years=list(map(int,re.findall(r'SIMULATION YEAR\s*=\s*(\d+)',text)))
    success=process.returncode==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in text and years==list(range(1,101))
    success=success and not any(x in text+stderr for x in ['Program stop','Fortran runtime error','PASS components error:'])
    receipt=dict(success=success,returncode=process.returncode,years=years,
        seconds=time.monotonic()-started,binary_sha256=SHA,outputs=manifest(case/'output'))
    save(case/'receipt.json',receipt)
    assert success,(trial,receipt)
    summary=summarize(case,trial)
    save(case/'summary.json',summary)
    return summary


def execute(sentinels=False):
    assert sha(ROOT/'wepp_hill')==SHA
    plan=json.loads((ROOT/'plan.json').read_text())
    if sentinels:
        plan=[t for t in plan if t['texture']=='loam' and t['severity']==0 and
              t['vegetation'] in ('forest','young forest','shrub','tall grass') and
              (t['reference'] or t['rrinit_m']==.006)]
    else:
        assert json.loads((ROOT/'sentinels.json').read_text())['failures']==[]
    results=[]; failures=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs={pool.submit(run_case,t):t for t in plan}
        for future in as_completed(jobs):
            try:
                results.append(future.result())
            except (OSError,ValueError,KeyError,AssertionError,subprocess.SubprocessError) as exc:
                failures.append(dict(case=jobs[future]['case'],error=str(exc),kind=type(exc).__name__))
            save(ROOT/'progress.json',dict(expected=len(plan),complete=len(results),failures=failures))
            if (len(results)+len(failures))%16==0:
                print(f'COMPLETE {len(results)}/{len(plan)} FAILURES {len(failures)}',flush=True)
    save(ROOT/('sentinels.json' if sentinels else 'execution.json'),dict(expected=len(plan),complete=len(results),failures=failures))
    assert not failures, failures
    pd.DataFrame(results).sort_values(['profile','id','rrinit_m']).to_csv(ROOT/('sentinel-results.csv' if sentinels else 'case-results.csv'),index=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','sentinels','execute'])
    args=parser.parse_args()
    {'prepare':prepare,'sentinels':lambda:execute(True),'execute':execute}[args.command]()
