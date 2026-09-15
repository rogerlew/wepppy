"""Retain/compare protected upstream bytes for one authorized development run."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def audit(root):
    selected = [root/'soils.nodb',root/'rusle.nodb']
    for name in ('soils','rusle','wepp/runs'):
        selected.extend(sorted((root/name).rglob('*')))
    result = {}
    for path in selected:
        if path.is_symlink():
            result[str(path.relative_to(root))] = {'link':os.readlink(path)}
        elif path.is_file():
            before = path.stat()
            with path.open('rb') as stream: digest = hashlib.file_digest(stream,'sha256').hexdigest()
            after = path.stat()
            if (before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                raise ValueError('Protected source changed during audit: '+str(path))
            result[str(path.relative_to(root))] = {'bytes':after.st_size,'sha256':digest}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--baseline',type=Path)
    args = parser.parse_args()
    root,output = args.project.absolute(),args.output.absolute()
    if not output.is_relative_to(root/'postfire_debris_flow') or output.exists():
        raise ValueError('Audit output must be a fresh module-owned file')
    output.parent.mkdir(parents=True,exist_ok=True)
    current = audit(root)
    record = {'project':str(root),'files':current}
    if args.baseline:
        previous = json.loads(args.baseline.read_text())
        if previous['project'] != str(root): raise ValueError('Wrong audit project')
        record['changed'] = sorted(k for k in set(previous['files'])|set(current) if previous['files'].get(k) != current.get(k))
    with output.open('x') as stream: json.dump(record,stream,sort_keys=True)
    print(json.dumps({'output':str(output),'files':len(current),'changed':record.get('changed')}))
    if record.get('changed'): raise SystemExit(1)
