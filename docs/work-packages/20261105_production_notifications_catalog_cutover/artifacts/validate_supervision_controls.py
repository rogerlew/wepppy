"""Exercise actual operational controls using disposable Redis and owned processes.

No SSH, production imports, production Redis, or project-data writes are allowed.
Dependency/identity boundaries are injected; guard functions and collector control
flow are compiled from the retained source without rewriting their statements.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import types
from datetime import datetime, timezone

import redis

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
COLLECTOR = HERE / 'observe_general_catalog_supervised.py'
SUPERVISOR = HERE / 'supervise_general_catalog.py'
PROBE = HERE / 'supervision_probe.py'
PAUSE = 'query-catalog:batch-admission:v1:paused'
OWNER = b'production-cutover-20261106:general-observation'
DEADLINE = 1794127194.157908


def functions(path, names):
    return [node for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name in names]


def compile_nodes(nodes, path):
    return compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec')


def write(path, value):
    temporary = path.with_suffix('.writing')
    temporary.write_text(json.dumps(value))
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_supervisor():
    spec = importlib.util.spec_from_file_location('review_supervisor', SUPERVISOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def connection(socket_path):
    return redis.Redis(unix_socket_path=socket_path, socket_timeout=2)


def collector_environment(root, socket_path, clock=time, deadline=None):
    r = connection(socket_path)
    q = types.SimpleNamespace(key='rq:queue:default')

    class Registry:
        def __init__(self, *args, **kwargs):
            pass

        def get_job_ids(self, **kwargs):
            return [value.decode() for value in r.lrange('test:started', 0, -1)]

    env = dict(json=json, os=os, signal=signal, sys=sys, time=clock, math=math,
               socket=socket, datetime=datetime, timezone=timezone, redis=redis,
               root=root, r=r, q=q, owner=OWNER, key='inventory', samples=0,
               ordinary={}, maintenance_seen=set(), target_cycle=None,
               baseline_cycle='old', activation=None, start=clock.time(),
               deadline=deadline if deadline is not None else clock.time() + 90,
               passed=False, manifest={'supervision_nonce': 'review-nonce'},
               StartedJobRegistry=Registry, Any=object,
               cq=types.SimpleNamespace(PREFIX='query_catalog_refresh_',
                   DESCRIPTION='Query catalog maintenance',
                   catalog_worker_configuration=lambda: {'review_only': True},
                   consumer_status=lambda queue: {'compatible': 12, 'incompatible': [], 'suspended': False}),
               cr=types.SimpleNamespace(catalog_refresh_status=lambda path: {}),
               TERMINAL=frozenset({'finished', 'failed', 'stopped', 'canceled'}))
    nodes = functions(COLLECTOR, {'save', 'pause', 'interrupted', 'check_parent', 'arm_sample', 'sample'})
    nodes += functions(REPO / 'tools/query_catalog_pilot.py', {'ordinary_waits'})
    nodes += functions(REPO / 'wepppy/rq/_query_catalog_admission.py', {'execution_uncertain', 'execution_outstanding'})
    exec(compile_nodes(nodes, COLLECTOR), env)
    env['admission'] = types.SimpleNamespace(LEDGER_KEY='ledger', PAUSE_KEY=PAUSE,
        execution_uncertain=env['execution_uncertain'], execution_outstanding=env['execution_outstanding'])
    return env


def control(env):
    nodes = ast.parse(COLLECTOR.read_text()).body
    start = next(index for index, node in enumerate(nodes)
                 if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'reason' for t in node.targets))
    exec(compile_nodes(nodes[start:], COLLECTOR), env)


def receipt(pid, stamp=None, **extra):
    return {'nonce': 'review-nonce', 'observer_pid': pid,
            'worker_hostname': socket.gethostname(), 'time': time.time() if stamp is None else stamp, **extra}


def seed(r):
    r.flushdb()
    r.set(PAUSE, OWNER)
    r.set('ledger', json.dumps({'jobs': {}, 'preserved': 'sentinel'}))
    r.set('inventory', json.dumps({'cycle': 'old', 'cycle_started_at': time.time() - 10, 'pending': []}))
    r.set('inventory:discovery', json.dumps({'cycle': 'old'}))


def child_mode():
    mode, socket_path, directory = sys.argv[2:5]
    root = Path(directory)
    if mode == 'writer':
        pid = int(sys.argv[5])
        while True:
            write(root / 'parent-heartbeat.json', receipt(pid))
            time.sleep(.1)
    env = collector_environment(root, socket_path)
    write(root / 'observer-start.json', {'pid': os.getpid(), 'started_at': env['start']})
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, env['interrupted'])
    control(env)


def run():
    results = []

    def passed(name, **details):
        results.append({'case': name, **details})

    with tempfile.TemporaryDirectory(prefix='catalog-supervision-review-') as directory:
        base = Path(directory)
        socket_path = str(base / 'redis.sock')
        server = subprocess.Popen(['redis-server', '--port', '0', '--unixsocket', socket_path,
                                   '--unixsocketperm', '700', '--save', '', '--appendonly', 'no'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = connection(socket_path)
        owned = []
        try:
            for _ in range(100):
                try:
                    r.ping()
                    break
                except redis.ConnectionError:
                    time.sleep(.02)
            else:
                raise RuntimeError('Disposable Redis did not start')

            # Real child collector and real heartbeat parent. SIGKILL bypasses
            # the parent's cleanup; the unmodified collector checks must pause.
            seed(r)
            root = base / 'hard-exit'
            root.mkdir(mode=0o700)
            log = (root / 'child.log').open('w')
            child = subprocess.Popen([sys.executable, __file__, '--child', 'collector', socket_path, str(root)],
                                     stdout=log, stderr=log)
            owned.append(child)
            parent = subprocess.Popen([sys.executable, __file__, '--child', 'writer', socket_path, str(root), str(child.pid)])
            owned.append(parent)
            limit = time.monotonic() + 10
            while not (root / 'activation.json').exists() and time.monotonic() < limit:
                if child.poll() is not None:
                    raise AssertionError((root / 'child.log').read_text())
                time.sleep(.05)
            assert (root / 'activation.json').exists(), 'Collector did not activate'
            parent.kill()
            parent.wait(timeout=3)
            killed = time.monotonic()
            child.wait(timeout=75)
            stop = json.loads((root / 'stop.json').read_text())
            elapsed = time.monotonic() - killed
            assert child.returncode != 0 and r.get(PAUSE) == OWNER and r.ttl(PAUSE) == -1
            assert elapsed < 60, 'Parent hard-loss containment exceeded its budget'
            assert 'stale' in stop['reason'] and stop['pause_owned'] is True
            assert not (root / 'completed.json').exists()
            assert json.loads(r.get('ledger')) == {'jobs': {}, 'preserved': 'sentinel'}
            passed('actual_parent_sigkill_collector_pauses', seconds_to_stop=elapsed, reason=stop['reason'])
            log.close()

            for name, change in [
                    ('stale_parent', lambda beat: beat.update(time=time.time() - 61)),
                    ('future_parent', lambda beat: beat.update(time=time.time() + 10)),
                    ('wrong_nonce', lambda beat: beat.update(nonce='other')),
                    ('wrong_pid', lambda beat: beat.update(observer_pid=os.getpid() + 1000)),
                    ('wrong_worker', lambda beat: beat.update(worker_hostname='other')),
                    ('nonfinite_parent', lambda beat: beat.update(time=float('nan'))),
                    ('malformed_parent', None),
                    ('missing_parent', None),
                    ('deadline', lambda beat: None),
                    ('foreign_pause', lambda beat: None)]:
                seed(r)
                root = base / name
                root.mkdir(mode=0o700)
                beat = receipt(os.getpid())
                if change:
                    change(beat)
                    write(root / 'parent-heartbeat.json', beat)
                else:
                    if name != 'missing_parent':
                        (root / 'parent-heartbeat.json').write_text('{')
                if name == 'foreign_pause':
                    r.set(PAUSE, b'foreign')
                env = collector_environment(root, socket_path,
                    deadline=time.time() - 1 if name == 'deadline' else None)
                if name == 'missing_parent':
                    env['start'] -= 46
                try:
                    control(env)
                except (OSError, ValueError, TypeError, KeyError, RuntimeError, AssertionError):
                    pass
                else:
                    raise AssertionError(name + ' unexpectedly passed')
                stop = json.loads((root / 'stop.json').read_text())
                assert stop['reason'] != 'observer_stopped'
                assert r.get(PAUSE) == (b'foreign' if name == 'foreign_pause' else OWNER)
                assert not (root / 'activation.json').exists()
                assert not (root / 'completed.json').exists()
                passed(name, reason=stop['reason'])

            # Probe actual code with identity/config imports injected and an
            # owned process whose argv can be checked through real /proc.
            seed(r)
            root = base / 'probe'
            root.mkdir(mode=0o700)
            pid_child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(90)',
                                          str(root / 'observe_general_catalog.py'), str(root)])
            owned.append(pid_child)
            manifest = {'absolute_deadline': DEADLINE, 'pause_owner': OWNER.decode(),
                        'supervision_nonce': 'review-nonce',
                        'host_runtime_images': {'wepp1': [{'service': 'rq-worker', 'id': socket.gethostname()}]}}
            write(root / 'manifest.json', manifest)
            digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            write(root / 'observer-start.json', {'pid': pid_child.pid, 'started_at': time.time()})
            proxy_os = types.SimpleNamespace(**{name: getattr(os, name) for name in ('open', 'fdopen', 'fsync', 'replace', 'O_WRONLY', 'O_CREAT', 'O_TRUNC')},
                                            getuid=lambda: 1002, getgid=lambda: 130, getenv=lambda name: 'wepp.cloud')
            env = dict(hashlib=hashlib, json=json, math=math, os=proxy_os, Path=Path, socket=socket,
                       time=time, redis=redis, RedisDB=types.SimpleNamespace(RQ=0),
                       redis_connection_kwargs=lambda db: {'unix_socket_path': socket_path})
            exec(compile_nodes(functions(PROBE, {'read', 'finite_time', 'probe'}), PROBE), env)
            value = env['probe'](root, digest)
            assert value['state'] == 'starting' and (root / 'parent-heartbeat.json').exists()
            passed('probe_real_pid_private_atomic_handshake')

            for name, setup, cleanup in [
                    ('probe_stale_parent', lambda: write(root / 'parent-heartbeat.json', receipt(pid_child.pid, time.time() - 61)), lambda: write(root / 'parent-heartbeat.json', receipt(pid_child.pid))),
                    ('probe_bad_digest', lambda: None, lambda: None),
                    ('probe_wrong_worker_receipt', lambda: write(root / 'parent-heartbeat.json', receipt(pid_child.pid, worker_hostname='other')), lambda: write(root / 'parent-heartbeat.json', receipt(pid_child.pid))),
                    ('probe_foreign_pause', lambda: r.set(PAUSE, b'foreign'), lambda: r.set(PAUSE, OWNER)),
                    ('probe_wrong_pid', lambda: write(root / 'observer-start.json', {'pid': os.getpid(), 'started_at': time.time()}), lambda: write(root / 'observer-start.json', {'pid': pid_child.pid, 'started_at': time.time()}))]:
                setup()
                try:
                    env['probe'](root, 'wrong' if name == 'probe_bad_digest' else digest)
                except (OSError, ValueError):
                    passed(name)
                else:
                    raise AssertionError(name)
                cleanup()
            for name in ('probe_parent_expires_during_call', 'probe_duration_exceeded'):
                now = time.time()
                write(root / 'parent-heartbeat.json', receipt(pid_child.pid, now - 44))
                before = (root / 'parent-heartbeat.json').read_bytes()
                timestamps = iter([now, now + 2, now + 2])
                monotonic_times = iter([0, 11 if name == 'probe_duration_exceeded' else 1])
                env['time'] = types.SimpleNamespace(time=lambda: next(timestamps), monotonic=lambda: next(monotonic_times))
                try:
                    env['probe'](root, digest)
                except ValueError:
                    assert (root / 'parent-heartbeat.json').read_bytes() == before
                    passed(name)
                else:
                    raise AssertionError(name)
                env['time'] = time
            env['time'] = types.SimpleNamespace(time=lambda: DEADLINE + 1, monotonic=time.monotonic)
            try:
                env['probe'](root, digest)
            except ValueError as error:
                assert 'deadline' in str(error)
                passed('probe_absolute_deadline')
            else:
                raise AssertionError('Probe accepted expired deadline')
            env['time'] = time
            r.delete(PAUSE)
            now = time.time()
            activation = {'started_at': now - 10, 'baseline_cycle': 'old'}
            target = {'cycle': 'fresh', 'started_at': now - 5}
            proof = {'cycle': 'fresh', 'artifacts_verified': True, 'pending_age_coverage_accepted': True}
            completed = {'cycle': 'fresh', 'time': now, 'artifact_proof': proof}
            for filename, data in [('activation.json', activation), ('target-cycle.json', target),
                                   ('artifact-acceptance.json', proof), ('completed.json', completed)]:
                write(root / filename, data)
            assert env['probe'](root, digest)['state'] == 'completed'
            passed('probe_coherent_completion')
            for name, filename, changed in [('probe_old_cycle_completion', 'activation.json', {**activation, 'baseline_cycle': 'fresh'}),
                                           ('probe_unaccepted_completion', 'artifact-acceptance.json', {**proof, 'pending_age_coverage_accepted': False})]:
                before = (root / filename).read_bytes()
                write(root / filename, changed)
                try:
                    env['probe'](root, digest)
                except ValueError:
                    passed(name)
                else:
                    raise AssertionError(name)
                (root / filename).write_bytes(before)
            pid_child.terminate()
            pid_child.wait(timeout=3)

            # Execute the real remote containment program locally with only the
            # redis-settings module boundary redirected to disposable Redis.
            module = load_supervisor()
            bootstrap = "import os,sys,types;os.environ['EXTERNAL_HOST']='wepp.cloud';m=types.ModuleType('wepppy.config.redis_settings');m.RedisDB=types.SimpleNamespace(RQ=0);m.redis_connection_kwargs=lambda db:{'unix_socket_path':sys.argv[1]};sys.modules[m.__name__]=m;exec(sys.stdin.read())"
            module.remote = lambda host, arguments: [sys.executable, '-c', bootstrap, socket_path]
            for name, owner, ttl, confirmed in [('contain_absent', None, None, True),
                    ('contain_foreign_persistent', b'foreign', None, True),
                    ('contain_foreign_expiring', b'foreign', 300, False)]:
                r.delete(PAUSE)
                if owner:
                    r.set(PAUSE, owner, ex=ttl)
                result = module.contain()
                assert result['confirmed'] is confirmed
                assert r.get(PAUSE) == (owner or OWNER)
                if ttl:
                    assert r.ttl(PAUSE) > 0
                passed(name, confirmed=confirmed, attempts=len(result['attempts']))

            # Main's subprocess timeout must invoke actual NX containment. The
            # launched child exits immediately; only the probe hangs for 15s.
            seed(r)
            manifest_path = base / 'supervisor-manifest.json'
            write(manifest_path, {'evidence_path': '/wc1/query-catalog-validation/20261106/general-observation-02',
                  'environment': 'https://wepp.cloud', 'supervision_nonce': 'review-nonce',
                  'absolute_deadline': DEADLINE})
            r.delete(PAUSE)
            def remote(host, arguments):
                if len(arguments) == 1:
                    return [sys.executable, '-c', bootstrap, socket_path]
                if arguments[0] == '-':
                    return [sys.executable, '-c', 'import time;time.sleep(90)']
                return [sys.executable, '-c', 'pass']
            module.remote = remote
            original_argv = sys.argv
            sys.argv = [str(SUPERVISOR), '--manifest', str(manifest_path), '--local-evidence', str(base / 'supervisor-output')]
            try:
                code = module.main()
            finally:
                sys.argv = original_argv
            journal = [json.loads(line) for line in (base / 'supervisor-output/supervisor.jsonl').read_text().splitlines()]
            assert code == 1 and 'TimeoutExpired' in journal[-1]['reason']
            assert journal[-1]['containment']['confirmed'] and r.get(PAUSE) == OWNER
            passed('actual_blocked_probe_timeout_contains', reason=journal[-1]['reason'].split(':')[0])

            for name in ('supervisor_deadline', 'supervisor_monotonic_gap',
                         'supervisor_noncompleted_exit', 'supervisor_completed_exit'):
                r.delete(PAUSE)
                output = base / name
                module = load_supervisor()
                def remote(host, arguments):
                    if len(arguments) == 1:
                        return [sys.executable, '-c', bootstrap, socket_path]
                    if arguments[0] == '-':
                        state = 'completed' if name == 'supervisor_completed_exit' else 'running'
                        payload = json.dumps({'state': state, 'samples': 1})
                        return [sys.executable, '-c', 'import time;time.sleep(.1);print(' + repr(payload) + ')']
                    return [sys.executable, '-c', 'pass']
                module.remote = remote
                monotonic_times = iter([0, 61])
                module.time = types.SimpleNamespace(
                    time=(lambda: DEADLINE + 1) if name == 'supervisor_deadline' else time.time,
                    monotonic=(lambda: next(monotonic_times)) if name == 'supervisor_monotonic_gap' else time.monotonic,
                    sleep=lambda seconds: time.sleep(min(seconds, .05)))
                sys.argv = [str(SUPERVISOR), '--manifest', str(manifest_path), '--local-evidence', str(output)]
                try:
                    code = module.main()
                finally:
                    sys.argv = original_argv
                journal = [json.loads(line) for line in (output / 'supervisor.jsonl').read_text().splitlines()]
                success = name == 'supervisor_completed_exit'
                assert code == (0 if success else 1)
                assert journal[-1]['passed'] is success
                assert r.get(PAUSE) == (None if success else OWNER)
                passed(name, reason=journal[-1]['reason'])
            sys.argv = [str(SUPERVISOR), '--manifest', str(manifest_path), '--local-evidence', str(output)]
            try:
                try:
                    module.main()
                except FileExistsError:
                    passed('supervisor_evidence_directory_reuse_rejected')
                else:
                    raise AssertionError('Supervisor reused evidence directory')
            finally:
                sys.argv = original_argv

            root = base / 'sample_budget'
            root.mkdir(mode=0o700)
            env = collector_environment(root, socket_path)
            write(root / 'parent-heartbeat.json', receipt(os.getpid(), time.time() - 40))
            try:
                env['arm_sample']()
                remaining, interval = signal.getitimer(signal.ITIMER_REAL)
                assert 0 < remaining <= 5 and interval == 0
                passed('sample_alarm_respects_remaining_parent_lifetime', remaining_seconds=remaining)
            finally:
                signal.alarm(0)

            # Large cursor metadata must not trigger unbounded filesystem reads.
            # Both admitted scopes are retained on every sample; pending rotates.
            seed(r)
            root = base / 'bounded_age_sample'
            root.mkdir(mode=0o700)
            env = collector_environment(root, socket_path)
            write(root / 'parent-heartbeat.json', receipt(os.getpid()))
            pending_paths = [f'/review/pending-{index:04d}' for index in range(4641)]
            admitted_paths = ['/review/admitted-a', '/review/admitted-b']
            bindings = {f'maintenance-{index}': {'claimed': True, 'scope': {'wd': path}}
                        for index, path in enumerate(admitted_paths)}
            r.set('ledger', json.dumps({'jobs': bindings}))
            for jid in bindings:
                r.hset('rq:job:' + jid, 'status', 'finished')
            r.set('inventory', json.dumps({'cycle': 'old', 'pending': [{'path': path} for path in pending_paths]}))
            observed_paths = []
            env['cr'] = types.SimpleNamespace(catalog_refresh_status=lambda path: observed_paths.append(path) or {})
            assert env['sample']() is False
            assert set(observed_paths) == set(admitted_paths + pending_paths[:25])
            assert len(observed_paths) == 27
            observed_paths.clear()
            assert env['sample']() is False
            assert set(observed_paths) == set(admitted_paths + pending_paths[25:50])
            assert len(observed_paths) == 27
            rows = [json.loads(line) for line in (root / 'samples.jsonl').read_text().splitlines()]
            assert rows[0]['age_sampling'] == {'pending_records': 4641, 'pending_population': 4641, 'pending_sample_count': 25,
                'pending_offset': 0, 'admitted_population': 2, 'paths_checked': 27, 'pending_exhaustive': False,
                'count_basis': 'lexically distinct paths, not unique scopes; aliases may overlap'}
            assert rows[1]['age_sampling']['pending_offset'] == 25
            assert 'independent full census required' in rows[1]['age_coverage']
            assert not (root / 'completed.json').exists()
            passed('large_pending_age_sample_bounded_and_rotating', population=4641, reads_per_sample=27)

            # Small populations wrap without duplicate reads; overlap with an
            # admitted scope is read once and empty pending still checks admitted.
            for count in (0, 3, 26):
                selected = pending_paths[:count]
                r.set('inventory', json.dumps({'cycle': 'old', 'pending': [{'path': path} for path in selected + admitted_paths[:1]]}))
                observed_paths.clear()
                assert env['sample']() is False
                assert set(admitted_paths).issubset(observed_paths)
                assert len(observed_paths) == len(set(observed_paths)) <= min(25, count + 1) + 2
            r.set('inventory', json.dumps({'cycle': 'old', 'pending': []}))
            observed_paths.clear()
            assert env['sample']() is False and set(observed_paths) == set(admitted_paths)
            passed('pending_age_wrap_overlap_empty_preserves_admitted')

            # Actual sample completion and target-cycle arrival filter, plus a
            # deadline crossing after initial guard and before final commit.
            for name in ('completion', 'pre_target_arrival', 'deadline_crossing'):
                seed(r)
                r.delete(PAUSE)
                root = base / name
                root.mkdir(mode=0o700)
                current = time.time()
                clock = types.SimpleNamespace(time=lambda: current, sleep=time.sleep)
                env = collector_environment(root, socket_path, clock=clock, deadline=current + 2)
                env['activation'] = current - 20
                write(root / 'parent-heartbeat.json', receipt(os.getpid(), current))
                proof = {'cycle': 'fresh', 'artifacts_verified': True, 'pending_age_coverage_accepted': True}
                write(root / 'artifact-acceptance.json', proof)
                r.set('inventory', json.dumps({'cycle': 'fresh', 'cycle_started_at': current - 10, 'completed_at': current - 1, 'pending': []}))
                r.set('inventory:discovery', json.dumps({'cycle': 'fresh', 'completed_at': current - 2}))
                r.rpush('test:started', 'ordinary')
                enqueued = current - (15 if name == 'pre_target_arrival' else 5)
                r.hset('rq:job:ordinary', mapping={'description': 'ordinary.work()',
                    'enqueued_at': datetime.fromtimestamp(enqueued, timezone.utc).isoformat(),
                    'started_at': datetime.fromtimestamp(enqueued + 1, timezone.utc).isoformat()})
                if name == 'deadline_crossing':
                    real_check = env['check_parent']
                    checks = []
                    def check_parent():
                        if checks:
                            clock.time = lambda: current + 3
                        checks.append(True)
                        real_check()
                    env['check_parent'] = check_parent
                    try:
                        env['sample']()
                    except AssertionError as error:
                        assert 'deadline' in str(error)
                    else:
                        raise AssertionError('Deadline crossing accepted')
                    assert not (root / 'completed.json').exists()
                else:
                    value = env['sample']()
                    assert value is (name == 'completion')
                    assert (root / 'completed.json').exists() is (name == 'completion')
                passed(name)
        finally:
            signal.alarm(0)
            for process in owned:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            server.terminate()
            server.wait(timeout=5)
    return {'checks_passed': len(results), 'redis': redis.__version__,
            'source_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (COLLECTOR, PROBE, SUPERVISOR)}, 'results': results}


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        child_mode()
    else:
        print(json.dumps(run(), indent=2))
