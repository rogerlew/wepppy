"""Archive/restore acceptance restricted to the existing disposable development run."""
from pathlib import Path
import json
import os
from wepppy.nodb.core import Soils
from wepppy.nodb.single_input_sources import read_source
from wepppy.rq.project_rq import archive_rq, restore_archive_rq

RUNID = 'single-input-acceptance-20260925'
WD = Path('/wc1/runs/si') / RUNID
assert WD.is_dir() and WD.name == RUNID
soils = Soils.getInstance(str(WD))
raw, _ = read_source(soils, 'soils')
metadata = soils._single_user_defined_source.copy()
assert metadata['version'] == '7777'
before = set((WD / 'archives').glob('*.zip'))
archive_rq(RUNID, '7777 supplied source acceptance')
created = set((WD / 'archives').glob('*.zip')) - before
assert len(created) == 1
archive = created.pop()
restore_archive_rq(RUNID, archive.name)
soils = Soils.getInstance(str(WD))
assert soils._single_user_defined_source == metadata
assert read_source(soils, 'soils')[0] == raw
result = {'archive': archive.name, 'source_metadata_and_hashes_preserved': True,
          'source_sha256': metadata['sha256'], 'uid': os.getuid(), 'gid': os.getgid()}
(WD / 'soil-7777-archive.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
