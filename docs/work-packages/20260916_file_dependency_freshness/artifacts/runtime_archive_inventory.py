"""Immutable producer artifacts and private directory modes around live RQ restore."""
import argparse
import hashlib
import json
from pathlib import Path
import stat

parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('--compare')
args = parser.parse_args()
root = Path('/wc1/runs/qa/qa-freshness-runtime-7e24c8d1')
files, directories = {}, {}
for relative in ('climate', 'postfire_debris_flow', 'wepp/reports/cache'):
    selected = root/relative
    assert selected.is_dir(), selected
    for path in [selected, *sorted(selected.rglob('*'))]:
        assert not path.is_symlink(), path
        info = path.stat()
        name = str(path.relative_to(root))
        if path.is_dir():
            directories[name] = stat.S_IMODE(info.st_mode)
        else:
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            files[name] = {'sha256': digest, 'bytes': info.st_size, 'mode': stat.S_IMODE(info.st_mode)}
result = {'root': str(root), 'files': files, 'directories': directories,
          'scope': 'Selected immutable climate/lineage, all post-fire attempts/results and report cache artifacts; excludes mutable root logs and controller/job bookkeeping.'}
if args.compare:
    old = json.loads(Path(__file__).with_name('runtime_archive_inventory_'+args.compare+'.json').read_text())
    result['equal_files'] = old['files'] == files
    result['equal_directories'] = old['directories'] == directories
output = Path(__file__).with_name('runtime_archive_inventory_'+args.label+'.json')
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(result, indent=2)+'\n')
if args.compare:
    assert result['equal_files'] and result['equal_directories'], 'Retained files or modes differ across live restore'
print('Retained producer inventory', args.label, len(files), 'files;', len(directories), 'directories')
