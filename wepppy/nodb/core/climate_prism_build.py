"""Historic PRISM collection outside NoDb locks and bounded artifact publication."""
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory, mkdtemp

import pandas as pd

from wepppy.climates.cligen import Cligen, CligenStationsManager, ClimateFile
from wepppy.climates.gridmet.admission import GridMetAdmissionConfig
from wepppy.climates.gridmet.gridmet_singlelocation_client import retrieve_historical_wind
from wepppy.climates.prism.bulk_client import PrismBulkClient
from wepppy.climates.prism._bulk_transport import write_json, now
from wepppy.climates.prism.wepp_adapter import build_cell, validate_years
from wepppy.nodb._derived_build import finalize, publish_files
from wepppy.nodb.core.climate_multiple_build import capture_multiple_build_inputs
from wepppy.nodb.core.climate_observed_build import _require_climate_directory

__all__ = ['run_prism800m_build']


def _locations(climate):
    watershed = climate.watershed_instance
    return {'ws': tuple(watershed.require_centroid()), **{
        str(top): tuple(watershed.hillslope_centroid_lnglat(top))
        for top, _ in watershed.centroid_hillslope_iter()}}


def _retain_cache_attempt(path, stage):
    target = stage / 'source' / path.name
    if not target.exists():
        shutil.copytree(path, target)
    return str(target.relative_to(stage))


def run_prism800m_build(climate, *, attrs=None):
    from wepppy.nodb.core.climate import ClimateSpatialMode

    climate.set_attrs(attrs)
    snapshot = capture_multiple_build_inputs(climate)
    validate_years(snapshot.observed_start_year, snapshot.observed_end_year)
    if 'us' not in climate.locales:
        raise ValueError('Historic PRISM is available only for continental US projects')
    locations = _locations(climate)
    nearest = snapshot.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated
    selected = locations if nearest else {'ws': locations['ws']}
    _require_climate_directory(climate)
    directory = Path(snapshot.cli_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stage = Path(mkdtemp(prefix='prism800m-build-', dir=directory))
    status = {'kind': 'prism800m', 'state': 'working', 'started_utc': now(),
              'start_year': snapshot.observed_start_year, 'end_year': snapshot.observed_end_year,
              'spatial_mode': int(snapshot.climate_spatialmode)}
    write_json(stage / 'build-status.json', status)
    complete = False
    try:
        client = PrismBulkClient()
        try:
            result = client.retrieve(selected, f'{snapshot.observed_start_year}-01-01',
                                     f'{snapshot.observed_end_year}-12-31')
        finally:
            # This client records only this call's attempts, including failed HTTP/parse work.
            for attempt in client.attempt_directories:
                _retain_cache_attempt(attempt, stage)
        sources = []
        for record in result.provenance:
            copied = dict(record)
            source = _retain_cache_attempt(Path(record['source_directory']), stage)
            copied.pop('cache_root')
            copied['source_directory'] = 'climate/' + stage.name + '/' + source
            copied['freshness_check_directory'] = 'climate/' + stage.name + '/source/' + record['freshness_check_attempt']
            sources.append(copied)
        write_json(stage / 'provenance.json', {'locations': result.locations, 'sources': sources,
                   'wind_location': locations['ws'], 'wind_day_alignment': 'calendar_label',
                   'station': snapshot.climatestation, 'seed': snapshot.cligen_seed,
                   'parameterization': 'ADR-0082'})
        for cell, frame in result.frames.items():
            frame.to_parquet(stage / (cell + '-source.parquet'))
        ws_cell = result.locations['ws']['cell']
        result.frames[ws_cell].to_parquet(stage / 'prism800m-source-ws.parquet')
        wind = retrieve_historical_wind(*locations['ws'], snapshot.observed_start_year,
                   snapshot.observed_end_year, admission=GridMetAdmissionConfig.from_env())
        wind.to_parquet(stage / 'gridmet-wind.parquet')
        station = CligenStationsManager(version=snapshot.cligen_db).get_station_fromid(snapshot.climatestation)
        cligen = Cligen(station, wd=str(stage))
        generated = {}
        bypassed = False
        for cell, frame in result.frames.items():
            climate.logger.info('Building PRISM cell %s (%s days)', cell, len(frame))
            generated[cell] = build_cell(cligen, frame, wind, stage, 'prism800m-' + cell,
                       seed=snapshot.cligen_seed, adjust_mx_pt5=snapshot.adjust_mx_pt5,
                       silent_pass_observed_quality_guard=snapshot.silent_pass_observed_quality_guard)
            bypassed |= bool(getattr(cligen, '_last_observed_quality_guard_bypassed', False))
        shutil.copy2(stage / generated[ws_cell][1], stage / 'wepp.cli')
        monthlies = ClimateFile(str(stage / 'wepp.cli')).calc_monthlies()
        cli_fns = None
        if nearest:
            cli_fns = {}
            for top in locations:
                if top == 'ws':
                    continue
                filename = f'prism800m-hill-{int(top)}.cli'
                shutil.copy2(stage / generated[result.locations[top]['cell']][1], stage / filename)
                cli_fns[top] = filename
            # Separate hill files allow existing spatial precipitation scaling
            # to assign different factors without same-cell overwrite collisions.
        par_fns = {top: generated[result.locations[top]['cell']][0] for top in locations if top != 'ws'} if nearest else None
        with finalize(climate) as publications:
            if capture_multiple_build_inputs(climate) != snapshot or _locations(climate) != locations:
                raise RuntimeError('PRISM build superseded by changed climate inputs or watershed geometry')
            publication = Path(publications.enter_context(TemporaryDirectory(prefix='.climate-publish-', dir=directory)))
            # Keep the full original attempt; only flat model/diagnostic outputs are published.
            for path in stage.iterdir():
                if path.is_file() and path.name != 'build-status.json':
                    shutil.copy2(path, publication / path.name)
            obsolete = [p.name for p in directory.iterdir() if p.is_file() and not p.name.startswith('.')]
            publications.enter_context(publish_files(publication, directory, climate, remove=obsolete))
            climate._observed_start_year = snapshot.observed_start_year
            climate._observed_end_year = snapshot.observed_end_year
            climate._input_years = snapshot.observed_end_year - snapshot.observed_start_year + 1
            climate.monthlies = monthlies
            climate.cli_fn = 'wepp.cli'
            climate.par_fn = station.par
            climate.sub_cli_fns = cli_fns
            climate.sub_par_fns = par_fns
            climate._observed_quality_guard_summary_warning = None
            climate._publish_quality_guard_bypass_warning_if_needed(quality_guard_bypassed=bypassed)
        complete = True
    finally:
        status.update(state='complete' if complete else 'failed', finished_utc=now())
        try:
            write_json(stage / 'build-status.json', status)
        except OSError:
            climate.logger.exception('Unable to record PRISM attempt outcome: %s', stage)
        if not complete:
            climate.logger.error('PRISM build failed; retained project evidence: %s', stage)
