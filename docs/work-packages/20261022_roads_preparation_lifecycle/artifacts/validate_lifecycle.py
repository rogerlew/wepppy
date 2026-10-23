"""Exercise two full Roads runs and replacement in the isolated UM1 restore."""
import hashlib
import json
import os
from pathlib import Path
import time

import pyarrow.parquet as pq
from wepppy.nodb.mods.roads import Roads
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

root = Path('/wc1/runs/ro/roads-segment-summary-validation')
original = Path('/wc1/runs/cl/clogging-starch')
assert root != original and root.is_dir()

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

protected = {str(path.relative_to(root)): digest(path)
             for folder in ('wepp/output', 'wepp/runs')
             for path in (root/folder).rglob('*') if path.is_file()}
original_hashes = {str(path.relative_to(original)): digest(path)
                   for path in original.glob('wepp/**/*.parquet')}
controller = Roads.getInstance(str(root))
started = time.time()
print('First full Roads run', flush=True)
first = controller.run_roads_wepp()
assert first['status'] == 'completed' and lifecycle.available(root)
first_receipt = lifecycle.require_current(root)
summary_path = root/lifecycle.OUTPUT/'interchange/roads_segment_loss_summary.parquet'
first_rows = pq.read_table(summary_path).num_rows
print('Reprepare; verify current output is revoked', flush=True)
controller.prepare_segments()
assert not lifecycle.available(root)
assert not summary_path.exists()
histories = list((root/lifecycle.HISTORY).iterdir())
assert any((path/lifecycle.RECEIPT).exists() for path in histories)
assert controller.query_summary()['last_run_summary'] is None
print('Second full Roads run', flush=True)
second = controller.run_roads_wepp()
assert second['status'] == 'completed' and lifecycle.available(root)
assert pq.read_table(summary_path).num_rows == first_rows
assert all(digest(root/path) == value for path,value in protected.items())
assert all(digest(original/path) == value for path,value in original_hashes.items())
result = {'root':str(root), 'uid':os.getuid(), 'gid':os.getgid(),
          'elapsed_seconds':time.time()-started, 'profile_rows':first_rows,
          'receipt':lifecycle.require_current(root), 'history_count':len(histories),
          'baseline_files_unchanged':len(protected), 'original_parquets_unchanged':len(original_hashes),
          'summary_sha256':digest(summary_path), 'two_full_runs_and_repreparation':True}
Path('/tmp/roads-lifecycle-real.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2), flush=True)
