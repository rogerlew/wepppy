# Contract decision: RUNS-TTL-BULK-01

## Authority and scope

Starting implementation revision: `f9610c8a1a1f75e384acf43f2023a493da6cd750`.
Operator explicitly requested: "Automatic deletion column on the runs/ page
should be sortable. users should be able to sort in ascending order and see
upcoming runs that will be deleted. add a button to "Disable Automated Deletion
for Selected" next to the Delete Selected button" (2026-11-05).
This is an intended enhancement, superseding the domain's no-sort requirement,
not a conformance fix. Operator granted checkpoint commit authority with "yes" on 2026-11-05.

## Applicable canonical contracts

- `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md`: sorting and bulk presentation amendment.
- `docs/ui-docs/contracts/project-ttl-control-contract.md`: reuse setter for selected runs.
- `docs/schemas/run-catalog-projection-contract.md`: additive sort parity in both catalog modes; no projection rollout.
- `docs/ui-docs/controller-contract.md`: preserve selection, safe rendering, observable errors and tests-first convention.
- `docs/schemas/weppcloud-csrf-contract.md`: unchanged same-origin POST plus CSRF header.
- `docs/schemas/request-payload-contract.md`: unchanged `ttl_disabled: true` JSON payload.
- `docs/schemas/rq-response-contract.md`: unchanged success/error envelope; no enqueue changes.

## Normative delta and rationale

Allow `sort=ttl_deletion_at`. Sort dates chronologically ascending/descending,
nulls last in both directions, including overdue dates. First header click is
ascending. Preserve other sort defaults, authorization, alias scope and paging.
Chronological ordering exposes the next eligible runs without inventing a
future-only filter or incorrectly sorting by Last Modified.

Place the exact requested button label beside Delete selected. Use the existing
visible checked-row selection (including its readonly restrictions). With no
selection or while the protection request batch is in progress, disable the
button. Snapshot the selection; send one sequential existing setter request
per run with JSON `ttl_disabled: true`, same-origin credentials and CSRF header.
Report progress and final success/failure counts with failed run identifiers.
Mark a row protected only after a valid successful setter response; leave failures
unchanged and retryable. Keep scope transitions from applying old responses to
newly loaded rows. Do not introduce a bulk endpoint or atomicity claim.

## Compatibility, data and security

Additive sort key; no persisted schema or parameterization change. Existing
setter owns TTL initialization, normalization and user audit. Run authorization
must be checked independently by each existing endpoint, including admin alias
views. Never infer write permission from catalog presence. No new queue edges,
filesystem operations, dependencies or destructive action. Security tier high
because the route sort allowlist changes; final dedicated security review required.
Existing uncommitted work and scheduler pause are excluded from this package.

## Valid states and regression evidence

Empty/no-selection: disabled action and ordinary empty table. Populated mixed
active/disabled/unknown metadata: chronological dates first, nulls last. Missing,
empty, legacy and malformed TTL: retain existing setter normalization, no new
client rejection. Readonly rows retain existing unselectable behavior. Mixed
success and authorization/CSRF/network/invalid-response failures: explicit partial
result, failed rows remain retryable and never falsely protected. Hostile labels
and errors render as text; URLs encode run/config and preserve site prefix.

Verify sort alias and both directions, legacy and projected catalog sorting,
rendered header/adjacent button, actual browser handler requests and partial
failure behavior. Retain existing real TTL-file/authorization/CSRF route tests
because the persistence boundary is reused unchanged. Run focused pytest,
frontend lint/test, broad pytest --maxfail=1 and docs lint. Deployment is separate.


Protection confirmation requires a non-null returned TTL object with
`delete_state: "active"` and either `policy: "disabled"` with
`user_disabled: true`, or `policy: "excluded"` with `disabled_reason: "batch"`,
as well as the successful response's `ttl_disabled: true`. Existing batch
exclusion is a successful protected outcome, not an invalid state. A missing run may return
null TTL; queued/trash/purged states cannot be reported as protected because
this action cannot stop or undo deletion already started. Report these as
unconfirmed failures with a specific explanation, retaining the existing server
behavior. Cover each response state in browser-handler tests. The batch/read-only
exclusions and existing setter normalization remain unchanged.

The existing non-job TTL state setter retains its `Content` response payload;
the RQ contract's job-submission success envelope is not a new transport for
this action. No envelope migration or shared-helper change is in scope.

## Reviews and disposition

Two independent read-only contract reviews accepted after correction; see
[reviews and disposition](2026-11-05_contract_reviews.md). No unresolved
high/medium contract findings. Operator granted checkpoint commit authority with "yes" on 2026-11-05. Implementation
conformance pending; no implementation commit may precede the accepted ancestor.
