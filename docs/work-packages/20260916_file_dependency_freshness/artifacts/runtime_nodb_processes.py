"""Normal NoDb setter and long-lived reader processes on a disposable NFS run."""
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import uuid

from wepppy.nodb.core import Ron


def reader(connection, wd):
    while connection.recv() == 'read':
        owner = Ron.getInstance(wd)
        st = (Path(wd)/'ron.nodb').stat()
        connection.send({'pid': os.getpid(), 'name': owner.name,
                         'cached_mtime': owner._nodb_mtime, 'cached_size': owner._nodb_size,
                         'disk_mtime': st.st_mtime, 'disk_size': st.st_size})


if __name__ == '__main__':
    root = Path('/wc1/runs/qa')/('qa-freshness-nodb-'+uuid.uuid4().hex[:12])
    root.mkdir()
    shutil.copy2('/wc1/runs/qa/qa-freshness-profile-7e24c8d1/config.cfg', root/'config.cfg')
    owner = Ron(str(root), 'config.cfg')
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe()
    process = context.Process(target=reader, args=(child, str(root)))
    process.start()
    records = []
    try:
        for value in ('freshness generation one', 'freshness generation two', 'freshness generation end'):
            owner.name = value
            parent.send('read')
            if not parent.poll(60):
                raise TimeoutError('NoDb reader process did not respond')
            row = parent.recv()
            records.append(row)
            assert row['pid'] != os.getpid() and row['name'] == value
            assert row['cached_mtime'] == row['disk_mtime'] and row['cached_size'] == row['disk_size']
    finally:
        parent.send('stop')
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join()
    assert process.exitcode == 0
    result = {'root': str(root), 'writer_pid': os.getpid(), 'uid': os.getuid(),
              'gid': os.getgid(), 'observations': records,
              'scope': 'Normal completed atomic writes followed by a persistent cross-process reader; concurrent acquisition races remain covered by independent implementation tests.'}
    Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Normal cross-process NoDb payload/version propagation passed')
