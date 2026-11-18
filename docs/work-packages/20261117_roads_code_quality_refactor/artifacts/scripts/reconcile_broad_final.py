"""Exact Roads broad evidence accounting; deliberately retains incomplete acceptance."""
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path

OUT = Path('/tmp/roads-refactor-validation')
ROOT = Path('/home/workdir/wepppy-roads-code-quality')
PACKAGE = ROOT / 'docs/work-packages/20261117_roads_code_quality_refactor/artifacts'
REPLACEMENT = 'broad-replacement-shape-retention-fork'
inputs = {}


def read(name):
    path = OUT / name
    raw = path.read_bytes()
    inputs[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def reports(name):
    path = OUT / name
    raw = path.read_bytes()
    inputs[str(path)] = hashlib.sha256(raw).hexdigest()
    result = defaultdict(list)
    for line in raw.decode().splitlines():
        row = json.loads(line)
        result[row['nodeid']].append(row)
    return result


def module(name):
    path = OUT / name
    inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location(name.replace('.', '_'), path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


observer = module('run_broad_module_replacements.py')
support = module('run_broad_continuation_v5.py')
support.ROOT = ROOT
inventory = read('broad-continuation-v5-inventory.json')
full = inventory['full_nodeids']
assert len(full) == len(set(full)) == 15104
v5_before = read('broad-continuation-v5-source-before.json')
v5_after = read('broad-continuation-v5-source-after.json')
v5_summary = read('broad-continuation-v5-summary.json')
v5_reports = reports('broad-continuation-v5-outcomes.jsonl')
assert inventory['selected_nodeids'] == full[8251:]
assert set(v5_reports) == set(full[8251:])
assert all(observer.phases_complete(v5_reports[node]) for node in full[8251:])
assert v5_summary['pytest_exitstatus'] == v5_summary['qualified_exitstatus'] == 1

prior = support.prior_progress()
canonical = support.qualified_prefix(read('broad-continuation-inventory.json'), full, 3484)
v2 = support.qualified_v2_prefix(full, v5_before)
v3 = support.qualified_v3_prefix(full, v5_before)
canonical_reports = defaultdict(list)
for report in read('prefix-canonical-complete-after.json')['reports']:
    canonical_reports[report['nodeid']].append(report)
v2_reports = reports('broad-continuation-v2-outcomes.jsonl')
v3_reports = reports('broad-continuation-v3-outcomes.jsonl')
evidence = {}


def add(node, outcome, origin, replace=False):
    assert (node in evidence) == replace, (node, replace)
    evidence[node] = {'outcome': outcome, 'origin': origin}


def add_reports(nodes, rows, origin, replace=False):
    for node in nodes:
        assert observer.phases_complete(rows[node]), node
        outcome = observer.node_outcome(rows[node])
        if outcome == 'failed' and any(r['outcome'] == 'failed' and r['when'] != 'call' for r in rows[node]):
            outcome = 'error'
        add(node, outcome, origin, replace)


canonical_nodes = set(canonical['nodeids'])
retained = [node for node in full[:3484] if node not in canonical_nodes]
assert len(retained) == 2947
for index, node in enumerate(full[:3484]):
    if node not in canonical_nodes:
        add(node, {'.': 'passed', 's': 'skipped'}[prior['progress'][index]], 'retrospective_original_prefix')
add_reports(canonical['nodeids'], canonical_reports, 'canonical_prefix')
add_reports(v2['nodeids'], v2_reports, 'completed_v2_prefix')
add_reports(v3['nodeids'], v3_reports, 'completed_v3_prefix')
add_reports(full[8251:], v5_reports, 'v5_diagnostic')
assert set(evidence) == set(full)
before_replacement = dict(Counter(value['outcome'] for value in evidence.values()))

replacement_inventory = read(REPLACEMENT + '-inventory.json')
replacement_summary = read(REPLACEMENT + '-summary.json')
replacement_spec = read(REPLACEMENT + '-spec.json')
replacement_reports = reports(REPLACEMENT + '-outcomes.jsonl')
replacement_before = read(REPLACEMENT + '-source-before.json')
replacement_after = read(REPLACEMENT + '-source-after.json')
assert replacement_inventory['full_nodeids'] == full
selected = [node for node in full if node.split('::')[0] in replacement_spec['modules']]
assert selected == replacement_inventory['selected_nodeids'] and len(selected) == 391
assert set(selected) <= set(full[8251:]) and set(replacement_reports) == set(selected)
assert replacement_summary['eligible_for_review'] and replacement_summary['coverage_complete']
assert replacement_summary['pytest_exitstatus'] == replacement_summary['qualified_exitstatus'] == 0
assert replacement_summary['outcomes'] == {'passed': 391}
assert replacement_before == replacement_after == support.source_manifest()
assert not any(replacement_summary[key] for key in ('source_drift', 'pinned_changed', 'script_changed',
    'support_changed', 'spec_changed', 'runtime_changed', 'environment_changed', 'outside_selection'))
assert read(REPLACEMENT + '-runtime-before.json') == read(REPLACEMENT + '-runtime-after.json')
assert read(REPLACEMENT + '-environment-before.json') == read(REPLACEMENT + '-environment-after.json')
changes = {name for name in v5_before.keys() | replacement_after.keys()
           if v5_before.get(name) != replacement_after.get(name)}
assert changes == set(replacement_spec['approved_source_changes'])
for name, approved in replacement_spec['approved_source_changes'].items():
    assert v5_before[name] == approved['before'] and replacement_after[name] == approved['after']
replaced_counts = dict(Counter(evidence[node]['outcome'] for node in selected))
add_reports(selected, replacement_reports, 'reviewed_complete_module_replacement', replace=True)

drift_path = 'wepppy/wepp/management/scripts/man42_5.man.json'
assert {name for name in v5_before if v5_before[name] != v5_after[name]} == {drift_path}
assert v5_summary['source_drift'] == {drift_path: {'before': v5_before[drift_path], 'after': v5_after[drift_path]}}
assert replacement_after[drift_path] == v5_before[drift_path]
assert v5_before[drift_path] == 'c20bdf210f1a10aac0bfbc6a7e13a51e079ee4057d2236d92ac0d397e69911b0'
assert v5_after[drift_path] == '9ba3c8e1a9961adcb767f7cd7f32ffa21f66bff8ca909d35892720131261017b'


def attribution(node):
    if 'test_unitizer_client_js.py' in node:
        return 'missing_generated_js_bundle', 'baseline_reproduced'
    if 'test_feature_access_routes.py' in node:
        return 'missing_jinja_fixture_global', 'baseline_reproduced'
    if 'test_runs_catalog_contract.py' in node or 'test_run_catalog_reader.py' in node:
        return 'missing_playwright_dependencies', 'baseline_reproduced'
    if 'test_run_catalog_postgres.py' in node:
        return 'catalog_notification_latency', 'isolated_baseline_passed_full_suite_load_inconclusive'
    if 'test_user_preferences_postgres.py' in node:
        return 'postgres_account_kind_schema_missing', 'representative_baseline_setup_error_reproduced'
    raise AssertionError('Unclassified remaining failure: ' + node)


remaining = []
for node in full:
    if evidence[node]['outcome'] in {'failed', 'error', 'incomplete'}:
        category, status = attribution(node)
        remaining.append({'nodeid': node, 'outcome': evidence[node]['outcome'],
                          'class': category, 'attribution_status': status})
assert len(remaining) == 17
counts = dict(Counter(value['outcome'] for value in evidence.values()))
assert counts == {'passed': 14582, 'skipped': 505, 'failed': 9, 'error': 8}
node_path = OUT / 'broad_final_node_evidence.json'
assert not node_path.exists()
node_path.write_text(json.dumps([{'index': i, 'nodeid': node, **evidence[node]}
                                for i, node in enumerate(full)], indent=2) + '\n')
receipt = {
    'acceptance_status': 'incomplete', 'broad_gate_passed': False,
    'coverage': {'unique_collected_nodes': 15104, 'all_nodes_accounted_for': True,
                 'retrospectively_reconstructed_nodes': 2947,
                 'nodes_with_retained_phase_reports': 12157},
    'before_replacement_counts': before_replacement, 'replaced_node_count': 391,
    'replaced_original_outcomes': replaced_counts, 'replacement_outcomes': {'passed': 391},
    'final_counts': counts, 'collection_skips_separate': inventory['collection_skips'],
    'remaining_classes': dict(Counter(row['class'] for row in remaining)),
    'remaining_failures_and_errors': remaining,
    'v5_subtest_outcomes_separate': dict(Counter(row['outcome'] for rows in v5_reports.values()
                                               for row in rows if 'subtest_context' in row)),
    'original_prefix_subtests': 'Original v3 console reports three passed subtests; per-node reports were not retained. Not added to unique item counts.',
    'limitations': [
        'No uninterrupted, single-process full-suite pass; prefix order is retrospective.',
        '2,947 retained original-prefix items used global /tmp retention root; canonical replays use /wc1.',
        'Each continuation/replacement introduces a process boundary; cross-boundary session state is not revalidated.',
        'v5 changed one generated management JSON file. Exact restoration and isolated writer reproduction explain the drift but do not make its integrity gate pass.',
        'Replacement uses reviewed read-only native parser mounts and a shorter AF_UNIX-compatible basetemp; these differ from v5.',
        'Nine failures and eight setup errors remain. Baseline attribution explains scope, not a passing gate.',
    ],
    'v5_source_drift_preserved': v5_summary['source_drift'],
    'final_source_manifest_sha256': inputs[str(OUT / (REPLACEMENT + '-source-after.json'))],
    'node_evidence_path': str(node_path), 'node_evidence_sha256': hashlib.sha256(node_path.read_bytes()).hexdigest(),
    'input_sha256': inputs,
}
target = OUT / 'broad_final_reconciliation.json'
assert not target.exists()
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ('acceptance_status', 'coverage', 'final_counts', 'remaining_classes')}, indent=2))
