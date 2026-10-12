"""Run inside forest's web container; disposable SA-01 project, no model execution."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import shutil
import hashlib
import builtins
import logging

from wepppy.nodb.core import Wepp, Ron
from wepppy.wepp.soils.utils import WeppSoilUtil

REPO = Path('/workdir/wepppy')
ROOT = Path('/wc1/runs/sa/sa-anisotropy-validation')
EVIDENCE = REPO / 'docs/work-packages/20261012_soil_anisotropy/artifacts'
ROOT.mkdir(parents=True, exist_ok=False)
(ROOT / "disturbed").mkdir()
for source in Path('/wc1/runs/gr/grating-implementation').glob('*.nodb'):
    shutil.copy2(source, ROOT/source.name)
wepp = Wepp.getInstance(str(ROOT))
assert Path(wepp.wd) == ROOT
with wepp.locked():
    wepp._multi_ofe = True
    wepp._run_wepp_ui = True
wepp.parse_inputs({'soil_anisotropy_upper': 25, 'soil_anisotropy_lower': 3})
wepp = Wepp.load_detached(str(ROOT))
assert (wepp.soil_anisotropy_upper, wepp.soil_anisotropy_lower) == (25, 3)
spec = importlib.util.spec_from_file_location('sa_fixtures', REPO/'tests/nodb/test_soil_anisotropy.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
source = fixtures._soil_source(ROOT)
fixtures._mofe_files(ROOT)
runs = ROOT/'wepp/runs'; runs.mkdir(parents=True)
original = hashlib.sha256(source.read_bytes()).hexdigest()
counts = {'source_reads': 0, 'destination_writes': 0}
real_open = builtins.open

def counted_open(file, mode='r', *args, **kwargs):
    if str(file) == str(source) and 'r' in mode:
        counts['source_reads'] += 1
    if str(file) == str(runs/'p1.sol') and 'w' in mode:
        counts['destination_writes'] += 1
    return real_open(file, mode, *args, **kwargs)

context = SimpleNamespace(multi_ofe=wepp.multi_ofe, run_wepp_ui=wepp.run_wepp_ui,
    soil_anisotropy_upper=wepp.soil_anisotropy_upper, soil_anisotropy_lower=wepp.soil_anisotropy_lower,
    wd=str(ROOT), logger=logging.getLogger('sa-validation'), kslast=None, kslast_map=None,
    climate_instance=SimpleNamespace(input_years=1), runs_dir=str(runs),
    watershed_instance=SimpleNamespace(subs_summary={'101': {}}, clip_hillslopes_configured=False,
        clip_hillslope_length=300),
    soils_instance=SimpleNamespace(clip_soils=False, clip_soils_depth=1000,
        clip_soils_minimum=False, clip_soils_minimum_depth=1000, initial_sat=.4))
builtins.open = counted_open
try:
    Wepp._prep_multi_ofe(context, SimpleNamespace(wepp=lambda **kwargs: 1), max_workers=1)
finally:
    builtins.open = real_open
soil = WeppSoilUtil(str(runs/'p1.sol'))
ratios = [[h['anisotropy'] for h in ofe['horizons']] for ofe in soil.obj['ofes']]
assert ratios == [[25, 25, 3], [25, 25, 3]]
assert counts == {'source_reads': 1, 'destination_writes': 1}
assert hashlib.sha256(source.read_bytes()).hexdigest() == original
shutil.copy2(runs/'p1.sol', EVIDENCE/'prepared-p1.sol')
result = {'runid': ROOT.name, 'config': Ron.getInstance(str(ROOT)).config_stem,
    'ratios': ratios, 'io': counts, 'source_sha256': original,
    'prepared_sha256': hashlib.sha256((runs/'p1.sol').read_bytes()).hexdigest(),
    'original_unchanged': True, 'persisted_overrides': [25, 3],
    'scope': 'Real locked Wepp persistence and real preparation/soil/native/file boundaries; bounded synthetic terrain/climate descriptors. No model executed.'}
(EVIDENCE/'forest-validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
