# Tracker - Run Archive Consistency and Symlink Hardening

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-02 17:25 UTC
**Current phase**: Contract discovery and decision
**Last updated**: 2026-08-02 17:25 UTC
**Next milestone**: Ratify and commit the contract checkpoint before code edits
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/2026-08-02_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Inventory all archive readers and same-run filesystem mutation entry
  points; classify participants, lock order, queue, duration, and cancellation.
- [ ] Characterize archive contents for ordinary files, valid directory/file
  symlinks, broken links, cross-run links, and disappearing entries.
- [ ] Draft `artifacts/2026-08-02_contract_decision.md` and all required
  canonical contract amendments.
- [ ] Obtain operator approval and two independent contract reviews; disposition
  findings and commit the checkpoint as a standalone ancestor.
- [ ] Write deterministic failing regressions for the production overlap and
  broken-link signatures.
- [ ] Implement the smallest approved coordination and symlink-policy changes.
- [ ] Update affected operator/developer documentation and RQ dependency catalog
  if queue wiring changes.
- [ ] Run focused and broad validation and generated ZIP/restore checks.
- [ ] Complete independent code, QA, and security reviews.
- [ ] Canary on Forest, deploy through the production runbook when authorized,
  and observe health/danger signals for 30 days.

### In Progress

- [ ] Contract and mutation-surface discovery.

### Blocked

- [ ] Production implementation is blocked until the contract-first checkpoint
  is approved, independently reviewed, dispositioned, and committed.

### Done

- [x] Captured production job, timing, traceback, filesystem, and service-health
  evidence (2026-08-02 17:15 UTC).
- [x] Distinguished the concurrent deletion defect from the already-broken
  scenario symlink (2026-08-02 17:15 UTC).
- [x] Searched and recorded relevant hardening, NoDb, NoDir, and RQ precedent
  (2026-08-02 17:25 UTC).
- [x] Scaffolded package, tracker, active ExecPlan, and security-review artifact
  (2026-08-02 17:25 UTC).

## Incident Timeline

- **2026-08-02 16:39:10 UTC** – First archive job
  `65717fb6-db0b-47e8-aa28-602dc798a18b` started.
- **2026-08-02 16:51:45 UTC** – First archive failed on the broken
  `prescribed_fire/climate` link.
- **2026-08-02 17:06:04 UTC** – `delete_omni_contrasts_rq` job
  `ae0ea873-ef03-410a-9a9f-d7e6e6c791e0` started.
- **2026-08-02 17:06:21 UTC** – Second archive job
  `b4eeaff3-f2ff-4107-a0ff-418638cb15dd` started while deletion was active.
- **2026-08-02 17:08:53 UTC** – Contrast deletion completed successfully.
- **2026-08-02 17:09:38 UTC** – Second archive failed on the same broken link.
- **2026-08-02 17:15 UTC** – `wepp1` services were confirmed running; the link
  target run was confirmed absent in the worker container.

## Decisions

- **2026-08-02 17:25 UTC** – Treat concurrent mutation and broken symlinks as
  separate workstreams under one package. Rationale: the second archive
  overlapped deletion, but the first archive proved the link was already broken.
- **2026-08-02 17:25 UTC** – Do not prescribe silent skip/retry behavior in the
  package brief. Rationale: representation and failure behavior are normative,
  security-sensitive choices requiring the contract-first checkpoint.
- **2026-08-02 17:25 UTC** – Classify security impact as high. Rationale: archive
  path traversal, cross-run symlinks, downloadable output, RQ concurrency, and
  run-data integrity are directly affected.
- **2026-08-02 17:25 UTC** – Require deterministic synchronization seams in
  tests instead of sleep-based races. Rationale: the regression must prove
  ordering without becoming flaky.

## Risks and Owners

| Risk | Severity | Mitigation | Owner | Status |
| --- | --- | --- | --- | --- |
| Incomplete mutation inventory leaves a race | High | Inventory enqueue and direct mutation sites before selecting the primitive | RQ/NoDb maintainer | Open |
| New lock deadlocks with NoDb/NoDir locks | High | Define global ordering and test contention, cancellation, and expiry | Implementer + reviewers | Open |
| Symlink policy leaks or silently omits data | High | Contract containment/representation first; adversarial security tests | Security reviewer | Open |
| Legacy Omni runs become unarchivable | Medium | Characterize valid historical links and define explicit compatibility | Omni maintainer | Open |
| TOCTOU remains after preflight | High | Revalidate at read boundary or use approved stable-snapshot mechanism | Implementer | Open |
| Queue latency increases | Medium | Measure wait/conflict duration and monitor guardrail signals | Operator | Open |

## Hardening Signal Log

- **Baseline**: two archive failures on one production run with the same raw
  `FileNotFoundError`; the second archive overlapped contrast deletion for about
  152 seconds.
- **Post-change automated signals**: pending exact race, symlink, cleanup, ZIP
  content, and restore regressions.
- **Post-deployment signal**: pending 30-day observation.
- **Danger signals observed**: current one-time NoDb lock-status check does not
  cover filesystem deletion outside the controller critical section.
- **Temporary callus register**: none authorized.

## Verification Checklist

- [ ] Contract checkpoint approved, reviewed twice, dispositioned, and committed
  before production code edits.
- [ ] `wctl run-pytest tests/rq/test_project_rq_archive.py --maxfail=1`
- [ ] Targeted Omni RQ/NoDb tests selected after mutation inventory.
- [ ] `wctl check-rq-graph` if enqueue/dependency wiring changes.
- [ ] Generated archive entries and restore behavior manually inspected.
- [ ] `wctl run-pytest tests --maxfail=1`
- [ ] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [ ] `wctl doc-lint --path docs/work-packages/20260802_archive_mutation_symlink_hardening`
- [ ] Affected durable docs linted.
- [ ] `git diff --check`
- [ ] Code review has no unresolved medium/high findings.
- [ ] QA review has no unresolved medium/high findings.
- [ ] Security review has no unresolved medium/high findings.
- [ ] Forest canary and rollback rehearsal complete.
- [ ] Production observation window complete.

## Progress Notes

### 2026-08-02 17:25 UTC: Incident scoping and package creation

**Agent/Contributor**: Codex

**Work completed**:

- Read canonical RQ failure evidence and correlated production worker logs.
- Confirmed `wepp1` identity, service health, broken link, and absent target.
- Confirmed the archive/deletion overlap and the earlier independent link
  failure.
- Created this package under the hardening and contract-first standards.

**Next steps**:

1. Complete the participant and symlink behavior inventories.
2. Draft the contract decision with explicit alternatives and compatibility
   evidence.
3. Stop before implementation until the checkpoint gate is satisfied.

**Test results**: Documentation-only scoping; scoped documentation lint pending.

## Watch List

- Whether other cleanup functions perform filesystem mutation outside their
  NoDb lock.
- Whether archive duration makes a Redis lease heartbeat or another primitive
  necessary.
- Existing semantics for valid directory symlinks, which `os.walk` may classify
  differently from broken links.
- Whether restore must reproduce allowed links or only materialized content.
