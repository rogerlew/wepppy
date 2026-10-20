"""Complete report build and settled-hit timing on isolated representative inputs."""
from pathlib import Path
import json,shutil,time,statistics,hashlib
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.nodb.core import Watershed
results=[]
for label,source in [('single',Path('/wc1/runs/th/thespian-cleanness')),('multi',Path('/wc1/runs/mo/mofe-et-dp-validation-20261020'))]:
 root=Path(f'/wc1/runs/mo/mofe-water-benchmark-{label}-20261020');root.mkdir(exist_ok=True)
 for name in ['watershed.nodb','ron.nodb','wepp.nodb','watershed/hillslopes.parquet','watershed/channels.parquet','wepp/output/interchange/H.wat.parquet']:
  p=source/name
  if not p.exists():continue
  dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
  if name.endswith('.nodb'):dst.write_text(dst.read_text().replace(str(source),str(root)))
 Watershed.getInstance(str(root)).translator_factory()
 start=time.perf_counter();report=HillslopeWatbalReport(root);first=time.perf_counter()-start
 times=[]
 for _ in range(5):
  start=time.perf_counter();report=HillslopeWatbalReport(root);times.append(time.perf_counter()-start)
 results.append(dict(label=label,native_sha256=hashlib.sha256(Path('/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so').read_bytes()).hexdigest(),first_seconds=first,settled_seconds=times,settled_mean_ms=statistics.mean(times)*1000,status=report.cache_status))
 print(results[-1],flush=True)
Path('/workdir/wepppy/docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_report_performance.json').write_text(json.dumps(results,indent=2)+'\n')
