"""Fresh isolated Roads PASS composition, watershed routing and native report validation."""
from pathlib import Path
import hashlib
import json
from types import SimpleNamespace

import pyarrow.parquet as pq
from wepppy.wepp.interchange.roads_accounting import compose, mark_routed, regenerate, accounting_source
from wepppy.wepp.interchange import run_wepp_hillslope_pass_interchange, run_wepp_watershed_interchange
from wepp_runner.wepp_runner import make_watershed_omni_contrasts_run, run_watershed

root = Path('/workdir/wepppy/tests/wepp/interchange/fixtures/roads-accounting-scratch/um1')
original = Path('/wc1/runs/cl/clogging-starch')
assert root != original and root.is_dir()
hash_file = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
originals = {str(p.relative_to(original)): hash_file(p) for scope in ('wepp/output', 'wepp/roads/output')
             for p in (original/scope/'interchange').glob('*.parquet')}
base = root/'wepp/output/interchange'
roads = root/'wepp/roads/output'
ids = sorted(pq.read_table(base/'H.pass.parquet', columns=['wepp_id'])['wepp_id'].unique().to_pylist())
records = json.loads((root/'wepp/roads/segments/roads.segment.pass.manifest.json').read_text())
ledger = compose(root, ids, records, single_storm=False)
print('composed', len(ledger['targets']), 'targets', len(ledger['sources']), 'sources', flush=True)
runs = root/'wepp/roads/runs'
make_watershed_omni_contrasts_run(16, [f'../output/H{i}' for i in ids], str(runs), wepp_bin='wepp_260409')
assert all(f'../output/H{i}.pass.dat' in (runs/'pw0.run').read_text() for i in ids)
run_watershed(str(runs), wepp_bin='wepp_260409')
mark_routed(root)
print('fresh watershed completed', flush=True)
run_wepp_hillslope_pass_interchange(roads)
settings = json.loads((root/'wepp.nodb').read_text())['py/state']['baseflow_opts']
regenerate(root, SimpleNamespace(**settings))
run_wepp_watershed_interchange(roads, start_year=2000, delete_after_interchange=False,
    run_soil_interchange=(roads/"soil_pw0.txt").exists(),
    run_chnwb_interchange=(roads/"chnwb.txt").exists() or (roads/"chnwb.txt.gz").exists(),
    run_chan_out_interchange=(roads/"chan.out").exists() or (roads/"chan.out.gz").exists())
accounting_source(root)
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
report = HillslopeWatbalReport(root, output_scope="roads")
water = pq.read_table(roads/'interchange/totalwatsed3.parquet').to_pandas()
metrics = ['Runoff', 'Lateral Flow', 'Percolation', 'Baseflow', 'Streamflow']
assert len(water) == 5844 and water.year.nunique() == 16
for rel, digest in originals.items():
    assert hash_file(original/rel) == digest, rel
result = {'scratch': str(root), 'rows': len(water), 'years': int(water.year.nunique()),
          'area_m2': float(water.Area.iloc[0]), 'average_report_area_m2': report.wsarea,
          'average_report_source': str(report._resolve_source_path()),
          'average_report_cache_status': report.cache_status, 'ledger_area_m2': sum(t['area_m2'] for t in ledger['targets']),
          'annual': water.groupby('year')[metrics].sum().reset_index().to_dict('records'),
          'original_parquet_files_unchanged': len(originals), 'pw0_run_sha256': hash_file(runs/'pw0.run'),
          'pw0_error_sha256': hash_file(runs/'pw0.err')}
(root.parent/'validation.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2), flush=True)
