"""Compose explicit prepared M1 artifacts locally; no controller or run publication.

Contract: docs/m1_predictors.md; parameterization: ADR-0059.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import collections.abc

import numpy as np
import rasterio  # type: ignore[import-untyped]

from .dnbr import summarize_dnbr
from .staley2017 import probability
from .m1_inputs import (M1Error, align_sbs, companions, digest, fail, prepare,
                        read_json, read_raster, regular, write_json)

__all__ = ['M1Error', 'M1Inputs', 'build_m1_predictors', 'evaluate_m1_scenarios']


@dataclass(frozen=True)
class M1Inputs:
    dem: Path
    mask: Path
    outlet: Path
    sbs: Path
    expected_sha256: collections.abc.Mapping[str, str]
    wbt_sha256: str
    source_kind: str
    k: Path | None = None
    k_manifest: Path | None = None
    dnbr: Path | None = None
    dnbr_manifest: Path | None = None
    lineage_sources: tuple[Path, ...] = ()
    elevation_units: str = 'm'
    sbs_alignment: str = 'exact'


def _sources(inputs):
    paths = [inputs.dem, inputs.mask, inputs.outlet, inputs.sbs, inputs.k,
             inputs.k_manifest, inputs.dnbr, inputs.dnbr_manifest, *inputs.lineage_sources]
    expected = {str(Path(p).absolute()): h for p, h in inputs.expected_sha256.items()}
    files = set()
    for path in paths:
        if path is None:
            continue
        p = regular(path)
        files.add(p)
        if p.suffix.lower() in ('.tif', '.tiff'):
            files.update(companions(p))
    hashes = {}
    for p in sorted(files):
        if str(p) not in expected:
            fail('missing_provenance', f'Missing expected SHA-256: {p}')
        actual = digest(p)
        if actual != expected[str(p)]:
            fail('provenance_mismatch', f'Source SHA-256 mismatch: {p}')
        hashes[str(p)] = actual
    return hashes


def _support(valid, domain):
    total = int(domain.sum())
    count = int(np.count_nonzero(valid & domain))
    return {'total_cells': total, 'valid_cells': count, 'coverage_fraction': count / total}


def _record(value, units, reason, support, **extra):
    return {'value': value, 'units': units,
            'status': 'available' if value is not None else 'unavailable',
            'reason': reason, 'support': support, **extra}


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _k_predictor(inputs, grid, domain):
    empty = _support(np.zeros(domain.shape, dtype=bool), domain)
    if inputs.k is None:
        return _record(None, 'USLE_customary', 'missing_input', empty), None
    if Path(inputs.k).name != 'k_polaris_nomograph.tif':
        fail('provenance_mismatch', 'K must be the named Nomograph artifact')
    values, finite, source_grid = read_raster(inputs.k, continuous_missing=True)
    if source_grid != grid:
        fail('invalid_grid', 'K grid must match raw DEM exactly')
    valid = finite & (values >= 0) & (values <= 1)
    support = _support(valid, domain)
    mean = float(np.mean(values[valid & domain], dtype=np.float64)) if support['valid_cells'] else None
    invalid = int(np.count_nonzero(domain & finite & ~valid))
    reason = None if support['valid_cells'] == support['total_cells'] else 'incomplete_k_coverage'
    provenance = None
    if inputs.k_manifest is None:
        reason = 'missing_provenance'
    else:
        manifest = read_json(inputs.k_manifest)
        provenance = manifest.get('k')
        if provenance is None:
            reason = 'missing_provenance'
        elif not isinstance(provenance, dict):
            fail('provenance_mismatch', 'K section must be an object')
        else:
            modes = provenance.get('selected_modes')
            artifacts = provenance.get('artifacts')
            if 'selected_modes' in provenance and (not isinstance(modes, list) or 'polaris_nomograph' not in modes):
                fail('provenance_mismatch', 'K provenance does not select Nomograph')
            if 'artifacts' in provenance:
                if not isinstance(artifacts, dict):
                    fail('provenance_mismatch', 'K artifacts must be an object')
                named = artifacts.get('nomograph')
                if named is not None and named != 'rusle/k_polaris_nomograph.tif':
                    fail('provenance_mismatch', 'K provenance names another artifact')
            required = {'selected_modes', 'artifacts', 'statistic', 'near_surface_depths',
                        'near_surface_weights_cm', 'mode_contract', 'gap_fill_policy', 'gap_fill_summary'}
            if not required <= provenance.keys() or not isinstance(artifacts, dict) or not artifacts.get('nomograph'):
                reason = 'missing_provenance'
            else:
                if (provenance['statistic'] != 'mean' or provenance['near_surface_depths'] != ['0_5', '5_15']
                        or provenance['near_surface_weights_cm'] != {'0_5': 5.0, '5_15': 10.0}):
                    fail('provenance_mismatch', 'K statistic/depth weighting differs from selected contract')
                for key in ('mode_contract', 'gap_fill_policy', 'gap_fill_summary'):
                    if not isinstance(provenance[key], dict):
                        fail('provenance_mismatch', f'K {key} must be an object')
                    if not provenance[key]:
                        reason = 'missing_provenance'
                mode = provenance['mode_contract'].get('polaris_nomograph')
                if mode is None:
                    reason = 'missing_provenance'
                elif not isinstance(mode, dict):
                    fail('provenance_mismatch', 'Nomograph mode contract must be an object')
                else:
                    mappings = {'vfs_source': 'rusle2_estimated_from_sand',
                                'structure_class_mapping': 'modeled_texture_proxy_v1',
                                'permeability_class_mapping': 'modeled_ksat_proxy_v1'}
                    for key, expected in mappings.items():
                        if key not in mode:
                            reason = 'missing_provenance'
                        elif mode[key] != expected:
                            fail('provenance_mismatch', f'Unsupported K mapping: {key}')
                    if 'cfvo_profile_fragment_adjustment' not in mode:
                        reason = 'missing_provenance'
                    elif not isinstance(mode['cfvo_profile_fragment_adjustment'], dict):
                        fail('provenance_mismatch', 'K fragment provenance must be an object')
                    elif not isinstance(mode['cfvo_profile_fragment_adjustment'].get('status'), str) or not mode['cfvo_profile_fragment_adjustment']['status']:
                        fail('provenance_mismatch', 'K fragment provenance requires status')
    return _record(mean if reason is None else None, 'USLE_customary', reason, support,
                   observed_mean=mean, invalid_cells=invalid, multiplier=1.0), provenance


def _f_predictor(inputs, grid, domain, binary_mask, hashes):
    empty = _support(np.zeros(domain.shape, dtype=bool), domain)
    if inputs.dnbr is None:
        return _record(None, 'normalized_dNBR', 'missing_input', empty)
    values, valid, source_grid = read_raster(inputs.dnbr, continuous_missing=True)
    if source_grid != grid:
        fail('invalid_grid', 'Normalized dNBR grid must match raw DEM exactly')
    support = _support(valid, domain)
    # Existing helper has its own self-contained input boundary and compiled mean.
    prepared_dnbr = binary_mask.parent / 'dnbr.tif'
    prepare(prepared_dnbr, values, valid, grid)
    summary = summarize_dnbr(prepared_dnbr, binary_mask)
    reason = 'empty_dnbr' if not support['valid_cells'] else None
    if inputs.dnbr_manifest is None:
        reason = 'missing_provenance'
    else:
        m = read_json(inputs.dnbr_manifest)
        required = {'schema_version', 'dnbr_sha256', 'target_grid', 'scale_factor', 'add_offset', 'input_sha256'}
        if not required <= m.keys():
            reason = 'missing_provenance'
        else:
            if (m['schema_version'] != 1 or m['dnbr_sha256'] != hashes[str(Path(inputs.dnbr).absolute())]
                    or m['target_grid'] != grid or not _number(m['scale_factor']) or m['scale_factor'] <= 0
                    or not _number(m['add_offset']) or not isinstance(m['input_sha256'], dict)):
                fail('provenance_mismatch', 'Invalid or mismatched normalization provenance')
            lineage = m['input_sha256']
            if not lineage:
                reason = 'missing_provenance'
            for path, expected in lineage.items():
                if path not in hashes:
                    reason = 'missing_provenance'
                elif hashes[path] != expected:
                    fail('provenance_mismatch', 'dNBR source lineage mismatch')
    return _record(summary['m1_f'] if reason is None else None, 'normalized_dNBR', reason,
                   support, observed_mean=summary['mean_dnbr'], warning=summary['warning'])


def _run(command, output, label):
    with (output / f'{label}.stdout.log').open('xb') as stdout, (output / f'{label}.stderr.log').open('xb') as stderr:
        try:
            result = subprocess.run(command, cwd=output, stdout=stdout, stderr=stderr, timeout=300, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise M1Error('tool_failed', f'WBT invocation failed: {label}') from exc
    if result.returncode:
        fail('tool_failed', f'WBT returned {result.returncode}; inspect {label} logs')


def _invoke(binary, output, prepared):
    capability = [str(binary), '--toolparameters=StaleySlopeSbs']
    _run(capability, output, 'capability')
    parameters = read_json(output / 'capability.stdout.log').get('parameters')
    if not isinstance(parameters, list) or not any(isinstance(p, dict) and '--sbs_classes' in p.get('flags', []) for p in parameters):
        fail('tool_unavailable', 'Executable lacks StaleySlopeSbs capability')
    destination = output / 'wbt'
    command = [str(binary), '-r=StaleySlopeSbs', f'--dem={prepared / "dem.tif"}',
               f'--mask={prepared / "mask.tif"}', f'--sbs={prepared / "sbs.tif"}',
               f'--output_dir={destination}', '--elevation_units=m', '--sbs_classes=0,1,2,3']
    _run(command, output, 'wbt')
    return command


def _tool_result(output, grid, domain):
    directory = output / 'wbt'
    try:
        summary = read_json(directory / 'summary.json')
        if summary.get('status') != 'complete' or summary.get('schema_version') != 1 or summary.get('tool') != 'StaleySlopeSbs':
            fail('invalid_tool_output', 'Incomplete or unrecognized WBT summary')
        expected_parameters = {'algorithm': 'Horn 3x3', 'dem_source': 'raw', 'edges': 'nine-valid-cells',
                               'threshold_degrees': 23, 'elevation_units': 'm', 'sbs_classes': [0, 1, 2, 3]}
        expected_grid = {'epsg': rasterio.crs.CRS.from_user_input(grid['crs']).to_epsg(),
                         'rows': grid['shape'][0], 'columns': grid['shape'][1],
                         'resolution_m': grid['transform'][0], 'west': grid['transform'][2], 'north': grid['transform'][5]}
        if summary.get('parameters') != expected_parameters or summary.get('grid') != expected_grid or not isinstance(summary.get('tool_version'), str):
            fail('invalid_tool_output', 'WBT parameters, grid or version mismatch')
        counts = summary['counts']
        n = int(domain.sum())
        y, u, f = (counts[k] for k in ('intersection_true', 'intersection_unknown', 'intersection_false'))
        if (any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= n for v in counts.values())
                or counts['basin'] != n or y + u + f != n or summary['T_lower'] != y/n
                or summary['T_upper'] != (y+u)/n or summary['T'] != (None if u else y/n)):
            fail('invalid_tool_output', 'Inconsistent WBT counts or bounds')
        products = {}
        for name in ('slope', 'intersection', 'support'):
            with rasterio.open(directory / f'{name}.tif') as ds:
                if ds.count != 1 or list(ds.shape) != grid['shape'] or str(ds.crs) != grid['crs'] or list(ds.transform)[:6] != grid['transform']:
                    fail('invalid_tool_output', 'WBT output grid mismatch')
                a = ds.read(1, masked=True)
                products[name] = a
                if name == 'slope' and (not np.isfinite(a.compressed()).all() or np.any((a.compressed() < 0) | (a.compressed() > 90))):
                    fail('invalid_tool_output', 'Invalid WBT slope values')
                if name != 'slope':
                    if not np.array_equal(~np.ma.getmaskarray(a), domain):
                        fail('invalid_tool_output', 'WBT output support mismatch')
                    allowed = [0, 1, 2] if name == 'intersection' else [0, 1, 2, 3]
                    if not np.isin(a.data[domain], allowed).all():
                        fail('invalid_tool_output', 'WBT output contains invalid codes')
                    if name == 'intersection' and [int(np.count_nonzero(a.data[domain] == k)) for k in (0, 1, 2)] != [f, y, u]:
                        fail('invalid_tool_output', 'WBT intersection counts mismatch')
        support = products['support'].data
        slope_valid = ~np.ma.getmaskarray(products['slope'])
        if not np.array_equal((support[domain] & 1) != 0, slope_valid[domain]):
            fail('invalid_tool_output', 'Slope support disagrees with support bits')
        for key, bits in (('slope_valid', 1), ('sbs_valid', 2), ('jointly_valid', 3)):
            if counts[key] != int(np.count_nonzero((support[domain] & bits) == bits)):
                fail('invalid_tool_output', 'Support bit counts disagree with summary')
        sbs, sbs_valid, _ = read_raster(output / 'prepared/sbs.tif', categorical=True)
        if not np.array_equal((support[domain] & 2) != 0, sbs_valid[domain]):
            fail('invalid_tool_output', 'SBS support disagrees with prepared input')
        for code, key in enumerate(('sbs_unburned', 'sbs_low', 'sbs_moderate', 'sbs_high')):
            if counts[key] != int(np.count_nonzero(domain & sbs_valid & (sbs == code))):
                fail('invalid_tool_output', 'SBS class counts disagree with prepared input')
        if not y <= counts['steep'] <= counts['slope_valid']:
            fail('invalid_tool_output', 'Inconsistent steep count')
        if any(summary['areas_m2'][key] != value * grid['transform'][0] ** 2 for key, value in counts.items()):
            fail('invalid_tool_output', 'Inconsistent WBT areas')
        return summary
    except (M1Error, KeyError, TypeError, OSError, rasterio.errors.RasterioError) as exc:
        raise M1Error('invalid_tool_output', 'Missing or malformed WBT products') from exc


def build_m1_predictors(inputs: M1Inputs, output_dir, *, wbt_executable) -> dict:
    """Build a new local bundle; failed reservations remain visibly incomplete."""
    if inputs.source_kind not in ('real', 'synthetic', 'mixed') or inputs.elevation_units != 'm' or inputs.sbs_alignment not in ('exact', 'nearest'):
        fail('invalid_input', 'Explicit source kind, meter elevations and supported alignment required')
    output = Path(output_dir).absolute()
    if output.exists() or output.is_symlink():
        fail('output_exists', 'Output already exists; retry in a fresh directory')
    hashes = _sources(inputs)
    binary = Path(wbt_executable).absolute()
    if binary.is_symlink() or not binary.is_file():
        fail('tool_unavailable', 'Expected an explicit regular WBT executable')
    if digest(binary) != inputs.wbt_sha256:
        fail('provenance_mismatch', 'WBT executable hash mismatch')
    dem, dem_valid, grid = read_raster(inputs.dem, target_grid=True)
    mask, mask_valid, mask_grid = read_raster(inputs.mask, target_grid=True)
    if mask_grid != grid:
        fail('invalid_grid', 'Mask grid must match DEM exactly')
    domain = mask_valid & (mask > 0)
    if not domain.any():
        fail('invalid_input', 'Empty watershed')
    sbs, sbs_valid, sbs_grid = read_raster(inputs.sbs, categorical=True)
    if not np.isin(sbs[sbs_valid], [0, 1, 2, 3]).all():
        fail('invalid_sbs', 'SBS must contain normalized classes 0–3')
    if sbs_grid != grid:
        if inputs.sbs_alignment != 'nearest':
            fail('invalid_grid', 'SBS alignment requires explicit nearest opt-in')
        sbs, sbs_valid = align_sbs(sbs, sbs_valid, sbs_grid, grid)
    outlet = read_json(inputs.outlet)
    feature = outlet
    if outlet.get('type') == 'FeatureCollection':
        features = outlet.get('features')
        if not isinstance(features, list) or len(features) != 1 or not isinstance(features[0], dict):
            fail('invalid_input', 'Expected exactly one existing outlet feature')
        feature = features[0]
    geometry = feature.get('geometry') if feature.get('type') == 'Feature' else feature
    if (not isinstance(geometry, dict) or geometry.get('type') != 'Point'
            or not isinstance(geometry.get('coordinates'), list) or len(geometry['coordinates']) != 2
            or not all(_number(v) for v in geometry['coordinates'])):
        fail('invalid_input', 'Expected resolved finite Point outlet')
    try:
        output.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise M1Error('output_exists', 'Output reserved concurrently') from exc
    write_json(output / 'incomplete.json', {'status': 'incomplete', 'retry': 'Use a fresh output directory'})
    prepared = output / 'prepared'
    prepared.mkdir(mode=0o700)
    prepare(prepared / 'dem.tif', dem, dem_valid, grid)
    prepare(prepared / 'mask.tif', mask, mask_valid, grid)
    prepare(prepared / 'sbs.tif', sbs, sbs_valid, grid, sbs=True)
    prepare(prepared / 'domain.tif', domain.astype(float), np.ones(domain.shape, dtype=bool), grid)
    command = _invoke(binary, output, prepared)
    summary = _tool_result(output, grid, domain)
    t = _record(summary['T'], 'fraction', None if summary['T'] is not None else 'unknown_intersection',
                {'total_cells': int(domain.sum()), 'valid_cells': int(domain.sum()) - summary['counts']['intersection_unknown'],
                 'coverage_fraction': 1 - summary['counts']['intersection_unknown'] / int(domain.sum())},
                lower=summary['T_lower'], upper=summary['T_upper'], wbt_summary=summary)
    f = _f_predictor(inputs, grid, domain, prepared / 'domain.tif', hashes)
    s, k_provenance = _k_predictor(inputs, grid, domain)
    points = {'T': t, 'F': f, 'S': s}
    count = sum(p['value'] is not None for p in points.values())
    area = int(domain.sum()) * grid['transform'][0] ** 2 / 1e6
    warnings = [] if .2 <= area <= 8 else ['area_outside_study_range']
    if f.get('warning'):
        warnings.append(f['warning'])
    manifest = {'schema_version': 1, 'status': 'complete',
                'availability': 'complete' if count == 3 else 'partial' if count else 'unavailable',
                'source_kind': inputs.source_kind, 'readiness': {'wepp_soils': 'not_checked_local', 'upstream_freshness': 'not_checked_local'},
                'grid': grid, 'outlet': outlet, 'area_km2': area, 'warnings': warnings,
                'predictors': points, 'sources_sha256': hashes, 'k_provenance': k_provenance,
                'preparation': {'sbs_alignment': inputs.sbs_alignment, 'source_sbs_grid': sbs_grid, 'domain': 'positive valid mask cells'},
                'tool': {'path': str(binary), 'sha256': inputs.wbt_sha256, 'version': summary['tool_version'], 'command': command},
                'prepared_sha256': {p.name: digest(p) for p in sorted(prepared.iterdir())},
                'artifacts_sha256': {str(p.relative_to(output)): digest(p) for p in sorted((output / 'wbt').iterdir())}}
    try:
        current = _sources(inputs)
        if current != hashes or digest(binary) != inputs.wbt_sha256:
            fail('source_changed', 'Source set or executable changed during build')
    except (M1Error, OSError) as exc:
        raise M1Error('source_changed', 'Source files, companions or executable changed during build') from exc
    write_json(output / 'manifest.json', manifest)
    (output / 'incomplete.json').unlink()
    return manifest


def evaluate_m1_scenarios(bundle: dict, scenarios) -> list[dict]:
    """Evaluate explicit accumulation scenarios, preserving unavailable predictors."""
    points = {key: bundle['predictors'][key]['value'] for key in ('T', 'F', 'S')}
    available = all(v is not None for v in points.values())
    results = []
    for duration, rainfall in scenarios:
        # Validate scenario even when unavailable inputs prevent evaluation.
        validation_predictors: dict = {'T': 0, 'F': 0, 'S': 0}
        probability('M1', duration, **validation_predictors, rainfall_mm=rainfall)
        value = probability('M1', duration, **points, rainfall_mm=rainfall) if available else None
        results.append({'duration_minutes': duration, 'rainfall_mm': rainfall, 'probability': value,
                        'reason': None if available else 'missing_predictors',
                        'warnings': bundle['warnings'], 'source_kind': bundle['source_kind']})
    return results
