"""Run in a fresh WEPPcloud process against the isolated MOFE validation copy."""
import hashlib
import json
from pathlib import Path
import time

import duckdb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from wepppyo3.wepp_interchange import wepp_interchange_rust as native
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.wepp.interchange.hill_wat_interchange import load_hill_wat_dataframe
from wepppy.nodb.mods.features_export.temporal_wide_materializer import derive_water_et, materialize_temporal_layer_wide

ROOT = Path('/wc1/runs/mo/mofe-et-dp-validation-20261020')
SOURCE = ROOT / 'wepp/output/interchange/H.wat.parquet'
OUT = ROOT / 'mofe-validation'
OUT.mkdir(exist_ok=True)
with duckdb.connect() as db:
    db.read_parquet(str(SOURCE)).create_view('wat')
    db.read_parquet(str(ROOT/'watershed/hillslopes.parquet')).create_view('hill')
    mapping = dict(db.execute('SELECT wepp_id,topaz_id FROM hill').fetchall())
    started = time.perf_counter()
    native.hillslope_watbal_to_parquet(str(SOURCE), str(OUT/'fresh-native.parquet'), mapping)
    native_seconds = time.perf_counter() - started
    expected = db.execute('''WITH daily AS (
        SELECT hill.topaz_id, water_year, sim_day_index,
               sum((Ep+Es+Er)*wat.Area)/sum(wat.Area) AS et,
               sum(Dp*wat.Area)/sum(wat.Area) AS dp
        FROM wat JOIN hill USING(wepp_id) GROUP BY ALL
        ) SELECT topaz_id,water_year,sum(et) AS et,sum(dp) AS dp FROM daily GROUP BY ALL
    ''').df().sort_values(['topaz_id','water_year'])
    actual = pq.read_table(OUT/'fresh-native.parquet').to_pandas().sort_values(['TopazID','WaterYear'])
    np.testing.assert_allclose(actual['Transpiration + Evaporation (mm)'], expected.et, rtol=1e-12, atol=1e-8)
    np.testing.assert_allclose(actual['Percolation (mm)'], expected.dp, rtol=1e-12, atol=1e-8)
    wepp_id = db.execute('SELECT wepp_id FROM wat GROUP BY wepp_id HAVING max(ofe_id)>1 LIMIT 1').fetchone()[0]
    sample = db.execute('SELECT * FROM wat WHERE wepp_id=? ORDER BY sim_day_index,ofe_id', [wepp_id]).df()
    pq.write_table(pq.read_table(SOURCE, filters=[("wepp_id", "=", wepp_id)]),
                   OUT/'actual-hill-water.parquet')
    daily = load_hill_wat_dataframe(ROOT/'wepp/output', wepp_id)
    reference = sample.groupby('sim_day_index').apply(
        lambda g: pd.Series({'ET': ((g.Ep+g.Es+g.Er)*g.Area).sum()/g.Area.sum(),
                             'Dp': (g.Dp*g.Area).sum()/g.Area.sum()}), include_groups=False)
    np.testing.assert_allclose(daily.Ep+daily.Es+daily.Er, reference.ET, rtol=1e-12, atol=1e-8)
    np.testing.assert_allclose(daily.Dp, reference.Dp, rtol=1e-12, atol=1e-8)
    sample = derive_water_et(sample); sample['key'] = sample.wepp_id
    exports = {}
    # Actual multi-year data, real daily reductions, persisted and read back.
    for mode in ('event','yearly','annual_average'):
        selected = sample if mode != 'event' else sample[sample.sim_day_index <= 2]
        result = materialize_temporal_layer_wide(
            frame=selected, layer_id='wepp.interchange.hill_wat', temporal_mode=mode,
            selected_columns=('ET','Dp'), unit_mapping={'ET':'mm','Dp':'mm'},
            join_key_column='key', event_selector=None).frame
        result.to_parquet(OUT/f'export-{mode}.parquet',index=False)
        result.to_csv(OUT/f'export-{mode}.csv',index=False)
        pd.testing.assert_frame_equal(pd.read_parquet(OUT/f'export-{mode}.parquet'),result)
        exports[mode] = result.to_dict(orient='records')
    expected_calendar = reference.copy()
    years = sample.drop_duplicates('sim_day_index').set_index('sim_day_index').year
    expected_calendar['year'] = years
    for metric in ('ET','Dp'):
        totals = expected_calendar.groupby('year')[metric].sum()
        for year,value in totals.items():
            np.testing.assert_allclose(exports['yearly'][0][f'{metric}_yr{year}'],value,rtol=1e-12)
        np.testing.assert_allclose(exports['annual_average'][0][metric],totals.mean(),rtol=1e-12)
    report = HillslopeWatbalReport(ROOT)
    cache = ROOT/'wepp/reports/cache/hillslope_watbal_summary.parquet'
    started = time.perf_counter(); warm = HillslopeWatbalReport(ROOT); warm_seconds = time.perf_counter()-started
    assert warm.cache_status == 'current'
    pd.DataFrame([dict(row.row) for row in report.avg_annual_iter()]).to_csv(OUT/'report-annual.csv',index=False)
    receipt = dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        native_module=native.__file__,native_sha256=hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        input_rows=pq.ParquetFile(SOURCE).metadata.num_rows,hills=len(mapping),summary_rows=len(actual),
        native_seconds=native_seconds,warm_seconds=warm_seconds,warm_status=warm.cache_status,
        sample_wepp_id=int(wepp_id),sample_rows=len(sample),sample_days=len(reference),
        daily_loader_parity=True,all_hill_year_oracle_parity=True,export_calendar_oracle_parity=True,
        outputs=str(OUT),cache=str(cache),exports=exports)
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k!='exports'},indent=2))
