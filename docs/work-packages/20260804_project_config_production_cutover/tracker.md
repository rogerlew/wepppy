# Tracker - Project Config Production Cutover (WP12)

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-31 16:06 UTC

**Current phase**: Production deployment preparation

**Last updated**: 2026-09-04

**Next milestone**: Deploy current master with all four flags enabled

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**:
`artifacts/20260831_security_review.md`

## Branch Contract

- Initiative branch: `feature/project-owned-config`
- Canonical branch: `master`
- Promotion policy: merge only at the roadmap promotion gate
- Verified local branch: `feature/project-owned-config`
- Verified upstream: `origin/feature/project-owned-config`
- Starting candidate: `30b30b3c6e2cf99aba47cf8ea3c2b8988f8dc381`
- Validated pre-merge candidate: `039192492ffec38782893a603916a2e91918cfca`
- Canonical merge base: `6af9ecdd63921189804c5e292114a97253914cbb`

## Task Board

### Ready / Backlog

- [ ] Merge the accepted boundary to `master` and record the merge revision.
- [ ] Deploy the canonical revision to production with staged flags.
- [ ] Record health, danger, rollback, and WP13 handoff evidence.

### In Progress

- [ ] Push the final reviewed feature candidate and merge the exact accepted
  boundary to `master`.

### Blocked

- None.

### Done

- [x] First wepp1 attempt failed closed before build/recreation on a conflicting
  shared-image definition; aligned `shape-converter` with the wepp1 build anchor
  and added merged-Compose regression coverage (2026-09-04).

- [x] Verified branch/upstream/merge-base contract (2026-08-31 16:06 UTC).
- [x] Confirmed WP11, WP12B, WP12C, and WP12D report Forest acceptance
  (2026-08-31 16:06 UTC).
- [x] Confirmed the feature branch is clean, pushed, zero commits behind
  `origin/master`, and 83 commits ahead (2026-08-31 16:06 UTC).
- [x] Repeated amendment 4 and amendment 5 changed-file comparisons and
  dispositioned every post-amendment commit without finding an unratified
  behavioral boundary (2026-08-31 16:18 UTC).
- [x] Corrected the six historical Markdown EOF-blank-line findings without
  changing review content (2026-08-31 16:18 UTC).
- [x] Passed the successful complete Python run with 7,280 passed and 63
  skipped; passed 108 frontend suites/833 tests and lint (2026-08-31 16:55 UTC).
- [x] Passed scoped stubs, stub completeness, broad exceptions, Vulture, and
  focused preset/capability tests after correcting one missing public stub
  export (2026-08-31 17:18 UTC).
- [x] Regenerated source-line-only RQ graph drift and passed the 144-edge graph
  check (2026-08-31 17:25 UTC).
- [x] Completed correctness and dedicated security promotion reviews with no
  unresolved findings (2026-08-31 17:35 UTC).
- [x] Committed pre-merge candidate `039192492ffec38782893a603916a2e91918cfca`
  and recorded its exact validation ancestry (2026-08-31 17:42 UTC).

## Decisions Log

### 2026-09-04: Compress flag activation into one deployment window

**Context**: Production remains on pre-Builder revision `075910aff`; all four
flags are absent. The limited deployment window does not permit a reader-only
deployment followed by a writer deployment.

**Decision**: The operator explicitly approved setting all four flags to true
before one canonical deployment. Preserve default-off tracked Compose values,
all validation/health gates, and writer-first disablement on rollback.

**Impact**: Dedicated wepp2/wepp3 worker Compose files must receive the same
flag passthrough as wepp1 before host-local `.env` values are staged.

### 2026-08-31 16:06 UTC: Execute WP12 as the roadmap promotion boundary

**Context**: The operator authorized scaffolding and execution after completing
Forest acceptance and final feature-branch gates.

**Decision**: Retain the roadmap's reader-before-writer rollout, exact-revision
inventory, rollback-reader compatibility, shared alias, and production-after-
merge ordering. Stop for operator input only if the final changed-file audit
reveals an unratified behavioral boundary or production evidence contradicts
the accepted contract.

**Impact**: Documentation-only audit corrections may proceed autonomously;
behavioral scope expansion requires explicit operator disposition.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Extra branch commits exceed the ratified WP12 boundary | High | Medium | Inventory and disposition every path before merge | Open |
| Production writer activation outruns rollback readers | High | Low | Reader-first staging and exact rollback test | Open |
| Feature flags or runtime revision differ across services | High | Low | Inspect canonical deployment inputs and running revisions | Open |
| Shared compatibility alias is removed early | High | Low | Verify alias remains before and after rollout | Open |

## Verification Checklist

### Code Quality

- [x] Complete Python suite passes.
- [x] Frontend tests and lint pass.
- [x] Applicable stub and test-hygiene gates are dispositioned.
- [ ] `git diff --check` is clean at the final checkpoint.

### Security

- [x] Security impact and dedicated review requirement recorded.
- [x] Security artifact is complete with no unresolved medium/high findings.
- [x] Auth, mutation, deployment, and rollback surfaces are reviewed.

### Documentation

- [x] WP12 package, tracker, active ExecPlan, and evidence are current.
- [ ] Scoped documentation lint passes at the final checkpoint.
- [ ] Roadmap and `PROJECT_TRACKER.md` reflect promotion state.

### Testing and Deployment

- [x] Forest user acceptance evidence is available from prerequisite packages.
- [x] Final runtime automated gates pass at the accepted feature revision.
- [ ] Canonical merge revision is deployed to production.
- [ ] Staged production smoke and rollback checks pass.

## Progress Notes

### 2026-08-31 16:06 UTC: Package scaffolded

**Agent/Contributor**: Codex

**Work completed**:

- Verified the initiative branch, upstream, merge base, and pushed candidate.
- Created WP12 from the roadmap promotion contract.
- Began the required final changed-file audit.

**Next steps**:

- Correct known documentation diff-check findings.
- Complete scope classification and final gates.
- Merge and deploy only after the accepted boundary is exact.

**Test results**: Pre-scaffold branch was clean and synchronized; the first
`git diff --check origin/master...HEAD` identified six documentation files with
an extra blank line at EOF.

### 2026-08-31 16:18 UTC: Repeated scope audit complete

**Agent/Contributor**: Codex

**Work completed**:

- Repeated the exact amendment 4 range from `596ff5758` through `588608f1a` and
  retained the operator-ratified correction.
- Repeated amendment 5 from `0ad76c547` through `b772877c4`; all production,
  test, and governance paths match its exact list.
- Classified all later branch commits by ratified WP12D continuation or their
  independently governed and operator-accepted package/fix provenance.

**Blockers encountered**: None. No new behavioral contract amendment is
required by the changed-file inventory.

**Next steps**:

- Run documentation and final automated gates.
- Complete promotion security/correctness evidence.
- Commit and push the reviewed candidate before canonical merge.

**Test results**: Scope audit passed; automated gates pending.

## Watch List

- **Post-amendment branch additions**: ESDAC diagnostics, CAP/session runtime
  hardening, Portland analytics removal, table accessibility, and final Forest
  evidence must receive explicit scope dispositions.
- **WP13 boundary**: do not remove the shared `_defaults.toml` alias.

### 2026-08-31 17:35 UTC: Pre-merge gates complete

**Agent/Contributor**: Codex

**Work completed**:

- Recorded the complete automated gate results and honest failure dispositions.
- Corrected the missing snapshot stub export and stale generated RQ source line.
- Completed correctness and security promotion reviews with zero unresolved
  findings.

**Blockers encountered**:

- The test-isolation tool defaults to five full unrandomized suite runs when no
  plugin/target is supplied and provided no progress from its first worker; it
  was stopped and dispositioned without claiming a pass.

**Next steps**:

- Commit and push the exact feature candidate.
- Rerun final diff/docs gates and record the candidate.
- Merge to `master`, then begin canonical production rollout.

**Test results**: See `artifacts/20260831_validation.md`.
