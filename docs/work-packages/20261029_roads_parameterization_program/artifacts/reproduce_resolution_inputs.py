"""Read-only reproduction of Roads attribute provenance and finite-input findings."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from wepppy.nodb.mods.roads.roads import Roads

controller = object.__new__(Roads)
source = Path(sys.modules[Roads.__module__].__file__)
rows = []
cases = {
    'invalid_fallback': {'WIDTH_M': 999, 'SOIL_TEXTURE': 'peat', 'RFG_PCT': 'bad'},
    'valid_alias_zero': {'WIDTH_M': 6, 'SOIL_TEXTURE': 'sandy loam', 'RFG_PCT': 0},
    'finite_clipping': {'RFG_PCT': 120, 'FILL_LENGTH_M': 999, 'FILL_SLOPE_PCT': 999},
    'nonfinite_nan': {'WIDTH_M': 'nan', 'RFG_PCT': 'nan', 'FILL_LENGTH_M': 'nan', 'FILL_SLOPE_PCT': 'nan'},
    'nonfinite_inf': {'WIDTH_M': 'inf', 'RFG_PCT': 'inf', 'FILL_LENGTH_M': 'inf', 'FILL_SLOPE_PCT': 'inf'},
    'invalid_fill': {'FILL_LENGTH_M': 'bad', 'FILL_SLOPE_PCT': 'bad'},
    'invalid_categories': {'SURFACE': 'bad', 'TRAFFIC': 'bad'},
}
for name, props in cases.items():
    warnings = Counter()
    resolved = controller._resolve_segment_run_inputs(
        properties=props, params=Roads._default_params(), segment_id='inventory',
        design='outslope_rutted', warning_counts=warnings, warning_examples=[], warning_limit=10)
    fill = controller._derive_fill_profile_from_inputs(
        fill_length_m=resolved['fill_length_m'], fill_slope_pct=resolved['fill_slope_pct'])
    rows.append(dict(case=name, requested=props, resolved=resolved, effective_fill=fill, warnings=dict(warnings)))
# Stringify nonfinite floats explicitly: valid JSON, no misleading null/zero.
def safe(obj):
    import math
    if isinstance(obj, float) and not math.isfinite(obj):
        return repr(obj)
    if isinstance(obj, dict):
        return {key: safe(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [safe(value) for value in obj]
    return obj
print(json.dumps(safe(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          scope='pure production resolver and fill derivation; no controller writes or native execution',
                          cases=rows)), indent=2, allow_nan=False))
