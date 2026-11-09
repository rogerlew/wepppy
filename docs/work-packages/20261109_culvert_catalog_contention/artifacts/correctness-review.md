# Correctness review: parallel culvert execution

## Metadata and user outcome

Independent reviewer: `culvert_review`, 2026-11-09. Review details and findings:
[review.md](../review.md). Security is assessed separately in
[security-review.md](security-review.md).

Goal: finish normal parallel culvert jobs with valid model artifacts, without
catalog identity conflicts, ordinary metadata lock failures or shared WBT settings
races. Authority: RedisPrep snapshot contract, query-catalog lifecycle contract,
and WBT `docs/stateless-execution.md`. Model formulas/defaults are unchanged.

## Failure-class coverage

| Shared assumption | Confirmed consumers repaired | Regression evidence |
| --- | --- | --- |
| Copied catalog identity is reusable | Culvert base and child copies | Absent/initialized/pending source clone pytest |
| Ordinary catalog publication may bypass Prep serialization | Initialization, clone rotation, snapshot, publication, receipt, status, refresh begin/ack/error and pilot receipt wrapper | Ten real-process sibling races plus91 peer tests |
| All catalog callers may fail immediately on lifecycle contention | HTTP schema/catalog/validate/activate/query/health | Six actual handler/process contention cases; acquisition retry only |
| Tool options may persist shared settings | Main CLI, all Rust get_configs consumers,25 bundled plugins | Real concurrent raster/plugin output and immutable settings |
| Python invocation may change parent cwd | Root, WBT and pip bindings | Concurrent instances, unchanged cwd/options, nonzero/timeout/reaping tests |
| Atomic replacement preserves permissions automatically | Explicit admin settings saves | Ownership, mode, symlink, ACL/xattr and creation-umask probes |

## Valid-state matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Optional catalog identity absent in source | yes | Fresh destination identity | Clone regression absent case |
| Source initialized or pending | yes | New scopes; source unchanged; retired receipts retained | Clone initialized/pending cases |
| Optional settings absent | yes | Existing defaults; tool creates no settings file | Real readonly-installation CLI |
| Empty/corrupt settings JSON | no | Explicit parse error; evidence retained | Corrupt-settings executable test |
| Populated static settings | yes | Invocation overrides stay local | Parallel raster compression/value checks |
| Legacy settings without raise_on_error | yes | Python defaultFalse, no KeyError | Three-wrapper constructor and execution test |
| Readonly installation | yes for tool runs | Execute without configuration writes | Real CLI outputs under normal worker identity |
| Settings symlink/ACL/non-primary group | yes | Preserve effective access/target on admin publication | Independent real CLI and Linux metadata test |
| Removed project while caller waits | no for publication | FileNotFoundError; never recreate tree | Real-process deletion/wait test |
| Stale wrapper after replacement | no | Reject before mutation | Existing RedisPrep lifecycle tests |

## Error and partial-state policy

RedisPrep still rejects genuine lifecycle conflicts before mutation; catalog
callers wait without holding the serializer across lifecycle contention. Caller
body errors propagate once. Corrupt/unreadable settings and failed metadata
preservation remain explicit errors, not silent defaults/retries. Failed culverts
retain metadata/tracebacks; finalizer completion is not all-child success.

## Generated artifact evidence chain

| Stage | Evidence | Result |
| --- | --- | --- |
| User intent | Exact incident ZIP SHA in active plan | Retained |
| Reloaded copied state | Real catalog clone identities and source snapshots | Pass |
| Tool executable inputs/outputs | Concurrent real GeoTIFF values, CRS, transform, compression; plugin output | Pass |
| Worker runtime | Installed/built hashes, normal identity, discovery | Pass on forest |
| Full model artifacts | Fresh33-child live pytest, no retries;4 overlapping children | Pass |
| User-facing artifact | Authenticated browse/download and2,877 ZIP member hashes | Pass |

Direct failing boundaries reproduced before their repairs. Focused WEPPpy gate:
296 passed, one deliberately disabled opt-in live test. WBT:207 Rust and23 Python
tests pass. Full-suite and fresh payload acceptance are still running. Highest
supported claim is implemented and locally validated, installed on forest for
acceptance. Do not claim full incident closure from RQ status alone.

## Verdict

Code review has no unresolved blocker after the HTTP compatibility and metadata
repairs. Forest correctness gate: passed with the recorded unrelated baseline-suite
limitation; fresh parallel artifacts and broader suite disposition are retained below. Production and other-platform rollout are outside
this authorization. Coverage is explicit above, not claimed exhaustive.


Live acceptance completed: second fresh replay passed the complete pytest in
1,943.10 seconds; first replay independently matches earlier model outputs.
Evidence: `second-live-evidence.json`, `second-concurrency.json`,
`first-model-comparison.json` and `first-archive-evidence.json`. Broad-suite
disposition remains the only pending local gate.


## Final disposition (2026-11-09)

Forest acceptance complete. Full sanity: 13,236 passed, 435 skipped, 15 passed
subtests; stopped at the known baseline failure
`tests/weppcloud/test_usersum_template_wiring.py::test_runs_template_uses_the_ttl_deletion_usersum_doc_id`
after 3,895.78 seconds. Both test and `templates/user/runs2.html` are unchanged;
HEAD already asserts `runsTtlDeletionHelpUrl` while the HEAD template lacks it.
The suite is not fully green, and maxfail=1 leaves the remaining tests unexecuted.
Focused real-Redis/HTTP/catalog/culvert checks: 296 passed, one opt-in live skip.
WBT: 207 Rust tests and 23 Python executable/binding tests passed. The separate
live gate passed, and both clean replays prove four overlapping child jobs.

Scope: forest batch-worker runtime reloaded and verified; other resident service
processes were not restarted. Production rollout/recovery and other-platform
validation are outside this completed task. Both repositories retain uncommitted
changes; the prior dirty WBT runtime is backed up. No model defaults changed.
