# Security review - Query-engine run access boundary

## Current implementation disposition (2026-11-11 UTC)

Independent local security review: PASS; no unresolved medium/high source findings.
See [implementation review dispositions](20261111_implementation_reviews.md).
Browser capacity/environment and deployment gates remain separate. The sections
below retain the initial planning assessment and are not a deployment receipt.


## Metadata

- **Package**: `docs/work-packages/20261110_query_engine_access_boundary/`
- **Initial planning reviewer**: unassigned; implementation author cannot self-approve.
- **Date**: 2026-11-10 Pacific / 2026-11-11 UTC.
- **Scope reviewed**: initial source and deployment assessment only.
- **Commit/branch context**: local `master` at `b3786ae7e`; fetched
  `origin/master` at `ef5b4e289`; no merge or branch switch.
- **Related artifacts**:
  - [Draft contract decision](20261110_contract_decision.md)
  - [Failure-class matrix](20261110_failure_class_matrix.md)
  - [Correctness review](20261110_correctness_review.md)

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the package changes public-route authorization, JWT and
  session-cookie transport, filesystem containment, CORS, and production ingress.
- **Threat model assumptions**:
  - Caddy is the public ingress to query-engine on wepp1.
  - Run identifiers are not secrets and cannot serve as authorization.
  - Private run records and generated datasets require current run access.
  - Catalog preparation may write cache artifacts and therefore must follow auth.
- **Valid states controls must preserve**: public anonymous reads; private
  owner/Admin/Root reads; approved service/bearer clients; documented ordinary,
  legacy, grouped, Omni, and playback identifiers; empty/catalog-absent runs.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-F1 | Critical | HTTP auth/filesystem | Ordinary query routes do not enforce run authorization and accept filesystem-shaped targets | `server.py`, `helpers.py`, `feature_access.py`, wepp1 Caddy | Complete this package and controlled rollout | Open |
| SEC-F1A | High | Browser session | Existing HttpOnly run cookie is not sent to `/query-engine`, so a denial-only guard would break private dashboards | `run_0_bp.py`, `browse_cookie.py` | Add exact query audience/path cookie without JS exposure | Open |
| SEC-F1B | High | Mutation/CSRF | Forced activation accepts GET and cookie-auth POST behavior is undefined | `server.py` route table and query console | Ratify POST/scope/same-origin contract and test it | Open |
| SEC-F1C | Medium | CORS | Query-engine permits wildcard origins and methods | `server.py:create_app` | Configure exact contracted origins/methods/headers | Open |

## Verdict

- **Gate status**: fail.
- **Unresolved findings**: Critical 1; High 2; Medium 1; Low 0.
- **Release recommendation**: hold. Decide immediate wepp1 containment; do not
  claim F1 closed from documentation or local tests.

## Surface Checks

### Auth, Session, and Authorization

- [ ] Every HTTP entry point authorizes before downstream work.
- [ ] Public/private, owner/unrelated, role, token class, audience, and scope are
      directly tested.
- [ ] Revocation and Redis session-marker behavior remain current.
- [ ] MCP scope/audience behavior remains independently enforced.

### Secrets and Credential Handling

- [ ] No token enters HTML, JavaScript, URLs, logs, or retained artifacts.
- [ ] Query cookie is Secure, HttpOnly, SameSite, short-lived, audience-specific,
      run-specific, and path-confined.
- [ ] Existing secret-file configuration remains required; no permissive fallback.

### Input Validation and Filesystem Boundary

- [ ] Route grammar rejects filesystem paths and malformed identifiers.
- [ ] Resolver and Redis cache results are contained after symlink resolution.
- [ ] Dataset paths remain inside the authorized run/parent-sharing contract.
- [ ] Denials occur before catalogs, datasets, or exception logs are touched.

### Network and Browser Boundary

- [ ] Exact CORS origin/method/header policy replaces wildcard production access.
- [ ] Explicit activation is POST-only and enforces scope plus contracted
      same-origin/CSRF controls for cookies.
- [ ] Errors disclose no private existence, ownership, path, query, or token data.

### Deployment and Incident Readiness

- [ ] Rendered wepp1 Caddy/Compose configuration is retained and reviewed.
- [ ] Production-equivalent identity, mounts, umask, Redis, and database pass.
- [ ] Rollback retains containment against the vulnerable revision.
- [ ] Fourteen-day signal owner and recurrence trigger are documented.

## Validation Evidence

- Automated checks run: documentation lint only during scaffold; runtime checks
  pending implementation.
- Manual checks run:
  - Source flow review - confirms ordinary guard omission and path fallbacks.
  - wepp1 configuration review - confirms direct public Caddy proxy path.
  - Browser token review - confirms current cookie path misses query-engine.
- Live production checks: none.

## Residual Risk

- The vulnerability remains present until a safe revision is deployed or ingress
  is contained.
- Unreviewed legacy/group/profile variants may regress under a simplistic root
  allowlist.
- Other audit findings remain separate and are not reduced by closing F1.

## Sign-off

- **Security reviewer**: pending.
- **Package owner**: pending.

The final reviewer must complete the repository security template's applicable
by-surface checks and refuse approval while any medium/high finding is open.

## M0 contract review checkpoint, 2026-11-11

Independent design review passed; see [contract review disposition](20261110_contract_reviews.md).
This closes design findings only. The runtime findings and release hold above
remain open. Exact operator ratification and ancestor commit are pending.
