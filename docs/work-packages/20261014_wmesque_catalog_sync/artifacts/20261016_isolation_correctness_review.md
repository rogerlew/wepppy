# M7 isolation repair correctness review

- Reviewer: independent `validation_correctness` agent, 2026-10-16 UTC.
- Context: working-tree changes above `1951875ba`; no reviewer runtime edits.
- Scope: isolation checker and regressions, seven collection-time stub removals,
  scoped application-import environment in two tests, terrain helper strict-breach
  forwarding, generated workflow JSON diagnostics.
- Authority: [test isolation boundary](../../../dev-notes/test-isolation.md),
  [conditioning contract](../../../schemas/wbt-conditioning-diagnostics-contract.md#breachdepressionsleastcost),
  and [ADR-0095](../../../adrs/ADR-0095-terrain-helper-strict-least-cost-breach.md).
- Previous environment review: [20261015 correctness review](20261015_validation_correctness_review.md).
  This review supersedes its warning that identical worker errors may pass;
  earlier environment receipts do not validate these later source changes.

## Findings

| ID | Severity | Finding and evidence | Resolution | Status |
| --- | --- | --- | --- | --- |
| ISO-COR-01 | Medium | Earlier `/tmp/m7-isolation-final.log` rejected 14 otherwise passing files for `_openssl.lib`. | Recognize CFFI native library objects, require a native FFI/Lib pair for `_openssl`, inspect Cryptography proxy metadata without forwarding, and recognize observed Cython ABI suffixes. Matching runner receipt passes all 15 selected files with `issues: []`; replacements and unrelated collection stubs remain detectable. | Resolved |
| ISO-COR-02 | Low | Earlier tests omitted the orchestration exit path and native-shape negative controls; nonpositive iterations could report clean without executing work. | Added actual orchestration regression proving errors cannot be baseline-suppressed, exit 2 survives, and report-only remains explicit and visible. Native-name near-miss and replacement regressions pass; parser rejects 0/-1. | Resolved |

The reviewed source closes the original lazy-lookup and lifecycle defects:
module metadata and watched singleton attributes are read from dictionaries;
`None` import sentinels are handled; session-start/session-finish snapshots retain
collection effects while excluding pytest shutdown. Missing requested snapshots
raise an explicit tool error. Every nonzero execution becomes an unsuppressible
finding, and exit codes above one return tool error unless report-only mode was
explicitly selected. Ordinary file-backed imports are no longer reported merely
because they were added; existing-module replacements remain findings.

The native-module and import-default rules are documented heuristics, not
provenance authentication. Environment exemptions are bounded to exact additions
with a newly imported file-backed dependency; changed/removed values remain
visible. No namespace-wide suppression or threshold reduction was introduced.
The `cython_runtime` rule intentionally remains a narrow name/key-shape heuristic;
it does not authenticate the origin of every newly added synthetic object.

## User outcome and valid states

The operator needs a trustworthy isolation result on the canonical runtime.
Passing tests must survive observation; a failed or incomplete worker must not
appear clean. Failed checks retain JSON details and per-worker logs. These tool
changes do not mutate deployed data or alter project authorization.

| State or input | Required behavior | Evidence and limit |
| --- | --- | --- |
| Empty test body with normal pytest startup/shutdown | Clean, without a false `PYTEST_VERSION` removal | Real child-process regression passes. |
| Lazy module or blocked import sentinel | Observe without importing or raising from `__getattr__` | New dictionary-read/`None` regression passes. |
| New ordinary import; replaced existing module | Accept import; report replacement | New classification-summary regression passes. |
| Persistent collection-time stub or environment addition | Report pollution | Real child-process regression detects both. |
| Exact library import defaults; preexisting value changed | Accept only documented initialization; report change | Pint positive/negative regression and native replacement/near-miss controls pass; matching runtime's real imports pass. Exhaustive library shapes and Rasterio negative cases are not claimed. |
| Repeated identical worker errors, missing requested snapshots | Visible incomplete execution and nonzero tool result | Actual orchestration, summary and worker-payload regressions pass; missing-snapshot guard inspected. |
| No tests, malformed invocation, report-only request | No successful isolation claim; explicit report-only exit exception | Parser rejects nonpositive iterations; actual orchestration preserves visible report-only findings. Exhaustive CLI combinations are not claimed. |
| Least-cost breach with filling disabled | Forward strict unresolved-depression failure | Helper assertion and real WBT path pass; existing diagnostic validation remains active. |
| Other conditioning modes and existing defaults | Preserve prior behavior | Conditional forwarding leaves their value false; no defaults changed. |

## Production error and artifact boundary

The terrain helper previously omitted `blc_fail_on_unresolved`, so the emulator
used false and produced diagnostics rejected by the existing strict contract.
The correction forwards true only for least-cost breach with filling disabled.
Unresolved depressions now fail at the existing WBT error boundary rather than
later diagnostic rejection. The existing `WbtUnresolvedDepressionsError`
translation and output-validation policy remain unchanged; no fallback artifact
becomes acceptable. ADR-0095 records rationale and rollback.

| Artifact stage | Direct evidence | Supported result |
| --- | --- | --- |
| Intent/prepared input | Existing real-WBT test passes `breach_least_cost`, `blc_fill=False`; helper regression inspects forwarded strict flag. | Input semantics reviewed. |
| Native execution and diagnostic consumer | `_create_relief` invokes real WBT then parses/validates its generated diagnostics; the two selected real-WBT tests pass in `/tmp/m7-isolation-repair-tests.log`. | Bounded synthetic DEM integration passes. |
| Flow outputs | Existing tests read the helper/phase artifact paths and assert generated flow-stack files. | Existing output checks pass; no deployed-project/browser acceptance claimed. |
| CI diagnostic output | Workflow adds `--json`; matching runner log records exit 0, no failure/error entries, and `issues: []` after all 15 selected files pass separately. | Focused runtime qualification passes; complete hosted isolation remains pending. |

Project artifact paths, archive membership and browser authorization are unchanged;
no new hidden project record is introduced. Persisted-state migration is not part
of this follow-up. Deployment and whole-project terrain parity remain outside the
bounded synthetic integration receipt.

## Validation and verdict

Inspected receipts: `/tmp/m7-checker-tests.log` has **15 passed**;
`/tmp/m7-isolation-repair-tests.log` has **142 passed**, no skips, including the
explicitly selected real-WBT module. The six test edits delete legacy dependency
stubs without deleting test bodies or assertions. Canonical runtime dependencies
now satisfy their imports directly.

Latest `/tmp/m7-isolation-topo-tests.log` records **178 passed, 4 skipped** in
22.57 seconds across checker/topography coverage. The opt-in skips do not replace
the earlier explicit real-WBT receipt. On the matching CI runtime,
`/tmp/m7-isolation-runner-qualified.log` records the combined focused run passing
in 24.04 seconds, **all 15 per-file checks passing**, and final `issues: []`.
This includes the checker regressions and real WBT module selected individually.

### Broad collection audit follow-up

The earlier `/tmp/m7-collection-audit.log` completed **703 successful per-file
collection checks**, with **39 state findings across 36 files**. It predates the
final corrections and is diagnostic evidence, not a passing current-source gate.
Review of the resulting bounded changes found no new correctness defect:

- Remove the additional module-level `deprecated` stub from
  `tests/wepp/soils/utils/test_wepp_soil_util.py`; test bodies/assertions remain.
- Limit recognition of Cython parallel/cimports/import proxies and Passlib's
  registry proxy to their observed concrete class module/name. Inspect Passlib's
  compatibility backing module directly. Actual-library and bare-name-stub
  regressions distinguish these from arbitrary Python stubs; replacements still
  produce findings. All module findings are now reported, avoiding the earlier
  first-finding-only output that hid additional helper objects.
- Accept `KMP_DUPLICATE_LIB_OK=True` only with a newly imported file-backed
  Threadpoolctl/Scikit-learn module, and the existing exact Certifi-path defaults
  with newly imported Pyogrio/Fiona modules. `/tmp/m7-shape-probe.log` directly
  shows Fiona loaded by the shape-converter test and both defaults matching the
  loaded Certifi path. New regressions preserve additions without that import
  and changes to existing values. The canonical inventory documents each
  addition; no global environment suppression is introduced.
- The RQ-info and PostgreSQL-preference tests use `MonkeyPatch.context()` around
  application import to supply a temporary asset version and restore the previous
  environment on both success and failure. Existing values are preserved. Their
  route/authentication/database assertions and production startup remain unchanged.

`/tmp/m7-audit-followup-tests.log` records **98 passed** in 19.21 seconds across
the checker and three changed test files. Subsequent
`/tmp/m7-checker-audit-tests.log` records **27 passed** in 17.51 seconds, including
the final dependency-default and real-proxy regressions.
`/tmp/m7-collection-recheck.log` passes all **36 affected-file collection checks**
with `issues: []`. `/tmp/m7-audit-isolation-final.log` passes the combined actual
execution in **24.33 seconds**, then all **four per-file execution checks**, with
no failures/errors and final `issues: []`. These directly close the focused
collection and execution conditions for the final reviewed changes.

Collection-only diagnostics do not replace the complete execution gate. Hosted
baseline/five-repeat success predates these revisions, and no randomization
plugin is installed. Do not claim shuffled-order coverage or M7 closeout.

Gate: **pass with validation conditions**. Unresolved findings: zero high,
zero medium, zero low. The reviewed bounded repair may proceed to fresh hosted
acceptance; complete isolation/M7 acceptance still requires that full gate.
No additional production correctness defect found in the bounded terrain
correction. No heavyweight reviewer tests were launched.
