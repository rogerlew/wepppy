#!/usr/bin/env python3
"""Actual direct Omni/SBS acceptance on an independent full Grizzly copy.

Run only after the coordinated development restart. No native/model seams,
shortened climate, named-project hydration or named writes. This does not replace
the separate live HTTP/RQ acceptance. Every failed/partial attempt is retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from uuid import uuid4

from runtime_project_copy import copy_one, digest_file, prepare_project_copy, verify_source, write_json


MODULES = (
    'wepppy/nodb/mods/omni/omni.py',
    'wepppy/nodb/mods/omni/omni_sbs_freshness.py',
    'wepppy/nodb/mods/omni/omni_run_orchestration_service.py',
    'wepppy/nodb/mods/omni/omni_mode_build_services.py',
    'wepppy/nodb/mods/omni/omni_clone_contrast_service.py',
    'wepppy/nodb/mods/omni/omni_station_catalog_service.py',
    'wepppy/nodb/core/landuse.py',
    'wepppy/nodb/core/soils.py',
)


def code_hashes(repository):
    return {name: digest_file(repository / name)['sha256'] for name in MODULES}


def make_control(template, destination, severity):
    """Explicit synthetic low/high classes on the retained real SBS footprint."""
    import numpy as np
    from osgeo import gdal
    from wepppy.nodb.mods.baer.sbs_map import _SBS_4CLASS_EXPORT_COLORS

    source = gdal.Open(str(template), gdal.GA_ReadOnly)
    if source is None or source.RasterCount != 1:
        raise RuntimeError('Expected the retained real single-band SBS template')
    band = source.GetRasterBand(1)
    values = band.ReadAsArray()
    mask = band.GetMaskBand().ReadAsArray() != 0
    nodata = band.GetNoDataValue()
    if nodata is not None:
        mask &= values != nodata
    if not np.any(mask):
        raise RuntimeError('Real SBS template has no valid footprint')
    output = np.full(values.shape, 255, dtype=np.uint8)
    output[mask] = severity
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    target = gdal.GetDriverByName('GTiff').Create(
        str(destination), source.RasterXSize, source.RasterYSize, 1,
        gdal.GDT_Byte, options=['COMPRESS=DEFLATE'])
    target.SetGeoTransform(source.GetGeoTransform())
    target.SetProjection(source.GetProjection())
    target_band = target.GetRasterBand(1)
    target_band.SetNoDataValue(255)
    palette = gdal.ColorTable()
    for value, rgba in _SBS_4CLASS_EXPORT_COLORS.items():
        palette.SetColorEntry(value, rgba)
    target_band.SetRasterColorTable(palette)
    target_band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    target_band.WriteArray(output)
    target.FlushCache()
    target_band = target = band = source = None
    return {'severity': severity, 'valid_pixels': int(mask.sum()),
            'shape': list(output.shape), 'identity': digest_file(destination),
            'origin': 'synthetic constant class on real Grizzly SBS footprint, projection and mask'}


def assert_control(path, severity):
    import numpy as np
    from osgeo import gdal

    dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f'Native child SBS cannot be read: {path}')
    values = dataset.ReadAsArray()
    unique = sorted(int(value) for value in np.unique(values[values != 255]))
    dataset = None
    if unique != [severity]:
        raise AssertionError(f'Child SBS class is {unique}, expected {severity}')
    return unique


def snapshot_child(child, evidence, project):
    """Retain all regular child artifacts; shared links are recorded, not followed."""
    evidence.mkdir()
    files, links = {}, {}
    for root, dirs, names in os.walk(child, followlinks=False):
        for name in list(dirs):
            path = Path(root) / name
            if path.is_symlink():
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(project):
                    raise RuntimeError(f'Child shared link escapes disposable project: {path}')
                links[str(path.relative_to(child))] = str(resolved)
                dirs.remove(name)
        for name in sorted(names):
            path = Path(root) / name
            relative = path.relative_to(child)
            if path.is_symlink():
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(project):
                    raise RuntimeError(f'Child file link escapes disposable project: {path}')
                links[str(relative)] = str(resolved)
                continue
            target = evidence / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            files[str(relative)] = copy_one(path, target, path.stat())
    result = {'files': files, 'shared_links': links,
              'shared_link_note': 'Links are recorded only; shared targets remain in the independent parent copy.'}
    write_json(evidence / 'snapshot-manifest.json', result)
    return result


def numerical_identity(child):
    selected = sorted((child / 'wepp/runs').glob('*.man'))
    selected += sorted((child / 'wepp/runs').glob('*.sol'))
    selected += sorted((child / 'wepp/runs').glob('*.run'))
    selected += sorted((child / 'wepp/output/interchange').glob('*.parquet'))
    return {str(path.relative_to(child)): digest_file(path) for path in selected}


def validate_generation(omni, definition, expected_sha, severity, expected_stems, expected_years):
    import pyarrow.parquet as pq
    from wepppy.nodb.mods.omni.omni import OMNI_REL_DIR, _scenario_name_from_scenario_definition
    from wepppy.nodb.mods.omni.omni_sbs_freshness import receipt_from_signature, child_source

    name = _scenario_name_from_scenario_definition(definition)
    child = Path(omni.wd) / OMNI_REL_DIR / 'scenarios' / name
    states = [item for item in omni.scenario_run_state if item['scenario'] == name]
    if len(states) != 1 or states[0]['status'] != 'executed':
        raise AssertionError(f'Expected actual execution state, got {states}')
    receipt = receipt_from_signature(omni.scenario_dependency_tree[name]['signature'])
    if receipt['sha256'] != expected_sha or receipt['source_path'] != definition['sbs_file_path']:
        raise AssertionError('Accepted association does not describe supplied upload')
    if Path(definition['sbs_file_path']).exists():
        raise AssertionError('Normal consumed-upload behavior did not occur')
    copied_sbs = child_source(omni, definition)
    if digest_file(copied_sbs)['sha256'] != expected_sha:
        raise AssertionError('Copied child main bytes do not match accepted receipt')
    classes = assert_control(copied_sbs, severity)
    generated = {}
    for extension in ('man', 'sol', 'run'):
        paths = {path.stem: path for path in (child / 'wepp/runs').glob(f'p*.{extension}')}
        if set(paths) != expected_stems:
            raise AssertionError(f'{extension} hillslope set differs from complete copied parent')
        if any(path.stat().st_size == 0 for path in paths.values()):
            raise AssertionError(f'Empty generated {extension} artifact')
        generated[extension] = len(paths)
    outputs = {}
    for filename in ('loss_pw0.out.parquet', 'loss_pw0.all_years.class_data.parquet',
                     'loss_pw0.hill.parquet'):
        path = child / 'wepp/output/interchange' / filename
        table = pq.read_table(path)
        if table.num_rows == 0:
            raise AssertionError(f'Native output has no rows: {filename}')
        outputs[filename] = {'rows': table.num_rows, 'columns': table.column_names,
                             'identity': digest_file(path)}
    if omni._year_set_for_scenario(name) != expected_years:
        raise AssertionError('Actual scenario output does not retain all baseline climate years')
    return child, {'scenario': name, 'state': states[0], 'receipt': receipt,
                   'generated_hillslope_files': generated, 'outputs': outputs,
                   'years': sorted(expected_years), 'native_child_classes': classes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='/wc1/runs/th/thespian-cleanness')
    parser.add_argument('--root', help='New /wc1/batch/qa-* evidence root; generated by default')
    parser.add_argument('--copy-manifest', help='Resume only the prepared independent baseline copy')
    parser.add_argument('--prepare-only', action='store_true', help='Copy only; do not import native owners or execute models')
    parser.add_argument('--ncpu', type=int, default=4, help='Existing WEPPPY_NCPU execution limit')
    args = parser.parse_args()
    if args.ncpu < 1:
        parser.error('--ncpu must be positive')
    repository = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repository))
    if args.copy_manifest:
        copy_manifest_path = Path(args.copy_manifest).absolute()
        copy_manifest = json.loads(copy_manifest_path.read_text())
        if copy_manifest['status'] != 'prepared':
            raise ValueError('Only a successfully prepared copy can start native acceptance')
        project = Path(copy_manifest['destination'])
        root = project.parent.parent
        if copy_manifest['run_group'] != 'batch' or project.parent.name != 'runs':
            raise ValueError('Omni runner requires its own disposable batch copy')
    else:
        root = Path(args.root or '/wc1/batch/qa-omni-native-' + uuid4().hex[:12]).absolute()
        if root.parent != Path('/wc1/batch') or not root.name.startswith('qa-') or root.exists():
            raise ValueError('Evidence root must be a new /wc1/batch/qa-* directory')
        root.mkdir(mode=0o750)
        project = root / 'runs' / (root.name + '-grizzly')
        copy_manifest_path = root / 'copy-manifest.json'
        copy_manifest = prepare_project_copy(args.source, project, copy_manifest_path)
    manifest_path = root / 'omni-native-manifest.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if previous.get('status') != 'prepared':
            raise ValueError('Do not overwrite a prior native attempt; create another independent copy')
    old_umask = os.umask(0)
    os.umask(old_umask)
    manifest = {'schema': 'freshness-omni-native/v1', 'root': str(root), 'project': str(project),
                'copy_manifest': str(copy_manifest_path), 'status': 'prepared',
                'identity': {'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
                             'umask': oct(old_umask)}, 'started_unix': time.time(), 'stages': [],
                'scope': 'Actual direct Omni native workflow; live HTTP/RQ remains a separate gate',
                'source': str(copy_manifest['source']), 'module_hashes': code_hashes(repository)}
    write_json(manifest_path, manifest)
    if args.prepare_only:
        print(json.dumps({'status': 'prepared', 'resume_copy_manifest': str(copy_manifest_path)}), flush=True)
        return
    os.environ['WEPPPY_NCPU'] = str(args.ncpu)
    logging.basicConfig(level=logging.INFO)
    try:
        if shutil.disk_usage(root).free < 15 * 1024**3:
            raise RuntimeError('Need 15 GiB free for complete native results and retained generations')
        manifest['source_preflight'] = verify_source(copy_manifest, hash_bytes=False)
        manifest['git_revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
        manifest['wepppy_ncpu'] = args.ncpu
        manifest['status'] = 'running'
        write_json(manifest_path, manifest)
        from osgeo import gdal
        from wepppy.nodb.mods.omni.omni import Omni, OmniScenario
        from wepppy.nodb.core import Wepp
        from wepppy.rq.project_rq import _reset_forked_run_job_markers
        from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths
        gdal.UseExceptions()
        if (project / 'omni.nodb').exists():
            raise ValueError('Baseline copy already has an Omni controller; retain it and start a fresh copy')
        if not project.name.startswith(root.name + '-'):
            raise ValueError('Prepared batch leaf is not unique for RedisPrep; rebase before owner hydration')
        if (project / '.redisprep-run-id').exists() or (project / '.redisprep-run-id').is_symlink():
            raise ValueError('Unexpected RedisPrep namespace override in disposable copy')
        # Same destination-only marker reset as canonical fork; never reconcile
        # inherited source job IDs as if they belonged to this copied identity.
        _reset_forked_run_job_markers(copy_manifest['runid'], str(project),
                                     copy_manifest['runid'] + ':fork')
        manifest['canonical_fork_job_markers_reset'] = True
        template = project / 'disturbed/GrizzlyCreek_SBS_final.tif'
        manifest['real_sbs_template'] = digest_file(template)
        model = Wepp.getInstance(str(project))
        manifest['wepp_binary'] = model.wepp_bin
        manifest['wepp_binary_identities'] = {str(path): digest_file(path)
                                             for path in get_linux_wepp_bin_role_paths(model.wepp_bin)}
        omni = Omni(str(project), 'config.cfg', run_group='batch', group_name=root.name)
        if omni.runid != copy_manifest['runid']:
            raise AssertionError('Actual NoDb owner identity differs from disposable copy')
        expected_stems = {path.stem for path in (project / 'wepp/runs').glob('p*.man')}
        expected_years = omni._year_set_for_scenario(str(omni.base_scenario))
        if not expected_stems or not expected_years:
            raise AssertionError('Full copied baseline lacks generated hillslopes/year lineage')
        manifest['baseline'] = {'hillslopes': len(expected_stems), 'years': sorted(expected_years)}
        upload = Path(omni.omni_dir) / '_limbo/0' / ('acceptance_sbs_' + root.name + '.tif')
        definition = {'type': 'sbs_map', 'sbs_file_path': str(upload)}
        omni.parse_scenarios([(OmniScenario.SBSmap, definition)])
        prior_identities = None
        prior_upload_times = None
        for generation, severity in enumerate((1, 3), 1):
            stage = {'generation': generation, 'severity': severity, 'status': 'preparing'}
            manifest['stages'].append(stage)
            write_json(manifest_path, manifest)
            stage['input'] = make_control(template, upload, severity)
            if prior_upload_times is None:
                info = upload.stat()
                prior_upload_times = (info.st_atime_ns, info.st_mtime_ns)
            else:
                os.utime(upload, ns=prior_upload_times)
                stage['restored_previous_upload_mtime_ns'] = prior_upload_times[1]
            supplied_sha = digest_file(upload)['sha256']
            input_copy = root / f'input-generation-{generation}.tif'
            copy_one(upload, input_copy, upload.stat())
            stage['status'] = 'executing'
            write_json(manifest_path, manifest)
            started = time.monotonic()
            omni.run_omni_scenarios()  # Normal direct owner; no scientific/native seams.
            stage['native_elapsed_seconds'] = time.monotonic() - started
            child, stage['actual'] = validate_generation(
                omni, definition, supplied_sha, severity, expected_stems, expected_years)
            current_identities = numerical_identity(child)
            stage['numerical_artifacts'] = current_identities
            if prior_identities is not None:
                changed = {extension: [name for name, value in current_identities.items()
                                       if name.endswith('.' + extension) and name in prior_identities
                                       and value['sha256'] != prior_identities[name]['sha256']]
                           for extension in ('man', 'sol')}
                if not all(changed.values()):
                    raise AssertionError(f'Same-name low/high change did not reach management and soil artifacts: {changed}')
                stage['changed_generated_files'] = changed
                output_key = 'wepp/output/interchange/loss_pw0.out.parquet'
                stage['watershed_output_changed'] = current_identities[output_key]['sha256'] != prior_identities[output_key]['sha256']
            stage['status'] = 'validating_consumed_skip'
            write_json(manifest_path, manifest)
            started = time.monotonic()
            omni.run_omni_scenarios()
            stage['consumed_skip_seconds'] = time.monotonic() - started
            states = [item for item in omni.scenario_run_state if item['scenario'] == stage['actual']['scenario']]
            if len(states) != 1 or states[0]['status'] != 'skipped':
                raise AssertionError(f'Consumed upload was not reused: {states}')
            if numerical_identity(child) != current_identities:
                raise AssertionError('Consumed-source skip rewrote generated numerical artifacts')
            stage['consumed_skip_state'] = states[0]
            retained = root / f'generation-{generation}'
            stage['retained_artifacts'] = str(retained)
            snapshot = snapshot_child(child, retained, project)
            stage['retained_regular_files'] = len(snapshot['files'])
            shutil.copy2(project / 'omni.nodb', retained / 'parent-omni.nodb')
            stage['status'] = 'passed'
            prior_identities = current_identities
            write_json(manifest_path, manifest)
        manifest['module_hashes_after'] = code_hashes(repository)
        if manifest['module_hashes_after'] != manifest['module_hashes']:
            raise AssertionError('Production source changed during actual native acceptance')
        manifest['source_after'] = verify_source(copy_manifest, hash_bytes=True)
        manifest.update(status='passed', finished_unix=time.time())
        write_json(manifest_path, manifest)
        print(json.dumps({'status': 'passed', 'root': str(root), 'manifest': str(manifest_path)}), flush=True)
    except BaseException as exc:  # Acceptance boundary: retain all partial native work and traceback.
        manifest.update(status='failed', error_type=type(exc).__name__, error=str(exc),
                        traceback=traceback.format_exc(), finished_unix=time.time())
        write_json(manifest_path, manifest)
        try:
            manifest['source_after_failure'] = verify_source(copy_manifest, hash_bytes=False)
        except (OSError, RuntimeError, ValueError) as verification_error:
            manifest['source_after_failure_error'] = str(verification_error)
        write_json(manifest_path, manifest)
        raise


if __name__ == '__main__':
    main()
