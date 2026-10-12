# Security Review — Portland combined viewer

## Metadata

- Package: `docs/work-packages/20261012_portland_combined_viewer/`.
- Prepared: 2026-10-12 08:21 UTC; reviewer: unassigned, must be independent.
- Scope: collection admission, PortlandGroup/resource binding, downstream query/geometry/report/file reads, generator input/CSRF, and derived artifact paths.
- Starting revision: `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`; candidate revision: pending.
- Related: [correctness review](2026-10-12_correctness_review.md), [decision draft](2026-10-12_contract_decision.md).

## Security Triage Decision

High impact; dedicated review required. Group membership must bind the caller to authoritative Portland resources, not arbitrary submitted IDs. No new PUBLIC markers, membership assignments, feature entitlements, or role privileges. Existing valid grants and supported legacy data must remain usable. This artifact is a review scaffold; no inspection or approval is claimed.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Pending review | Unassessed | All changed surfaces | Implementation does not yet exist | Scaffold only | Populate from independent review | Not reviewed |

## Surface Checks

- [ ] Valid-state noninterference: member, public, owner/admin, empty generator, legacy artifacts, and missing optional variables behave as contracted.
- [ ] Current membership and trusted resource association are enforced per run; mixed unauthorized collections and stale memberships cannot leak data.
- [ ] Session/user/service token paths preserve signature, audience, expiry, resource scope, and established identity semantics; no token-supplied group grants.
- [ ] CSRF remains enforced for generator POST; credentials are not placed in share URLs or artifacts.
- [ ] Run IDs, configuration, title, JSON parameters, bounds, and ranges are validated and safely rendered; traversal and script injection are rejected.
- [ ] Geometry, catalog, value queries, popups, and consumed browse/download paths cannot bypass collection authorization.
- [ ] Direct unmocked tests demonstrate both valid admission and hostile rejection at every changed auth/path boundary.
- [ ] File generation is contained to approved roots, preserves original data and permissions, and has a bounded retry/rollback manifest.
- [ ] Queue/subprocess surfaces: verify no change; apply full template checks if scope expands.
- [ ] Agent/MCP surfaces: verify no privilege expansion; any credential transport used by consumers retains current scope.
- [ ] Dependencies/CI/deployment: no new infrastructure or dependency; inspected canonical deploy path and production-equivalent identity evidence retained.
- [ ] Operational logs and review artifacts contain no tokens or private account dumps; failure responses do not disclose unauthorized metadata.

## Verdict

Gate status: pending (not passed). Finding counts: unassessed, not zero. Release recommendation: hold until independent review and closure of all medium/high findings. Residual-risk acceptance requires reviewer recommendation and explicit package-owner acknowledgment.

## Sign-off

Reviewer/date, reviewed revision, evidence links, and owner acknowledgment: pending. Security review does not replace correctness/UX review or the two contract checkpoint reviews.
