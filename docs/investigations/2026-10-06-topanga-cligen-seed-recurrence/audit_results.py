"""Post-run artifact readback, independent screen arithmetic and storage index."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from study import ROOT, LANES, FOCAL, PAIRS, cli_rows, sha, dump

seeds=json.loads((ROOT/'seeds.json').read_text())['inference']
labels=[f'inference-{s:05}' for s in seeds]
assert len(set(seeds))==100
assert not list((ROOT/'runs').glob('inference-*/failed.json'))
all_pairs=pd.read_parquet(ROOT/'analysis/event-pairs.parquet')
focal=pd.read_csv(ROOT/'analysis/focal-probabilities.csv')
any_event=pd.read_csv(ROOT/'analysis/any-event-probabilities.csv')
semantic=set();verified=0;warnings={};raw_tables=[]
_,_,original=cli_rows(ROOT/'inputs/ksat20/p106.cli')
fixed=[0,1,2,3,7,8,9,10,11,12]
for label in labels:
    root=ROOT/'runs'/label
    terminal=json.loads((root/'terminal.json').read_text())
    assert terminal['status']=='complete'
    _,_,climate=cli_rows(root/'climate/p106.cli')
    assert np.array_equal(climate[:,fixed],original[:,fixed])
    semantic.add(hashlib.sha256(climate[:,4:7].tobytes()).hexdigest())
    for warning in terminal['climate']['quality_errors_replaced_variables']:
        warnings[warning]=warnings.get(warning,0)+1
    for lane in LANES:
        record=terminal['lanes'][lane]
        assert sha(root/lane/'runs/p106.cli')==terminal['climate']['climate_sha256']
        for name,expected in record['inputs'].items():assert sha(root/lane/'runs'/name)==expected
        for rel,expected in [('runs/peak_diag.csv',record['trace_sha256']),*[(f'output/{name}',value) for name,value in record['outputs'].items()]]:
            digest=hashlib.sha256()
            with gzip.open(root/lane/(rel+'.gz'),'rb') as source:
                for block in iter(lambda:source.read(1048576),b''):digest.update(block)
            assert digest.hexdigest()==expected,(label,lane,rel)
            verified+=1
    table=pd.read_parquet(root/'pairs.parquet')
    both=table.baseline_event_present & table.mutant_event_present
    dp=(table.peak_m_s_mutant-table.peak_m_s_baseline).abs()
    dq=(table.runoff_post_m_mutant-table.runoff_post_m_baseline).abs()
    strict=both & (dp>1e-7) & (dp/table.peak_m_s_baseline.abs().clip(lower=1e-7)>0.25) & (dq/table.runoff_post_m_baseline.abs().clip(lower=1e-5)<0.05)
    assert np.array_equal(strict,table.peak_gt25pct_runoff_lt5pct)
    raw_tables.append(table)
raw=pd.concat(raw_tables,ignore_index=True)
assert len(raw)==len(all_pairs)
for pair in PAIRS:
    table=raw[raw.pair==pair]
    for day in FOCAL:
        k=table[(table.date==day)&table.peak_gt25pct_runoff_lt5pct].seed_label.nunique()
        row=focal[(focal.pair==pair)&(focal.date==day)&(focal.flag=='peak_gt25pct_runoff_lt5pct')].iloc[0]
        assert int(row.k)==k and int(row.n)==100
    k=table[table.peak_gt25pct_runoff_lt5pct].seed_label.nunique()
    row=any_event[(any_event.pair==pair)&(any_event.flag=='peak_gt25pct_runoff_lt5pct')].iloc[0]
    assert int(row.k)==k
assert len(semantic)==100
manual=pd.read_csv(ROOT/'analysis/manual-review.csv')
branch=pd.read_csv(ROOT/'analysis/manual-branch-replay.csv')
assert len(branch)==len(manual) and (branch.branch_replay_status=='pass').all()
assert (branch.selected_method_delta_m_s<=5e-11).all()
result={'schema_version':1,'status':'pass','completed_inference_seeds':100,'failed_inference_seeds':0,
        'independent_screen_counts_match':True,'fixed_daily_fields_exact':True,
        'distinct_semantic_storm_series':len(semantic),'lossless_raw_files_verified':verified,
        'event_pair_rows':len(raw),'quality_warning_occurrences_by_variable':warnings,
        'manual_replay_states':manual.replay_status.value_counts().to_dict(),
        'supplemental_branch_replay_states':branch.branch_replay_status.value_counts().to_dict(),
        'max_branch_replay_delta_m_s':float(branch.selected_method_delta_m_s.max())}
dump(ROOT/'analysis/artifact-validation.json',result)
entries=[]
for path in sorted(ROOT.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts and path.name!='storage-manifest.json':
        entries.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path)})
dump(ROOT/'analysis/storage-manifest.json',{'schema_version':1,'root':str(ROOT),'files':entries,
       'scope':'Internal raw evidence; public summary does not include restricted executable/source',
       'file_count':len(entries),'total_bytes':sum(e['bytes'] for e in entries)})
print(json.dumps(result,indent=2))
