# Focused review of factorial staging repair

**The staging defect is repaired and actual reused/fresh preflight readback
passes. No blocker to continuing the frozen v2 diagnostic execution.** Final
acceptance still requires the separate all-case runtime/log verification below.

## What the earlier review missed

The first review checked scientific input decks, output reuse, and dependency
identity but did not exercise the runtime audit called by `execute()`. The
contract in `20261029_roads_drainage_validation/artifacts/analyze.py`,
`validate_runtime()`, requires the exact `runs/` file set of declared native
inputs plus `reference.sol`, `stdout`, and `stderr` (with two specifically hashed
optional normalized-reference intermediates). It also checks that `wepp_ui.txt`
presence and the native UI banner agree with the case's runtime selection.
These auxiliary/log files are therefore part of the executable audit contract,
even though they are not all model inputs.

Omitting those files invalidated the original harness acceptance. The first
attempt is retained separately: nine native runs completed, zero audited records
were accepted. This was a staging/audit integration failure, not evidence of a
native model failure or a changed scientific result.

## Verified repair

The v2 declaration preserves all **928** original scientific task/input
definitions, changing only destination paths and adding auxiliary/log manifests.
Independently verified **928** `reference.sol` files and **928** reused
stdout/stderr files against their frozen sources. Called the actual
`validate_runtime()` read-only in the intended runtime container for every one
of the **464** staged reuse cases: all passed.

The initially proposed broad existing-record shortcut was insufficiently bound.
The frozen implementation now permits skips only for the exact two preflight
folders, binds their record hashes to the current declaration and script,
requires completed/physical success and native return code zero, verifies
artifact bytes, and independently reproduces passing particle audits.

Independently executed that verification against the actual reused and freshly
simulated preflight records, then separately called `validate_runtime()` on both.
Both pass physical/particle checks and have the required current log/reference
files. All **70** effective dependency hashes match. No missing-log or mutated
artifact was found in these actual preflight records.

- Frozen script: `803d4a41587a7dc5eea03c31d16e82377c77b28de4d9d85abc30a4bba4adf526`.
- Declaration: `11792fff8cea00ac3e74f35c324decc573283f85774a22a9d06e35d7ca61b849`.
- Actual preflight: `636af2cc8f98d6afd2ba64502d4e6abbafeee2c4b0f5459f732c19bacefb64c8`.

## Remaining verification boundary

Fresh generated stdout/stderr are not included in the frozen v2 record hash
manifest, and its cached-record verifier does not itself rerun `validate_runtime()`.
That is prospective guard coverage, not a demonstrated invalid simulation.
The reviewed records' actual logs are independently hashed in the companion
receipt. Preserve the running source/declaration; do not attribute later code to
this execution. Before accepting final results, independently hash every fresh
and reused log and call the actual runtime validator for every final case,
including both preflight records, retaining a separate verification receipt.

The full application suite remains its own release-handoff gate. This review
does not accept parameter transfer, magnitude performance, withheld validation,
or UI implementation.

Companion evidence: `/tmp/combined-hydraulics-r4-v2-implementation-review.json`.
