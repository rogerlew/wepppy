"""Read live source artifacts after ZIP restoration, without consulting shared cache."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import zipfile

import pandas as pd

from wepppy.climates.prism.wepp_adapter import validate_cli

root = Path('/wc1/runs/ch/chemotherapeutic-scope')
out = Path(__file__).parent
archive = root / 'archives/prism-integration-climate-portable.zip'
original = {
    str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (root / 'climate').rglob('*') if path.is_file()
}
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as target:
    for relative in original:
        target.write(root / relative, relative)

os.environ['PRISM_CACHE_DIR'] = '/nonexistent-prism-cache-for-portability-check'
with TemporaryDirectory(prefix='prism-restored-') as temporary:
    restored = Path(temporary)
    with zipfile.ZipFile(archive) as source:
        source.extractall(restored)
    for relative, digest in original.items():
        assert hashlib.sha256((restored / relative).read_bytes()).hexdigest() == digest
    proof = json.loads((restored / 'climate/provenance.json').read_text())
    for source in proof['sources']:
        directory = restored / source['source_directory']
        assert directory.is_dir()
        assert (restored / source['freshness_check_directory']).is_dir()
        assert hashlib.sha256((directory / 'bulk.csv.gz').read_bytes()).hexdigest() == source['raw_sha256']
    dates = pd.date_range('2019-01-01', '2021-12-31')
    for path in (restored / 'climate').glob('prism800m-hill-*.cli'):
        validate_cli(path, dates)
    cells = {item['cell'] for item in proof['locations'].values()}
    for cell in cells:
        frame = pd.read_parquet(restored / 'climate' / (cell + '-source.parquet'))
        assert frame.index.equals(dates)

record = {
    'archive': str(archive), 'files_restored_byte_identical': len(original),
    'source_partitions_resolved': len(proof['sources']), 'cells_read': len(cells),
    'cache_environment': os.environ['PRISM_CACHE_DIR'],
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'scope': 'Live climate ZIP/readback; canonical project archive/restore covered separately by regression tests',
}
(out / 'forest-portability.json').write_text(json.dumps(record, indent=2) + '\n')
print(record)
