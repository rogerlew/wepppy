"""Disposable SBS event path/access checks; no external endpoints or secrets."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from requests import RequestException

from wepppy.profile_recorder import sbs_seed
from wepppy.profile_recorder.assembler import ProfileAssembler


def record(name, **value):
    Path(__file__).with_name(f'profile_sbs_security_{name}.json').write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value))


def test_capture_replaced_event_directory_cannot_write_outside_root(tmp_path, monkeypatch):
    uploads, outside = tmp_path / 'uploads', tmp_path / 'outside'
    uploads.mkdir()
    outside.mkdir()
    source = tmp_path / 'source.tif'
    source.write_bytes(b'ordinary disposable profile payload')
    event_id = 'capture-boundary'
    entry = uploads / 'sbs/events' / hashlib.sha256(event_id.encode()).hexdigest()
    retained = entry.with_name(entry.name + '.retained')
    target = entry / 'input_upload_sbs.tif'
    original_open = Path.open
    changed = False

    def replace_before_payload_open(path, *args, **kwargs):
        nonlocal changed
        if path == target and args and args[0] == 'xb' and not changed:
            changed = True
            entry.rename(retained)
            entry.symlink_to(outside, target_is_directory=True)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', replace_before_payload_open)
    error = None
    try:
        sbs_seed.capture_event_seed(uploads, event_id, source)
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    outside_payload = outside / 'input_upload_sbs.tif'
    record('capture_directory_swap', error=error, swapped=changed,
           outside_written=outside_payload.exists(),
           retained_working_status=(retained / 'status.json').exists())
    assert changed and error is not None
    assert not outside_payload.exists()


def test_denied_selected_controller_path_does_not_capture_fallback(tmp_path, monkeypatch):
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.mods.baer import Baer
    run, uploads = tmp_path / 'run', tmp_path / 'uploads'
    denied = run / 'selected'
    denied.mkdir(parents=True)
    selected = denied / 'selected.tif'
    selected.write_bytes(b'selected original bytes')
    fallback = run / 'baer/fallback.tif'
    fallback.parent.mkdir()
    fallback.write_bytes(b'different fallback bytes')
    monkeypatch.setattr(Disturbed, 'getInstance', lambda *args: SimpleNamespace(disturbed_path=str(selected)))
    monkeypatch.setattr(Baer, 'getInstance', lambda *args: SimpleNamespace(baer_path=str(fallback)))
    denied.chmod(0)
    error = None
    try:
        ProfileAssembler(tmp_path / 'data')._snapshot_sbs_upload(uploads, run, event_id='denied-selection')
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        denied.chmod(0o700)
    captured = None
    try:
        seed = sbs_seed.read_event_seed(uploads, 'denied-selection', required=True)
        captured = seed.payload.decode()
    except RequestException:
        pass
    record('denied_selection', error=error, captured=captured)
    assert error is not None
    assert captured is None


def test_initial_outside_event_alias_is_rejected_without_write(tmp_path):
    uploads, outside = tmp_path / 'uploads', tmp_path / 'outside'
    outside.mkdir()
    events = uploads / 'sbs/events'
    events.mkdir(parents=True)
    (events / hashlib.sha256(b'outside-alias').hexdigest()).symlink_to(outside, target_is_directory=True)
    source = tmp_path / 'source.tif'
    source.write_bytes(b'ordinary source')
    with pytest.raises(ValueError):
        sbs_seed.capture_event_seed(uploads, 'outside-alias', source)
    assert not list(outside.iterdir())


def test_completed_duplicate_is_immutable_and_wrong_bytes_rejected(tmp_path):
    uploads, source = tmp_path / 'uploads', tmp_path / 'source.tif'
    source.write_bytes(b'first')
    sbs_seed.capture_event_seed(uploads, 'duplicate', source)
    first = sbs_seed.read_event_seed(uploads, 'duplicate', required=True)
    source.write_bytes(b'next!')
    with pytest.raises(ValueError, match='different selected bytes'):
        sbs_seed.capture_event_seed(uploads, 'duplicate', source)
    assert sbs_seed.read_event_seed(uploads, 'duplicate', required=True) == first


def test_required_missing_seed_fails_and_unmarked_absence_is_legacy(tmp_path):
    assert sbs_seed.read_event_seed(tmp_path, 'history') is None
    with pytest.raises(RequestException):
        sbs_seed.read_event_seed(tmp_path, 'marked', required=True)


def test_seed_payload_path_escape_rejected(tmp_path):
    source = tmp_path / 'source.tif'
    source.write_bytes(b'ordinary payload')
    uploads = tmp_path / 'uploads'
    sbs_seed.capture_event_seed(uploads, 'receipt-escape', source)
    entry = uploads / 'sbs/events' / hashlib.sha256(b'receipt-escape').hexdigest()
    receipt = entry / 'receipt.json'
    value = json.loads(receipt.read_text())
    value['payload'] = '../../../source.tif'
    receipt.write_text(json.dumps(value))
    with pytest.raises(RequestException):
        sbs_seed.read_event_seed(uploads, 'receipt-escape', required=True)
