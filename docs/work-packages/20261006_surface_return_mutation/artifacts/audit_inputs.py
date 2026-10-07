#!/usr/bin/env python3
"""Compare current frozen inputs with August snapshot and scenario counterparts."""
import argparse
import json
from pathlib import Path
from collections import Counter

from wepppy.wepp.peakflow_census.common import sha256_file

OLD = Path('/home/workdir/peakflow-topanga-census-evidence/b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de/input-snapshot')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    a = parser.parse_args()
    inputs = json.loads((a.root / 'inputs.json').read_text())
    result = {'versus_august': {}, 'between_scenarios': {}}
    for scenario, manifest in inputs.items():
        differing, missing, equivalent_pass_suffix = [], [], []
        for name, digest in manifest['sha256'].items():
            old = OLD / scenario / 'runs' / name
            new = a.root / 'snapshot' / scenario / 'runs' / name
            assert sha256_file(new) == digest
            if not old.exists():
                missing.append(name)
            elif sha256_file(old) != digest:
                if name.endswith('.run') and old.read_text() == new.read_text().replace('.pass.dat', '.hbp'):
                    equivalent_pass_suffix.append(name)
                else:
                    differing.append(name)
            if name.endswith('.run'):
                hill = name[1:-4]
                for token in new.read_text().split():
                    if '/' in token:
                        assert token.startswith(f'../output/H{hill}.') and token.count('/') == 2, (name, token)
        result['versus_august'][scenario] = {'differing': differing, 'not_in_old_snapshot': missing,
            'equivalent_pass_suffix': equivalent_pass_suffix,
            'different_by_extension': dict(Counter(Path(n).suffix for n in differing))}
    b = inputs['burned']['sha256']
    u = inputs['undisturbed']['sha256']
    result['between_scenarios'] = {'differing': [n for n in b.keys() & u.keys() if b[n] != u[n]],
                                   'burned_only': sorted(b.keys() - u.keys()), 'undisturbed_only': sorted(u.keys() - b.keys())}
    (a.root / 'input-comparison.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({s: {k: len(v) if isinstance(v, list) else v for k, v in r.items()} for s, r in result['versus_august'].items()}, indent=2))


if __name__ == '__main__':
    main()
