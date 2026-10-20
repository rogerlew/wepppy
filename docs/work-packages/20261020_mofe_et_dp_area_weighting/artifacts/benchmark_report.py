"""Explicit candidate-binary benchmark on an isolated representative project."""
import importlib.util
import json
from pathlib import Path
import statistics
import time
from wepppy.wepp.reports import hillslope_watbal as module
binary='/workdir/wepppyo3/target/release/libwepp_interchange_rust.so'
spec=importlib.util.spec_from_file_location('wepp_interchange_rust',binary)
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
module.require_wepppyo3_interchange=lambda *args:native
root=Path('/wc1/runs/mo/mofe-et-dp-benchmark-20261020')
# Warm imports/translator separately; do not call this cold-storage timing.
from wepppy.nodb.core import Watershed
Watershed.getInstance(str(root)).translator_factory()
t=time.perf_counter();report=module.HillslopeWatbalReport(root);first=time.perf_counter()-t
settled=[]
for _ in range(5):
 t=time.perf_counter();report=module.HillslopeWatbalReport(root);settled.append(time.perf_counter()-t)
print(json.dumps({'source_bytes':(root/'wepp/output/interchange/H.wat.parquet').stat().st_size,
 'explicit_binary':binary,'first_seconds':first,'settled_seconds':settled,
 'settled_mean_ms':statistics.mean(settled)*1000,'status':report.cache_status}))
