"""Read-only actual Parquet baseline, digest admission, and 512-path eviction.

Run: wctl exec dtale python <this path> [output-stem] [baseline-module-path].
No live D-Tale dataset registration, named-source mutation, or full pandas load.
Hash bytes are exact Python stream bytes; /proc IO is whole-process telemetry.
Repeat this script after D-Tale implementation to observe actual guard counts.
"""
from collections import defaultdict
import hashlib
import importlib
import json
import os
from pathlib import Path
from statistics import mean
import sys
from tempfile import TemporaryDirectory
from time import perf_counter, sleep

import pyarrow.parquet as pq

from wepppy.all_your_base import file_digest

ARTIFACTS = Path(__file__).parent
if len(sys.argv) > 2:
    import importlib.util
    spec = importlib.util.spec_from_file_location("dtale_freshness_qa_baseline", sys.argv[2])
    dtale = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = dtale
    spec.loader.exec_module(dtale)
else:
    dtale = importlib.import_module("wepppy.webservices.dtale.dtale")
SOURCE = Path("/wc1/runs/th/thespian-cleanness/wepp/output/interchange/H.wat.parquet")
OUTPUT = ARTIFACTS / ((sys.argv[1] if len(sys.argv) > 1 else "dtale_large_parquet_current") + ".json")
source_before = SOURCE.stat()
assert 0 < source_before.st_size < 512 * 1024 ** 2
checks = 0
reads = defaultdict(int)
read_calls = defaultdict(int)
pressure_paths = set()
original_open = Path.open
original_fingerprint = dtale._fingerprint


class CountedStream:
    def __init__(self, stream, key):
        self.stream, self.key = stream, key

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def __getattr__(self, key):
        return getattr(self.stream, key)

    def read(self, *args, **kwargs):
        block = self.stream.read(*args, **kwargs)
        reads[self.key] += len(block)
        read_calls[self.key] += 1
        return block


def counted_open(path, *args, **kwargs):
    stream = original_open(path, *args, **kwargs)
    key = str(path.absolute())
    mode = args[0] if args else kwargs.get("mode", "r")
    if mode == "rb" and (key == str(SOURCE) or key in pressure_paths):
        return CountedStream(stream, key)
    return stream


def counted_fingerprint(*args, **kwargs):
    global checks
    checks += 1
    return original_fingerprint(*args, **kwargs)


def verified_hash(path=SOURCE, **kwargs):
    global checks
    checks += 1
    return file_digest.sha256_file(path, **kwargs)


def process_io():
    return {line.split(":")[0]: int(line.split(":")[1])
            for line in Path("/proc/self/io").read_text().splitlines()}


def cache_info():
    return {"observation": file_digest._observed_at.cache_info()._asdict(),
            "digest": file_digest._digest.cache_info()._asdict()}


def clear_hash_cache():
    file_digest._digest.cache_clear()
    file_digest._observed_at.cache_clear()


def measured(label, callback, repeats=1):
    before_bytes, before_all = reads[str(SOURCE)], sum(reads.values())
    before_calls, before_checks = read_calls[str(SOURCE)], checks
    before_io = process_io()
    timing = []
    result = None
    for _ in range(repeats):
        start = perf_counter()
        result = callback()
        timing.append(perf_counter() - start)
    after_io = process_io()
    record = {"name": label, "repeats": repeats,
              "elapsed_seconds": timing, "mean_seconds": mean(timing),
              "fingerprint_checks": checks - before_checks,
              "target_hash_bytes": reads[str(SOURCE)] - before_bytes,
              "all_instrumented_hash_bytes": sum(reads.values()) - before_all,
              "target_read_calls": read_calls[str(SOURCE)] - before_calls,
              "process_rchar_delta": after_io["rchar"] - before_io["rchar"],
              "process_physical_read_bytes_delta": after_io["read_bytes"] - before_io["read_bytes"],
              "cache": cache_info()}
    if hasattr(result, "shape"):
        record["returned_shape"] = list(result.shape)
    elif isinstance(result, int):
        record["returned_count"] = result
    records.append(record)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n")
    return result


metadata = pq.ParquetFile(SOURCE).metadata
records = []
results = {"source": str(SOURCE), "bytes": source_before.st_size,
           "rows": metadata.num_rows, "columns": metadata.num_columns,
           "row_groups": metadata.num_row_groups, "uid": os.getuid(), "gid": os.getgid(),
           "dtale_source_sha256": hashlib.sha256(Path(dtale.__file__).read_bytes()).hexdigest(),
           "dtale_source_file": str(dtale.__file__),
           "scope": "isolated actual lazy accessors; no service/global-state registration",
           "measurements": records}
Path.open = counted_open
dtale._fingerprint = counted_fingerprint
try:
    clear_hash_cache()
    instance = measured("lazy_constructor", lambda: dtale.LazyParquetDtaleInstance(SOURCE))
    measured("native_first_count", instance.rows)
    measured("cached_count", instance.rows, repeats=50)
    measured("first_sample", lambda: instance.base_df)
    measured("cached_sample", lambda: instance.base_df, repeats=50)
    columns = list(instance.base_df.columns)
    results["requested_grid_columns"] = columns
    measured("bounded_100_row_page", lambda: instance.load_data(row_range=[0, 100], columns=columns), repeats=5)
    measured("bounded_middle_page", lambda: instance.load_data(row_range=[metadata.num_rows // 2, metadata.num_rows // 2 + 100], columns=columns), repeats=3)
    measured("bounded_sorted_page", lambda: instance.load_data(row_range=[0, 100], columns=columns, sort=[[instance.base_columns[0], "DESC"]]), repeats=3)

    def normal_page():
        instance.rows()
        return instance.load_data(row_range=[0, 100], columns=columns)

    clear_hash_cache()
    measured("normal_page_after_cache_clear", normal_page)
    measured("normal_page_during_admission", normal_page, repeats=3)
    sleep(1.05)
    measured("normal_page_admitting", normal_page)
    measured("normal_page_settled", normal_page, repeats=10)

    clear_hash_cache()
    measured("digest_forced_uncached", lambda: verified_hash(use_cache=False))
    clear_hash_cache()
    measured("digest_first_observation", verified_hash)
    measured("digest_during_admission", verified_hash, repeats=3)
    sleep(1.05)
    measured("digest_admitting", verified_hash)
    measured("digest_settled", verified_hash, repeats=100)

    with TemporaryDirectory(prefix="dtale-digest-pressure-", dir=ARTIFACTS) as temporary:
        paths = [Path(temporary) / f"pressure-{index:03d}.bin" for index in range(512)]
        for index, path in enumerate(paths):
            path.write_bytes(index.to_bytes(4, "big"))
        pressure_paths.update(str(path.absolute()) for path in paths)
        measured("observe_512_other_paths", lambda: [verified_hash(path) for path in paths])
        sleep(1.05)
        measured("admit_512_other_paths", lambda: [verified_hash(path) for path in paths])
        measured("target_after_512_path_eviction", verified_hash)
        measured("normal_page_after_512_path_eviction", normal_page)
        sleep(1.05)
        measured("target_readmit_after_eviction", verified_hash)
        measured("normal_page_settled_after_eviction", normal_page, repeats=5)
finally:
    Path.open = original_open
    dtale._fingerprint = original_fingerprint
    source_after = SOURCE.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    results["source_generation_unchanged"] = all(getattr(source_before, field) == getattr(source_after, field) for field in fields)
    results["hash_read_byte_definition"] = "exact bytes returned by Python binary reads on target/pressure files; native readers use process IO counters instead"
    results["filesystem_cache_note"] = "No OS page-cache drop; cold means helper-cache cold, not guaranteed physical-storage cold"
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
