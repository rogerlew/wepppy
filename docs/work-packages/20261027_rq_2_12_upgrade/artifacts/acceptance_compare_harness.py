"""Exact paired scientific-content comparison after the upgraded readback."""
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq

ART = Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts')
before = json.loads((ART / 'acceptance_baseline_readback.json').read_text())
after = json.loads((ART / 'acceptance_upgraded_readback.json').read_text())
left = Path('/wc1/runs/rq/rq212-20261027-baseline')
right = Path('/wc1/runs/rq/rq212-20261027-upgraded')
result = {'inputs': {}, 'parquets': {}, 'reports': {}}
assert before['persisted'] == after['persisted']
assert before['inputs'].keys() == after['inputs'].keys()
for name in before['inputs']:
    a = (left / 'wepp/runs' / name).read_bytes()
    b = (right / 'wepp/runs' / name).read_bytes()
    assert hashlib.sha256(a).hexdigest() == before['inputs'][name]['sha256']
    assert hashlib.sha256(b).hexdigest() == after['inputs'][name]['sha256']
    # Model diagnostic .err files are execution records, not consumed inputs.
    if name.endswith('.err'):
        result['inputs'][name] = {'diagnostic': True, 'byte_equal': a == b}
        continue
    normalized_a = a.replace(left.name.encode(), b'<DISPOSABLE_RUN>')
    normalized_b = b.replace(right.name.encode(), b'<DISPOSABLE_RUN>')
    result['inputs'][name] = {'byte_equal': a == b, 'run_identity_normalized_equal': normalized_a == normalized_b}
    assert normalized_a == normalized_b, ('Consumed input mismatch', name)
assert before['outputs'].keys() == after['outputs'].keys()
for name in before['outputs']:
    a = pq.read_table(left / 'wepp/output/interchange' / name)
    b = pq.read_table(right / 'wepp/output/interchange' / name)
    assert a.schema.equals(b.schema, check_metadata=False), ('Schema mismatch', name)
    exact = a.equals(b, check_metadata=False)
    if not exact:
        da = a.to_pandas().sort_values(a.column_names).reset_index(drop=True)
        db = b.to_pandas().sort_values(b.column_names).reset_index(drop=True)
        assert da.equals(db), ('Scientific value mismatch', name)
    result['parquets'][name] = {'rows': a.num_rows, 'ordered_value_equality': exact,
                                'all_value_equality': True,
                                'byte_equal': before['outputs'][name]['sha256'] == after['outputs'][name]['sha256']}
for table, data in before['reports'].items():
    assert data['rows'] == after['reports'][table]['rows'], ('Report mismatch', table)
    result['reports'][table] = {'rows_equal': True, 'rows': len(data['rows'])}
(ART / 'acceptance_paired_comparison.json').write_text(json.dumps(result, indent=2))
print('PASS:', len(result['inputs']), 'files,', len(result['parquets']), 'Parquets,', len(result['reports']), 'reports')
