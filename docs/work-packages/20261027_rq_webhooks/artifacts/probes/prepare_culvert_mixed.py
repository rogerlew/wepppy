"""Prepare an explicit offline test input: one valid point and 35 invalid points."""
import json
from pathlib import Path
import shutil
import zipfile
from wepppy.nodb.core import Climate
from wepppy.nodb.core.climate import ClimateMode, ClimateStationMode
from wepppy.rq.project_rq_fork import _rebase_fork_nodb_text

base = Path('/acceptance/runs/culvert-offline-base')
source = Path('/wc1/batch/culvert_base/_base')
shutil.copytree(source, base, symlinks=False)
for path in base.rglob('*.nodb'):
    path.write_text(_rebase_fork_nodb_text(path.read_text(), source_wd=str(source),
        destination_wd=str(base), source_runid='batch;;culvert_base;;_base',
        destination_runid='profile;;tmp;;culvert-offline-base'))
# A reusable batch template must not copy a live project's coordination receipts.
shutil.rmtree(base / '_query_engine', ignore_errors=True)
climate = Climate.getInstance(str(base))
climate.climate_mode = ClimateMode.Vanilla
climate.climatestation_mode = ClimateStationMode.Closest
climate.input_years = 2
climate.catalog_id = None
climate.use_gridmet_wind_when_applicable = False
climate.adjust_mx_pt5 = False
with zipfile.ZipFile('/acceptance/culvert-domain-failure.zip') as cached, zipfile.ZipFile('/acceptance/culvert-payload.zip') as original, zipfile.ZipFile('/acceptance/culvert-mixed.zip', 'w', zipfile.ZIP_DEFLATED) as target:
    for name in cached.namelist():
        data = cached.read(name)
        if name == 'culverts/culvert_points.geojson':
            points = json.loads(original.read(name))
            for point in points['features'][1:]:
                point['geometry']['coordinates'][0] += 1000000
            data = json.dumps(points).encode()
        if name == 'model-parameters.json':
            params = json.loads(data)
            params['base_project_runid'] = 'profile;;tmp;;culvert-offline-base'
            data = json.dumps(params).encode()
        target.writestr(name, data)
print('Prepared mixed-domain fixture with explicit local stochastic climate inputs.')
