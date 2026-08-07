# Tracker – Advisory Queue Rank in RQ Job Status

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-07 17:38 UTC
**Current phase**: Discovery / Contract Checkpoint
**Last updated**: 2026-08-07 17:38 UTC
**Next milestone**: Complete independent contract reviews and commit the checkpoint ancestor.
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260807_rq_jobstatus_queue_rank/artifacts/20260807_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Implement queue snapshot and regression tests after checkpoint ancestor.
- [ ] Run focused and repository validation gates.
- [ ] Obtain and disposition implementation code, QA, and security reviews.

### In Progress

- [x] Create package scaffold and register it as In Progress (2026-08-07 17:38 UTC).
- [x] Record starting revision and dirty-tree inventory (2026-08-07 17:38 UTC).
- [ ] Amend canonical contracts and complete checkpoint reviews.

### Blocked

- [ ] Two independent read-only contract reviewers are unavailable: four
  reviewer agents were attempted in two independent pairs; each remained
  `running` without returning review output after bounded waits and was closed.
  Contract-first implementation is blocked until independent review outputs
  are available.

### Done

- None yet.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Unrelated queued job ID disclosure | High | Low | Candidate IDs come only from registered tree links; return only selected candidate | Open |
| Polling cost amplified by large trees | High | Medium | One traversal and one ordered queue snapshot for a single-origin tree | Open |
| Queue/status race produces stale rank | Medium | High | Omit or choose remaining candidate; never fail authoritative status | Open |
| Auth/token behavior changes accidentally | High | Low | Route/auth regression tests and explicit non-change review | Open |
| Full suite blocked by baseline failure | Medium | Medium | Run focused gates first and record exact unrelated blocker | Open |

## Verification Checklist

### Code Quality

- [ ] Focused RQ and route pytest suites pass.
- [ ] Full `wctl run-pytest tests --maxfail=1` is run or exact unrelated blocker recorded.
- [ ] Broad-exception enforcement and code-quality observability are recorded.
- [ ] `git diff --check` passes.

### Security

- [ ] High-impact triage and dedicated artifact are complete.
- [ ] No unresolved High/Medium security findings remain.
- [ ] Open/optional/required auth modes and rate limiting remain unchanged.
- [ ] Browse token remains browse/download-only.

### Documentation

- [ ] Canonical contracts, rq README, route usersum docs, and Culvert docs updated.
- [ ] All changed Markdown is linted.
- [ ] Package closure notes and review artifacts are complete.

### Testing

- [ ] Root, descendant, finalizer, mixed-origin, race, status-normalization,
  bounded-access, and disclosure cases are covered.
- [ ] Existing status/progress/diagnostic/error/timestamp/not-found behavior is
  explicitly preserved.
- [ ] OpenAPI contract suite passes without route-count or response-code changes.

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
implementation tests and all runtime gates are intentionally not run because
the required independent contract reviews are unavailable.

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
agents can return exact findings and verdicts.

## Watch List

- RQ 1.16.2 queue list access must remain one-pass for large descendant trees.
- The queue object must never be added to `jobinfo`.
- Existing frozen inventory and RQ dependency graph must remain unchanged.
