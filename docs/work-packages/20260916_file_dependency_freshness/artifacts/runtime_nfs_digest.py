"""Actual /wc1 filesystem metadata operations, no mocked stat or digest."""
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from wepppy.all_your_base.file_digest import sha256_file

root = Path('/wc1/runs/qa') / ('qa-freshness-nfs-'+uuid.uuid4().hex[:12])
root.mkdir()
path = root/'ordinary.bin'
path.write_bytes(b'a'*4096)
initial = path.stat()
expected = hashlib.sha256(path.read_bytes()).hexdigest()
rows = []


def observe(label, wanted):
    actual = sha256_file(path)
    st = path.stat()
    row = {'label': label, 'sha256': actual, 'expected_sha256': wanted,
           **{name: getattr(st, name) for name in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')}}
    rows.append(row)
    assert actual == wanted, row


observe('initial', expected)
time.sleep(1.1)
observe('settled', expected)
os.link(path, root/'linked.bin')
observe('hardlink_added', expected)
(root/'linked.bin').unlink()
observe('hardlink_removed', expected)
os.utime(path, ns=(initial.st_atime_ns, initial.st_mtime_ns+1000000000))
observe('touch', expected)
os.chmod(path, 0o600)
observe('chmod_readable', expected)
collisions = 0
last_version = None
for index in range(1000):
    content = str(index).zfill(8).encode()*512
    path.write_bytes(content)
    os.utime(path, ns=(initial.st_atime_ns, initial.st_mtime_ns))
    current = path.stat()
    version = (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_ctime_ns)
    collisions += version == last_version
    last_version = version
    observe('restored_mtime_'+str(index), hashlib.sha256(content).hexdigest())
result = {'root': str(root), 'uid': os.getuid(), 'gid': os.getgid(),
          'same_whole_version_consecutive_writes': collisions, 'mismatches': 0,
          'scope': 'Single host/service observation on /wc1 NFS; no cross-host cache guarantee.', 'operations': rows}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
print('NFS digest probe passed:', len(rows), 'operations;', collisions, 'same-version writes')
