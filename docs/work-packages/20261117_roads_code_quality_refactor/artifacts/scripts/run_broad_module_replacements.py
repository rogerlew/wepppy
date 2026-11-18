"""Run reviewed complete-module replacements; retain failures without accepting them."""
from collections import Counter, defaultdict
import hashlib
import importlib.util
from io import open as evidence_open
import json
import os
from pathlib import Path
import re
import sys

import pytest

evidence_json = json.dumps
OUT = Path('/tmp/roads-refactor-validation')
ROOT = Path('/workdir/wepppy')
SUPPORT = OUT / 'run_broad_continuation_v5.py'
SUPPORT_SHA256 = 'e1baeb2bfcd91c4eb698c8690e65471389e5b2ac6fde353b870264e24b476f2a'
EXPECTED_ENV = {'VECTOR_UPLOAD_RUN_FILESYSTEM_ID': 'dev-wc1',
                'VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT': '/wc1'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_support():
    if digest(SUPPORT.read_bytes()) != SUPPORT_SHA256:
        raise RuntimeError('Source-manifest support differs from the reviewed v5 runner')
    spec = importlib.util.spec_from_file_location('frozen_roads_manifest_support', SUPPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    return module


def node_outcome(rows):
    ordinary = [row for row in rows if 'subtest_context' not in row]
    setup = [row for row in ordinary if row['when'] == 'setup']
    call = [row for row in ordinary if row['when'] == 'call']
    teardown = [row for row in ordinary if row['when'] == 'teardown']
    if any(row['outcome'] == 'failed' for row in rows):
        return 'failed'
    if (len(setup) != 1 or len(teardown) != 1 or teardown[0]['outcome'] != 'passed'
            or len(ordinary) != len(setup) + len(call) + len(teardown)):
        return 'incomplete'
    if setup[0]['outcome'] == 'skipped' and not call:
        return 'xfailed' if 'wasxfail' in setup[0] else 'skipped'
    if setup[0]['outcome'] != 'passed' or len(call) != 1:
        return 'incomplete'
    report = call[0]
    if report['outcome'] == 'skipped':
        return 'xfailed' if 'wasxfail' in report else 'skipped'
    if report['outcome'] == 'passed':
        return 'xpassed' if 'wasxfail' in report else 'passed'
    return 'incomplete'


def phases_complete(rows):
    ordinary = [row for row in rows if 'subtest_context' not in row]
    setup = [row for row in ordinary if row['when'] == 'setup']
    call = [row for row in ordinary if row['when'] == 'call']
    teardown = [row for row in ordinary if row['when'] == 'teardown']
    return (len(setup) == 1 and len(teardown) == 1
            and len(ordinary) == len(setup) + len(call) + len(teardown)
            and len(call) == (1 if setup[0]['outcome'] == 'passed' else 0))


def runtime_file_identity(entries):
    mounts = Path('/proc/self/mountinfo').read_text().splitlines()
    identities = {}
    for entry in entries:
        path = Path(entry['path'])
        if not path.is_absolute() or not path.is_file():
            raise RuntimeError(f'Reviewed runtime artifact is missing: {path}')
        version = path.stat()
        value = digest(path.read_bytes())
        if value != entry['sha256']:
            raise RuntimeError(f'Reviewed runtime artifact bytes differ: {path}')
        mount = None
        for line in mounts:
            fields = line.split()
            if fields[4] == str(path):
                separator = fields.index('-')
                mount = {'mount_point': fields[4], 'mount_root': fields[3],
                         'mount_options': fields[5].split(','),
                         'filesystem_type': fields[separator + 1]}
                break
        if entry.get('require_readonly_mount') and (mount is None or 'ro' not in mount['mount_options']):
            raise RuntimeError(f'Runtime artifact is not an exact read-only mount: {path}')
        identities[str(path)] = {'sha256': value, 'bytes': version.st_size,
                                 'mtime_ns': version.st_mtime_ns, 'mode': version.st_mode,
                                 'executable': os.access(path, os.X_OK), 'mount': mount}
    return identities


class ReplacementRun:
    def __init__(self, spec_path):
        self.spec_path = spec_path
        self.spec_bytes = spec_path.read_bytes()
        self.spec = json.loads(self.spec_bytes)
        self.label = self.spec['label']
        if not re.fullmatch(r'broad-replacement-[a-z0-9_-]+', self.label):
            raise ValueError('Use a unique broad-replacement-* label')
        self.modules = self.spec['modules']
        if (not self.modules or len(set(self.modules)) != len(self.modules)
                or any(not name.startswith('tests/') or not name.endswith('.py') for name in self.modules)):
            raise ValueError('Select explicit unique test modules')
        self.paths = {name: OUT / f'{self.label}-{name}.{suffix}' for name, suffix in (
            ('inventory', 'json'), ('outcomes', 'jsonl'), ('collection', 'jsonl'),
            ('source-before', 'json'), ('source-after', 'json'), ('summary', 'json'),
            ('environment-before', 'json'), ('environment-after', 'json'),
            ('runtime-before', 'json'), ('runtime-after', 'json'))}
        self.basetemp = Path(self.spec.get('basetemp', str(OUT / f'{self.label}-basetemp')))
        if 'basetemp' in self.spec and (self.basetemp.parent != Path('/tmp')
                or not re.fullmatch(r'roads-rpl-[a-z0-9-]+', self.basetemp.name)
                or len(str(self.basetemp)) > 40):
            raise ValueError('Explicit short basetemp must be a unique /tmp/roads-rpl-* path')
        if self.basetemp.exists() or any(path.exists() for path in self.paths.values()):
            raise RuntimeError('Refuse to overwrite replacement evidence or basetemp')
        self.environment_expected = dict(EXPECTED_ENV)
        for name, value in self.spec.get('runtime_environment', {}).items():
            if name in EXPECTED_ENV and value != EXPECTED_ENV[name]:
                raise ValueError('Runtime review cannot override canonical retention configuration')
            self.environment_expected[name] = value
        self.environment = {name: os.environ.get(name) for name in self.environment_expected}
        if self.environment != self.environment_expected:
            raise RuntimeError('Replacement environment is not canonical')
        self.runtime_files = self.spec.get('runtime_files', [])
        if (len({entry['path'] for entry in self.runtime_files}) != len(self.runtime_files)
                or (self.runtime_files and not self.spec.get('runtime_delta_review'))):
            raise ValueError('Runtime files require unique paths and explicit reviewed attribution')
        self.runtime_before = runtime_file_identity(self.runtime_files)
        self.pinned = dict(self.spec['evidence_files_sha256'])
        for key in ('reference_inventory', 'reference_source'):
            self.pinned[self.spec[key]] = self.spec[key + '_sha256']
        self.check_pinned()
        self.reference_inventory = json.loads(Path(self.spec['reference_inventory']).read_text())
        self.reference_sources = json.loads(Path(self.spec['reference_source']).read_text())
        self.support = load_support()
        self.before = self.support.source_manifest()
        self.script_sha256 = digest(Path(__file__).read_bytes())
        self.reports = defaultdict(list)
        self.buffers = defaultdict(list)
        self.collect_reports = []
        self.selected = []
        self.inventory = None
        approved = self.spec['approved_source_changes']
        changed = {name for name in self.reference_sources.keys() | self.before.keys()
                   if self.reference_sources.get(name) != self.before.get(name)}
        if changed != set(approved) or not changed <= set(self.modules):
            raise RuntimeError('Source changes exceed the reviewed selected-module transitions')
        for name, review in approved.items():
            if (not review['review'] or self.reference_sources[name] != review['before']
                    or self.before[name] != review['after']):
                raise RuntimeError(f'Reviewed source transition differs: {name}')
        self.write('source-before', self.before)
        self.write('environment-before', self.environment)
        self.write('runtime-before', self.runtime_before)

    def check_pinned(self):
        for name, expected in self.pinned.items():
            if digest(Path(name).read_bytes()) != expected:
                raise RuntimeError(f'Reference evidence changed: {name}')

    def write(self, name, payload):
        with evidence_open(str(self.paths[name]), 'w', encoding='utf-8') as stream:
            stream.write(evidence_json(payload, indent=2) + '\n')

    def pytest_collectreport(self, report):
        if not report.passed:
            self.collect_reports.append({'nodeid': report.nodeid, 'outcome': report.outcome,
                                         'reason': str(report.longrepr)})

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_collection_modifyitems(self, config, items):
        yield
        ids = [item.nodeid for item in items]
        if ids != self.reference_inventory['full_nodeids'] or len(ids) != len(set(ids)):
            raise RuntimeError('Complete ordered test inventory differs from the diagnostic')
        expected_collection = self.reference_inventory['collection_skips']
        if self.collect_reports != expected_collection:
            raise RuntimeError('Collection skips/errors differ from the diagnostic')
        selected_items = [item for item in items if item.nodeid.split('::')[0] in self.modules]
        self.selected = [item.nodeid for item in selected_items]
        if {node.split('::')[0] for node in self.selected} != set(self.modules):
            raise RuntimeError('A requested replacement module collected no items')
        selected_set = set(self.selected)
        removed = [item for item in items if item.nodeid not in selected_set]
        self.inventory = {
            'purpose': self.spec['purpose'], 'acceptance_claim': None,
            'qualification': 'Complete-module replacement evidence; no automatic composite acceptance.',
            'spec_path': str(self.spec_path), 'spec_sha256': digest(self.spec_bytes),
            'specification': self.spec, 'script_sha256': self.script_sha256,
            'support_sha256': SUPPORT_SHA256, 'current_head': self.support.git('rev-parse', 'HEAD').decode().strip(),
            'python': sys.version, 'pytest': pytest.__version__, 'maxfail': 0,
            'basetemp': str(self.basetemp),
            'plugins': [{'name': dist.project_name, 'version': dist.version}
                        for _, dist in config.pluginmanager.list_plugin_distinfo()],
            'environment': self.environment, 'full_nodeids': ids,
            'runtime_inputs': self.runtime_before,
            'runtime_delta_review': self.spec.get('runtime_delta_review'),
            'selected_nodeids': self.selected, 'deselected_nodeids': [item.nodeid for item in removed],
            'collection_reports': self.collect_reports,
        }
        self.write('inventory', self.inventory)
        items[:] = selected_items
        config.hook.pytest_deselected(items=removed)

    def pytest_runtest_logreport(self, report):
        row = {'nodeid': report.nodeid, 'when': report.when, 'outcome': report.outcome,
               'report_type': type(report).__name__}
        if hasattr(report, 'wasxfail'):
            row['wasxfail'] = str(report.wasxfail)
        if hasattr(report, 'context'):
            row['subtest_context'] = repr(report.context)
        self.reports[report.nodeid].append(row)
        self.buffers['outcomes'].append(row)

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session, exitstatus):
        self.buffers['collection'] = self.collect_reports
        for name in ('outcomes', 'collection'):
            with evidence_open(str(self.paths[name]), 'w', encoding='utf-8') as stream:
                for row in self.buffers[name]:
                    stream.write(evidence_json(row) + '\n')
        after = self.support.source_manifest()
        environment_after = {name: os.environ.get(name) for name in self.environment_expected}
        runtime_after = runtime_file_identity(self.runtime_files)
        self.write('source-after', after)
        self.write('environment-after', environment_after)
        self.write('runtime-after', runtime_after)
        drift = {name: {'before': self.before.get(name), 'after': after.get(name)}
                 for name in self.before.keys() | after.keys() if self.before.get(name) != after.get(name)}
        pinned_changed = [name for name, expected in self.pinned.items()
                          if digest(Path(name).read_bytes()) != expected]
        script_changed = digest(Path(__file__).read_bytes()) != self.script_sha256
        support_changed = digest(SUPPORT.read_bytes()) != SUPPORT_SHA256
        spec_changed = self.spec_path.read_bytes() != self.spec_bytes
        outside = sorted(set(self.reports) - set(self.selected))
        outcomes = {node: node_outcome(self.reports[node]) for node in self.selected}
        counts = Counter(outcomes.values())
        runtime_changed = runtime_after != self.runtime_before
        integrity_ok = not (drift or pinned_changed or script_changed or support_changed or spec_changed or runtime_changed
                            or outside or environment_after != self.environment or self.inventory is None)
        coverage_complete = (bool(self.selected) and not outside
                             and all(phases_complete(self.reports[node]) for node in self.selected))
        if int(exitstatus) == 0 and (not integrity_ok or not coverage_complete or counts['failed']):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
        self.write('summary', {
            'acceptance_claim': None, 'pytest_exitstatus': int(exitstatus),
            'qualified_exitstatus': int(session.exitstatus), 'coverage_complete': coverage_complete,
            'eligible_for_review': int(session.exitstatus) == 0 and integrity_ok and coverage_complete,
            'source_drift': drift, 'pinned_changed': pinned_changed, 'script_changed': script_changed,
            'support_changed': support_changed, 'spec_changed': spec_changed,
            'runtime_changed': runtime_changed,
            'environment_changed': environment_after != self.environment,
            'selected_node_count': len(self.selected), 'outcomes': dict(counts),
            'per_node_outcome': outcomes, 'outside_selection': outside,
            'subtest_outcomes': dict(Counter(row['outcome'] for row in self.buffers['outcomes']
                                            if 'subtest_context' in row)),
            'collection_reports': self.collect_reports,
            'source_before_sha256': digest(self.paths['source-before'].read_bytes()),
            'source_after_sha256': digest(self.paths['source-after'].read_bytes()),
            'inventory_sha256': digest(self.paths['inventory'].read_bytes()) if self.inventory else None,
        })


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: run_broad_module_replacements.py ABSOLUTE_REVIEWED_SPEC.json')
    plugin = ReplacementRun(Path(sys.argv[1]))
    os.environ['MYPY_CACHE_DIR'] = '/tmp/mypy_cache'
    raise SystemExit(pytest.main(['tests', '--maxfail=0', '-q', '--basetemp=' + str(plugin.basetemp)],
                                plugins=[plugin]))
