"""PF-R02 actual producer baselines and composed lineage-cost discovery.

No production implementation is substituted: composed snapshot/metadata paths
are labeled probe-only costs. All producers parse disposable CLI copies.
"""
from collections import defaultdict
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
from statistics import mean
import sys
from time import perf_counter, sleep
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pyarrow.parquet as pq

from wepppy.all_your_base import file_digest
from wepppy.climates.cligen import ClimateFile
from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService
from wepppy.wepp.interchange import _utils

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'cli_lineage_performance.json'
ROOT = Path('/wc1/batch') / ('qa-cli-lineage-perf-' + uuid4().hex[:12])
ROOT.mkdir()
sources = [Path('/wc1/runs/th/thespian-cleanness/climate/wepp.cli'), Path('/wc1/runs/pl/plastic-bundling/climate/wepp.cli')]
reads = defaultdict(int)
hash_checks = defaultdict(int)
original_open = Path.open
logger = logging.getLogger('cli-lineage-qa')
tracked = set()


def named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and named(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named-run writes in this benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named-run mutations in this benchmark')


sys.addaudithook(audit)


def version(path):
    info = path.stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def fd_version(stream):
    info = os.fstat(stream.fileno())
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


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
    if mode == 'rb' and path.absolute() in tracked:
        return CountedStream(stream, str(path.absolute()))
    return stream


def digest(path, **kwargs):
    hash_checks[str(path)] += 1
    return file_digest.sha256_file(path, **kwargs)


def io():
    return {line.split(':')[0]: int(line.split(':')[1]) for line in Path('/proc/self/io').read_text().splitlines()}


def delta(current, before):
    return {key: value - before.get(key, 0) for key, value in current.items() if value != before.get(key, 0)}


result = {'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(), 'cases': {},
          'scope': 'Actual existing Climate and interchange exports; probe-only coherent snapshot and metadata/readiness composition on disposable copies',
          'cache_note': 'No OS cache drop; copying inputs primes page cache. Helper-cold does not mean cold storage.',
          'module_hashes': {str(Path(module.__file__)): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for module in (sys.modules[ClimateArtifactExportService.__module__], _utils)}}


def flush():
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'benchmark-manifest.json').write_text(json.dumps(result, indent=2) + '\n')


def measured(case, name, callback, repeats=1):
    before_reads, before_hashes, before_io = dict(reads), dict(hash_checks), io()
    times, value = [], None
    for _ in range(repeats):
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
    after_io = io()
    record = {'name': name, 'repeats': repeats, 'seconds': times, 'mean_seconds': mean(times),
              'tracked_read_bytes': delta(reads, before_reads), 'hash_checks': delta(hash_checks, before_hashes),
              'process_rchar_delta': after_io['rchar'] - before_io['rchar'],
              'process_physical_read_bytes_delta': after_io['read_bytes'] - before_io['read_bytes']}
    if hasattr(value, 'shape'):
        record['shape'] = list(value.shape)
    case['measurements'].append(record)
    flush()
    print(f'{case["name"]} {name}: {mean(times)*1000:.3f} ms', flush=True)
    return value


def export(source, wd):
    owner = SimpleNamespace(wd=str(wd), cli_dir=str(source.parent), cli_fn=source.name, logger=logger)
    output = ClimateArtifactExportService().export_cli_parquet(owner)
    if output is None:
        raise RuntimeError('Actual CLI export failed; inspect retained log/output')
    return output


def coherent_snapshot(source, directory):
    directory.mkdir(mode=0o700)
    before = digest(source, use_cache=False)
    snapshot = directory / 'source.cli'
    descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with source.open('rb') as incoming, os.fdopen(descriptor, 'wb') as outgoing:
        opened = fd_version(incoming)
        shutil.copyfileobj(incoming, outgoing, length=1024*1024)
        assert fd_version(incoming) == opened == version(source)
    tracked.add(snapshot)
    assert digest(snapshot, use_cache=False) == before == digest(source, use_cache=False)
    return snapshot, before


try:
    with patch.object(Path, 'open', counted_open):
        for named_source in sources:
            name = named_source.parents[1].name
            case_root = ROOT / name
            case_root.mkdir()
            source = case_root / 'wepp.cli'
            named_before = version(named_source)
            named_hash = file_digest.sha256_file(named_source, use_cache=False)
            shutil.copy2(named_source, source)
            source.chmod(0o600)
            tracked.add(source)
            case = {'name': name, 'named_source': str(named_source), 'copy_source': str(source),
                    'source_bytes': source.stat().st_size, 'measurements': []}
            result['cases'][name] = case
            frame = measured(case, 'actual_cli_parse_peak_intensities', lambda: ClimateFile(str(source)).as_dataframe(calc_peak_intensities=True), 3)
            case['rows'], case['years'], case['parsed_columns'] = len(frame), int(frame.year.nunique()), list(frame.columns)
            produced = measured(case, 'actual_climate_service_export', lambda: export(source, case_root / ('service-' + uuid4().hex[:8])), 3)
            baseline_table = pq.read_table(produced)
            case['service_output_bytes'] = produced.stat().st_size

            def interchange_export():
                directory = case_root / ('interchange-' + uuid4().hex[:8]) / 'climate'
                directory.mkdir(parents=True)
                (directory / source.name).symlink_to(source)
                value = _utils._ensure_cli_parquet(directory, cli_file_hint=source.name)
                if value is None:
                    raise RuntimeError('Actual interchange export failed')
                return value

            interchange = measured(case, 'actual_interchange_export_with_selected_symlink', interchange_export, 3)
            case['both_producers_equal_rows_and_types'] = baseline_table.equals(pq.read_table(interchange), check_metadata=False)
            fast_before = version(interchange)
            measured(case, 'actual_interchange_existing_legacy_fast_path', lambda: _utils._ensure_cli_parquet(interchange.parent, cli_file_hint=source.name), 100)
            case['legacy_fast_path_unchanged'] = fast_before == version(interchange)
            measured(case, 'coherent_snapshot_copy_and_three_verified_digests', lambda: coherent_snapshot(source, case_root / ('snapshot-' + uuid4().hex[:8])), 3)

            def composed_export():
                snapshot, checksum = coherent_snapshot(source, case_root / ('composed-' + uuid4().hex[:8]))
                produced = export(snapshot, snapshot.parent)
                table = pq.read_table(produced)
                proof = {'version': 1, 'selected_cli': 'wepp.cli', 'sha256': checksum,
                         'producer': 'qa_cost_composition', 'interpretation_version': 1, 'qa_probe_only': True}
                metadata = dict(table.schema.metadata or {})
                metadata[b'wepppy_cli_source'] = json.dumps(proof, sort_keys=True).encode()
                candidate = produced.with_name('annotated.parquet')
                pq.write_table(table.replace_schema_metadata(metadata), candidate)
                assert digest(source, use_cache=False) == checksum
                os.replace(candidate, produced)
                return produced

            annotated = measured(case, 'composed_snapshot_export_metadata_publish', composed_export, 3)
            tracked.add(annotated)
            case['composed_rows_and_types_equal'] = baseline_table.equals(pq.read_table(annotated), check_metadata=False)
            case['annotated_bytes'] = annotated.stat().st_size
            case['prototype_metadata_is_not_production_contract'] = True

            def metadata_only():
                with annotated.open('rb') as stream:
                    before = fd_version(stream)
                    metadata = pq.read_schema(stream).metadata
                    assert before == fd_version(stream) == version(annotated)
                return json.loads(metadata[b'wepppy_cli_source'])

            def composed_readiness():
                proof = metadata_only()
                assert proof['selected_cli'] == source.name
                checksum = digest(source)
                assert checksum == proof['sha256']
                return True

            measured(case, 'coherent_parquet_metadata_only', metadata_only, 100)
            file_digest._digest.cache_clear()
            file_digest._observed_at.cache_clear()
            measured(case, 'composed_readiness_helper_cold', composed_readiness)
            measured(case, 'composed_readiness_during_admission', composed_readiness, 2)
            sleep(1.05)
            measured(case, 'composed_readiness_admitting', composed_readiness)
            measured(case, 'composed_readiness_settled', composed_readiness, 100)
            case['named_generation_unchanged'] = named_before == version(named_source)
            case['named_bytes_unchanged'] = named_hash == file_digest.sha256_file(named_source, use_cache=False)
            case['retained_file_bytes'] = {str(path.relative_to(case_root)): path.stat().st_size for path in case_root.rglob('*') if path.is_file() and not path.is_symlink()}
            case['snapshot_modes'] = {str(path.relative_to(case_root)): oct(path.stat().st_mode & 0o777) for path in case_root.rglob('source.cli')}
            flush()
finally:
    flush()
print(json.dumps(result, indent=2))
