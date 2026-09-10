# Independent QA review

Date: 2026-09-09 Pacific. Reviewer: secondary QA agent, independent of the
implementation and primary correctness/security reviewers. Scope:
`rainfall_io.py`, `rainfall.py`, `results.py`, and the two new
`tests/nodb/mods/test_postfire_debris_flow_{rainfall,results}.py` modules.
Runtime code was not modified by this reviewer.

## Verdict and findings

**QA gate: pass, including the approved R02 behavior.** Q01 is closed; no
medium/high QA findings remain. R02 approval is recorded in
[ADR-0062](../../../adrs/ADR-0062-staley-local-rainfall-results.md) and the
[decision register](decision_register.md). Package-wide acceptance remains
the parent's responsibility. The three-module organization is
cohesive: bounded local reads, Climate adapters, then persisted results/queries.
No new dependencies, speculative multi-model framework, global test stubs, or
silent exception recovery were introduced. The primary review's findings are
tracked in [correctness_review.md](correctness_review.md); this review does not
duplicate their scientific acceptance judgments.

### Q01 — Medium: protect the new semantic validators with direct-file tests

At the initial QA snapshot,
[test_postfire_debris_flow_results.py](../../../../tests/nodb/mods/test_postfire_debris_flow_results.py)
tested table tampering through hash rejection. It did not yet exercise the new
manifest/row validators with matching hashes. Predictor mutations likewise
covered only initial status/coverage guards, and
[test_postfire_debris_flow_rainfall.py](../../../../tests/nodb/mods/test_postfire_debris_flow_rainfall.py)
did not mutate NOAA data type or estimate-table headings.

Smallest closure: retain coherent valid fixture baselines; mutate one semantic
invariant per case; refresh the corresponding table/manifest digest; assert
`RainfallError.code` and a useful diagnostic that identifies the intended
guard. Cover NOAA depth/confidence metadata, K/grid/WBT inconsistencies, result
units/identity, duplicate or incomplete rows, and forward/inverse inconsistencies.
Keep source-hash rejection as a separate test. This prevents an earlier hash
failure or invalid fixture from making semantic-validation tests pass falsely.
Exercise successful empty/dry result opening and partial predictor states as
well as rejection cases. Add a mixed available/unavailable query case to prove
nulls remain last in both sort directions and ordinal ties remain deterministic.

**Closed:** durable tests now cover coherent K/grid/WBT and F/S mutations,
NOAA data type/heading rejection, rehashed event semantics, invalid manifest
units/identity, missing design/inverse combinations, and changed inverse values.
The inverse-value mutation preserves unit consistency so it reaches the scalar
guard. Manifest/design/inverse cases assert diagnostic messages and error codes;
table hashes and counts are refreshed to reach semantic checks. Empty catalogs,
partial S/F, nonunique/unavailable inverse results, and mixed-null sorting in both
directions also pass. Existing source-hash rejection remains separate.

### Q02 — Low, non-blocking: keep row validation easy to audit

[results.py](../../../../wepppy/nodb/mods/postfire_debris_flow/results.py),
`_validate_rows`, combines shared numerical/status validation, scalar consistency,
three table-specific schemas, event identity, and completeness bookkeeping in
one function. Several compact conditional expressions obscure which table
contract applies. This is readable enough for the fixed M1 scope, but future
extensions would make regressions harder to localize.

Smallest follow-up: with Q01 coverage in place, extract the event, design,
and inverse row checks into named private helpers, leaving shared checks and
cross-row bookkeeping in the coordinator. Expand compound conditions and use
descriptive local names; preserve the current validation order and errors.
No generic validator framework or additional dependency is warranted.

### Q03 — Low, non-blocking: add row context to semantic errors

[rainfall_io.py](../../../../wepppy/nodb/mods/postfire_debris_flow/rainfall_io.py),
`validate_predictors`, and `results.py`, `_validate_rows`, fail explicitly and
preserve stable error codes. Several diagnostics, such as `Invalid result
number`, omit the table, field, or event/scenario identity. Locating one bad row
in a large retained bundle therefore requires a second manual scan.

Smallest follow-up: include bounded local context in existing messages (table,
field, and ordinal or scenario) without changing codes or dumping source rows.
This improves operator diagnosis without adding logging infrastructure.

## Test quality and evidence

Positive coverage already uses temporary JSON, CSV, and Parquet files, fixed
controlled fixtures, explicit unit markers, duplicate dates, zero/missing
intensities, shared recurrence context, deterministic pagination, and successful
forward/inverse composition. The source-change test uses a narrow injection at
the recheck boundary while still modifying a real input file. No collection-time
`sys.modules` stubs or network dependencies were added.

The scalar helper is an appropriate composition oracle; it is not an independent
test of the published coefficients. The retained reproduction script supplies a
separate hand-equation check. The predictor fixture explicitly identifies its
synthetic artifact bytes and does not claim raster/scientific acceptance.

The R02 follow-up review covers the final adapter/reader changes and seven new
cases. The four controlled rank-boundary cases use explicit expected indices
`9/4/1/0`, independently of the rank helper. Counts 0, 1, 9, and 10 distinguish
an empty series, unsupported ranks, and the first supported sample count for
rank 9. They verify the retained rank/count, exact supported accumulation,
unaffected 30-minute results, subset parity, accepted clamped CSV values, and
rejection after changing a CSV value. Existing file-parser tests cover CSV
decoding; these cases deliberately isolate the adapter's parity contract.

The sparse-bundle regression uses actual Parquet input and all three result
families. It reopens the completed bundle, queries ten events, checks all twelve
design/six inverse rows, confirms null rainfall/probability for unsupported
ranks, and retains available other durations and the distinct zero-sample
reason. The change adds no new abstraction or test stub. No further QA finding
was identified.

The final correctness follow-up adds a small reader check requiring every CLI
design row retaining rainfall to have a supported rank, including rows whose
probability is unavailable because predictors are missing. Its two regressions
start from valid generated rows, change only the rank to the positive sample
count, refresh hashes, and assert the specific diagnostic and `invalid_input`
code. Both complete and missing-predictor cases reach the intended semantic
guard. This closes the reverse-direction consistency gap without broadening
the implementation structure or leaving a new QA finding.

Reviewed the parent's final canonical focused run in
`/tmp/staley-rainfall-approved-final-focused.log`: **62 passed**, two dependency
deprecation warnings, 10.13 seconds. This run includes the final JSON overflow
guard, approved R02 behavior, and retained-rainfall rank validation:

```bash
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_rainfall.py tests/nodb/mods/test_postfire_debris_flow_results.py --maxfail=1
```

Full-suite and genuine-source performance evidence remain package-level gates.
This artifact passes scoped documentation lint with no spelling changes.

Reviewed file SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `rainfall_io.py` | `a08f89fc746c631dcc1ae033c42e4f7f86bdaf4eadaa90adc7804a442642e1bd` |
| `rainfall.py` | `fd1da7a6ec7ce21268f7089b90d083ebfade9f66f49937396a59230531efa3da` |
| `results.py` | `e8ab818669c41b039be8ea0256bf32e42dc5d263186e4319fb877b1e5b6f985a` |
| `test_postfire_debris_flow_rainfall.py` | `b63d63aa5b4cc4dcc06d82d3caec0dd36515cd6a532ad726418d5e592da4f758` |
| `test_postfire_debris_flow_results.py` | `e287d32057a6390936fc898b9228514215d8d25d9450510943f492638f3280e1` |

## Residual scope

R02 now returns explicit unavailable rows for unsupported CLI ranks under the
owner-approved contract. It changes the local adapter only; the Climate export
and its clamped values remain intact. QA sign-off does not establish production
NoDb/RQ/UI integration or alter the trusted-local snapshot boundary.

Queries materialize the selected Arrow table as Pandas on each list call.
Assess the measured representative catalog latency before any optimization;
this review recommends no new storage/query dependency. A frozen `ResultCatalog`
contains a mutable manifest dictionary, so callers must treat the returned
catalog as a read-only snapshot; query response metadata is detached.

Q02 and Q03 are non-blocking quality follow-ups, not authorization to change
scientific policies, file-boundary assumptions, or production integration.
