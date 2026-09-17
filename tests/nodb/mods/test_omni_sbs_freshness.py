"""SBS receipts bind reuse and admission without consuming a newer upload."""
from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.omni import omni_sbs_freshness as freshness
from wepppy.nodb.mods.omni.omni import _scenario_name_from_scenario_definition

pytestmark = pytest.mark.unit


def owner(tmp_path):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'class-one')
    definition = {'type': 'sbs_map', 'sbs_file_path': str(source)}
    omni = SimpleNamespace(wd=str(tmp_path), scenarios=[definition], scenario_dependency_tree={})
    return omni, definition, source


def accept(omni, definition, signature):
    name = _scenario_name_from_scenario_definition(definition)
    omni.scenario_dependency_tree[name] = {'signature': signature, 'runid': 'child'}
    return name


def test_signature_content_and_consumed_receipt(tmp_path):
    omni, definition, source = owner(tmp_path)
    initial = freshness.scenario_signature(omni, definition)
    times = source.stat()
    source.write_bytes(b'class-tri')
    os.utime(source, ns=(times.st_atime_ns, times.st_mtime_ns))
    assert freshness.scenario_signature(omni, definition) != initial
    source.write_bytes(b'class-one')
    assert freshness.scenario_signature(omni, definition) == initial
    accept(omni, definition, initial)
    child = freshness.child_source(omni, definition)
    child.parent.mkdir(parents=True)
    execution = freshness.SbsExecution.capture(definition, initial)
    execution.copy_to(child)
    assert not source.exists()
    assert freshness.scenario_signature(omni, definition) == initial
    child.write_bytes(b'class-tri')
    with pytest.raises(OSError) as error:
        freshness.scenario_signature(omni, definition)
    assert error.value.errno == errno.ESTALE


def test_legacy_reuse_cannot_resurrect_invalidated_association(tmp_path):
    omni, definition, source = owner(tmp_path)
    source.unlink()
    signature = freshness.scenario_signature(omni, definition)
    name = accept(omni, definition, signature)
    reuse = freshness.SbsReuse.capture(omni, definition, signature)
    reuse.validate_admission(omni)
    del omni.scenario_dependency_tree[name]
    with pytest.raises(OSError) as error:
        reuse.validate_admission(omni)
    assert error.value.errno == errno.ESTALE


@pytest.mark.parametrize('alias', ['hardlink', 'symlink', 'same_path'])
def test_copy_rejects_same_file_without_truncation(tmp_path, alias):
    _, definition, source = owner(tmp_path)
    target = tmp_path / 'target.tif'
    if alias == 'hardlink':
        os.link(source, target)
    elif alias == 'symlink':
        target.symlink_to(source)
    else:
        target = source
    execution = freshness.SbsExecution.capture(definition)
    with pytest.raises(shutil.SameFileError):
        execution.copy_to(target)
    assert source.read_bytes() == b'class-one'


def test_admission_rechecks_child_after_replacement_upload_observation(tmp_path, monkeypatch):
    omni, definition, source = owner(tmp_path)
    execution = freshness.SbsExecution.capture(definition)
    target = tmp_path / 'copied.tif'
    execution.copy_to(target)
    source.write_bytes(b'class-one')
    original = freshness.sha256_file

    def mutate_child(path):
        result = original(path)
        if Path(path) == source:
            target.write_bytes(b'class-tri')
        return result

    monkeypatch.setattr(freshness, 'sha256_file', mutate_child)
    with pytest.raises(OSError) as error:
        execution.validate_admission(omni)
    assert error.value.errno == errno.ESTALE


def test_copy_preserves_observed_newer_upload(tmp_path, monkeypatch):
    _, definition, source = owner(tmp_path)
    execution = freshness.SbsExecution.capture(definition)
    target = tmp_path / 'copied.tif'
    original = freshness.sha256_file

    def replace_upload(path):
        result = original(path)
        if Path(path) == target:
            source.write_bytes(b'class-tri')
        return result

    monkeypatch.setattr(freshness, 'sha256_file', replace_upload)
    with pytest.raises(OSError):
        execution.copy_to(target)
    assert source.read_bytes() == b'class-tri'
    assert target.read_bytes() == b'class-one'


def test_path_input_and_reserved_receipt_do_not_change_definition(tmp_path):
    omni, definition, source = owner(tmp_path)
    definition['sbs_file_path'] = source
    definition['_sbs_content'] = {'untrusted': True}
    signature = freshness.scenario_signature(omni, definition)
    execution = freshness.SbsExecution.capture(definition, signature)
    execution.before_reset(omni)
    assert '_sbs_content' not in json.loads(freshness.definition_json(definition))
    non_sbs = {'type': 'unchanged_non_sbs', '_sbs_content': 'ordinary-field'}
    assert json.loads(freshness.definition_json(non_sbs)) == non_sbs


def test_legacy_ineligible_execution_preserves_missing_upload_error(tmp_path):
    omni, definition, source = owner(tmp_path)
    source.unlink()
    signature = freshness.scenario_signature(omni, definition)
    with pytest.raises(FileNotFoundError):
        freshness.SbsExecution.capture(definition, signature)


def test_selection_matches_existing_rq_integer_normalization(tmp_path):
    omni, definition, _ = owner(tmp_path)
    omni.scenarios = [dict(definition, type=8)]
    execution = freshness.SbsExecution.capture(definition, require_selection=True)
    execution.before_reset(omni)
    omni.scenarios = [dict(definition, sbs_file_path='another-upload.tif')]
    with pytest.raises(OSError) as error:
        execution.before_reset(omni)
    assert error.value.errno == errno.ESTALE


def test_equal_byte_new_inode_during_final_digest_is_not_consumed(tmp_path, monkeypatch):
    _, definition, source = owner(tmp_path)
    execution = freshness.SbsExecution.capture(definition)
    target = tmp_path / 'copied.tif'
    original = freshness.sha256_file

    def swap_source(path):
        if Path(path) == source:
            replacement = tmp_path / 'replacement.tif'
            replacement.write_bytes(b'class-one')
            replacement.replace(source)
        return original(path)

    monkeypatch.setattr(freshness, 'sha256_file', swap_source)
    with pytest.raises(OSError) as error:
        execution.copy_to(target)
    assert error.value.errno == errno.ESTALE
    assert source.read_bytes() == target.read_bytes() == b'class-one'
