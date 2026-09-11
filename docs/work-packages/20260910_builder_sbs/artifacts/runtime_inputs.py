"""Generated-input check on the disposable, API-created development Builder run."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

from wepppy.nodb.core import Ron, Landuse, Soils, Watershed, Wepp
from wepppy.nodb.base import TriggerEvents
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.management import get_management_summary
from wepppy.nodb.core.wepp import prep_soil
from wepppy.wepp.soils.utils import WeppSoilUtil

wd = Path('/wc1/runs/se/self-imposed-nave')
assert wd.name == 'self-imposed-nave'  # disposable run created for this check
ron, landuse, soils, watershed, wepp = [cls.getInstance(str(wd)) for cls in (Ron, Landuse, Soils, Watershed, Wepp)]
disturbed = Disturbed.getInstance(str(wd))
assert not disturbed.has_map  # browser has already removed the uploaded fixture
assert all('disturbed' in x.mods for x in (ron, landuse, soils, watershed, wepp, disturbed))
assert landuse.mapping == 'disturbed'
assert len(disturbed.get_disturbed_key_lookup()) >= 9
with watershed.locked():
    watershed._sub_area_lookup = {'101': 10000.0}
with landuse.locked():
    landuse.domlc_d = {'101': '42'}
    landuse.managements = {'42': get_management_summary(42, landuse.mapping)}
landuse.trigger(TriggerEvents.LANDUSE_DOMLC_COMPLETE)
assert landuse.domlc_d == {'101': '42'}
landuse.dump_landuse_parquet()  # Keep the synthetic development fixture migration-complete.
source = Path('/workdir/wepppy/tests/omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.sol')
Path(soils.soils_dir).mkdir(exist_ok=True)
shutil.copyfile(source, Path(soils.soils_dir) / 'base.sol')
with soils.locked():
    soils.domsoil_d = {'101': 'base'}
    soils.soils = {'base': SoilSummary(mukey='base', fname='base.sol', soils_dir=soils.soils_dir,
                                     build_date=str(datetime.now(timezone.utc)), desc='fixture soil', meta_fn=None)}
soils.trigger(TriggerEvents.SOILS_BUILD_COMPLETE)
key = soils.domsoil_d['101']
assert key != 'base', 'Normal unburned Disturbed soil adjustment must be active'
modified = Path(soils.soils_dir) / soils.soils[key].fname
runs = Path(wepp.runs_dir)
runs.mkdir(exist_ok=True)
prepared = runs / 'p1.sol'
prep_soil(('101', str(modified), str(prepared), wepp.kslast, None, soils.initial_sat,
           soils.clip_soils, soils.clip_soils_depth, soils.clip_soils_minimum, soils.clip_soils_minimum_depth))
assert WeppSoilUtil(str(prepared)).clay is not None
print(json.dumps({'runid': wd.name, 'no_sbs_landuse_event': 'passed', 'normal_soil_event': 'passed',
                  'soil_key': key, 'artifacts': {str(p.relative_to(wd)): hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in (modified, prepared)}}, indent=2))
