"""S02 complete actual assembler capture and verified Requests preparation.

Unique copied input/controller owners, full 34,830-byte primary configuration,
actual descriptor-bound event capture, actual playback _execute_request, and
Requests Session preparation. A prepare-only send override stops before any
HTTP. Named sources are ordinary read-only, and all outputs remain observable.
"""
from collections import defaultdict
from email.parser import BytesParser
from email.policy import default
import hashlib
import json
import os
from pathlib import Path
import shutil
from statistics import mean
import sys
from time import perf_counter, sleep
import tracemalloc
from unittest.mock import patch
from uuid import uuid4

import requests
from wepppy.all_your_base import file_digest
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.profile_recorder import assembler, playback, sbs_seed

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'profile_sbs_implementation_performance.json'
BASE = json.loads((ARTIFACTS / 'sbs_receipts_profile_performance_baseline.json').read_text())
PRIOR = Path(BASE['root'])
ROOT = Path('/wc1/batch') / ('qa-profile-sbs-implementation-' + uuid4().hex[:12])
ROOT.mkdir()
result = {'scope': __doc__, 'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'baseline_manifest': str(PRIOR / 'benchmark-manifest.json'),
          'cache_note': 'Warm filesystem pages; cold/settled are ordinary-digest states, not cold storage.',
          'module_hashes': {}, 'inputs': {}, 'cases': {}, 'gates': [], 'errors': [],
          'scope_limits': ['No live HTTP, authentication, RQ, or model execution.',
                           'Actual _execute_request and Requests Session.request/prepare_request run; only send returns locally.',
                           'Python allocation peak is not process RSS.',
                           'Path/open and os.fdopen payload reads are counted; shutil kernel copy bytes are not Python reads.',
                           'Every fixture uses the actual Grizzly primary config as a representative 34,830-byte copy workload; Rattlesnake original lacks that file.']}
for module in (file_digest, assembler, playback, sbs_seed):
    path = Path(module.__file__)
    raw = path.read_bytes()
    result['module_hashes'][str(path)] = hashlib.sha256(raw).hexdigest()
    (ROOT / path.name).write_bytes(raw)


def named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and named(args[0]):
        access, flags = args[1], args[2]
        if (access and any(char in access for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named writes in profile benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named mutation in profile benchmark')


sys.addaudithook(audit)


def version(path):
    info = Path(path).stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record_input(path):
    path = Path(path)
    result['inputs'][str(path)] = {'version': version(path), 'sha256': digest(path)}


config_source = Path('/wc1/runs/th/thespian-cleanness/config.cfg')
record_input(config_source)
config_master = ROOT / 'primary-config.cfg'
shutil.copy2(config_source, config_master)
assert config_master.stat().st_size == 34830
reads = defaultdict(int)
real_open, real_fdopen = Path.open, os.fdopen


class Counted:
    def __init__(self, stream, label):
        self.stream, self.label = stream, label
    def __enter__(self): self.stream.__enter__(); return self
    def __exit__(self, *args): return self.stream.__exit__(*args)
    def __getattr__(self, key): return getattr(self.stream, key)
    def read(self, *args, **kwargs):
        value = self.stream.read(*args, **kwargs)
        reads[self.label] += len(value)
        return value


def counted_open(path, *args, **kwargs):
    stream = real_open(path, *args, **kwargs)
    mode = args[0] if args else kwargs.get('mode', 'r')
    if mode == 'rb' and path.is_relative_to(ROOT) and path.suffix == '.tif':
        return Counted(stream, str(path))
    return stream


def counted_fdopen(fd, *args, **kwargs):
    mode = args[0] if args else kwargs.get('mode', 'r')
    label = os.readlink(f'/proc/self/fd/{fd}') if mode == 'rb' else ''
    stream = real_fdopen(fd, *args, **kwargs)
    if mode == 'rb' and label.startswith(str(ROOT)) and label.endswith('.tif'):
        return Counted(stream, label)
    return stream


def flush():
    payload = json.dumps(result, indent=2) + '\n'
    OUTPUT.write_text(payload)
    (ROOT / 'benchmark-manifest.json').write_text(payload)


def measure(case, name, callback, repeats=5, prepare=None, verify=None):
    samples = []
    for _ in range(repeats):
        if prepare: prepare()
        before = dict(reads)
        start = perf_counter()
        value = callback()
        elapsed = perf_counter() - start
        sample = {'seconds': elapsed, 'payload_read_bytes': {
            path: size - before.get(path, 0) for path, size in reads.items() if size != before.get(path, 0)}}
        samples.append(sample)
        if verify: verify(value)
    row = {'name': name, 'mean_ms': mean(sample['seconds'] for sample in samples) * 1000, 'samples': samples}
    case['measurements'].append(row)
    print(case['name'], name, round(row['mean_ms'], 3), 'ms',
          'payloads', [sum(sample['payload_read_bytes'].values()) for sample in samples], flush=True)
    flush()
    return value


def clear_digest():
    file_digest._observed_at.cache_clear()
    file_digest._digest.cache_clear()


def gate(name, value, limit):
    result['gates'].append({'name': name, 'actual': value, 'limit': limit, 'passed': value <= limit})


class PrepareOnlySession(requests.Session):
    """Exercise actual Requests preparation; stop at transport boundary."""
    def send(self, request, **kwargs):
        self.prepared = request
        response = requests.Response()
        response.status_code = 200
        response._content = b'{}'
        response.headers['Content-Type'] = 'application/json'
        response.request = request
        response.url = request.url
        return response


try:
    with patch.object(Path, 'open', counted_open), patch.object(os, 'fdopen', counted_fdopen):
        for tag, baseline_case in BASE['cases'].items():
            source_master = Path(baseline_case['source'])
            controller_master = source_master.parent.parent / 'disturbed.nodb'
            record_input(source_master)
            record_input(controller_master)
            case = result['cases'][tag] = {'name': tag, 'source_bytes': source_master.stat().st_size,
                'source_sha256': digest(source_master), 'fixture_note': baseline_case['fixture_note'],
                'primary_config_bytes': config_master.stat().st_size, 'measurements': [], 'owners': []}
            current = {}
            def prepare_first():
                original = ROOT / (tag + '-original-' + uuid4().hex[:10])
                source = original / 'disturbed' / source_master.name
                source.parent.mkdir(parents=True)
                shutil.copy2(source_master, source)
                state = json.loads(controller_master.read_text())
                state['py/state']['wd'] = str(original)
                state['py/state']['_disturbed_fn'] = source.name
                (original / 'disturbed.nodb').write_text(json.dumps(state))
                shutil.copy2(config_master, original / 'config.cfg')
                data_root = ROOT / (tag + '-profiles-' + uuid4().hex[:10])
                current.clear()
                current.update(original=original, source=source, data_root=data_root,
                               assembler=assembler.ProfileAssembler(data_root))
                case['owners'].append(str(original))
                clear_digest()
            def capture():
                original = current['original']
                event_id = uuid4().hex
                endpoint = f'/rq-engine/api/runs/{original.name}/config/tasks/upload-sbs/'
                event = dict(stage='response', id=event_id, method='POST', ok=True,
                             category='file_upload', endpoint=endpoint)
                current['assembler'].handle_event(original.name, 'capture', event, original)
                draft = current['data_root'] / 'profiles/_drafts' / original.name / 'capture'
                current.update(event_id=event_id, endpoint=endpoint, draft=draft)
                return event_id
            def verify_capture(event_id):
                root = current['draft'] / 'seed/uploads'
                seed = sbs_seed.read_event_seed(root, event_id, required=True)
                assert len(seed.payload) == case['source_bytes']
                assert hashlib.sha256(seed.payload).hexdigest() == case['source_sha256']
                assert (current['draft'] / 'seed/config/config.cfg').read_bytes() == config_master.read_bytes()
                last = json.loads((current['draft'] / 'events.jsonl').read_text().splitlines()[-1])
                assert last['id'] == event_id and last[sbs_seed.MARKER] == 1
                assert seed.name.endswith('.tif')
            measure(case, 'actual_complete_first_capture', capture, repeats=3,
                    prepare=prepare_first, verify=verify_capture)
            measure(case, 'actual_established_capture_cold_digest', capture,
                    prepare=clear_digest, verify=verify_capture)
            file_digest.sha256_file(current['source'])
            sleep(1.05)
            file_digest.sha256_file(current['source'])
            measure(case, 'actual_established_capture_settled_digest', capture,
                    verify=verify_capture)
            event_id = current['event_id']
            session = object.__new__(playback.PlaybackSession)
            session.seed_upload_root = current['draft'] / 'seed/uploads'
            session.run_dir = str(ROOT / (tag + '-sandbox'))
            session.profile_run_root = ROOT / (tag + '-profile-run')
            session.session = PrepareOnlySession()
            session.verbose = False
            session.execute = True
            session.results = []
            session._pending_jobs = []
            def dispatch():
                return session._execute_request('POST', 'https://disposable.invalid/upload', [], None, 200,
                    current['endpoint'], {'bodyType': 'form-data'},
                    sbs_event_id=event_id, sbs_seed_required=True)
            response = measure(case, 'actual_verified_dispatch_through_requests_preparation', dispatch)
            # Wire validation is outside measured dispatch and never sends network traffic.
            prepared = response.request
            message = BytesParser(policy=default).parsebytes(
                ('Content-Type: ' + prepared.headers['Content-Type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + prepared.body)
            parts = list(message.iter_parts())
            assert len(parts) == 1
            content = parts[0].get_payload(decode=True)
            case['wire_sha256'] = hashlib.sha256(content).hexdigest()
            case['wire_field'] = parts[0].get_param('name', header='content-disposition')
            case['wire_filename'] = parts[0].get_filename()
            case['wire_mime'] = parts[0].get_content_type()
            assert case['wire_sha256'] == case['source_sha256']
            assert case['wire_field'] == 'input_upload_sbs'
            assert case['wire_filename'] == 'input_upload_sbs.tif'
            assert case['wire_mime'] == 'application/octet-stream'
            tracemalloc.start()
            memory_response = dispatch()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            case['dispatch_python_peak_bytes'] = peak
            case['multipart_body_bytes'] = len(memory_response.request.body)
            case['retained_seed_bytes'] = sum(path.stat().st_size for path in (current['draft'] / 'seed').rglob('*') if path.is_file())
            case['event_count'] = len((current['draft'] / 'events.jsonl').read_text().splitlines())
            case['original_source_unchanged'] = digest(current['source']) == case['source_sha256']
            case['receipts_complete'] = True
            rows = {row['name']: row for row in case['measurements']}
            first_limit, capture_limit, dispatch_limit = (550, 450, 150) if tag == 'stress16m' else (125, 100, 20)
            gate(tag + '_complete_first_capture_ms', rows['actual_complete_first_capture']['mean_ms'], first_limit)
            for state in ('cold', 'settled'):
                gate(tag + '_' + state + '_capture_ms', rows['actual_established_capture_' + state + '_digest']['mean_ms'], capture_limit)
            row = rows['actual_verified_dispatch_through_requests_preparation']
            gate(tag + '_complete_dispatch_ms', row['mean_ms'], dispatch_limit)
            for index, sample in enumerate(row['samples']):
                gate(tag + '_dispatch_payload_read_bytes_' + str(index), sum(sample['payload_read_bytes'].values()), case['source_bytes'])
            session.session.close()
            flush()
    result['completed'] = True
    result['acceptance_passed'] = all(gate['passed'] for gate in result['gates'])
except BaseException as error:
    result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    raise
finally:
    result['inputs_unchanged'] = all(version(path) == tuple(info['version']) and digest(path) == info['sha256']
                                    for path, info in result['inputs'].items())
    result['modules_unchanged'] = all(digest(path) == sha for path, sha in result['module_hashes'].items())
    flush()
    print(json.dumps(result, indent=2), flush=True)
