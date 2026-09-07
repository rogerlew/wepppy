from __future__ import annotations

import errno
from types import SimpleNamespace

import pytest

from wepppy.nodb import _read_retry as retry
from wepppy.rq import wepp_rq_stage_prep as prep

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('entrypoint', [
    '_prep_multi_ofe_rq', '_prep_slopes_rq', '_prep_managements_rq',
    '_prep_soils_rq', '_prep_climates_rq', '_prep_remaining_rq',
])
def test_initial_preparation_reads_retry_but_translator_is_not_replayed(tmp_path, monkeypatch, entrypoint):
    path = tmp_path / 'controller.nodb'
    path.write_text('readable')
    calls = []
    sleeps = []
    now = [0.0]
    real_open = open

    def first_read_missing(*args, **kwargs):
        calls.append('read')
        if calls.count('read') == 1:
            raise FileNotFoundError(errno.ENOENT, 'injected transient', str(path))
        return real_open(*args, **kwargs)

    def sleep(delay):
        sleeps.append(delay)
        now[0] += delay

    def load(_wd):
        assert retry.read_retry_active()
        assert retry.read_text(str(path)) == 'readable'
        return SimpleNamespace(translator_factory=translate)

    original = FileNotFoundError(errno.ENOENT, 'translator must not be retried', str(path))

    def translate():
        calls.append('translate')
        assert not retry.read_retry_active()
        raise original

    monkeypatch.setattr(retry, 'open', first_read_missing, raising=False)
    monkeypatch.setattr(retry, 'time', SimpleNamespace(monotonic=lambda: now[0], sleep=sleep))
    monkeypatch.setattr(prep, 'get_current_job', lambda: SimpleNamespace(id='job'))
    monkeypatch.setattr(prep, 'get_wd', lambda _: str(tmp_path))
    monkeypatch.setattr(prep, 'Wepp', SimpleNamespace(getInstance=load))
    monkeypatch.setattr(prep, 'Watershed', SimpleNamespace(getInstance=load))
    monkeypatch.setattr(prep.StatusMessenger, 'publish', lambda *_: None)
    with pytest.raises(FileNotFoundError) as caught:
        getattr(prep, entrypoint)('run')
    assert caught.value is original
    assert calls.count('translate') == 1
    assert sleeps == [0.1]
    assert not retry.read_retry_active()


def test_preparation_mutation_failure_is_not_replayed(tmp_path, monkeypatch):
    calls = []
    original = OSError(errno.ESTALE, 'write failure')

    def mutate(_translator):
        assert not retry.read_retry_active()
        calls.append('mutation')
        raise original

    monkeypatch.setattr(prep, 'get_current_job', lambda: SimpleNamespace(id='job'))
    monkeypatch.setattr(prep, 'get_wd', lambda _: str(tmp_path))
    monkeypatch.setattr(prep, 'Wepp', SimpleNamespace(getInstance=lambda _: SimpleNamespace(_prep_soils=mutate)))
    monkeypatch.setattr(prep, 'Watershed', SimpleNamespace(getInstance=lambda _: SimpleNamespace(translator_factory=lambda: object())))
    monkeypatch.setattr(prep.StatusMessenger, 'publish', lambda *_: None)
    with pytest.raises(OSError) as caught:
        prep._prep_soils_rq('run')
    assert caught.value is original
    assert calls == ['mutation']
