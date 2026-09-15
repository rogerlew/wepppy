"""Project-authoritative M3 source binding and cheap freshness inventory."""
from pathlib import Path

from . import rainfall_io as io
from .soil_inputs import META, dependency_state, prepared_sources, _json_snapshot
from .soil_snapshot import source_state, verify_snapshot

__all__ = ['inventory', 'verify_soil', 'activate_sources']


def inventory(wd):
    root = Path(wd).absolute()
    prepared = prepared_sources(root)
    paths = [root/META, root/'soils/ssurgo.tif',root/'soils/ssurgo.tif.msk',
             root/'soils/ssurgo.tif.meta',root/'soils/ssurgo_tabular_cache.sqlite',
             root/'soils/ssurgo_tabular_cache.sqlite.meta.md',*map(Path,prepared['files'])]
    if prepared['fallback'] is not None:
        paths.append(Path(str(root/prepared['fallback']['path'])+'.msk'))
    state = dependency_state(paths)
    cache = root/'soils/ssurgo_tabular_cache.sqlite'
    companions = source_state(cache) if state[str(cache)] is not None else None
    return {'dependencies':state,'cache_state':companions,'prepared_sha256':prepared['files']}


def verify_soil(wd, predictor, output):
    """Re-read logical core outside the acceptance lock, preserving diagnostics."""
    from .source_preparation import _inside
    root = Path(wd).absolute()
    predictor,output = _inside(root,predictor),_inside(root,output)
    manifest,_ = _json_snapshot(predictor/'soil/manifest.json')
    for path in manifest['dependency_state']:
        _inside(root,path)
    if manifest['source_state'] is not None:
        verify_snapshot(Path(wd)/'soils/ssurgo_tabular_cache.sqlite',manifest,output)
    if dependency_state(manifest['dependency_state']) != manifest['dependency_state']:
        io.fail('source_changed','Soil sources changed before result acceptance')


def activate_sources(wd, receipt_path, *, expected_sha256):
    """Bind a prepared receipt to Ron/Watershed, then use file-only promotion."""
    from .production import sources, mutable, WorkflowError
    from .source_preparation import prepare_local_sources, promote_local_sources, _inside
    from wepppy.nodb.core import Ron
    def authority():
        eligible,readonly,checks,paths,snapshot = sources(wd,rainfall=False)
        ron = Ron.getInstance(str(wd))
        if not eligible or readonly or not checks['watershed'] or ron.cellsize != 10 or ron.dem_db != 'ned13/2022':
            raise WorkflowError('superseded','Source activation requires the current eligible 10 m basin.',409)
        return paths,snapshot
    receipt_path = _inside(Path(wd).absolute(),receipt_path)
    paths,snapshot = authority()
    receipt,digest = _json_snapshot(receipt_path)
    if digest != expected_sha256:
        io.fail('source_changed','Source receipt changed before authoritative binding')
    for key in ('dem','mask'):
        path = str(paths[key].absolute())
        if path not in receipt['sources_sha256'] or io.digest(path,512*1024*1024) != receipt['sources_sha256'][path]:
            io.fail('source_changed','Receipt does not bind the authoritative basin inputs')
    derived = prepare_local_sources(wd,paths['dem'],paths['mask'])
    current,_ = _json_snapshot(derived)
    if any(receipt[key] != current[key] for key in ('grid','mukeys','cache_identity')):
        io.fail('source_changed','Receipt grid/keys differ from the authoritative basin')
    def verify():
        if authority()[1] != snapshot:
            io.fail('source_changed','Project authority changed before source activation')
    return promote_local_sources(mutable(wd),receipt_path,expected_sha256=expected_sha256,
                                 verify_project=verify)
