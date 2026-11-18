"""Retrospectively qualify broad coverage; not an uninterrupted full-suite pass."""
from collections import Counter, defaultdict
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path('/workdir/wepppy')
OUT = Path('/tmp/roads-refactor-validation')
MODULE = 'tests/nodb/mods/geneva/test_geneva_cache_freshness.py'
FAILURE = MODULE + '::test_canonical_archive_preserves_geneva_failed_and_accepted_work'
PRIOR_REVISION = '43cb4e78fcaca24f608eef6246f8ed5292f096ca'
CONSTANTS = 'wepppy/nodb/mods/roads/_constants.py'
LEDGER = 'tests/roads/analysis_staleness_current.json'
LEDGER_SHA256 = '336aa0a5c43c21d0fb2154b54e4e0a469b9c8fda1a79ef7fdec663d03acee7a6'
FIXTURE_FILES = {MODULE, 'tests/nodb/test_cli_parquet_lineage.py',
                 'tests/wepp/reports/test_report_cache_freshness.py',
                 'tests/weppcloud/routes/test_roads_bp.py'}
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
SOURCE_ROOTS = ('wepppy/', 'wepp_runner/', 'tests/', 'tools/', 'wctl/')
CONFIG_SUFFIXES = {'.toml', '.ini', '.cfg', '.yaml', '.yml', '.json'}
QUALIFICATION = (
    'The prior prefix order is reconstructed retrospectively from stable full '
    'collection, reviewed source deltas, quiet progress and the first failure; '
    'the prior run did not retain per-node reports. The suffix starts in a new '
    'process, so cross-boundary session-state interactions are not revalidated. '
    'The retained prefix used root /tmp; this suffix inherits canonical dev-wc1,/wc1. '
    'Targeted canonical prefix tests qualify environment-sensitive paths separately. '
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


class Continuation:
    def __init__(self):
        self.paths = {name: OUT / f'broad-continuation-v2-{name}.{suffix}' for name, suffix in (
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
        self.paths[name].write_text(json.dumps(payload, indent=2) + '\n')

    def append(self, name, payload):
        with self.paths[name].open('a') as stream:
            stream.write(json.dumps(payload) + '\n')

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
        self.selected = ids[start:]
        self.inventory = dict(
            qualification=QUALIFICATION, prior=self.prior,
            inherited_retention_environment=self.environment,
            earlier_inventory_sha256=digest(earlier_inventory.read_bytes()),
            canonical_prefix_substitution=prefix_replay,
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
        removed = items[:start]
        items[:] = items[start:]
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

    def pytest_sessionfinish(self, session, exitstatus):
        environment_after = {name: os.environ.get(name) for name in EXPECTED_ENV}
        self.write('environment-after', environment_after)
        environment_changed = environment_after != self.environment
        after = source_manifest()
        self.write('source-after', after)
        drift = {name: {'before': self.before.get(name), 'after': after.get(name)}
                 for name in self.before.keys() | after.keys() if self.before.get(name) != after.get(name)}
        script_changed = digest(Path(__file__).read_bytes()) != self.script_sha256
        prefix_receipt_changed = digest(PREFIX_RECEIPT.read_bytes()) != PREFIX_RECEIPT_SHA256
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
        if int(exitstatus) == 0 and (drift or script_changed or environment_changed or prefix_receipt_changed or missing or outside
                                   or self.inventory is None or counts['failed'] or counts['incomplete']):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
        self.write('summary', dict(
            qualification=QUALIFICATION, pytest_exitstatus=int(exitstatus),
            qualified_exitstatus=int(session.exitstatus), source_drift=drift,
            script_changed=script_changed, environment_changed=environment_changed,
            canonical_prefix_receipt_changed=prefix_receipt_changed,
            inherited_retention_environment=self.environment,
            selected_node_count=len(self.selected),
            outcomes=dict(counts), missing_teardown=missing, outside_selection=outside,
            source_before_sha256=digest(self.paths['source-before'].read_bytes()),
            source_after_sha256=digest(self.paths['source-after'].read_bytes()),
            inventory_sha256=(digest(self.paths['inventory'].read_bytes()) if self.inventory else None),
            collection_reports=self.collect_reports,
        ))


if __name__ == '__main__':
    if (OUT / 'broad-candidate-20261117e').exists():
        raise RuntimeError('Refuse to overwrite an existing continuation basetemp')
    os.environ['MYPY_CACHE_DIR'] = '/tmp/mypy_cache'
    raise SystemExit(pytest.main(
        ['tests', '--maxfail=1', '-q', '--basetemp=' + str(OUT / 'broad-candidate-20261117e')],
        plugins=[Continuation()],
    ))
