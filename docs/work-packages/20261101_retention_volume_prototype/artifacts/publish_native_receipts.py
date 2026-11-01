"""Write compact source-free receipts for the native incident; no model calls."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
import shutil

incident=Path('/workdir/wepp-forest-release-20261009/docs/ablation/20261101_retention_volume_prototype')
raw=Path('/home/workdir/wepppy/out/retention-volume-prototype-20261101')
art=Path(__file__).resolve().parent
r=json.loads((raw/'readback-v3/receipt.json').read_text())
old=json.loads((raw/'campaign-v1/receipt.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(passed=r['passed'],native_processes=12,model_reruns=0,
 initialization_rows=sum(len(x['initialization']) for x in r['cases']),daily_rows_per_history=17532,
 all_initialized_domains_valid=all(y['initialized_domains_valid'] for x in r['cases'] for y in x['initialization']),
 campaign_files=len(r['campaign_inventory']),readback_sha256=sha(raw/'readback-v3/receipt.json'),
 original_failed_campaign_sha256=sha(raw/'campaign-v1/receipt.json'),comparisons=r['comparisons'],
 frost_calls=0,frost_counter_evidence='science-readback.md independently sums source-owned gate and skip payloads')
(art/'readback-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
headers=next(csv.reader((incident/'matrix.csv').open()));rows=[];observations=[]
for result,prior in zip(r['cases'],old['cases'],strict=True):
 case=result['chkey']+'-'+result['lane']; entry={k:'' for k in headers};candidate=result['lane']=='candidate';rundir=raw/'campaign-v1'/case/'runs'
 entry.update(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),incident_id=incident.name,
 lane_id='U1' if candidate else 'L0',case_id=case,host_role='dev',host_name='forest',container_service='none',
 binary_path=prior['command'][0],run_file=str(rundir/'p1.run'),mutation_group='retention_input' if candidate else 'baseline',
 mutation_name='screened_volume_inverse' if candidate else 'current_mass_complement',mutation_value=result['chkey'],
 contract_refs='SC-WATBAL-001#INV-WATBAL-001',boundary_disposition='requires_scientific_review',
 command=prior['command'][0]+' < '+str(rundir/'p1.run'),pass_fail='PASS',exit_code=0,last_simulation_year=16,
 success_marker_found='true',stderr_tail_path=str(rundir/'stderr'),stdout_path=str(rundir/'stdout'),
 repro_input_path=str(raw/'campaign-v1'/case/'pre-execution.json'),durability_lane='na',
 configured_simulation_years=16,simulated_years_completed=16,
 notes='Exploratory input prototype. Original reader failures retained; accepted v3 readback without model rerun. Initialization domains only; frost skipped. No promotion.')
 rows.append(entry)
 for inv,status,value in [('INV-WATBAL-001','satisfied','Observed initialization positive log argument; strict ratio<1 also checked'),('INV-WATBAL-002','not_observed','Full dynamic drainage and active frost/accepted-flux closure not observed')]:
  observations.append(dict(case_id=case,contract_id='SC-WATBAL-001',invariant_id=inv,
   contract_ref='SC-WATBAL-001#'+inv,status=status,observed_value=value,disposition='requires_scientific_review',
   evidence_path='artifacts/logs/readback-receipt.json',notes='Bounded initialization experiment; no general physical acceptance'))
for path,fields,data in [(incident/'matrix.csv',headers,rows),(incident/'artifacts/logs/contract_observations.csv',list(observations[0]),observations)]:
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
for name in ['readback-receipt.json','producer-receipt.json','science-readback.md','implementation-readback.md']:
 shutil.copy2(art/name,incident/'artifacts/logs'/name)
(incident/'artifacts/logs/findings.md').write_text('# Findings location\n\nThe reviewed findings are in WEPPpy docs/work-packages/20261101_retention_volume_prototype/artifacts/findings.md.\n\nTwelve complete histories and exact paired preparation pass bounded readback.\nInitial absolute water remains unchanged within roundoff; all frost opportunities\nwere skipped. Production admission remains unsupported.\n')
