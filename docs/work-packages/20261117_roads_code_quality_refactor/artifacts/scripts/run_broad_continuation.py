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
                 'tests/wepp/reports/test_report_cache_freshness.py'}
SOURCE_ROOTS = ('wepppy/', 'wepp_runner/', 'tests/', 'tools/', 'wctl/')
CONFIG_SUFFIXES = {'.toml', '.ini', '.cfg', '.yaml', '.yml', '.json'}
QUALIFICATION = (
    'The prior prefix order is reconstructed retrospectively from stable full '
    'collection, reviewed source deltas, quiet progress and the first failure; '
    'the prior run did not retain per-node reports. The suffix starts in a new '
    'process, so cross-boundary session-state interactions are not revalidated. '
    'This is composite coverage, not an uninterrupted full-suite pass.'
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


class Continuation:
    def __init__(self):
        self.paths = {name: OUT / f'broad-continuation-{name}.{suffix}' for name, suffix in (
            ('inventory', 'json'), ('outcomes', 'jsonl'), ('collection', 'jsonl'),
            ('source-before', 'json'), ('source-after', 'json'), ('summary', 'json'))}
        if any(path.exists() for path in self.paths.values()):
            raise RuntimeError('Refuse to overwrite existing continuation evidence')
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
        failure_index = ids.index(FAILURE)
        if failure_index != self.prior['completed_items']:
            raise RuntimeError(f'Prior item inventory does not reconcile: {failure_index}')
        start = next(i for i, nodeid in enumerate(ids) if nodeid.split('::')[0] == MODULE)
        changed = {name for name in git('diff', '--name-only', PRIOR_REVISION).decode().splitlines()
                   if scoped(name) and Path(name).suffix in {'.py', '.pyi', *CONFIG_SUFFIXES}}
        if changed - FIXTURE_FILES - {CONSTANTS, LEDGER}:
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
        after = source_manifest()
        self.write('source-after', after)
        drift = {name: {'before': self.before.get(name), 'after': after.get(name)}
                 for name in self.before.keys() | after.keys() if self.before.get(name) != after.get(name)}
        script_changed = digest(Path(__file__).read_bytes()) != self.script_sha256
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
        if int(exitstatus) == 0 and (drift or script_changed or missing or outside
                                   or self.inventory is None or counts['failed'] or counts['incomplete']):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
        self.write('summary', dict(
            qualification=QUALIFICATION, pytest_exitstatus=int(exitstatus),
            qualified_exitstatus=int(session.exitstatus), source_drift=drift,
            script_changed=script_changed, selected_node_count=len(self.selected),
            outcomes=dict(counts), missing_teardown=missing, outside_selection=outside,
            source_before_sha256=digest(self.paths['source-before'].read_bytes()),
            source_after_sha256=digest(self.paths['source-after'].read_bytes()),
            inventory_sha256=(digest(self.paths['inventory'].read_bytes()) if self.inventory else None),
            collection_reports=self.collect_reports,
        ))


if __name__ == '__main__':
    os.environ['VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT'] = '/tmp'
    os.environ['MYPY_CACHE_DIR'] = '/tmp/mypy_cache'
    raise SystemExit(pytest.main(
        ['tests', '--maxfail=1', '-q', '--basetemp=' + str(OUT / 'broad-candidate-20261117d')],
        plugins=[Continuation()],
    ))
