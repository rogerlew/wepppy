"""Bounded S01 filesystem/copy/admission probes; no model or named run."""
from contextlib import nullcontext
import errno
import json
import logging
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace
import uuid

import pytest

from wepppy.nodb.mods.omni.omni import Omni, OmniScenario, _scenario_name_from_scenario_definition
from wepppy.nodb.mods.omni import omni_mode_build_services as mode
from wepppy.nodb.mods.omni import omni_sbs_freshness as fresh


RESULTS = {}


def record(name, value):
    RESULTS[name] = value
    Path(__file__).with_suffix('.json').write_text(json.dumps(RESULTS, indent=2, default=str) + '\n')
    print(json.dumps({name: value}, default=str))


def definition(source):
    return {'type': OmniScenario.SBSmap, 'sbs_file_path': str(source)}


def capture_error(callback):
    try:
        callback()
    except (OSError, ValueError) as exc:
        return {'type': type(exc).__name__, 'errno': getattr(exc, 'errno', None), 'message': str(exc)}
    return None


def make_execution(tmp_path):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'accepted original main bytes')
    selected = definition(source)
    execution = fresh.SbsExecution.capture(selected)
    target = tmp_path / 'child.tif'
    execution.copy_to(target)
    return source, target, selected, execution


def test_child_change_during_replacement_upload_observation_rejects(tmp_path, monkeypatch):
    source, child, selected, execution = make_execution(tmp_path)
    source.write_bytes(child.read_bytes())
    original = fresh.sha256_file
    mutated = []

    def digest(path):
        result = original(path)
        if Path(path) == source:
            child.write_bytes(b'native child changed after last child guard')
            mutated.append(True)
        return result

    monkeypatch.setattr(fresh, 'sha256_file', digest)
    error = capture_error(lambda: execution.validate_admission(SimpleNamespace(scenarios=[selected])))
    record('joint_guard', {'error': error, 'mutated': bool(mutated), 'child': child.read_text()})
    assert mutated and error is not None and error['errno'] == errno.ESTALE


def test_actual_mode_same_inode_rejects_before_source_truncation(tmp_path):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'only copy of the uploaded bytes')
    child_dir = tmp_path / 'disturbed'
    child_dir.mkdir()
    child = child_dir / source.name
    os.link(source, child)
    before = source.read_bytes()
    with pytest.raises(shutil.SameFileError):
        shutil.copyfile(source, child)
    assert source.read_bytes() == before
    owner = SimpleNamespace(logger=logging.getLogger(__name__), timed=lambda _: nullcontext(),
                            rq_job_pool_max_worker_per_scenario_task=1)
    error = capture_error(lambda: mode.OmniModeBuildServices().apply_scenario_mode(
        owner, scenario_name='sbs_map_probe', scenario=OmniScenario.SBSmap,
        scenario_def=definition(source), new_wd=str(tmp_path),
        disturbed=SimpleNamespace(disturbed_dir=str(child_dir), validate=lambda *a, **k: None),
        landuse=SimpleNamespace(build=lambda: None), soils=SimpleNamespace(build=lambda **kwargs: None),
        omni_base_scenario_name=None))
    record('same_inode', {'error': error, 'source_bytes': source.read_text(),
                          'old_copy_preserved': before.decode()})
    assert error is not None
    assert source.read_bytes() == before and child.read_bytes() == before


def test_newer_upload_is_preserved_at_copy_verification(tmp_path, monkeypatch):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'old uploaded main')
    target = tmp_path / 'child.tif'
    execution = fresh.SbsExecution.capture(definition(source))
    original = fresh.sha256_file
    changed = []

    def digest(path):
        result = original(path)
        if Path(path) == target and not changed:
            pending = tmp_path / 'replacement'
            pending.write_bytes(b'new uploaded main')
            pending.replace(source)
            changed.append(True)
        return result

    monkeypatch.setattr(fresh, 'sha256_file', digest)
    error = capture_error(lambda: execution.copy_to(target))
    record('newer_upload', {'error': error, 'source': source.read_text(), 'child': target.read_text()})
    assert error is not None and error['errno'] == errno.ESTALE
    assert source.read_bytes() == b'new uploaded main'
    assert target.read_bytes() == b'old uploaded main'


def test_source_and_destination_alias_modes_follow_existing_copy_authority(tmp_path):
    physical_source = tmp_path / 'source.data'
    physical_source.write_bytes(b'alias supported bytes')
    selected = tmp_path / 'selected.tif'
    selected.symlink_to(physical_source)
    physical_target = tmp_path / 'output.data'
    physical_target.write_bytes(b'prior')
    physical_target.chmod(0o640)
    target = tmp_path / 'child.tif'
    target.symlink_to(physical_target)
    execution = fresh.SbsExecution.capture(definition(selected))
    execution.copy_to(target)
    execution.validate_admission(SimpleNamespace(scenarios=[definition(selected)]))
    assert not selected.is_symlink() and physical_source.read_bytes() == b'alias supported bytes'
    assert target.is_symlink() and physical_target.read_bytes() == b'alias supported bytes'
    assert stat.S_IMODE(physical_target.stat().st_mode) == 0o640
    record('aliases', {'source_target_retained': True, 'destination_alias_retained': True, 'mode': 0o640})


def test_readonly_copy_target_preserves_prior_bytes_and_source(tmp_path):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'new bytes')
    target = tmp_path / 'child.tif'
    target.write_bytes(b'prior bytes')
    target.chmod(0o444)
    execution = fresh.SbsExecution.capture(definition(source))
    error = capture_error(lambda: execution.copy_to(target))
    record('readonly_target', {'uid': os.geteuid(), 'error': error})
    assert error is not None and error['type'] == 'PermissionError'
    assert source.read_bytes() == b'new bytes' and target.read_bytes() == b'prior bytes'


def test_consumed_receipt_denied_present_upload_cannot_reuse_child(tmp_path):
    source = tmp_path / 'denied' / 'upload.tif'
    source.parent.mkdir()
    source.write_bytes(b'accepted')
    selected = definition(source)
    owner = SimpleNamespace(wd=str(tmp_path), scenario_dependency_tree={})
    signature = fresh.scenario_signature(owner, selected)
    child = fresh.child_source(owner, selected)
    child.parent.mkdir(parents=True)
    child.write_bytes(source.read_bytes())
    owner.scenario_dependency_tree[_scenario_name_from_scenario_definition(selected)] = {'signature': signature}
    source.parent.chmod(0o000)
    try:
        error = capture_error(lambda: fresh.scenario_signature(owner, selected))
    finally:
        source.parent.chmod(0o700)
    record('denied_present', {'error': error})
    assert error is not None and error['type'] == 'PermissionError'
    source.unlink()
    assert fresh.scenario_signature(owner, selected) == signature


def test_changed_then_restored_child_rejects_and_normal_siblings_do_not(tmp_path):
    source, child, selected, execution = make_execution(tmp_path)
    owner = SimpleNamespace(scenarios=[selected])
    (tmp_path / 'normal_native_output').write_bytes(b'allowed sibling')
    execution.validate_admission(owner)
    accepted = child.read_bytes()
    other = tmp_path / 'other-generation'
    other.write_bytes(b'intermediate native generation')
    other.replace(child)
    child.write_bytes(accepted)
    error = capture_error(lambda: execution.validate_admission(owner))
    record('child_aba', {'error': error, 'original_bytes_restored': child.read_bytes() == accepted})
    assert error is not None and error['errno'] == errno.ESTALE


def test_real_locked_admission_refreshes_durable_fields_and_uses_one_lock(tmp_path, monkeypatch):
    run = tmp_path / ('security-omni-' + uuid.uuid4().hex)
    run.mkdir()
    source = run / 'upload.tif'
    source.write_bytes(b'accepted bytes')
    selected = definition(source)
    owner = Omni(str(run), '0.cfg')
    with owner.locked():
        owner._scenarios = [selected]
        owner._scenario_dependency_tree = {'unrelated': {'value': 'original'}}
        owner._security_probe_marker = 'original'
    execution = fresh.SbsExecution.capture(selected, require_selection=True)
    target = run / 'child.tif'
    execution.copy_to(target)
    newer = Omni.load_detached(str(run))
    with newer.locked():
        newer._security_probe_marker = 'new durable value'
        newer._scenario_dependency_tree['unrelated'] = {'value': 'new durable value'}
    original_lock = Omni.lock
    locks = []

    def observed_lock(self, *args, **kwargs):
        locks.append(self.wd)
        return original_lock(self, *args, **kwargs)

    monkeypatch.setattr(Omni, 'lock', observed_lock)
    name = _scenario_name_from_scenario_definition(selected)
    fresh.admit_sbs_association(owner, execution, name,
        {'signature': json.dumps({**json.loads(fresh.definition_json(selected)),
                                  '_sbs_content': execution.receipt}, sort_keys=True)},
        {'scenario': name, 'status': 'ran'})
    loaded = Omni.load_detached(str(run))
    record('locked_admission', {'locks': len(locks), 'marker': loaded._security_probe_marker,
                               'unrelated': loaded.scenario_dependency_tree['unrelated'],
                               'run_state': loaded.scenario_run_state})
    assert locks == [str(run)]
    assert loaded._security_probe_marker == 'new durable value'
    assert loaded.scenario_dependency_tree['unrelated'] == {'value': 'new durable value'}
    assert loaded.scenario_run_state[-1]['status'] == 'ran'
    owner.logger.info('Actual logging remains usable after locked refresh')


def test_destination_alias_retarget_at_open_rejects_before_truncation(tmp_path, monkeypatch):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'only uploaded copy')
    physical_target = tmp_path / 'output.data'
    physical_target.write_bytes(b'prior output')
    selected_target = tmp_path / 'child.tif'
    selected_target.symlink_to(physical_target)
    execution = fresh.SbsExecution.capture(definition(source))
    original = os.open
    changed = []

    def switched_open(path, flags, *args, **kwargs):
        if Path(path) == selected_target and flags & os.O_WRONLY:
            selected_target.unlink()
            selected_target.symlink_to(source)
            changed.append(True)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, 'open', switched_open)
    error = capture_error(lambda: execution.copy_to(selected_target))
    record('late_same_inode', {'error': error, 'source': source.read_text(),
                              'prior_output': physical_target.read_text()})
    assert changed and error is not None and error['type'] == 'SameFileError'
    assert source.read_bytes() == b'only uploaded copy'
    assert physical_target.read_bytes() == b'prior output'


def test_pathlib_selected_input_preserves_programmatic_compatibility(tmp_path):
    source = tmp_path / 'upload.tif'
    source.write_bytes(b'pathlike supported bytes')
    selected = {'type': OmniScenario.SBSmap, 'sbs_file_path': source}
    # Both old name derivation and copy accepted this standard path-like input.
    name = _scenario_name_from_scenario_definition(selected)
    shutil.copyfile(source, tmp_path / 'old-copy-control')
    owner = SimpleNamespace(wd=str(tmp_path), scenarios=[selected], scenario_dependency_tree={})
    signature = fresh.scenario_signature(owner, selected)
    execution = fresh.SbsExecution.capture(selected, signature, require_selection=True)
    execution.before_reset(owner)
    child = fresh.child_source(owner, selected)
    child.parent.mkdir(parents=True)
    execution.copy_to(child)
    execution.validate_admission(owner)
    owner.scenario_dependency_tree[name] = {'signature': signature}
    assert fresh.scenario_signature(owner, selected) == signature
    record('pathlike', {'name': name, 'receipt_source_type': type(execution.receipt['source_path']).__name__,
                        'copied_bytes': child.read_text()})
