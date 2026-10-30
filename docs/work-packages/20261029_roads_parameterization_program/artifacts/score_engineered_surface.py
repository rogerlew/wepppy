"""Use unchanged gates for the engineered surface panel."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('screen_scoring', HERE/'score_screen.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
s.ROOT = s.ROOT.parent/'engineered-surface-screen-v1'


def main():
    declaration = json.loads((s.ROOT/'declaration.json').read_text())
    ui_root = s.ROOT.parent/'surface-screen-v4'
    ui = {'-'.join(r['case'].values()):r for r in json.loads((ui_root/'results.json').read_text())}
    rows = json.loads((s.ROOT/'results.json').read_text())
    expected=[]
    source=json.loads((s.ROOT.parent/'project-runtime-screen-v2/results.json').read_text())
    cases={'-'.join(r['case'].values()):r['case'] for r in source}
    for profile,target in declaration['tasks']:
        case=cases[profile].copy();case['variant']+='_'+target;expected.append(case)
    for row in rows:
        case=row['case'];prior_case=case.copy();prior_case['runtime']='ui-only';prior_case['variant']='erosion'
        old=ui['-'.join(prior_case.values())]
        profile='-'.join(case[k] for k in ('climate','soil','design','surface','traffic'))
        ref_file=Path('/wc1/runs/ro/roads-soil-benchmark-20261029/validation-v4')/f'{profile}-legacy-legacy'/'record.json'
        ref=json.loads(ref_file.read_text())['metrics']['sediment_export_kg_yr']
        if old['status']=='completed' and s.digest(ref_file)!=old['reference_record_sha256']:
            raise ValueError('Reference drift')
        row.update(reference_kg_yr=ref, meaningful=ref>1, reference_record_sha256=s.digest(ref_file))
        if row['status']=='completed':
            value=row['export_kg_yr']
            row['within']=.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref)
            row['record_sha256']=s.digest(s.ROOT/'matrix-v1'/'-'.join(case.values())/'record.json')
        else:
            row.update(within=False, negative_fluxes=[], report_reconciled=False, ebe_mismatch_events=None)
    s.verify(rows,dict(cases=expected))
    summary={v:s.score([r for r in rows if r['case']['variant']==v]) for v in sorted({r['case']['variant'] for r in rows})}
    output=dict(root=str(s.ROOT),declaration_sha256=s.digest(s.ROOT/'declaration.json'),
                results_sha256=s.digest(s.ROOT/'results.json'),variants=summary)
    (HERE/'engineered-surface-score.json').write_text(json.dumps(output,indent=2)+'\n')
    for v,r in summary.items():
        print(v,r['overall'],'native',len(r['native_failures']),'physical',len(r['physical_failures']),'screen_gate',r['screen_gate'])


if __name__=='__main__':main()
