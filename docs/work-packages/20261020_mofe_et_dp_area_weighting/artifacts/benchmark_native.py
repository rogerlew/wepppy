"""Read-only source benchmark; writes only to the isolated validation directory."""
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time
import pyarrow.parquet as pq
binary, source, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('wepp_interchange_rust',binary)
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
ids = native.hillslope_watbal_wepp_ids(str(source)); mapping = {key:key for key in ids}
times = []
for _ in range(3):
    started = time.perf_counter()
    native.hillslope_watbal_to_parquet(str(source),str(output),mapping)
    times.append(time.perf_counter()-started)
print(json.dumps(dict(binary=str(binary),source=str(source),bytes=source.stat().st_size,
    rows=pq.ParquetFile(source).metadata.num_rows,hills=len(ids),seconds=times,
    peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
