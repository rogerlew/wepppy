# Tracker — Deferred Job Retry Recovery

## Status

**Phase**: Dependency regression correction complete
**Last updated**: 2026-08-23 UTC

## Task Board

### In Progress

- [x] Ratify strict required-output dependency semantics while retaining
  automatic deferred-graph replacement, explicit terminal finalizers, and only
  the enumerated AgFields, Omni-contrast, and WBT-request serialization edges.
- [x] Complete dual corrective checkpoint reviews and disposition with no
  remaining High/Medium findings.
- [x] Complete fresh dual review and disposition for the WBT request-
  serialization addendum discovered during focused implementation validation.
- [x] Restore conforming dependency wiring, regenerate graph artifacts, and
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
  observers/finalizers and reviewed independent serialization edges.

- **2026-08-23 UTC** — Focused real-RQ validation identified a third existing
  serialization family: a prior WBT request tail serializes same-run mutation
  ownership for the next independent request. Codex classified that prior-tail
  edge as tolerant and the request's build-to-abstraction edge as strict,
  approved by fresh independent correctness and security review with no
  remaining High or Medium findings.

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

## Corrective evidence — 2026-08-23 UTC

- Focused dependency/controller validation: 165 passed; the added SWAT strict-
  dependency assertion passed separately; `wctl check-rq-graph` passed with 143
  generated edges.
- Same-revision local cutover occurred only after `wctl rq-info` reported zero
  queued/executing jobs and 11 idle workers across all three queues.
- `POST /api/runs/soft-boiled-copying/disturbed9002_wbt/run-wepp` returned
  replacement `06c141e3-ef3f-4dfb-98fd-9d650135a732`. Missing soils failed
  `_prep_managements_rq`; 13 downstream jobs remained deferred with
  `started_at=null`.
- Repeating the ordinary POST returned distinct replacement
  `18cd9c41-039f-482e-904f-e5edb0182a80` and canceled all 13 never-started
  deferred jobs from the superseded tree. The replacement reproduced one
  required-stage failure, three independent prep successes, and 13
  never-started deferred descendants.
- Final-tree validation passed 6,663 tests with 63 skips in 894.99 seconds.
  Focused real-RQ coverage includes strict and tolerant dependency behavior,
  Batch-to-Omni cleanup, WBT external-tail containment and retry splicing, and
  atomic eager finalizer release. The 143-edge graph, stub, broad-exception,
  and diff gates passed.
- Final same-working-tree cutover completed at 2026-08-23T20:19:51Z after
  zero queued/executing jobs, 11 idle workers, and empty scheduled registries
  for `default`, `batch`, and `fork-archive`. The restarted services were
  `weppcloud`, `rq-engine`, `scheduler`, and all three RQ worker families;
  `docker compose config --quiet` validated the rollback configuration.
- `POST /api/runs/soft-boiled-copying/disturbed9002_wbt/run-wepp` returned HTTP
  200 and job `a3dfef60-e322-4cb1-96ac-bc1d863a1819`. Its missing-soils tree
  reached aggregate `failed` with 13 deferred jobs, all never-started.
  Repeating the same ordinary POST returned HTTP 200 and distinct job
  `e19371e4-63c7-4832-a262-b589900c72d6`; the original tree's 13 deferred jobs
  became canceled without manual cancellation, and the replacement entered
  `started`. The short-lived service token was removed after validation.
