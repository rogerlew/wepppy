"""Profile actual settled lineage validation after a retained benchmark miss."""
import cProfile
import hashlib
import io
import json
from pathlib import Path
import pstats
from statistics import mean
import sys
from time import perf_counter, sleep

from wepppy.climates import cli_parquet
from wepppy.nodb.mods.postfire_debris_flow import production, rainfall_io

ARTIFACTS = Path(__file__).parent
suffix = '_' + sys.argv[1] if len(sys.argv) > 1 else ''
inputs = json.loads((ARTIFACTS / 'cli_lineage_implementation_performance_final.json').read_text())
output = {'scope': 'Actual production functions, no file wrappers; warm caches; cProfile separately adds instrumentation cost',
          'cases': {}, 'module_hashes': {str(Path(m.__file__)): hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in (cli_parquet, production, rainfall_io)}}
for name, case in inputs['cases'].items():
    source, parquet = Path(case['source']), Path(case['output'])
    root = source.parent.parent
    assert root.is_relative_to('/wc1/batch')
    files = {'active_cli': source, 'cli': parquet}
    records = {key: production.signature(root, path) for key, path in files.items()}

    def predicate():
        assert production._cli_lineage_current(root, files, records, {})

    def metadata():
        with rainfall_io.open_local(parquet) as stream:
            assert cli_parquet._read_proof(stream, rainfall_io.MAX_TEXT)[0]

    production._digest_version.cache_clear()
    production._digest_observed_at.cache_clear()
    predicate()
    sleep(1.05)
    predicate()
    checks = {}
    callbacks = {'full_predicate': predicate, 'metadata_with_local_opener': metadata,
                 'cached_cli_digest_with_local_opener': lambda: production.cached_digest(source, local=True),
                 'selection': lambda: cli_parquet._selection(root, source),
                 'both_post_read_signatures': lambda: (production.signature(root, parquet), production.signature(root, source)),
                 'both_initial_safe': lambda: (production.safe(root, parquet), production.safe(root, source))}
    for label, callback in callbacks.items():
        elapsed = []
        for _ in range(100):
            started = perf_counter()
            callback()
            elapsed.append(perf_counter() - started)
        checks[label] = {'mean_seconds': mean(elapsed), 'seconds': elapsed}
        print(name, label, f'{mean(elapsed)*1000:.3f} ms', flush=True)
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(100):
        predicate()
    profiler.disable()
    report = io.StringIO()
    stats = pstats.Stats(profiler, stream=report).strip_dirs().sort_stats('cumulative')
    stats.print_stats(35)
    report_path = ARTIFACTS / f'cli_lineage_profile_{name}{suffix}.txt'
    report_path.write_text(report.getvalue())
    checks['profile'] = str(report_path)
    output['cases'][name] = checks
    (ARTIFACTS / f'cli_lineage_predicate_profile{suffix}.json').write_text(json.dumps(output, indent=2) + '\n')
    print(report.getvalue(), flush=True)
