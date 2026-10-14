"""Verify retained hashes and canonical export values without rerunning models."""
import json
from pathlib import Path
import tarfile
import tempfile

import numpy as np
import pandas as pd

from wepppy.climates.edde.client import sha256, write_json
from wepppy.climates.edde.cligen import read_cli

HERE = Path(__file__).resolve().parent
project = json.loads((HERE/'project-validation.json').read_text())
writers = json.loads((HERE/'writer-validation.json').read_text())
archives = []
for record in [project, writers]:
    path = HERE / record['archive']['path']
    assert sha256(path) == record['archive']['sha256']
    root = Path(tempfile.mkdtemp(prefix='prism-retained-'))
    with tarfile.open(path) as archive:
        archive.extractall(root, filter='data')
    members = [dict(path=str(p.relative_to(root)), bytes=p.stat().st_size, sha256=sha256(p))
               for p in sorted(root.rglob('*')) if p.is_file()]
    archives.append(dict(path=path.name, sha256=sha256(path), members=members))
    if record is project:
        assert sha256(root/project['prepared']) == project['prepared_sha256']
        assert sha256(root/project['generated']) == project['prepared_sha256']
        table = pd.read_parquet(root/'climate/wepp_cli.parquet')
        source = read_cli(root/'climate/wepp.cli')
        assert len(table) == len(source) == 7305
        for name in ['prcp', 'tmax', 'tmin', 'rad', 'w-vl', 'w-dir', 'tdew']:
            np.testing.assert_allclose(table[name], source[name], rtol=0, atol=0)
write_json(HERE/'evidence-index.json', dict(status='complete', archives=archives,
    parquet_check='7305 rows; canonical watershed CLI weather values exactly match export',
    limitation='Canonical climate parquet describes the watershed CLI; per-hillslope spatial climates remain CLI artifacts.'))
