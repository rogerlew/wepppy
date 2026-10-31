"""Verify unique-node coverage from retained, unchanged application attempts."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import subprocess

ROOT = Path('/workdir/wepppy')
ART = Path(__file__).resolve().parent
OUT = ROOT / 'out/roads-parameterization-program-20261031/revision4-promotion'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_report(path):
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    finishes = [x for x in rows if x.get('$report_type') == 'SessionFinish']
    assert len(finishes) == 1, f'Incomplete or ambiguous execution: {path}'
    grouped = defaultdict(list)
    for row in rows:
        if row.get('$report_type') == 'TestReport' or row.get('_report_type') == 'SubTestReport':
            grouped[row['nodeid']].append(row)
    statuses = {}
    extra_call_reports = {}
    for node, reports in grouped.items():
        phases = defaultdict(list)
        for report in reports:
            phases[report['when']].append(report['outcome'])
        assert phases['teardown'] == ['passed'], (path, node, phases)
        if any('failed' in outcomes for outcomes in phases.values()):
            statuses[node] = 'failed'
        elif 'skipped' in phases['setup'] or 'skipped' in phases['call']:
            statuses[node] = 'skipped'
        else:
            assert phases['setup'] == ['passed'] and phases['call'], (path, node, phases)
            assert set(phases['call']) == {'passed'}, (path, node, phases)
            statuses[node] = 'passed'
        if len(phases['call']) > 1:
            extra_call_reports[node] = len(phases['call']) - 1
    return statuses, finishes[0]['exitstatus'], extra_call_reports


def main():
    declaration_path = ART / 'revision4-application-shards-declaration.json'
    completion_path = ART / 'revision4-application-completion-declaration.json'
    declaration = json.loads(declaration_path.read_text())
    completion = json.loads(completion_path.read_text())
    assert completion['source_declaration_sha256'] == sha(declaration_path)
    inventory = [node for spec in declaration['shards'] for node in spec['nodeids']]
    assert len(inventory) == len(set(inventory)) == declaration['collected'] == 12955
    assert sha(OUT / 'application-collection.log') == declaration['collection_sha256']
    accepted = {}
    accepted_attempts = defaultdict(list)
    original_failures = {}
    report_receipts = {}
    duplicates = Counter()
    subtests = {}

    def consume(label, expected, *, expected_exit, allow_failed=False):
        path = OUT / (label + '.jsonl')
        statuses, exitstatus, extra = inspect_report(path)
        assert exitstatus == expected_exit, (label, exitstatus)
        assert set(statuses) <= set(expected), (label, set(statuses) - set(expected))
        if not allow_failed:
            assert set(statuses) == set(expected), (label, set(expected) - set(statuses))
            assert 'failed' not in statuses.values(), label
        for node, status in statuses.items():
            if status == 'failed':
                original_failures.setdefault(node, []).append(label)
                continue
            if node in accepted:
                assert accepted[node] == status, (node, accepted[node], status)
                duplicates[node] += 1
            accepted[node] = status
            accepted_attempts[node].append(label)
        report_receipts[label] = dict(exitstatus=exitstatus, report_sha256=sha(path),
                                     log_sha256=sha(OUT / (label + '.log')),
                                     unique_outcomes=dict(Counter(statuses.values())))
        if extra:
            subtests[label] = extra

    for spec in declaration['shards']:
        number = spec['shard']
        assert sha(OUT / f'application-shard-{number}.args') == spec['args_sha256']
        consume(f'application-shard-{number}', spec['nodeids'],
                expected_exit=1 if number in (2, 8) else 0,
                allow_failed=number in (2, 8))
    for spec in completion['planned']:
        number = spec['shard']
        assert sha(OUT / f'application-completion-shard{number}.args') == spec['args_sha256']
        assert sha(OUT / f'application-shard-{number}.jsonl') == spec['original_report_sha256']
        consume(f'application-completion-shard{number}', spec['nodeids'], expected_exit=0)
    rejected_replay, code, _ = inspect_report(OUT / 'application-shard-8-replay.jsonl')
    assert code == 1
    report_receipts['application-shard-8-replay'] = dict(
        excluded_entire_attempt=True, exitstatus=code,
        unique_outcomes=dict(Counter(rejected_replay.values())),
        report_sha256=sha(OUT / 'application-shard-8-replay.jsonl'),
        log_sha256=sha(OUT / 'application-shard-8-replay.log'))
    assert set(accepted) == set(inventory), sorted(set(inventory) - set(accepted))
    assert set(original_failures) == {
        'tests/microservices/test_rq_engine_upload_disturbed_routes.py::test_upload_sbs_returns_disturbed_fn',
        'tests/wepp/interchange/test_roads_lifecycle.py::test_archive_catalog_guard_and_roads_refresh_complete_without_inversion'}
    assert all(accepted[node] == 'passed' for node in original_failures)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == declaration['source_commit']
    changed = subprocess.check_output(['git', 'diff', head, '--name-only', '--',
        'tests', 'wepppy', 'tools', 'wctl'], cwd=ROOT, text=True).splitlines()
    assert not [p for p in changed if p.endswith(('.py', '.toml', '.js', '.ts'))], changed
    identities = {name: sha(ROOT / 'wepp_runner/bin' / name) for name in declaration['binaries']}
    assert identities == declaration['binaries']
    counts = dict(Counter(accepted.values()))
    receipt = dict(complete_unique_node_coverage=True, collected=12955,
        unique_outcomes=counts, unresolved_failed_nodes=[],
        original_failed_attempts_retained=original_failures,
        original_order_sensitive_upload_defect_remains=True,
        one_uninterrupted_green_suite=False, application_code_or_test_changes=False,
        source_commit=head, binaries=identities, reports=report_receipts,
        duplicate_successful_nodes_counted_once=dict(duplicates),
        extra_passing_subtest_reports_not_added_to_denominator=subtests,
        accepted_node_outcomes={n: dict(outcome=accepted[n], attempts=accepted_attempts[n]) for n in inventory},
        declaration_sha256=sha(declaration_path), completion_declaration_sha256=sha(completion_path),
        diagnosis_sha256=sha(ART / 'revision4-application-failure-independent-review.json'),
        verifier_sha256=sha(Path(__file__)))
    (ART / 'revision4-application-unique-coverage.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'collected': len(inventory), 'unique_outcomes': counts,
                      'duplicates_excluded': sum(duplicates.values()),
                      'original_order_sensitive_upload_defect_remains': True}))


if __name__ == '__main__':
    main()
