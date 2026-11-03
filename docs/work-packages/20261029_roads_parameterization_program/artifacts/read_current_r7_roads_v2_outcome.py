"""Independent read-only Roads outcome audit; no native calls or converters."""
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
import math
import re

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from audit_pass_completeness_r7 import daily_records
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
from wepppy.wepp.interchange.roads_accounting import accounting_source, load
from wepppy.wepp.interchange.watershed_loss import AVERAGE_FILENAMES, Loss
from wepppy.wepp.reports.total_watbal import TotalWatbalReport

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/current-roads-v2')
ART = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def inventory(root, folders):
    return {str(path.relative_to(root)): sha(path)
            for folder in folders for path in sorted((root / folder).rglob('*'))
            if path.is_file()}


def main():
    declaration = read(ROOT / 'declaration.json')
    assert sha(ROOT / 'declaration.json') == 'd66eb2edd76242fce7515ff9179c089180b37fb4977b2cfd30153b10bddd4196'
    assert read(ROOT / 'execution-start.json')['declaration_sha256'] == sha(ROOT / 'declaration.json')
    rows = read(ROOT / 'results.json')
    assert [row['case'] for row in rows] == declaration['cases'] and len(rows) == 5
    source = Path(declaration['source'])
    source_before = inventory(source, ('wepp', 'roads', 'climate', 'dem', 'watershed'))
    source_before.update({p.name: sha(p) for p in source.glob('*.nodb')})
    assert source_before == declaration['source_inventory']
    assert all(sha(name) == digest for name, digest in declaration['dependencies'].items())
    report = dict(declaration_sha256=sha(ROOT / 'declaration.json'),
                  results_sha256=sha(ROOT / 'results.json'), script_sha256=sha(__file__),
                  source_files_verified=len(source_before), dependencies_verified=len(declaration['dependencies']),
                  scope='Read-only bounded controller outcome; no native or converter invocation', cases={})
    expected = {date(2000, 1, 1) + timedelta(days=i) for i in range(5844)}
    expected_tokens = {(day.year, day.timetuple().tm_yday) for day in expected}
    source_upload = read(source / 'roads/roads.uploaded.geojson')
    assert len(source_upload['features']) == 55
    for row in rows:
        case, evidence = row['case'], row['evidence']
        root = ROOT / case['name']
        assert read(ROOT / (case['name'] + '-receipt.json')) == row
        protected = read(root / 'validation-baseline-before.json')
        assert len(protected) == 907
        assert inventory(root, ('wepp/runs', 'wepp/output')) == protected
        assert all(source_before[name] == digest for name, digest in protected.items())
        original = read(root / 'validation-source-before.json')
        assert all(source_before[name] == digest for name, digest in original.items())
        before = inventory(root, ('wepp/roads',))
        selection = read(root / 'validation-selection.json')
        upload = read(root / 'validation-input.geojson')
        expected_upload = json.loads(json.dumps(source_upload))
        if case['exclude_infeasible_unrutted']:
            excluded = [f for f in expected_upload['features'] if str(f['properties'].get('OSUNUM')) == '6']
            assert len(excluded) == 1
            identity = hashlib.sha256(json.dumps(excluded[0], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            assert identity == 'b30f47d5562e899813769eb37c84be30f9a242d429c8aa6f87c534d791902b22'
            expected_upload['features'] = [f for f in expected_upload['features'] if str(f['properties'].get('OSUNUM')) != '6']
        for feature in expected_upload['features']:
            feature['properties']['DESIGN'] = case['design']
            if case['design'] == 'outslope_unrutted':
                feature['properties'].update(FILL_LENGTH_M=30., FILL_SLOPE_PCT=10., BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.)
        assert upload == expected_upload and len(upload['features']) == selection['input_features']
        item = dict(protected_baseline_files=907, unchanged_source_subset=len(original),
                    source_upload_features=55, input_features=len(upload['features']),
                    before_manifest_sha256=sha(root / 'validation-baseline-before.json'),
                    receipt_sha256=sha(ROOT / (case['name'] + '-receipt.json')))
        if case['negative']:
            assert not lifecycle.available(root) and not (root / lifecycle.RECEIPT).exists()
            manifest = root / evidence['manifest_relpath']
            assert sha(manifest) == evidence['manifest_sha256']
            failed = [r for r in read(manifest) if r.get('status') == 'failed']
            assert failed == evidence['failed_records'] and len(failed) == 2
            assert {r['target_hillslope_topaz_id'] for r in failed} == {271, 272}
            assert all(r['reason'] == 'failed_non_positive_top_ofe' and r['segment_id'] == 'roads-seg-000001' for r in failed)
            assert len(upload['features']) == 55 and not selection['excluded']
            item.update(expected_negative=True, failed_records=failed, current_receipt_absent=True,
                        failed_manifest_sha256=sha(manifest))
        else:
            assert lifecycle.require_current(root) == evidence['receipt']
            runs, output = root / 'wepp/roads/runs', root / 'wepp/roads/output'
            tc = runs / 'tc_out.txt'
            assert tc.is_file() and not tc.is_symlink()
            assert not tc.samefile(root / 'wepp/runs/tc_out.txt')
            assert sha(root / 'wepp/runs/tc_out.txt') == protected['wepp/runs/tc_out.txt']
            assert all(sha(runs / name) == digest for name, digest in
                       ((Path(k).name, v) for k, v in evidence['prepared_inputs'].items()))
            manifest = read(root / 'wepp/roads/segments/roads.segment.pass.manifest.json')
            completed = [r for r in manifest if r.get('status') == 'completed']
            assert completed and not any(r.get('status') == 'failed' for r in manifest)
            ids = [r['segment_run_id'] for r in completed]
            assert len(ids) == len(set(ids))
            native = []
            for identifier in ids + ['w0']:
                trace = (runs / f'p{identifier}.err').read_text()
                watershed = identifier == 'w0'
                binary = 'wepp_261029' if watershed else 'wepp_261029_hill'
                role = 'WATERSHED' if watershed else 'HILLSLOPE'
                assert f'binary_sha256={declaration["binaries"][binary]}' in trace
                assert 'binary_identity_status=ok' in trace
                assert f'WEPP COMPLETED {role} SIMULATION SUCCESSFULLY' in trace
                assert list(map(int, re.findall(r'SIMULATION YEAR =\s*(\d+)', trace))) == list(range(1, 17))
                assert not re.search(r'attempt [2-9]/', trace)
                native.append(dict(id=identifier, binary=binary, trace_sha256=sha(runs / f'p{identifier}.err')))
                if not watershed:
                    path = output / f'H{identifier}.pass.dat'
                    lines = path.read_text().splitlines()
                    assert lines[0] == 'WEPP_PASS_COMPONENTS 3' and lines[2].split() == ['16', '2000']
                    assert set(daily_records(lines)) == expected
                    assert all((output / f'H{identifier}.{suffix}.dat').stat().st_size > 0
                               for suffix in ('pass', 'wat', 'soil', 'plot', 'ebe', 'element', 'loss'))
            folder = output / 'interchange'
            ledger = load(root)
            accounting = accounting_source(root)
            assert ledger['state'] == 'ready' and sha(accounting) == evidence['accounting_sha256']
            assert sha(folder / 'totalwatsed3.parquet') == evidence['totalwatsed_sha256']
            assert sha(folder / 'roads_segment_loss_summary.parquet') == evidence['summary_sha256']
            wat = pq.read_table(folder / 'H.wat.parquet')
            dates = wat.select(['wepp_id', 'ofe_id', 'year', 'julian']).to_pandas()
            assert set(dates.wepp_id) == set(ids)
            groups = dates.groupby(['wepp_id', 'ofe_id'])
            for _, group in groups:
                assert len(group) == 5844 and set(zip(group.year, group.julian)) == expected_tokens
            nulls = {}
            for field in wat.schema:
                if pa.types.is_floating(field.type):
                    values = wat[field.name]
                    assert pc.all(pc.is_finite(pc.drop_null(values))).as_py() is not False
                    nulls[field.name] = values.null_count
            total = pq.read_table(folder / 'totalwatsed3.parquet').to_pandas().set_index('sim_day_index').sort_index()
            assert len(total) == 5844 and np.array_equal(total.index, np.arange(1, 5845))
            assert set(zip(total.year, total.julian)) == expected_tokens
            accounted = pq.read_table(accounting).to_pandas()
            area = sum(t['area_m2'] for t in ledger['targets'])
            assert np.allclose(total.Area, area, rtol=1e-10)
            assert np.allclose(accounted.groupby('sim_day_index').Area.sum(), area, rtol=1e-10)
            for raw, published in [('P', 'Precipitation'), ('Dp', 'Percolation'), ('latqcc', 'Lateral Flow'),
                                   ('Ep', 'Transpiration'), ('Es', 'Evaporation'), ('Er', 'Interception')]:
                weighted = (accounted[raw] * accounted.Area).groupby(accounted.sim_day_index).sum() / area
                assert np.isfinite(weighted).all() and np.isfinite(total[published]).all()
                assert np.allclose(weighted, total[published], rtol=1e-9, atol=1e-9)
            passes = pq.read_table(folder / 'H.pass.parquet', columns=['wepp_id', 'sim_day_index', 'runvol']).to_pandas()
            canonical = passes[passes.wepp_id.isin([t['id'] for t in ledger['targets']])]
            volume = canonical.groupby('sim_day_index').runvol.sum()
            assert np.allclose(volume, total.runvol, rtol=1e-9, atol=1e-9)
            assert np.allclose(volume / area * 1000., total.Runoff, rtol=1e-9, atol=1e-9)
            assert np.allclose(total.Streamflow, total.Runoff + total['Lateral Flow'] + total.Baseflow)
            summary = pq.read_table(folder / 'roads_segment_loss_summary.parquet').to_pylist()
            assert {r['segment_run_id'] for r in summary} == set(ids)
            assert all(r['simulation_years'] == 16 and r['modeled_area_m2'] > 0 and not r['loss_row_missing'] for r in summary)
            # Assert all assets exist so the installed reader cannot enter its converter fallback.
            assert all((folder / name).is_file() for name in AVERAGE_FILENAMES.values())
            loss = Loss(output / 'loss_pw0.txt', wd=str(root))
            assert len(loss.hill_tbl) == 66 and len(loss.chn_tbl) == 27 and len(loss.out_tbl) == 11
            assert math.isfinite(loss.wsarea) and loss.wsarea > 0
            water_report = TotalWatbalReport(root, output_scope='roads')
            assert water_report.data and all(math.isfinite(float(v)) for r in water_report.data for v in r.values())
            item.update(expected_negative=False, native=native, completed_native_profiles=len(ids),
                        completed_design_profiles=sum(r['design'] == case['design'] for r in completed),
                        native_ofe_groups=len(groups), native_water_rows=wat.num_rows,
                        native_pass_daily_rows=5844 * len(ids), water_null_counts=nulls,
                        tc_out_regular_independent=True, roads_tc_sha256=sha(tc),
                        baseline_tc_sha256=sha(root / 'wepp/runs/tc_out.txt'),
                        modeled_area_m2=area, modes=dict(Counter(t['mode'] for t in ledger['targets'])),
                        accounting_reconciliation=True, daily_accounting_rows=len(total),
                        summary_profiles=len(summary), installed_loss_rows=dict(hills=66, channels=27, outlet=11),
                        installed_loss_area_ha=loss.wsarea, installed_water_years=water_report.years,
                        mean_annual_mm={k: float(total[k].sum() / 16) for k in
                                        ['Precipitation', 'Runoff', 'Lateral Flow', 'Baseflow', 'Percolation', 'ET']})
        assert inventory(root, ('wepp/runs', 'wepp/output')) == protected
        assert inventory(root, ('wepp/roads',)) == before
        item['roads_files_verified_unchanged_during_review'] = len(before)
        item['roads_artifact_hashes'] = before
        report['cases'][case['name']] = item
        print(case['name'], 'readback passed', flush=True)
    after = inventory(source, ('wepp', 'roads', 'climate', 'dem', 'watershed'))
    after.update({p.name: sha(p) for p in source.glob('*.nodb')})
    assert after == source_before
    report.update(passed=True, source_unchanged=True, native_invocations=0, converter_invocations=0)
    target = ART / 'resumption-r7-current-roads-v2-outcome-readback.json'
    assert not target.exists()
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('PASS', sha(target), flush=True)


if __name__ == '__main__':
    main()
