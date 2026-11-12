# Test-support production guardrails and F1-F7 readiness

**Status**: Open (2026-11-12 UTC); M0-M3 implemented; M4 cleanup/runtime hold; F6 M4 pending

**Timezone**: UTC

## Overview

Remediate security audit finding F7/SEC-07 by making WEPPcloud test-support
routes impossible to enable accidentally in production and authenticated when
they are intentionally enabled in development or test environments. The
runtime deployment profile defaults to `production`; missing or invalid
configuration cannot silently expose `/tests/api/*`.

This package also provides the pre-deployment wrap-up for findings F1 through
F7. Closure means the seven remediation streams have compatible reviewed
implementations, required non-production evidence, one combined regression
receipt, and a reviewed deployment-validation plan. Closure does not mean that
the candidate has been deployed to wepp1 or wepp2, and it does not raise any
individual finding above the evidence retained by its owning package.

## Threat Model

- **Assets**: WEPPcloud run directories, run initialization state, test-support
  credentials, production route inventory, and the integrity of the combined
  F1-F7 release candidate.
- **Adversaries/failures**: an anonymous Internet client; a stale host `.env`;
  a misspelled or absent deployment profile; a leaked test credential; a smoke
  client that silently omits authentication; and a rollout assembled from
  partially validated remediation commits.
- **Trust boundaries**: runtime environment to Flask configuration; Flask
  configuration to blueprint registration; `wctl` to the existing WEPP_AUTH
  JWT issuer; Playwright request helpers to `/tests/api/*`; and the individual
  F1-F7 evidence sets to one release-readiness decision.
- **High-value paths**: anonymous run creation, deletion of a named run,
  accidental production registration of support routes, bearer leakage, and a
  deployment plan that overstates incomplete findings.

## Objectives

- Add a canonical `WEPPCLOUD_DEPLOYMENT_PROFILE` contract with recognized
  `production`, `development`, and `test` values and a default of `production`.
- Refuse startup when test support is enabled under the production profile or
  when the profile value is unknown.
- Keep test-support routes absent unless both an allowed non-production profile
  and `TEST_SUPPORT_ENABLED=true` are present.
- Reuse the existing WEPP_AUTH JWT issuer for a short-lived
  `test:support` bearer credential; do not add a static secret, identity store,
  or second authentication system.
- Make `wctl run-playwright` mint and inject the credential without requiring an
  agent to log in, copy a token, manage cookies, or obtain CSRF state.
- Preserve deterministic test-run creation and deletion without a smoke-marker
  registry. The bearer is an environment-wide non-production support
  capability, and that residual authority is explicit.
- Reconcile F1-F7 implementation, validation, and review evidence into one
  readiness matrix without rewriting the historical owning packages.
- Produce a reviewed, non-executed deployment-validation plan for the exact
  combined candidate, including wepp1 and any confirmed wepp2 consumers.

## Scope

### Included

- `wepppy/weppcloud/configuration.py` profile parsing and fail-closed startup
  invariants.
- `wepppy/weppcloud/_blueprints_context.py` production route exclusion.
- `wepppy/weppcloud/routes/test_bp.py` bearer verification, scope/audience
  checks, explicit response behavior, and CSRF exemption for bearer-only
  mutation requests.
- Production and development Compose literals needed to make the effective
  profile observable and non-overridable through an ordinary env-file value.
- Existing WEPP_AUTH token issuance and validation utilities. No new signing
  key or token datastore is permitted.
- `tools/wctl2/commands/playwright.py`, its tests and documentation, plus the
  Playwright smoke helpers and direct create/delete consumers.
- Canonical runtime, CSRF, configuration, Docker, smoke, and agent-facing
  documentation.
- Focused route/configuration/CLI/browser tests, combined F1-F7 regression
  gates, independent correctness/QA/security reviews, and readiness evidence.
- A deployment-validation plan that names authority, exact candidate identity,
  host/service impact, preflight, post-deploy evidence, rollback triggers, and
  safe production checks. Planning does not authorize execution.

### Explicitly Out of Scope

- Production deployment, service restart, secret rotation, firewall change, or
  live mutation of wepp1/wepp2 data.
- Smoke markers, a smoke-run registry, a new database table, a Redis allowlist,
  per-run cleanup capabilities, or changes to ordinary run ownership policy.
- Replacing the existing WEPP_AUTH JWT implementation or minting a credential
  through a public unauthenticated route.
- Enabling test support in any production profile, even with a valid token.
- Closing F8/SEC-08 port-publication work. Its deploy preflight may be planned
  beside this work, but it remains a separate finding and package boundary.
- Reimplementing or editing F1-F6 behavior except for a confirmed integration
  regression caused by the combined candidate and authorized through the
  owning package.

## Ratification Boundary

The operator has selected these durable decisions:

- `WEPPCLOUD_DEPLOYMENT_PROFILE` defaults to `production`.
- Authentication must be low friction for authorized agents.
- Test-support cleanup does not require smoke markers.
- F7 completion is the pre-deployment wrap-up point for F1-F7 and must leave a
  deployment-validation plan.

The proposed low-friction implementation reuses the existing short-lived
WEPP_AUTH issuer with audience `weppcloud-test-support` and scope
`test:support`. `wctl run-playwright` mints the token inside the configured
WEPPcloud container, captures it without logging it, and passes it only to the
smoke child process. This exact contract, response matrix, and CSRF exemption
must be promoted to canonical documentation, reviewed twice, and committed as
a standalone checkpoint before implementation.

## Complexity Budget

- **Existing mechanisms reused**: WEPP_AUTH JWT signing/decoding, the existing
  `wctl issue-auth-token` container boundary, Flask blueprint registration,
  Docker Compose configuration, current Playwright request contexts, and the
  existing work-package review gates.
- **New mechanisms permitted**: one deployment-profile enum; one JWT audience
  and scope; one internal `wctl` token-capture helper; one shared Playwright
  test-support request helper; one F1-F7 readiness artifact.
- **Simplest plausible change tested first**: production-default profile guard,
  existing JWT validation, and automatic wrapper injection around unchanged
  create/delete semantics.
- **Real acceptance condition**: production configuration cannot register the
  routes; an authorized agent can run the existing smoke workflow with no
  manual auth steps; invalid credentials cannot create or delete a run.
- **Evidence required before escalation**: retained failure showing the existing
  JWT issuer, wrapper, or request helper cannot satisfy a named acceptance case.
- **Explicitly prohibited expansion**: new service, datastore, daemon,
  dependency, signing key, persistent token registry, smoke marker, run schema,
  queue, deployment topology, or ordinary-user privilege.

## Valid-State Summary

| Profile | Test flag | Credential | Required result |
| --- | --- | --- | --- |
| absent | false/absent | any | Treat as production; routes absent |
| absent | true | any | Startup fails before route registration |
| production | false | any | Routes absent |
| production | true | any | Startup fails before route registration |
| development/test | false | any | Routes absent |
| development/test | true | missing/invalid | Routes present but request returns explicit auth denial; no side effect |
| development/test | true | valid scoped JWT | Ping/create/delete retain intended smoke behavior |
| unknown | any | any | Startup fails with an actionable configuration error |

The bearer intentionally authorizes environment-wide cleanup in development or
test. It does not establish run ownership. The production profile exclusion is
the primary containment boundary; bearer authentication is the secondary
non-production boundary.

## Generated Artifact Validation Gate

- **Applicable**: no for model/report artifacts. The workflow creates disposable
  run directories and generated browser test results.
- **Direct unmocked boundary**: use the actual configured Flask app and
  `wctl run-playwright` against a non-production stack; verify run creation,
  page load, deletion, and directory absence.
- **Production invariant evidence**: inspect the actual Flask URL map under the
  rendered production profile; an HTTP 404 alone is insufficient proof that the
  route was not registered.
- **Credential evidence**: retain only token-free assertions about audience,
  scope, lifetime, response status, subprocess environment keys, and log scans.
- **Highest completion claim currently supported**: diagnosed and scaffolded.
  No implementation, environment validation, or deployment is claimed.

## Stakeholders

- **Decision owner**: WEPPpy maintainer and production operator.
- **Primary implementers**: WEPPcloud route/configuration, Docker, wctl, and
  Playwright smoke maintainers.
- **Reviewers**: two read-only contract reviewers before implementation, then
  independent correctness, QA, security, and deployment-plan reviewers.
- **Security reviewer**: required and independent of the implementation author.

## Success Criteria

- [ ] Canonical test-support/profile and CSRF contracts are ratified, reviewed
      twice, and committed as a standalone ancestor before code changes.
- [ ] Missing profile means production; unknown values and production plus
      enabled test support fail startup with an actionable error.
- [ ] Rendered production Compose pins the production profile and test support
      off; the Flask production route inventory contains no `/tests/api/*`.
- [ ] Development/test support uses a short-lived WEPP_AUTH token with exact
      audience and `test:support` scope; missing, invalid, expired,
      wrong-audience, and wrong-scope cases perform no side effect.
- [ ] `wctl run-playwright` acquires and injects the credential automatically
      without printing, persisting, or placing it in a URL.
- [ ] Authorized ping, create, page-load, and delete workflows pass with no
      smoke marker or new state registry; deletion absence is read back.
- [ ] All direct Playwright support-route consumers use the shared auth helper,
      while ordinary browser and API requests do not receive the token.
- [ ] Focused Python, wctl, Compose, and Playwright tests pass, followed by one
      exact combined `wctl run-pytest tests --maxfail=1`, `wctl run-npm lint`,
      and `wctl run-npm test` pass on the F1-F7 candidate.
- [ ] F6 has reached its M4 exact-image, full-regression, review, and artifact
      acceptance gate. Its separately authorized production rollout is not a
      prerequisite for this package's readiness claim.
- [ ] The F1-F7 readiness matrix records exact revisions, evidence grades,
      unresolved items, and no unresolved medium/high correctness, QA, or
      security findings for the pre-deployment candidate.
- [ ] A reviewed deployment-validation plan exists for the exact candidate,
      identifies wepp1/wepp2 impact, uses canonical deployment entry points,
      and contains no implied deployment authorization.
- [ ] The audit board and `PROJECT_TRACKER.md` describe F1-F7 as
      pre-deployment-ready only to the degree supported by retained evidence.

## Parameterization ADR Gate

- **Parameterization change present**: no scientific/model parameterization.
- **ADR required**: no; fixed 3600 seconds reuses the WEPP_AUTH default, introduces no
  configurable threshold and changes no model parameterization.
- **Decision provenance captured**: yes, initially in
  `artifacts/20261111_contract_decision.md`; durable rules must be promoted to
  canonical documentation before implementation.

## Dependencies

### Prerequisites

- F1-F5 owning packages must retain their current implementation/review evidence
  and disclose any reopened medium/high finding.
- F6 must complete through M4, including exact final image evidence, combined
  Python/frontend gates, and independent reviews. F6 production rollout remains
  separately authorized.
- The current WEPP_AUTH secret-file and token issuer configuration must remain
  available to the WEPPcloud container used by `wctl`.

### Blocks

- Consolidated F1-F7 pre-deployment readiness declaration.
- Final operator review and execution planning for the combined production
  deployment-validation sequence.

## Related Packages

- **F1**: [Query-engine run access boundary](../20261110_query_engine_access_boundary/package.md)
- **F2**: [Pickle artifact restriction](../20261110_pickle_artifact_restriction/package.md)
- **F3**: [Browse listing output safety](../20261110_browse_listing_output_safety/package.md)
- **F4**: [Status/preflight WebSocket authorization](../20261111_status_preflight_websocket_authorization/package.md)
- **F5**: [Safe traceback sanitization](../20261111_safe_traceback_sanitization/package.md)
- **F6**: [wepp1 dependency security gate](../20261110_wepp1_dependency_security_gate/package.md)
- **F5 prerequisite**: [Redis credential transport](../20261111_redis_credential_transport/package.md)
- **Separate follow-up**: F8/SEC-08 host-port and ingress deployment hardening.

## Timeline Estimate

- **Expected duration**: 2-4 focused working days after the M0 checkpoint, plus
  any wait for F6 M4 evidence.
- **Complexity**: medium implementation complexity; high release-coordination
  significance.
- **Finding severity**: Low conditional in the default-disabled audit state;
  High impact if exposed.
- **Change security impact**: high because it changes public-route registration,
  bearer authorization, CSRF behavior, secret-backed token use, and deployment
  configuration.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **CWE/OWASP mapping**: CWE-306 (Missing Authentication for Critical
  Function), CWE-862 (Missing Authorization), and OWASP A01 Broken Access
  Control.
- **Security review artifact**:
  [artifacts/20261111_security_review.md](artifacts/20261111_security_review.md).
- **Correctness review artifact**:
  [artifacts/20261111_correctness_review.md](artifacts/20261111_correctness_review.md).
- **QA review artifact**:
  [artifacts/20261111_qa_review.md](artifacts/20261111_qa_review.md).

## Hardening and Observation Model

- **Failure signature**: `/tests/api/create-run` or `/tests/api/run/<runid>`
  performs a side effect without a valid scoped credential; or any
  `/tests/api/*` route appears in a production-profile Flask route inventory.
- **Scope boundary**: close F7 without changing ordinary run authorization,
  adding smoke markers, or executing production deployment.
- **Hypothesis**: a production-default profile guard plus automatic scoped JWT
  transport removes accidental production exposure while preserving low-friction
  authorized agent smoke workflows.
- **Health signals**: production route inventory remains empty; authorized smoke
  creation/deletion succeeds; invalid-token side-effect counters remain zero;
  agents need no manual auth steps.
- **Danger signals**: development unexpectedly defaults open; production accepts
  an env-file override; token material appears in output; the bearer is attached
  to unrelated requests; smoke cleanup failures accumulate; or the readiness
  roll-up hides an unresolved finding.
- **Observation model**: pre-deployment evidence plus recurrence-triggered
  review. Any production route appearance or unauthenticated side effect opens a
  new incident package; do not amend this package after closure.
- **Temporary calluses**: none planned.

## References

- `wepppy/weppcloud/configuration.py` - current boolean flag parsing.
- `wepppy/weppcloud/_blueprints_context.py` - conditional blueprint registration.
- `wepppy/weppcloud/routes/test_bp.py` - ping/create/delete handlers.
- `wepppy/weppcloud/utils/auth_tokens.py` - existing JWT issuer and validator.
- `tools/wctl2/commands/playwright.py` - smoke wrapper and ping preflight.
- `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml` - runtime profiles.
- `docs/standards/contract-first-change-standard.md` - required checkpoint.
- `docs/standards/hardening-lifecycle-standard.md` - failure-class assessment.
- Gitignored audit board at
  `out/security-audit-20261110/wepp1-security-audit-orchestration-board.md`.

## Deliverables

- Canonical test-support/profile contract and related documentation amendments.
- Profile, registration, bearer auth, wctl, and Playwright implementation.
- Focused and combined validation receipts.
- Completed correctness, QA, security, and deployment-plan reviews.
- Final F1-F7 readiness matrix and non-executed deployment-validation plan.

## Follow-up Work

- Execute the deployment-validation plan only after explicit operator
  authorization and exact-candidate review.
- Keep F8/SEC-08 port-binding hardening separate unless the operator later
  authorizes a combined deployment package.
