"""Bounded foreground SSH supervisor; a paired collector contains hard parent loss."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time


CONTAIN = '''import json,os,redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
if os.environ.get('EXTERNAL_HOST')!='wepp.cloud':raise RuntimeError('Wrong environment')
kwargs=redis_connection_kwargs(RedisDB.RQ);kwargs.update(socket_connect_timeout=5,socket_timeout=5)
r=redis.Redis(**kwargs);key='query-catalog:batch-admission:v1:paused';owner=b'production-cutover-20261106:general-observation'
r.set(key,owner,nx=True)
print(json.dumps({'paused':bool(r.exists(key)),'owned':r.get(key)==owner,'ttl':r.ttl(key)}))
'''


def remote(host, arguments):
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', host,
            'cd /workdir/wepppy && ' + shlex.join(['wctl', 'docker', 'compose', 'exec', '-T',
                                                 'rq-worker', '/opt/venv/bin/python', *arguments])]


def contain():
    # Explicit alternate host containment, never a hidden successful fallback.
    attempts = []
    for host in ('wepp1', 'wepp2'):
        try:
            result = subprocess.run(remote(host, ['-']), input=CONTAIN, text=True,
                                    capture_output=True, timeout=15, check=True)
            value = json.loads(result.stdout)
            attempts.append({'host': host, 'result': value})
            if value.get('paused') is True and value.get('ttl') == -1:
                return {'confirmed': True, 'attempts': attempts}
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            attempts.append({'host': host, 'error_type': type(error).__name__})
    return {'confirmed': False, 'attempts': attempts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--local-evidence', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    root = Path(manifest['evidence_path'])
    manifest_digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if (manifest['environment'] != 'https://wepp.cloud' or not manifest.get('supervision_nonce')
            or root.parent != Path('/wc1/query-catalog-validation/20261106')
            or root.name != 'general-observation-02'
            or manifest['absolute_deadline'] != 1794127194.157908):
        raise ValueError('Unexpected recovery scope or changed original deadline')
    output = args.local_evidence
    output.mkdir(mode=0o700)
    if output.resolve() != output or output.stat().st_mode & 0o077:
        raise ValueError('Local evidence must be private and canonical')
    probe = (Path(__file__).parent / 'supervision_probe.py').read_text()
    command = remote('wepp1', [str(root / 'observe_general_catalog.py'), str(root)])
    journal = (output / 'supervisor.jsonl').open('x')
    os.chmod(output / 'supervisor.jsonl', 0o600)
    console = (output / 'collector.log').open('x')
    os.chmod(output / 'collector.log', 0o600)
    child = None
    passed = False
    started = time.time()
    started_monotonic = time.monotonic()
    last_checked = started_monotonic
    last_samples = 0
    progress_at = started_monotonic
    reason = 'supervisor_interrupted'

    def record(value):
        journal.write(json.dumps({'time': time.time(), **value}) + '\n')
        journal.flush()
        os.fsync(journal.fileno())

    def interrupted(signum, frame):
        raise RuntimeError('Supervisor interrupted')

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    try:
        if started >= manifest['absolute_deadline']:
            raise RuntimeError('Original deadline already reached')
        child = subprocess.Popen(command, stdout=console, stderr=subprocess.STDOUT)
        record({'event': 'started', 'transport_pid': child.pid,
                'deadline': manifest['absolute_deadline']})
        while time.time() < manifest['absolute_deadline']:
            check_started = time.monotonic()
            if check_started - last_checked > 60:
                raise RuntimeError('Supervisor attendance gap')
            result = subprocess.run(remote('wepp1', ['-', str(root), manifest_digest]), input=probe,
                                    text=True, capture_output=True, timeout=15, check=True)
            value = json.loads(result.stdout)
            now = time.monotonic()
            if now - last_checked > 60:
                raise RuntimeError('Supervisor probe exceeded attendance bound')
            last_checked = now
            status = child.poll()
            record({'event': 'check', 'probe': value, 'transport_exit': status})
            if status is not None:
                if status == 0 and value['state'] == 'completed':
                    passed = True
                    reason = 'completed'
                    break
                raise RuntimeError('Collector transport exited without accepted completion')
            if value['state'] == 'starting':
                if now - started_monotonic > 60:
                    raise RuntimeError('Collector startup grace expired')
            elif value['state'] == 'running':
                count = value['samples']
                if count < last_samples:
                    raise RuntimeError('Collector sample counter moved backward')
                if count > last_samples:
                    last_samples, progress_at = count, now
                elif now - progress_at > 60:
                    raise RuntimeError('Collector sample progress stopped')
            elif value['state'] != 'completed':
                raise RuntimeError('Unknown collector state')
            time.sleep(max(0, min(15 - (time.monotonic() - check_started),
                                 manifest['absolute_deadline'] - time.time())))
        if not passed:
            reason = 'deadline_without_complete_evidence'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        reason = type(error).__name__ + ': ' + str(error)
    finally:
        # Safety boundary also runs for unexpected programming errors. If the
        # supervisor is killed outright, the collector's parent receipt expires.
        containment = None if passed else contain()
        record({'event': 'finished', 'passed': passed, 'reason': reason, 'containment': containment})
        if child is not None and child.poll() is None and not passed:
            # Admission is contained first. Closing only our SSH transport never
            # terminates an admitted RQ job; the paired collector sees the pause.
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                child.terminate()
        console.close()
        journal.close()
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
