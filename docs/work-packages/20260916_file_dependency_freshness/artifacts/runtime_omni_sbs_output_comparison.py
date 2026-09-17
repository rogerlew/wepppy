#!/usr/bin/env python3
"""Read retained actual low/high native results; never hydrate a source owner."""
import json
from pathlib import Path
import pandas as pd

root = Path('/wc1/batch/qa-omni-native-20260917-a61f3e')
relative = 'wepp/output/interchange/loss_pw0.out.parquet'
low = pd.read_parquet(root / 'generation-1' / relative)
high = pd.read_parquet(root / 'generation-2' / relative)
if low.shape != high.shape or list(low.columns) != list(high.columns):
    raise AssertionError('Low/high native result schemas differ')
changes = []
for position in range(len(low)):
    before, after = low.iloc[position].to_dict(), high.iloc[position].to_dict()
    if before != after:
        changes.append({'row': position, 'low': before, 'high': after})
if not changes:
    raise AssertionError('Actual low/high watershed result values are identical')
result = {'status': 'passed', 'source': relative, 'rows': len(low),
          'columns': list(low.columns), 'changed_values': changes}
output = Path(__file__).with_suffix('.json')
output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': 'passed', 'changed_rows': len(changes), 'output': str(output)}))
