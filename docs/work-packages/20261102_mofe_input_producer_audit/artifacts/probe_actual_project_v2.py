"""Fork one actual project through the owned fork helper, then inspect copied inputs."""
from pathlib import Path
import hashlib
import json
import os

from wepppy.rq.project_rq_fork import prepare_fork_run
from wepppy.io_wait import wait_for_paths
from wepppy.nodb.core import Ron, Landuse, Soils, Wepp, Watershed
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.wepp.management import read_management
from wepppy.wepp.management.pmetpara import pmetpara_prep
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope

SOURCE = Path('/wc1/runs/aw/awake-versatility')
DEST = Path('/wc1/runs/mi/mipa-awake-20261102')
EVIDENCE = Path('/workdir/wepppy/docs/work-packages/20261102_mofe_input_producer_audit/artifacts')


def manifest(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*')) if path.is_file() and not path.is_symlink()}


def main():
    if DEST.exists():
        raise FileExistsError(DEST)
    DEST.parent.mkdir(mode=0o700, exist_ok=True)
    before = manifest(SOURCE)
    status = []
    prepare_fork_run('awake-versatility', 'mipa-awake-20261102', undisturbify=False,
                     skip_wepp_runs_output=True, skip_omni_scenarios_contrasts=True,
                     status_channel='local-mipa', publish_status=lambda channel, message: status.append(message),
                     get_wd=lambda runid: str(SOURCE), get_primary_wd=lambda runid: str(DEST),
                     wait_for_paths=wait_for_paths, ron_cls=Ron, disturbed_cls=Disturbed,
                     landuse_cls=Landuse, soils_cls=Soils, initialize_ttl=None)
    result = {'source': str(SOURCE), 'clone': str(DEST), 'source_manifest': before,
              'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
              'fork_status': status, 'scope': 'Copied actual project producer readback, no native execution'}
    (EVIDENCE / 'actual_project_fork_v2.json').write_text(json.dumps(result, indent=2)+'\n')
    assert manifest(SOURCE) == before, 'Source changed during fork'
    print(json.dumps({'source': str(SOURCE), 'clone': str(DEST), 'source_unchanged': True}))


if __name__ == '__main__':
    main()
