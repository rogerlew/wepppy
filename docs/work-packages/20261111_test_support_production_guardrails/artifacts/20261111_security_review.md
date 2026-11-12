# Security review — F7

Reviewer: `contract_security` (independent read-only security reviewer),
2026-11-12 UTC. Impact: high (route availability, bearer authority, CSRF and
credential transport). Contract ancestor: `21a75b794`; implementation recorded
in `c2507338f`. Verdict: changed-source approved; release HOLD.

## Threat model and controls

Authorized host/container agents can mint existing WEPP_AUTH credentials.
Production must expose no support route, independent of tokens. Explicit
non-production runtimes may grant environment-wide create/delete authority via
a one-hour audience/scope bearer. Cookies alone never authorize it.

The review covers absent/unknown/enabled/disabled profiles, secret lookup order,
actual URL-map exclusion, real JWT validation, finite/bounded lifetime, scope
parsing, CSRF exemptions, no-side-effect denials, automatic minting, child-only
injection, native HTTP requests, redirects, proxies, TLS and diagnostics.

## Findings and disposition

| Finding | Severity | Resolution and recheck |
| --- | --- | --- |
| Remote plaintext could expose new deletion bearer | Medium, M0 | verified HTTPS required; loopback-only HTTP; reject userinfo before mint |
| Redirects could forward bearer | Clarification, M0 | both clients reject redirects; real local tests |
| Ambient Python/Node proxies receive loopback bearer | Medium | explicit proxy isolation in both consumers; startup-enabled proxy tests receive zero requests |
| Node insecure TLS override defeats verification | Medium | explicit rejectUnauthorized; independent self-signed server receives no authorization |
| Huge numeric expiration produces overflow | Low | bounded comparisons; fractional-issued-time/huge-expiration vector |

Reviewer independently passed native HTTP/proxy/TLS tests and verified rejection
with no canary token in captured output. No open medium/high finding in changed
auth/profile/transport code. Source findings are distinct from remaining runtime
acceptance failures.

## Residual authority and owner acknowledgment

A valid support bearer can delete any resolvable non-production run, including
one not created by smoke. Reviewer recommends acceptance under the operator's
explicit no-marker decision, bounded by production exclusion, one-hour expiry,
protected transport and non-retention. Package owner acknowledges this tradeoff
in the committed M0 decision. No ownership, Root login or marker mechanism is
silently introduced.

## Evidence and release hold

Actual full production app: 484 rules, no support routes. Dev/prod/worker rendered
consumer profiles pass. Real create/load and invalid-delete preservation pass;
generated files and captured process output contain no exact minted token.
However real authorized deletion returns 200 with a remaining NFS directory.
Full automatic wrapper/browser trace/report/log scans remain outstanding.
See [validation](20261112_validation.md). No production deployment occurred.

## Deployment draft review

Independent security review closed the rollback-image-pruning planning finding:
mandatory `--skip-docker-prune` protects retained recovery images. Frozen source
and `--skip-pull` preserve candidate identity. Operations separately reviewed
cross-host fence and partial-activation recovery. Draft quality approved only
as a nonexecuted HOLD document. Final approval requires F7 cleanup/browser
acceptance, F6 M4, exact candidate/images, blocking preflights and verified
rollback/recovery. No execution authority is granted.
