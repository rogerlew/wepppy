# Tracker - Topaz Conditioning WEPPpy Integration

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-30 01:24 UTC

**Current phase**: Contract checkpoint

**Last updated**: 2026-07-30 02:02 UTC

**Next milestone**: standalone documentation ancestor

**Security impact**: `high`

**Dedicated security review**:
`artifacts/2026-07-30_security_review.md`

## Task Board

### In Progress

- [x] Both independent reviewers returned post-fix PASS.

### Ready

- [ ] Commit the documentation-only checkpoint as a standalone ancestor.
- [ ] Build/install the WBT release and implement WEPPpy integration.
- [ ] Update contract tests and run generated-output validation.
- [ ] Complete final correctness/security review and close.

### Blocked

- Implementation is contract-blocked until the reviewed checkpoint ancestor
  exists.

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
| Wrapper advertises a tool absent from runtime binary | High | Build, atomically install, discover, and execute the tracked WBT binary | Open |
| Native child outlives a timeout/abandoned job | High | Bounded wrapper timeout, process-group termination, wait/reap, and forced-timeout regression | Open |
| New token reaches a worker with an old binary | High | Release WBT first and validate from the WEPPpy container runtime | Open |
| Invalid enum or wrong path config mutates/enqueues | High | Explicit pre-mutation allowlist and canonical config/run guard with negative tests | Open |
| UI token is accepted but dispatches a legacy path | High | Contract tests plus direct emulator call assertion | Open |
| Existing projects change behavior | Medium | Additive token; config-only default; no state migration | Open |
| Unrelated dirty worktree changes enter checkpoint commits | High | Stage exact package/contract hunks only and inspect cached diff | Open |

## Verification Checklist

- [ ] Documentation-only checkpoint ancestor exists.
- [ ] Contract and ADR lint pass.
- [ ] Installed WBT binary discovers and executes `TopazConditionDem`.
- [ ] Actual-template render and reload contract tests pass.
- [ ] Both channel controller payload tests pass.
- [ ] Watershed setter/config and emulator dispatch tests pass.
- [ ] RQ persistence-order test accepts `topaz`.
- [ ] Invalid-enum and config-mismatch requests prove no mutation or enqueue.
- [ ] Pre-existing persisted legacy selection survives config-default change.
- [ ] WBT forced-timeout test proves process-tree cleanup and explicit failure.
- [ ] Generated controller bundle is rebuilt and clean.
- [ ] Frontend lint/tests and targeted Python tests pass.
- [ ] Full Python sanity gate passes or any environmental blocker is recorded.
- [ ] Final security and correctness findings are dispositioned.

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
