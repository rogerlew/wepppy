"""Read actual native artifacts; keep comparison and physical acceptance distinct."""
from __future__ import annotations
import argparse
import calendar
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import csv
import importlib.util
import json
import math
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('drainage_study',HERE/'study.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
b=s.b;a=s.a


def validate_runtime(folder, case, record):
    ui_present=(folder/'runs/wepp_ui.txt').exists()
    ui_banner='WEPP hourly water seepage update set (UI code)' in (folder/'runs/stdout').read_text()
    expected_ui='runtime' in case
    if ui_present!=expected_ui or ui_banner!=expected_ui:
        raise ValueError('Native UI mode mismatch')
    expected_files=set(record['inputs']) | {'reference.sol','stdout','stderr'}
    # Known, unconsumed intermediates from the frozen FSWEPP template repair.
    normalized={'normalized-3psand10.sol':'c37870ab65aa917be188d2e591323bf4973292cd26f066b30c1337dcc277954b',
                'normalized-3pclay2.sol':'3b76cbcc6d3e783351da3f7364b5ea4a36e6b00e01c01138e7b55930e53067a3'}
    for name,sha in normalized.items():
        artifact=folder/'runs'/name
        if artifact.exists():
            if b.digest(artifact)!=sha:raise ValueError('Reference intermediate drift')
            expected_files.add(name)
    if {p.name for p in (folder/'runs').iterdir()} != expected_files:
        raise ValueError('Unrecorded working-directory file')


def sediment_diagnostics(rows, width, years, report_export):
    days=a.grouped(rows,('SedLeave',))
    negative=[dict(year=r['year'],julian=r['julian'],ofe=r['OFE'],sediment_kg_m=r['SedLeave'])
              for r in rows if r['SedLeave']<0]
    if not negative:
        result,days=a.sediment_budget(rows,width,years,report_export,strict=False)
    else:
        # Invalid native fluxes remain signed diagnostics, never accepted budgets.
        totals=[dict(boundary_kg_yr=0.,net_kg_yr=0.,positive_daily_net_kg_yr=0.,negative_daily_net_kg_yr=0.) for _ in range(3)]
        for day in days.values():
            upstream=0.
            for i in range(3):
                flux=day[i+1]['SedLeave']*width/years;net=flux-upstream
                for key,value in (('boundary_kg_yr',flux),('net_kg_yr',net),('positive_daily_net_kg_yr',max(net,0)),('negative_daily_net_kg_yr',min(net,0))):
                    totals[i][key]+=value
                upstream=flux
        bound=(len(days)*.0005/years+.0005)*width+abs(report_export)*1e-6
        delta=totals[-1]['boundary_kg_yr']-report_export
        result=dict(ofes=totals,dates=len(days),report_delta_kg_yr=delta,report_bound_kg_yr=bound,
                    report_reconciled=False,numerical_report_reconciled=abs(delta)<=bound)
    result.update(negative_fluxes=negative,physical_budget_valid=not negative)
    return result,days


def analyze_case(task):
    import pyarrow.parquet as pq
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange
    from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange
    from wepppy.wepp.interchange.hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
    root,case,destination=task;name='-'.join(case.values());folder=root/'matrix-v1'/name
    record=json.loads((folder/'record.json').read_text())
    if record['case']!=case or record['status']!='completed':raise ValueError('Case identity drift')
    s.check_files(folder,record)
    validate_runtime(folder,case,record)
    actual=WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes']
    if actual!=record['soil_readback']:raise ValueError('Soil readback drift')
    if b.parse_loss(folder/'output/H1.loss.dat',record['width_m'])!=record['metrics']:raise ValueError('Report drift')
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    climate=manifest['climates'][case['climate']]
    first=int(climate['first'].split('-')[0]);last=int(climate['last'].split('-')[0])
    dates={(y,j) for y in range(first,last+1) for j in range(1,366+calendar.isleap(y))}
    erows=pq.read_table(run_wepp_hillslope_element_interchange(folder/'output',start_year=first,expected_hillslopes=1)).to_pylist()
    wrows=pq.read_table(run_wepp_hillslope_wat_interchange(folder/'output',expected_hillslopes=1)).to_pylist()
    brows=pq.read_table(run_wepp_hillslope_ebe_interchange(folder/'output',start_year=first,expected_hillslopes=1)).to_pylist()
    sediment,edays=sediment_diagnostics(erows,record['width_m'],16,record['metrics']['sediment_export_kg_yr'])
    if not set(edays)<=dates:raise ValueError('ELEMENT calendar outside climate')
    ebe=a.ebe_check(brows,edays,strict=False)
    lines=[l for l in (folder/'runs/p1.slp').read_text().splitlines() if l and not l.startswith('#')]
    width=float(lines[2].split()[1]);areas=[width*float(lines[i].split()[1]) for i in (3,5,7)]
    water=a.water_budget(wrows,areas,dates,16)
    buffer=[r for r in wrows if r['OFE']==3]
    expected_depth=math.floor(min(actual[2]['horizons'][-1]['solthk']+200,1800)/200)*200
    if {r['ProfileDepth'] for r in buffer}!={expected_depth}:raise ValueError('Unexpected native profile depth')
    if any(r['ProfilePorosityCap']<=0 for r in buffer):raise ValueError('Invalid porosity capacity')
    near=sum(r['SoilWaterTotal']>=.9*r['ProfilePorosityCap'] for r in buffer)
    late_dates={d for d in dates if d[0]>first}
    late=a.water_budget([r for r in wrows if r['year']>first],areas,late_dates,15)
    annual=record['metrics']['annual_export']
    result=dict(name=name,case=case,metrics=record['metrics'],sediment=sediment,ebe=ebe,
                water=water,late_water=late,buffer_state=dict(days=len(buffer),near_capacity_days=near,
                profile_depth_mm=expected_depth,porosity_capacity_mm=[min(r['ProfilePorosityCap'] for r in buffer),max(r['ProfilePorosityCap'] for r in buffer)]),
                late_report_export_kg_yr=sum(r['sediment_export_kg'] for r in annual[1:])/15,
                input_signature=s.signature(record['inputs']),
                semantic_input_signature=s.signature(dict(soil=[{k:v for k,v in o.items() if k not in ('slid','texid')} for o in actual],
                    other={k:v for k,v in record['inputs'].items() if k!='p1.sol'})),record_sha256=b.digest(folder/'record.json'))
    b.dump(destination/'cases'/f'{name}.json',result)
    return result


def references(root):
    """Rehash every reused reference; assert its consumed non-soil inputs match."""
    records={}
    for climate,texture,design,surface,traffic,binary in __import__('itertools').product(s.CLIMATES,b.SPECIMENS,s.DESIGNS,('gravel','paved'),('high','low','none'),('legacy','modern')):
        name='-'.join((climate,texture,design,surface,traffic,binary,'legacy'))
        folder=b.DEFAULT_ROOT/'validation-v4'/name
        record=json.loads((folder/'record.json').read_text());s.check_files(folder,record)
        if record['status']!='completed':raise ValueError('Failed legacy reference')
        metrics=b.parse_loss(folder/'output/H1.loss.dat',record['width_m'])
        # The frozen reference record predates this additive parser audit field.
        common={k:v for k,v in metrics.items() if k!='annual_mean_export_delta_kg' or k in record['metrics']}
        if common!=record['metrics']:raise ValueError('Legacy report drift')
        records[name]=dict(metrics=metrics,record_sha256=b.digest(folder/'record.json'),inputs=record['inputs'],root=str(folder))
    b.dump(root/'analysis-v1/reference-provenance.json',records)
    return records


def summarize(root,results,refs):
    records={r['name']:json.loads((root/'matrix-v1'/r['name']/'record.json').read_text()) for r in results}
    by_profile=defaultdict(dict)
    for r in results:
        c=r['case'];by_profile['-'.join(c[k] for k in ('climate','soil','design','surface','traffic'))][c['drainage']]=r
    rows=[];reproduction=[];aliases=defaultdict(list);effects=[]
    for profile,pair in by_profile.items():
        if set(pair)!={'current','source'}:raise ValueError('Incomplete pair')
        cur,new=pair['current'],pair['source'];c=cur['case']
        rcur,rnew=records[cur['name']],records[new['name']]
        declaration=json.loads((root/'declaration.json').read_text())
        if s.buffer_change(rcur['soil_readback'],declaration['endpoints'][c['soil']]['source'])!=rnew['soil_readback']:
            raise ValueError('Paired treatment leaked outside buffer boundary')
        for key in ('p1.man','p1.slp','p1.cli','p1.run'):
            if rcur['inputs'][key]!=rnew['inputs'][key]:raise ValueError('Paired nonsoil input drift')
        ref_prefix='-'.join((c['climate'],s.TEXTURES[c['soil']],c['design'],c['surface'],c['traffic']))
        legacy=refs[ref_prefix+'-legacy-legacy'];modern=refs[ref_prefix+'-modern-legacy']
        for ref in (legacy,modern):
            for key in ('p1.man','p1.slp','p1.cli','p1.run'):
                if rcur['inputs'][key]!=ref['inputs'][key]:raise ValueError(f'Reference input mismatch: {profile} {key}')
        for treatment in ('current','source','policy'):
            selected=s.policy(c['soil']) if treatment=='policy' else treatment
            result=pair[selected];metric=result['metrics']['sediment_export_kg_yr']
            ref=legacy['metrics']['sediment_export_kg_yr'];modern_ref=modern['metrics']['sediment_export_kg_yr']
            row=dict(profile=profile,**{k:v for k,v in c.items() if k!='drainage'},treatment=treatment,
                     selected=selected,classification=s.CLASS[c['soil']],previously_unused=c['soil'] in s.NEW,
                     export_kg_yr=metric,legacy_kg_yr=ref,modern_legacy_kg_yr=modern_ref,
                     runoff_mm_yr=result['metrics']['runoff_mm_yr'],legacy_runoff_mm_yr=legacy['metrics']['runoff_mm_yr'],
                     **s.comparison(metric,ref),modern_reference_ratio=s.comparison(metric,modern_ref)['ratio'],
                     input_signature=result['input_signature'],semantic_input_signature=result['semantic_input_signature'],buffer_dp_m3_yr=result['water']['ofes'][2]['deep_percolation_m3_yr'],
                     buffer_q_m3_yr=result['water']['ofes'][2]['surface_out_m3_yr'],
                     buffer_lat_m3_yr=result['water']['ofes'][2]['lateral_out_m3_yr'],
                     near_capacity_days=result['buffer_state']['near_capacity_days'],
                     late_export_kg_yr=result['late_report_export_kg_yr'])
            rows.append(row)
        effect=dict(profile=profile,soil=c['soil'],climate=c['climate'],design=c['design'])
        for role,i in (('road',0),('fill',1),('buffer',2)):
            effect[role+'_sediment_boundary_delta_kg_yr']=new['sediment']['ofes'][i]['boundary_kg_yr']-cur['sediment']['ofes'][i]['boundary_kg_yr']
            effect[role+'_sediment_net_delta_kg_yr']=new['sediment']['ofes'][i]['net_kg_yr']-cur['sediment']['ofes'][i]['net_kg_yr']
            for field in ('surface_in_m3_yr','surface_out_m3_yr','deep_percolation_m3_yr','lateral_out_m3_yr'):
                effect[role+'_'+field+'_delta']=new['water']['ofes'][i][field]-cur['water']['ofes'][i][field]
        effects.append(effect)
        for result in pair.values():aliases[result['input_signature']].append(result['name'])
        if c['soil'] not in s.NEW:
            old=s.e.ROOT/'confirmation-v1'/(profile+'-modern-roles')
            prior=json.loads((old/'record.json').read_text());s.check_files(old,prior)
            output_matches={k:sha==prior['outputs'][k] for k,sha in rcur['outputs'].items()}
            reproduction.append(dict(profile=profile,all_native_outputs_identical=all(output_matches.values()),outputs=output_matches,
                                     prior_record_sha256=b.digest(old/'record.json')))
    if len(rows)!=2880 or len(reproduction)!=600:raise ValueError('Incomplete comparisons')
    strata={}
    for dimension in ('all','soil','climate','design','surface','traffic','classification','previously_unused'):
        groups=defaultdict(list)
        for row in rows:groups[(row['treatment'],str(row.get(dimension,'all')))].append(row)
        strata[dimension]={}
        for (treatment,key),group in groups.items():
            ratios=sorted(r['ratio'] for r in group if r['ratio'] is not None)
            strata[dimension][treatment+':'+key]=dict(cases=len(group),positive=len(ratios),within=sum(r['within'] is True for r in group),
                above=sum(r['ratio'] is not None and r['ratio']>10 for r in group),below=sum(r['ratio'] is not None and r['ratio']<.1 for r in group),
                zeros=sum(r['zero_reference'] for r in group),zero_matches=sum(r['zero_match'] is True for r in group),
                min_ratio=min(ratios) if ratios else None,max_ratio=max(ratios) if ratios else None,
                median_ratio=__import__('statistics').median(ratios) if ratios else None)
    transitions={}
    for treatment in ('source','policy'):
        counts=Counter()
        mapping={(r['profile'],r['treatment']):r for r in rows}
        for profile in by_profile:
            old=mapping[profile,'current'];new=mapping[profile,treatment]
            counts[f"{old['within']}->{new['within']}"]+=1
        transitions[treatment]=dict(counts)
    summary=dict(strata=strata,transitions=transitions,native_cases=len(results),unique_consumed_input_signatures=len(aliases),
                 unique_semantic_input_signatures=len({r['semantic_input_signature'] for r in results}),
                 policy_is_selection_not_new_runs=True,prior_controls=len(reproduction),
                 prior_controls_exact=sum(r['all_native_outputs_identical'] for r in reproduction))
    summary['sediment_report_reconciled']=sum(r['sediment']['report_reconciled'] for r in results)
    summary['negative_sediment_cases']=sum(bool(r['sediment'].get('negative_fluxes')) for r in results)
    summary['negative_sediment_flux_records']=sum(len(r['sediment'].get('negative_fluxes',[])) for r in results)
    summary['ebe_mismatch_cases']=sum(bool(r['ebe']['mismatches']) for r in results)
    summary['ebe_mismatch_events']=sum(len(r['ebe']['mismatches']) for r in results)
    summary['all_positive_cases_factor_ten']={t:all(r['within'] for r in rows if r['treatment']==t and not r['zero_reference']) for t in ('current','source','policy')}
    summary['excluding_duplicate_holdout']={}
    for treatment in ('current','source','policy'):
        group=[r for r in rows if r['treatment']==treatment and r['soil']!='holdout']
        summary['excluding_duplicate_holdout'][treatment]=dict(cases=len(group),positive=sum(not r['zero_reference'] for r in group),within=sum(r['within'] is True for r in group))
    modern_legacy=[s.comparison(r['modern_legacy_kg_yr'],r['legacy_kg_yr']) for r in rows if r['treatment']=='current']
    summary['modern_legacy_reference']={'positive':sum(not r['zero_reference'] for r in modern_legacy),'within':sum(r['within'] is True for r in modern_legacy)}
    summary['physical_candidate_accepted']=False
    summary['physical_acceptance_reason']='No independent hydrologic/geologic validation; underlying thickness and conductivity uncertain'
    b.dump(root/'analysis-v1/results.json',results)
    b.dump(root/'analysis-v1/comparisons.json',rows)
    b.dump(root/'analysis-v1/summary.json',summary)
    b.dump(root/'analysis-v1/control-reproduction.json',reproduction)
    b.dump(root/'analysis-v1/input-aliases.json',aliases)
    audits=[]
    for result in results:
        audits.append(dict(name=result['name'],**result['case'],report_reconciled=result['sediment']['report_reconciled'],
            report_delta_kg_yr=result['sediment']['report_delta_kg_yr'],report_bound_kg_yr=result['sediment']['report_bound_kg_yr'],
            ebe_mismatches=len(result['ebe']['mismatches']),ebe_max_delta_kg_m=result['ebe']['max_delta_kg_m'],
            negative_sediment_flux_records=len(result['sediment'].get('negative_fluxes',[])),
            wat_dates=result['water']['days'],profile_depth_mm=result['buffer_state']['profile_depth_mm'],
            max_surface_transfer_delta_m3=result['water']['max_surface_transfer_delta_m3'],
            max_lateral_transfer_delta_m3=result['water']['max_lateral_transfer_delta_m3'],
            road_boundary_kg_yr=result['sediment']['ofes'][0]['boundary_kg_yr'],
            fill_boundary_kg_yr=result['sediment']['ofes'][1]['boundary_kg_yr'],
            buffer_net_kg_yr=result['sediment']['ofes'][2]['net_kg_yr'],record_sha256=result['record_sha256']))
    for name,values in (('native-audits',audits),('pair-effects',effects)):
        with (root/'analysis-v1'/f'{name}.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    with (root/'analysis-v1/comparisons.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(summary,indent=2),flush=True)


def main():
    import wepppyo3
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=s.ROOT)
    parser.add_argument('--workers',type=int,default=12);args=parser.parse_args();root=args.root
    dest=root/'analysis-v1';dest.mkdir(exist_ok=False);(dest/'cases').mkdir()
    declaration=json.loads((root/'declaration.json').read_text())
    expected=declaration['cases']
    if len(list((root/'matrix-v1').glob('*/record.json')))!=len(expected):raise ValueError('Incomplete native matrix')
    if len(expected)!=1920 or len({tuple(c.values()) for c in expected})!=1920:raise ValueError('Invalid declared matrix')
    for binary in declaration['binaries'].values():
        if b.digest(binary['path'])!=binary['sha256']:raise ValueError('Binary drift')
    for path,sha in declaration['source_sha256'].items():
        candidate=s.REPO/path if not path.endswith('.md') else root/('frozen-'+Path(path).name)
        if path==str(Path(s.__file__).relative_to(s.REPO)):
            # Executed script is retained; published staging points to the completed plan.
            candidate=root/'executed-study.py'
        if b.digest(candidate)!=sha:raise ValueError('Frozen source/declaration drift')
    paths=[Path(__file__),Path(s.__file__),Path(a.__file__),Path(b.__file__),Path(wepppyo3.__file__)]
    paths+=list(Path(wepppyo3.__file__).parent.glob('*.so'))
    paths += [s.REPO/'wepppy/wepp/interchange'/name for name in ('hill_element_interchange.py','hill_wat_interchange.py','hill_ebe_interchange.py')]
    b.dump(dest/'provenance.json',dict(hashes={str(p):b.digest(p) for p in paths},declaration_sha256=b.digest(root/'declaration.json')))
    shutil.copy2(__file__,dest/'executed-analyze.py')
    refs=references(root);results=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for index,result in enumerate(pool.map(analyze_case,((root,c,dest) for c in expected)),1):
            results.append(result);print(f'{index}/1920 analyzed',flush=True)
    summarize(root,results,refs)


if __name__=='__main__':main()
