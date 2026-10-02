# Milestone one security review

## Metadata and triage

Reviewer: `/root/contract_security`, independent read-only review, 2026-10-01.
Base revision: `6cb552943`; contract ancestor: `d3639f970`. Scope: new account
schema/store/evaluator, app model registration, additive migration, registry
metadata and direct PostgreSQL tests. Security impact: **high** for the package;
M1 adds unconnected authorization infrastructure with no route/token changes.
[Correctness review](2026-10-01_m1_correctness_review.md) owns valid-state coverage.

Threat model: future adapters must verify identity, token scope/resource, expiry
and revocation before constructing trusted decision inputs. Neither a numeric
service subject nor token `groups` is a verified human identity/entitlement.
This stage does not validate or wire those adapters and cannot approve them.

## Findings and verdict

Reviewer found **zero unresolved High/Medium findings** in the final M1 scope.
The reviewer checked the correctness fixes for dependency error propagation,
contrast-derived inspection and expiration after database waits. No risks were
waived. Verdict: **pass for M1 substrate**, not approval to deploy or enable
self-service. Direct post-fix PostgreSQL validation completed: 26 tests passed, followed by 180 account/registry cases after the late metadata fix;
the reviewer assessed tests/source but did not independently rerun them.

## Late finding and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| M1-S01 | Medium | Omitting both metadata fields on a governed feature restored its legacy-role path | Shared required-feature inventory now rejects missing/null metadata in the registry and evaluator, including direct dependency specs. Regression cases cover all six and preserve unrelated omissions; both reviewers independently confirmed closure; final 180-case run passed |

The reviewer acknowledged that the initial pass missed this case. The author
raised it during final inspection; no deployment or consumer wiring occurred.

## Surface checks

- Valid states: ordinary anonymous actions and non-embargoed reads remain on
  existing consumers; new public read decisions avoid membership lookup.
- Authority: membership writes require a current active Root actor. Group-only
  features have no broad-role bypass; readonly, resource, backend and prerequisite
  checks remain conjunctive. Integration authority is explicit and Culvert-only.
- Current membership: database lookups, expiry and acknowledgment are enforced;
  removal affects later admission without relying on token group claims.
- Persistence: membership/event writes are one transaction, absent-row duplicates
  serialize on the account row, injected audit failure rolls back, and retained
  event snapshots have no cascading account/group foreign keys.
- Migration/rollback: definitions only, no user grants; schema matches model
  metadata. Destructive downgrade is explicitly refused to retain audit history.
- Input/error handling: IDs, operation, reason and aware dates are validated;
  SQL errors deny explicitly with operator logs rather than role fallback.
- Secrets: no credentials created, rotated or committed. Tests use existing
  account-engine configuration and isolated randomly named schemas.
- Session/CSRF/HTTP/output/path/queue boundaries: unchanged and not claimed as
  implemented. No worker/job wiring, frontend or filesystem access change.

## Remaining gates

Trusted principal/resource adapters, HTTP enforcement, PowerUser transactions,
real UI/model/artifact workflows, Culvert credential renewal/live compatibility,
backup/rollout and implementation reviews of later milestones remain required.
The full-suite result and any baseline failure are recorded separately in the
tracker; M1 source review does not replace those validation results.
