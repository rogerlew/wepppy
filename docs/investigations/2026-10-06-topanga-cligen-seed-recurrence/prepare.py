"""Stage immutable scientific inputs and preregister seed sampling; no model run."""
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys

ROOT = Path('/home/workdir/topanga-seed-recurrence-20261006')
REPO = Path('/workdir/wepppy')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')

bundle = ROOT / 'bundle'
bundle.mkdir(exist_ok=False)
(bundle / 'bin').mkdir()
(bundle / 'tools').mkdir()
(bundle / 'inputs').mkdir()
(bundle / 'climate-source').mkdir()
fixtures = {
    'ksat20': '2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat/baseline-ksat20/runs',
    'ksat35': '2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat/mutant-ksat35/runs',
    'cover90': '2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer/baseline/runs',
    'cover80': '2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer/lower-ground-cover/runs',
    'dense': '2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer/dense-canopy/runs',
}
for lane, relative in fixtures.items():
    shutil.copytree(REPO / 'docs/investigations' / relative, bundle / 'inputs' / lane)
for name in ('ws.prn', 'ca041484.par', 'wepp.cli'):
    shutil.copy2(Path('/wc1/runs/ha/hand-to-mouth-drought/climate') / name, bundle / 'climate-source' / name)
for name in ('peakflow_phase1_replay.py', 'peakflow_phase1_protocol.py', 'peakflow_phase1_fixture.py', 'peakflow_phase1_1986_fixture.py', 'peakflow_phase1_negative_control.py', 'peakflow_gate21_acceptance.py'):
    shutil.copy2(REPO / 'tools' / name, bundle / 'tools' / name)
shutil.copy2(REPO / 'wepppy/wepp/peakflow_census/observer.py', bundle / 'tools/observer.py')
shutil.copy2(REPO / 'wepppy/wepp/peakflow_census/pairing.py', bundle / 'tools/pairing.py')
shutil.copy2(REPO / 'wepppy/climates/cligen/bin/cligen532', bundle / 'bin/cligen532')
pilot = [0, 1, 12345, 54321, 99999]
sample = random.Random(20261006).sample([s for s in range(100000) if s not in pilot], 100)
dump(bundle / 'seeds.json', {'pilot': pilot, 'inference': sample, 'sampler': 'Python random.Random(20261006).sample(range(100000) excluding pilot, 100)', 'repeat_seed': 12345})
dump(bundle / 'input-manifest.json', {str(p.relative_to(bundle)): sha(p) for p in sorted(bundle.rglob('*')) if p.is_file()})
print(json.dumps({'bundle': str(bundle), 'seed_manifest_sha256': sha(bundle/'seeds.json'), 'first_five_inference':sample[:5], 'climate_hashes':{k:sha(bundle/'inputs'/k/'p106.cli') for k in fixtures}},indent=2))
