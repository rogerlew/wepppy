"""Accepted generations survive replacement, cleanup and publication failures."""
from copy import deepcopy
from pathlib import Path

import pytest

from wepppy.nodb.single_input_sources import accept_source, read_source, write_generated_source
from wepppy.wepp.single_input import SingleInputError

pytestmark = pytest.mark.unit
SOL = Path(__file__).resolve().parents[2] / 'wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol'


class SourceController:
    mods = []
    def __init__(self, wd):
        self.wd = str(wd)
        self.durable = None
        self.failure = None
        self.locked = False
        type(self).instance = self
    def config_get_bool(self, *_args):
        return True
    def config_get_str(self, section, key, default=None):
        return "True" if key == "single_user_defined_uploads" else "wepp_260803"
    def lock(self):
        assert not self.locked
        self.locked = True
    def unlock(self):
        assert self.locked
        self.locked = False
    def dump(self):
        assert self.locked
        if self.failure == 'stale':
            from wepppy.nodb.base import NoDbStaleWriteError
            raise NoDbStaleWriteError('injected stale write')
        if self.failure == 'before':
            raise OSError('injected precommit failure')
        self.durable = deepcopy(self._single_user_defined_source)
        if self.failure == 'after':
            raise OSError('injected postcommit failure')
    @classmethod
    def getInstance(cls, _wd):
        return cls.instance
    @classmethod
    def load_detached(cls, _wd):
        value = object.__new__(cls)
        value._single_user_defined_source = deepcopy(cls.instance.durable)
        return value


def test_accept_reuse_normalize_retain_two_generations(tmp_path):
    controller = SourceController(tmp_path)
    raw = SOL.read_bytes()
    first = accept_source(controller, 'soils', raw, 'First.SOL')
    assert read_source(controller, 'soils')[0] == raw
    generated = Path(write_generated_source(controller, 'soils'))
    assert generated.exists()
    assert (tmp_path / 'soils' / first['relative_path']).read_bytes() == raw
    second = accept_source(controller, 'soils', raw + b'\n# second\n', 'Second.sol')
    third = accept_source(controller, 'soils', raw + b'\n# third\n', 'Third.sol')
    assert not (tmp_path / 'soils' / first['relative_path']).exists()
    assert (tmp_path / 'soils' / second['relative_path']).exists()
    assert (tmp_path / 'soils' / third['relative_path']).exists()
    assert len(list((tmp_path / 'soils/single-user-defined').iterdir())) == 2


@pytest.mark.parametrize('failure', ['before', 'after'])
def test_failed_publication_uses_durable_pointer(tmp_path, failure):
    controller = SourceController(tmp_path)
    raw = SOL.read_bytes()
    old = accept_source(controller, 'soils', raw, 'Old.sol')
    controller.failure = failure
    with pytest.raises(SingleInputError, match='Unable to store'):
        accept_source(controller, 'soils', raw + b'\n# new\n', 'New.sol')
    assert not controller.locked
    assert controller._single_user_defined_source == controller.durable
    assert controller.durable['filename'] == ('Old.sol' if failure == 'before' else 'New.sol')
    assert len(list((tmp_path / 'soils/single-user-defined').iterdir())) == (1 if failure == 'before' else 2)
    assert (tmp_path / 'soils' / old['relative_path']).read_bytes() == raw
    read_source(controller, 'soils')


@pytest.mark.parametrize('malformed', [{}, {'relative_path': None}, 'bad'])
def test_valid_replacement_repairs_malformed_metadata(tmp_path, malformed):
    controller = SourceController(tmp_path)
    controller._single_user_defined_source = malformed
    with pytest.raises(SingleInputError) as error:
        read_source(controller, 'soils')
    assert error.value.status_code == 409
    accept_source(controller, 'soils', SOL.read_bytes(), 'Recovered.sol')
    assert read_source(controller, 'soils')[0] == SOL.read_bytes()


def test_rejection_preserves_source_and_metadata(tmp_path):
    controller = SourceController(tmp_path)
    metadata = accept_source(controller, 'soils', SOL.read_bytes(), 'Old.sol')
    with pytest.raises(SingleInputError):
        accept_source(controller, 'soils', b'not a soil', 'Bad.sol')
    assert controller.durable == metadata
    assert controller._single_user_defined_source == metadata


def test_external_root_and_child_symlinks_rejected(tmp_path):
    run = tmp_path / 'run'; run.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    controller = SourceController(run)
    (run / 'soils').symlink_to(outside, target_is_directory=True)
    with pytest.raises(SingleInputError):
        accept_source(controller, 'soils', SOL.read_bytes(), 'File.sol')
    assert list(outside.iterdir()) == []
    (run / 'soils').unlink(); (run / 'soils').mkdir()
    (run / 'soils/single-user-defined').symlink_to(outside, target_is_directory=True)
    with pytest.raises(SingleInputError):
        accept_source(controller, 'soils', SOL.read_bytes(), 'File.sol')
    assert list(outside.iterdir()) == []


def test_managed_projection_root_accepts_source(tmp_path):
    controller = SourceController(tmp_path)
    managed = tmp_path / '.nodir/upper/soils'; managed.mkdir(parents=True)
    (tmp_path / 'soils').symlink_to(managed, target_is_directory=True)
    accept_source(controller, 'soils', SOL.read_bytes(), 'File.sol')
    assert read_source(controller, 'soils')[0] == SOL.read_bytes()


def test_readonly_rejected_before_creating_source_directory(tmp_path):
    controller = SourceController(tmp_path)
    (tmp_path / 'READONLY').touch()
    with pytest.raises(SingleInputError) as error:
        accept_source(controller, 'soils', SOL.read_bytes(), 'File.sol')
    assert error.value.status_code == 403
    assert not (tmp_path / 'soils').exists()
    assert controller.durable is None


def test_failed_repair_of_malformed_metadata_removes_candidate(tmp_path):
    controller = SourceController(tmp_path)
    controller.durable = 'bad'
    controller._single_user_defined_source = 'bad'
    controller.failure = 'before'
    with pytest.raises(SingleInputError):
        accept_source(controller, 'soils', SOL.read_bytes(), 'Repair.sol')
    assert controller._single_user_defined_source == 'bad'
    assert list((tmp_path / 'soils/single-user-defined').iterdir()) == []


def test_idle_replacement_removes_only_owned_regular_staging(tmp_path):
    controller = SourceController(tmp_path)
    first = accept_source(controller, 'soils', SOL.read_bytes(), 'First.sol')
    root = tmp_path / 'soils/single-user-defined'
    stale = [root / ('.source-' + 'a' * 32), root / ('.validate-' + 'b' * 32 + '.man')]
    for path in stale:
        path.write_text('interrupted')
    unrelated = root / '.source-other'; unrelated.write_text('keep')
    directory = root / ('.source-' + 'c' * 32); directory.mkdir()
    link = root / ('.source-' + 'd' * 32); link.symlink_to(unrelated)
    accept_source(controller, 'soils', SOL.read_bytes() + b'\n# replacement\n', 'Next.sol')
    assert all(not path.exists() for path in stale)
    assert unrelated.read_text() == 'keep'
    assert directory.is_dir() and link.is_symlink()
    assert (tmp_path / 'soils' / first['relative_path']).exists()


def test_stale_metadata_conflict_preserves_previous_generation(tmp_path):
    controller = SourceController(tmp_path)
    old = accept_source(controller, 'soils', SOL.read_bytes(), 'Old.sol')
    controller.failure = 'stale'
    with pytest.raises(SingleInputError) as error:
        accept_source(controller, 'soils', SOL.read_bytes() + b'\n# candidate\n', 'Next.sol')
    assert error.value.status_code == 409 and error.value.code == 'conflict'
    assert controller.durable == old
    assert controller._single_user_defined_source == old
    assert len(list((tmp_path / 'soils/single-user-defined').iterdir())) == 1


@pytest.mark.parametrize('version', ['2006', '2006.2', '7777', '9002'])
def test_new_format_publication_reuse_and_rejected_replacement(tmp_path, version):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    raw = (SOL.parents[6] / f'tests/data/single_input_soils/{version}.sol').read_bytes()
    controller = SourceController(tmp_path)
    metadata = accept_source(controller, 'soils', raw, f'Uploaded {version}.SOL')
    assert metadata['version'] == version
    assert read_source(controller, 'soils')[0] == raw
    generated = Path(write_generated_source(controller, 'soils'))
    assert '#' not in generated.read_text()
    assert WeppSoilUtil(str(generated), preserve_input_format=True).obj['datver'] == float(version)
    with pytest.raises(SingleInputError):
        accept_source(controller, 'soils', raw + b'\n42\n', 'Rejected.sol')
    assert controller.durable == metadata
    assert read_source(controller, 'soils')[0] == raw
    assert (tmp_path / 'soils' / metadata['relative_path']).read_bytes() == raw
