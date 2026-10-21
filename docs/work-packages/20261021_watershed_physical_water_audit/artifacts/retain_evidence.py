"""Retain compact receipts and hash external replay evidence without copying decks."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
ART=Path('/workdir/wepppy/docs/work-packages/20261021_watershed_physical_water_audit/artifacts')
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
receipts=['release-matrix/execution.json','release-matrix/audit.json','networks/execution.json',
'observer-v2/parity.json','observer-v2/audit.json','network-observer/parity.json','network-observer/audit.json',
'side-observer/parity.json','side-observer/audit.json','hourly-observer/parity.json','hourly-observer/audit.json',
'initial-groundwater/audit.json','flat-hydrograph-system/audit.json','diagnostic-controls.json']
for name in receipts:shutil.copy2(ROOT/name,ART/name.replace('/','-'))
paths=[]
for p in ROOT.rglob('*'):
    if p.is_file() and ('source' not in str(p.relative_to(ROOT))) and (p.suffix in ['.json','.csv'] or p.name.startswith('water_audit_')):
        paths.append(dict(path=str(p),bytes=p.stat().st_size,sha256=digest(p)))
(ART/'retained-evidence.json').write_text(json.dumps(dict(root=str(ROOT),files=paths),indent=2)+'\n')
bins=[Path('/workdir/wepppy/wepp_runner/bin')/n for n in ['wepp_261021','wepp_261021_hill']]
(ART/'release-provenance.json').write_text(json.dumps(dict(source_commit='a87925df9ffe6ebb928e126395dd159d484285fa',artifact_commit='6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb',binaries={str(p):digest(p) for p in bins},source_inputs='/wc1/runs/wb/wb34-impoundment-cohort/wepp/runs',private_inputs='Supplementary scientific investigation inputs; not a new mandatory release gate. Original Ayush input decks unavailable.'),indent=2)+'\n')
print(len(paths),'retained files')
