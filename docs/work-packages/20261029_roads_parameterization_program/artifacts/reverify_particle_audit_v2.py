"""Additive particle-only readback of five frozen research panels.

No existing record, declaration, verification, audit or acceptance is rewritten.
Fresh output directory is mandatory. Native runs and their acceptance are not
re-executed or reclassified; strict particle flags are retained as findings.
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from collections import Counter
import argparse
import datetime
import json
import audit_particle_closure_v2 as v2

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def attempt_audit(record):
    try:
        return v2.audit(record)
    except ValueError as exc:
        return dict(record=str(record), record_sha256=v2.digest(record),
                    audit_error=str(exc), passed=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-root', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    if args.output_dir.exists():
        raise FileExistsError('Use a fresh output directory; retained evidence is immutable')
    args.output_dir.mkdir(parents=True)
    panels = [
        ('legacy_r3', args.raw_root/'legacy-soil-control-r3/results.json', 116),
        ('legacy_r4', args.raw_root/'legacy-soil-anchors-r4/results.json', 116),
        ('factorial_r4', args.raw_root/'combined-hydraulics-r4-v2/results.json', 928),
        ('U12_roads', args.raw_root/'param-sign-u12-combined/roads-results.json', 840),
        ('U12_downstream', args.raw_root/'param-sign-u12-combined/downstream-results.json', 348),
    ]
    records = {}
    frozen = {HERE/'audit_particle_closure.py', HERE/'review-legacy-element-fixed-width-fixture.json'}
    provenance = {}
    for name, result_path, count in panels:
        results = load(result_path)
        if len(results) != count:
            raise ValueError(f'Incorrect panel denominator: {name}')
        if name == 'legacy_r3':
            # Original generation predates the folder field; use its declared layout.
            keys = ('climate','soil','design','surface','traffic','variant','runtime')
            paths = [result_path.parent/'matrix-v1'/'-'.join(row['case'][k] for k in keys)/'record.json' for row in results]
        else:
            paths = [Path(row['folder'])/'record.json' for row in results]
        for row, path in zip(results, paths):
            if load(path) != row:
                raise ValueError(f'Result/record mismatch: {path}')
        if len(set(paths)) != count:
            raise ValueError(f'Duplicate panel records: {name}')
        records[name] = paths
        for path in result_path.parent.glob('*.json'):
            frozen.add(path)
        for path in result_path.parent.glob('*.py'):
            frozen.add(path)
        for path in paths:
            frozen.add(path)
            previous = path.parent/'particle-audit.json'
            if previous.exists():
                frozen.add(previous)
        provenance[name] = dict(results=str(result_path), results_sha256=v2.digest(result_path),
            cases=count, records=[dict(path=str(p), sha256=v2.digest(p),
                declared_input_sha256=load(p)['inputs'],
                binary_sha256=load(p)['binary_sha256']) for p in paths])
    immutable_before = {str(p):v2.digest(p) for p in sorted(frozen)}
    old_sha = immutable_before[str(HERE/'audit_particle_closure.py')]
    new_sha = v2.digest(v2.__file__)
    declared = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Particle-only reread; no native rerun, parameter acceptance or threshold change',
        old_audit_sha256=old_sha, new_audit_sha256=new_sha,
        runner_sha256=v2.digest(__file__), panels=provenance,
        scope_declaration_sha256=v2.digest(HERE/'particle-audit-v2-scope.md'),
        immutable_sha256_before=immutable_before,
        inputs_scope='Record-bound original input digests retained; this particle-only pass freshly hashes PASS/ELEMENT and records, not all native input files')
    declaration_path = args.output_dir/'declaration.json'
    declaration_path.write_text(json.dumps(declared, indent=2)+'\n')
    summaries = {}
    receipts = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for name, _, count in panels:
            rows=[]
            for row in pool.map(attempt_audit, records[name], chunksize=4):
                rows.append(row)
                if len(rows)%100==0:
                    print(f'{name}: {len(rows)}/{count}', flush=True)
            invalid = [row for row in rows if 'audit_error' in row]
            valid = [row for row in rows if 'audit_error' not in row]
            result = v2.summarize(valid)
            result['selected_cases'] = count
            result['rejected_records'] = invalid
            result['rejected_record_count'] = len(invalid)
            result['panel'] = name
            result['declaration_sha256'] = v2.digest(declaration_path)
            result['old_audit_sha256'] = old_sha
            causes = Counter(c for row in valid for event in row['flags'] for c in event['causes'])
            result['causes'] = dict(causes)
            result['particle_only'] = True
            result['unavailable_diagnostic_columns'] = dict(Counter(d['column'] for row in valid for d in row['numeric_unavailable_diagnostics']))
            path = args.output_dir/(name+'.json')
            path.write_text(json.dumps(result,indent=2)+'\n')
            receipts[name] = dict(path=str(path),sha256=v2.digest(path))
            summaries[name] = {k:result[k] for k in ['selected_cases','cases','rejected_record_count','events','positive_events','flagged_cases','flagged_events','causes','unavailable_diagnostic_fields','cases_with_unavailable_diagnostics']}
            print(name, summaries[name], flush=True)
    changed = [p for p,h in immutable_before.items() if v2.digest(p)!=h]
    if changed:
        raise ValueError(f'Frozen evidence changed during audit: {changed}')
    if new_sha != v2.digest(v2.__file__):
        raise ValueError('Versioned audit changed during execution')
    final=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope=declared['scope'],old_audit_sha256=old_sha,new_audit_sha256=new_sha,
        declaration_sha256=v2.digest(declaration_path),
        frozen_files_verified_unchanged=len(immutable_before),
        panels=summaries,receipts=receipts,
        numerical_criteria_changed=False,strict_flags_retained=True,
        original_records_and_verifications_unchanged=True,
        parameter_promotion_approved=False)
    path=args.output_dir/'receipt.json';path.write_text(json.dumps(final,indent=2)+'\n')
    print('FINAL',json.dumps(final),flush=True)


if __name__ == '__main__':
    main()
