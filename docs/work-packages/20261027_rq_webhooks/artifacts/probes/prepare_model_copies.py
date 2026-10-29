"""Use canonical fork path rebasing to prepare disposable model fixtures."""
from pathlib import Path
import shutil
from wepppy.rq.project_rq_fork import _rebase_fork_nodb_text
from wepppy.query_engine.catalog_refresh import invalidate_catalog_incarnation
from wepppy.nodb.mods.rap import RAP_TS

source = Path('/fixtures/source')
for name in ('ready-baseline', 'ready-healthy', 'ready-failing'):
    destination = Path('/acceptance/runs') / name
    shutil.copytree(source, destination, symlinks=False)
    for path in destination.rglob('*.nodb'):
        path.write_text(_rebase_fork_nodb_text(path.read_text(),
            source_wd='/wc1/runs/rq/rq212-20261027-upgraded', destination_wd=str(destination),
            source_runid='rq212-20261027-upgraded', destination_runid='profile;;tmp;;' + name))
    invalidate_catalog_incarnation(destination)
    rap = RAP_TS.getInstance(str(destination))
    assert rap.data is not None, 'Canonical copy must hydrate retained RAP input'
print('Three path-rebased model copies passed RAP input hydration.')
