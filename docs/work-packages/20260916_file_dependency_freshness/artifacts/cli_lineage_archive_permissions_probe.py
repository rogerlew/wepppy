"""Actual archive/restore confidentiality for new retained CLI snapshots."""
import json
import stat

import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from tests.nodb.test_cli_parquet_lineage import test_cleanup_skeleton_archive_restore_keep_history
from wepppy.nodb.core import Climate

pytestmark = pytest.mark.integration


def test_characterize_restored_snapshot_modes(owner_project):
    root, _ = owner_project
    owner = Climate.getInstance(str(root))
    source = root / 'climate' / owner.cli_fn
    source.chmod(0o600)
    assert owner._export_cli_parquet() is not None
    attempts = list(root.glob('climate_artifacts/cli_parquet/attempts/*'))
    selected = max(attempts, key=lambda path: path.stat().st_mtime_ns)
    snapshot = selected / 'source.cli'
    before = {'directory': oct(stat.S_IMODE(selected.stat().st_mode)),
              'snapshot': oct(stat.S_IMODE(snapshot.stat().st_mode)),
              'source': oct(stat.S_IMODE(source.stat().st_mode))}
    # The existing actual workflow covers cleanup, skeletonization, ArchiveRuntime,
    # ZIP members and restore_archive_rq; it checks all retained bytes too.
    test_cleanup_skeleton_archive_restore_keep_history(owner_project)
    after = {'directory': oct(stat.S_IMODE(selected.stat().st_mode)),
             'snapshot': oct(stat.S_IMODE(snapshot.stat().st_mode))}
    print('ARCHIVE_SNAPSHOT_ACCESS ' + json.dumps({'before': before, 'after': after}))
    assert before['directory'] == '0o700' and before['source'] == '0o600'
    assert after['directory'] == '0o755' and after['snapshot'] == '0o644'
