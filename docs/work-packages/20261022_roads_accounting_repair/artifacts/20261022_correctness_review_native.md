# Final native Roads accounting correctness review

## Verdict and scope

**PASS for the reviewed native implementation.** No unresolved high or medium
native correctness findings remain. This is implementation review, not production
deployment approval or certification of the package's remaining operational gates.

Reviewer: independent `accounting_contract_review` agent, 2026-10-22.
Runtime code and tests were read only. The reviewer authored this artifact and
the earlier contract-review artifact, but did not implement the native changes.
Contract ancestor: `83f7410e852575483418590919a3bde2dbf19f4a`.

Reviewed `wepppyo3/wepp_interchange/src/totalwatsed/roads.rs`, the shared
`totalwatsed.rs` extraction, Roads-specific weighted PASS changes in
`hill_pass_combine.rs`, their Python API boundaries, and retained UM1 artifacts
against the [approved contract](../../../schemas/roads-water-accounting-contract.md).
WEPPpy orchestration and report admission have a separate
[security/integration review](20261022_security_review.md).

## Findings and disposition

| Finding | Severity | Final disposition |
| --- | --- | --- |
| All target/day accumulators were retained simultaneously | High | Resolved: equivalent reporting accumulates and writes one target at a time; only watershed daily totals persist across targets. Source inspection confirms bounded target accumulation; this is not a measured peak-memory claim. |
| Nonexistent output paths through symlinked parents could alias and overwrite TotalWatSed with accounting WAT | High | Resolved: destination identities canonicalize parents before comparison. The release regression rejects the alias before publication. |
| Optional SOIL calendar mismatch caused a native panic | Medium | Resolved: unmatched source dates return an ordinary error. Regression passes. |
| Infinite WAT, overflowing area sums, malformed optional schemas, and NULL canonical PASS values could publish invalid accounting | Medium | Resolved: explicit schema/value/area checks fail before publication. Release tests and independent probes pass. |
| Out-of-range simulation days or water years silently saturated output integer columns | Medium | Resolved: Int32/Int16 bounds are checked. Canonical target IDs also enforce their serialized Int32 domain. |
| Invalid month/day and shared missing or duplicate simulation days were admitted | Medium | Resolved: month-length bounds and contiguous unique simulation-day checks reject the reproduced cases. Source-calendar equality remains required. |
| Physical terminal-Q or groundwater/final-row arithmetic could overflow after initial accumulation checks | Medium | Resolved: physical accounting and Roads-only final-row/reservoir checks reject these cases while retaining non-Roads behavior. |

Native topology remains source-qualified until terminal Q/lateral selection.
TotalWatSed retains all-OFE diagnostic Q/QOFE; equivalent reporting WAT receives
the independently reduced physical Q. Optional SOIL/ELEMENT contributions retain
their native joins and weighted valid-support denominators. Canonical PASS is
selected once by target ID, excluding standalone contributors. Roads alone admits
different particle diameters and preserves the first-source header; AgFields
retains its stricter compatibility check.

## Independent executable checks

Executed against the reviewed release library:

```text
WEPP_INTERCHANGE_TEST_BINARY=/workdir/wepppyo3/target/release/libwepp_interchange_rust.so \
  /workdir/wepppy/.venv/bin/python -m pytest \
  tests/wepp_interchange/test_roads_water.py \
  tests/wepp_interchange/test_totalwatsed3.py \
  tests/wepp_interchange/test_weighted_hillslope_pass.py -q
61 passed, 1 dependency deprecation warning, 8.35 seconds
```

The 61 tests comprise 16 Roads, 43 frozen TotalWatSed, and 2 weighted-PASS tests.
They cover zero-road parity, independent native outlets, literal versus physical
Q, malformed-input handling, alias rejection, publication behavior and existing
non-Roads compatibility.

Eight additional release probes used the normal frozen fixture with one defect
per case: terminal-Q overflow, reservoir overflow, February 31, simulation-day
overflow, water-year overflow, target-ID overflow, a shared missing interior day,
and duplicate simulation-day identity. Every case raised `RuntimeError` and
preserved both preexisting destination byte strings. Probe outputs are retained
locally at `/tmp/roads-final-review-ag8dcl_t`; they are scratch evidence, not
repository fixtures.

Additional optional-data probes covered absent files, valid present-empty
SOIL/ELEMENT schemas, and partial observations with source weights 0.5 and 1.25.
Absent/empty diagnostics remained null; partial TSMF, QRain and QSnow matched
independent valid-support weighted means within `rtol=1e-14`. Scratch evidence:
`/tmp/roads-optional-final-7xdv8rtl`.

The author reports 110 Rust unit and 17 integration tests passing. This reviewer
did not repeat that full suite. Existing shared `commit_staged` tests explicitly
exercise restoration of prior generations, cleanup without prior outputs and
retained recovery backups after rollback failure; the Roads producer uses that
same paired-publication primitive.

## Independent UM1 artifact readback

Read the [retained validation receipt](20261022_um1_validation.json), its
[execution script](validate_um1.py), and actual files under the isolated
`tests/wepp/interchange/fixtures/roads-accounting-scratch/um1` project.

Confirmed from the ledger, Parquet data and watershed run file:

- 66 canonical targets, 100 source profiles, 5,844 daily rows and 16 years.
- Ledger area is 441,820.29 square meters. Every TotalWatSed day and every sum of
  equivalent target areas agrees within `rtol=1e-14`.
- Accounting WAT contains 385,704 rows, exactly the canonical target IDs and one
  equivalent OFE per target/day.
- Independently recomputing annual lateral volume from each original native
  terminal OFE, its local area and ledger weight reproduces all reported annual
  lateral depths. Maximum absolute difference is `1.1368683772161603e-12` mm.
- Summing only canonical PASS target runoff reproduces every annual reported
  Runoff depth within `rtol=1e-12`.
- All 66 canonical PASS hashes match the ledger. `pw0.run` references precisely
  those 66 target files, and the retained `pw0.err` ends with successful
  completion of the watershed simulation.
- TotalWatSed carries `roads_accounting_policy=roads_modeled_area_v1`.

The receipt records 2001 Runoff 183.26310493761832 mm, Lateral Flow
1011.5502449533644 mm and Baseflow 71.4562594052902 mm. It also records average
report area 441,820.29000000004 square meters and 44 unchanged original Parquet
files. This reviewer verified current numerical artifacts but did not repeat the
whole model execution or independently reconstruct the before/after original-file
hash observation; those assertions remain bound to the retained execution receipt.

## Reviewed fingerprints and limits

| Reviewed item in wepppyo3 | SHA-256 |
| --- | --- |
| `wepp_interchange/src/totalwatsed/roads.rs` | `756c3e72764df8196b895ca8b524fc145ad9aa6ae59757f9d3b53b8e11b8ddc2` |
| `wepp_interchange/src/totalwatsed.rs` | `dff0d3ef9f3e5fa84252574ab6b24dccad313e2b566f1870d1c090d2055b4a9c` |
| `wepp_interchange/src/hill_pass_combine.rs` | `52a0d14a16e66982d28882236b0fa27ea1392a95d03538b81cf57f87cdeefe20` |
| `target/release/libwepp_interchange_rust.so` | `4ae01a243bebb596e6bf719626804a04e8ebdced7d9134e170f2af2a1bd31b6e` |

These hashes match `wepppyo3/docs/roads-accounting-release-20261022.json`.
The release manifest explicitly identifies included preexisting calendar/HBP
edits; those changes were not independently reviewed here.

Residual limits: paired publication supports rollback, not simultaneous visibility
of multiple paths; package readiness/provenance supplies the admission boundary.
This review does not establish crash recovery, archive/restore fidelity, live
authorized artifact access, production identity/mount parity, or a large-project
memory/performance bound. Real UM1 evidence exercises continuous additive Roads;
replacement, expansion and single-storm coverage relies on focused implementation
tests and the separate integration review. Broad WEPPpy gates and operational
closeout remain the package owner's responsibility.

The approved scientific model remains a mixture of existing modeled responses.
It does not recompute residual hillslope geometry or infer geographic ownership.
No new scientific accounting rule is introduced by this review.
