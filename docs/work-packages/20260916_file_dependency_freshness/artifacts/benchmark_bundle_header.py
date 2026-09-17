"""Read-only representative bundle header benchmark, canonical container."""
import json
from pathlib import Path
from time import perf_counter
from wepppy.weppcloud.utils.assets import resolve_controllers_gl_build_id

path = Path('/workdir/wepppy/wepppy/weppcloud/static/js/controllers-gl.js')
started = perf_counter()
for _ in range(1000):
    observed = resolve_controllers_gl_build_id(path)
elapsed = perf_counter() - started
print(json.dumps({'path': str(path), 'bytes': path.stat().st_size,
                  'lookups': 1000, 'mean_seconds': elapsed / 1000,
                  'build_id': observed}, indent=2))
assert observed and elapsed / 1000 < .001
