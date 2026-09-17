"""Characterize portable producer identity through a supported run-root alias."""
import json
from pathlib import Path

import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from wepppy.climates.cli_parquet import _read_proof
from wepppy.nodb.core import Climate
from wepppy.nodb.mods.postfire_debris_flow import production
from wepppy.wepp.interchange._utils import _ensure_cli_parquet

pytestmark = pytest.mark.integration


def test_characterize_root_alias_source_identity(owner_project):
    root, _ = owner_project
    owner = Climate.getInstance(str(root))
    assert production.sources(root)[2]['climate']
    alias = root.parent / (root.name + '-alias')
    alias.symlink_to(root, target_is_directory=True)
    try:
        output = root / 'climate/wepp_cli.parquet'
        output.unlink()
        selected = _ensure_cli_parquet(alias / 'climate', cli_file_hint=owner.cli_fn)
        assert selected is not None
        with output.open('rb') as stream:
            proof = _read_proof(stream, 1024 * 1024)[0]
        ready = production.sources(root)[2]['climate']
        print('ROOT_ALIAS ' + json.dumps({'proof_source': proof['source'],
              'proof_resolved_source': proof['resolved_source'], 'canonical_ready': ready,
              'expected_source': 'climate/' + owner.cli_fn}))
        assert proof['source'] != 'climate/' + owner.cli_fn
        assert not ready
    finally:
        alias.unlink()
