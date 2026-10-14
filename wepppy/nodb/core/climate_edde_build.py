"""Collect EDDE outside locks and publish one validated climate generation."""
from copy import deepcopy
from pathlib import Path
import shutil
import json
import sys
from tempfile import TemporaryDirectory, mkdtemp

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

from wepppy.climates.cligen import CligenStationsManager, ClimateFile
from wepppy.climates.edde.client import EddeClient, Point, locate, sha256, write_json, AvailabilityError, DataQualityError
from wepppy.climates.edde.cligen import build_climate, read_cli, _validate_cli
from wepppy.climates.prism._bulk_transport import now
from wepppy.nodb._derived_build import finalize, publish_files, file_signature
from wepppy.nodb.core.climate_observed_build import _require_climate_directory
from wepppy.nodb.core.climate_edde_inputs import validate_edde_selection
from wepppyo3.climate import cli_revision, rust_cli_p_scale, rust_cli_p_scale_monthlies

__all__ = ['run_edde_build']


def _inputs(climate):
    names = ('edde_projection', 'future_start_year', 'future_end_year', 'climatestation',
             'cligen_db', 'cligen_seed', 'climate_mode', 'climate_spatialmode', 'catalog_id',
             'locales', 'precip_scaling_mode', 'precip_scale_factor', 'precip_monthly_scale_factors',
             'precip_scale_factor_map', 'wmesque_version', 'wmesque_endpoint', 'cli_dir')
    result = deepcopy({name: getattr(climate, name) for name in names})
    watershed = climate.watershed_instance
    result['locations'] = {'ws': tuple(watershed.require_centroid())}
    if int(climate.climate_spatialmode) == 1:
        result['locations'].update({str(top): tuple(watershed.hillslope_centroid_lnglat(top))
                                   for top, _ in watershed.centroid_hillslope_iter()})
    result['map'] = deepcopy((climate.ron_instance.map.extent, climate.ron_instance.map.cellsize))
    station = CligenStationsManager(version=result['cligen_db']).get_station_fromid(result['climatestation'])
    if station is None:
        raise ValueError('Selected EDDE auxiliary station is unavailable')
    result['station_identity'] = file_signature(station.parpath)
    scale_map = result['precip_scale_factor_map']
    result['scale_map_identity'] = file_signature(scale_map) if int(climate.precip_scaling_mode) == 4 else None
    return result


def _normals(climate, stage, locations):
    from .climate_build_helpers import _retrieve_prism_revision_tiles
    paths = {name: stage / f'prism-{name}.tif' for name in ('ppt', 'tmin', 'tmax')}
    _retrieve_prism_revision_tiles(climate, climate.ron_instance.map,
                                  str(paths['ppt']), str(paths['tmin']), str(paths['tmax']))
    normals = {name: {} for name in locations}
    identities = {}
    acquisition = {}
    for variable, path in paths.items():
        identities[variable] = sha256(path)
        metadata = json.loads(Path(str(path) + '.meta').read_text())
        source = metadata.get('wmesque', {})
        if source.get('dataset', '').strip('/') != f'prism/{variable}':
            raise DataQualityError('PRISM source identity does not match the requested normal product')
        acquisition[variable] = metadata
        with rasterio.open(path) as src:
            if src.count != 12 or src.crs is None:
                raise DataQualityError('PRISM eligibility requires twelve georeferenced monthly bands')
            for name, (lng, lat) in locations.items():
                x, y = transform('EPSG:4326', src.crs, [lng], [lat])
                row, col = src.index(x[0], y[0])
                if not (0 <= row < src.height and 0 <= col < src.width):
                    raise DataQualityError(f'PRISM normals do not cover {name}')
                values = src.read(window=((row, row + 1), (col, col + 1)), masked=True)[:, 0, 0]
                if np.ma.getmaskarray(values).any() or not np.isfinite(values).all():
                    raise DataQualityError(f'PRISM normals are missing at {name}')
                normals[name][variable] = values.tolist()
    for name, values in normals.items():
        if (np.any(np.asarray(values['ppt']) < 0)
                or np.any(np.asarray(values['tmin']) > values['tmax'])):
            raise DataQualityError(f'Invalid PRISM normals at {name}')
    if np.any(np.asarray(normals['ws']['ppt']) <= 0):
        raise DataQualityError('Reference PRISM precipitation must be positive')
    # All points share the same acquired normal rasters; no mixing of periods/units.
    write_json(stage / 'prism-normals.json', {'locations': normals, 'sha256': identities,
               'source': 'wmesque prism 800m M4 normals', 'period': '1991-2020',
               'acquisition': acquisition, 'endpoint': climate.wmesque_endpoint,
               'version': climate.wmesque_version, 'units': {'ppt': 'mm/month', 'tmin': 'C', 'tmax': 'C'}})
    return normals


def _inventory(client, model, scenario, start, end, stage):
    selected = {}
    for year in range(start, end + 1):
        objects = client.inventory(model, scenario, year)
        planned = []
        for month in range(1, 13):
            for variable in ('prday', 'tsmax', 'tsmin'):
                found = [obj for obj in objects if obj['key'].split('/')[-1].startswith(variable + '.')
                         and f'.{year}-{month:02d}.raw.nc' in obj['key']]
                if len(found) != 1:
                    raise AvailabilityError(f'Expected one {variable} file for {model}/{scenario}/{year}-{month:02d}')
                planned.extend(found)
        if sum(obj['size'] for obj in planned) + 4_000_000 > client.max_download_bytes:
            raise AvailabilityError(f'EDDE {year} exceeds the yearly source budget')
        selected[year] = planned
        write_json(stage / 'source-inventory.json', selected)
    return sum(obj['size'] for objects in selected.values() for obj in objects)


def _retain_cache(cache, destination):
    destination.mkdir(exist_ok=True)
    for path in Path(cache).glob('*.json'):
        shutil.copy2(path, destination / path.name)


def _scale(stage, filenames, inputs):
    """Use existing native scaling and the established spatial skip semantics."""
    from .climate import ClimatePrecipScalingMode as Mode
    from wepppy.all_your_base.geo import RasterDatasetInterpolator
    mode = inputs['precip_scaling_mode']
    if mode == Mode.NoScaling:
        return filenames
    raster = RasterDatasetInterpolator(inputs['precip_scale_factor_map']) if mode == Mode.Spatial else None
    result = {}
    for point, filename in filenames.items():
        destination = 'scale_' + filename
        if mode == Mode.Monthlies:
            rust_cli_p_scale_monthlies(str(stage / filename), str(stage / destination), inputs['precip_monthly_scale_factors'])
        else:
            factor = raster.get_location_info(*inputs['locations'][point]) if raster else inputs['precip_scale_factor']
            if raster and (factor is None or not 0.1 < factor < 10.0):
                result[point] = filename
                continue
            rust_cli_p_scale(str(stage / filename), str(stage / destination), factor)
        result[point] = destination
    return result


def run_edde_build(climate, *, attrs=None):
    """Retain every attempt; only successful, current inputs publish derived state."""
    climate.set_attrs(attrs)
    inputs = _inputs(climate)
    model, scenario, start, end = validate_edde_selection(
        inputs['edde_projection'], inputs['future_start_year'], inputs['future_end_year'],
        locales=inputs['locales'], spatial_mode=inputs['climate_spatialmode'], scaling_mode=inputs['precip_scaling_mode'])
    _require_climate_directory(climate)
    directory = Path(inputs['cli_dir'])
    stage = Path(mkdtemp(prefix='edde-build-', dir=directory))
    status = {'kind': 'edde-v2', 'state': 'incomplete', 'started_utc': now(),
              'projection': inputs['edde_projection'], 'start_year': start, 'end_year': end,
              'requested_years': end - start + 1, 'yearly_source_budget_bytes': 4_000_000_000,
              'locations': inputs['locations'], 'station': inputs['climatestation'], 'seed': inputs['cligen_seed']}
    write_json(stage / 'build-status.json', status)
    complete = False
    try:
        points = [Point(name, *coordinates) for name, coordinates in inputs['locations'].items()]
        with TemporaryDirectory(prefix='edde-source-') as cache:
            client = EddeClient(cache)
            try:
                grid, grid_record = client.grid(model)
                cells = locate(grid, points)
                write_json(stage / 'eligibility.json', {'points': cells, 'grid': grid_record})
                status['planned_weather_bytes'] = _inventory(client, model, scenario, start, end, stage)
                write_json(stage / 'build-status.json', status)
            finally:
                _retain_cache(cache, stage / 'grid-source')
                client.session.close()
        normals = _normals(climate, stage, inputs['locations']) if int(inputs['climate_spatialmode']) == 1 else None
        frames, manifests = [], []
        for year in range(start, end + 1):
            status['collecting_year'] = year
            write_json(stage / 'build-status.json', status)
            with TemporaryDirectory(prefix='edde-source-') as cache:
                client = EddeClient(cache)
                try:
                    frame, manifest = client.query([points[0]], model, scenario, f'{year}-01-01', f'{year}-12-31', ['prday', 'tsmax', 'tsmin'])
                    write_json(stage / f'source-{year}.json', manifest)
                    if any(manifest['grid'][key] != grid_record[key] for key in ('source', 'sha256')):
                        raise DataQualityError('EDDE grid identity changed after project eligibility preflight')
                    if manifest['points'] != [cells[0]]:
                        raise DataQualityError('EDDE watershed cell changed after project eligibility preflight')
                    frame.to_csv(stage / f'source-{year}.csv', index=False)
                    write_json(stage / f'source-{year}.json', manifest)
                    frames.append(frame)
                    manifests.append(manifest)
                finally:
                    _retain_cache(cache, stage / f'source-{year}-attempts')
                    client.session.close()
        station = CligenStationsManager(version=inputs['cligen_db']).get_station_fromid(inputs['climatestation'])
        generated = stage / 'generated'
        replay = build_climate(pd.concat(frames, ignore_index=True), manifests, station, generated, seed=inputs['cligen_seed'])
        filenames = {'ws': 'wepp.cli'}
        if normals:
            ref = normals['ws']
            for point, target in normals.items():
                if point == 'ws':
                    continue
                filename = f'_{int(point)}.cli'
                cli_revision(str(generated / 'wepp.cli'), str(generated / filename),
                             ref['ppt'], ref['tmax'], ref['tmin'], target['ppt'], target['tmax'], target['tmin'])
                filenames[point] = filename
        filenames = _scale(generated, filenames, inputs)
        expected_dates = pd.date_range(f'{start}-01-01', f'{end}-12-31')
        for filename in filenames.values():
            frame = read_cli(generated / filename)
            _validate_cli(frame)
            if not frame.index.equals(expected_dates):
                raise DataQualityError('Final climate dates differ from the requested period')
        provenance = {'projection': inputs['edde_projection'], 'start_year': start, 'end_year': end,
                      'points': cells, 'station': replay['station'], 'seed': inputs['cligen_seed'],
                      'attempt': stage.name, 'generated_fields': replay['generated_fields'],
                      'scaling': {key: value for key, value in inputs.items() if key.startswith('precip_')},
                      'files': {name: sha256(generated / name) for name in filenames.values()}}
        write_json(generated / 'edde-provenance.json', provenance)
        monthlies = ClimateFile(str(generated / filenames['ws'])).calc_monthlies()
        with finalize(climate) as publications:
            if _inputs(climate) != inputs:
                status['state'] = 'superseded'
                raise RuntimeError('EDDE build superseded by changed climate inputs or watershed geometry')
            publication = Path(publications.enter_context(TemporaryDirectory(prefix='.climate-publish-', dir=directory)))
            for path in generated.iterdir():
                if path.is_file():
                    shutil.copy2(path, publication / path.name)
            obsolete = [p.name for p in directory.iterdir() if p.is_file() and not p.name.startswith('.')]
            publications.enter_context(publish_files(publication, directory, climate, remove=obsolete))
            climate.cli_fn = filenames['ws']
            climate.par_fn = station.par
            climate.sub_cli_fns = {key: value for key, value in filenames.items() if key != 'ws'} or None
            climate.sub_par_fns = {key: station.par for key in filenames if key != 'ws'} or None
            climate.monthlies = monthlies
            climate._input_years = end - start + 1
            climate._edde_provenance = provenance
            climate._observed_quality_guard_summary_warning = None
        complete = True
    finally:
        error = sys.exc_info()[1]
        if error is not None:
            status['error'] = {'type': type(error).__name__, 'message': str(error)}
        status.update(state='complete' if complete else ('superseded' if status['state'] == 'superseded' else 'failed'), finished_utc=now())
        try:
            write_json(stage / 'build-status.json', status)
        except OSError:
            climate.logger.exception('Unable to record EDDE attempt outcome: %s', stage)
