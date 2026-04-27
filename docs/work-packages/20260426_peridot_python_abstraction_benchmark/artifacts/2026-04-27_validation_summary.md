# Validation Summary (2026-04-27)

## Environment Context

- `confirmed`: WEPPpy commit: `392201222ec4b2ace01d4171d1e30d24a8000239`.
- `confirmed`: Peridot source repo commit: `e09f54c6f729192320e0e14a972d927f996aec9b`.
- `confirmed`: Host: `Linux forest 6.8.0-101-generic x86_64`.
- `confirmed`: CPU: `48` logical CPUs, Intel Xeon E5-2697 v2.
- `confirmed`: Memory at validation time: `125Gi` total, `84Gi` available.
- `confirmed`: WEPPpy vendored `abstract_watershed` SHA256: `82fb989c07b1ec1f6d91ebad2dd38642a7bf5015dae08b0f8e6b575c1a11ce90`.
- `confirmed`: `/home/workdir/peridot/target/release/abstract_watershed` SHA256: `2a22921e81ceff84c3c98a94b08c91b2ea9db365f2d36de9da0238b5f05ecb4d`.
- `confirmed`: Peridot target release binaries were dirty before benchmark execution and were not staged.

## Smoke Commands

### Python Comparator

Command:

```bash
/usr/bin/time -v .venv/bin/python - <<'PY'
from pathlib import Path
from wepppy.topo.watershed_abstraction.watershed_abstraction import WatershedAbstraction
wd = Path('/tmp/peridot-python-benchmark-20260427-0138/python-smoke-fail')
absw = WatershedAbstraction(str(wd / 'dem' / 'topaz'), str(wd / 'watershed'))
absw.abstract(clip_hillslopes=False, verbose=False)
absw.write_slps(channels=1, subcatchments=0, flowpaths=1)
PY
```

Result:

- `confirmed`: Exit status `1`.
- `confirmed`: Failure: `numpy.core._exceptions._UFuncOutputCastingError` in `wepppy/topo/watershed_abstraction/support.py::cummnorm_distance()`.
- `confirmed`: Wall-clock time before failure: `0:01.77`.
- `confirmed`: Max resident set size before failure: `262500 KB`.

### Peridot Comparator

Command:

```bash
/usr/bin/time -v ./wepppy/topo/peridot/bin/abstract_watershed /tmp/peridot-python-benchmark-20260427-0138/peridot-smoke-log --ncpu 4
```

Result:

- `confirmed`: Exit status `0`.
- `confirmed`: Wall-clock time for smoke completion: `0:00.16`.
- `confirmed`: Max resident set size: `62976 KB`.
- `confirmed`: Outputs include `hillslopes.parquet`, `channels.parquet`, `flowpaths.parquet`, `network.txt`, channel slope bundle, eight hillslope slope files, and eight flowpath slope bundles.

## Benchmark Timing Status

`confirmed`: No valid benchmark timing artifact was produced because the Python comparator failed and output parity was not adequate.

`inference`: The Peridot smoke timing is useful only as a health check, not as a Python-vs-Peridot performance result.

`hypothesis`: After comparator remediation, this same fixture can serve as a first smoke benchmark, but representative performance claims will require larger curated workloads and repeated runs.

## Required Validation

The required documentation and whitespace gates were run at package closure:

- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_python_abstraction_benchmark`: `10 files validated, 0 errors, 0 warnings`.
- `git diff --check`: passed with no output.
- `diff -u <file> <(uk2us <file>)`: no package-file spelling diffs; one unrelated existing `PROJECT_TRACKER.md` spelling suggestion was left untouched.

No benchmark helper script was introduced by this package.

## Post-Close Remediation Validation

After the user requested rough benchmark numbers without exact parity, two targeted remediation tests were added for the legacy Python comparator:

- `tests/topo/test_watershed_abstraction_support.py::test_cummnorm_distance_normalizes_integer_distances`
- `tests/topo/test_watershed_abstraction_support.py::test_transform_px_to_wgs_returns_geojson_coordinate_lists`

Validation result:

```text
wctl run-pytest tests/topo/test_watershed_abstraction_support.py
2 passed, 2 warnings
```

Rough benchmark execution result:

- Python comparator: `5/5` repetitions exited `0`.
- Peridot comparator: `5/5` repetitions exited `0`.
- Detailed rough timing is recorded in `2026-04-27_rough_benchmark_after_cummnorm_remediation.md`.
