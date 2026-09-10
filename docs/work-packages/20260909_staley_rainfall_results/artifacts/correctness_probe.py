"""Direct-file regression probes for the independent initial correctness review."""
import json
from pathlib import Path
import shutil
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.nodb.mods.postfire_debris_flow import rainfall
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow import results


def main():
    here = Path(__file__).resolve().parent
    predecessor = here.parents[1] / '20260909_staley_m1_predictors/artifacts/generated/wallow-rebuilt-final/bundle'
    findings = {}
    with tempfile.TemporaryDirectory(prefix='rainfall-correctness-') as temporary:
        root = Path(temporary)
        source = root / 'predictors'
        (source / 'wbt').mkdir(parents=True)
        for name in io.ARTIFACTS:
            shutil.copyfile(predecessor / name, source / name)
        original = json.loads((predecessor / 'manifest.json').read_text())
        manifest_path = source / 'manifest.json'
        for label, mutate in (
            ('missing_k_provenance', lambda m: m.update(k_provenance=None)),
            ('wrong_k_multiplier', lambda m: m['predictors']['S'].update(multiplier=100)),
            ('contradictory_f_observed_mean', lambda m: m['predictors']['F'].update(observed_mean=-123.)),
            ('empty_grid_outlet', lambda m: m.update(grid={}, outlet={})),
            ('inconsistent_t_support', lambda m: [p['support'].update(total_cells=1, valid_cells=1)
                                                for p in m['predictors'].values()]),
            ('missing_wbt_summary', lambda m: m['predictors']['T'].pop('wbt_summary')),
        ):
            m = json.loads(json.dumps(original))
            mutate(m)
            manifest_path.write_text(json.dumps(m))
            try:
                io.load_predictors(manifest_path, {str(manifest_path): io.digest(manifest_path)}, {})
            except io.RainfallError as exc:
                findings[label] = {'accepted': False, 'code': exc.code}
            except (KeyError, AttributeError) as exc:
                findings[label] = {'accepted': False, 'unexpected_exception': type(exc).__name__}
            else:
                findings[label] = {'accepted': True}

        manifest_path.write_text(json.dumps(original))
        climate = root / 'climate.parquet'
        pq.write_table(pa.table({'prcp': [1.], 'year': [1], 'peak_intensity_15': [40.]}), climate)
        inputs = rainfall.RainfallInputs(manifest_path, climate,
            {str(p): io.digest(p) for p in (manifest_path, climate)},
            'controlled-probe', 'cligen', 'simulation_labels', 'controlled-probe')
        output = root / 'results'
        results.build_m1_results(inputs, output, frequency_source='noaa',
            return_intervals=[1], durations=[15], target_probabilities=[.5])
        result_manifest = output / 'manifest.json'
        events = output / 'events.parquet'
        pristine_manifest = result_manifest.read_text()
        pristine_rows = pq.read_table(events).to_pylist()
        for label, mutate in (
            ('missing_result_identity', lambda m, rows: m.update(identity={})),
            ('wrong_result_units', lambda m, rows: m['units'].update(rainfall_mm='inches')),
            ('out_of_range_probability', lambda m, rows: rows[0].update(probability=42.)),
            ('wrong_scalar_probability', lambda m, rows: rows[0].update(probability=.123456789)),
            ('duplicate_event_duration', lambda m, rows: rows.append(dict(rows[0]))),
            ('incorrect_event_date_status', lambda m, rows: rows[0].update(date_status='simulation_labels', month=13.)),
            ('unavailable_reason_with_rainfall', lambda m, rows: rows[0].update(status='unavailable', reason='missing_duration', probability=None)),
        ):
            m = json.loads(pristine_manifest)
            rows = json.loads(json.dumps(pristine_rows))
            mutate(m, rows)
            pq.write_table(pa.Table.from_pylist(rows, schema=results.SCHEMAS['events']), events)
            m['tables']['events'] = {'sha256': io.digest(events), 'rows': len(rows)}
            result_manifest.write_text(json.dumps(m))
            try:
                catalog = results.open_results(output, expected_manifest_sha256=io.digest(result_manifest))
                page = results.list_events(catalog, duration_minutes=15)
            except io.RainfallError as exc:
                findings[label] = {'accepted': False, 'code': exc.code}
            else:
                findings[label] = {'accepted': True, 'returned_probability': page['rows'][0]['probability']}

        csv_path = root / 'noaa.csv'
        genuine = (here / 'sources/atlas14_intensity_pds_mean_metric.csv').read_text()
        csv_path.write_text(genuine.replace('Data type: Precipitation intensity',
            'Data type: Precipitation depth').replace('PRECIPITATION FREQUENCY ESTIMATES',
            'UPPER CONFIDENCE BOUND'))
        try:
            parsed = rainfall.frequency_csv(csv_path, {str(csv_path): io.digest(csv_path)}, {}, source='noaa')
        except io.RainfallError as exc:
            findings['contradictory_noaa_type'] = {'accepted': False, 'code': exc.code}
        else:
            findings['contradictory_noaa_type'] = {'accepted': True,
                'rainfall_mm': rainfall.noaa_design(parsed, (1,), (15,))[0]['rainfall_mm']}
        nonfinite_climate = root / 'nonfinite.parquet'
        pq.write_table(pa.table({'prcp': [1., 1.], 'year': [1, 2],
                                'peak_intensity_15': [float('inf'), 40.]}), nonfinite_climate)
        nonfinite_inputs = rainfall.RainfallInputs(manifest_path, nonfinite_climate,
            {str(nonfinite_climate): io.digest(nonfinite_climate)},
            'controlled-probe', 'cligen', 'simulation_labels', 'controlled-probe')
        _, df, info = rainfall.climate_events(nonfinite_inputs, (15,), {})
        try:
            rows = rainfall.cli_design(df, (1,), (15,), info)
        except io.RainfallError as exc:
            findings['nonfinite_cli_support'] = {'accepted': False, 'code': exc.code}
        else:
            findings['nonfinite_cli_support'] = {'accepted': rows[0]['status'] == 'available',
                'rank_index': rows[0]['rank_index'], 'positive_samples': rows[0]['positive_samples']}

        sparse_climate = root / 'sparse.parquet'
        pq.write_table(pa.table({'prcp': [1.] * 10, 'year': list(range(1, 11)),
            'peak_intensity_15': [100.] + [0.] * 9,
            'peak_intensity_30': list(range(100, 90, -1)),
            'peak_intensity_60': [0.] * 10}), sparse_climate)
        sparse_csv = root / 'sparse.csv'
        sparse_csv.write_text('\n'.join([
            'Point precipitation frequency estimates (mm, hours, mm/hour)',
            'WEPP CLI derived precipitation frequency statistics',
            'Data type: Precipitation depth, storm duration, peak intensities',
            'Time series type: Partial duration', 'Latitude: 33 Degree', 'Longitude: -109 Degree',
            '', 'PRECIPITATION FREQUENCY ESTIMATES', 'by metric for ARI (years):, 1,2,5,10',
            '15-min intensity (mm/hour):, 100,100,100,100',
            '30-min intensity (mm/hour):, 91,96,99,100',
            '60-min intensity (mm/hour):, 0,0,0,0', '']))
        sparse_inputs = rainfall.RainfallInputs(manifest_path, sparse_climate,
            {str(p): io.digest(p) for p in (manifest_path, sparse_climate, sparse_csv)},
            'controlled-probe', 'cligen', 'simulation_labels', 'controlled-probe',
            cli_frequency_csv=sparse_csv)
        sparse_output = root / 'sparse-results'
        sparse_manifest = results.build_m1_results(sparse_inputs, sparse_output,
            frequency_source='cli', return_intervals=[1, 2, 5, 10],
            durations=[15, 30, 60], target_probabilities=[.5])
        sparse_manifest_path = sparse_output / 'manifest.json'
        sparse_catalog = results.open_results(sparse_output,
            expected_manifest_sha256=io.digest(sparse_manifest_path))
        design_path = sparse_output / 'design.parquet'
        design_rows = pq.read_table(design_path).to_pylist()
        unsupported = [r for r in design_rows if r['reason'] == 'insufficient_positive_samples']
        assert [r['rank_index'] for r in unsupported] == [9, 4, 1]
        assert all(r['positive_samples'] == 1 for r in unsupported)
        assert all(r[k] is None for r in unsupported
                   for k in ('intensity_mm_per_hour', 'rainfall_mm', 'probability'))
        supported = [r for r in design_rows if r['duration_minutes'] == 30]
        assert [r['rainfall_mm'] for r in supported] == [45.5, 48., 49.5, 50.]
        assert all(r['status'] == 'available' for r in supported)
        assert [r['reason'] for r in design_rows if r['duration_minutes'] == 60] == ['no_positive_samples'] * 4
        assert design_rows[-3]['rainfall_mm'] == 25.
        assert results.list_events(sparse_catalog, duration_minutes=15)['total'] == 10
        findings['approved_sparse_cli_roundtrip'] = {'unavailable_ranks': [9, 4, 1],
            'positive_samples': 1, 'supported_other_duration_rainfall_mm': [45.5, 48., 49.5, 50.],
            'event_rows': sparse_manifest['tables']['events']['rows'],
            'design_rows': sparse_manifest['tables']['design']['rows'],
            'inverse_rows': sparse_manifest['tables']['inverse']['rows'],
            'csv_clamped_parity': True}
        pristine_sparse_manifest = sparse_manifest_path.read_text()
        for label, change in (
            ('insufficient_reason_with_supported_rank', lambda row: row.update(rank_index=0)),
            ('insufficient_reason_with_zero_samples', lambda row: row.update(positive_samples=0)),
            ('available_cli_rainfall_without_rank_support', lambda row: row.update(
                **{k: design_rows[-3][k] for k in
                   ('intensity_mm_per_hour', 'rainfall_mm', 'probability', 'status', 'reason')})),
        ):
            changed_rows = json.loads(json.dumps(design_rows))
            change(changed_rows[0])
            pq.write_table(pa.Table.from_pylist(changed_rows, schema=results.SCHEMAS['design']), design_path)
            m = json.loads(pristine_sparse_manifest)
            m['tables']['design']['sha256'] = io.digest(design_path)
            sparse_manifest_path.write_text(json.dumps(m))
            try:
                results.open_results(sparse_output, expected_manifest_sha256=io.digest(sparse_manifest_path))
            except io.RainfallError as exc:
                findings[label] = {'accepted': False, 'code': exc.code}
            else:
                findings[label] = {'accepted': True}

        inventory = json.loads((here / 'source_inventory.json').read_text())
        cli = here / 'sources/wepp_cli.parquet'
        cli_csv = here / 'sources/wepp_cli_pds_mean_metric.csv'
        pins = {str(here / 'sources' / Path(key).name): data['sha256']
                for key, data in inventory['sources'].items()}
        real_inputs = rainfall.RainfallInputs(manifest_path, cli, pins,
            'woolen-refusal', 'cligen', 'simulation_labels', 'Wallow evidence')
        _, df, info = rainfall.climate_events(real_inputs, (15, 30, 60), {})
        parsed = rainfall.frequency_csv(cli_csv, pins, {}, source='cli')
        rows = rainfall.cli_design(df, (1, 2, 5, 10), (15, 30, 60), info, parsed)
        assert len(rows) == 12 and all(row['status'] == 'available' for row in rows)
        findings['genuine_cli_parity'] = {'available_design_rows': len(rows),
            'full_recurrence_context': info['recurrence_context'], 'first_design': rows[0]}
    print(json.dumps(findings, indent=2))


if __name__ == '__main__':
    main()
