"""Compose actual M3 terrain and prepared soil/SBS on common spatial support."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

from . import rainfall_io as io
from .analysis_support import write_valid_mask
from .integration import _record, _support
from .m1_inputs import align_sbs, companions, prepare, read_raster
from .m3_terrain import build_terrain
from .soil_inputs import _copy, prepare_soil, dependency_state
from .soil_snapshot import source_state

__all__ = ['M3Inputs', 'build_m3_predictors']


@dataclass(frozen=True)
class M3Inputs:
    wd: Path
    dem: Path
    pointer: Path
    mask: Path
    outlet: Path
    sbs: Path
    expected_sha256: dict
    wbt_sha256: str
    source_kind: str
    sbs_alignment: str = 'exact'


def _outlet(outlet, grid, total):
    io._validate_grid_outlet(dict(grid=grid,outlet=outlet,area_km2=total*grid['transform'][0]**2/1e6),total)
    crs = outlet.get('crs')
    if crs is not None:
        if not isinstance(crs,dict) or not isinstance(crs.get('properties'),dict):
            io.fail('invalid_input', 'Malformed outlet CRS')
        try:
            supplied_crs = rasterio.crs.CRS.from_user_input(crs['properties'].get('name'))
        except (rasterio.errors.CRSError, TypeError, ValueError) as exc:
            raise io.RainfallError('invalid_input', 'Malformed outlet CRS') from exc
        if supplied_crs != rasterio.crs.CRS.from_user_input(grid['crs']):
            io.fail('invalid_input', 'Outlet CRS differs from terrain')
    feature = outlet['features'][0] if outlet['type'] == 'FeatureCollection' else outlet
    geometry = feature.get('geometry') if feature.get('type') == 'Feature' else feature
    x,y = geometry['coordinates']
    row,col = rasterio.transform.rowcol(rasterio.Affine(*grid['transform']),x,y)
    properties = feature.get('properties') or {}
    if not isinstance(properties,dict):
        io.fail('invalid_input', 'Malformed outlet properties')
    for key, expected in (('row',row),('column',col)):
        if key in properties and properties[key] != expected:
            io.fail('invalid_input', 'Outlet coordinates and recorded cell disagree')
    return [int(row),int(col)]


def build_m3_predictors(inputs, output_dir, *, wbt_executable):
    if inputs.source_kind not in ('real','synthetic','mixed') or inputs.sbs_alignment not in ('exact','nearest'):
        io.fail('invalid_input', 'Explicit M3 source kind and SBS alignment required')
    root, output = Path(inputs.wd).absolute(), Path(output_dir).absolute()
    if not output.is_relative_to(root) or '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):
        io.fail('invalid_input', 'M3 output must remain in this project')
    binary = Path(wbt_executable).absolute()
    expected = dict(inputs.expected_sha256, **{str(binary):inputs.wbt_sha256})
    consumed, companion_sets = {}, {}
    for value in (inputs.dem,inputs.pointer,inputs.mask,inputs.outlet,inputs.sbs):
        path = Path(value).absolute()
        if not path.is_relative_to(root):
            io.fail('invalid_input', 'M3 sources must remain in this project')
        paths = [path]
        if path.suffix.lower() in ('.tif','.tiff'):
            companion_sets[path] = companions(path)
            paths.extend(companion_sets[path])
        for p in paths:
            io.pinned(p,expected,consumed,512*1024*1024)
    _, _, grid = read_raster(inputs.dem,target_grid=True)
    mask,mask_valid,mask_grid = read_raster(inputs.mask,target_grid=True)
    domain = mask_valid & (mask > 0)
    if mask_grid != grid or not domain.any():
        io.fail('invalid_input', 'M3 watershed and DEM grids differ or watershed is empty')
    sbs,sbs_valid,sbs_grid = read_raster(inputs.sbs,categorical=True)
    if not np.isin(sbs[sbs_valid],[0,1,2,3]).all():
        io.fail('invalid_input', 'M3 SBS requires normalized classes 0 through 3')
    if sbs_grid != grid:
        if inputs.sbs_alignment != 'nearest':
            io.fail('invalid_input', 'M3 SBS alignment requires explicit nearest sampling')
        sbs,sbs_valid = align_sbs(sbs,sbs_valid,sbs_grid,grid)
    outlet = io.read_json(inputs.outlet)
    rowcol = _outlet(outlet,grid,int(domain.sum()))
    output.mkdir()
    io.write_json(output/'incomplete.json',{'status':'incomplete'})
    prepared = output/'prepared'; prepared.mkdir()
    prepare(prepared/'sbs.tif',sbs,sbs_valid,grid)
    prepare(prepared/'domain.tif',domain,np.ones(domain.shape,dtype=bool),grid)
    terrain = build_terrain(inputs.dem,inputs.pointer,inputs.mask,rowcol,output/'terrain',
                            binary=binary,expected_sha256=expected)
    wbt = output/'wbt'; wbt.mkdir()
    for name in ('relief.tif','area.tif','coverage.tif','summary.json'):
        _copy(output/'terrain/wbt'/name,wbt/name,terrain['artifacts_sha256']['wbt/'+name],
              io.MAX_TEXT if name.endswith('.json') else io.MAX_PREDICTOR_BYTES)
    soil = prepare_soil(root,output/'soil',grid,domain)
    thickness,thickness_valid,soil_grid = read_raster(output/'soil/thickness_cm.tif',continuous_missing=True)
    source,source_valid,source_grid = read_raster(output/'soil/source.tif',categorical=True)
    if soil_grid != grid or source_grid != grid or not np.array_equal(source_valid,domain):
        io.fail('invalid_input', 'Prepared soil grid/domain mismatch')
    common = domain & sbs_valid & thickness_valid & np.isin(source,[1,2])
    coverage = write_valid_mask(output/'valid_mask.tif',grid,domain,common)
    coverage.update(primary_valid_cells=int(np.count_nonzero(common & (source == 1))),
                    fallback_valid_cells=int(np.count_nonzero(common & (source == 2))))
    support = _support(common,domain)
    reason = None if common.any() else 'zero_valid_support'
    terrain_valid = terrain['summary']['terrain_valid']
    t = _record(terrain['T'],'dimensionless',terrain['summary']['reason'],
                _support(domain if terrain_valid else np.zeros(domain.shape,dtype=bool),domain),
                wbt_summary=terrain['summary'])
    f = _record(float(np.count_nonzero(common & (sbs >= 2)))/int(common.sum()) if common.any() else None,
                'fraction',reason,support)
    s = _record(float(np.mean(thickness[common],dtype=np.float64))/254 if common.any() else None,
                'thickness_cm_div_254',reason,support)
    points = {'T':t,'F':f,'S':s}
    available = sum(p['value'] is not None for p in points.values())
    area = int(domain.sum())*grid['transform'][0]**2/1e6
    consumed.update(terrain['sources_sha256'])
    consumed.update(soil['sources_sha256'])
    io.recheck(consumed,limits={p:512*1024*1024 for p in consumed})
    if any(companions(path) != names for path,names in companion_sets.items()):
        io.fail('source_changed', 'M3 source companions changed')
    if dependency_state(soil['dependency_state']) != soil['dependency_state']:
        io.fail('source_changed', 'M3 soil dependencies changed')
    if soil['source_state'] is not None and source_state(root/'soils/ssurgo_tabular_cache.sqlite') != soil['source_state']:
        io.fail('source_changed', 'M3 soil cache changed')
    inventory = ('valid_mask.tif','wbt/relief.tif','wbt/area.tif','wbt/coverage.tif','wbt/summary.json',
                 'soil/thickness_cm.tif','soil/source.tif','soil/manifest.json',
                 'terrain/manifest.json','terrain/wbt/watershed.tif','prepared/sbs.tif','prepared/domain.tif')
    manifest = dict(schema_version=2,model='M3',support_policy='common_valid_v1',soil_policy='recorded_depth_v1',
        status='complete',availability='complete' if available == 3 else 'partial' if available else 'unavailable',
        source_kind=inputs.source_kind,readiness={'wepp_soils':'not_checked_local','upstream_freshness':'not_checked_local'},
        grid=grid,outlet=outlet,area_km2=area,warnings=[] if .2 <= area <= 8 else ['area_outside_study_range'],
        predictors=points,coverage=coverage,sources_sha256=consumed,tool=terrain['tool'],
        prepared_sha256={'terrain/manifest.json':io.digest(output/'terrain/manifest.json'),
                         'soil/manifest.json':io.digest(output/'soil/manifest.json')},
        artifacts_sha256={name:io.digest(output/name,io.MAX_TEXT if name.endswith('.json') else io.MAX_PREDICTOR_BYTES) for name in inventory})
    io.validate_predictors(manifest)
    io.write_json(output/'manifest.json',manifest)
    (output/'incomplete.json').unlink()
    return manifest
