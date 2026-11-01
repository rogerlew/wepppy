"""Read-only correction for retained whole-hillslope legacy context; no model run."""
import json,runpy,sys
from pathlib import Path
from read_flux_v5 import read,sha
from run_flux_v2 import RAW,OLD,OLDPUB,TARGETS,verify,save,inv

def main():
 f=json.loads((RAW/'freeze.json').read_text());verify(f['files'])
 root=RAW/'campaign-v2';before=inv(root);dest=RAW/'readback-v2';dest.mkdir()
 inputs={str(Path(__file__).resolve()):sha(Path(__file__))}
 for n in ['read_flux_v5.py','check_flux_reader_v7.py']:
  p=Path(__file__).with_name(n);inputs[str(p.resolve())]=sha(p)
 inputs[str(RAW/'reader-controls-v7/receipt.json')]=sha(RAW/'reader-controls-v7/receipt.json')
 save(dest/'declaration.json',dict(files=inputs,original_campaign_inventory=before,scope='No native execution; strict legacy-global context exception only'))
 sys.path.insert(0,str(OLDPUB));validate=runpy.run_path(str(OLDPUB/'run_history_campaign.py'))['output_check'];rows=[]
 for s,(year,day) in TARGETS.items():
  source=root/s;out=dest/s;out.mkdir();r=json.loads((source/'readback.json').read_text())
  if r['returncode']!=0 or 'WEPP COMPLETED' not in (source/'runs/execution.stdout').read_text():raise ValueError('Incomplete native history')
  values=validate(source);c=f['comparators'][s]
  if values['output_hashes']!=c['output_hashes'] or sha(source/'runs/frwatc-history.txt')!=c['trace_sha256']:raise ValueError('Parity')
  verify({str(source/'runs'/n):h for n,h in f['inputs'][s].items()})
  obs=read(source/'runs/buffer-observation.txt',year,day,OLD/s/'runs/buffer-observation.txt');save(out/'observations.json',obs)
  summary=dict(passed=True,scenario=s,original_readback_passed=r['passed'],original_readback_sha256=sha(source/'readback.json'),original_error=r.get('error'),output_hashes=values['output_hashes'],daily_keys=values['daily_keys'],trace_sha256=c['trace_sha256'],observations_sha256=sha(out/'observations.json'),hourly_groups=obs['hourly_groups'],daily_groups=obs['daily_groups'],outside_allowance=obs['outside_allowance'],flagged_hours=obs['flagged_hours'],flagged_days=obs['flagged_days'],legacy_filtered_sha256=obs['legacy_filtered_sha256'])
  save(out/'readback.json',summary);rows.append(summary)
 if inv(root)!=before:raise ValueError('Native evidence mutated')
 verify(inputs);verify(f['files'])
 save(dest/'receipt.json',dict(passed=True,cases=rows,original_campaign_unchanged=True,original_dependencies_unchanged=True,reader_files=inputs))
if __name__=='__main__':main()
