"""Real source replacement, model identity and historical-read boundaries."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from wepppy.nodb.mods.ash_transport import water_provenance as provenance

pytestmark = pytest.mark.unit


def inputs(tmp_path):
    source=tmp_path/'wepp/output/interchange';source.mkdir(parents=True)
    for name in ('H.wat.parquet','H.pass.parquet','totalwatsed3.parquet'):
        (source/name).write_bytes(name.encode())
    model=tmp_path/'ash/H1_ash.parquet';model.parent.mkdir();model.write_bytes(b'model')
    provenance.write_model_proof(model,{'algorithm':provenance.ALGORITHM,
        'wat_sha256':provenance.fingerprint(source/'H.wat.parquet')})
    return source,model,[('ash/H1_ash.parquet',101,1.,2)],{'manifest': [['ash/H1_ash.parquet',101,1.,2]], 'ash_wepp_ids': [1]}


def test_old_model_cannot_be_blessed_by_new_post(tmp_path):
    source,model,manifest,mapping=inputs(tmp_path)
    proof=provenance.post_inputs(tmp_path,manifest,mapping)
    (tmp_path/'ash/post').mkdir()
    (tmp_path/'ash/post/watershed_daily.parquet').write_bytes(b'post')
    provenance.publish_post_proof(tmp_path,proof)
    assert provenance.historical_warning(tmp_path,mapping) is None
    (source/'H.wat.parquet').write_bytes(b'new WAT generation')
    with pytest.raises(ValueError,match='regenerate'):
        provenance.post_inputs(tmp_path,manifest,mapping)
    assert provenance.historical_warning(tmp_path,mapping)
    assert model.read_bytes()==b'model'


def test_modified_model_and_mapping_are_not_current(tmp_path):
    _,model,manifest,mapping=inputs(tmp_path)
    proof=provenance.post_inputs(tmp_path,manifest,mapping)
    (tmp_path/'ash/post').mkdir();(tmp_path/'ash/post/watershed_daily.parquet').write_bytes(b'post')
    provenance.publish_post_proof(tmp_path,proof)
    assert provenance.historical_warning(tmp_path,[[102,1.,2]])
    model.write_bytes(b'replaced model')
    with pytest.raises(ValueError,match='Stale'):
        provenance.post_inputs(tmp_path,manifest,mapping)
    assert provenance.historical_warning(tmp_path,mapping)


def test_missing_dependency_retains_historical_downloads(tmp_path):
    source,_,manifest,mapping=inputs(tmp_path)
    proof=provenance.post_inputs(tmp_path,manifest,mapping)
    (tmp_path/'ash/post').mkdir();output=tmp_path/'ash/post/watershed_daily.parquet';output.write_bytes(b'post')
    provenance.publish_post_proof(tmp_path,proof)
    (source/'H.pass.parquet').unlink()
    assert provenance.historical_warning(tmp_path,mapping)
    assert output.read_bytes()==b'post'
    with pytest.raises(FileNotFoundError):
        provenance.post_inputs(tmp_path,manifest,mapping)


def test_nan_runoff_is_rejected_before_model_transport():
    frame=pd.DataFrame({name:[1.] for name in ('P','RM','Q','Total-Soil Water','Snow-Water')})
    frame.Q=np.nan
    with pytest.raises(ValueError,match='finite daily'):
        provenance.model_input_proof(frame)


def test_pre_read_digest_cannot_be_rebased_by_metadata_preserving_rewrite(tmp_path, monkeypatch):
    source, model, manifest, mapping = inputs(tmp_path)
    source = source / 'H.wat.parquet'
    old_digest = provenance.fingerprint(source)
    signature = provenance._signature(source)
    frame = pd.DataFrame({name: [1.] for name in ('P','RM','Q','Total-Soil Water','Snow-Water')})
    frame.attrs.update(source_path=str(source), source_signature=signature,
                       water_aggregation=provenance.ALGORITHM, water_source_sha256=old_digest)
    cache = {}
    provenance.bind_model_source(frame, cache)
    provenance.bind_model_source(frame.copy(), cache)
    assert cache['digest'] == old_digest
    source.write_bytes(b'new generation')
    actual_signature = provenance._signature
    # Filesystems can retain the same timestamp tick. Even an indistinguishable
    # metadata signature must not attach a new digest to an older dataframe.
    monkeypatch.setattr(provenance, '_signature', lambda path: signature if path == source else actual_signature(path))
    proof = provenance.model_input_proof(frame)
    assert proof['wat_sha256'] == old_digest
    provenance.write_model_proof(model, proof)
    with pytest.raises(ValueError, match='regenerate'):
        provenance.post_inputs(tmp_path, manifest, mapping)


@pytest.mark.parametrize('payload', [[], None, {'algorithm': provenance.ALGORITHM, 'mapping': None, 'sources': []}])
def test_malformed_sidecar_is_historical(tmp_path, payload):
    post = tmp_path / 'ash/post'
    post.mkdir(parents=True)
    (post / 'watershed_daily.parquet').write_bytes(b'old')
    (post / provenance.POST_PROOF).write_text(json.dumps(payload))
    assert provenance.historical_warning(tmp_path)


def test_partial_proof_never_certifies_existing_outputs(tmp_path):
    _, _, manifest, mapping = inputs(tmp_path)
    proof = provenance.post_inputs(tmp_path, manifest, mapping)
    post = tmp_path/'ash/post'
    post.mkdir()
    (post/'watershed_daily.parquet').write_bytes(b'old')
    proof.update(models={}, outputs={})
    (post/provenance.POST_PROOF).write_text(json.dumps(proof))
    assert provenance.historical_warning(tmp_path, mapping)


def test_pickle_only_history_is_visibly_unverified(tmp_path):
    post = tmp_path/'ash/post'
    post.mkdir(parents=True)
    (post/'old.pkl').write_bytes(b'old')
    assert provenance.historical_warning(tmp_path)


def test_warning_property_initial_and_missing_archived_topology(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from wepppy.nodb.mods.ash_transport.ash import Ash, Watershed
    calls = []
    def absent(_):
        calls.append(True)
        def translate():
            raise RuntimeError('No sub_ids/chn_ids available for translator (no summaries or parquet files)')
        return SimpleNamespace(translator_factory=translate)
    monkeypatch.setattr(Watershed, 'getInstance', absent)
    instance = SimpleNamespace(wd=str(tmp_path), has_ash_results=False)
    assert Ash.water_accounting_warning.fget(instance) is None
    assert not calls
    post = tmp_path/'ash/post'
    post.mkdir(parents=True)
    (post/'historical.pkl').write_bytes(b'old')
    instance.has_ash_results = True
    assert Ash.water_accounting_warning.fget(instance)
    assert calls
