"""Run-scoped source readiness and immutable M1 publication.

Contract: docs/production_m1.md. Long processing never holds a NoDb lock.
"""
from copy import deepcopy
from functools import lru_cache
from datetime import datetime, timezone
import json
import logging
from redis.exceptions import RedisError
from pathlib import Path
import re
import shutil
import uuid

import numpy as np
import rasterio

from . import dnbr
from .encoding import inspect_encoding
from .integration import M1Inputs, build_m1_predictors
from .m1_inputs import digest, read_raster, prepare, read_json, companions
from .postfire_debris_flow import PostfireDebrisFlow, empty_state
from .results import RainfallInputs, build_m1_results

__all__ = ['WorkflowError', 'get_state', 'execute_upload', 'execute_model']
ACTIVE = {'staged', 'queued', 'running', 'enqueue_unknown'}
ID = re.compile(r'[0-9a-f]{32}\Z')
FILES = ('events.parquet', 'design.parquet', 'inverse.parquet', 'manifest.json')
LABELS = {'watershed': ('Delineate watershed', '#subcatchments-delineation'),
          'soils': ('Build soils', '#soils'), 'sbs': ('Set soil burn severity', '#disturbed-sbs'),
          'k': ('Prepare in RUSLE', '#rusle'), 'climate': ('Build climate', '#climate'),
          'dnbr': ('Upload dNBR', '#postfire-debris-flow')}


class WorkflowError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.status = code, status


def now():
    return datetime.now(timezone.utc).isoformat()


def notify(wd):
    from wepppy.nodb.redis_prep import RedisPrep
    try:
        prep = RedisPrep.getInstance(str(wd))
        prep.redis.hset(prep.run_id, 'postfire_debris_flow:revision', uuid.uuid4().hex)
    except RedisError:
        logging.getLogger(__name__).exception('Preflight notification failed after durable postfire state commit; reload reconciles state')


def state_at(wd):
    controller = PostfireDebrisFlow.tryGetInstance(str(wd))
    return controller.state if controller is not None else empty_state()


def mutable(wd):
    from wepppy.nodb.core import Ron
    from wepppy.nodb.base import clear_nodb_file_cache
    ron = Ron.getInstance(str(wd))
    if ron.readonly:
        raise WorkflowError('readonly', 'This project is read-only.', 403)
    clear_nodb_file_cache(ron.runid, pup_relpath='postfire_debris_flow.nodb', wd_override=str(wd))
    obj = PostfireDebrisFlow.tryGetInstance(str(wd))
    return obj if obj is not None else PostfireDebrisFlow(str(wd), ron.config_stem)


def safe(wd, path, *, exists=True):
    if '..' in Path(path).parts or '..' in Path(wd).parts:
        raise WorkflowError('invalid_path', 'Parent paths are not permitted.', 422)
    root = Path(wd).absolute()
    path = Path(path).absolute()
    if not path.is_relative_to(root):
        raise WorkflowError('invalid_path', 'Project data are outside the project directory.', 422)
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise WorkflowError('invalid_path', 'Project data must not use symbolic links.', 422)
        if parent == root:
            break
    if exists and not path.is_file():
        raise WorkflowError('missing_input', 'Required project data are missing.', 422)
    return path


def directory(wd, identity):
    if not isinstance(identity, str) or not ID.fullmatch(identity):
        raise WorkflowError('invalid_candidate', 'Invalid upload identifier.')
    return safe(wd, Path(wd)/'postfire_debris_flow'/'attempts'/identity, exists=False)


def signature(wd, path, *, strong=False):
    p = safe(wd, path)
    st = p.stat()
    return [str(p.relative_to(Path(wd).absolute())), st.st_size, st.st_mtime_ns, st.st_ctime_ns] + ([digest(p)] if strong else [])


def noaa_current(wd, path, centroid):
    if not centroid or not path.is_file(): return False
    if path.stat().st_size > 1024*1024: return False
    from decimal import Decimal, InvalidOperation
    try:
        safe(wd,path)
        text=path.read_text()
        if not text.startswith('Point precipitation frequency estimates (millimeters/hour)'): return False
        metadata=dict(line.split(':',1) for line in text.splitlines() if line.startswith(('Latitude:','Longitude:')))
        for key,expected in zip(('Longitude','Latitude'),centroid):
            token=metadata[key].strip().removesuffix(' Degree')
            value=Decimal(token)
            if not value.is_finite() or abs(value.as_tuple().exponent)>12: return False
            if Decimal(str(expected)).quantize(value)!=value: return False
        return True
    except (OSError,ValueError,KeyError,InvalidOperation):
        return False


def k_current(wd, files, polaris_completed):
    """Check K's own published provenance, independent of full RUSLE completion."""
    if not polaris_completed:
        return False
    from wepppy.nodb.mods.rusle.k_integration import NEAR_SURFACE_DEPTHS
    try:
        manifest = read_json(safe(wd, files['k_manifest']))['k']
        generated = datetime.fromisoformat(manifest['generated_utc'].replace('Z', '+00:00')).timestamp()
        if manifest['statistic'] != 'mean' or 'polaris_nomograph' not in manifest['selected_modes']:
            return False
        if manifest['artifacts']['nomograph'] != 'rusle/k_polaris_nomograph.tif':
            return False
        for prop in ('sand', 'silt', 'clay', 'om', 'ksat'):
            for depth in NEAR_SURFACE_DEPTHS:
                files[f'polaris_{prop}_{depth}'] = Path(wd)/'polaris'/f'{prop}_mean_{depth}.tif'
        cfvo = manifest.get('cfvo_summary', {})
        if cfvo.get('status') == 'available':
            source = cfvo.get('source', {})
            for key in ('top_path', 'sub_path', 'source_top_path', 'source_sub_path'):
                if source.get(key): files[f'polaris_cfvo_{key}'] = Path(wd)/source[key]
        elif manifest.get('mode_contract', {}).get('polaris_nomograph', {}).get('cfvo_profile_fragment_adjustment', {}).get('status') == 'applied':
            return False
        k_time_ns = safe(wd, files['k']).stat().st_mtime_ns
        # A newer owner build or source cannot belong to this completed K map.
        return polaris_completed <= generated and all(
            safe(wd, path).stat().st_mtime_ns <= k_time_ns
            for key, path in files.items() if key.startswith('polaris_') or key == 'dem')
    except (OSError, ValueError, KeyError, TypeError):
        return False


def sources(wd, *, rainfall=True, frequency='cli'):
    from wepppy.nodb.core import Ron, Watershed, Soils, Climate
    from wepppy.nodb.mods.disturbed import Disturbed
    from wepppy.nodb.project_config_capabilities import resolve_run_capability_authority
    ron = Ron.getInstance(str(wd))
    watershed = Watershed.getInstance(str(wd))
    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
    prep = RedisPrep.getInstance(str(wd))
    completed = {key: prep[str(task)] for key, task in (
        ("watershed", TaskEnum.build_subcatchments), ("soils", TaskEnum.build_soils),
        ("sbs", TaskEnum.init_sbs_map), ("climate", TaskEnum.build_climate),
        ("polaris", TaskEnum.fetch_polaris), ("abstract", TaskEnum.abstract_watershed),
        ("landuse", TaskEnum.build_landuse), ("rangeland", TaskEnum.build_rangeland_cover))}
    authority = resolve_run_capability_authority(ron)
    eligible = ('postfire_debris_flow' in ron.mods and watershed.delineation_backend_is_wbt
                and authority.locale_profile == 'continental-us')
    files = {'dem': Path(ron.dem_fn), 'mask': Path(watershed.wbt_wd)/'bound.tif',
             'outlet': Path(watershed.wbt_wd)/'outlet.geojson'}
    checks = {'watershed': bool(completed['watershed']) and all(p.is_file() for p in files.values()) and files['dem'].suffix.lower() in ('.tif','.tiff')}
    selections = {'locale': authority.locale_profile, 'backend': bool(watershed.delineation_backend_is_wbt),
                  'completed': {'watershed': completed['watershed']}, 'dem': str(files['dem']), 'outlet': watershed.outlet.as_dict() if watershed.outlet else None}
    if rainfall:
        def after(key, parent):
            return bool(completed[key] and completed[parent] and completed[key] > completed[parent])
        checks['watershed'] = checks['watershed'] and after('abstract', 'watershed')
        soils = Soils.tryGetInstance(str(wd))
        climate = Climate.tryGetInstance(str(wd))
        disturbed = Disturbed.tryGetInstance(str(wd))
        inventory = getattr(soils, 'soils', {}) or {}
        soil_paths = [Path(soils.soils_dir)/str(summary.fname) for summary in inventory.values()] if soils else []
        checks['soils'] = bool(after('soils','abstract') and (after('soils','landuse') or after('soils','rangeland')) and soils and soils.has_soils and soil_paths and all(p.is_file() for p in soil_paths))
        for index, path in enumerate(sorted(soil_paths)):
            files[f'soil_{index}'] = path
        if disturbed:
            files['sbs'] = Path(disturbed.sbs_4class_path)
        files['k'] = Path(wd)/'rusle'/'k_polaris_nomograph.tif'
        files['k_manifest'] = Path(wd)/'rusle'/'manifest.json'
        files['cli'] = Path(wd)/'climate'/'wepp_cli.parquet'
        cli_name = getattr(climate, 'cli_fn', None)
        if climate and cli_name:
            files['active_cli'] = Path(climate.cli_dir)/cli_name
        noaa = Path(climate.cli_dir)/'atlas14_intensity_pds_mean_metric.csv' if climate else Path(wd)/'climate'/'atlas14_intensity_pds_mean_metric.csv'
        if frequency == 'noaa':
            files['noaa'] = noaa
        checks.update(sbs=bool(completed['sbs'] and disturbed and files['sbs'].is_file()),
                      k=files['k'].is_file() and files['k_manifest'].is_file(),
                      climate=bool(after('climate','abstract') and climate and files['cli'].is_file()
                          and files.get('active_cli') and files['active_cli'].is_file()
                          and files['cli'].stat().st_mtime_ns >= files['active_cli'].stat().st_mtime_ns), noaa=noaa_current(wd,noaa,getattr(watershed,'_centroid',None)))
        selections['engine_sha256'] = engine_identity()
        from whitebox_tools import WhiteboxTools
        tool = WhiteboxTools()
        binary = Path(tool.exe_path)/tool.exe_name
        selections['wbt_sha256'] = cached_digest(binary)
        selections['completed'] = completed
        candidate = Path(wd)/'polaris'/'manifest.json'
        if candidate.is_file(): files['polaris_manifest'] = candidate
        checks['k'] = checks['k'] and k_current(wd, files, completed['polaris'])
        selections['sbs'] = {key: getattr(disturbed, key, None) for key in ('disturbed_fn','classes','breaks','nodata_vals','sbs_mode','fire_date')}
        selections['climate'] = {key: getattr(climate, key, None) for key in ('catalog_id','climatestation','input_years','observed_start_year','observed_end_year','future_start_year','future_end_year','precip_scale_factor','precip_monthly_scale_factors','adjust_mx_pt5')}
        selections['soil_mapping'] = dict(getattr(soils, 'domsoil_d', {}) or {})
        for key, relative in (('polaris_manifest','polaris/manifest.json'),):
            candidate = Path(wd)/relative
            if candidate.is_file(): files[key] = candidate
        mode = getattr(climate, 'climate_mode', None)
        selections.update(climate_mode=getattr(mode, 'name', str(mode)), cli_fn=getattr(climate, 'cli_fn', None),
                          soil_source=getattr(soils, 'soil_source', None),
                          soil_mode=str(getattr(soils, 'mode', None)))
    # External masks affect decoded project support; inert statistics do not.
    for key in ('dem', 'mask'):
        companion = Path(str(files[key]) + '.msk')
        if companion.exists() or companion.is_symlink():
            files[key + '_mask'] = safe(wd, companion)
    snapshot = {'selections': selections, 'files': {key: signature(wd,p) if p.is_file() else None for key,p in files.items()}}
    return eligible, bool(ron.readonly), checks, files, snapshot


def artifacts_current(wd, record, *, strong=True):
    try:
        return bool(record.get('artifacts')) and all(signature(wd, Path(wd)/rel,strong=strong and len(sig)==5)==(sig if strong else sig[:4]) for rel,sig in record['artifacts'].items())
    except (OSError, WorkflowError):
        return False


def reconcile_attempts(wd, state, connection, *, persist=False):
    """RQ owns terminal status; read projections never persist reconciliation."""
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    from wepppy.nodb.core import Ron
    runid = Ron.getInstance(str(wd)).runid
    result=deepcopy(state)
    changes={}
    for kind in ('upload_attempt','run_attempt'):
        attempt=result[kind]
        if not attempt or attempt['phase'] not in ACTIVE: continue
        job_id=attempt.get('job_id')
        if not job_id:
            raise WorkflowError('invalid_receipt', 'Operation receipt is missing its job identifier.', 409)
        try:
            job=Job.fetch(job_id,connection=connection)
            if (tuple(job.args)!=(runid,attempt['id']) or job.origin!='default'
                    or job.func_name != 'wepppy.rq.postfire_debris_flow_rq.' + ('upload_dnbr_rq' if kind=='upload_attempt' else 'run_m1_rq')):
                raise WorkflowError('job_mismatch','Job association could not be verified.',409)
            phase=job.get_status(refresh=True)
            phase=getattr(phase,'value',phase)
        except NoSuchJobError:
            phase='missing'
        latest_state = state_at(wd)
        latest = latest_state[kind]
        if latest and (latest['id'] != attempt['id'] or latest['phase'] not in ACTIVE):
            # Publication commits attempt and accepted artifacts atomically. Keep
            # that whole revision together when a worker finishes during this read.
            result = latest_state
            changes.pop(kind, None)
            continue
        if phase in ('failed','stopped','canceled','finished','missing'):
            attempt.update(phase='failed',retryable=True,error={'code':'job_incomplete','message':'The operation did not publish a result. Try again.'})
        attempt['job_id']=job_id
        if attempt != state[kind]: changes[kind]=attempt
    if persist and changes:
        def apply(current):
            for kind,attempt in changes.items():
                if current[kind] and current[kind]['id']==attempt['id'] and current[kind]['phase'] in ACTIVE:
                    current[kind].update(phase=attempt['phase'],retryable=attempt['retryable'],error=attempt['error'],job_id=attempt['job_id'])
        mutable(wd).change(apply)
    return result


def public_attempt(attempt):
    if attempt is None:
        return None
    return {key: deepcopy(attempt.get(key)) for key in ('id','job_id','phase','created_at','error','retryable','filename')}


def get_state(wd, config, *, frequency=None, reconcile=True):
    from wepppy.nodb.core import Ron
    runid = Ron.getInstance(str(wd)).runid
    state = state_at(wd)
    if reconcile and any(state[k] and state[k]['phase'] in ACTIVE for k in ('upload_attempt','run_attempt')):
        import redis
        from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
            from wepppy.nodb.core import Ron
            from wepppy.rq.submission_recovery import rq_submission_lock, RqSubmissionConflict
            runid = Ron.getInstance(str(wd)).runid
            try:
                with rq_submission_lock(connection, f'{runid}:postfire-admission', lifecycle_key=runid, blocking_timeout=0):
                    state=reconcile_attempts(wd,state_at(wd),connection)
            except RqSubmissionConflict:
                state=state_at(wd)
    if frequency is not None:
        state['frequency_source'] = frequency
    eligible, readonly, checks, paths, snapshot = sources(wd, frequency=state['frequency_source'])
    active = deepcopy(state['active_dnbr'])
    upload_sources = sources(wd, rainfall=False)
    checks['dnbr'] = bool(active and active['snapshot'] == upload_sources[4] and artifacts_current(wd,active,strong=False))
    if active:
        active['current'] = checks['dnbr']
        active = {k:v for k,v in active.items() if k not in ('snapshot','source_id','source_sha256','artifacts')}
    result = deepcopy(state['last_successful_run'])
    current = bool(result and checks['dnbr'] and artifacts_current(wd,result,strong=False) and result['snapshot'] == {'inputs': snapshot, 'dnbr': active['id'] if active else None, 'frequency': state['frequency_source']})
    if result:
        result.pop('snapshot', None)
        result.pop('artifacts', None)
        result.pop('predictor_artifacts', None)
        result['current'] = current
        result['files'] = [{'name': name, 'url': f'/rq-engine/api/runs/{runid}/{config}/postfire-debris-flow/files/{result["id"]}/{name}'} for name in FILES]
    required = [{'key': key, 'ready': bool(checks.get(key)), 'reason': None if checks.get(key) else 'missing_input',
                 'message': '' if checks.get(key) else label, 'control': anchor} for key,(label,anchor) in LABELS.items()]
    return {'schema_version': 1, 'eligible': eligible, 'readonly': readonly,
            'unavailable_reason': None if eligible else 'Post-fire debris flow requires a WBT project in the continental US.',
            'required': required, 'noaa_available': bool(checks.get('noaa')),
            'frequency_source': state['frequency_source'], 'upload_ready': eligible and not readonly and upload_sources[2]['watershed'],
            'run_ready': eligible and not readonly and all(item['ready'] for item in required) and (state['frequency_source']!='noaa' or checks['noaa']),
            'upload': public_attempt(state['upload_attempt']), 'run': public_attempt(state['run_attempt']),
            'dnbr': active, 'results': result, 'freshness': 'current' if current else ('stale' if result else 'absent')}


def update_attempt(wd, kind, identity, **changes):
    def apply(state):
        attempt = state[kind]
        if not attempt or attempt['id'] != identity:
            raise WorkflowError('superseded', 'Inputs changed. Run the model again.', 409)
        attempt.update(changes)
    mutable(wd).change(apply)


def execute_upload(wd, identity):
    state = state_at(wd); attempt = state['upload_attempt']
    if not attempt or attempt['id'] != identity:
        raise WorkflowError('superseded', 'Upload was superseded.', 409)
    update_attempt(wd, 'upload_attempt', identity, phase='running')
    target = directory(wd, identity)
    eligible, readonly, checks, files, snapshot = sources(wd, rainfall=False)
    if not eligible or readonly or not checks['watershed'] or snapshot != attempt['snapshot']:
        raise WorkflowError('superseded', 'The watershed changed. Upload the map again.', 409)
    project_sha256 = {str(path): digest(path) for path in files.values()}
    # Derive the positive routed watershed mask with the accepted M1 decoder.
    values, valid, grid = read_raster(files['mask'])
    prepare(target/'mask.tif', (valid & (values>0)).astype(float), np.ones(valid.shape,dtype=bool), grid)
    # The upload decoder accepts self-contained files; project DEMs may have
    # validated inert statistics caches or external masks. Preserve decoded support.
    dem_values, dem_valid, dem_grid = read_raster(files['dem'], target_grid=True)
    reference_dem = target/'dem.tif'
    prepare(reference_dem, dem_values, dem_valid, dem_grid)
    del dem_values, dem_valid
    source = directory(wd, attempt['source_id'])/'source'/attempt['filename']
    refs = tuple(source.parent.glob('*')) if source.suffix.lower()=='.vrt' else ()
    def verify_sources():
        if any(digest(path) != expected for path, expected in project_sha256.items()):
            raise WorkflowError('superseded', 'The watershed changed. Upload the map again.', 409)
        if not attempt.get('source_sha256') or any(digest(safe(wd, Path(wd)/rel))!=h for rel,h in attempt['source_sha256'].items()):
            raise WorkflowError('changed_source', 'Uploaded files changed. Upload the map again.', 409)
    verify_sources()
    encoding = inspect_encoding(source, reference_dem, target/'mask.tif', refs=tuple(p for p in refs if p!=source), **attempt['encoding'])
    verify_sources()
    manifest = dnbr.normalize_dnbr(source, reference_dem, target/'mask.tif', target/'normalized',
                                  scale_factor=encoding['factor'], add_offset=encoding['offset'],
                                  source_refs=tuple(p for p in refs if p!=source))
    verify_sources()
    (target/'encoding.json').write_text(json.dumps(encoding, allow_nan=False))
    prepared, finite, _ = read_raster(target/'normalized'/'dnbr.tif', continuous_missing=True)
    observed = prepared[finite & valid & (values>0)]
    summary = {'id': identity, 'filename': attempt['filename'], 'format': encoding['format'], 'dtype': encoding['dtype'],
               'cell_size_m': [grid['transform'][0], abs(grid['transform'][4])],
               'coverage_fraction': manifest['watershed']['coverage_fraction'], 'source_range': encoding['source']['range'],
               'prepared_range': [float(observed.min()), float(observed.max())], 'scale_mode': encoding['mode'],
               'scale_factor': encoding['factor'], 'add_offset': encoding['offset'], 'scale_method': encoding['method'],
               'completed_at': now(), 'snapshot': snapshot, 'source_id': attempt['source_id'], 'source_sha256': attempt['source_sha256']}
    if sources(wd, rainfall=False)[4] != snapshot:
        raise WorkflowError('superseded', 'The watershed changed. Upload the map again.', 409)
    summary['artifacts'] = {str(path.relative_to(Path(wd))): signature(wd,path,strong=True) for path in (*files.values(), *[Path(wd)/rel for rel in attempt['source_sha256']], target/'normalized'/'dnbr.tif', target/'normalized'/'manifest.json', target/'encoding.json', target/'mask.tif', reference_dem)}
    verify_sources()
    verified_sources = {rel: signature(wd, Path(wd)/rel) for rel in summary['artifacts']}
    def publish(current):
        if any(signature(wd, Path(wd)/rel)!=sig for rel,sig in verified_sources.items()):
            raise WorkflowError('changed_source','Uploaded files changed. Upload the map again.',409)
        if current['upload_attempt']['id'] != identity or sources(wd,rainfall=False)[4] != snapshot:
            raise WorkflowError('superseded', 'Upload was superseded.', 409)
        current['active_dnbr'] = summary
        current['upload_attempt'].update(phase='complete', retryable=True)
    mutable(wd).change(publish)


def reuse_predictors(wd, accepted, hashes, binary_hash, output):
    """Reuse only a published predictor bundle with verified content identities."""
    if not accepted or not accepted.get('predictor_artifacts'):
        return False
    if not artifacts_current(wd, {'artifacts': accepted['predictor_artifacts']}):
        return False
    previous = directory(wd, accepted['id'])/'predictors'
    manifest = read_json(previous/'manifest.json')
    if manifest['tool']['sha256'] != binary_hash:
        return False
    if any(hashes.get(path) != checksum for path, checksum in manifest['sources_sha256'].items()):
        return False
    engine = accepted['snapshot']['inputs']['selections'].get('engine_sha256')
    if not engine or engine != engine_identity():
        return False
    from .rainfall_io import validate_predictors
    validate_predictors(manifest)
    output.mkdir()
    for relative in accepted['predictor_artifacts']:
        source = safe(wd, Path(wd)/relative)
        local = source.relative_to(previous)
        destination = safe(wd, output/local, exists=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return True


@lru_cache(maxsize=64)
def _digest_version(path, version):
    return digest(path)


def cached_digest(path):
    path = Path(path)
    stat = path.stat()
    return _digest_version(str(path), (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))


def engine_identity():
    root = Path(__file__).parent
    return {name: cached_digest(root/name) for name in ('integration.py','m1_inputs.py',
        'staley2017.py','dnbr.py','encoding.py','rainfall.py','rainfall_io.py','results.py','production.py')}


def execute_model(wd, identity, binary):
    state=state_at(wd); attempt=state['run_attempt']; active=state['active_dnbr']
    if not attempt or attempt['id']!=identity or not active:
        raise WorkflowError('superseded', 'Run was superseded.',409)
    update_attempt(wd,'run_attempt',identity,phase='running')
    eligible, readonly, checks, paths, snapshot = sources(wd,frequency=state['frequency_source'])
    expected={'inputs':snapshot,'dnbr':active['id'],'frequency':state['frequency_source']}
    if not eligible or readonly or expected != attempt['snapshot'] or not all(checks.values() if state['frequency_source']=='noaa' else (v for k,v in checks.items() if k!='noaa')):
        raise WorkflowError('superseded','Required project data changed. Run the model again.',409)
    if not artifacts_current(wd, active):
        raise WorkflowError('changed_source','Uploaded files changed. Upload the map again.',409)
    root=directory(wd,identity); root.mkdir(exist_ok=True)
    normalization=directory(wd,active['id'])/'normalized'
    manifest=read_json(normalization/'manifest.json')
    lineage=tuple(Path(p) for p in manifest['input_sha256'])
    paths.update(dnbr=normalization/'dnbr.tif',dnbr_manifest=normalization/'manifest.json')
    all_paths=set(paths.values())|set(lineage)
    for p in tuple(all_paths):
        safe(wd,p)
        if p.suffix.lower() in ('.tif','.tiff'):all_paths.update(companions(p))
    hashes={str(p.absolute()):digest(p) for p in all_paths}
    binary_hash = digest(binary)
    if not reuse_predictors(wd, state['last_successful_run'], hashes, binary_hash, root/'predictors'):
        build_m1_predictors(M1Inputs(dem=paths['dem'],mask=paths['mask'],outlet=paths['outlet'],sbs=paths['sbs'],
                           k=paths['k'],k_manifest=paths['k_manifest'],dnbr=paths['dnbr'],dnbr_manifest=paths['dnbr_manifest'],
                           lineage_sources=lineage,expected_sha256=hashes,wbt_sha256=digest(binary),source_kind='real',
                           sbs_alignment='nearest'),root/'predictors',wbt_executable=binary)
    predictor=root/'predictors'/'manifest.json'
    result_hashes={**hashes,str(predictor):digest(predictor)}
    from wepppy.nodb.core import Ron
    mode=snapshot['selections']['climate_mode']
    build_m1_results(RainfallInputs(predictor,paths['cli'],result_hashes,Ron.getInstance(str(wd)).runid,mode,
                     'simulation_labels' if mode in ('Vanilla','Future','PRISM') else 'calendar',active['id'],noaa_csv=paths.get('noaa')),
                     root/'results',frequency_source=state['frequency_source'],return_intervals=(1,2,5,10),durations=(15,30,60),target_probabilities=(.5,))
    if any(digest(p)!=h for p,h in hashes.items()) or sources(wd,frequency=state['frequency_source'])[4]!=snapshot:
        raise WorkflowError('superseded','Inputs changed. Run the model again.',409)
    destination=root/'results'
    result_manifest=read_json(destination/'manifest.json')
    import pandas as pd
    area_warning = 'area_outside_study_range' in result_manifest['predictor_snapshot']['warnings']
    partial=any(v.get('value') is None for v in result_manifest['predictor_snapshot']['predictors'].values())
    for name in ('events.parquet', 'design.parquet'):
        frame = pd.read_parquet(destination/name)
        partial = partial or bool(frame['probability'].isna().any())
    predictor_artifacts = {str(path.relative_to(Path(wd))):signature(wd,path,strong=True) for path in (root/'predictors').rglob('*') if path.is_file()}
    result_artifacts = {str((destination/name).relative_to(Path(wd))):signature(wd,destination/name,strong=True) for name in FILES}
    def publish(current):
        if (current['run_attempt']['id']!=identity or current['active_dnbr']['id']!=active['id']
                or current['frequency_source']!=state['frequency_source']
                or sources(wd,frequency=state['frequency_source'])[4]!=snapshot
                or not artifacts_current(wd,current['active_dnbr'], strong=False)
                or not artifacts_current(wd, {'artifacts': result_artifacts}, strong=False)
                or not artifacts_current(wd, {'artifacts': predictor_artifacts}, strong=False)):
            raise WorkflowError('superseded','Inputs changed. Run the model again.',409)
        current['last_successful_run']={'id':identity,'completed_at':now(),'snapshot':expected,'partial':partial,'area_warning':area_warning,
            'artifacts': result_artifacts, 'predictor_artifacts': predictor_artifacts}
        current['run_attempt'].update(phase='complete',retryable=True)
    mutable(wd).change(publish)
