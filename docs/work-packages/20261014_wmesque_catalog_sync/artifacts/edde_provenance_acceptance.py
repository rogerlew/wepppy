"""Read back additive EDDE normal provenance from real PRISM acquisition."""
import json
import os
from pathlib import Path
import sys

from wepppy.nodb.core import Climate
from wepppy.nodb.core.climate_edde_build import _normals

project = Path(sys.argv[1])
assert project.name.startswith('wmesque-acceptance-')
climate = Climate.getInstance(str(project))
stage = project / 'climate' / 'wmesque-edde-provenance'
stage.mkdir(exist_ok=True)
os.environ['WMESQUE_ENDPOINTS'] = json.dumps([
    'http://wmesque2:8030', 'https://wepp.cloud/webservices/wmesque2'])
locations = {'ws': tuple(climate.watershed_instance.require_centroid())}
normals = _normals(climate, stage, locations)
record = json.loads((stage / 'prism-normals.json').read_text())
assert record['endpoint'] == climate.wmesque_endpoint
for variable in ('ppt', 'tmin', 'tmax'):
    assert len(normals['ws'][variable]) == 12
    assert record['serving_endpoints'][variable] == record['acquisition'][variable]['wmesque_retrieve']['wmesque_endpoint']
    assert record['dataset_revisions'][variable] == record['acquisition'][variable]['wmesque'].get('revision')
evidence = json.loads((project / 'wmesque-acceptance.json').read_text())
evidence['edde_normal_provenance'] = {
    'path': str(stage / 'prism-normals.json'), 'endpoint': record['endpoint'],
    'serving_endpoints': record['serving_endpoints'], 'dataset_revisions': record['dataset_revisions'],
    'sha256': record['sha256'], 'monthly_values_per_variable': 12}
(project / 'wmesque-acceptance.json').write_text(json.dumps(evidence, indent=2))
print(json.dumps(evidence['edde_normal_provenance'], indent=2))
