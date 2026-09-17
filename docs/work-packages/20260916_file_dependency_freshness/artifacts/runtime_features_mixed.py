#!/usr/bin/env python3
"""Prepared C02 shipped-profile native acceptance; execute only in root's window.

Full independent source copy uses runtime_project_copy.py. All native readers,
owners, source mutations and exports operate on that unique disposable copy.
No catalog/profile/reader/Unitizer implementation is substituted. The explicit
fresh-output control calls the actual private cache-miss executor with a newly
prepared real submission; old artifacts remain and normal cache bindings update.
This is local owner/native acceptance, not live HTTP/RQ transport acceptance.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

from runtime_project_copy import digest_file, prepare_project_copy, verify_source

ARTIFACTS = Path(__file__).parent


def digest_json(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Run only after root releases restart/runtime window')
    parser.add_argument('--source', default='/wc1/runs/th/thespian-cleanness')
    parser.add_argument('--destination', help='New /wc1/batch/qa-*/runs/NAME; default is a unique batch')
    parser.add_argument('--label', default='initial', help='Retain separate filenames for any revised attempt')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Preparation only: --execute is required after the coordinated runtime window opens')

    # Imports/native initialization occur only on actual authorized execution.
    import geopandas as gpd
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    from osgeo import gdal
    from wepppy.nodb.core import Watershed
    from wepppy.nodb.unitizer import Unitizer, precisions
    from wepppy.nodb.mods.features_export import service, profiles

    if not args.label.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Label must contain only letters, digits, underscore or hyphen')
    identity = uuid4().hex[:12]
    wd = Path(args.destination) if args.destination else (
        Path('/wc1/batch') / ('qa-features-mixed-' + identity) / 'runs' / ('qa-features-mixed-' + identity + '-grizzly'))
    if not str(wd.absolute()).startswith('/wc1/batch/qa-'):
        raise ValueError('This probe requires a unique disposable /wc1/batch/qa-* root')
    if not wd.name.startswith('qa-features-'):
        raise ValueError('Use a globally unique qa-features-* leaf; RedisPrep keys use the leaf basename')
    root = wd.parent.parent
    output = ARTIFACTS / f'features_mixed_runtime_{args.label}.json'
    if output.exists():
        raise FileExistsError(f'Retain prior attempt; choose a new --label: {output}')
    result = {'scope': __doc__, 'started_unix': time.time(), 'uid': os.getuid(), 'gid': os.getgid(),
              'source': args.source, 'destination': str(wd), 'phases': {}, 'native_reads': [],
              'module_hashes': {}, 'errors': [], 'limits': [
                  'The two real shipped profiles cover their selected sources, not all27 catalog datasets.',
                  'Native GPKG and CSV contents are compared semantically; ZIP timestamps/artifact IDs are not identity.',
                  'Forced controls use the actual private cache-miss executor, not a public force-rebuild option.',
                  'No claim of arbitrary ABA or recursive native closure outside the observed input set.',
                  'Previously retained native failure/publication tests are cited separately, not rerun here.']}
    copy_manifest = None
    saved_artifacts = {}
    stage = 'preparation'
    evidence = root / 'features-evidence'

    def flush():
        raw = json.dumps(result, indent=2, default=str) + '\n'
        output.write_text(raw)
        if root.exists():
            (root / 'features-runtime-manifest.json').write_text(raw)

    def named(value):
        return isinstance(value, (str, bytes, os.PathLike)) and str(
            Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')

    def audit(event, values):
        if event == 'open' and named(values[0]):
            mode, flags = values[1], values[2]
            if (mode and any(token in mode for token in 'wax+')) or flags & (
                    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                raise PermissionError('Named project writes prohibited')
        if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime',
                     'os.rename', 'os.link', 'os.symlink'}:
            if any(named(value) for value in values[:2]):
                raise PermissionError('Named project mutation prohibited')

    sys.addaudithook(audit)

    def local_path(value):
        path = Path(value).resolve()
        if not path.is_relative_to(wd.resolve()):
            raise AssertionError(f'Disposable native input escaped copied project: {path}')
        return path

    real_vector, real_parquet, real_schema = gpd.read_file, pd.read_parquet, pq.read_schema

    def vector_read(path, *positional, **kwargs):
        selected = local_path(path)
        frame = real_vector(path, *positional, **kwargs)
        dataset = gdal.OpenEx(str(selected), gdal.OF_VECTOR | gdal.OF_READONLY)
        files = dataset.GetFileList() if dataset is not None else None
        driver = dataset.GetDriver().ShortName if dataset is not None else None
        dataset = None
        result['native_reads'].append({'phase': stage, 'reader': 'geopandas.read_file',
            'path': str(selected), 'driver': driver, 'gdal_file_list': files,
            'rows': len(frame), 'columns': list(frame.columns)})
        return frame

    def parquet_read(path, *positional, **kwargs):
        selected = local_path(path)
        frame = real_parquet(path, *positional, **kwargs)
        result['native_reads'].append({'phase': stage, 'reader': 'pandas.read_parquet',
            'path': str(selected), 'rows': len(frame), 'columns': list(frame.columns)})
        return frame

    def schema_read(path, *positional, **kwargs):
        selected = local_path(path)
        schema = real_schema(path, *positional, **kwargs)
        result['native_reads'].append({'phase': stage, 'reader': 'pyarrow.parquet.read_schema',
            'path': str(selected), 'schema': str(schema)})
        return schema

    def artifact_snapshot(job_result, label):
        archive = local_path(wd / job_result['artifact_relpath'])
        saved_artifacts[str(archive)] = digest_file(archive)['sha256']
        with ZipFile(archive) as zipped:
            manifest = json.loads(zipped.read('manifest.json'))
            payloads = sorted(name for name in zipped.namelist() if name.endswith(('.gpkg', '.csv')))
            assert payloads, 'Expected shipped-profile GPKG/CSV native data'
            tables = {}
            for member in payloads:
                if member.endswith('.csv'):
                    frame = pd.read_csv(io.BytesIO(zipped.read(member)))
                    rows = clean(frame.to_dict('records'))
                    tables[member] = {'columns': list(frame.columns), 'attributes': sorted(rows, key=digest_json),
                                      'geometries': []}
                else:
                    target = evidence / label / Path(member).name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zipped.read(member))
                    dataset = gdal.OpenEx(str(target), gdal.OF_VECTOR | gdal.OF_READONLY)
                    assert dataset is not None
                    for layer_index in range(dataset.GetLayerCount()):
                        layer = dataset.GetLayerByIndex(layer_index)
                        rows, geometries = [], []
                        for feature in layer:
                            properties = clean(dict(feature.items()))
                            geometry = feature.GetGeometryRef()
                            wkb = bytes(geometry.ExportToWkb()).hex() if geometry is not None else None
                            rows.append(properties)
                            geometries.append({'properties': properties, 'wkb': wkb})
                        tables[layer.GetName()] = {
                            'columns': [field.GetName() for field in layer.schema],
                            'attributes': sorted(rows, key=digest_json),
                            'geometries': sorted(geometries, key=digest_json),
                            'crs': layer.GetSpatialRef().ExportToWkt() if layer.GetSpatialRef() else None}
                    dataset = None
        assert manifest['dependency_verification']['status'] == 'verified'
        retained = evidence / f'{label}-snapshot.json'
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_text(json.dumps(tables, indent=2, default=str) + '\n')
        return {'tables': tables, 'manifest': manifest, 'snapshot': str(retained),
                'semantic_sha256': digest_json(tables),
                'attributes_sha256': digest_json({k: v['attributes'] for k, v in tables.items()}),
                'geometry_sha256': digest_json({k: sorted([g['wkb'] for g in v['geometries'] if g['wkb']])
                                               for k, v in tables.items()}),
                'row_counts': {k: len(v['attributes']) for k, v in tables.items()}}

    def execute(profile, phase, *, force=False):
        nonlocal stage
        stage = phase + ':' + profile['key'] + (':fresh_control' if force else '')
        job_id = 'qa-' + phase + '-' + profile['key'] + ('-fresh' if force else '') + '-' + uuid4().hex[:8]
        before = time.perf_counter()
        if force:
            submission = service.prepare_export_submission(wd, profile['request'])
            exported = service._run_cache_miss_export(wd, runid=copy_manifest['runid'], config=config,
                job_id=job_id, submission=submission)
        else:
            exported = service.execute_features_export(wd, runid=copy_manifest['runid'], config=config,
                job_id=job_id, payload=profile['request'])
        elapsed = time.perf_counter() - before
        snapshot = artifact_snapshot(exported, job_id)
        record = {'result': exported, 'elapsed_seconds': elapsed, 'job_id': job_id,
                  'cache_hit': exported['cache_hit'], **{k: v for k, v in snapshot.items() if k not in {'tables', 'manifest'}}}
        record['manifest'] = str(wd / exported['manifest_relpath'])
        result['phases'].setdefault(phase, {}).setdefault(profile['key'], {})['fresh' if force else 'ordinary'] = record
        print(stage, 'cache_hit', exported['cache_hit'], 'rows', snapshot['row_counts'], flush=True)
        flush()
        return exported, snapshot

    def control(profile, phase, ordinary):
        fresh_export, fresh_snapshot = execute(profile, phase, force=True)
        assert fresh_snapshot['semantic_sha256'] == ordinary['semantic_sha256'], 'Cached/rebuilt output disagrees with actual forced native export'
        result['phases'][phase][profile['key']]['fresh_matches'] = True
        return fresh_export, fresh_snapshot

    try:
        for path in sorted(Path(service.__file__).parent.rglob('*.py')):
            result['module_hashes'][str(path)] = digest_file(path)['sha256']
        for path in [Path(service.__file__).parent / 'layer_catalog.yaml',
                     *sorted(profiles.default_profiles_dir().glob('*.yml'))]:
            result['module_hashes'][str(path)] = digest_file(path)['sha256']
        flush()
        copy_manifest = prepare_project_copy(args.source, wd, root / 'full-project-copy.json')
        result['copy_manifest'] = str(root / 'full-project-copy.json')
        result['copied_file_count'] = len(copy_manifest['source_files'])
        result['copied_bytes'] = copy_manifest['logical_bytes']
        watershed = Watershed.getInstance(str(wd))
        unitizer = Unitizer.getInstance(str(wd))
        assert Path(watershed.wd).resolve() == wd.resolve() == Path(unitizer.wd).resolve()
        assert watershed.runid == copy_manifest['runid'] == unitizer.runid
        config = watershed.config_stem
        result['runid'], result['config'] = copy_manifest['runid'], config
        chosen = [item for item in profiles.load_builtin_profiles() if item['key'] in ('prep_details', 'post_wepp')]
        assert len(chosen) == 2
        result['profiles'] = chosen
        result['initial_preferences'] = dict(unitizer.preferences)
        result['initial_preferences_fingerprint'] = unitizer.preferences_fingerprint()
        last = {}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gpd, 'read_file', vector_read))
            stack.enter_context(patch.object(pd, 'read_parquet', parquet_read))
            stack.enter_context(patch.object(pq, 'read_schema', schema_read))
            dependency_paths = set()
            for profile in chosen:
                submission = service.prepare_export_submission(wd, profile['request'])
                result.setdefault('selected_dependencies', {})[profile['key']] = submission.dependency_snapshot.to_mapping()
                for entry in submission.dependency_snapshot.entries:
                    path = local_path(wd / entry.relpath)
                    if path.is_file():
                        dependency_paths.add(path)
                ordinary, snapshot = execute(profile, 'baseline')
                last[profile['key']] = control(profile, 'baseline', snapshot)

            result['unique_regular_dependencies'] = [str(path) for path in sorted(dependency_paths)]
            for phase in ('touch_only', 'equal_byte_replace'):
                for path in sorted(dependency_paths):
                    before = path.stat()
                    if phase == 'touch_only':
                        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
                    else:
                        pending = path.with_name(path.name + '.qa-equal-' + uuid4().hex[:6])
                        pending.write_bytes(path.read_bytes())
                        shutil.copystat(path, pending)
                        pending.replace(path)
                for profile in chosen:
                    previous, previous_snapshot = last[profile['key']]
                    exported, snapshot = execute(profile, phase)
                    assert exported['cache_hit'] is True and exported['artifact_relpath'] == previous['artifact_relpath']
                    assert snapshot['semantic_sha256'] == previous_snapshot['semantic_sha256']
                    last[profile['key']] = exported, snapshot

            parquet = local_path(wd / 'watershed/hillslopes.parquet')
            source_table = pq.read_table(parquet)
            candidates = [name for name in source_table.column_names
                          if name.lower() in ('area', 'area_m2', 'slope', 'slope_scalar', 'length', 'length_m')
                          and (pa.types.is_floating(source_table.schema.field(name).type)
                               or pa.types.is_integer(source_table.schema.field(name).type))]
            assert candidates, 'Representative native table needs a exported nonidentity numeric field'
            column = candidates[0]
            values = source_table[column].to_pylist()
            index = next(i for i, value in enumerate(values) if value is not None and math.isfinite(value))
            previous_value = values[index]
            values[index] = previous_value * 2 + 1
            modified = source_table.set_column(source_table.schema.get_field_index(column),
                source_table.schema.field(column), pa.array(values, type=source_table.schema.field(column).type))
            evidence.mkdir(exist_ok=True)
            shutil.copy2(parquet, evidence / 'hillslopes-before.parquet')
            before = parquet.stat()
            pending = parquet.with_name(parquet.name + '.qa-changed')
            pq.write_table(modified, pending)
            pending.replace(parquet)
            os.utime(parquet, ns=(before.st_atime_ns, before.st_mtime_ns))
            result['parquet_mutation'] = {'path': str(parquet), 'column': column, 'row': index,
                'before': previous_value, 'after': values[index], 'mtime_restored': True,
                'size_before': before.st_size, 'size_after': parquet.stat().st_size}
            for profile in chosen:
                old = last[profile['key']][1]
                exported, snapshot = execute(profile, 'parquet_changed')
                assert not exported['cache_hit'] and snapshot['attributes_sha256'] != old['attributes_sha256']
                assert snapshot['geometry_sha256'] == old['geometry_sha256']
                last[profile['key']] = control(profile, 'parquet_changed', snapshot)

            geometry = local_path(watershed.subwta_shp)
            payload = json.loads(geometry.read_text())
            selected = next(feature for feature in payload['features'] if (feature.get('geometry') or {}).get('coordinates'))
            shutil.copy2(geometry, evidence / 'subcatchments-before.geojson')
            def translate(values):
                if values and isinstance(values[0], (int, float)):
                    return [values[0] + 0.0001, values[1] + 0.0001, *values[2:]]
                return [translate(value) for value in values]
            selected['geometry']['coordinates'] = translate(selected['geometry']['coordinates'])
            before = geometry.stat()
            geometry.write_text(json.dumps(payload))
            os.utime(geometry, ns=(before.st_atime_ns, before.st_mtime_ns))
            result['geometry_mutation'] = {'path': str(geometry), 'properties': selected['properties'],
                'translation_degrees': [0.0001, 0.0001], 'mtime_restored': True}
            for profile in chosen:
                old = last[profile['key']][1]
                exported, snapshot = execute(profile, 'geometry_changed')
                assert not exported['cache_hit']
                assert snapshot['attributes_sha256'] == old['attributes_sha256']
                if profile['key'] == 'post_wepp':
                    assert snapshot['geometry_sha256'] != old['geometry_sha256']
                last[profile['key']] = control(profile, 'geometry_changed', snapshot)

            unitizer = Unitizer.getInstance(str(wd))
            updates = {key: next(unit for unit in options if unit != unitizer.preferences.get(key))
                       for key, options in precisions.items() if len(options) > 1}
            unitizer.set_preferences(updates)
            result['updated_preferences'] = dict(unitizer.preferences)
            result['updated_preferences_fingerprint'] = unitizer.preferences_fingerprint()
            assert result['updated_preferences_fingerprint'] != result['initial_preferences_fingerprint']
            for profile in chosen:
                old = last[profile['key']][1]
                exported, snapshot = execute(profile, 'units_changed')
                assert not exported['cache_hit'] and snapshot['attributes_sha256'] != old['attributes_sha256']
                assert snapshot['geometry_sha256'] == old['geometry_sha256']
                last[profile['key']] = control(profile, 'units_changed', snapshot)
        result['historical_artifacts_unchanged'] = all(digest_file(path)['sha256'] == expected
                                                     for path, expected in saved_artifacts.items())
        assert result['historical_artifacts_unchanged']
        result['historical_artifact_count'] = len(saved_artifacts)
        result['completed'] = True
    except BaseException as error:  # Probe boundary: retain failure and all native work.
        result['errors'].append({'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()})
        raise
    finally:
        result['modules_unchanged'] = all(digest_file(path)['sha256'] == expected
                                          for path, expected in result['module_hashes'].items())
        if copy_manifest is not None:
            try:
                result['source_verification'] = verify_source(copy_manifest, hash_bytes=True)
            except BaseException as error:
                result['source_verification'] = {'unchanged': False, 'type': type(error).__name__, 'error': str(error)}
                result['completed'] = False
        result['finished_unix'] = time.time()
        flush()
        print(json.dumps({key: result.get(key) for key in ('completed', 'errors', 'modules_unchanged',
              'source_verification', 'historical_artifact_count', 'destination')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
