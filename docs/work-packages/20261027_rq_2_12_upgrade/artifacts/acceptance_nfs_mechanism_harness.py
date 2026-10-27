"""Reproduce retained-log NFS semantics without importing or using RQ."""
from pathlib import Path
import errno
import json
import logging
import os
import tempfile

out = Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts/acceptance_nfs_mechanism.json')
root = Path(tempfile.mkdtemp(prefix='.rq212-nfs-probe-', dir='/wc1/runs/rq'))
path = root / 'owned.log'
handler = logging.FileHandler(path)
handler.emit(logging.LogRecord('rq212', logging.INFO, '', 0, 'owned probe', (), None))
handler.flush()
path.unlink()
held = list(root.glob('.nfs*'))
assert len(held) == 1
try:
    held[0].unlink()
except OSError as exc:
    assert exc.errno == errno.EBUSY
    result = {'identity': {'uid': os.getuid(), 'gid': os.getgid()},
              'open_file_unlink_creates_nfs': True, 'second_unlink_errno': exc.errno,
              'second_unlink_error': exc.strerror, 'rq_used': False}
else:
    raise AssertionError('Expected NFS open-handle EBUSY')
handler.close()
assert not list(root.iterdir())
root.rmdir()
result['close_releases_nfs_file'] = True
result['probe_removed'] = True
out.write_text(json.dumps(result, indent=2))
