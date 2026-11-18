"""Retrospectively qualify broad coverage; not an uninterrupted full-suite pass."""
from collections import Counter, defaultdict
import ast
import hashlib
from io import open as evidence_open
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

evidence_json = json.dumps

ROOT = Path('/workdir/wepppy')
OUT = Path('/tmp/roads-refactor-validation')
MODULE = 'tests/nodb/mods/geneva/test_geneva_cache_freshness.py'
RESUME_MODULE = 'tests/nodb/test_derived_file_signature.py'
QUEUE_MODULE = 'tests/rq/test_batch_deferred_recovery.py'
QUEUE_SOURCE_BEFORE = '2ea4b9d244889061dad363cd37ff9169a5d5118de6d8c5e349b4b71499f80355'
QUEUE_SOURCE_AFTER = '823469a8b90c95607c1bd6a468dfceaf9cccdeb4dc7f2e0a535e97914aaad5cd'
FAILURE = MODULE + '::test_canonical_archive_preserves_geneva_failed_and_accepted_work'
PRIOR_REVISION = '43cb4e78fcaca24f608eef6246f8ed5292f096ca'
CONSTANTS = 'wepppy/nodb/mods/roads/_constants.py'
LEDGER = 'tests/roads/analysis_staleness_current.json'
LEDGER_SHA256 = '336aa0a5c43c21d0fb2154b54e4e0a469b9c8fda1a79ef7fdec663d03acee7a6'
FIXTURE_FILES = {MODULE, 'tests/nodb/test_cli_parquet_lineage.py',
                 'tests/wepp/reports/test_report_cache_freshness.py',
                 'tests/weppcloud/routes/test_roads_bp.py', QUEUE_MODULE}
PREFIX_FIXTURE_FILES = {
    'tests/microservices/test_rq_engine_ag_fields_routes.py',
    'tests/microservices/test_rq_engine_omni_routes.py',
    'tests/microservices/test_rq_engine_upload_batch_runner_routes.py',
    'tests/microservices/test_vector_upload_normalization.py',
}
PREFIX_RECEIPT = OUT / 'prefix-canonical-complete-after.json'
PREFIX_RECEIPT_SHA256 = '6bbd6a44b9cb773a9ba75f9cf8fbc35c089427f9a0043c7faebf8228733638ec'
EXPECTED_ENV = {'VECTOR_UPLOAD_RUN_FILESYSTEM_ID': 'dev-wc1',
                'VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT': '/wc1'}
V2_EVIDENCE = {
    'run_broad_continuation_v2.py': 'ca4c2eada6dea587c522a1b86ac035473c6eabe95842bea09e1ee21d6d68887e',
    'broad-continuation-v2-inventory.json': '720e497e151cbaa53556cc6ccddf3271332a35f2d25af422a4399856c7981058',
    'broad-continuation-v2-outcomes.jsonl': '938aa3acfe54761718198f907beebc2d7feb61e6b66f2f5235a309be72e9f2d1',
    'broad-continuation-v2-source-before.json': '6d243df4263ff191c414d41974b5e9aab2f7a8f12c3e2bdffef549ed915a9edf',
    'broad-continuation-v2-environment-before.json': '1cccb01c3c26ede8f172f8fb494a92e037958a9d56a3906d0924ad02a43e317a',
    'broad-continuation-v2-collection.jsonl': 'a97170a01f90b1b13f5983608e12050f468363445573e06adc92f167d1a761dc',
    'broad-continuation-v2.log': 'a19307dafecc66626cb12fd2727f87126de19fd062d1769810d5946d4d8c0010',
    'broad-continuation-v2-postexit-source-receipt.json': '7cd6b643197373bc6c43ae665a0ed53e117282e2eba76e734cd81c21e7db7f4b',
    'broad-continuation-v2-postexit-source-after.json': '6d243df4263ff191c414d41974b5e9aab2f7a8f12c3e2bdffef549ed915a9edf',
}
V3_EVIDENCE = {
    'run_broad_continuation_v3.py': '80f94084f65d170b94688687e748674062d0e2aeb9ce55fb72c14f525fdcc249',
    'broad-continuation-v3-inventory.json': '6e52047556bbbae5d88dd727ddca6b3ccc19bb07015097f0484ed52bb91e370d',
    'broad-continuation-v3-summary.json': '998dea26cfc939a9cfa5045f0336148840ec021f4b1f5365b0120f7c5d838209',
    'broad-continuation-v3-outcomes.jsonl': '884e24a4f0144a96da0b5c727dd520e217667e60f25c6da9c9b3544c472fc9d3',
    'broad-continuation-v3-source-before.json': '6d243df4263ff191c414d41974b5e9aab2f7a8f12c3e2bdffef549ed915a9edf',
    'broad-continuation-v3-source-after.json': '6d243df4263ff191c414d41974b5e9aab2f7a8f12c3e2bdffef549ed915a9edf',
    'broad-continuation-v3-environment-before.json': '1cccb01c3c26ede8f172f8fb494a92e037958a9d56a3906d0924ad02a43e317a',
    'broad-continuation-v3-environment-after.json': '1cccb01c3c26ede8f172f8fb494a92e037958a9d56a3906d0924ad02a43e317a',
    'broad-continuation-v3-collection.jsonl': 'a97170a01f90b1b13f5983608e12050f468363445573e06adc92f167d1a761dc',
    'broad-continuation-v3.log': 'd7a684a1531f1760053b6cf543c21d81d5a1a7815920f481ce5d062e22437044',
}
SOURCE_ROOTS = ('wepppy/', 'wepp_runner/', 'tests/', 'tools/', 'wctl/')
CONFIG_SUFFIXES = {'.toml', '.ini', '.cfg', '.yaml', '.yml', '.json'}
QUALIFICATION = (
    'The prior prefix order is reconstructed retrospectively from stable full '
    'collection, reviewed source deltas, quiet progress and the first failure; '
    'the prior run did not retain per-node reports. The suffix starts in a new '
    'process, so cross-boundary session-state interactions are not revalidated. '
    'The retained prefix used root /tmp; this suffix inherits canonical dev-wc1,/wc1. '
    'Targeted canonical prefix tests qualify environment-sensitive paths separately. '
    'A completed canonical v2 prefix is retained through the module before the '
    'observer interruption; its source equivalence was checked in a fresh process. '
    'All derived-signature module items are rerun with a buffered observer. '
    'The complete v3 prefix before batch-deferred recovery is retained; its '
    'source and environment fingerprints match before/after execution. The '
    'batch-deferred module is rerun after the reviewed private-queue fixture repair. '
    'This is mixed-environment composite coverage, not an uninterrupted full-suite pass.'
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def scoped(name):
    return name.startswith(SOURCE_ROOTS) or '/' not in name


def source_manifest():
    names = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')
    selected = {name for name in names if name and scoped(name) and (
        Path(name).suffix in {'.py', '.pyi', *CONFIG_SUFFIXES}
        or ('/' not in name and (name.startswith('requirements') or name.endswith('.lock')))
    )}
    result = {}
    for name in sorted(selected):
        path = ROOT / name
        if path.is_symlink():
            result[name] = {'symlink': os.readlink(path),
                            'target_sha256': digest(path.read_bytes()) if path.is_file() else None}
        else:
            result[name] = digest(path.read_bytes()) if path.is_file() else {'missing': True}
    return result


def prior_progress():
    data = (OUT / 'broad-final-v3.log').read_bytes()
    text = data.decode()
    prefix = re.split(r'^=+ FAILURES =+$', text, flags=re.M)[0]
    progress = ''.join(match.group(1) for line in prefix.splitlines()
                      if (match := re.fullmatch(r'([.sFExX]+)(?:\s+\[\s*\d+%\])?', line)))
    summary = next(line for line in reversed(text.splitlines())
                   if re.match(r'^1 failed, 3341 passed, 155 skipped,', line))
    if Counter(progress) != Counter({'.': 3341, 's': 154, 'F': 1}) or not progress.endswith('F'):
        raise RuntimeError('Prior progress does not reconcile with reviewed first-failure evidence')
    if f'FAILED {FAILURE}' not in text:
        raise RuntimeError('Prior failure identity changed')
    return dict(log=str(OUT / 'broad-final-v3.log'), sha256=digest(data), summary=summary,
                progress=progress, passed=3341, runtime_skipped=154,
                collection_skipped=1, completed_items=len(progress) - 1)


def qualified_prefix(earlier, full_ids, start):
    raw = PREFIX_RECEIPT.read_bytes()
    if digest(raw) != PREFIX_RECEIPT_SHA256:
        raise RuntimeError('Canonical prefix receipt differs from reviewed evidence')
    receipt = json.loads(raw)
    selection = json.loads((OUT / 'canonical-prefix-sensitive-modules.json').read_text())
    nodes = receipt['nodeids']
    if (receipt['exitstatus'] != 0 or receipt['environment'] != EXPECTED_ENV
            or not receipt['source_unchanged'] or len(nodes) != 537 or len(set(nodes)) != 537
            or nodes != selection['nodeids'] or receipt['modules'] != selection['modules']):
        raise RuntimeError('Canonical prefix status/environment/item inventory is unqualified')
    expected = [node for node in full_ids[:start] if node.split('::')[0] in receipt['modules']]
    if nodes != expected or earlier['deselected_prefix_nodeids'] != full_ids[:start]:
        raise RuntimeError('Canonical prefix does not exactly replace the selected prior nodes')
    expected_files = set(receipt['modules']) | {'tests/conftest.py', 'tests/microservices/conftest.py', 'pyproject.toml'}
    before, after = receipt['source_sha256_before'], receipt['source_sha256_after']
    if set(before) != expected_files or before != after or any(
            digest((ROOT / name).read_bytes()) != value for name, value in after.items()):
        raise RuntimeError('Canonical prefix source fingerprints differ from frozen current files')
    reports = defaultdict(list)
    for report in receipt['reports']:
        reports[report['nodeid']].append(report)
    if set(reports) != set(nodes):
        raise RuntimeError('Canonical prefix outcomes omit or add test items')
    totals = Counter()
    for node in nodes:
        phases = reports[node]
        setup = [r for r in phases if r['when'] == 'setup']
        call = [r for r in phases if r['when'] == 'call']
        teardown = [r for r in phases if r['when'] == 'teardown']
        if (len(setup) != 1 or len(teardown) != 1 or teardown[0]['outcome'] != 'passed'
                or len(phases) != len(setup) + len(call) + len(teardown)):
            raise RuntimeError(f'Incomplete canonical prefix phases: {node}')
        if setup[0]['outcome'] == 'skipped' and not call:
            totals['skipped'] += 1
        elif setup[0]['outcome'] == 'passed' and len(call) == 1 and call[0]['outcome'] in {'passed', 'skipped'}:
            totals[call[0]['outcome']] += 1
        else:
            raise RuntimeError(f'Unqualified canonical prefix outcome: {node}')
    if totals != Counter(passed=508, skipped=29):
        raise RuntimeError('Canonical prefix outcome totals differ from reviewed receipt')
    return {'receipt': str(PREFIX_RECEIPT), 'sha256': PREFIX_RECEIPT_SHA256,
            'nodeids': nodes, 'outcomes': dict(totals), 'source_sha256': after}


def sources_match_reviewed_repair(reference, current):
    changed = {name for name in reference.keys() | current.keys()
               if reference.get(name) != current.get(name)}
    return (changed == {QUEUE_MODULE} and reference[QUEUE_MODULE] == QUEUE_SOURCE_BEFORE
            and current[QUEUE_MODULE] == QUEUE_SOURCE_AFTER)


def qualified_v2_prefix(full_ids, current_sources):
    for name, expected in V2_EVIDENCE.items():
        if digest((OUT / name).read_bytes()) != expected:
            raise RuntimeError(f'Frozen v2 evidence changed: {name}')
    inventory = json.loads((OUT / 'broad-continuation-v2-inventory.json').read_text())
    before = json.loads((OUT / 'broad-continuation-v2-source-before.json').read_text())
    after = json.loads((OUT / 'broad-continuation-v2-postexit-source-after.json').read_text())
    receipt = json.loads((OUT / 'broad-continuation-v2-postexit-source-receipt.json').read_text())
    if (inventory['full_nodeids'] != full_ids or before != after
            or not sources_match_reviewed_repair(after, current_sources)
            or receipt['environment'] != EXPECTED_ENV or not receipt['source_unchanged']
            or receipt['changed_paths'] or receipt['before_files'] != 2836
            or receipt['after_files'] != 2836
            or inventory['inherited_retention_environment'] != EXPECTED_ENV
            or receipt['frozen_observer_sha256'] != V2_EVIDENCE['run_broad_continuation_v2.py']):
        raise RuntimeError('Fresh v2 source/environment equivalence is unqualified')
    start = next(i for i, node in enumerate(full_ids) if node.split('::')[0] == RESUME_MODULE)
    old_start = inventory['start_module_index']
    nodes = full_ids[old_start:start]
    if start != 6005 or old_start != 3484 or len(nodes) != 2521:
        raise RuntimeError('v2 completed-prefix boundary differs from reviewed inventory')
    rows = [json.loads(line) for line in (OUT / 'broad-continuation-v2-outcomes.jsonl').read_text().splitlines()]
    by_node = defaultdict(list)
    for row in rows:
        by_node[row['nodeid']].append(row)
    if list(by_node)[:len(nodes)] != nodes:
        raise RuntimeError('v2 observed order differs from the exact retained prefix')
    totals = Counter()
    for node in nodes:
        phases = by_node[node]
        shape = [(r['when'], r['outcome'], r['report_type']) for r in phases]
        if shape == [('setup', 'passed', 'TestReport'), ('call', 'passed', 'TestReport'),
                     ('teardown', 'passed', 'TestReport')]:
            totals['passed'] += 1
        elif shape == [('setup', 'skipped', 'TestReport'), ('teardown', 'passed', 'TestReport')]:
            totals['skipped'] += 1
        else:
            raise RuntimeError(f'Incomplete or failed v2 prefix item: {node}')
    if totals != Counter(passed=2518, skipped=3):
        raise RuntimeError('v2 completed-prefix outcomes differ from reviewed evidence')
    excluded = list(by_node)[len(nodes):]
    if any(node.split('::')[0] != RESUME_MODULE for node in excluded):
        raise RuntimeError('Unexpected v2 outcomes beyond the retained prefix')
    return {'evidence_sha256': V2_EVIDENCE, 'nodeids': nodes, 'outcomes': dict(totals),
            'excluded_interrupted_module_nodeids': excluded, 'resume_index': start}


def qualified_v3_prefix(full_ids, current_sources):
    for name, expected in V3_EVIDENCE.items():
        if digest((OUT / name).read_bytes()) != expected:
            raise RuntimeError(f'Frozen v3 evidence changed: {name}')
    inventory = json.loads((OUT / 'broad-continuation-v3-inventory.json').read_text())
    summary = json.loads((OUT / 'broad-continuation-v3-summary.json').read_text())
    before = json.loads((OUT / 'broad-continuation-v3-source-before.json').read_text())
    after = json.loads((OUT / 'broad-continuation-v3-source-after.json').read_text())
    env_before = json.loads((OUT / 'broad-continuation-v3-environment-before.json').read_text())
    env_after = json.loads((OUT / 'broad-continuation-v3-environment-after.json').read_text())
    if (inventory['full_nodeids'] != full_ids or before != after
            or not sources_match_reviewed_repair(after, current_sources)
            or env_before != EXPECTED_ENV or env_after != EXPECTED_ENV
            or summary['pytest_exitstatus'] != 1 or summary['qualified_exitstatus'] != 1
            or summary['source_drift'] or summary['script_changed'] or summary['environment_changed']
            or summary['canonical_prefix_receipt_changed'] or summary['v2_evidence_changed']):
        raise RuntimeError('v3 prior-run source, environment or exit evidence is unqualified')
    start = next(i for i, node in enumerate(full_ids) if node.split('::')[0] == QUEUE_MODULE)
    old_start = inventory['start_module_index']
    nodes = full_ids[old_start:start]
    if start != 8251 or old_start != 6005 or len(nodes) != 2246:
        raise RuntimeError('v3 completed-prefix boundary differs from reviewed inventory')
    rows = [json.loads(line) for line in (OUT / 'broad-continuation-v3-outcomes.jsonl').read_text().splitlines()]
    by_node = defaultdict(list)
    for row in rows:
        by_node[row['nodeid']].append(row)
    if list(by_node)[:len(nodes)] != nodes:
        raise RuntimeError('v3 observed order differs from the exact retained prefix')
    totals = Counter()
    for node in nodes:
        shape = [(r['when'], r['outcome'], r['report_type']) for r in by_node[node]]
        if shape == [('setup', 'passed', 'TestReport'), ('call', 'passed', 'TestReport'),
                     ('teardown', 'passed', 'TestReport')]:
            totals['passed'] += 1
        elif shape in ([('setup', 'skipped', 'TestReport'), ('teardown', 'passed', 'TestReport')],
                       [('setup', 'passed', 'TestReport'), ('call', 'skipped', 'TestReport'),
                        ('teardown', 'passed', 'TestReport')]):
            totals['skipped'] += 1
        else:
            raise RuntimeError(f'Incomplete or failed v3 prefix item: {node}')
    if totals != Counter(passed=2170, skipped=76):
        raise RuntimeError('v3 completed-prefix outcomes differ from reviewed evidence')
    excluded = list(by_node)[len(nodes):]
    if excluded != [full_ids[start]] or excluded[0].split('::')[0] != QUEUE_MODULE:
        raise RuntimeError('Unexpected v3 outcomes beyond the retained prefix')
    return {'evidence_sha256': V3_EVIDENCE, 'nodeids': nodes, 'outcomes': dict(totals),
            'excluded_failed_module_nodeids': excluded, 'resume_index': start,
            'reviewed_source_delta': {QUEUE_MODULE: {'before': QUEUE_SOURCE_BEFORE,
                                                    'after': QUEUE_SOURCE_AFTER}}}


class Continuation:
    def __init__(self, smoke=False):
        self.smoke = smoke
        self.label = 'v4-smoke' if smoke else 'v4'
        self.buffers = defaultdict(list)
        self.paths = {name: OUT / f'broad-continuation-{self.label}-{name}.{suffix}' for name, suffix in (
            ('inventory', 'json'), ('outcomes', 'jsonl'), ('collection', 'jsonl'),
            ('source-before', 'json'), ('source-after', 'json'), ('summary', 'json'),
            ('environment-before', 'json'), ('environment-after', 'json'))}
        if any(path.exists() for path in self.paths.values()):
            raise RuntimeError('Refuse to overwrite existing continuation evidence')
        self.environment = {name: os.environ.get(name) for name in EXPECTED_ENV}
        if self.environment != EXPECTED_ENV:
            raise RuntimeError(f'Canonical retention environment differs: {self.environment}')
        self.write('environment-before', self.environment)
        self.prior = prior_progress()
        self.before = source_manifest()
        self.script_sha256 = digest(Path(__file__).read_bytes())
        self.collect_reports = []
        self.reports = defaultdict(list)
        self.selected = []
        self.inventory = None
        self.write('source-before', self.before)

    def write(self, name, payload):
        with evidence_open(str(self.paths[name]), 'w', encoding='utf-8') as stream:
            stream.write(evidence_json(payload, indent=2) + '\n')

    def append(self, name, payload):
        # Tests patch Path.open and other IO globally while call reports fire.
        # Retain plain rows only; persist after fixture teardown at session end.
        self.buffers[name].append(payload)

    def pytest_collectreport(self, report):
        if not report.passed:
            row = {'nodeid': report.nodeid, 'outcome': report.outcome, 'reason': str(report.longrepr)}
            self.collect_reports.append(row)
            self.append('collection', row)

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_collection_modifyitems(self, config, items):
        # Inspect final item order after ordinary collection hooks have run.
        yield
        ids = [item.nodeid for item in items]
        if len(ids) != len(set(ids)):
            raise RuntimeError('Duplicate node IDs cannot qualify exact composite coverage')
        if any(row['outcome'] == 'failed' for row in self.collect_reports):
            raise RuntimeError('Collection errors cannot qualify a continuation')
        skipped = sum(row['outcome'] == 'skipped' for row in self.collect_reports)
        if skipped != self.prior['collection_skipped']:
            raise RuntimeError(f'Collection skips do not reconcile: {skipped}')
        earlier_inventory = OUT / 'broad-continuation-inventory.json'
        earlier = json.loads(earlier_inventory.read_text())
        if ids != earlier['full_nodeids']:
            raise RuntimeError('Full ordered collection differs from first continuation')
        failure_index = ids.index(FAILURE)
        if failure_index != self.prior['completed_items']:
            raise RuntimeError(f'Prior item inventory does not reconcile: {failure_index}')
        start = next(i for i, nodeid in enumerate(ids) if nodeid.split('::')[0] == MODULE)
        prefix_replay = qualified_prefix(earlier, ids, start)
        v2_replay = qualified_v2_prefix(ids, self.before)
        v3_replay = qualified_v3_prefix(ids, self.before)
        replaced = set(prefix_replay['nodeids'])
        retained_prefix = [node for node in ids[:start] if node not in replaced]
        retained_progress = ''.join(self.prior['progress'][i] for i, node in enumerate(ids[:start])
                                    if node not in replaced)
        if len(retained_prefix) != 2947:
            raise RuntimeError('Retained prefix count does not reconcile after canonical substitution')
        changed = {name for name in git('diff', '--name-only', PRIOR_REVISION).decode().splitlines()
                   if scoped(name) and Path(name).suffix in {'.py', '.pyi', *CONFIG_SUFFIXES}}
        if changed - FIXTURE_FILES - PREFIX_FIXTURE_FILES - {CONSTANTS, LEDGER}:
            raise RuntimeError(f'Unreviewed source changes: {sorted(changed)}')
        if digest((ROOT / LEDGER).read_bytes()) != LEDGER_SHA256:
            raise RuntimeError('Historical-staleness ledger differs from reviewed bytes')
        if CONSTANTS in changed:
            original = git('show', f'{PRIOR_REVISION}:{CONSTANTS}')
            current = (ROOT / CONSTANTS).read_bytes()
            if original != current + b'\n\n' or ast.dump(ast.parse(original)) != ast.dump(ast.parse(current)):
                raise RuntimeError('Constants delta exceeds accepted trailing-newline cleanup')
        prefix_files = {nodeid.split('::')[0] for nodeid in ids[:start]}
        if prefix_files & (changed & FIXTURE_FILES):
            raise RuntimeError('Changed fixture module would be excluded from this run')
        paths = sorted({str(Path(item.path).relative_to(ROOT)) for item in items})
        start = v3_replay['resume_index']
        selected_items = ([item for item in items if item.nodeid.split('::')[0] == RESUME_MODULE]
                          if self.smoke else items[start:])
        self.selected = [item.nodeid for item in selected_items]
        if self.smoke and len(self.selected) != 8:
            raise RuntimeError('Observer smoke must contain the entire eight-item module')
        self.inventory = dict(
            qualification=QUALIFICATION, prior=self.prior,
            inherited_retention_environment=self.environment,
            earlier_inventory_sha256=digest(earlier_inventory.read_bytes()),
            canonical_prefix_substitution=prefix_replay,
            canonical_v2_prefix=v2_replay, observer_smoke=self.smoke,
            canonical_v3_prefix=v3_replay,
            retained_prefix_nodeids=retained_prefix,
            retained_prefix_progress=retained_progress,
            retained_prefix_outcomes=dict(Counter(retained_progress)),
            prior_source_revision=PRIOR_REVISION,
            current_head=git('rev-parse', 'HEAD').decode().strip(),
            reviewed_source_deltas=sorted(changed), script_sha256=self.script_sha256,
            python=sys.version, pytest=pytest.__version__,
            plugins=[{'name': dist.project_name, 'version': dist.version}
                     for _, dist in config.pluginmanager.list_plugin_distinfo()],
            prior_failure_index=failure_index, start_module_index=start,
            collection_skips=self.collect_reports, full_nodeids=ids,
            deselected_prefix_nodeids=ids[:start], selected_nodeids=self.selected,
            test_source_sha256={name: digest((ROOT / name).read_bytes()) for name in paths},
        )
        self.write('inventory', self.inventory)
        selected_ids = set(self.selected)
        removed = [item for item in items if item.nodeid not in selected_ids]
        items[:] = selected_items
        config.hook.pytest_deselected(items=removed)

    def pytest_runtest_logreport(self, report):
        row = dict(nodeid=report.nodeid, when=report.when, outcome=report.outcome,
                   report_type=type(report).__name__)
        if hasattr(report, 'wasxfail'):
            row['wasxfail'] = str(report.wasxfail)
        if hasattr(report, 'context'):
            row['subtest_context'] = repr(report.context)
        self.reports[report.nodeid].append(row)
        self.append('outcomes', row)

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session, exitstatus):
        for name in ('outcomes', 'collection'):
            with evidence_open(str(self.paths[name]), 'w', encoding='utf-8') as stream:
                for row in self.buffers[name]:
                    stream.write(evidence_json(row) + '\n')
        environment_after = {name: os.environ.get(name) for name in EXPECTED_ENV}
        self.write('environment-after', environment_after)
        environment_changed = environment_after != self.environment
        after = source_manifest()
        self.write('source-after', after)
        drift = {name: {'before': self.before.get(name), 'after': after.get(name)}
                 for name in self.before.keys() | after.keys() if self.before.get(name) != after.get(name)}
        script_changed = digest(Path(__file__).read_bytes()) != self.script_sha256
        prefix_receipt_changed = digest(PREFIX_RECEIPT.read_bytes()) != PREFIX_RECEIPT_SHA256
        v2_evidence_changed = [name for name, expected in V2_EVIDENCE.items()
                               if digest((OUT / name).read_bytes()) != expected]
        v3_evidence_changed = [name for name, expected in V3_EVIDENCE.items()
                               if digest((OUT / name).read_bytes()) != expected]
        missing = [nodeid for nodeid in self.selected if not any(
            row['when'] == 'teardown' for row in self.reports[nodeid])]
        outside = sorted(set(self.reports) - set(self.selected))
        counts = Counter()
        for nodeid in self.selected:
            rows = self.reports[nodeid]
            if any(row['outcome'] == 'failed' for row in rows):
                counts['failed'] += 1
            elif any(row['outcome'] == 'skipped' and 'subtest_context' not in row for row in rows):
                counts['skipped'] += 1
            elif any(row['when'] == 'call' and row['outcome'] == 'passed'
                     and 'subtest_context' not in row for row in rows):
                counts['passed'] += 1
            else:
                counts['incomplete'] += 1
        if int(exitstatus) == 0 and (drift or script_changed or environment_changed or prefix_receipt_changed or v2_evidence_changed or v3_evidence_changed or missing or outside
                                   or self.inventory is None or counts['failed'] or counts['incomplete']):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
        self.write('summary', dict(
            qualification=QUALIFICATION, pytest_exitstatus=int(exitstatus),
            qualified_exitstatus=int(session.exitstatus), source_drift=drift,
            script_changed=script_changed, environment_changed=environment_changed,
            canonical_prefix_receipt_changed=prefix_receipt_changed,
            v2_evidence_changed=v2_evidence_changed, observer_smoke=self.smoke,
            v3_evidence_changed=v3_evidence_changed,
            inherited_retention_environment=self.environment,
            selected_node_count=len(self.selected),
            outcomes=dict(counts), missing_teardown=missing, outside_selection=outside,
            source_before_sha256=digest(self.paths['source-before'].read_bytes()),
            source_after_sha256=digest(self.paths['source-after'].read_bytes()),
            inventory_sha256=(digest(self.paths['inventory'].read_bytes()) if self.inventory else None),
            collection_reports=self.collect_reports,
        ))


if __name__ == '__main__':
    smoke = sys.argv[1:] == ['--observer-smoke']
    if sys.argv[1:] and not smoke:
        raise RuntimeError('Only --observer-smoke is supported')
    basetemp = OUT / ('broad-candidate-20261117g-smoke' if smoke else 'broad-candidate-20261117g')
    if basetemp.exists():
        raise RuntimeError('Refuse to overwrite an existing continuation basetemp')
    os.environ['MYPY_CACHE_DIR'] = '/tmp/mypy_cache'
    raise SystemExit(pytest.main(
        ['tests', '--maxfail=1', '-q', '--basetemp=' + str(basetemp)],
        plugins=[Continuation(smoke=smoke)],
    ))
