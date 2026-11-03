"""Read completed v2 controller outputs without native calls or converters."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
import math
import re
import zipfile

import numpy as np
from osgeo import gdal

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from audit_pass_completeness_r7 import daily_records

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/current-project-v2')
ART = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    project = ROOT / 'baseline'
    runs, output = project / 'wepp/runs', project / 'wepp/output'
    before = {'runs': inventory(runs), 'output': inventory(output)}
    plot_hashes = inventory(project / 'wepp/plots')
    export_hashes = inventory(project / 'export')
    declaration_path = ROOT / 'baseline-execution-declaration.json'
    declaration = json.loads(declaration_path.read_text())
    assert all(sha(project / name) == value for name, value in declaration['inputs'].items())
    start = json.loads((ROOT / 'baseline-execution-start.json').read_text())
    assert start['declaration_sha256'] == sha(declaration_path)
    expected = {date(2000, 1, 1) + timedelta(days=i) for i in range(5844)}
    hills, notices = [], {}
    for identifier in list(range(1, 67)) + ['w0']:
        trace_path = runs / f'p{identifier}.err'
        trace = trace_path.read_text()
        watershed = identifier == 'w0'
        role = 'WATERSHED' if watershed else 'HILLSLOPE'
        binary = 'wepp_261029' if watershed else 'wepp_261029_hill'
        assert f'binary_sha256={declaration["binaries"][binary]}' in trace
        assert 'binary_identity_status=ok' in trace
        assert f'WEPP COMPLETED {role} SIMULATION SUCCESSFULLY' in trace
        assert all(marker in trace for marker in (
            '->Gwcoeff parameters set', '->WEPP hourly water seepage update set (UI code)',
            'FAO Penman-Monteith ET Method Implemented'))
        assert list(map(int, re.findall(r'SIMULATION YEAR =\s*(\d+)', trace))) == list(range(1, 17))
        assert not re.search(r'attempt [2-9]/', trace)
        if 'No Penman-Monteith ET parameters' in trace:
            begin = trace.index('*************** Notice')
            end = trace.index('FAO Penman-Monteith ET Method Implemented', begin)
            notices[trace_path.name] = trace[begin:end].strip()
        if watershed:
            continue
        lines = (output / f'H{identifier}.pass.dat').read_text().splitlines()
        assert lines[0] == 'WEPP_PASS_COMPONENTS 3'
        assert lines[1].strip() == f'p{identifier}.cli' and lines[2].split() == ['16', '2000']
        records = daily_records(lines)
        assert set(records) == expected
        families = [f'H{identifier}.{family}.dat' for family in
                    ('loss', 'wat', 'soil', 'plot', 'ebe', 'element', 'pass')]
        assert all((output / name).stat().st_size > 0 for name in families)
        hills.append(dict(wepp_id=identifier, calendar_days=len(records), labels=dict(Counter(records.values()))))
    interchange = output / 'interchange'
    water = pq.read_table(interchange / 'H.wat.parquet')
    daily = water.select(['wepp_id', 'ofe_id', 'year', 'julian']).to_pandas()
    expected_tokens = {(day.year, day.timetuple().tm_yday) for day in expected}
    groups = daily.groupby(['wepp_id', 'ofe_id'])
    assert len(groups) == 193
    for _, group in groups:
        assert len(group) == 5844 and set(zip(group.year, group.julian)) == expected_tokens
    nulls = {}
    for field in water.schema:
        if pa.types.is_floating(field.type):
            values = water[field.name]
            assert pc.all(pc.is_finite(pc.drop_null(values))).as_py() is not False
            nulls[field.name] = values.null_count
    elements = pq.read_table(interchange / 'H.element.parquet', columns=['SedLeave'])
    assert pc.all(pc.greater_equal(elements['SedLeave'], 0)).as_py()
    channel_dates = defaultdict(set)
    channel_rows = Counter()
    for line in (output / 'chnwb.txt').read_text().splitlines():
        tokens = line.split()
        if not tokens or not tokens[0].isdigit():
            continue
        assert len(tokens) == 27
        channel, julian, year = map(int, tokens[:3])
        assert all(math.isfinite(float(value)) for value in tokens[3:])
        channel_dates[channel].add((year, julian))
        channel_rows[channel] += 1
    assert channel_dates and all(days == expected_tokens for days in channel_dates.values())
    assert all(count == 5844 for count in channel_rows.values())
    annual = pq.read_table(interchange / 'loss_pw0.all_years.out.parquet')
    assert set(annual['year'].to_pylist()) == set(range(2000, 2016))
    log = (ROOT / 'baseline-run.log').read_text()
    assert 'Configured baseline native workflow completed' in log and 'Traceback' not in log
    completion_path = ROOT / 'baseline-native-completed.json'
    completed = json.loads(completion_path.read_text())
    assert completed['input_integrity'] and completed['source_integrity']
    assert completed['outputs'] == {f'wepp/output/{name}': value for name, value in before['output'].items()}
    prior_root = ROOT.parent / 'current-project-v1'
    prior = json.loads((ART / 'resumption-r7-current-project-v1-native-readback.json').read_text())
    raw = {name: digest for name, digest in before['output'].items() if '/' not in name}
    assert len(raw) == 470
    assert raw == {name: digest for name, digest in prior['artifacts']['output'].items() if '/' not in name}
    assert all(sha(prior_root / 'baseline/wepp/output' / name) == digest for name, digest in raw.items())
    required = ('H.pass.parquet', 'H.wat.parquet', 'H.loss.parquet', 'H.soil.parquet', 'H.element.parquet',
                'H.ebe.parquet', 'pass_pw0.events.parquet', 'pass_pw0.metadata.parquet', 'chnwb.parquet',
                'chanwb.parquet', 'chan.out.parquet', 'soil_pw0.parquet', 'ebe_pw0.parquet',
                'totalwatsed3.parquet', 'loss_pw0.hill.parquet', 'loss_pw0.chn.parquet', 'loss_pw0.out.parquet')
    interchange_rows = {name: pq.read_table(interchange / name).num_rows for name in required}
    assert all(count > 0 for count in interchange_rows.values())
    from wepppy.nodb.core import Wepp
    installed = Wepp.getInstance(str(project)).loss_report
    assert len(installed.hill_tbl) == 66 and len(installed.chn_tbl) == 27
    assert len(installed.out_tbl) == 11 and installed.wsarea == 44.33
    raster_info = {}
    for name in ('loss.tif', 'loss.WGS.tif'):
        raster = gdal.Open(str(project / 'wepp/plots' / name), gdal.GA_ReadOnly)
        assert raster is not None and raster.RasterXSize > 0 and raster.RasterYSize > 0
        band = raster.GetRasterBand(1)
        pixels = band.ReadAsArray()
        valid = pixels != band.GetNoDataValue()
        assert valid.any() and np.isfinite(pixels[valid]).all() and raster.GetProjection()
        raster_info[name] = dict(width=raster.RasterXSize, height=raster.RasterYSize,
                                valid_pixels=int(valid.sum()), sha256=sha(project / 'wepp/plots' / name))
        raster = None
    zip_paths = list((project / 'export').rglob('*.zip'))
    assert {p.name for p in zip_paths} == {'features_export.geopackage.zip', 'features_export.gdb.zip'}
    for path in zip_paths:
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
    gpkg_paths = list((project / 'export').rglob('features_export.gpkg'))
    assert len(gpkg_paths) == 1
    vector = gdal.OpenEx(str(gpkg_paths[0]), gdal.OF_VECTOR | gdal.OF_READONLY)
    assert vector is not None
    feature_layers = {vector.GetLayerByIndex(index).GetName(): vector.GetLayerByIndex(index).GetFeatureCount()
                      for index in range(vector.GetLayerCount())}
    assert feature_layers and all(count > 0 for count in feature_layers.values())
    vector = None
    assert before == {'runs': inventory(runs), 'output': inventory(output)}
    assert plot_hashes == inventory(project / 'wepp/plots') and export_hashes == inventory(project / 'export')
    report = dict(workflow_pass=True, scope='Bounded public-controller baseline only; no RQ/catalog parity',
        completion_sha256=sha(completion_path), raw_output_parity_with_failed_v1=470,
        installed_report=dict(hills=66, channels=27, outlet_rows=11, watershed_area_ha=installed.wsarea),
        interchange_rows=interchange_rows, rasters=raster_info, feature_layers=feature_layers,
        plot_hashes=plot_hashes, export_hashes=export_hashes,
        declaration_sha256=sha(declaration_path), start_sha256=sha(ROOT / 'baseline-execution-start.json'),
        run_log_sha256=sha(ROOT / 'baseline-run.log'), reader_sha256=sha(Path(__file__)),
        binary_sha256=declaration['binaries'], input_integrity=True, review_changed_evidence=False,
        hills=hills, daily_pass_records=sum(h['calendar_days'] for h in hills),
        wat_rows=water.num_rows, wat_ofes=len(groups), water_null_counts=nulls,
        element_rows=elements.num_rows, element_sedleave_nonnegative=True,
        channel_water_rows=sum(channel_rows.values()), channel_count=len(channel_rows),
        channel_dates_complete=True, watershed_annual_years=list(range(2000, 2016)),
        pmet_notices=notices, artifacts=before,
        limits=['No full water/particle closure audit', 'No dynamic snow-consumption trace',
                'No RQ, query-catalog, browser or later Roads workflow claim',
                'PMET channel fallback retained explicitly; coefficients do not discriminate ownership'])
    target = ART / 'resumption-r7-current-project-v2-native-readback.json'
    with target.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('workflow_pass', 'daily_pass_records', 'wat_rows',
          'wat_ofes', 'channel_water_rows', 'channel_count', 'pmet_notices')}))


if __name__ == '__main__':
    main()
