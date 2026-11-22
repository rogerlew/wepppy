# Roads controller test refactor validation

## Baseline

The baseline was `782552bde21186e2327caa3540a16ce943f8cb27` with source
tree `1bd6ce6f5c363860b4a225d2c2451c23aae1a7bf`. The isolated Python-profile
runner passed all 92 cases in 23.00 seconds. Local receipt
`c390d98d335648b99f51a89dddb97dcf` reports pytest exit 0 and an empty source
change list. A second run on the same source tree retained JUnit results and
passed all 92 cases.

From the repository root, run each command on its respective source revision.

```bash
wctl run-pytest --profile python -- tests/nodb/mods/test_roads_controller.py -q --junitxml=.wctl-test-runs/roads-controller-before.xml
wctl run-pytest --profile python -- tests/nodb/mods/roads_controller -q --junitxml=.wctl-test-runs/roads-controller-after.xml
wctl run-pytest --profile python -- tests/nodb/mods/roads_controller tests/weppcloud/test_configuration.py --collect-only -q
```

## Quality measurements

Use `analyze_python_text` from `tools/code_quality_observability.py` with
Radon 6.0.1. The measurement counts nonblank, noncomment source lines, maximum
function line span, and maximum cyclomatic complexity. Red thresholds are
1,200, 150, and 30, respectively.

| File | Source lines | Longest function | Max complexity |
| --- | ---: | ---: | ---: |
| `test_roads_controller.py` (baseline) | 3,543 (red) | 285 (red) | 41 (red) |
| `__init__.py` | 1 (green) | — | — |
| `_support.py` | 119 (green) | 26 (green) | 3 (green) |
| `conftest.py` | 47 (green) | 48 (green) | 1 (green) |
| `test_configuration.py` | 358 (green) | 45 (green) | 9 (green) |
| `test_inspection.py` | 312 (green) | 74 (green) | 18 (yellow) |
| `test_native_files.py` | 241 (green) | 39 (green) | 14 (green) |
| `test_parameterization.py` | 267 (green) | 32 (green) | 12 (green) |
| `test_prepare.py` | 414 (green) | 125 (yellow) | 17 (yellow) |
| `test_run_channel.py` | 366 (green) | 110 (yellow) | 21 (yellow) |
| `test_run_trace.py` | 372 (green) | 135 (yellow) | 17 (yellow) |
| `test_run_unrutted.py` | 553 (green) | 146 (yellow) | 29 (yellow) |

Total source lines fell from 3,543 to 3,050. Every replacement module is
below all three red thresholds. The package initializer has no functions.

`uvx --offline ruff check --select F,I tests/nodb/mods/roads_controller`
passed. Static comparison found the same 63 test definitions, decorators,
module markers, and 31 `pytest.raises` calls.

## Independent review

The reviewer compared the 53 mechanically moved cases and the ten cases with
orchestration setup changes. The review checked prepared GeoJSON content,
baseline and raster fixture differences, error injection, and artifact
readback. The directory-scoped accounting fixture remains opt-in.

The 398 assertions reachable under the original setup were preserved. Three
assertions were removed with a dormant callback in
`test_run_roads_wepp_maps_hillslopes_and_runs_watershed`. The baseline
unconditionally replaced its monkeypatch before invoking the controller. The
effective PASS writer and its artifact assertions were preserved.

The source review accepted the change with no unresolved findings.

## Focused runtime parity

The candidate passed all 92 cases in 10.50 seconds. Local receipt
`4ebe6042a82e49edb6c8a937f0f33f1d` reports pytest exit 0 and an empty source
change list. The baseline and candidate each emitted two dependency
deprecation warnings.

Comparing the retained JUnit reports by test name, parameter suffix, and
outcome yielded identical results for all 92 cases. The SHA-256 digest of
the sorted `name<TAB>outcome<LF>` records is
`53f308292e39b4eaf0c36c6ce0d9637f76da886ef56ba18425962e9f931a378b`.
The directory split changes the file portion of each pytest node ID.

Combined collection passed with 144 cases, including the 92 Roads cases and
52 WEPPcloud configuration cases. Local receipt
`f04fce73304c4c9fa85a6ebd406bd007` reports pytest exit 0 and an empty source
change list. The full suite was outside the requested validation scope.

All 11 staged test files matched the content hashes in both candidate
receipts. `wctl --project-dir "$PWD" doc-lint` scanned all six staged Markdown
files with zero findings. `git diff --cached --check` passed.
