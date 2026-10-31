"""Actual file recovery at manual publication boundaries, including held references."""
import logging
from pathlib import Path

import pytest

import wepppy.nodb.base as base
from wepppy.nodb import _derived_build, single_input_sources as sources
from tests.nodb.test_base_boundary_characterization import _DummyNoDb, _RedisStub
from tests.nodb.test_single_input_sources import SOL

pytestmark = pytest.mark.unit


@pytest.fixture
def controller(tmp_path, monkeypatch):
    monkeypatch.setattr(base, 'redis_lock_client', _RedisStub())
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    instance = _DummyNoDb(str(tmp_path))
    with instance.locked():
        instance.value = {'items': ['accepted']}
    instance = _DummyNoDb.getInstance(str(tmp_path))
    instance.logger = logging.getLogger(__name__)
    return instance


@pytest.mark.parametrize('stage', ['body', 'replace', 'after_commit'])
def test_derived_finalization_preserves_actual_durable_generation(controller, monkeypatch, stage):
    original_replace = base.os.replace
    def replace(src, dst):
        if stage == 'replace' and str(dst).endswith('.nodb'):
            raise OSError('replace interrupted')
        return original_replace(src, dst)
    monkeypatch.setattr(base.os, 'replace', replace)
    if stage == 'after_commit':
        monkeypatch.setattr(base, 'write_version', lambda *_: (_ for _ in ()).throw(OSError('metadata interrupted')))
    with pytest.raises((ValueError, OSError)):
        with _derived_build.finalize(controller):
            controller.value['items'].append('proposed')
            if stage == 'body':
                raise ValueError('domain interrupted')
    expected = {'items': ['accepted', 'proposed'] if stage == 'after_commit' else ['accepted']}
    assert controller.value == expected
    assert _DummyNoDb.load_detached(controller.wd).value == expected
    assert _DummyNoDb.getInstance(controller.wd) is controller


@pytest.mark.parametrize('stage', ['replace', 'after_commit'])
def test_source_acceptance_keeps_durable_pointer_and_source(controller, monkeypatch, stage):
    monkeypatch.setattr(sources, 'require_single_input_policy', lambda *_, **__: None)
    raw = SOL.read_bytes()
    first = sources.accept_source(controller, 'soils', raw, 'Accepted.sol')
    original_replace = base.os.replace
    def replace(src, dst):
        if str(dst).endswith('.nodb'):
            raise OSError('replace interrupted')
        return original_replace(src, dst)
    with monkeypatch.context() as fault:
        if stage == 'replace':
            fault.setattr(base.os, 'replace', replace)
        else:
            fault.setattr(base, 'write_version', lambda *_: (_ for _ in ()).throw(OSError('metadata interrupted')))
        with pytest.raises(sources.SingleInputError):
            sources.accept_source(controller, 'soils', raw + b'\n# next\n', 'Next.sol')
    durable = _DummyNoDb.load_detached(controller.wd)
    assert sources.source_metadata(controller) == sources.source_metadata(durable)
    selected = sources.source_metadata(controller)
    assert selected['filename'] == ('Next.sol' if stage == 'after_commit' else 'Accepted.sol')
    assert (Path(controller.wd) / 'soils' / selected['relative_path']).exists()
    assert (Path(controller.wd) / 'soils' / first['relative_path']).exists()
    with controller.locked():
        controller.unrelated = 'accepted later'
    assert sources.source_metadata(_DummyNoDb.load_detached(controller.wd)) == selected


@pytest.mark.parametrize('stage', ['body', 'replace', 'after_commit', 'unknown_cancel'])
def test_derived_artifacts_track_commit_without_swallowing_cancellation(controller, monkeypatch, stage):
    wd = Path(controller.wd)
    destination = wd / 'derived'
    destination.mkdir()
    target = destination / 'input.txt'
    target.write_text('accepted')
    staged = destination / 'attempt'
    staged.mkdir()
    (staged / target.name).write_text('proposed')
    original_replace = base.os.replace
    original_read = Path.read_text
    nodb = Path(controller._nodb)
    def replace(src, dst):
        if stage == 'replace' and Path(dst) == nodb:
            raise OSError('replace interrupted')
        return original_replace(src, dst)
    def version(*_):
        if stage == 'unknown_cancel':
            raise KeyboardInterrupt('cancelled after replace')
        raise OSError('metadata interrupted')
    def read(path, *args, **kwargs):
        if stage == 'unknown_cancel' and path == nodb:
            raise OSError('classification unavailable')
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(base.os, 'replace', replace)
    monkeypatch.setattr(Path, 'read_text', read)
    if stage in ('after_commit', 'unknown_cancel'):
        monkeypatch.setattr(base, 'write_version', version)
    with pytest.raises((ValueError, OSError, KeyboardInterrupt)) as failure:
        with _derived_build.finalize(controller) as publications:
            publications.enter_context(_derived_build.publish_files(staged, destination, controller))
            controller.value['items'].append('proposed')
            if stage == 'body':
                raise ValueError('domain interrupted')
    committed = stage in ('after_commit', 'unknown_cancel')
    assert target.read_text() == ('proposed' if committed else 'accepted')
    assert controller.value['items'] == (['accepted', 'proposed'] if committed else ['accepted'])
    if stage == 'unknown_cancel':
        assert isinstance(failure.value, KeyboardInterrupt)
        assert 'commit outcome unknown' in ' '.join(failure.value.__notes__)
        retained = list(destination.glob('derived-backup-*'))
        assert len(retained) == 1
        assert (retained[0] / target.name).read_text() == 'accepted'


def test_source_recovery_failure_retains_candidate_and_primary_until_safe_refresh(controller, monkeypatch):
    monkeypatch.setattr(sources, 'require_single_input_policy', lambda *_, **__: None)
    raw = SOL.read_bytes()
    first = sources.accept_source(controller, 'soils', raw, 'Accepted.sol')
    wd = controller.wd
    original_snapshot = base._read_retry.read_text_snapshot
    failed = False
    def replace(*_):
        nonlocal failed
        failed = True
        raise OSError('primary replace failure')
    def snapshot(*args, **kwargs):
        if failed:
            raise OSError('recovery unavailable')
        return original_snapshot(*args, **kwargs)
    with monkeypatch.context() as fault:
        fault.setattr(base.os, 'replace', replace)
        fault.setattr(base._read_retry, 'read_text_snapshot', snapshot)
        with pytest.raises(sources.SingleInputError) as error:
            sources.accept_source(controller, 'soils', raw + b'\n# candidate\n', 'Next.sol')
        assert 'primary replace failure' in str(error.value.__cause__)
        assert 'recovery unavailable' in ' '.join(error.value.__cause__.__notes__)
        with pytest.raises(RuntimeError, match='unavailable after a failed mutation'):
            sources.source_metadata(controller)
    # Do not delete possibly referenced bytes when recovery could not read truth.
    assert len(list((Path(wd) / 'soils/single-user-defined').glob('*.sol'))) == 2
    controller.recover_mutation_state()
    assert sources.source_metadata(controller) == first
    with controller.locked():
        controller.unrelated = 'safe follow-up'
    assert sources.source_metadata(_DummyNoDb.load_detached(wd)) == first


def test_source_cleanup_cancellation_propagates_with_primary_context(controller, monkeypatch):
    monkeypatch.setattr(sources, 'require_single_input_policy', lambda *_, **__: None)
    raw = SOL.read_bytes()
    sources.accept_source(controller, 'soils', raw, 'Accepted.sol')
    original_snapshot = base._read_retry.read_text_snapshot
    failed = False
    def replace(*_):
        nonlocal failed
        failed = True
        raise OSError('primary replace failure')
    def snapshot(*args, **kwargs):
        if failed:
            raise KeyboardInterrupt('cancelled recovery')
        return original_snapshot(*args, **kwargs)
    with monkeypatch.context() as fault:
        fault.setattr(base.os, 'replace', replace)
        fault.setattr(base._read_retry, 'read_text_snapshot', snapshot)
        with pytest.raises(KeyboardInterrupt, match='cancelled recovery') as error:
            sources.accept_source(controller, 'soils', raw + b'\n# candidate\n', 'Next.sol')
        chain = []
        exception = error.value
        while exception is not None:
            chain.append(str(exception))
            exception = exception.__cause__ or exception.__context__
        assert any('primary replace failure' in text for text in chain)
    controller.recover_mutation_state()
    assert sources.source_metadata(controller)['filename'] == 'Accepted.sol'
