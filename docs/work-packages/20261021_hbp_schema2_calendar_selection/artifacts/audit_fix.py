"""Accept date-correct delivery, unchanged hillslopes, and nonintrusive observations."""
from pathlib import Path
import argparse
import calendar
import csv
import hashlib
import json
import sys

OLD = Path(__file__).resolve().parents[2] / '20261021_watershed_channel_routing_closure/artifacts'
sys.path.insert(0, str(OLD))
from audit_replays import readback, channel_ledger, summarize
from compare_parity import inventory

ROOT = Path('/workdir/hbp-schema2-calendar-selection-20261021')
HOLDOUT = Path('/wc1/holdouts/watershed-channel-routing-closure-20261021')
LOCAL = Path('/workdir/watershed-channel-routing-closure-20261021')
PACKAGE = Path(__file__).resolve().parent


def audit(case):
    off, on = (ROOT / mode / case for mode in ['off', 'on'])
    baseline = LOCAL / 'real-second-off' if case == 'real' else HOLDOUT / 'controlled-off' / case
    executions = [json.loads((r / 'execution.json').read_text()) for r in [off, on]]
    for e in executions:
        assert e['results'][-1]['card'] == 'pw0.run'
        assert all(r['success'] for r in e['results'])
    old_files, off_files, on_files = (inventory(r) for r in [baseline, off, on])
    assert off_files == on_files, 'Observations changed ordinary files'
    # The fix changes only watershed delivery. Require every hillslope product
    # (including binary PASS, WAT, loss, EBE and sediment outputs) to stay exact.
    hill_keys = sorted(k for k in old_files if k.startswith('output/H'))
    assert hill_keys and all(old_files[k] == off_files.get(k) for k in hill_keys)
    hills = sorted(int(p.stem[1:]) for p in (on / 'runs').glob('p[0-9]*.run'))
    receipts = {}
    for hill in hills:
        result = readback(on, hill)
        assert result['violation_count'] == 0, (case, hill, result['first_violations'])
        # Legacy audit also diagnoses sequential consumption; those counters are
        # intentionally not applicable to the corrected requested-date reader.
        receipts[hill] = {k: result[k] for k in ['days', 'years', 'hbp_sha256', 'maximum_deltas',
                                              'violation_count', 'event_counts']}
        receipts[hill]['last_requested_date'] = [result['years'][-1], 365 + calendar.isleap(result['years'][-1])]
        receipts[hill]['all_requested_days_checked'] = True
    rows = channel_ledger(on, case)
    ledger_path = ROOT / (case + '-channel-ledger.csv')
    with ledger_path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    data = {'case': case, 'roots': [str(baseline), str(off), str(on)],
            'executions': executions, 'off_on_exact': True, 'files_compared': len(off_files),
            'unchanged_hillslope_files': hill_keys, 'date_readback': receipts,
            'changed_watershed_files': sorted(k for k in set(old_files) | set(off_files)
                                             if old_files.get(k) != off_files.get(k)),
            'channel_publication_arithmetic_only': summarize(rows),
            'ledger': {'path': str(ledger_path), 'bytes': ledger_path.stat().st_size,
                       'sha256': hashlib.sha256(ledger_path.read_bytes()).hexdigest()}}
    (PACKAGE / (case + '-validation.json')).write_text(json.dumps(data, indent=2) + '\n')
    print(case, len(hills), 'hills, all dates pass, off/on exact, hillslope artifacts unchanged', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('case', choices=['single', 'upper60', 'real'])
    audit(p.parse_args().case)
