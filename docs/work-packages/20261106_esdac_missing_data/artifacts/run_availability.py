"""Build every sampled location and retain parsed-artifact availability evidence.

Run in rq-worker with --output in an isolated directory. No project is modified.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path('/workdir/wepppy')
sys.path.insert(0, str(ROOT))
PACKAGE = ROOT / 'docs/work-packages/20261106_esdac_missing_data'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def init_worker(baseline):
    if baseline:
        # Load the actual pre-change modules in an isolated diagnostic process.
        import wepppy.eu.soils.esdac as package
        for name in ('quality', 'esdac'):
            module_name = f'wepppy.eu.soils.esdac.{name}'
            code = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                f'{baseline}:wepppy/eu/soils/esdac/{name}.py'], text=True)
            spec = importlib.util.spec_from_loader(module_name, loader=None)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            exec(compile(code, module_name, 'exec'), module.__dict__)
            setattr(package, name, module)
        package.ESDAC = sys.modules['wepppy.eu.soils.esdac.esdac'].ESDAC


def build_one(task):
    from wepppy.eu.soils.esdac import ESDAC
    from wepppy.eu.soils.esdac.quality import ESDACSoilBuildError
    from wepppy.wepp.soils.utils import WeppSoilUtil
    sample, output = task
    directory = Path(output) / 'soils' / str(sample['sample_id'])
    directory.mkdir(parents=True, exist_ok=False)
    result = dict(sample)
    started = time.monotonic()
    try:
        key, horizon, _ = ESDAC().build_wepp_soil(sample['lng'], sample['lat'], str(directory))
        path = directory / f'{key}.sol'
        parsed = WeppSoilUtil(str(path))
        ofe = parsed.obj['ofes'][0]
        # Numeric artifact content, not successful return or file existence.
        import math
        rows = ofe['horizons']
        assert rows and all(math.isfinite(float(v)) for row in rows for v in row.values())
        assert all(float(row['bd']) > 0 for row in rows)
        depths = [float(row['solthk']) for row in rows]
        assert depths == sorted(set(depths)) and depths[0] > 0
        assert all(0 <= float(row['wp']) <= float(row['fc']) <= 1 for row in rows)
        result.update(outcome=horizon.quality_result.outcome,
            diagnostics=horizon.quality_result.as_dict()['diagnostics'],
            soil_key=key, artifact=str(path.relative_to(output)), sha256=digest(path),
            physical=ofe)
    except ESDACSoilBuildError as exc:
        result.update(outcome='rejected', diagnostics=exc.result.as_dict()['diagnostics'])
    except Exception as exc:  # Diagnostic boundary: retain every unexpected failure, never count as success.
        result.update(outcome='unexpected_error', error_type=type(exc).__name__, error=str(exc))
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--samples', type=int, default=1000)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--baseline-ref')
    args = parser.parse_args()
    candidate_hashes = {name:digest(ROOT / f'wepppy/eu/soils/{name}')
        for name in ('esdac/quality.py', 'esdac/esdac.py', 'soil_build.py')}
    args.output.mkdir(parents=True, exist_ok=False)
    if args.manifest:
        manifest = json.loads(args.manifest.read_text())
    else:
        from tools.eu_invalid_soil_search import build_manifest
        path = build_manifest(sample_count=args.samples, seed=20261106,
            output=args.output / 'manifest.json')
        manifest = json.loads(path.read_text())
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    samples = manifest['samples']
    counts = Counter()
    reasons = Counter()
    strata = defaultdict(Counter)
    results = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             initargs=(args.baseline_ref,)) as pool:
        with (args.output / 'results.jsonl').open('w') as stream:
            for result in pool.map(build_one, [(sample, str(args.output)) for sample in samples]):
                results.append(result)
                counts[result['outcome']] += 1
                for diagnostic in result.get('diagnostics', []):
                    reasons[f"{diagnostic['severity']}:{diagnostic['code']}:{diagnostic['field']}"] += 1
                # Geographic bins are explicit degrees, independent of raster CRS.
                cell = f"lon{int(result['lng']//10)*10}:lat{int(result['lat']//10)*10}"
                strata[cell][result['outcome']] += 1
                stream.write(json.dumps(result, allow_nan=False)+'\n')
                stream.flush()
                if len(results) % 50 == 0:
                    print(len(results), dict(counts), flush=True)
    summary = {
        'sample_count': len(samples), 'counts': dict(counts), 'reasons': dict(reasons),
        'geographic_bins_10_degrees': dict(strata),
        'bounds': {axis: [min(r[axis] for r in results), max(r[axis] for r in results)] for axis in ('lng','lat')},
        'hostname': socket.gethostname(), 'uid': os.getuid(),
        'baseline_ref': args.baseline_ref,
        'git_head': subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        'candidate_sha256': candidate_hashes,
        'source_unchanged': candidate_hashes == {name:digest(ROOT / f'wepppy/eu/soils/{name}') for name in candidate_hashes},
        'manifest_sha256': digest(args.output / 'manifest.json'),
        'results_sha256': digest(args.output / 'results.jsonl'),
    }
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    print(json.dumps(summary, indent=2), flush=True)

if __name__ == '__main__':
    main()
