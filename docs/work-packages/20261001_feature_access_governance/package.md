# Feature access governance

Status: Open; M1/M2/M3 complete locally. M4/M5 and production rollout remain open, 2026-10-02 UTC.

Timezone: UTC

## Overview

Align WEPPcloud with the operator-directed feature governance amendment: let unentitled users inspect limited features on public projects read-only, provide PowerUser self-service, and let one maintainer administer internal feature groups with reasons and timestamps. OpenET and Batch each begin with a group containing only the designated maintainer. Reconcile human Culvert access while preserving its authorized service integration.

The starting implementation revision is `45a39a8337d37c7f7d30087ff4d23c03610072b3`. The [assessment](../../dev-notes/feature-maturity-governance-implementation-assessment.md) retains the source inventory and 275-test baseline. The [canonical contract](../../schemas/feature-access-governance-contract.md) owns intended behavior; this package is an execution record.

## Scope

Include public inspection/action separation, auditable groups and membership, versioned onboarding, automatic PowerUser approval, current server-side group checks, conservative multi-OFE maturity, internal endpoint/data parity, additive database migration and workflow acceptance. Amend affected user/developer/operator documentation together. FA-02 explicitly permits sharing results from permitted use; the embargo restricts feature operation only. Preserve private-resource and sensitive-file controls.

Preserve ordinary anonymous creation and functionality. Exclude new global writer gates, creator credentials and legacy ownerless-run recovery. Exclude PowerUser suspension, reapplication and permanent revocation; new identity providers/services/queues; model formulas/defaults; blanket role hierarchy changes; new anonymous Culvert roots; automatic public release of private resources; credential rotation/TTL changes; and production deployment during the current documentation task. A multi-role review queue is explicitly excluded from access administration.

## Complexity budget

Reuse Flask-Security, SQLAlchemy/Alembic, the existing account database, registry, JWT/CSRF/response helpers and UI patterns. Permit groups, memberships, access-event history and onboarding-acceptance records in that database, one shared access module and bounded profile/admin UI endpoints. No new external dependency or infrastructure is permitted.

Test ordinary request-time membership queries first. Escalate only after retained evidence shows they miss actual acceptance conditions. Group management must stay a simple add/remove-with-reason operation; technical implementation reviews are not additional operational reviewers.

## Implementation fidelity and evidence

Target faithful wiring into the real profile, public run, feature actions, API and data paths. A standalone group model/helper does not complete the implementation. Preserve legacy role paths where FA-01 says so; intentionally replace them for group-only features. Validate both source behavior and generated output under the actual service identities before any rollout claim.

## Generated artifact validation gate

Applicable: yes, because access spans model execution, generated reports and artifact delivery. Trace an authorized request through persisted membership and project state, prepared model inputs, queue/job identity, fresh output and the read-only public result. Exercise actual database commits/readback and at least one real internal workflow. Verify a denied direct action creates no mutation/job and a new inspect-only restricted-feature view creates no missing feature controller state. Test shared retained contrast/PATH-CE results through direct, query and archive paths as well as named reports; test actual private-resource denial separately.

Highest current completion claim: M1/M2 account records, group administration,
acknowledgment and initialization are complete. M3 sharing reconciliation,
restricted action/data admission and private SQL/D-Tale containment are complete
locally at candidate `23c2f27fe`. Production-equivalent local service/browser
acceptance and final independent correctness/security reviews pass with zero
unresolved findings. PowerUser self-service, conservative maturity and production
rollout remain open.

## Security and correctness gates

Security impact: high (privilege assignment, group enforcement, JWT/session identity, public data and restricted actions). Dedicated independent security and correctness review artifacts are required before runtime closeout. The [review gate record](artifacts/2026-10-01_review_gates.md) links independent prepared-plan reviews and confirmed fixes. Milestone-zero correctness/security reviews passed with no unresolved High/Medium findings; implementation evidence remains pending.

Follow `docs/standards/contract-first-change-standard.md`: resolve the complete surface matrix, obtain two independent read-only contract reviews and disposition findings, then record the standalone ancestor commit before runtime changes. No reviewer may approve their own amendment. This engineering gate remains separate from the user-directed single-maintainer membership workflow.

## Success criteria

- The canonical contract and each affected shared/domain contract agree on reads, actions and public embargo handling.
- A normal authenticated user completes the two-question PowerUser flow with atomic, versioned evidence and no internal action grant.
- A maintainer adds/removes a named group member with a reason; history survives removal and changed memberships affect subsequent admissions even with old JWTs.
- OpenET and Batch enforce their separate groups with only the designated account initially admitted; broad roles cannot execute either feature without membership.
- Public retained feature views are readable without restricted execution or feature initialization; unauthorized restricted actions are denied.
- Culvert submit/retry/finalize/poll/cancel/browse/download retain the explicitly inventoried integration behavior and resource boundaries.
- The conservative override preserves Experimental/Internal/Deprecated labels.
- Meaningful database, endpoint, browser, accessibility and artifact evidence passes; independent medium/high findings are closed.

## Dependencies and gates

Milestone zero records per-deployment account identity, non-secret Culvert metadata, the feature-only scope, exact protected data surfaces and mixed-bundle behavior. Read-only verification found the configured Culvert token expired; operator renewal and positive integration evidence are later rollout prerequisites. FA-02 resolves the formerly reserved result-sharing question and supersedes M0's feature-derived data embargo; retained results may be shared under normal resource rules. PowerUser sanctions are not a dependency.

Parameterization change: no. ADR-0080 records governance, not numerical parameter changes. RQ graph checks apply only if implementation proves queue wiring changes necessary; none is planned.

## Deliverables and next action

Use the [active ExecPlan](prompts/active/feature_access_governance_execplan.md), [tracker](tracker.md), [contract decision](artifacts/2026-10-01_contract_decision.md) and [surface inventory](artifacts/2026-10-01_surface_inventory.md). M4 is the active milestone. Source investigation and bounded review evidence are in [the M0 record](artifacts/2026-10-01_milestone_zero.md); operator inputs and deployed identity investigation are resolved. M3 closeout is recorded in the [service/browser acceptance](artifacts/2026-10-02_m3_service_browser_acceptance.md) and [final reviews](artifacts/2026-10-02_m3_final_reviews.md).

Milestone-one implementation and validation details: [account records](../../dev-notes/feature-access-records.md), [correctness review](artifacts/2026-10-01_m1_correctness_review.md), and [security review](artifacts/2026-10-01_m1_security_review.md). No shared schema, membership or credential mutation is included in this implementation step.
