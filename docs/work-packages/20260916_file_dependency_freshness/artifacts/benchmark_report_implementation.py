"""Actual report provenance build/hit benchmark on a retained disposable copy.

Named inputs are read-only. Full source copies stay under /tmp; compact outputs,
attempt diagnostics, script, JSON and log remain in the work-package artifacts.
Run with wctl exec weppcloud python <this path> [output-stem].
"""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
from statistics import mean
import sys
from tempfile import mkdtemp
from time import perf_counter, sleep
from unittest.mock import patch

import pyarrow.parquet as pq

from wepppy.all_your_base import file_digest
from wepppy.nodb import base
from wepppy.nodb.core import Watershed
from wepppy.wepp.interchange._rust_interchange import require_wepppyo3_interchange
from wepppy.wepp.reports import _cache_freshness as freshness
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport

ARTIFACTS = Path(__file__).parent
NAMED = Path('/wc1/runs/th/thespian-cleanness')
CLONE = Path(mkdtemp(prefix='report-implementation-qa-'))
OUTPUT = ARTIFACTS / ((sys.argv[1] if len(sys.argv) > 1 else 'reports_implementation_performance') + '.json')
RETAINED = ARTIFACTS / 'reports_implementation_outputs' / CLONE.name
RELATIVES = ['wepp/output/interchange/H.wat.parquet', 'watershed.nodb', 'nodb.version',
             'watershed/hillslopes.parquet', 'watershed/channels.parquet',
             'landuse/landuse.parquet', 'wepp/output/interchange/loss_pw0.hill.parquet',
             '_query_engine/catalog.json', 'wepp/reports/cache/hillslope_watbal_summary.parquet',
             'wepp/reports/cache/hillslope_watbal_summary.meta.json']
SOURCES = {CLONE / item for item in RELATIVES if item.endswith('.parquet') and '/cache/' not in item}
reads = defaultdict(int)
checks = defaultdict(int)
native_calls = defaultdict(int)
records = []
original_open = Path.open
original_hash = freshness.sha256_file
native = require_wepppyo3_interchange('hillslope water balance', 'hillslope_watbal_wepp_ids', 'hillslope_watbal_to_parquet')
original_ids = native.hillslope_watbal_wepp_ids
original_summary = native.hillslope_watbal_to_parquet
original_query = AverageAnnualsByLanduseReport._build_dataframe
parquet_fallback = False


def named_path(value):
    return isinstance(value, (str, bytes, os.PathLike)) and Path(os.fsdecode(value)).absolute().is_relative_to(NAMED)


def readonly_audit(event, args):
    if event == 'open' and named_path(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError(f'Blocked named-run write: {args[0]}')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named_path(arg) for arg in args[:2]):
            raise PermissionError(f'Blocked named-run mutation: {event} {args[:2]}')


sys.addaudithook(readonly_audit)


def generation(path):
    info = path.stat()
    return [getattr(info, field) for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')]


before_named = {item: generation(NAMED / item) for item in RELATIVES}
for relative in RELATIVES:
    target = CLONE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(NAMED / relative, target)
catalog_path = CLONE / '_query_engine/catalog.json'
catalog = json.loads(catalog_path.read_text())
original_catalog_root = catalog['root']
# Explicit disposable-fixture workaround for retained stale-root relocation
# failure. Both production query and observation currently use catalog.root.
rebase_catalog = '--preserve-catalog-root' not in sys.argv
if rebase_catalog:
    catalog['root'] = str(CLONE)
    catalog_path.write_text(json.dumps(catalog))
C08_CACHE = CLONE / 'wepp/reports/cache/hillslope_watbal_summary.parquet'
C08_CACHE.chmod(0o600)
baseline_rows = pq.read_table(C08_CACHE).to_pandas()
modules = [sys.modules[HillslopeWatbalReport.__module__], sys.modules[AverageAnnualsByLanduseReport.__module__], freshness]


def module_hashes():
    return {str(Path(module.__file__)): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for module in modules}


result = {'named_run': str(NAMED), 'disposable_source_clone': str(CLONE), 'retained_outputs': str(RETAINED),
          'uid': os.getuid(), 'gid': os.getgid(), 'source_bytes': {item: (CLONE / item).stat().st_size for item in RELATIVES},
          'modules_before': module_hashes(), 'scope': 'Actual report constructors on copied real sources; actual detached Watershed filesystem hydration replaces singleton acquisition only; Redis disabled in this process',
          'filesystem_note': 'No OS cache drop; helper-cold means digest cache cold, not physical storage cold',
          'catalog_rebase_workaround': {'applied': rebase_catalog, 'before': original_catalog_root, 'after': catalog['root'], 'scope': 'disposable fixture only; an applied workaround does not prove restoration compatibility'},
          'measurements': records}


class CountedStream:
    def __init__(self, stream, path):
        self.stream, self.path = stream, path

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def __getattr__(self, key):
        return getattr(self.stream, key)

    def read(self, *args, **kwargs):
        value = self.stream.read(*args, **kwargs)
        reads[self.path] += len(value)
        return value


def counted_open(path, *args, **kwargs):
    stream = original_open(path, *args, **kwargs)
    mode = args[0] if args else kwargs.get('mode', 'r')
    if mode == 'rb' and path.absolute() in SOURCES:
        return CountedStream(stream, str(path.relative_to(CLONE)))
    return stream


def counted_hash(path):
    checks[str(path.relative_to(CLONE))] += 1
    return original_hash(path)


def counted_ids(*args, **kwargs):
    native_calls['id_scan'] += 1
    return original_ids(*args, **kwargs)


def counted_summary(*args, **kwargs):
    native_calls['summary'] += 1
    return original_summary(*args, **kwargs)


def counted_query(report, *args, **kwargs):
    native_calls['landuse_query'] += 1
    return original_query(report, *args, **kwargs)


def acquire_watershed(wd):
    owner = Watershed.load_detached(wd)
    if parquet_fallback:
        owner._subs_summary = owner._chns_summary = None
    return owner


def clear_hashes():
    file_digest._digest.cache_clear()
    file_digest._observed_at.cache_clear()


def io():
    return {line.split(':')[0]: int(line.split(':')[1]) for line in Path('/proc/self/io').read_text().splitlines()}


def delta(current, before):
    return {key: value - before.get(key, 0) for key, value in current.items() if value != before.get(key, 0)}


def measured(name, factory, repeats=1):
    before_reads, before_checks, before_native, before_io = dict(reads), dict(checks), dict(native_calls), io()
    times, statuses = [], []
    report = None
    for _ in range(repeats):
        start = perf_counter()
        report = factory()
        times.append(perf_counter() - start)
        statuses.append(report.cache_status)
    after_io = io()
    record = {'name': name, 'repeats': repeats, 'seconds': times, 'mean_seconds': mean(times),
              'statuses': statuses, 'hash_bytes': delta(reads, before_reads), 'hash_checks': delta(checks, before_checks),
              'native_calls': delta(native_calls, before_native), 'process_rchar_delta': after_io['rchar'] - before_io['rchar'],
              'process_physical_read_bytes_delta': after_io['read_bytes'] - before_io['read_bytes']}
    records.append(record)
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{name}: {mean(times)*1000:.3f} ms; {record["hash_bytes"]}; {record["native_calls"]}', flush=True)
    return report


try:
    with patch.object(Path, 'open', counted_open), patch.object(freshness, 'sha256_file', counted_hash), \
            patch.object(base, 'redis_nodb_cache_client', None), \
            patch.object(Watershed, 'getInstance', side_effect=acquire_watershed), \
            patch.object(native, 'hillslope_watbal_wepp_ids', counted_ids), \
            patch.object(native, 'hillslope_watbal_to_parquet', counted_summary), \
            patch.object(AverageAnnualsByLanduseReport, '_build_dataframe', counted_query):
        clear_hashes()
        built = measured('c08_legacy_upgrade_build', lambda: HillslopeWatbalReport(CLONE))
        result['c08_rows_equal_original'] = built._per_hill_year.equals(baseline_rows)
        result['c08_mode_after_build'] = oct(C08_CACHE.stat().st_mode & 0o777)
        sleep(1.05)
        measured('c08_matching_settled', lambda: HillslopeWatbalReport(CLONE), 20)
        clear_hashes()
        measured('c08_matching_helper_cold', lambda: HillslopeWatbalReport(CLONE))
        measured('c08_matching_during_admission', lambda: HillslopeWatbalReport(CLONE))
        sleep(1.05)
        measured('c08_matching_readmitting', lambda: HillslopeWatbalReport(CLONE))
        measured('c08_matching_after_readmission', lambda: HillslopeWatbalReport(CLONE), 20)
        parquet_fallback = True
        measured('c08_matching_isolated_parquet_fallback', lambda: HillslopeWatbalReport(CLONE), 20)
        parquet_fallback = False
        clear_hashes()
        landuse = measured('c09_new_build', lambda: AverageAnnualsByLanduseReport(CLONE))
        previous_landuse = ARTIFACTS / 'reports_performance_outputs/09b0f891f7e7/landuse/wepp/reports/cache/average_annuals_by_landuse.parquet'
        result['c09_rows_equal_native_baseline'] = landuse._dataframe.equals(pq.read_table(previous_landuse).to_pandas())
        c09_cache = CLONE / 'wepp/reports/cache/average_annuals_by_landuse.parquet'
        result['c09_first_creation_mode'] = oct(c09_cache.stat().st_mode & 0o777)
        sleep(1.05)
        measured('c09_matching_admitting', lambda: AverageAnnualsByLanduseReport(CLONE))
        measured('c09_matching_settled', lambda: AverageAnnualsByLanduseReport(CLONE), 20)
        clear_hashes()
        measured('c09_matching_helper_cold', lambda: AverageAnnualsByLanduseReport(CLONE))
        pressure = CLONE / 'digest-pressure'
        pressure.mkdir()
        pressure_paths = [pressure / f'{index:03d}.bin' for index in range(512)]
        for index, path in enumerate(pressure_paths):
            path.write_bytes(index.to_bytes(4, 'big'))
            file_digest.sha256_file(path)
        sleep(1.05)
        for path in pressure_paths:
            file_digest.sha256_file(path)
        result['digest_cache_after_512_pressure_paths'] = {
            'observations': file_digest._observed_at.cache_info()._asdict(),
            'digests': file_digest._digest.cache_info()._asdict(),
        }
        measured('c08_matching_after_digest_eviction', lambda: HillslopeWatbalReport(CLONE))
        measured('c09_matching_after_digest_eviction', lambda: AverageAnnualsByLanduseReport(CLONE))
finally:
    result['named_generations_unchanged'] = {item: generation(NAMED / item) == before_named[item] for item in RELATIVES}
    result['modules_after'] = module_hashes()
    RETAINED.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CLONE / 'wepp/reports/cache', RETAINED / 'cache', dirs_exist_ok=True)
    result['output_files'] = {str(path.relative_to(RETAINED)): {'bytes': path.stat().st_size, 'mode': oct(path.stat().st_mode & 0o777)} for path in RETAINED.rglob('*') if path.is_file()}
    result['output_directory_modes'] = {str(path.relative_to(RETAINED)): oct(path.stat().st_mode & 0o777) for path in RETAINED.rglob('*') if path.is_dir()}
    result['attempt_statuses'] = [json.loads(path.read_text()) for path in RETAINED.rglob('status.json')]
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
