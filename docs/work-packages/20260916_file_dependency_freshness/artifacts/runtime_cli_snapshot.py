"""Retain actual CLI content and inode metadata in the disposable runtime run."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('--compare')
args = parser.parse_args()
root = Path('/wc1/runs/qa/qa-freshness-runtime-7e24c8d1')
output = Path(__file__).with_name('runtime_cli_'+args.label+'.json')
if output.exists():
    raise FileExistsError(output)
files = {}
for path in sorted((root/'climate').rglob('*.cli')):
    before = path.stat()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    assert all(getattr(before, field) == getattr(after, field) for field in fields)
    files[str(path.relative_to(root))] = {'sha256': digest, **{field: getattr(after, field) for field in fields}}
assert files
result = {'root': str(root), 'files': files}
if args.compare:
    previous = json.loads(Path(__file__).with_name('runtime_cli_'+args.compare+'.json').read_text())['files']
    result['comparison'] = {'same_paths': files.keys() == previous.keys(),
        'changed_bytes': [name for name in files if name not in previous or files[name]['sha256'] != previous[name]['sha256']],
        'changed_ctime': [name for name in files if name in previous and files[name]['st_ctime_ns'] != previous[name]['st_ctime_ns']],
        'changed_links': [name for name in files if name in previous and files[name]['st_nlink'] != previous[name]['st_nlink']]}
output.write_text(json.dumps(result, indent=2)+'\n')
print('CLI snapshot', args.label, len(files), result.get('comparison'))
