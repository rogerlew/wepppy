# Independent SSURGO/STATSGO builder regression review

Status: bounded builder/downstream parity approved; no discrepancy found.
Reviewer: independent `source_contract_review`, 2026-09-14 local time.
This supplies the generated-file evidence required by [the regression plan](soil_regression_plan.md), not full production acceptance.

## Revisions and method

Base: `97800607c30c0979d422f99b1e2c65f1b8a89ab5`.
Candidate HEAD: `b998d44e2126889e8014cc83230d51f6b89e9c82`; candidate source bytes are independently pinned.
All 39 protected Python/template files inspected under SSURGO/soil utilities,
NoDb soils/WEPP preparation, and the WEPP runner match the base exactly.
[Protected identities](soil_builder_validation_20260914_r6/protected_identities.json)
and [environment/fixture identities](soil_builder_validation_20260914_r6/environment.json)
retain hashes, Python/SQLite/package versions, native NumPy/DuckDB identities,
and Rosetta source/model database hashes. No WBT or WEPP executable was invoked.

[The validation script](soil_builder_parity.py) executes retained baseline and
candidate `ssurgo.py`, `wepp.py`, and `wepp_runner.py` module source in separate
processes, with canonical module identities for real process-pool execution.
The installed resource paths and byte-identical protected dependencies are shared;
this is deliberately a bounded original-builder comparison, not a complete
baseline application checkout. No soil-building implementation is stubbed.

Each original `SurgoSoilCollection` receives its own frozen SQLite copy, calls
`makeWeppSoils(max_workers=1)` and `writeWeppSoils(write_logs=True)`, and requires
zero missing-key synchronization. Missing-record fetches raise immediately;
an Internet socket audit guard also blocks import-time Redis connections.
SQLite access during builder execution is restricted to the validation directory.
Rosetta uses its installed read-only model database. No live project or shared
soil cache is opened for writing; no source acquisition occurs.

The output clock alone is fixed at `2026-09-14T12:00:00Z`. Raw summary JSON is
retained; its `soils_dir` is compared as the relative `soils` directory because
baseline/candidate output roots differ. No numerical fields, file headers,
parameter values, or generated soil/run bytes are normalized away.

## Results

[Final comparison](soil_builder_validation_20260914_r6/comparison.json): all eight
cases match across 16 builder executions. Per revision: 22 built `.sol` files,
44 downstream prepared `.sol` files, and 44 real `make_hillslope_run` `.run` files.
All 296 retained payload hashes were rechecked after worker exit.

| Panel | Source mode | Selected component / result |
| --- | --- | --- |
| Existing reclaimed Fairpoint synthetic fixture, three MUKEYs | Both `use_statsgo=False/True` | Fairpoint major component; one retained layer and restrictive index 1 |
| Same fixture, missing dominant-component sand/clay | Both modes | Existing WEPP texture defaults preserved; same component and restriction behavior |
| Same fixture, dominant-component sand = 0 | Both modes | WEPP rejects dominant component and selects Bethesda minor component; raw dominant depth remains M3-valid at 152 cm |
| Historical bundled SSURGO, MUKEY 2396743 | `use_statsgo=False` | COKEY 26257945, Redraven, five layers |
| Historical bundled STATSGO, MUKEYs 661787 / 661951 / 661956 | `use_statsgo=True` | COKEYs 14194570 / 14196323 / 14196362; four / four / three layers |

The bundled historical databases are read in single read-only transactions to
extract complete selected-key table subsets. Source hashes are checked before
and after extraction. Their exact historical collection versions are unknown;
the [source inventory](soil_builder_validation_20260914_r6/inputs/bundled_source_provenance.json)
does not infer present SDA lineage. These STATSGO tabular soils are distinct from
the USGS original THICK fallback raster used by M3.

Compared fields include selected component metadata, every retained horizon
attribute, validity masks, layer counts, restrictive-layer index/conductivity,
build notes/logs, SoilSummary fields, source-label sidecars, cache schema and
committed table rows. All copied cache rows/schemas and frozen input DB bytes
remain unchanged. SQLite WAL/shared-memory housekeeping files are not stable
soil payloads and are excluded only from payload hashes; committed records are
compared explicitly. The experiment does not ignore WAL-backed source changes.

Downstream calls use the real `prep_soil` worker for both default parameters and
an explicit clipping/kslast/initial-saturation treatment, then write real hillslope
run files and verify their soil references. Both numerical file contents and
`.run` bytes match. [Baseline](soil_builder_validation_20260914_r6/base/results.json)
and [candidate](soil_builder_validation_20260914_r6/candidate/results.json) contain
the detailed comparisons and relative artifact hash inventories.

## Existing regression gate

Executed independently twice; final retained result: **78 passed, 5 skipped**.
The five skips are explicitly network-dependent SDA integration tests.
Existing fallback, serialization, masked-valid raster, restrictive-layer,
cache, NoDb gridded creation, reporting and parquet tests ran.

```bash
wctl run-pytest tests/soils tests/nodb/test_soils_ssurgo_cache.py \
  tests/nodb/test_soils_report.py tests/nodb/test_soils_gridded_root_creation.py \
  tests/nodb/test_soils_parquet_area_fallback.py --maxfail=1 \
  --junitxml=docs/work-packages/20260914_staley_m3_integration/artifacts/soil_builder_validation_20260914_r5/existing_soil_regression.xml
```

[JUnit evidence](soil_builder_validation_20260914_r5/existing_soil_regression.xml)
retains individual tests and skip reasons. Fork-from-multithreaded-process and
dependency deprecation warnings remain; no warning was treated as a pass for an
otherwise failed comparison.

## Retention, reproduction and limits

Final visible local root:
`docs/work-packages/20260914_staley_m3_integration/artifacts/soil_builder_validation_20260914_r6/`.
It retains `inputs/*.sqlite`, `inputs/*.json`, `source/{base,candidate}/`,
`{base,candidate}/<panel>/<mode>/soils/`, the copied `tabular.sqlite` and sidecar,
and `<treatment>/wepp/runs/*`. Failed/preliminary roots remain beside it:
`soil_builder_validation_20260914/` and `_r2/`, `_r3/`, `_r4/`, `_r5/` suffixes.
Each has an explicit `status.json`; these are not silently promoted to final evidence.

The local `.gitignore` omits generated trial payloads and duplicate source copies
from Git only. Compact status, final input rows/schema, result/hash inventories,
environment, logs and test evidence remain versioned. This does not hide local
files or alter project browser/archive policy. No trial evidence was deleted.

Reproduce with a new visible output directory, never overwrite a retained trial:

```bash
wctl run-python docs/work-packages/20260914_staley_m3_integration/artifacts/soil_builder_parity.py \
  --output docs/work-packages/20260914_staley_m3_integration/artifacts/soil_builder_validation_20260914_repeat
```

Limits: small frozen panels, not exhaustive continental coverage or current SDA
delivery. Full NoDb spatialization, external donor/substitution assignment,
project rebuild, WEPP simulation, and M3 failure/cancellation/publication/retry
noninterference are not executed by this script. In particular it does not itself
prove unchanged live `soils.nodb`, `rusle.nodb`, RUSLE records or existing project
`wepp/runs/*`; the production acceptance's protected-source inventory and runtime
failure tests must supply that complementary evidence. No production code was edited.
