"""Inspect owned D8UpstreamRelief outputs for one authoritative basin/outlet."""
import math
from pathlib import Path

import numpy as np
import rasterio

from . import rainfall_io as io
from .integration import _run
from .m1_inputs import companions, prepare, read_raster

__all__ = ['build_terrain']


def build_terrain(dem, pointer, mask, outlet, output, *, binary, expected_sha256):
    """Build retained native products; no acquisition, controller or publication."""
    output, binary = Path(output).absolute(), Path(binary).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output, *output.parents)):
        io.fail('invalid_input', 'Unsafe terrain output path')
    files = [Path(p).absolute() for p in (dem, pointer, mask)]
    for p in tuple(files):
        files.extend(companions(p))
    consumed = {}
    for p in (*files, binary):
        io.pinned(p, expected_sha256, consumed, 512*1024*1024)
    elevation, elevation_valid, grid = read_raster(dem, target_grid=True)
    routing, routing_valid, routing_grid = read_raster(pointer, categorical=True, target_grid=True)
    basin, basin_valid, basin_grid = read_raster(mask, target_grid=True)
    if grid != routing_grid or grid != basin_grid or grid['transform'][0] != 10:
        io.fail('invalid_input', 'M3 requires aligned genuine 10 m terrain inputs')
    if not np.array_equal(elevation_valid, routing_valid):
        io.fail('invalid_input', 'Raw elevation and routing validity masks differ')
    domain = basin_valid & (basin > 0)
    if not domain.any() or np.any(domain & ~elevation_valid):
        io.fail('invalid_input', 'Watershed requires valid raw elevation and routing')
    if (not isinstance(outlet, (list, tuple)) or len(outlet) != 2
            or any(type(v) is not int for v in outlet)
            or not 0 <= outlet[0] < domain.shape[0] or not 0 <= outlet[1] < domain.shape[1]
            or not domain[tuple(outlet)]):
        io.fail('invalid_input', 'Outlet row/column must identify a watershed cell')
    output.mkdir()
    io.write_json(output/'incomplete.json', {'status': 'incomplete'})
    prepared = output/'prepared'; prepared.mkdir()
    destination = output/'wbt'; destination.mkdir()
    prepare(prepared/'dem.tif', elevation, elevation_valid, grid)
    prepare(prepared/'pointer.tif', routing, routing_valid, grid)
    _run([str(binary), '--version'], output, 'version')
    version = io.regular(output/'version.stdout.log', io.MAX_TEXT).read_text().strip()
    if not version:
        io.fail('invalid_tool_output', 'Missing native tool version')
    command = [str(binary), '-r=D8UpstreamRelief', f'--dem={prepared/"dem.tif"}',
               f'--d8_pntr={prepared/"pointer.tif"}', f'--output={destination/"relief.tif"}',
               f'--area={destination/"area.tif"}', f'--coverage={destination/"coverage.tif"}',
               '--elevation_units=m']
    _run(command, output, 'terrain')
    outputs = {}
    hashes = {}
    for name in ('relief', 'area', 'coverage'):
        path = destination/f'{name}.tif'
        io.regular(path, io.MAX_PREDICTOR_BYTES)
        values, valid, actual_grid = read_raster(path, categorical=name == 'coverage')
        with rasterio.open(path) as ds:
            expected_type = 'uint8' if name == 'coverage' else 'float64'
            if ds.dtypes != (expected_type,):
                io.fail('invalid_tool_output', 'Native terrain output has unexpected sample type')
        if actual_grid != grid or not np.array_equal(valid, elevation_valid):
            io.fail('invalid_tool_output', 'Native terrain output grid/support differs')
        if (name == 'coverage' and not np.isin(values[valid], [0, 1]).all()) or (name != 'coverage' and np.any(values[valid] < 0)):
            io.fail('invalid_tool_output', 'Invalid native terrain values')
        outputs[name] = values
        hashes[f'wbt/{name}.tif'] = io.digest(path, io.MAX_PREDICTOR_BYTES)
    cell = tuple(outlet)
    area, relief = float(outputs['area'][cell]), float(outputs['relief'][cell])
    cell_area = grid['transform'][0]**2
    upstream = area/cell_area
    if not math.isfinite(upstream) or upstream < 1 or upstream != int(upstream):
        io.fail('invalid_tool_output', 'Native area is not a positive whole cell count')
    reason = ('terrain_potentially_truncated' if outputs['coverage'][cell] else
              'watershed_area_mismatch' if int(upstream) != int(domain.sum()) else None)
    # Equal areas can still describe different basins. Use the owned routing
    # implementation to prove membership, independently of soil/SBS support.
    x, y = rasterio.Affine(*grid['transform'])*(outlet[1]+0.5, outlet[0]+0.5)
    pour_point = prepared/'outlet.geojson'
    io.write_json(pour_point, {'type':'FeatureCollection', 'features':[
        {'type':'Feature', 'properties':{}, 'geometry':{'type':'Point','coordinates':[x,y]}}],
        'crs':{'type':'name','properties':{'name':grid['crs']}}})
    routed_path = destination/'watershed.tif'
    _run([str(binary), '-r=Watershed', f'--d8_pntr={prepared/"pointer.tif"}',
          f'--pour_pts={pour_point}', f'--output={routed_path}'], output, 'watershed')
    routed, routed_valid, routed_grid = read_raster(routed_path, categorical=True)
    if routed_grid != grid:
        io.fail('invalid_tool_output', 'Routing-derived watershed grid differs')
    if reason is None and not np.array_equal(routed_valid & (routed > 0), domain):
        io.fail('invalid_input', 'Routing-derived watershed membership differs from authoritative mask')
    hashes['wbt/watershed.tif'] = io.digest(routed_path, io.MAX_PREDICTOR_BYTES)
    summary = dict(schema_version=1, status='complete', tool='D8UpstreamRelief',
                   tool_version=version, tool_sha256=consumed[str(binary)], grid=grid,
                   outlet=list(outlet), full_upstream_cells=int(upstream), area_m2=area,
                   relief_m=relief, terrain_valid=reason is None, reason=reason)
    io.recheck(consumed, limits={p:512*1024*1024 for p in consumed})
    for p in (dem, pointer, mask):
        if set(companions(p)) != {q for q in files if q == Path(str(Path(p).absolute())+'.msk')}:
            io.fail('source_changed', 'Terrain source companions changed')
    io.write_json(destination/'summary.json', summary)
    hashes['wbt/summary.json'] = io.digest(destination/'summary.json', io.MAX_TEXT)
    manifest = dict(schema_version=1, status='complete', summary=summary,
                    T=relief/math.sqrt(area) if reason is None else None,
                    sources_sha256=consumed, artifacts_sha256=hashes,
                    tool={'path':str(binary), 'sha256':consumed[str(binary)], 'version':version, 'command':command})
    io.write_json(output/'manifest.json', manifest)
    (output/'incomplete.json').unlink()
    return manifest
