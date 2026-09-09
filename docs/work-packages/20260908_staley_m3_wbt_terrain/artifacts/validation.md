# Final validation and reproduction

Execution completed 2026-09-09 UTC. All required gates passed. No branches,
commits, deployment, installed runtime binary, production M3 wiring or live
run artifacts were changed.

## Source and binary provenance

- WEPPpy clean starting revision: `582ddb0f65181eafd32eb6f302de13a8b08fb85e`.
- WBT clean starting revision: `0af47c38356ab12967e209f5b2fde3a8d802348b`.
- Reference clean revision: `2be86e5928cb5d2940f6bfb68193b00722505056`.
- Executed binary: `/home/workdir/weppcloud-wbt/target/release/whitebox_tools`.
- Binary SHA-256: `d4adb49d0e856a587ff996cf695bb71fbacf5669b90e4b526de403aac91d4718`.

[Source hashes](source_hashes.json) include the lockfile, tool, registrations,
shared raster changes, bindings and study harnesses. [Source delta](wbt_source.patch)
records the built changes relative to the WBT starting revision, including new
source files. Reproduction requires these changes, not only the base revision.
The installed `WBT/whitebox_tools` binary was not replaced.

## Gates

From `/workdir/weppcloud-wbt`:

| Command | Result |
| --- | --- |
| `python test_fixtures/staley_m3_resolution/verify.py` | 66 files across six runs verified |
| `cargo check -p whitebox-tools-app` | Passed; existing compiler warnings |
| `cargo test -p whitebox-tools-app` | 152 passed |
| `cargo test -p whitebox_raster` | 42 integration cases and one doc example passed |
| `cargo build --locked -p whitebox-tools-app --release` | Passed; binary above |
| `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py` | Passed |
| `python -m unittest discover -s tests -p 'test_*.py'` | 15 passed |

The Python set includes 11 generated-output/binding regressions, two study
matching tests and two existing wrapper/process tests. CLI coverage includes
analytical descending/internal-maximum/pit cases, aliases and existing outputs,
invalid pointers/cycles/masks/grids/units, terminal NoData, source point/multiband/
zero-scale rejection, NaN/BigTIFF, compressed/uncompressed single-row H/A/
coverage/metadata readback, and preserved legacy D8Pointer georeferencing.
Five new Rust tests cover traversal, tributaries, nesting, coverage, parser,
cycle handling and no-replace publication/write failures.

From `/workdir/wepppy`:

| Command | Result |
| --- | --- |
| `wctl run-pytest tests --maxfail=1` | 7742 passed, 72 skipped, 3106 warnings; 815.73 seconds |
| `wctl doc-lint --path docs/work-packages/20260908_staley_m3_wbt_terrain` | Passed |
| `wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow` | Passed |
| `wctl doc-lint --path docs/adrs/ADR-0052-staley-m3-upstream-terrain.md` | Passed |

Both repository diffs pass whitespace checks. Changed Markdown spelling was
previewed and normalized where appropriate, and local links checked after
archiving. WBT documentation and PROJECT_TRACKER files were also linted with
`markdown-doc lint --path <file>` from the WBT root. `wctl doc-lint` panics
on absolute sibling-repository paths; direct use of the canonical backend
from the sibling root succeeds. Tooling follow-up: reject out-of-root paths
with an actionable error before invoking the backend.
Logs are `/tmp/staley-m3-{final-check,final-cargo-test,raster-tests,release,all-python-tests,wepppy-tests}.log`.
An initial `cargo test -p whitebox-raster` invocation used the directory name;
the actual package ID is `whitebox_raster`, and the corrected gate passed.

## Generated-output evidence

Both binding modules load the current release executable directory explicitly
and execute `d8_upstream_relief` in `tests/test_d8_upstream_relief.py`. The tests
read generated TIFF arrays, masks, CRS/affine, data types and ImageDescription;
wrapper presence or compilation alone was not treated as execution evidence.

The final reference comparison command was:

```bash
cd /workdir/weppcloud-wbt
PYTHONPATH=/workdir/usgs-pfdf /tmp/staley-m3-reference-env/bin/python \
  tools/staley_m3_reference_compare.py \
  --binary /workdir/weppcloud-wbt/target/release/whitebox_tools \
  --output /tmp/staley-m3-terrain-study/reference-built-v4
```

The output directory must be new; use a fresh suffix for repeats. The isolated
reference venv uses installed pfdf 3.0.2/pysheds 0.4 dependencies, with source
selected explicitly by PYTHONPATH. Exact versions and observed results are in
[reference_built_comparison.json](reference_built_comparison.json). WBT yields
H=30 m and A=300 m2 at all three diagnostic outlets. Reference H is 25/35/5 m;
its errors are explained in [reference_parity.md](reference_parity.md).

## Study reproduction

```bash
cd /workdir/weppcloud-wbt
python tools/staley_m3_resolution_study.py \
  --fixtures /workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution \
  --binary /workdir/weppcloud-wbt/target/release/whitebox_tools \
  --output /tmp/staley-m3-terrain-study/study-v4
```

Again use a fresh output path on repetition. The harness requires installed
numpy, rasterio and matplotlib; it adds no runtime dependency. All 78 actual
WBT invocations are in [commands.json](commands.json), including full fixture
paths and controlled preprocessing. Generated rasters, process logs and time
files remain in that external directory. The harness writes the CSVs, plot,
environment and unavailable-case report reproduced here. Study-v3 exactly
matches the independently reviewed study-v1/v2 numerical comparison/scenario
CSVs; only final binary/provenance/timings changed during raster repairs. Final
harnesses explicitly pass `--compress_rasters=false` to remove dependence on
persisted settings; v4 numerical CSVs exactly equal v3 as well.

The 1198-by-1162 grid benchmark used three new-output invocations: 0.307,
0.316 and 0.312 seconds including I/O, peak RSS 108936-108936 KiB. Hardware:
dual Intel Xeon E5-2697 v2 at 2.70 GHz, 48 logical CPUs, MemTotal 131777580 KiB.
Measurements were local warm-cache runs under concurrent load. The terrain
traversal is serial; WBT helper environment was capped at 12 workers.

## Independent review

[Correctness review](20260908_correctness_review.md) and
[security review](20260908_security_review.md) pass with zero unresolved
medium/high findings. Five correctness and two security findings were repaired
and revalidated. Independent checks cover all 24 paired catchment masks and
864 M3 scenarios, plus separately constructed path-walk/rectangular-cell cases.

Approval covers local tooling under stable caller-controlled input files and
output parents. Per-file no-replace publication requires hard-link support;
a whole output set is not transactional. Hostile upload services, deployment,
production identity/mount parity and M3 UI enforcement remain separate scope.
