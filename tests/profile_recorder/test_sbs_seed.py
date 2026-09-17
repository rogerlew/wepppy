"""Event identity and actual Requests multipart bytes; no raster decoding claim."""
import hashlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import requests

from tests.profile_recorder.stubdeps import load_profile_module
from wepppy.profile_recorder.sbs_seed import capture_event_seed, read_event_seed

Assembler = load_profile_module('assembler.py', 'tests.profile_recorder.seed_assembler',
                                package='wepppy.profile_recorder').ProfileAssembler
Playback = load_profile_module('playback.py', 'tests.profile_recorder.seed_playback').PlaybackSession
pytestmark = pytest.mark.integration
ENDPOINT = '/rq-engine/api/runs/disposable/disturbed/tasks/upload-sbs/'


@pytest.fixture
def capture(tmp_path, monkeypatch):
    source = tmp_path / 'run' / 'disturbed' / 'same.tif'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'generation-one')
    for module_name, class_name, attribute, value in [
        ('wepppy.nodb.mods.disturbed', 'Disturbed', 'disturbed_path', str(source)),
        ('wepppy.nodb.mods.baer', 'Baer', 'baer_path', None),
    ]:
        module = ModuleType(module_name)
        setattr(module, class_name, SimpleNamespace(getInstance=lambda _, a=attribute, v=value: SimpleNamespace(**{a: v})))
        monkeypatch.setitem(sys.modules, module_name, module)
    assembler = Assembler(tmp_path / 'data')
    monkeypatch.setattr(assembler, '_ensure_config_seed', lambda *args: None)
    def record(event_id):
        assembler.handle_event('disposable', 'capture', {
            'stage': 'response', 'id': event_id, 'method': 'POST', 'ok': True,
            'category': 'file_upload', 'endpoint': ENDPOINT}, source.parents[1])
    return assembler, source, record


def playback(seed_root, tmp_path):
    session = object.__new__(Playback)
    session.seed_upload_root = seed_root
    session.run_dir = str(tmp_path / 'sandbox')
    session.profile_run_root = tmp_path / 'profile-run'
    session.results = []
    session.execute = False
    session.verbose = False
    session._should_wait_for_completion = lambda *args: False
    session._log = lambda *args: None
    wire = []
    def request(method, url, **kwargs):
        kwargs.pop('timeout', None)
        wire.append(requests.Request(method, url, **kwargs).prepare())
        return SimpleNamespace(status_code=200)
    session.session = SimpleNamespace(request=request)
    return session, wire


def test_two_response_events_promote_and_send_their_own_bytes(capture, tmp_path):
    assembler, source, record = capture
    record('one')
    source.write_bytes(b'generation-three')
    record('three')
    promoted = assembler.promote_draft('disposable', 'capture', slug='event-seeds')
    root = Path(promoted['capture_path'])
    events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
    assert [event['_sbs_seed_version'] for event in events] == [1, 1]
    session, wire = playback(root / 'seed' / 'uploads', tmp_path)
    for event_id in ['one', 'three']:
        session._execute_request('POST', 'https://disposable.invalid/upload', [], None, 200,
                                 ENDPOINT, {'bodyType': 'form-data'},
                                 sbs_event_id=event_id, sbs_seed_required=True)
    assert b'generation-one' in wire[0].body and b'generation-three' not in wire[0].body
    assert b'generation-three' in wire[1].body and b'generation-one' not in wire[1].body
    assert b'filename="input_upload_sbs.tif"' in wire[1].body
    assert b'Content-Type: application/octet-stream' in wire[1].body


def test_failure_before_seed_creation_is_marked_and_never_uses_old_seed(capture, tmp_path, monkeypatch):
    assembler, source, record = capture
    record('one')
    def fail(*args):
        raise PermissionError('injected config failure before seed directory')
    monkeypatch.setattr(assembler, '_ensure_config_seed', fail)
    source.write_bytes(b'generation-three')
    record('three')
    promoted = assembler.promote_draft('disposable', 'capture', slug='failed-event')
    root = Path(promoted['capture_path'])
    events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
    assert events[-1]['_sbs_seed_version'] == 1
    session, _ = playback(root / 'seed' / 'uploads', tmp_path)
    with pytest.raises(requests.RequestException):
        session._build_form_request(ENDPOINT, {'bodyType': 'form-data'},
                                    sbs_event_id='three', sbs_seed_required=True)
    legacy_files = session._build_form_request(ENDPOINT, {'bodyType': 'form-data'})[1]
    assert legacy_files['input_upload_sbs'][0].read_bytes() == b'generation-one'


def test_duplicate_event_is_immutable_and_corruption_rejected(tmp_path):
    source = tmp_path / 'source.tif'
    source.write_bytes(b'one')
    seed_root = tmp_path / 'uploads'
    capture_event_seed(seed_root, 'event', source)
    capture_event_seed(seed_root, 'event', source)
    source.write_bytes(b'two')
    with pytest.raises(ValueError, match='Repeated'):
        capture_event_seed(seed_root, 'event', source)
    assert read_event_seed(seed_root, 'event', required=True).payload == b'one'
    entry = seed_root / 'sbs' / 'events' / hashlib.sha256(b'event').hexdigest()
    (entry / 'input_upload_sbs.tif').write_bytes(b'two')
    with pytest.raises(requests.RequestException, match='does not match'):
        read_event_seed(seed_root, 'event', required=True)


def test_event_path_escape_never_reads_external_payload(tmp_path):
    root = tmp_path / 'uploads'
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / 'sbs').mkdir(parents=True)
    (root / 'sbs' / 'events').symlink_to(outside, target_is_directory=True)
    with pytest.raises(requests.RequestException, match='escapes'):
        read_event_seed(root, 'event', required=True)
    assert not list(outside.iterdir())


def test_event_directory_replacement_never_writes_outside(tmp_path, monkeypatch):
    import os
    from wepppy.profile_recorder import sbs_seed
    source = tmp_path / 'source.tif'
    source.write_bytes(b'captured record')
    seed_root = tmp_path / 'uploads'
    entry = seed_root / 'sbs/events' / hashlib.sha256(b'event').hexdigest()
    retained = entry.with_name('retained-original')
    outside = tmp_path / 'outside'
    outside.mkdir()
    real_open = os.open
    injected = False
    def replace_before_payload(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal injected
        if path == 'input_upload_sbs.tif' and flags & os.O_CREAT and not injected:
            injected = True
            entry.rename(retained)
            entry.symlink_to(outside, target_is_directory=True)
        return real_open(path, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(sbs_seed.os, 'open', replace_before_payload)
    with pytest.raises(ValueError, match='escapes|changed'):
        capture_event_seed(seed_root, 'event', source)
    assert injected
    assert list(outside.iterdir()) == []
    assert (retained / 'input_upload_sbs.tif').read_bytes() == source.read_bytes()
    assert json.loads((retained / 'status.json').read_text())['status'] == 'failed'
