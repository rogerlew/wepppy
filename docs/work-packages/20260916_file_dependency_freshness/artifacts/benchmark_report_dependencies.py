"""Read-only C08/C09 native report, dependency, and cache baseline.

Run: wctl exec weppcloud python <this path> [output-stem].
Only this artifact directory receives generated summaries/cache files. The audit
guard rejects Python writes to the named run; native output is explicitly local.
No OS page-cache eviction: helper-cold measurements remain warm-filesystem data.
"""
from collections import defaultdict
import hashlib
import importlib
import json
import os
from pathlib import Path
from statistics import mean
import sys
from time import perf_counter, sleep
from uuid import uuid4

from wepppy.all_your_base import file_digest
from wepppy.nodb import base
from wepppy.nodb.core import Watershed
from wepppy.nodb.version import CURRENT_VERSION, read_version
from wepppy.query_engine.context import resolve_run_context
from wepppy.query_engine.core import _resolve_dataset_path
from wepppy.query_engine.core import _apply_identifier_aliases
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_path
from wepppy.wepp.interchange._rust_interchange import require_wepppyo3_interchange
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports.helpers import ReportCacheManager
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

ARTIFACTS = Path(__file__).parent
RUN = Path("/wc1/runs/th/thespian-cleanness")
SOURCE = RUN / "wepp/output/interchange/H.wat.parquet"
OUTPUT = ARTIFACTS / ((sys.argv[1] if len(sys.argv) > 1 else "reports_performance_baseline") + ".json")
DISPOSABLE = ARTIFACTS / "reports_performance_outputs" / uuid4().hex[:12]
DISPOSABLE.mkdir(parents=True)
reads = defaultdict(int)
checks = defaultdict(int)
records = []
original_open = Path.open
original_redis = base.redis_nodb_cache_client
helpers = importlib.import_module("wepppy.wepp.reports.helpers")
original_resolve = helpers.resolve_run_context
original_build = HillslopeWatbalReport._build_summary


def named_path(value):
    return isinstance(value, (str, bytes, os.PathLike)) and Path(os.fsdecode(value)).absolute().is_relative_to(RUN)


def readonly_audit(event, args):
    if event == "open" and named_path(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in "wax+")) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError(f"Read-only benchmark blocked {event}: {args[0]}")
    if event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime", "os.rename", "os.link", "os.symlink"}:
        if any(named_path(arg) for arg in args[:2]):
            raise PermissionError(f"Read-only benchmark blocked {event}: {args[:2]}")


sys.addaudithook(readonly_audit)
assert read_version(RUN) >= CURRENT_VERSION, "Do not migrate the named run"
# Disable only this process's Redis cache client: detached acquisition uses the
# real disk decoder without mutating or trusting another process's shared cache.
base.redis_nodb_cache_client = None


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
        value = self.stream.read(*args, **kwargs)
        reads[self.key] += len(value)
        return value


def counted_open(path, *args, **kwargs):
    stream = original_open(path, *args, **kwargs)
    mode = args[0] if args else kwargs.get("mode", "r")
    if mode == "rb" and path.absolute() in dependency_paths:
        return CountedStream(stream, str(path.absolute()))
    return stream


def verified_hash(path):
    checks[str(path)] += 1
    return file_digest.sha256_file(path)


def io():
    return {line.split(":")[0]: int(line.split(":")[1]) for line in Path("/proc/self/io").read_text().splitlines()}


def generation(path):
    info = path.stat()
    return [getattr(info, field) for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")]


def flush():
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")


def measured(name, callback, repeats=1):
    before_reads, before_checks, before_io = dict(reads), dict(checks), io()
    times = []
    value = None
    for _ in range(repeats):
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
    after_io = io()
    record = {"name": name, "repeats": repeats, "seconds": times, "mean_seconds": mean(times),
              "hash_bytes": {path: size - before_reads.get(path, 0) for path, size in reads.items() if size != before_reads.get(path, 0)},
              "hash_checks": {path: count - before_checks.get(path, 0) for path, count in checks.items() if count != before_checks.get(path, 0)},
              "process_rchar_delta": after_io["rchar"] - before_io["rchar"],
              "process_physical_read_bytes_delta": after_io["read_bytes"] - before_io["read_bytes"]}
    if hasattr(value, "shape"):
        record["shape"] = list(value.shape)
    elif isinstance(value, (dict, list, tuple)):
        record["length"] = len(value)
    records.append(record)
    flush()
    print(f"{name}: {record['mean_seconds'] * 1000:.3f} ms", flush=True)
    return value


def resolve_inputs():
    context = resolve_run_context(str(RUN), auto_activate=False, run_interchange=False)
    selected = {}
    for logical in logical_inputs:
        entry = context.catalog.get(logical)
        assert entry is not None
        selected[logical] = _resolve_dataset_path(context.base_dir, entry.fs_path or logical, logical)
    return selected


def resolve_inputs_and_aliases():
    context = resolve_run_context(str(RUN), auto_activate=False, run_interchange=False)
    return {logical: {"path": str(_resolve_dataset_path(context.base_dir, context.catalog.get(logical).fs_path or logical, logical)),
                      "alias_expression": _apply_identifier_aliases("selected_reader", logical, context.catalog)}
            for logical in logical_inputs}


def c09_provenance_observation():
    resolved = resolve_inputs_and_aliases()
    for observation in resolved.values():
        observation["sha256"] = verified_hash(Path(observation["path"]))
    return json.dumps(resolved, sort_keys=True, separators=(",", ":"))


def no_rebuild(report):
    raise AssertionError("Existing cache not admitted; no named-run rebuild permitted")


def resolve_without_activation(*args, **kwargs):
    kwargs["auto_activate"] = False
    return original_resolve(*args, **kwargs)


logical_inputs = [AverageAnnualsByLanduseReport._LOSS_DATASET, AverageAnnualsByLanduseReport._HILLSLOPE_DATASET, AverageAnnualsByLanduseReport._LANDUSE_DATASET]
landuse_inputs = resolve_inputs()
translator_inputs = {logical: Path(pick_existing_parquet_path(str(RUN), logical)) for logical in ("watershed/hillslopes.parquet", "watershed/channels.parquet")}
dependency_paths = {SOURCE, RUN / "watershed.nodb", *landuse_inputs.values(), *translator_inputs.values()}
wat_cache = RUN / "wepp/reports/cache/hillslope_watbal_summary.parquet"
wat_meta = wat_cache.with_suffix(".meta.json")
guarded_paths = dependency_paths | {wat_cache, wat_meta, RUN / "_query_engine/catalog.json", RUN / "nodb.version"}
before = {str(path): generation(path) for path in guarded_paths}
result = {"run": str(RUN), "uid": os.getuid(), "gid": os.getgid(), "disposable_outputs": str(DISPOSABLE),
          "source_sizes": {str(path): path.stat().st_size for path in guarded_paths},
          "landuse_resolver_selected_inputs": {logical: str(path) for logical, path in landuse_inputs.items()},
          "translator_resolver_selected_inputs": {logical: str(path) for logical, path in translator_inputs.items()},
          "measurement_scope": "Actual native readers, actual current cached C08 constructor, detached filesystem NoDb load with process-local Redis disabled; C09 actual query with catalog activation prohibited and disposable cache",
          "filesystem_note": "No OS page-cache drop; cold means digest helper cache cold, not physical-storage cold",
          "source_modules_sha256": {str(Path(module.__file__)): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for module in (sys.modules[HillslopeWatbalReport.__module__], sys.modules[AverageAnnualsByLanduseReport.__module__], file_digest)},
          "measurements": records}
Path.open = counted_open
helpers.resolve_run_context = resolve_without_activation
HillslopeWatbalReport._build_summary = no_rebuild
try:
    native = require_wepppyo3_interchange("hillslope water balance", "hillslope_watbal_wepp_ids", "hillslope_watbal_to_parquet")
    file_digest._digest.cache_clear()
    file_digest._observed_at.cache_clear()
    measured("hwat_digest_first_observation", lambda: verified_hash(SOURCE))
    measured("hwat_digest_during_admission", lambda: verified_hash(SOURCE), 2)
    sleep(1.05)
    measured("hwat_digest_admitting", lambda: verified_hash(SOURCE))
    measured("hwat_digest_settled", lambda: verified_hash(SOURCE), 100)
    wepp_ids = measured("native_hwat_wepp_id_scan", lambda: native.hillslope_watbal_wepp_ids(str(SOURCE)), 3)
    result["source_wepp_id_count"] = len(wepp_ids)
    watershed = measured("watershed_detached_disk_load", lambda: Watershed.load_detached(str(RUN)), 10)
    result["translator_branch"] = "persisted_summary_keys" if watershed._subs_summary is not None and watershed._chns_summary is not None else "parquet_tables"
    translator = measured("actual_translator_factory", watershed.translator_factory, 10)
    result["translator_hillslopes"] = translator.hillslope_n
    result["translator_channels"] = translator.channel_n
    mapping = measured("effective_mapping_for_retained_source_ids", lambda: {int(item): int(translator.top(wepp=int(item))) for item in wepp_ids}, 100)
    measured("mapping_canonical_json", lambda: json.dumps(mapping, sort_keys=True, separators=(",", ":")), 100)

    def c08_provenance_observation():
        checksum = verified_hash(SOURCE)
        observed = Watershed.load_detached(str(RUN)).translator_factory()
        effective = {int(item): int(observed.top(wepp=int(item))) for item in wepp_ids}
        return json.dumps({"sha256": checksum, "mapping": effective}, sort_keys=True, separators=(",", ":"))

    measured("c08_settled_observation_with_disk_hydration", c08_provenance_observation, 20)
    # An isolated hydrated object exercises the established parquet fallback;
    # the named run's persisted summaries are neither edited nor reserialized.
    fallback = Watershed.load_detached(str(RUN))
    fallback._subs_summary = fallback._chns_summary = None
    fallback_translator = measured("isolated_parquet_fallback_translator", fallback.translator_factory, 10)
    result["parquet_fallback_mapping_equals_actual"] = fallback_translator.wepp2top == translator.wepp2top
    measured("existing_c08_cached_report_first", lambda: HillslopeWatbalReport(RUN))
    measured("existing_c08_cached_report_repeat", lambda: HillslopeWatbalReport(RUN), 20)
    measured("existing_c08_cached_parquet_only", lambda: ReportCacheManager(RUN).read_parquet(HillslopeWatbalReport._CACHE_KEY, version="1"), 20)

    generated = object.__new__(HillslopeWatbalReport)
    generated.wd, generated._output_scope = DISPOSABLE / "hwat", "baseline"
    generated.wd.mkdir()
    summary = measured("native_summary_to_disposable_cache", lambda: generated._write_native_summary(native, SOURCE, mapping))
    result["native_summary_equals_existing_rows"] = summary.equals(ReportCacheManager(RUN).read_parquet(HillslopeWatbalReport._CACHE_KEY, version="1"))

    measured("c09_resolve_catalog_and_three_inputs", resolve_inputs, 20)
    result["c09_effective_aliases"] = measured("c09_resolve_catalog_inputs_and_aliases", resolve_inputs_and_aliases, 20)
    measured("c09_three_dependency_hashes_first", lambda: [verified_hash(path) for path in landuse_inputs.values()])
    sleep(1.05)
    measured("c09_three_dependency_hashes_admitting", lambda: [verified_hash(path) for path in landuse_inputs.values()])
    measured("c09_three_dependency_hashes_settled", lambda: [verified_hash(path) for path in landuse_inputs.values()], 100)
    measured("c09_settled_provenance_observation", c09_provenance_observation, 20)
    landuse = object.__new__(AverageAnnualsByLanduseReport)
    landuse.wd = RUN
    dataframe = measured("c09_actual_duckdb_report_query", landuse._build_dataframe, 5)
    (DISPOSABLE / "landuse").mkdir()
    landuse_cache = ReportCacheManager(DISPOSABLE / "landuse")
    landuse_cache.write_parquet(landuse._CACHE_KEY, dataframe, version="1", index=False)
    measured("c09_disposable_cached_report", lambda: AverageAnnualsByLanduseReport(DISPOSABLE / "landuse"), 20)
    measured("translator_small_dependency_hashes_first", lambda: [verified_hash(path) for path in [RUN / "watershed.nodb", *translator_inputs.values()]])
    sleep(1.05)
    measured("translator_small_dependency_hashes_admitting", lambda: [verified_hash(path) for path in [RUN / "watershed.nodb", *translator_inputs.values()]])
    measured("translator_small_dependency_hashes_settled", lambda: [verified_hash(path) for path in [RUN / "watershed.nodb", *translator_inputs.values()]], 100)
finally:
    Path.open = original_open
    helpers.resolve_run_context = original_resolve
    HillslopeWatbalReport._build_summary = original_build
    base.redis_nodb_cache_client = original_redis
    result["named_generations_unchanged"] = {str(path): before[str(path)] == generation(path) for path in guarded_paths}
    result["retained_output_sizes"] = {str(path.relative_to(DISPOSABLE)): path.stat().st_size for path in DISPOSABLE.rglob("*") if path.is_file()}
    flush()
print(json.dumps(result, indent=2))
