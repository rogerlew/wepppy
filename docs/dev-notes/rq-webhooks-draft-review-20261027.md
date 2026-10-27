# RQ webhook draft review and disposition

Date: 2026-10-27. Scope: independent read-only review of the
[discussion draft](rq-webhooks-contract-draft.md). No implementation, runtime
changes or contract ratification were requested or performed.

Reviewers: `webhook_correctness` (reviewer), `webhook_security`
(security_reviewer), and `webhook_operations` (ops_security_control_agent).
The author dispositions their findings below. Severity describes prospective
design risk, not a deployed vulnerability. Draft closure means the omission was
addressed with a requirement or explicit decision gate; implementation evidence
and operator choices remain outstanding.

## Findings and author disposition

| ID | Severity | Finding | Disposition and amended draft section |
| --- | --- | --- | --- |
| WH-COR-01 | Medium | Ambiguous subscription closure could change an event during delayed delivery/requeue | Accepted; Proposed event semantics closes observation atomically with unique immutable event creation, independently of delivery. Acceptance adds competing observers and requeue. |
| WH-COR-02 | Medium | Raw job success can disagree legitimately with aggregate polling status | Accepted; Proposed event semantics adds `subject_type: rq_job` and parent/child explanation; acceptance requires the distinction. |
| WH-COR-03 | Medium | Capture reliability and delivery lifetime were conflated | Accepted; Proposed event semantics separates observation deadlines/outage bounds from delivery age starting at event capture, and exposes observation failures. Numeric policies remain open. |
| WH-COR-04 | Medium | Post-enqueue subscriptions to terminal jobs and ambiguous creation were unspecified | Accepted; Proposed event semantics proposes immediate authorized capture, explicit rejection and principal/operation-scoped idempotency with conflict handling. API selection remains open. |
| WH-SEC-01 | High | Stable identity alone extends narrow credentials into durable outbound authority | Accepted; Ownership and endpoint lifecycle requires bounded resource/event/endpoint grants, token-class eligibility and revocation rules; unknown authorization pauses delivery. Exact grant policy remains a ratification gate. |
| WH-SEC-02 | Medium | Owning an endpoint record does not prove control of a public destination | Accepted; Ownership and endpoint lifecycle requires activation-policy selection: challenge or operator approval, with no event data before activation and URL-change revalidation. Arbitrary targets require explicit risk acceptance. |
| WH-SEC-03 | Medium | Client abuse can exhaust shared observer/delivery capacity | Accepted; Ownership and endpoint lifecycle requires per-client/global quotas, rates, payload limits, fairness and explicit rejection without affecting accepted computations. Values remain open. |
| WH-SEC-04 | Medium | Existing encryption facility was assumed without evidence | Accepted; Delivery and destination security replaces the assumption with inventory/key-management gates, independent key material, recovery and disclosure policy. Missing keys stop notifications only. |
| OPS-01 | High | RQ registry read helpers can run cleanup and change tasking | Accepted; Smallest implementation candidates prohibits observation-side mutation and cleanup, including TTL extension, and requires committed exact-job reads. Acceptance adds expired-started-entry noninterference. |
| OPS-02 | High | Persistence acknowledgment does not guarantee outcome capture or zero-loss recovery | Accepted; Smallest implementation candidates separates acceptance/capture/receiver acknowledgment, requires recovery point/loss-window disclosure and verification of Redis persistence. No shared persistence change authorized. |
| OPS-03 | Medium | Saturation and indefinite deferred subscriptions lacked bounds | Accepted; Ownership and endpoint lifecycle adds lifetime/history/byte/count bounds and overload semantics. Acceptance adds sustained backlog and datastore pressure. |
| OPS-04 | Medium | Disable/rollback lacked lease, outstanding-event and schema semantics | Accepted; Smallest implementation candidates requires distinct admission/dispatch/component controls and a recovery runbook. Exact pause-age policy remains open; acceptance covers acknowledgment-loss restore. |
| OPS-05 | Medium | Prototype sequencing could authorize pre-checkpoint production edits | Accepted; Implementation milestones limits early probes to disposable synthetic isolated environments, excludes live data/endpoints/restarts, and requires a package before sustained work. |

Additional correctness clarification: receipts and observers must read committed
state, not callback-local `job._status`, which can precede a callback failure.
This is now explicit under Smallest implementation candidates.

## Evidence anchors

- Existing principal resolution is not scope/resource authorization:
  `wepppy/weppcloud/utils/feature_access_identity.py`,
  `wepppy/microservices/rq_engine/auth.py`.
- RQ 2.12 `BaseRegistry.get_job_ids(cleanup=True)` and
  `StartedJobRegistry.cleanup()` mutate state during default registry cleanup.
- `docker/redis-entrypoint.sh` supplies persistence defaults; actual deployment
  settings still require readback before making durability claims.
- `wepppy/config/secrets.py` and `docker/secrets/README.md` establish deployment
  secret retrieval, not an already-approved dynamic encryption facility.
- `docs/schemas/rq-response-contract.md` governs aggregate polling and the
  existing prohibition on exposed native webhooks during the runtime migration.

## Outstanding gates

Event scope, reliability level and endpoint API shape remain operator choices.
The observer design, storage, capacity/topology, grants/revocation, endpoint
activation, encryption, retention, retry numbers and rollback pause semantics
remain evaluation/ratification gates, not implicitly accepted defaults.

These reviews do not replace the two independent reviews of a final canonical
contract required by the contract-first standard. No work package was opened,
no ancestor checkpoint was committed and no implementation was authorized here.

## Re-review and validation

All three independent reviewers re-read the amended draft and this disposition
record. Correctness confirmed WH-COR-01 through WH-COR-04 addressed with no
residual drafting findings; security confirmed WH-SEC-01 through WH-SEC-04
addressed with no new findings; operations confirmed OPS-01 through OPS-05
addressed with no residual drafting gap. All explicitly withheld implementation
or final canonical-contract approval.

Both documents passed `wctl doc-lint --path <file>` with zero errors and warnings.
Spelling previews using `diff -u <file> <(uk2us <file>)` produced no differences.
No runtime tests were run because this change only revises discussion documents.
