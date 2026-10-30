"""Isolated, fail-closed WEPP2010/261026 scientific benchmark (not production)."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
import hashlib
from functools import partial
import itertools
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time

REPO = Path(__file__).resolve().parents[4]
DEFAULT_ROOT = Path('/wc1/runs/ro/roads-soil-benchmark-20261029')
SPECIMENS = {
    'sand': '/wc1/runs/ad/addicted-reservist/soils/1718465.sol',
    'loam': '/wc1/runs/cl/clogging-starch/soils/2711184.sol',
    'silt': '/wc1/runs/cl/clogging-starch/soils/2711250.sol',
    'clay': '/wc1/runs/ad/addicted-reservist/soils/1718510.sol',
}
CLIMATES = {'birmingham': 'default', 'denver': 'run_2', 'flagstaff': 'run_3', 'charleston': 'run_4'}
VARIANTS = ('generated', 'road_erosion', 'road_conductivity', 'road_rock', 'road_combined', 'all_combined')
NUM = r'[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def climate_subset(source, target, years=16):
    """Select complete original calendar years, retaining meteorological bytes."""
    lines = Path(source).read_text().splitlines(True)
    start = next(i for i, s in enumerate(lines) if s.split()[:3] == ['da', 'mo', 'year']) + 2
    rows = []
    for s in lines[start:]:
        fields = s.split()
        if not fields:
            continue
        d, m, y = map(int, fields[:3])
        rows.append((date(y, m, d), s))
    first = rows[0][0]
    if (first.month, first.day) != (1, 1):
        raise ValueError('Climate must start January 1')
    end = date(first.year + years, 1, 1)
    selected = [(d, s) for d, s in rows if d < end]
    expected = [first + timedelta(days=i) for i in range((end-first).days)]
    if [d for d, _ in selected] != expected:
        raise ValueError(f'Incomplete/duplicate climate calendar: {source}')
    # Header duration is metadata; rewrite only the advertised number of years.
    header = lines[:start]
    tokens = header[4].split()
    tokens[-2:] = [str(first.year), str(years)]
    header[4] = ' '.join(tokens) + '\n'
    Path(target).write_text(''.join(header) + ''.join(s for _, s in selected))
    return dict(first=str(first), last=str(selected[-1][0]), days=len(selected), years=years,
                source=str(source), source_sha256=digest(source), sha256=digest(target))


def parse_loss(path, width, require_annual=True):
    """Read common native report; net spatial loss is NOT gross daily detachment."""
    text = Path(path).read_text()
    if text.count('ANNUAL AVERAGE SUMMARIES') != 1:
        raise ValueError(f'Missing/duplicate final summary: {path}')
    summary = text.split('ANNUAL AVERAGE SUMMARIES')[1]
    def number(pattern, block=summary):
        matches = re.findall(pattern, block)
        if len(matches) != 1:
            raise ValueError(f'Expected one {pattern!r} in {path}: {matches}')
        value = float(matches[0])
        if not math.isfinite(value):
            raise ValueError(f'Nonfinite output: {path}')
        return value
    years = int(number(r'Number of years\s+(\d+)'))
    export = number(r'\n\s*(' + NUM + r')\s+kg/m of width') * width
    rain = number(r'Mean annual runoff from rainfall\s+(' + NUM + ')')
    snow = number(r'and/or rain storm during winter\s+(' + NUM + ')')
    if 'AREA OF NET SOIL LOSS' in summary:
        loss_block = summary.split('AREA OF NET SOIL LOSS')[1].split('AREA OF SOIL DEPOSITION')[0]
        avg = number(r'Avg\. of Net Detachment Areas\)\s*=\s*(' + NUM + ')', loss_block)
        regions = re.findall(r'^\s*(' + NUM + r')\s*-\s*(' + NUM + r')\s+(' + NUM + r')\s', loss_block, re.M)
        if not regions and avg != 0:
            raise ValueError(f'Nonzero loss without spatial regions: {path}')
    else:
        # Native WEPP omits A/B sections when no positive spatial loss exists.
        # Require the full printed profile as evidence, never default a missing metric.
        profile = summary.split('SOIL LOSS/DEPOSITION ALONG SLOPE PROFILE')[1].split('OFF SITE EFFECTS')[0]
        points=[]
        for line in profile.splitlines():
            fields=line.split()
            if len(fields)==9 and all(fields[i].isdigit() for i in (2,5,8)):
                points.extend((float(fields[i]),float(fields[i+1]),int(fields[i+2])) for i in (0,3,6))
        if (len(points)!=300 or {o for _,_,o in points}!={1,2,3}
                or any(v>0 or not math.isfinite(v) or not math.isfinite(x) for x,v,_ in points)):
            raise ValueError('Missing loss section without complete nonpositive profile evidence')
        regions=[]
    net_loss = 0.0
    for a, b, v in regions:
        a, b, v = map(float, (a,b,v))
        if b < a or v < 0 or not all(math.isfinite(x) for x in (a,b,v)):
            raise ValueError('Invalid net loss interval')
        net_loss += (b-a)*v*width
    yearly = []
    pieces = re.split(r'HILLSLOPE\s+1\s+YEARLY SUMMARY FOR\s+(\d+)', text.split('ANNUAL AVERAGE SUMMARIES')[0])
    for i in range(1, len(pieces), 2):
        block = pieces[i+1]
        match = re.search(r'SEDIMENT LEAVING PROFILE for year\s+\d+\s+(' + NUM + r')\s*kg/m', block)
        if not match:
            raise ValueError('Missing yearly sediment export')
        yearly.append(dict(year=int(pieces[i]), sediment_export_kg=float(match[1])*width))
    if require_annual and (len(yearly) != years or len({r['year'] for r in yearly}) != years):
        raise ValueError(f'Incomplete yearly summaries: {len(yearly)} != {years}')
    # Reports have decimal rounding plus native accumulation precision. The
    # long paved-silt modern control differs by 6.1e-7 relatively; retain its
    # discrepancy, admitting at most 1e-6 relative or one displayed decimal unit.
    annual_mean=sum(r['sediment_export_kg'] for r in yearly)/years if yearly else None
    if yearly and not math.isclose(annual_mean, export, rel_tol=1e-6, abs_tol=0.0011*width):
        raise ValueError('Annual and mean export disagree beyond report precision')
    return dict(years=years, sediment_export_kg_yr=export,
                spatial_net_loss_kg_yr=net_loss, runoff_mm_yr=rain+snow,
                annual_export=yearly, export_resolution_kg=0.001*width,
                annual_mean_export_delta_kg=(annual_mean-export) if yearly else None)


def validate_wat(path, calendar, nofe=3):
    """Validate common date columns only; do not translate unsupported 2010 fluxes."""
    rows = []
    with Path(path).open() as f:
        for line in f:
            fields = line.split()
            if len(fields) >= 17 and all(x.isdigit() for x in fields[:3]):
                if not all(math.isfinite(float(x)) for x in fields):
                    raise ValueError('Nonfinite WAT row')
                rows.append(tuple(map(int, fields[:3])))
    first, last = date.fromisoformat(calendar['first']), date.fromisoformat(calendar['last'])
    expected = set()
    d = first
    observed_years = {r[2] for r in rows}
    calendar_years = set(range(first.year,last.year+1))
    simulation_years = set(range(1,calendar['years']+1))
    if observed_years == calendar_years:
        offset = 0
    elif observed_years == simulation_years:
        offset = first.year-1
    else:
        raise ValueError('WAT years do not cover climate')
    while d <= last:
        expected.update((o, d.timetuple().tm_yday, d.year-offset) for o in range(1,nofe+1))
        d += timedelta(days=1)
    if len(rows) != len(expected) or set(rows) != expected:
        raise ValueError(f'Incomplete WAT dates: {len(rows)} rows, expected {len(expected)}')
    return len(rows)


def stage(root):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    inputs = root/'inputs'
    inputs.mkdir(exist_ok=False)
    (inputs/'soils').mkdir()
    (inputs/'climates').mkdir()
    manifest = dict(soils={}, climates={}, binaries={}, holdout={'climate':'charleston', 'soil':'clay'},
                    harness_sha256=digest(__file__))
    for texture, source in SPECIMENS.items():
        target = inputs/'soils'/f'{texture}.sol'
        shutil.copy2(source,target)
        soil = WeppSoilUtil(str(target))
        if soil.obj['datver'] != 7778 or soil.obj['ntemp'] != 1:
            raise ValueError('Study specimens must be generated single-OFE 7778 soils')
        manifest['soils'][texture] = dict(source=source,sha256=digest(target),data=soil.obj)
    for name, case in CLIMATES.items():
        source = next((root/'reference/parity-runs/wepproad'/case/'legacy/working').glob('*.cli'))
        manifest['climates'][name] = climate_subset(source,inputs/'climates'/f'{name}.cli')
    manifest['climates']['site'] = climate_subset(REPO/'tests/roads/data/site.cli',inputs/'climates/site.cli')
    for label, path in [('legacy',root/'reference/bin/wepp2010'),('modern',REPO/'wepp_runner/bin/wepp_261026')]:
        manifest['binaries'][label] = dict(path=str(path),sha256=digest(path))
    manifest['reference_templates'] = {str(p.relative_to(root)):digest(p) for p in
        sorted((root/'reference/api/db/wepproad').rglob('*')) if p.is_file()}
    manifest['sources'] = {str(p.relative_to(REPO)):digest(p) for p in [
        REPO/'wepppy/wepp/soils/utils/wepp_soil_util.py', REPO/'wepp_runner/templates/hillslope.template',
        REPO/'wepppy/nodb/mods/roads/roads.py']}
    dump(inputs/'manifest.json',manifest)
    return manifest


def reference_soil(root, texture, design, surface, traffic, output, cloud_lookup=False):
    """Use production road adjustment writer; explicitly select reference lookup."""
    from wepppy.nodb.mods.roads import Roads
    tau = '10' if design == 'inveg' else '1' if surface == 'paved' and (design == 'inbare' or cloud_lookup) else '2'
    template = root/'reference/api/db/wepproad/soils'/f'3{"p" if surface == "paved" else "g"}{texture}{tau}.sol'
    known_trailing_k = {
        '3psand10.sol': 'ee0f7441fc97ad08cf1a15cd81a2f9c4f62a8506c0861b6047b09e0c57483750',
        '3pclay2.sol': '31f939fcea97da6e24371435695ee79a0867cb2d73181b08884789a68642d565',
    }
    if template.name in known_trailing_k:
        # Two enumerated fswepp2 assets have a trailing capture character after
        # their three OFEs. Require their exact original bytes before repair.
        if digest(template) != known_trailing_k[template.name] or not template.read_text().endswith('k\n'):
            raise ValueError('Unrecognized reference template version')
        clean=template.read_text()[:-2]
        template=output.parent/f'normalized-{template.name}'
        template.write_text(clean)
    Roads._build_routed_three_ofe_soil_file(object.__new__(Roads),template_path=template,output_path=output,
                                           traffic=traffic,surface=surface,rfg_pct=20.)


def generated_soil(source, legacy, output, variant):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    soil = WeppSoilUtil(str(source))
    references = WeppSoilUtil(str(legacy)).obj['ofes']
    soil.obj['ofes'] = [deepcopy(soil.obj['ofes'][0]) for _ in range(3)]
    soil.obj['ntemp'] = 3
    for i, ofe in enumerate(soil.obj['ofes']):
        target = references[i]
        if i != 0 and variant != 'all_combined':
            continue
        if variant in ('road_erosion','road_combined','all_combined'):
            for key in ('ki','kr','shcrit'):
                ofe[key] = target[key]
        if variant in ('road_conductivity','road_combined','all_combined'):
            ofe['horizons'][0]['ksat'] = target['avke']
        if variant in ('road_rock','road_combined','all_combined'):
            ofe['horizons'][0]['rfg'] = target['horizons'][0]['rfg']
    soil.obj['header'].append(f'Benchmark experimental variant: {variant}; source={source.name}')
    soil.write(str(output))
    readback = WeppSoilUtil(str(output)).obj
    if readback['ofes'] != soil.obj['ofes']:
        raise ValueError('Generated soil semantic readback mismatch')
    return readback


def slope_text(design):
    length, width, grade = 60.96, 3.96, 0.04
    if design == 'outunrut':
        grade = math.hypot(grade,0.04)
        sim_length = width*grade/0.04
        width = length*width/sim_length
        length = sim_length
    # Match fswepp2's emitted two-decimal slope coordinates and lengths.
    text = (f'97.3\n# Benchmark matched fswepp2 geometry\n3\n100 {width:.15g}\n'
            f'2 {length:.2f}\n0.00, {grade:.2f} 1.00, {grade:.2f}\n'
            f'3 4.57\n0.00, {grade:.2f} 0.05, 0.50 1.00, 0.50\n'
            '3 39.62\n0.00, 0.50 0.05, 0.25 1.00, 0.25\n')
    return text, width, round(length,2)+4.57+39.62


def execute_case(root, manifest, case, batch):
    from wepp_runner import make_hillslope_run
    from wepppy.wepp.soils.utils import WeppSoilUtil
    name = '-'.join(case.values())
    folder = root/batch/name
    runs, output = folder/'runs', folder/'output'
    runs.mkdir(parents=True,exist_ok=False)
    output.mkdir()
    record = dict(case=case,name=name,status='prepared')
    legacy = runs/'reference.sol'
    reference_soil(root,case['soil'],case['design'],case['surface'],case['traffic'],legacy,
                   cloud_lookup=case['variant']=='cloud_legacy')
    if case['variant'] in ('legacy','cloud_legacy'):
        shutil.copy2(legacy,runs/'p1.sol')
    else:
        generated_soil(root/'inputs/soils'/f"{case['soil']}.sol",legacy,runs/'p1.sol',case['variant'])
    man_name = {'inbare':'3inslope','inveg':'3inslope','outrut':'3outrut','outunrut':'3outunr'}[case['design']]
    if case['variant']=='cloud_legacy':
        man_name='3inslope'
    man_name += 'n.man' if case['traffic']=='none' else '.man'
    shutil.copy2(root/'reference/api/db/wepproad/managements'/man_name,runs/'p1.man')
    slope,width,length = slope_text(case['design'])
    (runs/'p1.slp').write_text(slope)
    shutil.copy2(root/'inputs/climates'/f"{case['climate']}.cli",runs/'p1.cli')
    calendar = manifest['climates'][case['climate']]
    make_hillslope_run(1,calendar['years'],str(runs),reveg=False,wepp_bin='wepp_261026')
    runfile = runs/'p1.run'
    run_lines = runfile.read_text().splitlines()
    if run_lines[6] != '1' or run_lines[5] != '../output/H1.pass.dat':
        raise ValueError('Unexpected runner prompt contract')
    run_lines[6] = '2'  # Detailed annual summaries; the runner strips comments.
    runfile.write_text('\n'.join(run_lines)+'\n')
    record.update(soil_readback=WeppSoilUtil(str(runs/'p1.sol')).obj,
                  width_m=width,profile_length_m=length,modeled_area_m2=width*length,
                  inputs={p.name:digest(p) for p in runs.iterdir() if p.is_file()})
    binary = manifest['binaries'][case['binary']]
    if digest(binary['path']) != binary['sha256']:
        raise ValueError('Binary changed')
    dump(folder/'record.json',record)
    start=time.monotonic()
    with (runs/'stdout').open('w') as out,(runs/'stderr').open('w') as err,runfile.open() as stdin:
        try:
            proc=subprocess.run([binary['path']],stdin=stdin,stdout=out,stderr=err,cwd=runs,timeout=90)
        except subprocess.TimeoutExpired:
            record.update(status='failed',error='native timeout')
            dump(folder/'record.json',record)
            return record
    record['elapsed_s']=time.monotonic()-start
    if proc.returncode != 0 or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        record.update(status='failed',error=f'native completion failed: {proc.returncode}')
    else:
        try:
            record['metrics']=parse_loss(output/'H1.loss.dat',width)
            record['wat_rows']=validate_wat(output/'H1.wat.dat',calendar)
            record['status']='completed'
        except (ValueError,IndexError) as exc:
            record.update(status='failed',error=str(exc))
    record['outputs']={p.name:digest(p) for p in output.iterdir() if p.is_file()}
    dump(folder/'record.json',record)
    return record


def matrix(phase, variants):
    climates = ('birmingham','denver','flagstaff','site') if phase=='screen' else (*CLIMATES,'site')
    soils = ('sand','loam','silt') if phase=='screen' else tuple(SPECIMENS)
    designs = ('outrut',) if phase=='screen' else ('inbare','inveg','outrut','outunrut')
    surfaces = ('gravel',) if phase=='screen' else ('gravel','paved')
    traffics = ('low',) if phase=='screen' else ('high','low','none')
    for climate,soil,design,surface,traffic in itertools.product(climates,soils,designs,surfaces,traffics):
        common=dict(climate=climate,soil=soil,design=design,surface=surface,traffic=traffic)
        for binary,variant in [('legacy','legacy'),('modern','legacy'),*[("modern",v) for v in variants]]:
            yield dict(**common,binary=binary,variant=variant)


def reproduce(root):
    """Fresh original-duration runs; compare common summary values to archives."""
    folder = root/'reproduce'
    folder.mkdir(exist_ok=False)
    shutil.copy2(__file__,folder/'execution-script.py')
    results=[]
    for case in ('default','run_2','run_3','run_4','run_5'):
        source=root/'reference/parity-runs/wepproad'/case/'legacy/working'
        original=next(source.glob('*.in'))
        original_lines=original.read_text().splitlines()
        for label,binary in [('legacy',root/'reference/bin/wepp2010'),
                             ('modern',REPO/'wepp_runner/bin/wepp_261026')]:
            d=folder/f'{case}-{label}'
            d.mkdir()
            for ext in ('sol','cli','slp'):
                shutil.copy2(next(source.glob(f'*.{ext}')),d/f'p.{ext}')
            soil=d/'p.sol'
            lines=soil.read_text().splitlines()
            stripped=lines[0].endswith('.sol')
            if stripped:
                soil.write_text('\n'.join(lines[1:])+'\n')
            management=root/'reference/api/db/wepproad/managements'/Path(original_lines[18]).name
            shutil.copy2(management,d/'p.man')
            prompts=['p.'+Path(s).suffix[1:] if s.endswith(('.sol','.slp','.cli','.man','.out')) else s
                     for s in original_lines]
            prompts[5]='2'
            (d/'p.in').write_text('\n'.join(prompts)+'\n')
            inputs={p.name:digest(p) for p in d.iterdir()}
            with (d/'stdout').open('w') as out,(d/'stderr').open('w') as err,(d/'p.in').open() as stdin:
                p=subprocess.run([str(binary)],stdin=stdin,stdout=out,stderr=err,cwd=d,timeout=90)
            row=dict(case=case,binary=label,binary_sha256=digest(binary),inputs=inputs,
                     removed_capture_filename_line=stripped,source_sha256={s.name:digest(s) for s in source.iterdir() if s.is_file()})
            if p.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (d/'stdout').read_text():
                row.update(status='failed',error=f'Native exit {p.returncode}')
            else:
                slope=[s for s in (d/'p.slp').read_text().splitlines() if s and not s.startswith('#')]
                width=float(slope[2].split()[1])
                row.update(status='completed',metrics=parse_loss(d/'p.out',width),
                           archived=parse_loss(next(source.glob('*.out')),width,require_annual=False),
                           output_sha256=digest(d/'p.out'))
                row['archive_deltas']={k:row['metrics'][k]-row['archived'][k] for k in
                                       ('sediment_export_kg_yr','spatial_net_loss_kg_yr','runoff_mm_yr')}
            results.append(row)
            dump(d/'record.json',row)
            print(case,label,row['status'],row.get('archive_deltas'),flush=True)
    dump(folder/'results.json',results)


def analyze_batch(root, batch):
    """Revalidate retained artifacts; leave execution records and failures immutable."""
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    folder=root/batch
    cases=json.loads((folder/'cases.json').read_text())
    rows=[]
    for case in cases:
        d=folder/'-'.join(case.values())
        record=json.loads((d/'record.json').read_text())
        if record['case']!=case:
            raise ValueError('Case identity mismatch')
        for sub,key in [('runs','inputs'),('output','outputs')]:
            for name,expected in record[key].items():
                if digest(d/sub/name)!=expected:
                    raise ValueError(f'Changed consumed artifact: {d/sub/name}')
        if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (d/'runs/stdout').read_text():
            raise ValueError(f'Native failure: {d}')
        metrics=parse_loss(d/'output/H1.loss.dat',record['width_m'])
        wat_rows=validate_wat(d/'output/H1.wat.dat',manifest['climates'][case['climate']])
        rows.append(dict(case=case,metrics=metrics,wat_rows=wat_rows,area_m2=record['modeled_area_m2'],
                         record_sha256=digest(d/'record.json')))
    dump(folder/'analysis.json',dict(analyzer_sha256=digest(__file__),rows=rows))
    print(f'Validated {len(rows)} cases and full daily calendars',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['stage','reproduce','screen','validate','analyze'])
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--batch',default=None)
    parser.add_argument('--variants',nargs='+',default=list(VARIANTS))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--resume',action='store_true',help='Retain completed cases and archive incomplete attempts')
    args=parser.parse_args()
    if args.phase=='analyze':
        if not args.batch:
            parser.error('analyze requires --batch')
        analyze_batch(args.root,args.batch)
        return
    if args.phase=='reproduce':
        reproduce(args.root)
        return
    if args.phase=='stage':
        manifest=stage(args.root)
        print(json.dumps({k:{n:{a:b for a,b in v.items() if a!='data'} for n,v in vals.items()}
                          for k,vals in manifest.items() if k in ('soils','climates','binaries')},indent=2))
        return
    manifest=json.loads((args.root/'inputs/manifest.json').read_text())
    for name, info in manifest['soils'].items():
        if digest(args.root/'inputs/soils'/f'{name}.sol') != info['sha256']:
            raise ValueError('Soil fixture changed')
    for name, info in manifest['climates'].items():
        if digest(args.root/'inputs/climates'/f'{name}.cli') != info['sha256']:
            raise ValueError('Climate fixture changed')
    cases=list(matrix(args.phase,args.variants))
    batch=args.batch or args.phase
    existing=[]
    if args.resume:
        folder=args.root/batch
        if json.loads((folder/'cases.json').read_text())!=cases:
            raise ValueError('Resume case matrix changed')
        original=json.loads((folder/'execution.json').read_text())
        if original['manifest_sha256']!=digest(args.root/'inputs/manifest.json'):
            raise ValueError('Resume fixture manifest changed')
        if (folder/'resume.json').exists():
            raise ValueError('Only one explicitly recorded resume epoch is supported')
        completed={}
        for case in cases:
            d=folder/'-'.join(case.values())
            p=d/'record.json'
            record=json.loads(p.read_text()) if p.exists() else None
            if record and record['case']==case and record['status']=='completed':
                existing.append(record)
                completed[d.name]=digest(p)
            elif d.exists():
                (folder/'failed-attempts').mkdir(exist_ok=True)
                shutil.move(str(d),str(folder/'failed-attempts'/d.name))
        shutil.copy2(__file__,folder/'resume-execution-script.py')
        dump(folder/'resume.json',dict(harness_sha256=digest(__file__),completed_record_sha256=completed,
                                      reason='Admit exact trailing-k repair for 3pclay2; completed case inputs unchanged'))
        pending=[c for c in cases if '-'.join(c.values()) not in completed]
    else:
        (args.root/batch).mkdir(exist_ok=False)
        shutil.copy2(__file__,args.root/batch/'execution-script.py')
        dump(args.root/batch/'cases.json',cases)
        dump(args.root/batch/'execution.json',dict(harness_sha256=digest(__file__),manifest_sha256=digest(args.root/'inputs/manifest.json')))
        pending=cases
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows=existing
        for row in pool.map(partial(execute_case,args.root,manifest,batch=batch),pending):
            rows.append(row)
            print(f'{len(rows)}/{len(cases)} {row["status"]} {row["name"]} {row.get("error","")}',flush=True)
    by_name={r['name']:r for r in rows}
    rows=[by_name['-'.join(c.values())] for c in cases]
    dump(args.root/batch/'results.json',rows)
    if any(r['status']!='completed' for r in rows):
        raise SystemExit('Failed cases retained; no complete benchmark claim')


if __name__=='__main__':
    main()
