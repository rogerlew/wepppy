"""Score a complete frozen screen without dropping native or accounting failures."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261029/surface-screen-v4')
GROUPS = ('climate', 'soil', 'design', 'surface', 'traffic')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rate(rows):
    return dict(cases=len(rows), passing=sum(r['within'] for r in rows),
                fraction=sum(r['within'] for r in rows)/len(rows) if rows else None)


def score(rows):
    """All cases remain in coverage; every physical failure is a separate veto."""
    if not rows:
        raise ValueError('Empty panel')
    failed = [r for r in rows if r['status'] != 'completed']
    physical = [r for r in rows if r['status'] != 'completed' or
                r['negative_fluxes'] or not r['report_reconciled'] or r['ebe_mismatch_events']]
    groups = {key:{value:rate([r for r in rows if r['case'][key] == value])
                   for value in sorted({r['case'][key] for r in rows})} for key in GROUPS}
    # Classify failed runs by their reference too; do not drop them from either
    # load stratum's denominator. Apply 95/90 separately to the two strata.
    strata = {}
    for label, flag in (('small', False), ('meaningful', True)):
        selected = [r for r in rows if r['meaningful'] == flag]
        strata[label] = dict(overall=rate(selected), groups={key:{value:
            rate([r for r in selected if r['case'][key] == value])
            for value in sorted({r['case'][key] for r in selected})} for key in GROUPS})
    small = strata['small']['overall']
    meaningful = strata['meaningful']['overall']
    overall = rate(rows)
    numerical = (overall['fraction'] >= .95 and
                 all(g['fraction'] >= .9 for values in groups.values() for g in values.values()) and
                 all((s['overall']['fraction'] is None or s['overall']['fraction'] >= .95) and
                     all(g['fraction'] >= .9 for values in s['groups'].values() for g in values.values())
                     for s in strata.values()))
    return dict(overall=overall, groups=groups, load_strata=strata, small_load=small, meaningful_load=meaningful,
                native_failures=[r['case'] for r in failed],
                physical_failures=[r['case'] for r in physical], numerical_gate=numerical,
                physical_gate=not physical, screen_gate=numerical and not physical,
                acceptance=False, limitation='Development screen only; withheld, routing and project-runtime validation pending')


def verify(rows, declaration):
    expected = {tuple(c.items()) for c in declaration['cases']}
    actual = [tuple(r['case'].items()) for r in rows]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('Missing, duplicate or unexpected case')
    for row in rows:
        profile = '-'.join(row['case'][key] for key in ('climate','soil','design','surface','traffic'))
        ref_file = Path('/wc1/runs/ro/roads-soil-benchmark-20261029/validation-v4')/f'{profile}-legacy-legacy'/'record.json'
        ref = json.loads(ref_file.read_text())['metrics']['sediment_export_kg_yr']
        if row['status'] == 'completed':
            if digest(ref_file) != row['reference_record_sha256'] or ref != row['reference_kg_yr']:
                raise ValueError('Reference drift')
            value = row['export_kg_yr']
            expected_pass = .1 <= value/ref <= 10 if ref > 1 else value <= max(1, 10*ref)
            if expected_pass != row['within'] or row['meaningful'] != (ref > 1):
                raise ValueError('Comparison drift')
        else:
            row['meaningful'] = ref > 1
            row['reference_kg_yr'] = ref
        folder = ROOT/'matrix-v1'/'-'.join(row['case'].values())
        file = folder/('record.json' if row['status'] == 'completed' else 'failure.json')
        record = json.loads(file.read_text())
        if record['case'] != row['case'] or record['status'] != row['status']:
            raise ValueError('Record identity drift')
        for sub, key in (('runs', 'inputs'), ('output', 'outputs')):
            for name, sha in record[key].items():
                if digest(folder/sub/name) != sha:
                    raise ValueError('Native artifact drift')
        if row['status'] == 'completed':
            if digest(file) != row['record_sha256']:
                raise ValueError('Record drift')
            audit = json.loads((ROOT/'analysis/cases'/f"{'-'.join(row['case'].values())}.json").read_text())
            if (audit['record_sha256'] != row['record_sha256'] or
                audit['sediment']['negative_fluxes'] != row['negative_fluxes'] or
                audit['sediment']['report_reconciled'] != row['report_reconciled'] or
                len(audit['ebe']['mismatches']) != row['ebe_mismatch_events'] or
                record['metrics']['sediment_export_kg_yr'] != row['export_kg_yr']):
                raise ValueError('Audit/result drift')
        else:
            for name in ('stdout', 'stderr'):
                if digest(folder/'runs'/name) != row[f'{name}_sha256']:
                    raise ValueError('Failure diagnostic drift')
            if row['within']:
                raise ValueError('Failed native run cannot pass')


def main():
    rows = json.loads((ROOT/'results.json').read_text())
    declaration = json.loads((ROOT/'declaration.json').read_text())
    verify(rows, declaration)
    variants = defaultdict(list)
    for row in rows:
        variants[row['case']['variant']].append(row)
    results = dict(root=str(ROOT), declaration_sha256=digest(ROOT/'declaration.json'),
                   results_sha256=digest(ROOT/'results.json'), variants={k:score(v) for k,v in variants.items()})
    (HERE/'surface-screen-score.json').write_text(json.dumps(results, indent=2)+'\n')
    for variant, result in results['variants'].items():
        print(variant, result['overall'], 'native', len(result['native_failures']),
              'physical', len(result['physical_failures']), 'screen_gate', result['screen_gate'])


if __name__ == '__main__':
    main()
