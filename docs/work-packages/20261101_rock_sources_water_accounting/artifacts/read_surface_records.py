"""Validate and summarize a bounded SDA XML response without imputing cover."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

MATERIALS = {'1718465', '1718494', '1856573', '2711184'}
FIELDS = ['mukey', 'cokey', 'compname', 'comppct_r', 'cosurffragskey',
          'sfragcov_l', 'sfragcov_r', 'sfragcov_h', 'sfragkind',
          'sfragsize_l', 'sfragsize_r', 'sfragsize_h', 'sfraghard']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--xml', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    payload = a.xml.read_bytes()
    root = ET.fromstring(payload)
    if root.tag != 'NewDataSet':
        raise ValueError('Expected SDA NewDataSet; HTTP success alone is insufficient')
    rows = []
    components = {}
    keys = set()
    for element in root.findall('Table'):
        observed = {child.tag: child.text for child in element}
        if set(observed) - set(FIELDS):
            raise ValueError('Unexpected response columns')
        row = {key: observed.get(key) for key in FIELDS}
        if row['mukey'] not in MATERIALS or not row['cokey']:
            raise ValueError('Out-of-scope or missing component identity')
        key = (row['mukey'], row['cokey'])
        pct = float(row['comppct_r'])
        if not 0 <= pct <= 100:
            raise ValueError('Invalid component proportion')
        component = components.setdefault(key, {
            'mukey': key[0], 'cokey': key[1], 'name': row['compname'],
            'component_percent': pct, 'records': []})
        if component['component_percent'] != pct or component['name'] != row['compname']:
            raise ValueError('Inconsistent repeated component metadata')
        record_key = row['cosurffragskey']
        if record_key is not None:
            if record_key in keys:
                raise ValueError('Duplicate surface-fragment record')
            keys.add(record_key)
            for prefix, limit in [('sfragcov', 100), ('sfragsize', float('inf'))]:
                values = [row[prefix + suffix] for suffix in ('_l', '_r', '_h')]
                if all(v is not None for v in values):
                    lo, mid, hi = map(float, values)
                    if not 0 <= lo <= mid <= hi <= limit:
                        raise ValueError('Invalid source interval')
            component['records'].append(row)
        elif any(row[k] is not None for k in FIELDS[5:]):
            raise ValueError('Surface values lack fragment identity')
        rows.append(row)
    if {r['mukey'] for r in rows} != MATERIALS:
        raise ValueError('Incomplete requested material support')
    summaries = []
    for mukey in sorted(MATERIALS):
        selected = [c for c in components.values() if c['mukey'] == mukey]
        total = sum(c['component_percent'] for c in selected)
        if total > 100:
            raise ValueError('Component proportions exceed 100')
        summaries.append({'mukey': mukey, 'components': len(selected),
            'surface_records': sum(len(c['records']) for c in selected),
            'reported_component_percent_total': total,
            'unallocated_component_percent': 100 - total,
            'reported_component_percent_with_records': sum(c['component_percent'] for c in selected if c['records']),
            'reported_component_percent_without_records': sum(c['component_percent'] for c in selected if not c['records']),
            'total_surface_cover_percent': None,
            'disposition': 'No cover aggregation: row overlap, completeness and local role not established'})
    with (a.out/'surface-records.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    (a.out/'surface-records.json').write_text(json.dumps(rows, indent=2)+'\n')
    (a.out/'component-support.json').write_text(json.dumps(list(components.values()), indent=2)+'\n')
    receipt = {'source_sha256': hashlib.sha256(payload).hexdigest(),
        'rows': len(rows), 'components': len(components), 'surface_records': len(keys),
        'zero_representative_records': sum(r['sfragcov_r'] == '0' for r in rows),
        'materials': summaries,
        'limitation': 'Component percentages are survey composition, not measured footprint area. Null is not zero. Current response is not the historical run snapshot.'}
    (a.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
