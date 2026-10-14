"""Paired warm native-writer timings; baseline must be the retained old library."""
import importlib.util
import json
from pathlib import Path
import statistics
import tempfile
import time

from wepppy.climates.edde.client import sha256, write_json
import wepppyo3.climate.cli_revision_rust as patched

HERE = Path(__file__).resolve().parent
state = json.loads((HERE / 'writer-validation.json').read_text())
old_path = Path('/workdir/wepppyo3/target/prism-baseline/cli_revision_rust.so')
assert sha256(old_path) == state['baseline_binary_sha256']
spec = importlib.util.spec_from_file_location('baseline.cli_revision_rust', old_path)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
case = state['patched_cases'][0]
source = Path(state['root']) / 'workflows-full' / case['model'] / case['scenario'] / 'apostolic-saw/climate/wepp.cli'
reference, target = case['edde']['reference'], case['edde']['target']
root = Path(tempfile.mkdtemp(prefix='prism-timing-'))
timings = {'baseline': [], 'patched': []}
for i in range(31):
    order = [('baseline', baseline), ('patched', patched)]
    if i % 2: order.reverse()
    for label, module in order:
        started = time.perf_counter()
        module.cli_revision(str(source), str(root / (label + '.cli')),
                                 reference['ppt'], reference['tmax'], reference['tmin'],
                                 target['ppt'], target['tmax'], target['tmin'])
        elapsed = time.perf_counter() - started
        if i: timings[label].append(elapsed)
write_json(HERE/'native-timing.json', dict(
    source=str(source), source_sha256=sha256(source), repetitions=30, warmup_pairs=1,
    order='alternating baseline/patched; same process, same input, separate destinations',
    baseline_sha256=sha256(old_path), patched_sha256=sha256(Path(patched.__file__)),
    timings=timings, medians={key: statistics.median(values) for key, values in timings.items()}))
