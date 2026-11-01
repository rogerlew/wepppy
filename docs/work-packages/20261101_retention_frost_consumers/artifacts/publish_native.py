"""Publish source-free per-process outcomes; never execute a model."""
import csv,datetime,json,shutil
from pathlib import Path
import campaign as c
incident=Path('/workdir/wepp-forest-release-20261009/docs/ablation/20261101_retention_frost_consumers')
s=json.loads((c.HERE/'summary.json').read_text());headers=next(csv.reader((incident/'matrix.csv').open()));rows=[];observations=[]
for r in s['cases']:
 cell=r['cell'];case=c.name(cell);dest=c.RAW/'comparators-v1'/case;process=json.loads((dest/'process-result.json').read_text());candidate=cell[1]=='candidate';entry={k:'' for k in headers}
 entry.update(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),incident_id=incident.name,lane_id=('U1' if candidate else 'L0')+'-KS'+str(cell[2]),case_id=case,host_role='dev',host_name='forest',container_service='none',binary_path=process['command'][0],run_file=str(dest/'runs/p1.run'),mutation_group='retention_input' if candidate else 'baseline',mutation_name='screened_volume_inverse' if candidate else 'current_mass_complement',mutation_value=cell[0],contract_refs='SC-WATBAL-001#INV-WATBAL-001',boundary_disposition='requires_scientific_review',command=process['command'][0]+' < '+str(dest/'runs/p1.run'),pass_fail='PASS' if r['passed'] else 'FAIL',exit_code=r['returncode'],last_simulation_year=16 if r['passed'] else 9,success_marker_found=str(r['completion']).lower(),stderr_tail_path=str(dest/'runs/stderr'),stdout_path=str(dest/'runs/stdout'),repro_input_path=str(dest/'pre-execution.json'),durability_lane='na',configured_simulation_years=16,simulated_years_completed=16 if r['passed'] else 8,notes='Exploratory input/configuration cell; no promotion. '+('Complete ordinary calendar and strict frost-history readback.' if r['passed'] else 'STOP1 year9day355 OFE3hour1; 9830 daily rows only; no full-history admission.'))
 rows.append(entry)
 observations.append(dict(case_id=case,contract_id='SC-WATBAL-001',invariant_id='INV-WATBAL-002',contract_ref='SC-WATBAL-001#INV-WATBAL-002',status='not_observed',observed_value='Executed consumer-domain campaign deferred after comparator failure',disposition='requires_scientific_review',evidence_path='artifacts/logs/summary.json',notes='No dynamic consumer or physical flux closure admission'))
for path,fields,data in [(incident/'matrix.csv',headers,rows),(incident/'artifacts/logs/contract_observations.csv',list(observations[0]),observations)]:
 with path.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(data)
for name in ('summary.json','findings.md','comparator-outcome-science-review.md','comparator-outcome-implementation-review.md','prior-preservation.json'):
 shutil.copy2(c.HERE/name,incident/'artifacts/logs'/name)
(incident/'artifacts/logs/fuzzy_failures.md').write_text('# Failure ledger\n\nNo promotion fuzzy suite was run; no patch or input formula is promoted.\nDeclared moderate-rock candidate KSFLAG1 fails at year9/day355/OFE3/hour1\nwith HOURLY_WATER_UNMET/STOP1. Eleven other cells complete.\nNo new native observer was built or executed.\n')
(incident/'artifacts/README.md').write_text('# Evidence\n\nCompact source-free observations and independent reviews are retained here.\nPrivate full build, inputs and traces are bound by archive-receipt.json.\nNative canonical source and release binaries are unchanged.\n')
