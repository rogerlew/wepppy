"""Independently bind completed release application coverage without rerunning tests."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

A = Path(__file__).resolve().parent
ROOT = Path('/workdir/wepppy/out/261029-r3-isolated')
RAW = Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-application-evidence')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parsed_counts(line):
    return {key: sum(map(int, re.findall(r'(\d+) ' + pattern + r'\b', line)))
            for key, pattern in [('passed', 'passed'), ('skipped', 'skipped'),
                                 ('failed', 'failed'), ('errors', 'errors?')]}

disposition = json.loads((A / 'application-disposition.json').read_text())
for name, expected in disposition['logs_sha256'].items():
    assert sha(RAW / name) == expected, name
main = (RAW / 'roads-native-funding-r3-application-full-v2.log').read_text()
third = (RAW / 'roads-native-funding-r3-application-shard3-replay-v2.log').read_text()
tail = (RAW / 'roads-native-funding-r3-application-shard2-tail.log').read_text()
original = {}
collected = {}
modules = {}
for i in range(1, 5):
    tag = str(i)
    prefix = r'^\[pytest-shard ' + tag + r'\]\[stdout\] '
    summary = re.findall(prefix + r'(=+.*\d+ passed.*=+)$', main, re.M)
    assert len(summary) == 1, (tag, summary)
    original[tag] = parsed_counts(summary[0])
    counts = re.findall(prefix + r'collected (\d+) items$', main, re.M)
    assert len(counts) == 1
    collected[tag] = int(counts[0])
    modules[tag] = set(re.findall(prefix + r'(tests/\S+\.py)(?=\s)', main, re.M))
assert original == disposition['original_shards']
assert collected == disposition['original_collected']
assert 'No module timing cache for selected files; using file-size weighting.' in main
assert 'tests/weppcloud/test_run_catalog_reader.py .......F' in main
assert "Executable doesn't exist at /ms-playwright/chromium_headless_shell-1194/" in main
assert 'PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers' in tail

def replay(text):
    summaries = re.findall(r'^(=+.*\d+ passed.*=+)$', text, re.M)
    assert len(summaries) == 1
    count = parsed_counts(summaries[0])
    totals = re.findall(r'^collected (\d+) items$', text, re.M)
    assert len(totals) == 1
    assert count['failed'] == count['errors'] == 0
    assert count['passed'] + count['skipped'] == int(totals[0])
    return count, set(re.findall(r'^(tests/\S+\.py)(?=\s)', text, re.M))

r3, m3 = replay(third)
rt, mt = replay(tail)
assert r3 == disposition['replayed_whole_shard3']
assert rt == disposition['replayed_shard2_tail']
assert rt == dict(passed=94, skipped=0, failed=0, errors=0)
assert modules['2'] & mt == {'tests/weppcloud/test_run_catalog_reader.py'}
s2 = dict(passed=original['2']['passed'] + rt['passed'] - 7,
          skipped=original['2']['skipped'] + rt['skipped'], failed=0, errors=0)
assert s2 == disposition['completed_shard2']
accepted = [original['1'], s2, r3, original['4']]
for number, count in enumerate(accepted, 1):
    assert count['passed'] + count['skipped'] == collected[str(number)]
    assert count['failed'] == count['errors'] == 0
total = {key: sum(row[key] for row in accepted) for key in r3}
assert total == disposition['completed_segmented_coverage']
assert total == dict(passed=12536, skipped=367, failed=0, errors=0)
assert sum(collected.values()) == total['passed'] + total['skipped'] == 12903

completed_modules = [modules['1'], modules['2'] | mt, m3, modules['4']]
union = set.union(*completed_modules)
assert sum(map(len, completed_modules)) == len(union) == 761
spec = importlib.util.spec_from_file_location('independent_release_shards', ROOT / 'tools/run_pytest_sharded.py')
sharder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sharder
spec.loader.exec_module(sharder)
planned = sharder.plan_shards([str(ROOT / p) for p in sorted(union)], 4, module_timings={})
for declared, observed in zip(planned, completed_modules, strict=True):
    assert set(declared) == {str(ROOT / p) for p in observed}
selection3 = json.loads((A / 'application-shard3-selection.json').read_text())
selection2 = json.loads((A / 'application-shard2-tail-selection.json').read_text())
assert selection3['files'] == planned[2]
start = planned[1].index(str(ROOT / 'tests/weppcloud/test_run_catalog_reader.py'))
assert selection2['files'] == planned[1][start:]
assert {str(ROOT / p) for p in mt} == set(selection2['files'])

declaration = json.loads((A / 'isolated-application-declaration.json').read_text())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == declaration['base_commit']
status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, text=True)
expected_paths = {f'wepp_runner/bin/{name}{suffix}'
                  for name in declaration['identities'] for suffix in ('', '.json')}
assert {line[3:] for line in status.splitlines()} == expected_paths
assert all(line[:3] == ' M ' for line in status.splitlines())
isolated_hashes = {p: sha(ROOT / p) for p in sorted(expected_paths)}
for name, identity in declaration['identities'].items():
    assert isolated_hashes[f'wepp_runner/bin/{name}'] == identity['binary_sha256']
    assert isolated_hashes[f'wepp_runner/bin/{name}.json'] == identity['sidecar_sha256']

bound = ['application-disposition.json', 'integration-gates.json',
         'application-shard2-tail-selection.json', 'application-shard3-selection.json',
         'isolated-application-declaration.json', 'finalize_application.py',
         'replay_application_shard2_tail.py', 'replay_application_shard3.py',
         'final-integration-independent-readback.json',
         'final-application-independent-review.md', 'review_final_application.py']
receipt = dict(reviewer='Independent Codex AI implementation reviewer', accepted=True,
               scope='Complete segmented isolated application coverage; operational integration accepted separately.',
               completed_coverage=total, collected=collected, completed_module_counts=list(map(len, completed_modules)),
               unique_modules=len(union), no_cross_shard_module_overlap=True,
               deterministic_partition_and_replay_selections_exact=True,
               duplicate_passes_removed=7, one_uninterrupted_green_suite=False,
               unchanged_application_base=head, isolated_files_sha256=isolated_hashes,
               evidence_sha256={p: sha(A / p) for p in bound},
               retained_logs_sha256=disposition['logs_sha256'],
               sharder_source_sha256=sha(ROOT / 'tools/run_pytest_sharded.py'),
               executed_module_sha256={p: sha(ROOT / p) for p in sorted(union)},
               production_deployment=False)
(A / 'final-application-independent-readback.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'accepted': True, 'coverage': total, 'modules': len(union)}))
