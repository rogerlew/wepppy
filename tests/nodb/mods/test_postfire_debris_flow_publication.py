from pathlib import Path

import pytest

from wepppy.nodb.mods.postfire_debris_flow import preflight, publication
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow

pytestmark = pytest.mark.unit


@pytest.fixture
def accepted_project(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, 'notify', lambda wd: None)
    controller = PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    def accept(identity, value=b'accepted', hook=True):
        nonlocal controller
        controller = PostfireDebrisFlow.getInstance(str(tmp_path))
        root = p.directory(tmp_path, identity)/'results'
        root.mkdir(parents=True)
        for name in p.FILES:
            (root/name).write_bytes(value + name.encode())
        record = {'id': identity, 'snapshot': {}, 'completed_at': p.now(), 'partial': True,
                  'artifacts': {str((root/name).relative_to(tmp_path)): p.signature(tmp_path, root/name, strong=True)
                                for name in p.FILES}}
        if hook:
            controller.change(lambda state: state.update(last_successful_run=record))
        else:
            with controller.locked():
                controller._state['last_successful_run'] = record
        return root
    return controller, accept, tmp_path/'postfire_debris_flow'


def test_absent_and_empty_are_noop(tmp_path):
    assert publication.publish_outputs(tmp_path) == []
    assert not (tmp_path/'postfire_debris_flow.nodb').exists()
    PostfireDebrisFlow(str(tmp_path), 'disturbed9002_wbt.cfg')
    assert publication.publish_outputs(tmp_path) == []
    assert not (tmp_path/'postfire_debris_flow').exists()


def test_completion_hook_publishes_partial_replaces_and_keeps_originals(accepted_project):
    controller, accept, output = accepted_project
    first = accept('a'*32)
    for name in p.FILES:
        assert (output/name).read_bytes() == (first/name).read_bytes()
    second = accept('b'*32, b'new')
    for name in p.FILES:
        assert (output/name).read_bytes() == (second/name).read_bytes()
        assert (first/name).read_bytes().startswith(b'accepted')
    controller.change(lambda state: state.update(run_attempt={
        'id': 'c'*32, 'snapshot': {}, 'phase': 'failed', 'created_at': p.now(), 'retryable': True}))
    assert (output/'events.parquet').read_bytes().startswith(b'new')
    assert not list(output.glob('.publish-*'))


@pytest.mark.parametrize('damage', ['source', 'source_symlink', 'destination_symlink', 'destination_directory'])
def test_bad_last_file_preserves_all_visible_outputs(accepted_project, damage):
    controller, accept, output = accepted_project
    accept('a'*32)
    before = {name: (output/name).read_bytes() for name in p.FILES}
    source = accept('b'*32, b'new', hook=False)
    last = source/'manifest.json'
    if damage == 'source':
        last.write_bytes(b'tampered')
    elif damage == 'source_symlink':
        last.unlink()
        last.symlink_to(output/'manifest.json')
    else:
        target = output/'manifest.json'
        target.unlink()
        if damage == 'destination_symlink':
            target.symlink_to(source/'manifest.json')
        else:
            target.mkdir()
    with pytest.raises(p.WorkflowError):
        publication.publish_outputs(controller.wd)
    for name in p.FILES[:-1]:
        assert (output/name).read_bytes() == before[name]
    assert not list(output.glob('.publish-*'))


@pytest.mark.parametrize('fail_at', [0, 1, 3])
def test_interrupted_publication_repairs_without_recomputation(accepted_project, monkeypatch, fail_at):
    controller, accept, output = accepted_project
    accept('a'*32)
    latest = accept('b'*32, b'new', hook=False)
    before_state = Path(controller.wd, controller.filename).read_bytes()
    real_replace = publication.os.replace
    calls = []
    def fail(src, dst):
        if Path(dst).parent == output and Path(dst).name in p.FILES:
            calls.append(Path(dst).name)
            if len(calls) == fail_at+1:
                raise OSError('injected output installation failure')
        real_replace(src, dst)
    with monkeypatch.context() as patch:
        patch.setattr(publication.os, 'replace', fail)
        with pytest.raises(OSError, match='injected'):
            publication.publish_outputs(controller.wd)
    assert calls == list(p.FILES[:fail_at+1])
    import json
    retained = [folder for folder in (output/'publication_work').iterdir()
                if json.loads((folder/'status.json').read_text())['status'] == 'incomplete']
    assert len(retained) == 1
    assert (retained[0]/'manifest.json').is_file()
    assert Path(controller.wd, controller.filename).read_bytes() == before_state
    publication.publish_outputs(controller.wd)
    assert Path(controller.wd, controller.filename).read_bytes() == before_state
    for name in p.FILES:
        assert (output/name).read_bytes() == (latest/name).read_bytes()
    assert not list(output.glob('.publish-*'))


def test_delayed_callback_reads_latest_accepted_state(accepted_project):
    controller, accept, output = accepted_project
    accept('a'*32)
    latest = accept('b'*32, b'latest', hook=False)
    publication.publish_outputs(controller.wd)
    assert (output/'manifest.json').read_bytes() == (latest/'manifest.json').read_bytes()


@pytest.mark.parametrize('damage', ['recorded_hash', 'copied_hash'])
def test_hash_failure_before_install_preserves_prior_outputs(accepted_project, monkeypatch, damage):
    controller, accept, output = accepted_project
    accept('a'*32)
    prior = {name: (output/name).read_bytes() for name in p.FILES}
    accept('b'*32, b'new', hook=False)
    if damage == 'recorded_hash':
        controller = PostfireDebrisFlow.getInstance(controller.wd)
        with controller.locked():
            for expected in controller._state['last_successful_run']['artifacts'].values():
                expected[-1] = '0'*64  # Same file/stat, incorrect accepted hash.
    else:
        monkeypatch.setattr(p, 'digest', lambda path: '0'*64)
    with pytest.raises(p.WorkflowError, match='files changed'):
        publication.publish_outputs(controller.wd)
    assert {name: (output/name).read_bytes() for name in p.FILES} == prior
    assert not list(output.glob('.publish-*'))


def test_hook_failure_retains_accepted_state_for_republication(accepted_project, monkeypatch):
    controller, accept, output = accepted_project
    accept('a'*32)
    real_replace = publication.os.replace
    def fail_public_output(src, dst):
        if Path(dst) == output/'events.parquet':
            raise OSError('output installation failure')
        real_replace(src, dst)
    with monkeypatch.context() as patch:
        patch.setattr(publication.os, 'replace', fail_public_output)
        with pytest.raises(OSError, match='output installation failure'):
            accept('b'*32, b'new')
    loaded = PostfireDebrisFlow.load_detached(controller.wd)
    assert loaded.state['last_successful_run']['id'] == 'b'*32
    assert (output/'events.parquet').read_bytes().startswith(b'accepted')
    publication.publish_outputs(controller.wd)
    assert (output/'events.parquet').read_bytes().startswith(b'new')
