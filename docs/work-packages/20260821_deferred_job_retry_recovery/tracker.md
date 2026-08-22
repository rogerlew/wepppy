# Tracker — Deferred Job Retry Recovery

## Status

**Phase**: Contract checkpoint approved; standalone ancestor pending
**Last updated**: 2026-08-21 UTC

## Task Board

### In Progress

- [ ] Commit the approved SURF-20A / GOV-00A-M1J documentation-only ancestor.

### Pending

- [ ] Add the shared deferred-job reaping primitive with direct Redis/RQ evidence.
- [ ] Update every in-scope backend admission/cache guard.
- [ ] Make shared controller buttons retryable on `deferred` and rebuild assets.
- [ ] Add focused regression coverage and run quality gates.
- [ ] Complete correctness, security, code, and QA review.

### Blocked

- Production diagnosis of `gastric-tall` is not required for implementation and
  remains read-only unless the operator separately authorizes a mutation.

## Decisions

- **2026-08-21 UTC** — The operator explicitly required one broad invariant:
  deferred jobs never add user friction, never block resubmission, and are
  cleared by the resubmission itself. Queued, started, and scheduled work keeps
  existing duplicate protection.
- **2026-08-21 UTC** — Centralize destructive RQ cleanup in one tested helper;
  controller-specific guards call it rather than implementing partial registry
  cleanup independently.

## Notes — 2026-08-21 UTC

- Confirmed the earlier WEPP-only fix deliberately allowed viable deferred jobs
  to block and therefore cannot satisfy the new cross-controller requirement.
- Inventory found additional deferred-as-active guards in Roads, AgFields,
  Path CE, migration, archive/render, and the shared JavaScript controller base.
- Initial independent checkpoint reviews found four High findings each: the
  source boundary was not finite, ordinary Redis pipelines could race RQ job
  promotion, exact-job cleanup omitted graph descendants, and ownership plus
  security/governance evidence were incomplete. All are accepted; corrected
  checkpoint received both post-fix approvals with no remaining High/Medium
  findings on 2026-08-21.
