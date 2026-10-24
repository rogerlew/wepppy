# Roads GL Dashboard

Status: accepted operator decisions; independent contract review and disposition complete.
Runtime implementation, checkpoint commit and deployment are not part of this review turn.

## Purpose and scope

Expose current Roads soil detachment on prepared road centerlines and a visible
Baseline/Roads output-scope switch. The existing dashboard supports scoped URLs
but has no segment renderer or scope selector. This is a new UI capability, not
a failed Roads model rerun. The reported clogging-starch rerun has 39 prepared
lines and 34 summary rows; existing artifacts are read-only review evidence.

The operator accepted area-weighted full-profile rates, including labeled mixed
profiles; excluded remainder lines and inferred MOFE fill/buffer/land-use geometry;
selected the existing jet2 palette; and accepted recommended availability and
linear scaling. Current authority is the canonical Roads dashboard contract.

## Complexity and compatibility budget

Reuse the existing dashboard, authorized browse/query transports, native/server
CRS transformation and upstream Roads lifecycle. No new service, queue, datastore,
dependency, identity protocol, model calculation, artifact schema, auth policy,
or model rerun. Baseline remains the default. The new display aggregation does
not rewrite source summaries or represent incremental road impact. Combined/batch
dashboards gain no scope semantics; child runs use their own data.

## Security impact

High: a new consumer joins authorized project artifacts across asynchronous reads
and exposes uploaded labels/geometry. Existing auth and lifecycle checks must
remain authoritative. Dedicated security review is required, including valid-state
noninterference; no new privileges are proposed. This is contract review, not
evidence that future runtime boundaries pass.

## Acceptance and authority

This turn completes when independent correctness/security/UX findings are
dispositioned, reviewers confirm medium/high closure, ADR and canonical amendments
agree, and documentation checks pass. Retain review timestamps and file hashes.
Those review gates passed with nine findings closed; the prepared checkpoint is
uncommitted. This is specification approval only, not implementation acceptance.
Implementation requires the standalone ancestor checkpoint under the contract-first
standard and an implementation ExecPlan. The earlier async-catalog commit/push
authorization does not authorize committing this new package automatically.

Future artifact acceptance follows actual generated geometry, manifest and summary
into authorized queries and the browser. Verify joins, units, legend, keyboard
details, scope transitions and stale-result rejection; job success and screenshots
alone do not establish numeric correctness. Preserve browse/download/archive access.

## Entry points

Review plan: [review_execplan.md](prompts/active/review_execplan.md).
Progress and dispositions: [tracker.md](tracker.md).
Decision checkpoint: [contract_decision.md](artifacts/2026-10-24_contract_decision.md).

