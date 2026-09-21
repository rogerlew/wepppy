"""Read production artifacts over SSH; write only local summary CSVs/provenance.

Run from the repository root with .venv/bin/python and pandas/pyarrow installed.
Calculations mirror the 20260917 work-package summarize_production.py.
"""
import hashlib
import io
import json
import math
import shlex
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

OUTPUT = Path(__file__).resolve().parent
REFERENCE = OUTPUT.parents[2] / 'docs/work-packages/20260917_mofe_scenario_artifact_integrity/artifacts/mofe-production-hillslope-response-summary.csv'
PROJECTS = [('rithet-creek', 'choice-feminist'), ('judge', 'aliquot-shoji')]
SCENARIOS = [
    ('base', 'Base / SBS scenario'),
    ('undisturbed', 'Unburned / undisturbed'),
    ('uniform_low', 'Low severity fire'),
    ('uniform_moderate', 'Moderate severity fire'),
    ('uniform_high', 'High severity fire'),
    ('prescribed_fire', 'Prescribed fire'),
    ('thinning_30_90', 'Thinning: 30% canopy cover / 90% ground cover'),
    ('thinning_50_90', 'Thinning: 50% canopy cover / 90% ground cover'),
]


def summarize(frame, label, order):
    area = frame['Hillslope Area']
    runoff = frame['Runoff Volume'] / (area * 10)
    sediment, soil_loss = frame['Sediment Yield'], frame['Soil Loss']
    row = dict(scenario=label, hillslope_count=len(frame), area_ha=area.sum(),
               area_weighted_runoff_depth_mm_per_yr=frame['Runoff Volume'].sum()/(area.sum()*10),
               total_runoff_volume_m3_per_yr_estimated=frame['Runoff Volume'].sum(),
               total_sediment_yield_tonne_per_yr=sediment.sum()/1000,
               total_soil_loss_tonne_per_yr=soil_loss.sum()/1000,
               zero_runoff_hillslopes=int((runoff == 0).sum()),
               negligible_runoff_hillslopes_lt_1_mm_yr=int((runoff < 1).sum()),
               zero_sediment_hillslopes=int((sediment == 0).sum()),
               negligible_sediment_hillslopes_lt_1_kg_yr=int((sediment < 1).sum()))
    for name, values in {
        'runoff_depth_mm_per_yr': runoff, 'runoff_volume_m3_per_yr': frame['Runoff Volume'],
        'sediment_yield_kg_per_yr': sediment, 'sediment_yield_density_kg_ha_yr': sediment/area,
        'soil_loss_kg_per_yr': soil_loss, 'soil_loss_density_kg_ha_yr': soil_loss/area,
    }.items():
        stats = dict(min=values.min(), q1=values.quantile(.25), median=values.median(),
                     mean=values.mean(), std=values.std(), q3=values.quantile(.75),
                     iqr=values.quantile(.75)-values.quantile(.25),
                     p95=values.quantile(.95), max=values.max())
        row.update({name+'_'+key: value for key, value in stats.items()})
    row['scenario_order'] = order
    return row


def main():
    columns = list(pd.read_csv(REFERENCE, nrows=0).columns)
    for project, runid in PROJECTS:
        root = f'/geodata/wc1/runs/{runid[:2]}/{runid}'
        prefixes = {key: '' if key == 'base' else f'_pups/omni/scenarios/{key}/'
                    for key, _ in SCENARIOS}
        names = ['omni.nodb', 'watershed/hillslopes.parquet']
        for prefix in prefixes.values():
            names.extend([prefix+'wepp/output/interchange/loss_pw0.hill.parquet', prefix+'wepp.nodb'])
        command = shlex.join(['tar', '-cf', '-', '-C', root, *names])
        snapshot = subprocess.check_output(['ssh', 'wepp1', command])
        rows, sources = [], []
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as archive:
            def read(name):
                return archive.extractfile(name).read()
            omni = json.loads(read('omni.nodb'))['py/state']
            definitions = omni['_scenarios']
            keys = {d['type'] if d['type'] != 'thinning' else
                    f"thinning_{d['canopy_cover']}_{d['ground_cover']}".replace('%', '')
                    for d in definitions}
            assert keys == set(prefixes) - {'base'}, definitions
            hills = pd.read_parquet(io.BytesIO(read('watershed/hillslopes.parquet')))
            expected_ids = set(hills.wepp_id)
            baseline_area = None
            for order, (key, label) in enumerate(SCENARIOS, 1):
                name = prefixes[key] + 'wepp/output/interchange/loss_pw0.hill.parquet'
                raw = read(name)
                frame = pd.read_parquet(io.BytesIO(raw))
                assert len(frame) == len(expected_ids) == frame.wepp_id.nunique(), key
                assert set(frame.wepp_id) == expected_ids, key
                for column in ['Hillslope Area', 'Runoff Volume', 'Sediment Yield', 'Soil Loss']:
                    assert frame[column].map(math.isfinite).all(), (key, column)
                    assert (frame[column] >= 0).all(), (key, column)
                assert (frame['Hillslope Area'] > 0).all()
                areas = frame.set_index('wepp_id')['Hillslope Area'].sort_index()
                if baseline_area is None:
                    baseline_area = areas
                pd.testing.assert_series_equal(areas, baseline_area)
                metadata = pq.read_schema(io.BytesIO(raw)).metadata
                assert int(metadata[b'average_years']) > 0
                rows.append(summarize(frame, label, order))
                wepp = json.loads(read(prefixes[key]+'wepp.nodb'))['py/state']
                sources.append(dict(scenario=key, file=root+'/'+name,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    modified_utc=datetime.fromtimestamp(archive.getmember(name).mtime, timezone.utc).isoformat(),
                    average_years=int(metadata[b'average_years']), wepp_bin=wepp.get('_wepp_bin')))
        result = pd.DataFrame(rows)
        assert list(result.columns) == columns
        assert len({s['average_years'] for s in sources}) == 1
        output = OUTPUT / f'{project}-{runid}-hillslope-response-summary.csv'
        result.to_csv(output, index=False)
        assert list(pd.read_csv(output).columns) == columns
        provenance = dict(retrieved_utc=datetime.now(timezone.utc).isoformat(), host='wepp1',
                          runid=runid, scenario_definitions=definitions, sources=sources)
        output.with_suffix('.sources.json').write_text(json.dumps(provenance, indent=2)+'\n')
        print(output.name)
        print(result[['scenario', 'hillslope_count', 'area_weighted_runoff_depth_mm_per_yr',
                      'total_sediment_yield_tonne_per_yr']].to_string(index=False))


if __name__ == '__main__':
    main()
