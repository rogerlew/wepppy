"""Reproducible synthetic exceptional/normal-path timing; prints no values."""
from pathlib import Path
import io
import json
import logging
import os
from statistics import median
import tempfile
import time

from wepppy.observability import safe_traceback as safe
from wepppy.observability.safe_logging import install

with tempfile.TemporaryDirectory() as directory:
    specs = []
    for index in range(24):
        name = f'F5_BENCH_{index}'
        path = Path(directory) / name
        path.write_text(f'synthetic-benchmark-value-{index}-392ad')
        os.environ[name + '_FILE'] = str(path)
        specs.append(safe.SecretSourceSpec(name, name + '_FILE', required=True))
    profile = safe.SecretSourceProfile('benchmark', tuple(specs))
    exc = ValueError('ordinary context ' * 480 + 'synthetic-benchmark-value-17-392ad')
    durations = []
    for _ in range(105):
        start = time.perf_counter()
        safe.render_exception(exc, source_profile=profile)
        durations.append(time.perf_counter() - start)
    install(profile)
    source_opens = []
    import sys
    sys.addaudithook(lambda event, args: source_opens.append(args[0])
                     if event == 'open' and isinstance(args[0], str) and args[0].startswith(directory) else None)
    output = io.StringIO()
    logger = logging.getLogger('f5-benchmark')
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(output))
    logger.setLevel(logging.INFO)
    start = time.perf_counter()
    for _ in range(10_000):
        logger.info('ordinary progress')
    normal_elapsed = time.perf_counter() - start
    assert not source_opens
    print(json.dumps({'source_count': 24, 'diagnostic_chars': len(str(exc)),
                      'render_median_ms': median(durations[5:]) * 1000,
                      'render_max_ms': max(durations[5:]) * 1000,
                      'normal_records': 10000, 'normal_source_reads': len(source_opens),
                      'normal_total_ms': normal_elapsed * 1000}))
