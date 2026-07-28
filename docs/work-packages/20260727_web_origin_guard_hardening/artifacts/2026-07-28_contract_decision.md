# Web-origin guard hardening contract decision

## Status

Checkpoint candidate for independent review. This document is not authority to
edit implementation files until the reviewed standalone ancestor is recorded.

## Starting Revision

`4c574dcd6c6a07b80cc0e704961f108728ab90ea`

## Applicable Authority

- `docs/standards/contract-first-change-standard.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/schemas/weppcloud-session-contract.md`
- `docs/ui-docs/diagnostics-page.spec.md`
- GOV-00A-M1D / REM-04 bounded-remediation registration:
  `docs/work-packages/20260716_pure_ui_contract_ratification/artifacts/2026-07-28_web_origin_guard_bounded_remediation_decision.md`

## Discrepancy Classification

The query-engine upstream-TLS rejection is a confirmed production defect.
Origin-conflict handling, forwarded-header trust, cookie-clear scope, and copied
report disclosure are security hardening changes. Because the package changes
normative behavior and not only conformance to an unchanged contract, it must
use the full reviewed checkpoint path rather than urgent restoration.

## Normative Delta

All three guards reject `Sec-Fetch-Site: cross-site`, malformed or opaque
origins, conflicting hosts/subdomains/explicit ports, mismatched exact fallback
origins, and requests missing every origin signal. Exact Origin or Referer
fallback compares normalized scheme, host, and port.

`Sec-Fetch-Site: same-origin` authorizes a request without Origin. With Origin,
it accepts exact public origin or the narrow public HTTPS versus trusted
internal HTTP scheme bridge when host and effective public port agree. It never
overrides a host, subdomain, or explicit-port conflict. Raw forwarded headers
do not add allowed origins.

The bridge is available only for the exact authoritative application
`http://host:80` to browser `https://host:443` pair. Flask obtains its tuple
after one-hop ProxyFix and requires final-proxy-only reachability with replaced
forwarding headers. rq-engine and query-engine use their ASGI request URL/Host
and configured public origins; they ignore raw forwarded origin headers.
Without an authoritative or configured tuple, fallback rejects.

Existing CSRF and authentication requirements remain layered outside the
same-origin predicate. A same-origin signal does not satisfy Flask-WTF CSRF.
The shared matrix tests predicates; separate surface adapters test Flask-WTF,
rq-engine cookie/session authentication, and query-engine boundary controls.

Reset deletes exactly the configured session name/path/domain and remember
name/path/domain tuples. It creates no parent-domain/path variants and deletes
no generic CSRF cookie; Flask-WTF state is removed with the session.
Resolved remember-cookie configuration is used directly; an unset remember
domain remains host-only even when the session domain is configured.

Copied diagnostics contain only report metadata and known check IDs whose fixed
title/severity come from the report catalog. Status selects a fixed evidence and
fix-hint message. Unknown checks and all raw evidence, backend text, URLs,
hostnames, run IDs, and extension fields are omitted. The complete fixed catalog
and messages are normative in `docs/ui-docs/diagnostics-page.spec.md` section 9.

## Rationale

The same browser request currently receives different authorization decisions
depending on which service handles it and where TLS terminates. Reset deletion
and copied diagnostics also cross boundaries broader than their advertised
WEPPcloud-only and safe-to-share scopes. A reviewed common contract makes the
security properties testable and prevents implementation from defining intent.

## Compatibility

Same-origin requests should remain accepted and cross-origin requests should
remain rejected. The intended compatibility restoration is acceptance of the
upstream-TLS same-origin query-engine request. The current missing-header
divergence resolves to rejection on all three guards. The guarded endpoints are
browser boundaries; non-browser clients without Origin, Referer, or Fetch
Metadata are no longer compatible and must use an appropriate bearer-token
surface where available.

No response payload keys, route paths, queue behavior, model parameters, or
project data schemas may change.

## Security Impact

Security impact is `high`. The primary risks are accepting attacker-controlled
origins, bypassing CSRF, deleting a sibling application's cookie, and copying
untrusted backend text into a public report. The checkpoint and final reviews
must cover each risk by surface.

## Contract Conflict Disposition

The prior session contract allowed
`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true` to add raw forwarded-origin
aliases, while the amended CSRF contract prohibited that trust. The session
contract now delegates to the shared guard contract. The legacy environment
variable remains accepted but inert for origin authorization. Deployments that
used it must configure explicit external host/scheme values before REM-04.

## Regression Evidence

WP04 will apply one reviewed predicate matrix to all three services and separate
outer-layer vectors to Flask-WTF, rq-engine cookie/session authentication, and
query-engine controls. Focused tests will cover the inert forwarded-origin
switch, exact cookie deletion tuples, distinct/unset cookie domains, and hostile
report metadata/evidence. The package will run focused Python suites,
JavaScript lint/tests, the full Python suite, documentation lint,
broad-exception enforcement, and independent final reviews.

## Operator Approval

The operator requested execution of the scaffolded package on 2026-07-27,
requested a governance-compliant executable scaffold revision on 2026-07-28,
and then explicitly requested execution of that revised package. This records
approval of REM-04, the normative matrix above, dual independent reviews, and
the required standalone checkpoint commit.

## Exclusions

Caddy configuration, deployment, new guarded endpoints, authentication or role
policy, queue wiring, model parameterization, project schemas, diagnostics card
display, and unrelated Pure UI owner work are excluded.

## Checkpoint Reviews and Disposition

- Security/governance:
  `2026-07-28_checkpoint_security_governance_review.md` - PASS after rereview,
  zero unresolved findings.
- Correctness/compatibility:
  `2026-07-28_checkpoint_correctness_compatibility_review.md` - PASS after
  rereview, zero unresolved findings.
- Primary disposition:
  `2026-07-28_checkpoint_review_disposition.md`.

Revision note: Drafted and independently reviewed on 2026-07-28; reconciled
forwarded-origin authority, executable bridge inputs, report catalog metadata,
surface-specific security layers, and cookie configuration provenance.
