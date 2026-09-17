"""Canonical archive/restore mode characterization on disposable failed work."""
import json
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace
import zipfile

import pytest

from wepppy.nodb.mods.geneva.collaborators._cache_freshness import _Attempt
from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.project_config_update import project_config_lifecycle_guard
from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def test_failed_attempt_permissions_survive_canonical_archive_restore(tmp_path):
    run = tmp_path / 'disposable-run'
    run.mkdir(mode=0o755)
    geneva = SimpleNamespace(wd=str(run), artifact_io=GenevaArtifactIO())
    with pytest.raises(RuntimeError, match='retained failure'):
        with _Attempt(geneva, 'hru_map_features.wgs.geojson', 'hru_geometry') as attempt:
            payload = attempt.candidate('candidate.geojson')
            payload.write_text('retained partial project output')
            raise RuntimeError('retained failure')
    ordinary = run / 'ordinary'
    ordinary.mkdir(mode=0o750)
    (ordinary / 'private.txt').write_text('private file mode control')
    (ordinary / 'private.txt').chmod(0o600)
    paths = [attempt.root.parent, attempt.root, payload, attempt.root / 'status.json',
             ordinary, ordinary / 'private.txt']
    before = {str(path.relative_to(run)): mode(path) for path in paths}
    contents = {str(path.relative_to(run)): path.read_bytes() for path in paths if path.is_file()}
    runtime = ArchiveRuntime(
        get_current_job=lambda: SimpleNamespace(id='disposable-permission-probe'),
        get_wd=lambda runid: str(run), get_prep_from_runid=lambda runid: None,
        lock_statuses=lambda runid: {}, clear_nodb_file_cache=lambda runid: [],
        publish_status=lambda channel, message: None, disk_usage=shutil.disk_usage,
        zip_file_cls=zipfile.ZipFile, project_config_lifecycle_guard=project_config_lifecycle_guard,
        project_config_authority_wd=lambda runid: str(run))
    archive_rq('disposable-permission-probe', 'permission characterization', runtime=runtime)
    archive = next((run / 'archives').glob('*.zip'))
    with zipfile.ZipFile(archive) as zf:
        members = {item.filename: {'directory': item.is_dir(),
                                  'mode': stat.S_IMODE(item.external_attr >> 16),
                                  'create_system': item.create_system} for item in zf.infolist()}
        assert all(zf.read(name) == value for name, value in contents.items())
    restore_archive_rq('disposable-permission-probe', archive.name, runtime=runtime)
    after = {str(path.relative_to(run)): mode(path) for path in paths}
    result = {'uid': os.geteuid(), 'gid': os.getegid(), 'before': before, 'after': after,
              'archive_mode': mode(archive), 'zip_members': members,
              'all_bytes_preserved': all((run / name).read_bytes() == value for name, value in contents.items()),
              'scope': 'actual producer attempt and canonical archive/restore; job/Redis transport supplied by ArchiveRuntime'}
    Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    assert result['all_bytes_preserved']
    assert after == before
