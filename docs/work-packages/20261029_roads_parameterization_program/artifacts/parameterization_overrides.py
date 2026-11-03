"""Declared study-only native road header overrides; no production wiring."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import calendar
import importlib.util
import math
import subprocess
from pathlib import Path
import re
import shutil
import sys

from tests.roads import roads_matrix as matrix
from tests.roads import roads_sensitivity as h
from wepppy.wepp.soils.utils import WeppSoilUtil
import revised_sensitivity as prior

ART = Path(__file__).resolve().parent
REPO = ART.parents[3]
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1')
CONTEXTS = {'road': matrix.Case('median', 'loam', 'gravel', 'low', 'bare_direct'),
            'road_fill_buffer': matrix.Case('median', 'loam', 'gravel', 'low', 'rutted')}
DECLARATION = ROOT / 'declaration-v5.json'
FIELDS = {'avke': 8, 'ki': 5, 'kr': 6, 'shcrit': 7}
BINS = {'wepp_261029': '4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825',
        'wepp_261029_hill': '210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936'}

def read(path):
    return json.loads(Path(path).read_text())

def dependencies():
    result = {str((REPO / k).resolve()): v for k,v in matrix.execution_identity()['source_sha256'].items()}
    paths = [Path(__file__), ART / 'parameterization-overrides-protocol.md', Path(h.__file__)]
    paths += [Path(m.__file__) for m in tuple(sys.modules.values())
              if getattr(m, '__file__', None) and str(m.__file__).startswith(str(ART)) and str(m.__file__).endswith('.py')]
    paths += list((REPO / 'wepppy/wepp/interchange').glob('*.py'))
    result.update(prior.seeds.common.effective_dependencies())
    for path in paths:
        result[str(path.resolve())] = h.digest(path)
    for name,expected in BINS.items():
        path = REPO / 'wepp_runner/bin' / name
        if h.digest(path) != expected:
            raise ValueError('Installed r7 binary identity mismatch')
        result[str(path)] = expected
    from wepppyo3 import wepp_interchange
    libraries = list(Path(wepp_interchange.__file__).parent.glob('*.so'))
    if not libraries:
        raise ValueError('Native reader library identity absent')
    for path in [*libraries, *(ROOT / 'native-source').iterdir()]:
        result[str(path)] = h.digest(path)
    return result

def verify(bindings):
    for path,digest in bindings.items():
        if h.digest(path) != digest:
            raise ValueError(f'Dependency drift: {path}')

def stage_source():
    source = Path('/workdir/wepp-forest-release-20261009')
    target = ROOT / 'native-source'
    target.mkdir()
    commit = 'e0abe0581f77c6f66917e90daf8f8f429e9315c8'
    files = {}
    for name in ('input.for','tilage.for','infpar.for','param.for','scon.for'):
        data = subprocess.check_output(['git','-C',str(source),'show',f'{commit}:src/{name}'])
        if data != (source/'src'/name).read_bytes():
            raise ValueError('Selected source differs from r7')
        (target/name).write_bytes(data)
        files[name] = h.digest(target/name)
    release = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD']).decode().strip()
    if not release.startswith('547b9e7eb'):
        raise ValueError('Unexpected source release')
    h.save_new(target/'receipt.json',dict(source_commit=commit,release_head=release,files=files))


def audit(row, climate, response):
    """Use actual OFE/calendar membership; preserve existing printed tolerances."""
    import pyarrow.parquet as pq
    root=Path(row['root']); record=row['record']; capsule=root/'wepp/roads'
    terminal=len(record['ofe_order']); first=int(climate['first'][:4]); years=climate['years']
    parsed=dict(case=dict(context=row['context'],arm=row['arm'],runtime='project'),
        inputs={n:v for n,v in record['prepared_files'].items() if n!='reference.sol'},
        outputs={Path(k).name:v for k,v in record['output_sha256'].items()},
        width_m=record['emitted']['width_m'],soil_readback=record['soil_readback'])
    parsed['metrics']=prior.seeds.common.c.b.parse_loss(capsule/'output/H1.loss.dat',parsed['width_m'],require_annual=False)
    h.save_new(capsule/'record.json',parsed)
    # Private module instances adapt only terminal OFE membership, not predicates.
    def private(name):
        spec=importlib.util.spec_from_file_location('override_'+name,ART/(name+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    particles=private('audit_particle_closure_v2');particles.TERMINAL_OFE=terminal
    completeness=private('audit_pass_completeness_r7');completeness.particles=particles
    complete=completeness.audit(capsule/'record.json',climate)
    particle=particles.audit(capsule/'record.json')
    tables=capsule/'output/interchange'
    erows=pq.read_table(tables/'H.element.parquet').to_pylist()
    wrows=pq.read_table(tables/'H.wat.parquet').to_pylist()
    brows=pq.read_table(tables/'H.ebe.parquet').to_pylist()
    dates={(y,j) for y in range(first,first+years) for j in range(1,366+calendar.isleap(y))}
    for ofe in range(1,terminal+1):
        actual=[(r['year'],r['julian']) for r in wrows if r['OFE']==ofe]
        if len(actual)!=len(dates) or set(actual)!=dates:
            raise ValueError('Incomplete WAT role calendar')
    for line in (capsule/'output/H1.wat.dat').read_text().splitlines():
        fields=line.split()
        if fields and fields[0].isdigit() and any(not math.isfinite(float(v)) or float(v)<0 for v in fields[3:]):
            raise ValueError('Invalid signed/nonfinite native water field')
    terminal_rows={}
    for r in erows:
        if not math.isfinite(r['SedLeave']) or r['SedLeave']<0:
            raise ValueError('Invalid native sediment boundary')
        if r['OFE']==terminal:
            key=(r['year'],r['julian'])
            if key in terminal_rows or key not in dates:
                raise ValueError('Duplicate/outside terminal calendar')
            terminal_rows[key]=r['SedLeave']
    seen=set();max_ebe=0.
    for r in brows:
        key=(r['year'],r['julian']);value=r['Sed.Del']
        if key in seen or key not in terminal_rows or value is None or not math.isfinite(value):
            raise ValueError('Invalid EBE calendar/value')
        seen.add(key);delta=abs(value-terminal_rows[key]);max_ebe=max(max_ebe,delta)
        if delta>.0505+abs(value)*1e-6:
            raise ValueError('EBE/terminal ELEMENT mismatch')
    if not seen or any(v!=0 for k,v in terminal_rows.items() if k not in seen):
        raise ValueError('Missing EBE terminal sediment event')
    terminal_export=sum(terminal_rows.values())*parsed['width_m']/years
    report_export=parsed['metrics']['sediment_export_kg_yr']
    bound=(len(terminal_rows)*.0005/years+.0005)*parsed['width_m']+abs(report_export)*1e-6
    if abs(terminal_export-report_export)>bound:
        raise ValueError('Printed LOSS/terminal ELEMENT mismatch')
    stdout=(capsule/'runs/stdout').read_text()
    markers={key:text in stdout for key,text in {'ui':'WEPP hourly water seepage update set (UI code)','groundwater':'Gwcoeff parameters set','pmet':'FAO Penman-Monteith ET Method Implemented'}.items()}
    if not all(markers.values()):
        raise ValueError('Declared runtime not activated')
    result=dict(physical_pass=True,calendar_pass=complete['passed'],particle_pass=particle['passed'],particle_flags=particle['flags'],terminal_ofe=terminal,terminal_export_kg_yr=terminal_export,report_export_kg_yr=report_export,report_printed_bound_kg_yr=bound,max_ebe_delta_kg_m=max_ebe,full_water_storage_closure_claim=False,runtime_markers=markers)
    h.save_new(root/'audits.json',dict(summary=result,completeness=complete,particles=particle))
    return result

def prepare(root, case, field, factor):
    record = h.prepare(root, case)
    runs = root / 'wepp/roads/runs'
    (root / 'prepared.json').rename(root / 'canonical-prepared.json')
    before = record['soil_readback']
    if field:
        lines = (runs / 'p1.sol').read_text().splitlines(keepends=True)
        found = 0
        for i,line in enumerate(lines):
            if line.startswith("'Road'"):
                tokens = list(re.finditer(r"'[^']*'|\S+", line))
                token = tokens[FIELDS[field]]
                value = float(token.group()) * factor
                lines[i] = line[:token.start()] + format(value, '.12g') + line[token.end():]
                found += 1
        if found != 1:
            raise ValueError('Expected exactly one native Road header')
        (runs / 'p1.sol').write_text(''.join(lines))
    after = WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes']
    expected = json.loads(json.dumps(before))
    if field:
        expected[0][field] *= factor
    if after != expected:
        raise ValueError('Override changed unexpected soil semantics')
    record.update(soil_readback=after, requested_override={'role':'road','field':field,'factor':factor},
                  canonical_prepared_sha256=h.digest(root / 'canonical-prepared.json'),
                  input_sha256={str(p.relative_to(root)):h.digest(p) for p in runs.glob('p1.*')},
                  prepared_files=h.inventory(runs))
    h.save_new(root / 'prepared.json', record)
    return record

def declare():
    ROOT.mkdir(parents=True, exist_ok=False)
    stage_source()
    dep = dependencies()
    tasks = []
    arms = [('baseline',None,1.)] + [(f'{f}_{label}',f,factor) for f in FIELDS for label,factor in [('half',.5),('double',2.)]]
    for context,case in CONTEXTS.items():
        for arm,field,factor in arms:
            root = ROOT / context / arm
            record = prepare(root,case,field,factor)
            tasks.append(dict(context=context,arm=arm,generated=False,climate='fixture',root=str(root),record=record))
    verify(dep)
    h.save_new(DECLARATION,dict(tasks=tasks,dependencies=dep,binaries=BINS,native_source='e0abe0581f77c6f66917e90daf8f8f429e9315c8',calls=18,withheld_materials_used=False))
    print('Declared 18 profiles, no native calls',flush=True)

def bind():
    d=read(ROOT/'declaration-v4.json')
    d['dependencies'] = dependencies()
    d['predecessor_declaration_sha256'] = h.digest(ROOT/'declaration-v4.json')
    d['binding_amendment'] = 'Preserve nonempty EBE event requirement from existing accounting audit. No native calls or scientific-input changes.'
    h.save_new(DECLARATION,d)

def run():
    d=read(DECLARATION); review=read(ROOT/'execution-review-v5.json')
    if review.get('declaration_sha256') != h.digest(DECLARATION) or review.get('passed') is not True:
        raise ValueError('Missing exact declaration review')
    verify(d['dependencies'])
    h.save_new(ROOT/'execution-start.json',{'declaration_sha256':h.digest(DECLARATION)})
    results=[]
    for row in d['tasks']:
        root=Path(row['root'])
        try:
            row['record']=h.execute(root,row['record'])
            climate=prior.climate_for(row)
            response=h.summarize(root,row['record'],start_year=int(climate['first'][:4]),years=climate['years'])
            diagnostics=audit(row, climate, response)
            if not all(diagnostics[k] for k in ('physical_pass','calendar_pass','particle_pass')):
                raise ValueError('Strict native artifact gate failed')
        except Exception as exc:
            # Deliberate isolated study boundary retains parser/audit failure evidence.
            if not (root/'failure.json').exists():
                h.save_new(root/'failure.json',dict(exception=type(exc).__name__,message=str(exc),artifacts=h.inventory(root/'wepp/roads')))
            raise
        result=dict(context=row['context'],arm=row['arm'],root=str(root),diagnostics=diagnostics,response=response)
        h.save_new(root/'result.json',result);results.append(result)
        verify(d['dependencies'])
        print(row['context'],row['arm'],response['summary']['runoff_volume_m3'],response['summary']['sediment_yield_kg'],flush=True)
    h.save_new(ROOT/'results.json',results)

def analyze():
    results=read(ROOT/'results.json'); d=read(DECLARATION);verify(d['dependencies'])
    rows=[]
    for context in CONTEXTS:
        base=next(r for r in results if r['context']==context and r['arm']=='baseline')
        base_record=read(Path(base['root'])/'prepared.json')
        for result in [r for r in results if r['context']==context]:
            record=read(Path(result['root'])/'prepared.json')
            changes=h.paired_input_changes(base_record,record)
            if changes != ([] if result['arm']=='baseline' else ['wepp/roads/runs/p1.sol']):
                raise ValueError('Unexpected paired input changes')
            response=result['response']; b=base['response']['summary'];s=response['summary']
            metrics={key:dict(value=s[key],baseline=b[key],delta=s[key]-b[key],percent=None if b[key]==0 else 100*(s[key]/b[key]-1)) for key in ('runoff_volume_m3','sediment_yield_kg','sediment_yield_density_kg_m2','runoff_depth_mm')}
            paired=h.paired_events(base['root'],result['root'])
            h.save_new(Path(result['root'])/'paired-events.json',paired)
            rows.append(dict(context=context,arm=result['arm'],metrics=metrics,role_boundary=response['role_boundary'],strict_audits=result['diagnostics'],input_changes=changes))
    h.save_new(ROOT/'analysis.json',dict(rows=rows,profile_count=len(results),native_calls=len(results),source_hashes=d['dependencies'],declaration_sha256=h.digest(DECLARATION),results_sha256=h.digest(ROOT/'results.json')))
    print(json.dumps(rows,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('declare','bind','run','analyze'));parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    ROOT=args.root
    DECLARATION=ROOT/'declaration-v5.json'
    {'declare':declare,'bind':bind,'run':run,'analyze':analyze}[args.action]()
