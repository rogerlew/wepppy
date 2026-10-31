"""Bind the retained analysis scope to a fresh, successfully preflighted root."""
from pathlib import Path
import argparse
import hashlib
import json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    target = root / 'analysis-declaration.json'
    assert not target.exists(), target
    original = Path(__file__).resolve().parent / 'analysis-declaration.json'
    data = json.loads(original.read_text())
    preflight = json.loads((root / 'preflight.json').read_text())
    assert preflight['declaration_sha256'] == sha(root / 'declaration.json')
    assert len(preflight['records']) == 2
    for receipt in preflight['records']:
        assert sha(Path(receipt['receipt'])) == receipt['sha256']
    data.update(
        summary_script_sha256=sha(root / 'summarize.py'),
        ledger_declaration_sha256=sha(root / 'declaration.json'),
        preflight_receipt_sha256=sha(root / 'preflight.json'),
        original_analysis_declaration_sha256=sha(original),
        selection_rule='Three largest signed reported daily outlet differences per case, including zeros, then year/day; full calendar, not limited to PASS EVENT.',
        reproduction_note='Fresh-root binding and wording correction only; original executed declaration remains immutable.',
    )
    target.write_text(json.dumps(data, indent=2) + '\n')
    print(target)


if __name__ == '__main__':
    main()
