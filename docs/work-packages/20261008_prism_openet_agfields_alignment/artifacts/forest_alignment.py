"""Bounded real API/native WEPP probes; run with wctl exec -T weppcloud python.

Only fixture routing is substituted: source controllers remain read-only, selected
polygons and output directories are isolated. No API, parser, writer or binary mock.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import shutil
import sys

import numpy as np
import pandas as pd
from wepppy.climates.prism.wepp_adapter import validate_cli
from wepppy.nodb.core import Climate, Landuse, Watershed
from wepppy.nodb.mods.openet.openet_ts import OpenET_TS
from wepppy.nodb.mods.ag_fields.ag_fields import run_wepp_subfield

SOURCE = Path('/wc1/runs/ch/chemotherapeutic-scope')
ROOT = Path('/wc1/prism-downstream-alignment-20261008')
OUT = Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
climate = Climate.getInstance(str(SOURCE))
landuse = Landuse.getInstance(str(SOURCE))
watershed = Watershed.getInstance(str(SOURCE))
translator = watershed.translator_factory()
assert int(climate.climate_mode) == 16
assert (climate.observed_start_year, climate.observed_end_year) == (2019, 2021)
dates = pd.date_range('2019-01-01', '2021-12-31')
geo = json.loads(Path(watershed.subwta_shp).read_text())
features = [f for f in geo['features'] if not str(f['properties']['TopazID']).endswith('4')]
# Reproducible spread through the watershed's existing hillslope ordering.
selected = [features[i] for i in [0, len(features)//2, len(features)-1]]
ids = [str(f['properties']['TopazID']) for f in selected]
shape = ROOT / 'sample-hillslopes.geojson'
shape.write_text(json.dumps(dict(type='FeatureCollection', features=selected)))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def openet():
    scratch = ROOT / 'openet-probe'
    scratch.mkdir(exist_ok=True)
    ctl = OpenET_TS.getInstance(str(scratch)) if (scratch / 'openet_ts.nodb').exists() else OpenET_TS(str(scratch), 'disturbed9002_wbt.cfg')
    with patch.object(Climate, 'getInstance', return_value=climate), patch.object(
        Watershed, 'getInstance', return_value=SimpleNamespace(subwta_shp=str(shape))
    ):
        ctl.acquire_timeseries(max_workers=2)
    ctl.analyze()
    frame = pd.read_parquet(ctl.openet_parquet_path)
    frame.to_parquet(OUT / 'openet-sample.parquet', index=False)
    coverage(frame)


def coverage(frame):
    expected = {(y, m) for y in range(2019, 2022) for m in range(1, 13)}
    report = []
    for topaz in ids:
        for dataset in ['ensemble', 'eemetric']:
            part = frame[(frame.topaz_id == topaz) & (frame.dataset_key == dataset)]
            assert not part.duplicated(['year', 'month']).any()
            assert set(part.units) == {'mm'}
            available = set(zip(part.year, part.month))
            assert available <= expected
            report.append(dict(topaz_id=topaz, dataset=dataset, months=len(part), null_values=int(part.value.isna().sum()),
                               missing_months=sorted(expected-available)))
    (OUT / 'openet-coverage.json').write_text(json.dumps(report, indent=2)+'\n')
    print({'openet_rows':len(frame), 'coverage':report}, flush=True)


def agfields():
    fixture = Path('/workdir/wepppy/wepppy/wepp/management/data/Agriculture/corn-no till.man')
    results = []
    for spatial in [1, 2]:
        archive = SOURCE / f'archives/prism-integration-mode{spatial}-2019-2021'
        for topaz in ids:
            hill = translator.wepp(top=int(topaz))
            scratch = ROOT / f'mode{spatial}-hill{hill}'
            runs = scratch / 'wepp/ag_fields/runs'
            for directory in [runs, runs.parent/'output', scratch/'wepp/runs', scratch/'ag_fields/plant_files', scratch/'ag_fields/sub_fields/slope_files']:
                directory.mkdir(parents=True, exist_ok=True)
            for suffix in ['cli', 'sol']:
                shutil.copyfile(archive/f'wepp/runs/p{hill}.{suffix}', scratch/f'wepp/runs/p{hill}.{suffix}')
            parent = scratch/f'wepp/runs/p{hill}.cli'
            data = validate_cli(parent, dates)
            shutil.copyfile(archive/f'wepp/runs/p{hill}.slp', scratch/f'ag_fields/sub_fields/slope_files/field_1_{topaz}.slp')
            shutil.copyfile(fixture, scratch/'ag_fields/plant_files/corn.man')
            (scratch/'ag_fields/rotation_lookup.tsv').write_text('crop_name\tdatabase\trotation_id\nCorn\tplant_file_db\tcorn.man\n')
            with patch.object(Climate, 'getInstance', return_value=climate), patch.object(Landuse, 'getInstance', return_value=landuse):
                run_wepp_subfield(str(scratch), 1, topaz, hill, 1, ['Corn']*3, False, None, 'wepp_260430')
            run = (runs/'p1.run').read_text().splitlines()
            reference = [line for line in run if line.endswith('.cli')]
            assert reference == [f'../../runs/p{hill}.cli']
            assert digest(runs/reference[0]) == digest(archive/f'wepp/runs/p{hill}.cli')
            lines = (runs.parent/'output/H1.wat.dat').read_text().splitlines()
            rows = [[float(x) for x in line.split()] for line in lines if len(line.split()) == 25 and line.split()[0].isdigit()]
            water = pd.DataFrame(rows)
            assert len(water) == len(dates)
            actual_dates = pd.to_datetime(water[2].astype(int).astype(str), format='%Y') + pd.to_timedelta(water[1]-1, unit='D')
            assert pd.DatetimeIndex(actual_dates).equals(dates)
            assert np.isfinite(water.to_numpy()).all()
            assert np.allclose(water[3], data.prcp, atol=.051, rtol=0)
            results.append(dict(spatial=spatial, topaz_id=topaz, wepp_id=hill,
                                days=len(water), leap_day=bool((actual_dates == '2020-02-29').any()),
                                parent_cli_sha256=digest(parent), run_cli_reference=reference[0],
                                management_sha256=digest(runs/'p1.man'),
                                water_balance_sha256=digest(runs.parent/'output/H1.wat.dat'),
                                precipitation_mm=float(water[3].sum())))
        print({'agfields_spatial':spatial, 'cases':len(ids)}, flush=True)
    (OUT/'agfields-native.json').write_text(json.dumps(results, indent=2)+'\n')


def direct():
    frames = []
    for topaz in ids:
        for model, dataset in [('Ensemble','ensemble'),('eeMETRIC','eemetric')]:
            evidence = json.loads((OUT/f'direct-openet-{topaz}-{model}.json').read_text())
            assert evidence['status'] == 200
            frame = pd.DataFrame(json.loads(evidence['body']))
            timestamps = pd.to_datetime(frame['time'])
            values = pd.to_numeric(frame['et'], errors='raise')
            assert np.isfinite(values.dropna()).all()
            # Retain missing ET as NaN; never interpret missing observations as zero.
            frames.append(pd.DataFrame(dict(topaz_id=topaz, year=timestamps.dt.year,
                month=timestamps.dt.month, value=values, units='mm',
                dataset_key=dataset, source='direct_openet_v2.1_mean')))
    result = pd.concat(frames, ignore_index=True)
    result.to_parquet(OUT/'openet-sample.parquet', index=False)
    coverage(result)


def align():
    observed = pd.read_parquet(OUT/'openet-sample.parquet')
    results = []
    frames = []
    for spatial in [1,2]:
        archive = SOURCE/f'archives/prism-integration-mode{spatial}-2019-2021'
        wat = pd.read_parquet(archive/'wepp/output/interchange/H.wat.parquet')
        for topaz in ids:
            hill = translator.wepp(top=int(topaz))
            model = wat[wat.wepp_id == hill].copy()
            model_dates = pd.to_datetime(model.year.astype(int).astype(str), format='%Y') + pd.to_timedelta(model['julian']-1, unit='D')
            model['month'] = model_dates.dt.month
            model['wepp_et_mm'] = model[['Ep','Es','Er']].sum(axis=1)
            monthly = model.groupby(['year','month'], as_index=False).agg(wepp_et_mm=('wepp_et_mm','sum'), days=('wepp_et_mm','size'))
            assert monthly.loc[(monthly.year == 2020) & (monthly.month == 2),'days'].iloc[0] == 29
            part = observed[observed.topaz_id == topaz]
            joined = part.merge(monthly, on=['year','month'], validate='many_to_one')
            assert len(joined) == len(part)
            joined['spatial'] = spatial
            frames.append(joined)
            results.append(dict(spatial=spatial, topaz_id=topaz, wepp_months=len(monthly), satellite_rows=len(part), matched_rows=len(joined)))
    pd.concat(frames).to_csv(OUT/'monthly-alignment.csv', index=False)
    (OUT/'alignment.json').write_text(json.dumps(results, indent=2)+'\n')
    print(results, flush=True)

if __name__ == '__main__':
    {'openet':openet, 'direct':direct, 'agfields':agfields, 'align':align}[sys.argv[1]]()
