"""Containment and dependency-parity gates for the fixed source image recipe."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
spec = importlib.util.spec_from_file_location('source_overlay', Path(__file__).resolve().parents[2] / 'scripts/build_source_overlay.py')
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)
BASE = 'sha256:' + 'a' * 64


@pytest.fixture
def source(tmp_path):
    files = {}
    for name in overlay.APP_FILES:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'answer = 42\n')
        files[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return tmp_path, {'version': 1, 'base_image_id': BASE, 'files': files}


def test_exact_sources_and_no_additional_payload(source):
    root, manifest = source
    assert set(overlay.read_sources(root, manifest)) == overlay.APP_FILES
    manifest['files']['../escape'] = 'a' * 64
    with pytest.raises(ValueError, match='exactly'):
        overlay.read_sources(root, manifest)


def test_changed_source_and_symlink_rejected(source):
    root, manifest = source
    p = root / 'tools/query_catalog_pilot.py'
    p.write_text('changed')
    with pytest.raises(ValueError, match='content changed'):
        overlay.read_sources(root, manifest)
    p.unlink()
    p.symlink_to(root / 'wepppy/rq/query_catalog_rq.py')
    with pytest.raises(ValueError, match='symlink'):
        overlay.read_sources(root, manifest)


@pytest.mark.parametrize('drift', ['none', 'native', 'distributions', 'config', 'source', 'container', 'tag'])
def test_build_checks_parity_before_service_tag_promotion(source, monkeypatch, drift):
    root, manifest = source
    config = {'User': '1000:1000', 'Env': ['A=B'], 'Entrypoint': ['worker'], 'Cmd': ['batch']}
    candidate_config = copy.deepcopy(config)
    if drift == 'config':
        candidate_config['User'] = '0'
    before = {'distributions': 'packages', 'distribution_count': 307, 'native': {'scanner': 'same'}, 'sources': {}, 'source_metadata': {name: [0o664, 1002, 130] for name in overlay.APP_FILES}}
    after = copy.deepcopy(before)
    after['sources'] = dict(manifest['files'])
    if drift in {'native', 'distributions'}:
        after[drift] = 'changed'
    if drift == 'source':
        after['sources'] = {}
    calls = []
    def docker(*args):
        calls.append(args)
        if args[:2] == ('image', 'inspect'):
            candidate = args[2].startswith('wepppy-source-candidate:')
            identity = 'sha256:' + 'b' * 64 if candidate else BASE
            if drift == 'tag' and args[2] == 'wepppy:test':
                identity = 'wrong'
            return json.dumps([{'Id': identity, 'Config': candidate_config if candidate else config}])
        if args[0] == 'inspect':
            return json.dumps([{'Image': 'wrong' if drift == 'container' else BASE, 'State': {'Running': True}}])
        if args[0] == 'build':
            recipe = (Path(args[-1]) / 'Dockerfile').read_text()
            assert '--network=none' in args
            assert 'USER 0\n' in recipe and recipe.endswith('USER 1000:1000\n')
            assert 'pip ' not in recipe
        return ''
    monkeypatch.setattr(overlay, 'docker', docker)
    monkeypatch.setattr(overlay, 'fingerprint', lambda ref: before if ref == BASE else after)
    if drift == 'none':
        result = overlay.build_overlay(root, manifest, 'wepppy:test', 'batch-container')
        assert result['base_image_id'] == BASE
    else:
        with pytest.raises(ValueError):
            overlay.build_overlay(root, manifest, 'wepppy:test', 'batch-container')
    assert not any(c[:2] == ('image', 'tag') and c[-1] == 'wepppy:test' for c in calls)
