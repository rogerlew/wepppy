"""Validate rebuilt source with unchanged historical packet/peak expectations."""
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys

root=Path('/home/workdir/topanga-seed-recurrence-20261006')
repo=Path('/workdir/wepppy')
art=repo/'docs/work-packages/20260808_peakflow_phase1/artifacts'
out=root/'acceptance'
out.mkdir(exist_ok=False)
identities={}
for kind, binary in [('observer',root/'source/src/wepp_hill'),('replay',root/'peak_replay')]:
    original=json.loads((art/f'{kind}-build-manifest.json').read_text())
    current=dict(original)
    current['executable_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    current['os']=platform.platform()
    # build_id remains the source/protocol label because it participates in the
    # immutable expected packet hashes. Both executable identities are explicit.
    (out/f'{kind}-build-manifest.json').write_text(json.dumps(current,indent=2)+'\n')
    identities[kind]={'historical_hash':original['executable_sha256'],'rebuilt_hash':current['executable_sha256'],'binary':str(binary),'protocol_build_id':current['build_id']}
    shutil.copy2(binary,root/'bundle/bin'/('wepp_hill' if kind=='observer' else 'peak_replay'))
(out/'rebuild-identities.json').write_text(json.dumps(identities,indent=2)+'\n')
cmd=[sys.executable,str(repo/'tools/peakflow_gate21_acceptance.py'),
 '--fixture',str(repo/'docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat'),
 '--fixture-1986',str(repo/'docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer'),
 '--observer-binary',str(root/'bundle/bin/wepp_hill'),'--observer-manifest',str(out/'observer-build-manifest.json'),
 '--replay-binary',str(root/'bundle/bin/peak_replay'),'--replay-manifest',str(out/'replay-build-manifest.json'),
 '--artifacts',str(out)]
with (out/'acceptance.log').open('w') as log:
    result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=300)
print(json.dumps(identities,indent=2))
print('acceptance returncode',result.returncode)
if result.returncode:
    print((out/'acceptance.log').read_text()[-4000:]);sys.exit(result.returncode)
report=json.loads((out/'gate21-acceptance-report.json').read_text())
historical=json.loads((art/'observer-parity-report.json').read_text())
assert report['active_trace_parity']['lanes']==historical['lanes'], 'historical canonical-output parity failed'
print('PASS historical canonical hashes, active/inactive parity, exact packets/replays, 1986 peaks and negative control')
