# Query catalog refresh contract decision

Date: 2026-10-23 UTC. Starting revision: `fc3234efc6da58ff1da896dfab5b2dd5875988c2`.
Status: independently reviewed checkpoint prepared; all findings closed 2026-10-23 20:20 UTC; no ancestor commit or implementation.

## Operator authority and exact delta

Operator: “we need a comprehensive analysis to figure out where the async can be safely deployed. that should be the preferred route. let's do this contract first. author the contract and dispatch agents to review and disposition changes”. This is explicit authority for async-preferred design, contract authorship, comprehensive classification and review/disposition. It is not a claim of operator acceptance of yet-unreviewed mechanics, commit permission or production deployment.

Amendment ID: QCAT-ASYNC-01. New canonical `docs/schemas/query-engine-catalog-refresh-contract.md` specifies explicit asynchronous producer requests, durable invalidation, one admitted job per exact project scope, no-lost-update acknowledgment, atomic coordinated publication, recovery, consumer barriers, lifecycle/auth preservation and runtime acceptance. Existing synchronous APIs are preserved, not globally rewritten. Source boundary is enumerated in `caller_matrix.md`; no source files change in this phase.

## Applicable canonical authority

| Contract | Delta or binding obligation |
| --- | --- |
| `docs/schemas/query-engine-catalog-refresh-contract.md` | New domain authority; all sections implementation pending. |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Add Derived query catalog refresh section; separate source commit from metadata readiness. |
| `docs/schemas/rq-response-contract.md` | Add Query-engine catalog maintenance section; canonical IDs, no replacement domain job response, safe job disclosure. |
| `docs/schemas/report-cache-freshness-contract.md` | Add Asynchronous catalog coexistence section; preserve consumed-source selection and cache checks. |
| `docs/ui-docs/contracts/gl-dashboard-flow-duration-contract.md` | Add Asynchronous catalog coexistence clarification: background publication invalidates held snapshot; preserve reload/refusal behavior. |
| `docs/ui-docs/contracts/combined-watershed-viewer-contract.md` | Add Query catalog coordination section preserving explicit offline READONLY exception while joining stable guard. |
| `docs/schemas/roads-preparation-lifecycle-contract.md`, `output-scope-contract.md` | Existing logical/physical source lifecycle and baseline/Roads separation remain binding. |
| `docs/schemas/weppcloud-browse-auth-contract.md` | Preserve exact run/path authorization and filtered catalog visibility. |
| `docs/schemas/weppcloudr-render-execution-contract.md` | Preserve interchange/render preparation and completion obligations. |
| `docs/schemas/nodir-thaw-freeze-contract.md` | No read-request cleanup; readonly/legacy behavior preserved. |
| `docs/standards/contract-first-change-standard.md` | Two independent reviews, disposition, standalone accepted ancestor before runtime edits. |
| Artifact observability / generated-artifact validation standards | Visible records, normal archives, real consumer readback and production-equivalent validation before deployment claims. |

WMesque and Runs catalog contracts are unchanged precedents. Existing security and lifecycle owners are not advanced or closed by this package.

## Rationale and rejected alternatives

Native scan in a submission caused process heartbeat starvation. Explicit async notification removes that work from producers. Global async replacement would break activation response contracts and immediate report queries. Bare queue deduplication loses invalidation during execution and after Redis loss. Redis-only lease checks cannot atomically fence NFS rename. The draft therefore distinguishes durable intent, admission and publication, preserving synchronous coordination and consumer barriers.

No additional service/queue/datastore is proposed. Native GIL release is required for retained web-serving scans before rollout and does not alone remove request work. Domain parameterization is unchanged; retry/backoff operational settings must be documented and reviewed before implementation, not invented as scientific defaults.

## Compatibility and regression plan

This phase changes only documentation. Future evolution is additive: catalog schema/model outputs stay compatible; async callers use a new interface; old synchronous return/error behavior remains; status metadata is additive. New visible refresh records require exact archive/restore and lifecycle-incarnation acceptance. Before migrating each A/A-C family, test actual published artifacts plus immediate UI/report consumer and finalizer. B/C callers retain contracts and join publication coordination.

See canonical implementation gates and caller matrix for real Redis/NFS races, stale reader caches, lost wakeups, failures, nested scopes, readonly and lifecycle coverage. No unit-only result may substitute for NFS/identity evidence. Current highest completion claim is analyzed/specification drafted, not implemented, validated in environment, deployed, repaired or incident resolved.

## Security and scope

High impact for future background path execution/public polling/lifecycle boundaries; dedicated read-only security review requested. Preserve existing identities, access and normal valid-state behavior. Exclude broad auth changes, scientific schema/formula changes, new public endpoints, new topology, unrelated packages and production repair.

## Discrepancy classification

Intended behavior change, not strict conformance restoration. Current synchronous semantics are retained unless the explicit migration permits a different producer notification. The reported defect motivates the bounded architectural change selected by the operator; it does not authorize silently broadening scientific or deployment scope.

## Reviews and ancestor

Independent correctness and security/operations reviewers approved the revised canonical design and matrix on 2026-10-23 20:20 UTC. All five correctness and five security/operations findings/clarifications are dispositioned and confirmed closed in the review artifacts. Primary author retained their findings and decisions. Checkpoint ancestor commit remains pending and must precede implementation. No commit is created in this contract-only task.

## Checkpoint authorization

2026-10-23 UTC: after receiving the completed contract and independent review disposition, the operator instructed “commit and scaffold work-package for execution”. This authorizes committing the reviewed checkpoint and preparing execution scaffolding. The checkpoint records the accepted async-preferred contract; implementation and production deployment have not been performed. The execution tracker will record this commit as the standalone ancestor.
