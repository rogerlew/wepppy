"""Audit mode activation and report matched runtime/drainage contrasts."""
from __future__ import annotations
import argparse
import csv
import importlib.util
import json
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime_analysis_common',HERE/'analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
s=a.s;b=s.b
ROOT=s.ROOT/'runtime-bridge-v1'


def analyze_case(task):
    return a.analyze_case(task)


def collect():
    root=ROOT;dest=root/'analysis-v3';(dest/'cases').mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,dest/'executed-analyze-runtime.py')
    shutil.copy2(a.__file__,dest/'executed-analyze.py')
    b.dump(dest/'collection-source-hashes.json',{str(p):b.digest(p) for p in (Path(__file__),Path(a.__file__))})
    declaration=json.loads((root/'declaration.json').read_text());expected=declaration['cases']
    if len(expected)!=192 or len(list((root/'matrix-v1').glob('*/record.json')))!=192:raise ValueError('Incomplete bridge')
    for path,sha in declaration['runtime_source_sha256'].items():
        if b.digest(s.REPO/path)!=sha:raise ValueError('Runtime source drift')
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for index,result in enumerate(pool.map(analyze_case,((root,c,dest) for c in expected)),1):
            results.append(result);print(f'{index}/192 runtime cases analyzed',flush=True)
    b.dump(dest/'results.json',results)


def summarize():
    root=ROOT;dest=root/'analysis-v3'
    declaration=json.loads((root/'declaration.json').read_text())
    for path,sha in json.loads((dest/'collection-source-hashes.json').read_text()).items():
        frozen={'analyze_runtime.py':'executed-analyze-runtime.py','analyze.py':'executed-analyze.py'}[Path(path).name]
        if b.digest(dest/frozen)!=sha:raise ValueError('Retained collection source changed')
    results=json.loads((dest/'results.json').read_text())
    rows=[];pairs=defaultdict(dict);alias_rows=[]
    main_results={r['name']:r for r in json.loads((s.ROOT/'analysis-v1/results.json').read_text())}
    by_signature=defaultdict(list)
    for candidate in main_results.values():by_signature[candidate['input_signature']].append(candidate)
    references=json.loads((s.ROOT/'analysis-v1/reference-provenance.json').read_text())
    for result in results:
        c=result['case'];case={k:v for k,v in c.items() if k!='runtime'};base_name='-'.join(case.values())
        folder=root/'matrix-v1'/result['name'];record=json.loads((folder/'record.json').read_text())
        base_folder=s.ROOT/'matrix-v1'/base_name;base=json.loads((base_folder/'record.json').read_text())
        s.check_files(folder,record);s.check_files(base_folder,base)
        if base['soil_readback']!=record['soil_readback']:raise ValueError('Runtime altered soil input')
        for key,sha in base['inputs'].items():
            if record['inputs'][key]!=sha:raise ValueError('Runtime altered common input')
        extras=set(record['inputs'])-set(base['inputs'])
        expected_extras={'wepp_ui.txt'} if c['runtime']=='ui-only' else set(declaration['runtime_shared_sha256'])
        if extras!=expected_extras:raise ValueError('Unexpected runtime inputs')
        if (base_folder/'runs/wepp_ui.txt').exists():raise ValueError('Baseline mode drift')
        if 'WEPP hourly water seepage update set (UI code)' in (base_folder/'runs/stdout').read_text():raise ValueError('Baseline mode banner unexpected')
        if 'WEPP hourly water seepage update set (UI code)' not in (folder/'runs/stdout').read_text():raise ValueError('UI mode not activated')
        for key in expected_extras:
            if record['inputs'][key]!=declaration['runtime_shared_sha256'][key]:raise ValueError('Shared runtime bytes differ')
        reference=s.b.DEFAULT_ROOT/'validation-v4'/('-'.join((c['climate'],s.TEXTURES[c['soil']],c['design'],c['surface'],c['traffic'],'legacy','legacy')))
        legacy=json.loads((reference/'record.json').read_text());s.check_files(reference,legacy)
        ref=b.parse_loss(reference/'output/H1.loss.dat',record['width_m'])['sediment_export_kg_yr']
        value=result['metrics']['sediment_export_kg_yr'];old=main_results[base_name]
        profile='-'.join(case[k] for k in ('climate','soil','design','surface','traffic'))
        pairs[(profile,c['runtime'])][c['drainage']]=result
        for candidate in by_signature[old['input_signature']]:
            alias=candidate['case'];alias_profile='-'.join(alias[k] for k in ('climate','soil','design','surface','traffic'))
            reference_name='-'.join((alias['climate'],s.TEXTURES[alias['soil']],alias['design'],alias['surface'],alias['traffic'],'legacy','legacy'))
            ref_value=references[reference_name]['metrics']['sediment_export_kg_yr']
            alias_rows.append(dict(native_case=result['name'],alias_profile=alias_profile,runtime=c['runtime'],**alias,
                export_kg_yr=value,legacy_kg_yr=ref_value,**s.comparison(value,ref_value),
                common_input_signature=old['input_signature'],additional_native_run=False))
        rows.append(dict(name=result['name'],profile=profile,**c,legacy_kg_yr=ref,export_kg_yr=value,
            baseline_no_ui_kg_yr=old['metrics']['sediment_export_kg_yr'],**s.comparison(value,ref),
            runoff_mm_yr=result['metrics']['runoff_mm_yr'],baseline_no_ui_runoff_mm_yr=old['metrics']['runoff_mm_yr'],
            buffer_dp_m3_yr=result['water']['ofes'][2]['deep_percolation_m3_yr'],
            buffer_surface_out_m3_yr=result['water']['ofes'][2]['surface_out_m3_yr'],
            buffer_lateral_out_m3_yr=result['water']['ofes'][2]['lateral_out_m3_yr'],
            near_capacity_days=result['buffer_state']['near_capacity_days'],
            report_reconciled=result['sediment']['report_reconciled'],report_delta_kg_yr=result['sediment']['report_delta_kg_yr'],
            report_bound_kg_yr=result['sediment']['report_bound_kg_yr'],ebe_mismatches=len(result['ebe']['mismatches']),
            late_export_kg_yr=result['late_report_export_kg_yr'],record_sha256=result['record_sha256']))
    effects=[]
    for (profile,runtime),pair in pairs.items():
        if set(pair)!={'current','source'}:raise ValueError('Incomplete runtime pair')
        current,source=pair['current'],pair['source']
        value=current['metrics']['sediment_export_kg_yr'];changed=source['metrics']['sediment_export_kg_yr']
        effects.append(dict(profile=profile,runtime=runtime,current_kg_yr=value,source_kg_yr=changed,
            source_over_current=None if value==0 else changed/value,
            buffer_dp_delta_m3_yr=source['water']['ofes'][2]['deep_percolation_m3_yr']-current['water']['ofes'][2]['deep_percolation_m3_yr']))
    summary={}
    for runtime in ('ui-only','site-shared'):
        for treatment in ('current','source','policy'):
            subset=[r for r in rows if r['runtime']==runtime and r['drainage']==(s.policy(r['soil']) if treatment=='policy' else treatment)]
            summary[runtime+':'+treatment]=dict(cases=len(subset),positive=sum(not r['zero_reference'] for r in subset),
                within=sum(r['within'] is True for r in subset),zeros=sum(r['zero_reference'] for r in subset),
                above=sum(r['ratio'] is not None and r['ratio']>10 for r in subset),below=sum(r['ratio'] is not None and r['ratio']<.1 for r in subset),
                report_reconciled=sum(r['report_reconciled'] for r in subset),ebe_mismatch_cases=sum(r['ebe_mismatches']>0 for r in subset),
                ebe_mismatch_events=sum(r['ebe_mismatches'] for r in subset))
    for name,values in (('comparisons',rows),('pair-effects',effects),('exact-input-alias-comparisons',alias_rows)):
        b.dump(dest/f'{name}.json',values)
        with (dest/f'{name}.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    b.dump(dest/'results.json',results);b.dump(dest/'summary.json',summary)
    paths=[Path(__file__),Path(a.__file__),HERE/'runtime_bridge.py']
    b.dump(dest/'provenance.json',dict(hashes={str(p):b.digest(p) for p in paths},declaration_sha256=b.digest(root/'declaration.json'),
        native_reader_provenance_sha256=b.digest(s.ROOT/'analysis-v1/provenance.json'),
        collection_source_hashes=json.loads((dest/'collection-source-hashes.json').read_text())))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('collect','summarize','all'),default='all',nargs='?')
    args=parser.parse_args()
    if args.phase in ('collect','all'):collect()
    if args.phase in ('summarize','all'):summarize()
