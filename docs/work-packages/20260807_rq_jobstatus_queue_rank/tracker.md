# Tracker – Advisory Queue Rank in RQ Job Status

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-07 17:38 UTC
**Current phase**: Closure
**Last updated**: 2026-08-07 19:10 UTC
**Next milestone**: Archive the ExecPlan, register Done, and commit closure docs.
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260807_rq_jobstatus_queue_rank/artifacts/20260807_security_review.md`

## Task Board

### Ready / Backlog

- None.

### In Progress

- [x] Create package scaffold and register it as In Progress (2026-08-07 17:38 UTC).
- [x] Record starting revision and dirty-tree inventory (2026-08-07 17:38 UTC).
- [x] Amend canonical contracts and record unavailable reviewer attempts
  (2026-08-07 17:55 UTC).
- [x] Receive explicit operator authorization to proceed despite unavailable
  delegated reviewer outputs (2026-08-07 18:44 UTC).
- [x] Implement and commit the feature (`a416e7dd7`, 2026-08-07 UTC).
- [x] Apply review remediation (`97141ba44`, 2026-08-07 UTC).
- [x] Complete validation, reviews, documentation, and closure artifacts.

### Blocked

- None after explicit operator authorization on 2026-08-07 18:44 UTC.

### Done

- Package closed in `4565ec00b3b6a6d494b1abf7585cfb5d2b95f19c`.

## Timeline

- **2026-08-07 17:38 UTC** – Package created; starting revision recorded as `0f4aaaae5b0f370beb6a6193707fb57d4a8abc5d`; unrelated untracked investigation preserved.

## Decisions Log

### 2026-08-07 17:38 UTC: Single-origin advisory snapshot

**Context**: A Culvert orchestration root finishes after registering children,
so root-only queue lookup cannot identify the next queued work item.

**Decision**: Traverse registered `jobs:*` links once, collect queued members
with non-empty origins, omit on mixed origins or unreliable races, and select
the smallest offset from one ordered queue list.

**Impact**: The response can identify a queued Culvert child or finalizer while
remaining additive, bounded, and incapable of fabricating a cross-queue rank.

### 2026-08-07 18:44 UTC: Operator authorization to resume

**Context**: Delegated read-only contract reviewers did not return outputs, and
the prior session stopped before implementation under the initial governance
instruction.

**Decision**: The operator explicitly authorized implementation to proceed and
stated that no blockers are identified. The committed checkpoint contract
remains unchanged; implementation and post-implementation reviews must still
document their actual evidence and findings honestly.

**Impact**: The package resumes at implementation from checkpoint commit
`7ce0cf524d9e7f4d2be6270ca220b574f04e91ed`.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Unrelated queued job ID disclosure | High | Low | Candidate IDs come only from registered tree links; return only selected candidate | Closed |
| Polling cost amplified by large trees | High | Medium | One traversal and one ordered queue snapshot for a single-origin tree; explicit contract limitation | Accepted by operator-approved contract |
| Queue/status race produces stale rank | Medium | High | Omit or choose remaining candidate; never fail authoritative status | Closed |
| Auth/token behavior changes accidentally | High | Low | Route/auth regression tests and explicit non-change review | Closed |
| Full suite blocked by baseline failure | Medium | Medium | Run focused gates first and record exact unrelated blocker | Closed by full-suite result |

## Verification Checklist

### Code Quality

- [x] Focused RQ and route pytest suites pass.
- [x] Full `wctl run-pytest tests --maxfail=1` is run or exact unrelated blocker recorded.
- [x] Broad-exception enforcement and code-quality observability are recorded.
- [x] `git diff --check` passes.

### Security

- [x] High-impact triage and dedicated artifact are complete.
- [x] No unresolved High/Medium security findings remain.
- [x] Open/optional/required auth modes and rate limiting remain unchanged.
- [x] Browse token remains browse/download-only.

### Documentation

- [x] Canonical contracts, rq README, route usersum docs, and Culvert docs updated.
- [x] All changed Markdown is linted.
- [x] Package closure notes and review artifacts are complete.

### Testing

- [x] Root, descendant, finalizer, mixed-origin, race, status-normalization,
  bounded-access, and disclosure cases are covered.
- [x] Existing status/progress/diagnostic/error/timestamp/not-found behavior is
  explicitly preserved.
- [x] OpenAPI contract suite passes without route-count or response-code changes.

## Progress Notes

### 2026-08-07 17:38 UTC: Package scaffold and discovery

**Agent/Contributor**: Codex

**Work completed**:

- Read required repository, RQ-engine, test, contract, Culvert, package-template,
  and precedent documents.
- Verified RQ `1.16.2`, Redis DB 9, `batch` worker queue, existing polling auth
  modes, and the approved progress-field discrepancy.
- Created the package scaffold and preserved the unrelated untracked directory.

**Blockers encountered**: None.

**Next steps**: Obtain the required independent contract review outputs, then
disposition them and commit the standalone ancestor before production edits.

**Test results**: Documentation lint passed for the current checkpoint draft;
implementation tests and all runtime gates were intentionally deferred until
the operator authorized implementation.

### 2026-08-07 17:55 UTC: Governance blocker

**Agent/Contributor**: Codex

**Work completed**:

- Attempted two independent reviewer pairs with distinct reviewer roles:
  `rq_refactorer` + `qa_reviewer`, then `reviewer` + `security_reviewer`.
- Each agent remained in `running` state and returned no review text after
  bounded waits; all four were closed. No review evidence was fabricated.

**Blocker**: The contract-first standard requires two independent read-only
contract reviews and disposition before implementation. The reviewers were
unavailable, so no checkpoint commit or production edit is safe.

**Next steps**: Resume from the current scaffold when independent reviewer
agents can return exact findings and verdicts. This historical note is retained
for governance traceability; implementation later proceeded under explicit
operator authorization.

### 2026-08-07 19:10 UTC: Implementation, review, and validation

**Agent/Contributor**: Codex, with independent read-only reviewer subagents

**Work completed**:

- Added the optional exact `queue` object to successful jobstatus responses by
  collecting normalized queued candidates during the existing tree traversal.
- Added deterministic coverage for root, child, finalizer, mixed-origin,
  omission, race, enum/string status, disclosure, duplicate-entry, Redis-error,
  and one-ordered-read large-tree behavior.
- Updated RQ, rq-engine, and current Culvert documentation without modifying
  `submit_payload.py`, auth issuance, queue wiring, or frozen inventories.
- Remediated duplicate-offset selection and module stubs in `97141ba44`.

**Review results**: Code, QA, and dedicated security reviews are recorded in
the three implementation artifacts. The only High/Medium implementation concern
was the one ordered snapshot, which is explicitly allowed by and documented as
an operator-approved contract limitation. The pre-existing forwarded-header
limiter concern is outside this package and unchanged.

**Validation results**: Combined focused tests passed 105 tests; post-remediation
implementation tests passed 70 tests; Culvert regressions passed 26 tests;
OpenAPI passed 10 tests; direct stubtest passed; graph, inventory, checklist,
broad-exception, docs-lint, and diff checks passed. Full-suite status: `wctl
run-pytest tests --maxfail=1` passed with 5,961 passed, 61 skipped, and 1,054
warnings in 13:03.

**Commits**: checkpoint `7ce0cf524`, implementation `a416e7dd7`, remediation
`97141ba44`, `7b5c6d67a`, closure `4565ec00b`.

## Watch List

- RQ 1.16.2 queue list access must remain one-pass for large descendant trees.
- The queue object must never be added to `jobinfo`.
- Existing frozen inventory and RQ dependency graph must remain unchanged.
