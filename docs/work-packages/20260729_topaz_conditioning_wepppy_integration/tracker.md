# Tracker - Topaz Conditioning WEPPpy Integration

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-30 01:24 UTC

**Current phase**: Closed

**Last updated**: 2026-07-30 03:20 UTC

**Next milestone**: production promotion remains a separately authorized
release/deploy action

**Security impact**: `high`

**Dedicated security review**:
`artifacts/2026-07-30_security_review.md`

## Task Board

### In Progress

- None.

### Ready

- None.

### Blocked

- None.

### Done

- [x] Mapped the existing DOM-05 control, persistence, RQ, emulator, config,
  tests, and WBT release surfaces (2026-07-30 01:24 UTC).
- [x] Recorded the operator-approved normative delta and ADR
  (2026-07-30 01:24 UTC).
- [x] Retained and dispositioned both initial FAIL reviews; expanded the
  checkpoint with exact default/hydration, explicit width 2, staged rollback,
  enum/config guards, bounded native cleanup, provenance, and negative-test
  requirements (2026-07-30 02:02 UTC).
- [x] Received governance and operations/security post-fix PASS with no
  unresolved blocking/high/medium checkpoint findings
  (2026-07-30 02:16 UTC).
- [x] Committed the standalone documentation ancestor
  `5754a1e06798a2f116a04b5eff4601402e143962`
  (2026-07-30 02:24 UTC).
- [x] Built and committed the WBT runtime release at
  `0f226804e568c12bb698795f352c47ecbc324769`, then closed the
  early-output-EOF containment bypass in required follow-up
  `47ca8e44730c0691cfcf8ac2bfa106e792254b36`; installed binary SHA-256
  `e5b33364b788f0046db15760320c7b03c6412fda99987f2bbe3ac76ba53b4cd0`,
  and passed seven-case parity plus container discovery/execution
  (2026-07-30 02:47 UTC).
- [x] Implemented UI, enum/config validation, NoDb validation, schema,
  explicit width/timeout dispatch, config-scoped default, and contract tests
  (2026-07-30 03:12 UTC).
- [x] Passed the definitive full suite (5,598 passed, 58 skipped), frontend,
  stubs, docs, graph, WBT, containment, and parity gates
  (2026-07-30 03:11 UTC).
- [x] Received final operations/security PASS with no unresolved high/medium
  findings and dispositioned the governance closure/hygiene findings
  (2026-07-30 03:14 UTC).
- [x] Restarted the local stack and completed the operator-authorized
  `austere-inaction` RQ E2E; parent and both children finished, persisted mode
  is `topaz`, and run-scoped relief/flow artifacts were regenerated
  (2026-07-30 03:15 UTC).
- [x] Published final validation and review evidence and closed the package
  (2026-07-30 03:20 UTC).

## Decisions

### 2026-07-30 01:24 UTC: Add one explicit token

**Decision**: Use canonical token `topaz` and user-visible label
`Topaz Conditioning Algorithm`.

**Rationale**: The token is short and stable while the label distinguishes the
source-faithful TOPAZ FILDEP/RELIEF implementation from generic depression
filling or breaching.

### 2026-07-30 01:24 UTC: Keep the default config-scoped

**Decision**: Change only `disturbed9002_wbt.cfg` from
`breach_least_cost` to `topaz`.

**Rationale**: This implements the operator request without migrating persisted
runs, changing the Watershed fallback, or altering other configurations.

## Risks

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Wrapper advertises a tool absent from runtime binary | High | Build, atomically install, discover, and execute the tracked WBT binary | Closed |
| Native child outlives a timeout/abandoned job | High | Bounded wrapper timeout, process-group termination, wait/reap, and forced-timeout regression | Closed |
| New token reaches a worker with an old binary | High | Release WBT first and validate from all three local Python service roles | Closed locally; production promotion check remains |
| Invalid enum or wrong path config mutates/enqueues | High | Explicit pre-mutation allowlist and canonical config/run guard with negative tests | Closed |
| UI token is accepted but dispatches a legacy path | High | Contract tests, direct emulator assertion, and local E2E run log | Closed |
| Existing projects change behavior | Medium | Additive token; config-only default; no state migration | Closed |
| Unrelated dirty worktree changes enter commits | High | Stage exact package/source/test hunks and inspect cached diff | Pre-commit gate |

## Verification Checklist

- [x] Documentation-only checkpoint ancestor exists.
- [x] Contract and ADR lint pass.
- [x] Installed WBT binary discovers and executes `TopazConditionDem`.
- [x] Actual-template render and reload contract tests pass.
- [x] Both channel controller payload tests pass.
- [x] Watershed setter/config and emulator dispatch tests pass.
- [x] RQ persistence-order test accepts `topaz`.
- [x] Invalid-enum and config-mismatch requests prove no mutation or enqueue.
- [x] Pre-existing persisted legacy selection survives config-default change.
- [x] WBT forced-timeout test proves process-tree cleanup and explicit failure.
- [x] Generated controller bundle is rebuilt and clean.
- [x] Frontend lint/tests and targeted Python tests pass.
- [x] Full Python sanity gate passes.
- [x] Final security and correctness findings are dispositioned.

## Progress Notes

### 2026-07-30 01:24 UTC: Contract-first scaffold

The existing DOM-05 matrix and REM-05 checkpoint explicitly limit the current
contract to `fill`, `breach`, and `breach_least_cost` and exclude algorithm and
default changes. DOM-05A is therefore an intended-behavior amendment rather
than a conformance fix. Implementation remains untouched pending the mandatory
reviews and standalone checkpoint commit.

### 2026-07-30 02:02 UTC: Initial reviews failed; checkpoint revised

Governance and operations/security reviewers returned FAIL. All
blocking/high/medium findings were accepted or bounded in the disposition.
Implementation remains untouched pending both reviewers' post-fix PASS and the
standalone documentation ancestor.

### 2026-07-30 02:16 UTC: Revised checkpoint passed

Both independent reviewers returned post-fix PASS. The only remaining
pre-implementation gate is a standalone documentation commit whose cached diff
contains only DOM-05A contract material.

### 2026-07-30 03:12 UTC: Release and integration wired

WBT release `0f226804e568c12bb698795f352c47ecbc324769` adds per-call
process-tree containment and installs the parity-hardened binary. Required
follow-up `47ca8e44730c0691cfcf8ac2bfa106e792254b36` retains deadline and
cancellation enforcement after early output EOF. WEPPpy now exposes/persists
`topaz`, validates it before mutation/enqueue and at the NoDb boundary, pins
width 2 and a 540-second native timeout, and changes only
`disturbed9002_wbt.cfg`. Focused generated-output, route, schema, RQ, render,
config, dispatch, and frontend tests pass.

### 2026-07-30: Final review blockers corrected

Final correctness review found that a deployment override below 600 seconds
could erase the native cleanup margin, the new public enum constant was absent
from the NoDb stub, and two records contained a mistyped checkpoint SHA. Topaz
now elevates only its build-channel child timeout to at least 600 seconds,
preserving higher operator values and legacy-method timeout behavior. The stub
and checkpoint provenance are corrected.

### 2026-07-30 03:20 UTC: Full validation and E2E closed

The full Python suite passed 5,598 tests with 58 skips. An initial full run
found a legacy Daymet test that polluted `sys.modules` with a fake
`whitebox_tools`; it now imports the real installed module first, has the
required unit marker, and the exact Daymet-before-Topaz order passes. Both
independent final reviews approve the implementation.

The local stack restarted cleanly. Contract discovery supplied the exact
existing extent and channel parameters for `austere-inaction`; the authorized
RQ rerun changed only `wbt_fill_or_breach` to `topaz`. Parent job
`30df3081-bed5-4cf1-b75d-63e792d03448` and both children finished. The
persisted mode and run log confirm Topaz dispatch, and new `relief.tif` and
`flovec.tif` hashes are retained in the final validation artifact.
