"""Collect retained replay receipts; failed cases never become closure passes."""
from pathlib import Path
import csv
import hashlib
import json

from audit_replays import channel_ledger, readback, summarize, observed_controls, controls, pipeline_controls
from compare_parity import compare

LOCAL = Path('/workdir/watershed-channel-routing-closure-20261021')
HOLDOUT = Path('/wc1/holdouts/watershed-channel-routing-closure-20261021')
PACKAGE = Path(__file__).resolve().parent


def exploratory_cases():
    # These attempts localize failures only; they do not establish parity or closure.
    return [
        {'case': 'up-pedantry-evappm-failure', 'configured_years': 6, 'completed': False,
         'exact_parity': 'not assessed', 'observe_root': str(HOLDOUT / 'up-pedantry-baseline')},
        {'case': 'near-burton-creek-zero-HMAX', 'configured_years': 30, 'completed': False,
         'exact_parity': 'not assessed', 'observe_root': str(HOLDOUT / 'real-baseline')},
    ]


def main():
    groups = {name: [HOLDOUT / 'controlled-baseline' / name, HOLDOUT / 'controlled-off' / name,
                     LOCAL / 'controlled-on' / name] for name in ['single', 'equal', 'upper60', 'lower60', 'three']}
    groups.update({name: [LOCAL / 'extensions' / mode / name for mode in ['baseline', 'off', 'on']]
                   for name in ['daily', 'tributaries', 'cascade', 'impoundment']})
    groups['real-tight-orthodontist'] = [LOCAL / ('real-second-' + mode) for mode in ['baseline', 'off', 'on']]
    parity, summaries, matrix, ledgers = {}, {}, [], []
    for name, roots in groups.items():
        result = compare(roots)
        parity[name] = result
        execution = json.loads((roots[-1] / 'execution.json').read_text())
        years = int((roots[-1] / 'runs/pw0.run').read_text().splitlines()[-1])
        matrix.append({'case': name, 'configured_years': years, 'completed': result['all_executions_successful'],
                       'exact_parity': result['exact_file_parity'], 'observe_root': str(roots[-1])})
        if not result['all_executions_successful']:
            summaries[name] = {'disposition': 'incomplete; no closure claim', 'executions': execution['results']}
            continue
        assert result['exact_file_parity'], (name, result['differences'])
        hills = sorted(int(p.stem[1:]) for p in (roots[-1] / 'runs').glob('p[0-9]*.run'))
        passes = {hill: readback(roots[-1], hill) for hill in hills}
        rows = channel_ledger(roots[-1], name)
        assert len(rows) % next(iter(passes.values()))['days'] == 0
        for row in rows:
            row['boundary'] = 'channel publication'
            row['interval'] = 'calendar day; integrated published volumes'
            row['phase'] = 'post-routing publication with start/end storage'
            row['source_artifacts'] = str(roots[-1] / 'channel_publish.csv') + ';' + str(roots[-1] / 'channel_balance.csv')
            row['binary_sha256'] = execution['binary_sha256']
            row['input_manifest'] = str(roots[-1] / 'input_manifest.json')
        ledgers.extend(rows)
        summaries[name] = {'pass_readback_by_hill': passes, 'channel_publication_arithmetic': summarize(rows),
                           'disposition': 'calendar selection defect; domain conservation unresolved'}
    matrix.extend(exploratory_cases())
    target = LOCAL / 'audit-complete'
    target.mkdir(exist_ok=True)
    with (target / 'volume_ledger.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(ledgers[0])); writer.writeheader(); writer.writerows(ledgers)
    diagnostic = {'hand_computable': controls(), 'observed_mutations': observed_controls(ledgers, target),
                  'pipeline_rejections': pipeline_controls(LOCAL / 'controlled-on/single', target)}
    for filename, data in [('parity.json', parity), ('residual_summary.json', summaries), ('diagnostic_controls.json', diagnostic)]:
        (PACKAGE / filename).write_text(json.dumps(data, indent=2) + '\n')
    with (PACKAGE / 'case_matrix.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(matrix[0])); w.writeheader(); w.writerows(matrix)
    compact = []
    for name, record in summaries.items():
        if 'channel_publication_arithmetic' not in record:
            continue
        r = record['channel_publication_arithmetic']
        compact.append({'case': name, 'rows': r['rows'], 'signed_m3': r['signed_m3'], 'absolute_m3': r['absolute_m3'],
                        'max_absolute_m3': abs(r['worst']['residual']), 'outside_arithmetic_bound': r['outside_arithmetic_bound'],
                        'negative_loss_rows': r['negative_loss_rows']})
    with (PACKAGE / 'residual_summary.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(compact[0])); w.writeheader(); w.writerows(compact)
    payloads = [target / 'volume_ledger.csv', target / 'observed_control_ledgers.csv']
    (PACKAGE / 'retained_ledgers.json').write_text(json.dumps([{'path': str(p), 'bytes': p.stat().st_size,
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in payloads], indent=2) + '\n')


if __name__ == '__main__':
    main()
