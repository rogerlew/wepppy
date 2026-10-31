"""Score frozen development panel with existing references and acceptance rules."""
import json,hashlib
from pathlib import Path
import score_screen as screen
import role_boundary_assessment as role
import continuation as c
ROOT=Path('/workdir/wepppy/out/roads-native-funding-20261031/D2-matrix840')
HERE=Path(__file__).resolve().parent

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    source=ROOT/'results.json';records=json.loads(source.read_text());assert len(records)==840
    baseline=json.loads((role.MATRIX/'magnitude-scores.json').read_text())
    old={json.dumps(r['case'],sort_keys=True):r for r in baseline};assert len(old)==840
    rows=[];refs={}
    for r in records:
        case=r['case'];prior=old[json.dumps(case,sort_keys=True)]
        profile='-'.join((case['climate'],role.TEXTURES[case['soil']],case['design'],case['surface'],case['traffic'],'legacy','legacy'))
        folder=role.REFERENCE/profile
        if profile not in refs:
            ref=json.loads((folder/'record.json').read_text());c.e.a.s.check_files(folder,ref);refs[profile]=ref
        ref=refs[profile];reference=ref['metrics']['sediment_export_kg_yr'];assert reference==prior['reference_kg_yr']
        for name in ['p1.cli','p1.man','p1.slp']:assert r['inputs'][name]==ref['inputs'][name]
        generated=ROOT/'matrix-v1'/'-'.join(case.values())
        for name,sha in r['outputs'].items():assert digest(generated/'output'/name)==sha
        complete=r['status']=='completed';value=r['metrics']['sediment_export_kg_yr'] if complete else None
        within=complete and (.1<=value/reference<=10 if reference>1 else value<=max(1,10*reference))
        audit=r.get('audit',{});sed=audit.get('sediment',{})
        rows.append(dict(case=case,status=r['status'],reference_kg_yr=reference,reference_record_sha256=digest(folder/'record.json'),export_kg_yr=value,meaningful=reference>1,within=within,physical_pass=r['physical_pass'],negative_fluxes=sed.get('negative_fluxes',[]),report_reconciled=sed.get('report_reconciled',False),ebe_mismatch_events=len(audit.get('ebe',{}).get('mismatches',[])),previous_within=prior['within']))
    summary=screen.score(rows)
    summary['physical_failures']=[r['case'] for r in rows if not r['physical_pass']]
    summary['physical_gate']=not summary['physical_failures'];summary['screen_gate']=summary['numerical_gate'] and summary['physical_gate']
    summary.update(binary_sha256=records[0]['binary_sha256'],results_sha256=digest(source),recovered=sum(not r['previous_within'] and r['within'] for r in rows),regressed=sum(r['previous_within'] and not r['within'] for r in rows),final_acceptance=False)
    (ROOT/'magnitude-scores.json').write_text(json.dumps(rows,indent=2)+'\n');(ROOT/'magnitude-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (HERE/'native-D2-magnitude-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print({k:summary[k] for k in ['overall','meaningful_load','small_load','physical_gate','numerical_gate','recovered','regressed']})
if __name__=='__main__':main()
