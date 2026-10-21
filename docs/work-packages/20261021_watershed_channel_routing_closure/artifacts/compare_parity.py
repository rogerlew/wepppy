"""Exact replay file parity, including scientific files written in runs/."""
from pathlib import Path
import argparse
import hashlib
import json


def inventory(root):
    result = {}
    for directory in ['runs', 'output']:
        for path in sorted((root / directory).rglob('*')):
            if not path.is_file() or path.name in {'wepp_observe.on', 'wepp_observe.log'}:
                continue
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def compare(roots):
    manifests = [inventory(root) for root in roots]
    executions = [json.loads((root / 'execution.json').read_text()) for root in roots]
    keys = sorted(set().union(*manifests))
    differences = [k for k in keys if len({m.get(k) for m in manifests}) != 1]
    return {'roots': [str(r) for r in roots], 'files_compared': len(keys),
            'differences': differences, 'exact_file_parity': not differences,
            'all_executions_successful': all(all(x['success'] for x in e['results']) for e in executions),
            'binaries': [e['binary_sha256'] for e in executions],
            'seconds': [sum(x['seconds'] for x in e['results']) for e in executions],
            'diagnostic_bytes': [sum(p.stat().st_size for p in root.rglob('*') if p.is_file()
                                  and (p.name.endswith('.observe.log') or p.name == 'wepp_observe.log'
                                       or p.name in {'channel_balance.csv', 'channel_publish.csv'})) for root in roots]}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('roots', type=Path, nargs=3)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.write_text(json.dumps(compare(a.roots), indent=2) + '\n')
