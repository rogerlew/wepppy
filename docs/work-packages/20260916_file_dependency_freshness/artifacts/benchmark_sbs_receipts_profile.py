"""S01/S02 pre-implementation costs; actual old operations plus labeled compositions.

Only ordinary read-copy opens named input files. All controllers/native opens,
receipts, seed copies, events, and multipart operations use unique disposable
fixtures. No HTTP, job submission, promotion of a named run, or runtime edits.
Compositions are cost discovery, not implementation/coherence acceptance.
"""
from collections import defaultdict
from contextlib import nullcontext
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import shutil
import stat
from statistics import mean
import sys
from time import perf_counter, sleep
import tracemalloc
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from osgeo import gdal
import requests
from wepppy.all_your_base import file_digest
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.omni.omni import OmniScenario
from wepppy.nodb.mods.omni import omni_mode_build_services as mode_module
from wepppy.nodb.mods.omni import omni_station_catalog_service as signature_module
from wepppy.profile_recorder import assembler as assembler_module, playback as playback_module

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'sbs_receipts_profile_performance_baseline.json'
ROOT = Path('/wc1/batch') / ('qa-sbs-receipts-' + uuid4().hex[:12])
ROOT.mkdir()
result = {'scope': __doc__, 'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'cache_note': 'Copied files prime filesystem pages. Helper-cold/evicted is not cold storage.',
          'module_hashes': {}, 'named_inputs': {}, 'cases': {}, 'errors': [],
          'measurement_limits': ['S01 excludes clone/reset, native validation, landuse/soil/WEPP execution and NoDb locks.',
                                 'S02 uses actual copied NoDb controller lookup, append/config/seed operations and Requests preparation; no network.',
                                 'Prototype receipt paths/guards are cost composition, not a substitute for independent implementation security review.',
                                 'Digest/read counters track Python Path.open reads; shutil fast-copy reads are separately known logical copied bytes.']}
for module in (file_digest, mode_module, signature_module, assembler_module, playback_module):
    source = Path(module.__file__)
    raw = source.read_bytes()
    result['module_hashes'][str(source)] = hashlib.sha256(raw).hexdigest()
    (ROOT / source.name).write_bytes(raw)


def is_named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and is_named(args[0]):
        access, flags = args[1], args[2]
        if (access and any(c in access for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named writes in SBS receipt benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(is_named(value) for value in args[:2]):
            raise PermissionError('No named mutation in SBS receipt benchmark')


sys.addaudithook(audit)


def version(path):
    return fd_version(Path(path).stat())


def fd_version(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def raw_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def copy_named(source, destination):
    result['named_inputs'][str(source)] = {'version': version(source), 'sha256': raw_digest(source)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    assert raw_digest(destination) == result['named_inputs'][str(source)]['sha256']


reads = defaultdict(int)
real_open = Path.open


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


def flush():
    text = json.dumps(result, indent=2) + '\n'
    OUTPUT.write_text(text)
    (ROOT / 'benchmark-manifest.json').write_text(text)


def measure(case, name, callback, repeats=5, prepare=None):
    times, read_counts = [], []
    for _ in range(repeats):
        if prepare:
            prepare()
        before = sum(reads.values())
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
        read_counts.append(sum(reads.values()) - before)
    row = {'name': name, 'repeats': repeats, 'seconds': times, 'mean_ms': mean(times) * 1000,
           'python_tiff_read_bytes': read_counts}
    case['measurements'].append(row)
    print(f"{case['name']} {name}: {row['mean_ms']:.3f} ms, reads {read_counts}", flush=True)
    flush()
    return value


def clear_digest():
    file_digest._observed_at.cache_clear()
    file_digest._digest.cache_clear()


def pressure():
    for path in pressure_files:
        file_digest.sha256_file(path)
    sleep(1.05)
    for path in pressure_files:
        file_digest.sha256_file(path)
    assert file_digest._observed_at.cache_info().currsize == 512
    assert file_digest._digest.cache_info().currsize == 512


def checked_copy(source, destination, expected=None):
    """Prototype one opened source/hash/copy plus independent destination hash."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    checksum, count = hashlib.sha256(), 0
    with source.open('rb') as stream:
        before = fd_version(os.fstat(stream.fileno()))
        assert stat.S_ISREG(os.fstat(stream.fileno()).st_mode)
        assert version(source) == before
        with destination.open('wb') as target:
            while block := stream.read(1024 * 1024):
                count += len(block)
                checksum.update(block)
                target.write(block)
        assert fd_version(os.fstat(stream.fileno())) == before == version(source)
    digest = checksum.hexdigest()
    assert expected is None or digest == expected
    assert file_digest.sha256_file(destination) == digest
    return {'sha256': digest, 'size': count}, before


def snapshot_event(source, seed_root, event_id):
    """Labeled proposal composition: visible status, guarded copy, atomic receipt."""
    event_root = seed_root / 'sbs/events' / hashlib.sha256(event_id.encode()).hexdigest()
    event_root.mkdir(parents=True)
    assert event_root.resolve().is_relative_to(seed_root.resolve())
    payload = event_root / ('payload' + source.suffix)
    status = event_root / 'receipt.json'
    status.write_text(json.dumps({'version': 1, 'event_id': event_id, 'status': 'capturing'}))
    receipt, _ = checked_copy(source, payload)
    receipt.update(version=1, event_id=event_id, status='complete', payload=payload.name)
    temporary = event_root / 'receipt.next.json'
    temporary.write_text(json.dumps(receipt, sort_keys=True))
    temporary.replace(status)
    return status


def verified_multipart(receipt_path, expected_event):
    receipt = json.loads(receipt_path.read_text())
    assert receipt['version'] == 1 and receipt['status'] == 'complete'
    assert receipt['event_id'] == expected_event and receipt['payload'] == 'payload.tif'
    payload = receipt_path.parent / receipt['payload']
    assert payload.resolve().parent == receipt_path.parent.resolve()
    with payload.open('rb') as stream:
        before = fd_version(os.fstat(stream.fileno()))
        assert stat.S_ISREG(os.fstat(stream.fileno()).st_mode)
        assert before == version(payload)
        content = stream.read()
        assert fd_version(os.fstat(stream.fileno())) == before == version(payload)
    assert len(content) == receipt['size'] and hashlib.sha256(content).hexdigest() == receipt['sha256']
    return requests.Request('POST', 'https://disposable.invalid/upload',
                            files={'input_upload_sbs': (payload.name, content, 'application/octet-stream')}).prepare()


try:
    fixtures = []
    for tag, named in [('grizzly', Path('/wc1/runs/th/thespian-cleanness/disturbed/GrizzlyCreek_SBS_final.tif')),
                       ('rattlesnake', Path('/wc1/runs/in/incomparable-gracefulness/disturbed/Rattlesnake.tif'))]:
        original = ROOT / (tag + '-original')
        source = original / 'disturbed' / named.name
        copy_named(named, source)
        controller = original / 'disturbed.nodb'
        copy_named(named.parent.parent / 'disturbed.nodb', controller)
        state = json.loads(controller.read_text())
        state['py/state']['wd'] = str(original)
        state['py/state']['_disturbed_fn'] = source.name
        controller.write_text(json.dumps(state))
        fixtures.append((tag, original, source, 'Unmodified actual uploaded main bytes'))
    original = ROOT / 'stress16m-original'
    source = original / 'disturbed/stress16m.tif'
    source.parent.mkdir(parents=True)
    dataset = gdal.Translate(str(source), str(fixtures[0][2]), format='GTiff', width=4096, height=4096,
                             outputType=gdal.GDT_Byte, resampleAlg='nearest', creationOptions=['COMPRESS=NONE', 'TILED=YES'])
    dataset = None
    state = json.loads((fixtures[0][1] / 'disturbed.nodb').read_text())
    state['py/state']['wd'] = str(original)
    state['py/state']['_disturbed_fn'] = source.name
    (original / 'disturbed.nodb').write_text(json.dumps(state))
    fixtures.append(('stress16m', original, source,
                     'Valid 4096x4096 uncompressed Byte TIFF derived from copied Grizzly pixels by nearest resampling; not an actual uploaded file'))
    pressure_root = ROOT / 'pressure'
    pressure_root.mkdir()
    pressure_files = [pressure_root / str(i) for i in range(512)]
    for i, path in enumerate(pressure_files):
        path.write_bytes(f'pressure-{i}'.encode())
    with patch.object(Path, 'open', counted_open):
        for tag, original, source, note in fixtures:
            case = result['cases'][tag] = {'name': tag, 'source': str(source), 'source_bytes': source.stat().st_size,
                'source_sha256': raw_digest(source), 'fixture_note': note, 'measurements': []}
            expected = case['source_sha256']
            with gdal.Open(str(source)) as dataset:
                case['shape'] = [dataset.RasterYSize, dataset.RasterXSize]
            owner = measure(case, 'actual_controller_first_lookup', lambda: Disturbed.getInstance(str(original)), repeats=1)
            assert owner.disturbed_path == str(source)
            measure(case, 'actual_controller_settled_lookup', lambda: Disturbed.getInstance(str(original)), repeats=10)
            scenario_def = {'type': OmniScenario.SBSmap, 'sbs_file_path': str(source)}
            service = signature_module.OmniStationCatalogService()
            measure(case, 'actual_definition_only_signature', lambda: service.scenario_signature(None, scenario_def), repeats=30)
            def receipt_signature():
                content = dict(version=1, source_path=str(source), sha256=file_digest.sha256_file(source))
                return service.scenario_signature(None, dict(scenario_def, _sbs_content=content))
            measure(case, 'receipt_signature_cold', receipt_signature, prepare=clear_digest)
            receipt_signature()
            sleep(1.05)
            receipt_signature()
            measure(case, 'receipt_signature_settled', receipt_signature, repeats=30)
            measure(case, 'receipt_signature_actual512evicted', receipt_signature, repeats=3, prepare=pressure)
            def reuse():
                before = receipt_signature()
                assert receipt_signature() == before
            measure(case, 'reuse_pre_post_cold', reuse, prepare=clear_digest)
            receipt_signature()
            sleep(1.05)
            receipt_signature()
            measure(case, 'reuse_pre_post_settled', reuse, repeats=30)
            destination_root = ROOT / (tag + '-omni-child') / 'disturbed'
            destination_root.mkdir(parents=True)
            upload = ROOT / (tag + '-limbo') / source.name
            upload.parent.mkdir()
            destination = destination_root / source.name
            omni = SimpleNamespace(logger=logging.getLogger('sbs-benchmark'), timed=lambda _: nullcontext(),
                                   rq_job_pool_max_worker_per_scenario_task=1)
            disturbed = SimpleNamespace(disturbed_dir=str(destination_root), validate=lambda *a, **k: None)
            def actual_mode_copy():
                mode_module.OmniModeBuildServices().apply_scenario_mode(
                    omni, scenario_name='sbs_map_benchmark', scenario=OmniScenario.SBSmap,
                    scenario_def={'type': OmniScenario.SBSmap, 'sbs_file_path': str(upload)},
                    new_wd=str(destination_root.parent), disturbed=disturbed,
                    landuse=SimpleNamespace(build=lambda: None), soils=SimpleNamespace(build=lambda **k: None),
                    omni_base_scenario_name=None)
            with patch.object(mode_module, '_run_with_directory_roots_lock', lambda wd, roots, callback, **kw: callback()):
                measure(case, 'actual_mode_copy_consume_only', actual_mode_copy,
                        prepare=lambda: shutil.copy2(source, upload))
            assert not upload.exists() and raw_digest(destination) == expected
            def composed_copy_admission():
                # Initial observation and pre-reset reobservation; native work and metadata lock omitted.
                receipt = file_digest.sha256_file(upload)
                assert file_digest.sha256_file(upload) == receipt
                copied, source_version = checked_copy(upload, destination, receipt)
                assert version(upload) == source_version
                upload.unlink()
                copied_version = version(destination)
                # Outer and locked success-admission observations, with physical version retained.
                assert file_digest.sha256_file(destination) == receipt and version(destination) == copied_version
                assert file_digest.sha256_file(destination) == receipt and version(destination) == copied_version
                return copied
            def copy_prepare():
                shutil.copy2(source, upload)
                clear_digest()
            measure(case, 'composed_initial_receipt_copy_consume_two_admissions', composed_copy_admission, prepare=copy_prepare)
            assert not upload.exists() and raw_digest(destination) == expected
            case['omni_copy_scope'] = 'Actual apply_scenario_mode copy/unlink; native validation/build and directory lock callback are explicit seams.'
            case['composed_copy_expected_read_factor'] = 6

            data_root = ROOT / (tag + '-profiles')
            assembler = assembler_module.ProfileAssembler(data_root)
            endpoint = '/rq-engine/api/runs/' + original.name + '/config/tasks/upload-sbs'
            def event():
                return dict(stage='response', id=uuid4().hex, method='POST', ok=True,
                            category='file_upload', endpoint=endpoint)
            measure(case, 'actual_assembler_first_event', lambda: assembler.handle_event(original.name, 'capture', event(), original), repeats=1)
            measure(case, 'actual_assembler_repeated_event', lambda: assembler.handle_event(original.name, 'capture', event(), original))
            draft = data_root / 'profiles/_drafts' / original.name / 'capture'
            canonical = draft / 'seed/uploads/sbs' / ('input_upload_sbs' + source.suffix)
            assert raw_digest(canonical) == expected
            latest = {}
            actual_capture = assembler._capture_file_upload
            def composed_capture(event, draft_root, run_dir):
                actual_capture(event, draft_root, run_dir)
                latest['id'] = event['id']
                latest['receipt'] = snapshot_event(source, draft_root / 'seed/uploads', event['id'])
            def composed_event():
                current = event()
                current['_sbs_seed_version'] = 1
                assembler.handle_event(original.name, 'capture', current, original)
                assert latest['id'] == current['id']
            with patch.object(assembler, '_capture_file_upload', composed_capture):
                measure(case, 'composed_assembler_event_with_verified_receipt', composed_event)
            session = object.__new__(playback_module.PlaybackSession)
            session.seed_upload_root = draft / 'seed/uploads'
            session.run_dir = str(ROOT / (tag + '-sandbox'))
            session.profile_run_root = ROOT / (tag + '-profile-run')
            def actual_multipart():
                data, files = session._build_form_request(endpoint, {'bodyType': 'form-data'})
                path, mime = files['input_upload_sbs']
                with path.open('rb') as stream:
                    return requests.Request('POST', 'https://disposable.invalid/upload', data=data,
                                            files={'input_upload_sbs': (path.name, stream, mime)}).prepare()
            prepared = measure(case, 'actual_form_and_requests_multipart', actual_multipart)
            verified = measure(case, 'composed_verified_event_multipart',
                               lambda: verified_multipart(latest['receipt'], latest['id']))
            for label, callback in [('actual', actual_multipart), ('verified', lambda: verified_multipart(latest['receipt'], latest['id']))]:
                tracemalloc.start()
                payload = callback()
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                case[label + '_multipart_python_peak_bytes'] = peak
                case[label + '_multipart_body_bytes'] = len(payload.body)
            # Parse actual prepared wire bodies without HTTP to prove exact file bytes.
            from email.parser import BytesParser
            from email.policy import default
            for label, payload in [('actual', prepared), ('verified', verified)]:
                message = BytesParser(policy=default).parsebytes(
                    ('Content-Type: ' + payload.headers['Content-Type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + payload.body)
                parts = list(message.iter_parts())
                content = parts[0].get_payload(decode=True)
                case[label + '_multipart_main_sha256'] = hashlib.sha256(content).hexdigest()
                assert hashlib.sha256(content).hexdigest() == expected
                assert parts[0].get_param('name', header='content-disposition') == 'input_upload_sbs'
                assert parts[0].get_content_type() == 'application/octet-stream'
            assert raw_digest(source) == expected
            case['source_unchanged'] = True
            case['recorded_event_count'] = len((draft / 'events.jsonl').read_text().splitlines())
            flush()
    result['completed'] = True
except BaseException as error:
    result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    raise
finally:
    result['named_inputs_unchanged'] = all(version(Path(path)) == tuple(info['version']) and raw_digest(path) == info['sha256']
                                          for path, info in result['named_inputs'].items())
    result['modules_unchanged'] = all(raw_digest(path) == digest for path, digest in result['module_hashes'].items())
    flush()
    print(json.dumps(result, indent=2), flush=True)
