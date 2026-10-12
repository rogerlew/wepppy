"""Exercise the real native writer and publication/rollback boundary."""
import json
from pathlib import Path
import shutil

import pytest

from wepppy.weppcloud.combined_viewer_preparation import prepare, rollback, digest


def make_run(tmp_path):
    source = Path(__file__).parents[1] / 'wepp/interchange/test_project/output/loss_pw0.txt'
    output = tmp_path/'wepp/output'
    output.mkdir(parents=True)
    shutil.copy2(source, output/'loss_pw0.txt')
    (tmp_path/'READONLY').write_text('keep me')
    (tmp_path/'watershed.nodb').write_text(json.dumps({'_subs_summary':{str(i*10+1):{'wepp_id':i} for i in [1,2,3]}}))
    geometry=tmp_path/'dem/topaz/SUBCATCHMENTS.WGS.JSON'
    geometry.parent.mkdir(parents=True)
    geometry.write_text(json.dumps({'type':'FeatureCollection','features':[{'properties':{'TopazID':i*10+1},'geometry':{'type':'Polygon','coordinates':[]}} for i in [1,2,3]]}))
    return tmp_path


def test_preparation_preserves_sources_and_reuses_then_rolls_back(tmp_path):
    root=make_run(tmp_path)
    original=digest(root/'wepp/output/loss_pw0.txt')
    result=prepare(root)
    assert result['status']=='complete'
    assert result['validation']['rows']==3
    assert prepare(root)==result
    assert digest(root/'wepp/output/loss_pw0.txt')==original
    assert (root/'READONLY').read_text()=='keep me'
    assert (root/'_query_engine/catalog.json').exists()
    rollback(root)
    assert not (root/'wepp/output/interchange').exists()
    assert (root/'combined-viewer-preparation/manifest.json').exists()
    assert (root/'READONLY').read_text()=='keep me'


def test_preparation_refuses_unknown_outputs_and_symlink_escape(tmp_path):
    root=make_run(tmp_path/'run')
    output=root/'wepp/output/interchange';output.mkdir()
    with pytest.raises(FileExistsError):prepare(root)
    output.rmdir()
    outside=tmp_path/'outside';outside.mkdir()
    output.symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):prepare(root)
    assert not list(outside.iterdir())


def test_failure_is_visible_and_rollback_wont_delete_changed_output(tmp_path):
    root=make_run(tmp_path)
    prepare(root)
    target=root/'wepp/output/interchange/loss_pw0.hill.parquet'
    target.write_bytes(b'external modification')
    with pytest.raises(ValueError):rollback(root)
    assert target.read_bytes()==b'external modification'
    assert (root/'_query_engine/catalog.json').exists()


def test_missing_source_preserves_readonly_and_no_partial_success(tmp_path):
    root=make_run(tmp_path)
    (root/'wepp/output/loss_pw0.txt').write_text('invalid source')
    with pytest.raises((RuntimeError,ValueError)):prepare(root)
    state=json.loads((root/'combined-viewer-preparation/manifest.json').read_text())
    assert state['status']=='failed'
    assert state['error']
    assert (root/'combined-viewer-preparation/staging/loss_pw0.txt').exists()
    assert (root/'READONLY').read_text()=='keep me'
    with pytest.raises(RuntimeError):prepare(root)


@pytest.mark.parametrize('after_publish', [False, True])
def test_interrupted_atomic_publication_is_recoverable(tmp_path, monkeypatch, after_publish):
    import wepppy.weppcloud.combined_viewer_preparation as preparation
    root = make_run(tmp_path)
    original_link = preparation.os.link

    def interrupted_link(source, target):
        if after_publish:
            original_link(source, target)
        raise OSError('injected publication interruption')

    monkeypatch.setattr(preparation.os, 'link', interrupted_link)
    with pytest.raises(OSError, match='injected'):
        prepare(root)
    rollback(root)
    assert not (root / 'wepp/output/interchange').exists()
    assert (root / 'READONLY').read_text() == 'keep me'


def test_rollback_rejects_manifest_source_deletion(tmp_path):
    root = make_run(tmp_path)
    prepare(root)
    manifest_path = root / 'combined-viewer-preparation/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['outputs']['READONLY'] = digest(root / 'READONLY')
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='unowned'):
        rollback(root)
    assert (root / 'READONLY').read_text() == 'keep me'
    assert (root / '_query_engine/catalog.json').exists()
