#!/usr/bin/env python3
"""Read-only opening evidence for the January 1993 Topanga event outlier."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
OUT = HERE/'artifacts/opening-window'
PRIOR = HERE.parents[1]/'investigations/2026-10-09-watershed-return-period-comparisons/artifacts/snapshot'
ROOT = Path('/wc1/runs/sc/scrawny-relay')
NAMES = ('H.pass.parquet', 'pass_pw0.events.parquet', 'H.wat.parquet',
         'H.ebe.parquet', 'tc_out.parquet', 'chanwb.parquet', 'chnwb.parquet',
         'totalwatsed3.parquet')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    prior = json.loads((PRIOR/'provenance.json').read_text())['runs']
    OUT.mkdir(parents=True, exist_ok=False)
    manifest = {}
    summaries = []
    peaks = []
    for scenario in ('burned', 'undisturbed'):
        run = ROOT if scenario == 'burned' else ROOT/'_pups/omni/scenarios/undisturbed'
        inter = run/'wepp/output/interchange'
        known = next(r for r in prior if r['key'] == f'topanga_gridmet_261009_{scenario}')
        assert sha(inter/'ebe_pw0.parquet') == known['source_sha256']
        data = {}
        for name in NAMES + ('ebe_pw0.parquet', 'chan.out.parquet', 'pass_pw0.metadata.parquet'):
            source = inter/name
            before = sha(source)
            filters = None if name == 'pass_pw0.metadata.parquet' else [('year', '=', 1993), ('julian', '>=', 10), ('julian', '<=', 24)]
            table = pq.read_table(source, filters=filters)
            assert table.num_rows > 0, name
            dest = OUT/f'{scenario}__{name}'
            pq.write_table(table, dest, compression='zstd')
            check = pq.read_table(dest)
            assert check.equals(table) and before == sha(source)
            manifest[dest.name] = dict(source=str(source), source_sha256=before,
                extract_sha256=sha(dest), rows=table.num_rows,
                selection='all metadata' if filters is None else 'year=1993; julian=10..24',
                field_units={f.name:(f.metadata or {}).get(b'units', b'').decode() for f in table.schema})
            data[name] = check.to_pandas()
        p = data['H.pass.parquet']
        meta = data['pass_pw0.metadata.parquet'][['wepp_id','area']]
        for day in range(10,25):
            source = p.loc[p.julian.eq(day)]
            outlet = data['ebe_pw0.parquet'].loc[lambda f:f.julian.eq(day)].iloc[0]
            timing = data['tc_out.parquet'].loc[lambda f:f.julian.eq(day)].iloc[0]
            ledger = data['chanwb.parquet'].loc[lambda f:f.julian.eq(day)].iloc[0]
            row = dict(scenario=scenario, julian=day, hillslopes=len(source),
                source_runvol_m3=float(source.runvol.sum()),
                source_lateral_m3=float(source.sbrunv.sum()),
                sum_individual_source_peaks_m3s=float(source.peakro.sum()),
                max_source_peak_m3s=float(source.peakro.max()),
                max_peak_wepp_id=int(source.loc[source.peakro.idxmax(),'wepp_id']),
                outlet_volume_m3=float(outlet.runoff_volume), outlet_peak_m3s=float(outlet.peak_runoff),
                timing={k:float(timing[k]) for k in ['Time of Conc (hr)','Storm Duration (hr)','Storm Peak (hr)']},
                reported_channel_ledger={k:float(ledger[k]) for k in ['Inflow (m^3)','Outflow (m^3)','Storage (m^3)','Baseflow (m^3)','Loss (m^3)','Balance (m^3)']})
            summaries.append(row)
        focus = p.loc[p.julian.eq(18)].merge(meta,on='wepp_id',validate='one_to_one')
        focus['scenario'] = scenario
        peaks.append(focus.nlargest(20,'peakro'))
    pd.concat(peaks).to_csv(OUT/'largest-source-peaks-jan18.csv',index=False)
    (OUT/'daily-summary.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')
    (OUT/'provenance.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in sorted(OUT.iterdir())},indent=2)+'\n')
    for row in summaries:
        if row['julian'] in (16,17,18,19,20):
            print(json.dumps(row),flush=True)


if __name__ == '__main__':
    main()
