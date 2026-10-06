"""Retain rejected climate attempts and rerun their unchanged sampled seeds."""
from datetime import datetime, timezone
import json
import shutil
from study import ROOT, sha, dump, one_seed

seeds=json.loads((ROOT/'seeds.json').read_text())['inference']
failed=sorted((ROOT/'runs').glob('inference-*/failed.json'))
assert {int(p.parent.name.split('-')[1]) for p in failed}=={46045,53846}
assert len(list((ROOT/'runs').glob('inference-*/terminal.json')))==98
assert not (ROOT/'inference-complete.json').exists()
shutil.copy2(ROOT/'bundle-manifest.json',ROOT/'bundle-manifest-v3.json')
manifest=json.loads((ROOT/'bundle-manifest.json').read_text())
for relative in manifest:manifest[relative]=sha(ROOT/relative)
dump(ROOT/'bundle-manifest.json',manifest)
attempts=ROOT/'attempts/inference-daily-quality-names';attempts.mkdir()
results=[]
for failed_path in failed:
    failure=json.loads(failed_path.read_text())
    assert failure['error']=="AssertionError('quality warning in non-replaced variable')"
    old=failed_path.parent;raw_hash=sha(old/'climate/raw.cli')
    assert not list(old.glob('*/terminal.json'))
    old.rename(attempts/old.name)
    result=one_seed(failure['label'],failure['seed'])
    assert result['climate']['raw_sha256']==raw_hash,'same seed changed raw climate'
    results.append({'label':failure['label'],'raw_climate_identical_to_rejected_attempt':True})
assert len(list((ROOT/'runs').glob('inference-*/terminal.json')))==100
assert not list((ROOT/'runs').glob('inference-*/failed.json'))
dump(ROOT/'inference-retry-report.json',{'status':'pass','policy':'allow only named fixed daily fields; exact daily parity required','retained_attempts':str(attempts),'reruns':results})
dump(ROOT/'inference-complete.json',{'status':'complete','conditions':100,'labels':[f'inference-{s:05}' for s in seeds],
     'finished_at':datetime.now(timezone.utc).isoformat(),'initial_rejections':2,'rerun_unchanged_seeds':results})
