"""Real filesystem generations must stay paired with their loaded NoDb bytes."""
import errno
import jsonpickle
import os
from pathlib import Path

import pytest

from wepppy.nodb import base, _read_retry as retry

pytestmark = pytest.mark.unit


class SnapshotProbe(base.NoDbBase):
    filename = 'snapshot_probe.nodb'
    replacement = None

    def _init_logging(self):
        pass

    @classmethod
    def _decode_jsonpickle(cls, text):
        instance = super()._decode_jsonpickle(text)
        if cls.replacement is not None:
            source, destination = cls.replacement
            os.replace(source, destination)
            cls.replacement = None
        return instance


@pytest.mark.parametrize('loader', ['hydrate', 'detached'])
def test_decode_time_replacement_cannot_relabel_old_bytes(tmp_path, monkeypatch, loader):
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    (tmp_path/'READONLY').touch()
    first = SnapshotProbe.__new__(SnapshotProbe)
    first.wd = str(tmp_path)
    first.value = 'A'
    target = tmp_path/SnapshotProbe.filename
    target.write_text(jsonpickle.encode(first))
    first_stat = target.stat()
    first.value = 'B'
    replacement = tmp_path/'replacement'
    replacement.write_text(jsonpickle.encode(first))
    os.utime(replacement, ns=(first_stat.st_atime_ns, first_stat.st_mtime_ns + 2000000000))
    monkeypatch.setattr(SnapshotProbe, 'replacement', (replacement, target))
    if loader == 'hydrate':
        observed = SnapshotProbe._hydrate_instance(str(tmp_path), False, False, True, use_redis_cache=False)
    else:
        observed = SnapshotProbe.load_detached(str(tmp_path))
    assert observed.value == 'A'
    assert observed._nodb_mtime == first_stat.st_mtime
    matches, _ = SnapshotProbe._cache_instance_matches_file_signature(instance=observed, filepath=str(target))
    assert not matches


def test_open_descriptor_replacement_preserves_complete_old_snapshot(tmp_path, monkeypatch):
    source = tmp_path/'state.nodb'
    source.write_text('old Unicode: café\n')
    old = source.stat()
    replacement = tmp_path/'replacement'
    replacement.write_text('new Unicode: 東京\n')
    real_open = open
    class ReplacingReader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self):
            text = self.stream.read()
            os.replace(replacement, source)
            return text
    def replacing_open(*args, **kwargs):
        return ReplacingReader(real_open(*args, **kwargs))
    monkeypatch.setattr(retry, 'open', replacing_open, raising=False)
    text, observed = retry.read_text_snapshot(str(source))
    assert text == 'old Unicode: café\n'
    assert (observed.st_ino, observed.st_size, observed.st_mtime_ns) == (old.st_ino, old.st_size, old.st_mtime_ns)
    assert source.read_text() == 'new Unicode: 東京\n'


def test_snapshot_absence_and_original_permission_error(tmp_path, monkeypatch):
    path = str(tmp_path/'missing')
    assert retry.read_text_snapshot(path, allow_missing=True) is None
    with pytest.raises(FileNotFoundError):
        retry.read_text_snapshot(path)
    original = PermissionError(errno.EACCES, 'denied', path)
    def denied(*args, **kwargs):
        raise original
    monkeypatch.setattr(retry, 'open', denied, raising=False)
    with pytest.raises(PermissionError) as caught:
        retry.read_text_snapshot(path)
    assert caught.value is original


@pytest.mark.parametrize('scoped', [False, True])
def test_snapshot_drift_retries_only_read_transaction(tmp_path, monkeypatch, scoped):
    from contextlib import nullcontext
    from types import SimpleNamespace
    path = tmp_path/'state'
    path.write_text('initial')
    real_open = open
    attempts = []
    clock = [0.0]
    def sleep(delay):
        clock[0] += delay
    monkeypatch.setattr(retry, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep))
    class ChangingReader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self):
            text = self.stream.read()
            if len(attempts) == 1:
                with real_open(path, 'a') as writer:
                    writer.write(' changed')
            return text
    def changing_open(*args, **kwargs):
        attempts.append(args[0])
        return ChangingReader(real_open(*args, **kwargs))
    monkeypatch.setattr(retry, 'open', changing_open, raising=False)
    context = retry.initial_read_retry(runid='snapshot', job_id='read') if scoped else nullcontext()
    with context:
        if scoped:
            text, version = retry.read_text_snapshot(str(path))
            assert text == 'initial changed'
            assert version.st_size == len(text)
            assert len(attempts) == 2 and clock[0] == 2
        else:
            with pytest.raises(OSError) as caught:
                retry.read_text_snapshot(str(path))
            assert caught.value.errno == errno.ESTALE
            assert caught.value.filename == str(path)
            assert len(attempts) == 1 and clock[0] == 0
