"""Rebuild the reported hillslopes through the real batch and downstream writer."""
import csv
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, '/workdir/wepppy')
from wepppy.eu.soils import soil_build
from wepppy.eu.soils.esdac import load_soil_quality_report, validate_disturbed_soil_artifact
from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture
package = Path('/workdir/wepppy/docs/work-packages/20261106_esdac_missing_data')
source = json.loads((package/'artifacts/incident_soil_quality.json').read_text())
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
source_paths = [Path('/workdir/wepppy/wepppy/eu/soils')/name for name in
    ('esdac/esdac.py','esdac/quality.py','soil_build.py')]
source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
soil_build.NCPU = 4
orders = [(p['topaz_id'], (p['longitude'], p['latitude'])) for p in source['profiles']]
soils, dominant = soil_build.build_esdac_soils(orders, str(output))
quality = load_soil_quality_report(output/'soil_quality.json')
lookup = Path('/workdir/wepppy/wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv')
with lookup.open() as stream:
    rows = list(csv.DictReader(stream))
results = []
for topaz_id, key in dominant.items():
    base = WeppSoilUtil(str(output/f'{key}.sol'))
    texture = simple_texture(clay=base.clay, sand=base.sand)
    landuse = 'forest low sev fire'
    replacements = next(dict(r) for r in rows if r['stext']==texture and r['luse']==landuse)
    replacements.update(luse=landuse, stext=texture)
    path = output/f'{topaz_id}-disturbed.sol'
    base.to_over9000(replacements, version=9002).write(str(path))
    q = quality[str(topaz_id)]
    result = validate_disturbed_soil_artifact(path, context=q.context,
        expected_datver=9002, expected_luse=landuse, expected_stext=texture, base_quality=q)
    assert result.accepted, result.as_dict()
    results.append(dict(topaz_id=topaz_id, key=key, outcome=result.outcome,
        horizons=WeppSoilUtil(str(path)).obj['ofes'][0]['horizons'],
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(output/'downstream_readback.json').write_text(json.dumps(results,indent=2)+'\n')
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.sol')}
assert soil_build.build_esdac_soils(orders, str(output))[1] == dominant
assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.sol')}
assert source_hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
receipt = dict(accepted=len(dominant),unique_soils=len(soils),downstream=len(results),
    retry_bytes_preserved=True, candidate_sha256=source_hashes, artifact_sha256=before)
(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
