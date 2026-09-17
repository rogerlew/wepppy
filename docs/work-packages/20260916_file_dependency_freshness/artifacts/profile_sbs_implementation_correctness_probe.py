"""Disposable actual append/promotion/paired playback/Requests multipart probes.

No HTTP, named runs, Redis mutation or raster processing claim. Only controller
pointer discovery, unrelated config setup and transport/lock setup are isolated.
The real event stream, seed code, promotion, playback.run pairing and encoder run.
"""
from collections import deque
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.profile_recorder.assembler import ProfileAssembler
from wepppy.profile_recorder.playback import PlaybackSession
from wepppy.profile_recorder import playback, sbs_seed

ENDPOINT = '/rq-engine/api/runs/disposable-correctness/disturbed/tasks/upload-sbs/'
ONE = b'opaque-SBS-generation-one'
THREE = b'opaque-SBS-generation-three'


def record(name, result):
    target = Path(__file__).with_name('profile_sbs_correctness_' + name + '.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print('SBS_CORRECTNESS', name, json.dumps(result, sort_keys=True))


@pytest.fixture
def capture(tmp_path, monkeypatch):
    run = tmp_path / 'source'
    source = run / 'disturbed' / 'same.tiff'
    source.parent.mkdir(parents=True)
    source.write_bytes(ONE)
    monkeypatch.setattr(Disturbed, 'getInstance', lambda _: SimpleNamespace(disturbed_path=str(source)))
    monkeypatch.setattr(Baer, 'getInstance', lambda _: SimpleNamespace(baer_path=None))
    assembler = ProfileAssembler(tmp_path / 'data')
    monkeypatch.setattr(assembler, '_ensure_config_seed', lambda *args: None)

    def append(event_id, *, response=True):
        request = {'stage': 'request', 'id': event_id, 'method': 'POST',
                   'category': 'file_upload', 'endpoint': ENDPOINT,
                   'requestMeta': {'bodyType': 'form-data', 'request_id': 'not-the-event-id'}}
        assembler.handle_event('disposable-correctness', 'capture', request, run)
        if response:
            assembler.handle_event('disposable-correctness', 'capture',
                                   dict(request, stage='response', ok=True, status=200), run)

    def promote():
        promoted = assembler.promote_draft('disposable-correctness', 'capture', slug='probe')
        return Path(promoted['profile_root'])

    return assembler, source, append, promote


def make_playback(profile, tmp_path, monkeypatch, *, before_encode=None):
    wire = []

    def request(method, url, **kwargs):
        kwargs.pop('timeout', None)
        if before_encode is not None:
            before_encode()
        prepared = requests.Request(method, url, **kwargs).prepare()
        wire.append(prepared)
        response = requests.Response()
        response.status_code = 200
        response._content = b'{}'
        response.headers['Content-Type'] = 'application/json'
        return response

    monkeypatch.setattr(PlaybackSession, '_clear_playback_locks', lambda *args, **kwargs: None)
    monkeypatch.setattr(PlaybackSession, '_retag_run_group', lambda *args: None)
    monkeypatch.setattr(playback.time, 'sleep', lambda _: None)
    session = PlaybackSession(profile, base_url='https://disposable.invalid', execute=True,
                              run_dir=tmp_path / 'sandbox',
                              session=SimpleNamespace(request=request),
                              playback_run_id='profile;;tmp;;independent')
    return session, wire


def test_actual_ui_slash_two_events_pair_and_encode_own_bytes(capture, tmp_path, monkeypatch):
    _, source, append, promote = capture
    append('event-one')
    source.write_bytes(THREE)
    append('event-three')
    profile = promote()
    session, wire = make_playback(profile, tmp_path, monkeypatch)
    session.run()
    responses = [item for item in session.events if item['stage'] == 'response']
    result = {'response_markers': [item.get(sbs_seed.MARKER) for item in responses],
              'wire_count': len(wire), 'results': session.results,
              'paired_bytes': len(wire) == 2 and ONE in wire[0].body and THREE in wire[1].body,
              'retained_suffix_mime': len(wire) == 2 and all(
                  b'filename="input_upload_sbs.tiff"' in item.body and
                  b'Content-Type: application/octet-stream' in item.body for item in wire),
              'sandbox_urls': [item.url for item in wire]}
    record('paired_ui_slash', result)
    assert result['response_markers'] == [1, 1]
    assert result['wire_count'] == 2 and result['paired_bytes'] and result['retained_suffix_mime']
    assert THREE not in wire[0].body and ONE not in wire[1].body
    assert all('/runs/profile;;tmp;;independent/' in item.url for item in wire)


def test_missing_new_entry_stays_failed_after_promotion_and_paired_run(capture, tmp_path, monkeypatch):
    assembler, source, append, promote = capture
    append('event-one')
    source.write_bytes(THREE)

    def fail(*args):
        raise PermissionError('probe config capture failure before event entry')

    monkeypatch.setattr(assembler, '_ensure_config_seed', fail)
    append('event-three')
    profile = promote()
    session, wire = make_playback(profile, tmp_path, monkeypatch)
    session.run()
    result = {'events_preserved': len(session.events), 'wire_count': len(wire),
              'results': session.results, 'third_fails': 'error Unable to verify SBS' in session.results[-1][1]}
    record('missing_marked', result)
    assert len(session.events) == 4 and len(wire) == 1 and ONE in wire[0].body
    assert result['third_fails']


def test_unmarked_history_without_entry_keeps_legacy_bytes(capture, tmp_path, monkeypatch):
    _, _, append, promote = capture
    append('legacy')
    profile = promote()
    session, wire = make_playback(profile, tmp_path, monkeypatch)
    for event in session.events:
        event.pop(sbs_seed.MARKER, None)
        event['id'] = 'historical-no-entry'
    session.requests = session._index_requests(session.events)
    session.run()
    record('legacy', {'wire_count': len(wire), 'results': session.results})
    assert len(wire) == 1 and ONE in wire[0].body


@pytest.mark.parametrize('version', [True, 0, '1', None])
def test_bad_marker_fails_through_existing_result_boundary(capture, tmp_path, monkeypatch, version):
    _, _, append, promote = capture
    append('event')
    session, wire = make_playback(promote(), tmp_path, monkeypatch)
    session.events[-1][sbs_seed.MARKER] = version
    session.run()
    assert not wire
    assert 'Unsupported SBS seed expectation version' in session.results[-1][1]


def test_changed_path_after_verification_cannot_change_wire(capture, tmp_path, monkeypatch):
    _, _, append, promote = capture
    append('event')
    profile = promote()
    seed = profile / 'capture/seed/uploads/sbs/events' / hashlib.sha256(b'event').hexdigest() / 'input_upload_sbs.tiff'

    def swap():
        candidate = seed.with_suffix('.replacement')
        candidate.write_bytes(THREE)
        candidate.replace(seed)

    session, wire = make_playback(profile, tmp_path, monkeypatch, before_encode=swap)
    session.run()
    result = {'path_is_replaced': seed.read_bytes() == THREE,
              'wire_is_verified_prior': len(wire) == 1 and ONE in wire[0].body and THREE not in wire[0].body,
              'results': session.results}
    record('verified_wire', result)
    assert result['path_is_replaced'] and result['wire_is_verified_prior']


def test_duplicate_complete_does_not_rewrite_receipt(capture, tmp_path, monkeypatch):
    assembler, source, append, promote = capture
    append('duplicate')
    uploads = assembler.data_repo_root / 'profiles/_drafts/disposable-correctness/capture/seed/uploads'
    entry = uploads / 'sbs/events' / hashlib.sha256(b'duplicate').hexdigest()
    original = {p.name: (p.read_bytes(), p.stat().st_ino) for p in entry.iterdir()}
    source.write_bytes(THREE)
    append('duplicate')
    assert {p.name: (p.read_bytes(), p.stat().st_ino) for p in entry.iterdir()} == original
    profile = promote()
    retained = sbs_seed.read_event_seed(profile / 'capture/seed/uploads', 'duplicate', required=True)
    record('duplicate', {'completed_original_preserved': retained.payload == ONE,
                         'all_four_events_retained': len(PlaybackSession._load_events(profile / 'capture/events.jsonl')) == 4})
    assert retained.payload == ONE


def test_failed_capture_partial_is_promoted_and_retry_cannot_bless_it(capture, tmp_path, monkeypatch):
    assembler, source, append, promote = capture
    original = sbs_seed._read_stable
    changed = False

    def replace_source(path, **kwargs):
        nonlocal changed
        value = original(path, **kwargs)
        if kwargs.get('dir_fd') is not None and str(path).startswith('input_upload_sbs') and not changed:
            changed = True
            replacement = source.with_suffix('.replacement')
            replacement.write_bytes(THREE)
            replacement.replace(source)
        return value

    monkeypatch.setattr(sbs_seed, '_read_stable', replace_source)
    append('failed')
    monkeypatch.setattr(sbs_seed, '_read_stable', original)
    append('failed')
    profile = promote()
    entry = profile / 'capture/seed/uploads/sbs/events' / hashlib.sha256(b'failed').hexdigest()
    status = json.loads((entry / 'status.json').read_text())
    session, wire = make_playback(profile, tmp_path, monkeypatch)
    session.run()
    result = {'status': status['status'], 'partial_retained': (entry / 'input_upload_sbs.tiff').read_bytes() == ONE,
              'receipt_present': (entry / 'receipt.json').exists(), 'wire_count': len(wire), 'results': session.results}
    record('failed_duplicate', result)
    assert result['status'] == 'failed' and result['partial_retained']
    assert not result['receipt_present'] and not wire
    assert all('error Unable to verify SBS' in result[1] for result in session.results)


def test_unselected_optional_controller_failure_does_not_block_selected_source(capture, tmp_path, monkeypatch):
    _, _, append, promote = capture

    def denied(_):
        raise PermissionError('probe denied nonselected Baer controller')

    monkeypatch.setattr(Baer, 'getInstance', denied)
    append('selected-disturbed')
    session, wire = make_playback(promote(), tmp_path, monkeypatch)
    session.run()
    result = {'wire_count': len(wire), 'results': session.results,
              'selected_disturbed_sent': len(wire) == 1 and ONE in wire[0].body}
    record('unselected_denial', result)
    assert result['selected_disturbed_sent']
