"""Bounded disposable-run overlap; execute under actual rq-worker identity."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from wepppy.runtime_paths.wepp_inputs import copy_input_file

runid, attempt, mode = sys.argv[1:]
assert runid == 'qa-active-cli-20260917'
assert len(attempt) == 32 and all(char in '0123456789abcdef' for char in attempt)
assert mode in ('overlap', 'negative', 'restore')
wd = Path('/wc1/runs/qa')/runid
root = wd/'postfire_debris_flow/attempts'/attempt
cli = wd/'climate/wepp.cli'
backup = root/'runtime_validation_cli_backup'

def record():
    st = cli.stat()
    return {'sha256':hashlib.sha256(cli.read_bytes()).hexdigest(),
            'stat':[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns],
            'nlink':st.st_nlink}

before = record()
if mode == 'restore':
    metadata = json.loads((root/'runtime_validation_mutation.json').read_text())
    cli.write_bytes(backup.read_bytes())
    os.utime(cli, ns=(cli.stat().st_atime_ns,metadata['before']['stat'][3]))
else:
    deadline = time.monotonic()+45
    while not (root/'predictors').is_dir():
        if time.monotonic() >= deadline:
            raise RuntimeError('Native predictor execution did not start in time')
        time.sleep(.1)
    before = record()
    if mode == 'overlap':
        copy_input_file(str(wd),'climate/wepp.cli',wd/'wepp/runs/pw0.cli')
        (wd/'wepp/runs/pw0.cli').unlink()
        copy_input_file(str(wd),'climate/wepp.cli',wd/'wepp/runs/pw0.cli')
        assert (wd/'wepp/runs/pw0.cli').stat().st_ino == cli.stat().st_ino
    else:
        data = cli.read_bytes()
        with backup.open('xb') as stream:
            stream.write(data)
        index = max(index for index,value in enumerate(data) if 48 <= value <= 57)
        changed = data[:index] + bytes([48+(data[index]-48+1)%10]) + data[index+1:]
        cli.write_bytes(changed)
        os.utime(cli, ns=(cli.stat().st_atime_ns,before['stat'][3]))
after = record()
result = {'mode':mode,'runid':runid,'attempt':attempt,'uid':os.getuid(),'gid':os.getgid(),
          'groups':os.getgroups(),'utc_unix':time.time(),'before':before,'after':after,
          'predictors_present':(root/'predictors').is_dir()}
if mode == 'overlap':
    assert before['sha256'] == after['sha256']
    assert before['stat'][:4] == after['stat'][:4]
    assert before['stat'][4] != after['stat'][4]
(root/('runtime_validation_'+('restore' if mode=='restore' else 'mutation')+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
