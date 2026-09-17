"""Actual S01 receipt/copy/reuse components, with separate real NoDb lock cost.

Uses unchanged retained real/stress fixtures through new disposable copies.
Calls complete implemented helpers in their actual direct/worker order. Native
clone/reset, SBS validation, landuse/soil/WEPP and live RQ transport are excluded.
The separate locked sequence uses real Omni persistence, detached refresh and
Redis locks. Component-only checks do not substitute for whole native runtime.
"""
from collections import defaultdict
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from statistics import mean
import sys
from time import perf_counter, sleep
from unittest.mock import patch
from uuid import uuid4

from wepppy.all_your_base import file_digest
from wepppy.nodb.mods.omni import omni_sbs_freshness as fresh
from wepppy.nodb.mods.omni import omni as omni_module
from wepppy.nodb.mods.omni import omni_mode_build_services as mode_module
from wepppy.nodb.mods.omni import omni_run_orchestration_service as orchestration
from wepppy.rq import omni_rq

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'omni_sbs_implementation_performance.json'
BASELINE = json.loads((ARTIFACTS / 'sbs_receipts_profile_performance_baseline.json').read_text())
ROOT = Path('/wc1/batch') / ('qa-omni-sbs-implementation-' + uuid4().hex[:12])
ROOT.mkdir()
RESULT = {'scope': __doc__, 'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'cache_note': 'Warm filesystem pages; helper-cold and actual eviction are not cold storage.',
          'module_hashes': {}, 'input_fixtures': {}, 'cases': {}, 'gates': [], 'errors': [],
          'limits': ['No native calculation, clone/reset, live HTTP or queued job execution.',
                     'Component gates exclude canonical lock acquisition/refresh/dump; actual checks inside locks are included as equivalent calls.',
                     'Separate real-lock sequence includes invalidation and admission, detached hydration and persistence.',
                     'Lock residence is acquired-context entry through context exit including dump/release; body time is also retained.',
                     'Python read counters cover all main-file payload reads in the changed helper; fixture fast-copy preparation is untimed.']}


def raw_digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            checksum.update(block)
    return checksum.hexdigest()


def version(path):
    info = Path(path).stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


for module in (file_digest, fresh, omni_module, mode_module, orchestration, omni_rq):
    path = Path(module.__file__)
    RESULT['module_hashes'][str(path)] = raw_digest(path)
    (ROOT / path.name).write_bytes(path.read_bytes())

protected = [Path(item['source']) for item in BASELINE['cases'].values()]


def is_protected(value):
    if not isinstance(value, (str, bytes, os.PathLike)):
        return False
    path = Path(os.fsdecode(value)).absolute()
    return str(path).startswith('/wc1/runs/') or path in protected


def audit(event, args):
    if event == 'open' and is_protected(args[0]):
        access, flags = args[1], args[2]
        if (access and any(c in access for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('Benchmark input writes prohibited')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(is_protected(value) for value in args[:2]):
            raise PermissionError('Benchmark input mutation prohibited')


sys.addaudithook(audit)
reads = defaultdict(int)
digest_calls = []
lock_records = []
real_open, real_digest = Path.open, fresh.sha256_file
real_locked = omni_module.Omni.locked


class CountedStream:
    def __init__(self, stream, path):
        self.stream, self.path = stream, path
    def __enter__(self):
        self.stream.__enter__()
        return self
    def __exit__(self, *args):
        return self.stream.__exit__(*args)
    def __getattr__(self, key):
        return getattr(self.stream, key)
    def read(self, *args, **kwargs):
        block = self.stream.read(*args, **kwargs)
        reads[str(self.path)] += len(block)
        return block


def counted_open(path, *args, **kwargs):
    stream = real_open(path, *args, **kwargs)
    access = args[0] if args else kwargs.get('mode', 'r')
    if access == 'rb' and path.is_relative_to(ROOT) and path.suffix == '.tif':
        return CountedStream(stream, path)
    return stream


def counted_digest(path, **kwargs):
    digest_calls.append(str(path))
    return real_digest(path, **kwargs)


@contextmanager
def timed_locked(owner, *args, **kwargs):
    start = perf_counter()
    with real_locked(owner, *args, **kwargs):
        acquired = perf_counter()
        yield
        body_done = perf_counter()
    end = perf_counter()
    lock_records.append({'acquire_ms': (acquired-start)*1000,
                         'body_ms': (body_done-acquired)*1000,
                         'acquired_to_exit_ms': (end-acquired)*1000,
                         'total_ms': (end-start)*1000})


def flush():
    value = json.dumps(RESULT, indent=2) + '\n'
    OUTPUT.write_text(value)
    (ROOT / 'benchmark-manifest.json').write_text(value)


def clear_digest():
    file_digest._observed_at.cache_clear()
    file_digest._digest.cache_clear()


pressure_files = [ROOT / 'pressure' / str(i) for i in range(512)]
pressure_files[0].parent.mkdir()
for i, path in enumerate(pressure_files):
    path.write_bytes(f'actual-cache-pressure-{i}'.encode())


def pressure():
    for path in pressure_files:
        file_digest.sha256_file(path)
    sleep(1.05)
    for path in pressure_files:
        file_digest.sha256_file(path)
    assert file_digest._observed_at.cache_info().currsize == 512
    assert file_digest._digest.cache_info().currsize == 512


def measure(case, name, callback, *, repeats=5, prepare=None, budget=None, zero_reads=False):
    samples = []
    for _ in range(repeats):
        if prepare:
            prepare()
        before_reads, before_checks, before_locks = dict(reads), len(digest_calls), len(lock_records)
        start = perf_counter()
        value = callback()
        elapsed = perf_counter()-start
        payload = {path: total-before_reads.get(path, 0) for path, total in reads.items()
                   if total != before_reads.get(path, 0)}
        samples.append({'ms': elapsed*1000, 'main_read_bytes': sum(payload.values()),
                        'reads_by_path': payload, 'digest_check_count': len(digest_calls)-before_checks,
                        'locks': lock_records[before_locks:]})
    row = {'name': name, 'mean_ms': mean(item['ms'] for item in samples), 'samples': samples}
    case['measurements'].append(row)
    if budget is not None:
        RESULT['gates'].append({'case': case['name'], 'operation': name, 'gate': 'mean_ms',
                                'actual': row['mean_ms'], 'maximum': budget, 'pass': row['mean_ms'] <= budget})
    if zero_reads:
        RESULT['gates'].append({'case': case['name'], 'operation': name, 'gate': 'settled_payload_reads',
                                'actual': [s['main_read_bytes'] for s in samples], 'maximum': 0,
                                'pass': all(s['main_read_bytes'] == 0 for s in samples)})
    print(case['name'], name, round(row['mean_ms'], 3), 'ms;',
          [s['main_read_bytes'] for s in samples], 'bytes;',
          [s['digest_check_count'] for s in samples], 'digest checks', flush=True)
    flush()
    return value


try:
    with patch.object(Path, 'open', counted_open), patch.object(fresh, 'sha256_file', counted_digest), \
            patch.object(omni_module.Omni, 'locked', timed_locked):
        for tag, baseline in BASELINE['cases'].items():
            fixture = Path(baseline['source'])
            expected = raw_digest(fixture)
            assert expected == baseline['source_sha256']
            RESULT['input_fixtures'][str(fixture)] = {'version': version(fixture), 'sha256': expected}
            wd = ROOT / ('run-' + tag + '-' + uuid4().hex[:8])
            wd.mkdir()
            owner = omni_module.Omni(str(wd), '0.cfg', run_group='batch', group_name=ROOT.name)
            assert ROOT.name in owner.runid
            upload = Path(owner.omni_dir) / '_limbo/0' / fixture.name
            upload.parent.mkdir(parents=True)
            definition = {'type': 'sbs_map', 'sbs_file_path': str(upload)}
            owner.scenarios = [definition]
            child = fresh.child_source(owner, definition)
            child.parent.mkdir(parents=True)
            child.write_bytes(b'previous private child')
            child.chmod(0o640)
            name = omni_module._scenario_name_from_scenario_definition(definition)
            case = RESULT['cases'][tag] = {'name': tag, 'source': str(fixture),
                'source_bytes': baseline['source_bytes'], 'source_sha256': expected,
                'fixture_note': baseline['fixture_note'], 'owner_wd': str(wd),
                'runid': owner.runid, 'child': str(child), 'measurements': []}
            cold_budget = 200 if tag == 'stress16m' else 30
            execution_budget = 650 if tag == 'stress16m' else 75
            shutil.copy2(fixture, upload)
            signature = fresh.scenario_signature(owner, definition)
            entry = {'signature': signature, 'dependency_sha1': 'unchanged-base-loss',
                     'dependency_target': 'undisturbed', 'timestamp': 1}
            owner.scenario_dependency_tree = {name: entry}

            def reuse():
                current = fresh.scenario_signature(owner, definition)
                guard = fresh.SbsReuse.capture(owner, definition, current)
                guard.validate_admission(owner)
                assert current == signature
                return guard

            for selected_state in ('present_upload', 'consumed_child'):
                if selected_state == 'consumed_child':
                    shutil.copyfile(fixture, child)
                    upload.unlink()
                measure(case, selected_state + '_reuse_cold', reuse, prepare=clear_digest, budget=cold_budget)
                reuse()
                sleep(1.05)
                reuse()
                measure(case, selected_state + '_reuse_settled', reuse, repeats=30, budget=10, zero_reads=True)
                measure(case, selected_state + '_reuse_actual512evicted', reuse, repeats=3,
                        prepare=pressure, budget=cold_budget)
                reuse()
                sleep(1.05)
                reuse()
                measure(case, selected_state + '_reuse_post_eviction_settled', reuse,
                        repeats=10, budget=10, zero_reads=True)

            def prepare_upload():
                shutil.copy2(fixture, upload)
                clear_digest()

            def prepare_settled_upload():
                prepare_upload()
                file_digest.sha256_file(upload)
                sleep(1.05)
                file_digest.sha256_file(upload)

            def execute_component():
                current = fresh.scenario_signature(owner, definition)
                execution = fresh.SbsExecution.capture(definition, current, require_selection=True)
                execution.before_reset(owner)  # Outer scenario boundary.
                execution.before_reset(owner)  # Actual reset callback's locked check.
                execution.copy_to(child)
                execution.validate_admission(owner)  # After native work.
                execution.validate_admission(owner)  # Locked admission equivalent.
                assert execution.receipt['sha256'] == expected and not upload.exists()
                return execution

            measure(case, 'execution_complete_helper_cold', execute_component,
                    prepare=prepare_upload, budget=execution_budget)
            measure(case, 'execution_complete_initial_upload_settled', execute_component,
                    prepare=prepare_settled_upload, repeats=3, budget=execution_budget)
            assert raw_digest(child) == expected and stat.S_IMODE(child.stat().st_mode) == 0o640

            def execute_with_locks():
                current = fresh.scenario_signature(owner, definition)
                execution = fresh.SbsExecution.capture(definition, current, require_selection=True)
                execution.before_reset(owner)
                fresh.invalidate_sbs_association(owner, execution)
                execution.copy_to(child)
                execution.validate_admission(owner)
                actual_entry = {**entry, 'signature': current}
                fresh.admit_sbs_association(owner, execution, name, actual_entry,
                    {'scenario': name, 'status': 'executed', 'reason': 'benchmark'})
                durable = omni_module.Omni.load_detached(owner.wd)
                assert durable.scenario_dependency_tree[name] == actual_entry
                assert durable.scenario_run_state[-1]['status'] == 'executed'

            measure(case, 'execution_with_real_reset_and_admission_locks', execute_with_locks,
                    prepare=prepare_upload, repeats=3)
            signature = owner.scenario_dependency_tree[name]['signature']

            def reuse_with_lock():
                current = fresh.scenario_signature(owner, definition)
                guard = fresh.SbsReuse.capture(owner, definition, current)
                fresh.admit_sbs_association(owner, guard, name, owner.scenario_dependency_tree[name],
                    {'scenario': name, 'status': 'skipped', 'reason': 'benchmark'})

            reuse_with_lock()
            sleep(1.05)
            reuse_with_lock()
            measure(case, 'consumed_reuse_with_real_admission_lock_settled', reuse_with_lock,
                    repeats=5, zero_reads=True)
            case['final_child_sha256'] = raw_digest(child)
            case['final_child_mode'] = oct(stat.S_IMODE(child.stat().st_mode))
            case['source_consumed'] = not upload.exists()
            case['final_run_state_count'] = len(owner.scenario_run_state)
            assert case['final_child_sha256'] == expected and case['source_consumed']
            flush()
    RESULT['completed'] = True
    RESULT['all_gates_pass'] = all(gate['pass'] for gate in RESULT['gates'])
except BaseException as error:
    RESULT['errors'].append({'type': type(error).__name__, 'message': str(error)})
    raise
finally:
    RESULT['inputs_unchanged'] = all(version(path) == tuple(info['version']) and raw_digest(path) == info['sha256']
                                     for path, info in RESULT['input_fixtures'].items())
    RESULT['modules_unchanged'] = all(raw_digest(path) == digest for path, digest in RESULT['module_hashes'].items())
    flush()
    print(json.dumps(RESULT, indent=2), flush=True)
