"""Reproduce the original all-nine, both-mode explanatory contrast table."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retained', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = args.retained
    paths = [source / name for name in ('structural.csv', 'layers.csv', 'target-buffer.csv')]
    bindings = {str(path.resolve()): sha(path) for path in paths}
    accepted = json.loads((source / 'receipt.json').read_text())
    for path in paths:
        if sha(path) != accepted['outputs'][path.name]:
            raise ValueError(f'Retained table drift: {path}')
    bindings[str((source / 'receipt.json').resolve())] = sha(source / 'receipt.json')
    structures = {
        (r['case'], r['lane'], r['mode'], r['year'], r['day'], r['consumer_ofe'], r['layer']): r
        for r in csv.DictReader((source / 'structural.csv').open())
    }
    components = {}
    for row in csv.DictReader((source / 'layers.csv').open()):
        if row['target'] != 'True' or row['consumer_ofe'] != '3':
            continue
        key = row['case'], row['lane'], row['mode']
        totals = components.setdefault(key, [0., 0.])
        structural = structures[
            row['case'], row['lane'], row['mode'], row['year'], row['day'],
            row['owner_ofe'], row['layer']
        ]
        weight = float(row['weight'])
        totals[0] += weight * float(structural['initial_pore_volume_m'])
        totals[1] += weight * float(structural['dry_water_offset_m'])
    target_rows = list(csv.DictReader((source / 'target-buffer.csv').open()))
    calls = {(r['case'], r['lane'], r['mode']): r for r in target_rows}
    if len(target_rows) != 36 or len(calls) != 36 or len(components) != 36:
        raise ValueError('Expected all nine cases, two lanes and both modes')
    rows = []
    for number in range(1, 10):
        for mode in ('0', '1'):
            case = f'B{number}'
            legacy = calls[case, 'legacy', mode]
            modern = calls[case, 'modern', mode]
            generated_components = components[case, 'modern', mode]
            legacy_components = components[case, 'legacy', mode]
            # Preserve original double operation order: subtract meters, then scale.
            rows.append(dict(
                case=case,
                mode=mode,
                delta_pore_mm=1000 * (generated_components[0] - legacy_components[0]),
                delta_dry_mm=1000 * (generated_components[1] - legacy_components[1]),
                delta_ul_mm=1000 * (float(modern['ul_m']) - float(legacy['ul_m'])),
                negative_delta_saved_liquid_mm=-1000 * (
                    float(modern['saved_liquid_m']) - float(legacy['saved_liquid_m'])),
                delta_available_mm=1000 * (
                    float(modern['connected_available_m']) - float(legacy['connected_available_m']))))
    output = args.out / 'target-contrasts.csv'
    with output.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    for path, expected in bindings.items():
        if sha(Path(path)) != expected:
            raise ValueError(f'Input changed: {path}')
    receipt = dict(passed=True, rows=len(rows), input_bindings=bindings,
                   reader_sha256=sha(Path(__file__)), table_sha256=sha(output),
                   arithmetic='Original double explanatory components: weighted sums in retained row order, subtract meters, then multiply by1000; native REAL checks remain separate.')
    with (args.out / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'rows': len(rows), 'table_sha256': receipt['table_sha256']}))


if __name__ == '__main__':
    main()
