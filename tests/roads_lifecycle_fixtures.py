"""Explicit current-result receipt fixtures for consumer tests.

These seed admission, not full-run correctness. Publication is exercised through
real publish/retain operations in test_roads_lifecycle.py.
"""
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange import _roads_lifecycle as lifecycle


def write_current_roads_fixture(root):
    root = Path(root)
    paths = sorted(lifecycle.mandatory_paths(False))
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            if path.suffix == '.parquet':
                pq.write_table(pa.table({'fixture': [1]}), path)
            else:
                path.write_text('Consumer fixture')
    for relative in ('wepp/roads/output/interchange/chnwb.parquet',
                     'wepp/roads/output/interchange/H.accounting.wat.parquet',
                     'wepp/roads/segments/roads.accounting.json'):
        if (root / relative).is_file():
            paths.append(relative)
    with lifecycle.operation(root):
        (root / lifecycle.RECEIPT).write_text(json.dumps({
            'policy': lifecycle.POLICY, 'is_single_storm': False,
            'required_relpaths': paths}))
