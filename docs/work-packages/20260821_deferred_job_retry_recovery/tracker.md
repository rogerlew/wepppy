# Tracker — Deferred Job Retry Recovery

## Status

**Phase**: Dependency regression correction in progress
**Last updated**: 2026-08-23 UTC

## Task Board

### In Progress

- [ ] Ratify strict required-output dependency semantics while retaining
  automatic deferred-graph replacement, explicit terminal finalizers, and only
  the enumerated AgFields/Omni-contrast independent serialization edges.
- [x] Complete dual corrective checkpoint reviews and disposition with no
  remaining High/Medium findings.
- [ ] Restore conforming dependency wiring, regenerate graph artifacts, and
  complete focused, broad, and independent review gates.

### Pending

- [x] Add the shared deferred-job reaping primitive with direct Redis/RQ evidence.
- [x] Update every in-scope backend admission/cache guard.
- [x] Make shared controller buttons retryable on `deferred` and rebuild assets.
- [x] Add focused regression coverage and run focused quality gates.
- [x] Complete correctness, security, code, and QA review.
- [x] Add layered production-bound state/failure evidence for every matrix row,
  plus spanning destructive-ordering tests for fork replacement and archive deletion.

### Blocked

- Production diagnosis of `gastric-tall` is not required for implementation and
  remains read-only unless the operator separately authorizes a mutation.

## Decisions

- **2026-08-23 UTC** — After live job `5af82b08-f1af-4180-8613-9917d53ac3f0`
  demonstrated a cascade over absent soils, the operator explicitly classified
  downstream execution after required-parent failure as a regression. Strict
  required-output dependencies and frictionless deferred retry are separate,
  simultaneous requirements; failure tolerance is limited to explicit terminal
  observers/finalizers and the two enumerated independent serialization families.

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
- Final security review exposed and drove closure of pre-WATCH association and
  late-receipt-creation races; job identity is now watched before association,
  and missing receipts are validated transactionally before replacement.
- Final validation passed 6,636 Python tests (62 skipped; 12 subtests), 768
  frontend tests, the RQ dependency graph gate, stub checks, documentation lint,
  and changed-file broad-exception enforcement. All four implementation reviews
  closed with no remaining High/Medium runtime findings.
