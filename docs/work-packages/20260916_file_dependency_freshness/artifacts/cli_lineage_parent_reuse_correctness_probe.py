"""Independent boundary probes for one-call CLI parent descriptor reuse."""
import errno
import os

import pandas as pd
import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from wepppy.climates import cli_parquet
from wepppy.nodb.mods.postfire_debris_flow import production, rainfall_io

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('content', [False, True])
def test_parent_replacement_after_final_leaf_signature_is_rejected(owner_project, monkeypatch, content):
    root, _ = owner_project
    parent = root / 'climate'
    replacement = root / 'replacement-climate'
    replacement.mkdir()
    for item in parent.iterdir():
        if item.is_file():
            os.link(item, replacement / item.name)
    real_read = cli_parquet._read_proof
    real_signature = production.signature
    armed = False

    def read_proof(stream, limit):
        nonlocal armed
        result = real_read(stream, limit)
        armed = True
        return result

    def signature(wd, path, **kwargs):
        nonlocal armed
        result = real_signature(wd, path, **kwargs)
        if armed and path.suffix == '.cli':
            armed = False
            parent.rename(root / 'former-climate')
            replacement.rename(parent)
        return result

    monkeypatch.setattr(cli_parquet, '_read_proof', read_proof)
    monkeypatch.setattr(production, 'signature', signature)
    with pytest.raises(production.WorkflowError) as raised:
        production.sources(root, content=content)
    assert raised.value.code == 'changed_source'


@pytest.mark.parametrize('prehashed', [False, True])
def test_different_source_parent_keeps_real_lineage_compatibility(tmp_path, prehashed):
    source = tmp_path / 'selected/source.cli'
    source.parent.mkdir()
    source.write_bytes(b'independent preserved source bytes\n')
    output = tmp_path / 'climate/wepp_cli.parquet'
    output.parent.mkdir()
    # Exercise the actual atomic lineage producer. Scientific parsing is outside
    # this path-authority probe; its rows are an explicit one-row fixture.
    with cli_parquet._CliParquetAttempt(tmp_path, source, output, 'climate') as attempt:
        attempt.publish(pd.DataFrame({'prcp': [4.0]}), lambda: source)
    files = {'active_cli': source, 'cli': output}
    records = {key: production.signature(tmp_path, path) for key, path in files.items()}
    hashes = {'active_cli': production.cached_digest(source, local=True)} if prehashed else {}
    assert production._cli_lineage_current(tmp_path, files, records, hashes)


def test_parent_descriptor_closes_when_caller_returns_early(tmp_path):
    retained = []

    def early_return():
        with rainfall_io._local_parent(tmp_path) as descriptor:
            retained.append(descriptor)
            return False

    assert early_return() is False
    with pytest.raises(OSError) as raised:
        os.fstat(retained[0])
    assert raised.value.errno == errno.EBADF
