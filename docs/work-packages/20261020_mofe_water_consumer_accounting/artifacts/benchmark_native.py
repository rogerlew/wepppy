import importlib.util,time,json,resource,hashlib
from pathlib import Path
import pyarrow.parquet as pq
binary='/workdir/wepppyo3/target/release/libwepp_interchange_rust.so'
spec=importlib.util.spec_from_file_location('wepp_interchange_rust',binary);n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
results=[]
for label,root in [('single','/wc1/runs/th/thespian-cleanness'),('multi','/wc1/runs/mo/mofe-et-dp-validation-20261020')]:
 p=Path(root)/'wepp/output/interchange/H.wat.parquet'
 ids=n.hillslope_watbal_wepp_ids(str(p));mapping={i:i for i in ids}
 times=[]
 for repeat in range(3):
  start=time.perf_counter();n.hillslope_watbal_to_parquet(str(p),f'/tmp/wca-bench-{label}.parquet',mapping);times.append(time.perf_counter()-start)
 results.append(dict(label=label,native_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),rows=pq.read_metadata(p).num_rows,seconds=times,maxrss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
 print(results[-1],flush=True)
Path('/workdir/wepppy/docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_native_performance.json').write_text(json.dumps(results,indent=2)+'\n')
