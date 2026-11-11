# Query-engine run access boundary

**Status**: Open (2026-11-11 UTC); contract checkpoint `2f9401f93`; implemented and forest validated; production rollout/observation pending

**Timezone**: UTC

## Overview

Remediate security audit finding F1, tracked here as `SEC-F1`: the public
query-engine HTTP surface resolves ordinary run requests without enforcing the
run's access policy and also accepts filesystem-shaped route values. On wepp1,
Caddy forwards `/query-engine/*` directly to the Starlette service. The current
ordinary-run guard is a no-op, so catalog discovery, query execution, and
activation can cross the intended run authorization and filesystem boundaries.

This package is the durable execution record. It restates the relevant evidence
because the originating audit board is intentionally local and gitignored.

## Objectives

- Accept canonical run identifiers and configuration slugs, never client-chosen
  filesystem paths.
- Authorize the canonical run before catalog discovery, query execution,
  activation, or any filesystem/log side effect.
- Preserve documented public-run reads and authorized private-run queries for
  ordinary, legacy, batch, culvert, Omni, and profile-playback run forms.
- Give browser query calls a least-privilege, HttpOnly, query-engine-scoped token
  without exposing bearer material to JavaScript.
- Make explicit forced activation an authenticated POST operation with a
  contract-defined same-origin/CSRF posture.
- Prove the fix locally, in a production-equivalent stack, and on wepp1 before
  claiming deployment or incident resolution.

## Scope

### Included

- Query-engine route parsing, filesystem containment, run authorization, CORS,
  and explicit activation semantics.
- The existing WEPPcloud run-page token bridge and shared JWT/cookie helpers
  needed for direct browser-to-query-engine calls.
- HTTP, resolver, browser, Compose, Caddy, and deployment regression evidence.
- Canonical query-engine access, session-token, and browser mutation contracts.
- Temporary Caddy containment only when separately authorized by the wepp1
  operator; rollback must retain containment until the application fix is live.

### Explicitly Out of Scope

- Security findings F2 through F8, including pickle parsing, browse XSS,
  WebSocket authorization, traceback disclosure, and dependency upgrades.
- A Flask proxy for query responses, a new identity service, a new datastore,
  or a new token protocol.
- Changes to run ownership, feature-access entitlement policy, public/private
  defaults, model outputs, or parameterization.
- Live exploit validation, bulk production-data inspection, or production
  deployment without explicit operator authorization.

## Complexity Budget

- **Existing mechanisms reused**: `get_wd`, composite-runid rules,
  `authorize_run_access`, browse/session JWTs, Redis session markers, Caddy,
  Starlette, and current query-engine tests.
- **New mechanisms permitted**: one strict query route-target value object or
  equivalent small helper; one query-engine cookie-path helper; exact audience
  and scope configuration for the existing JWT protocol.
- **Simplest plausible change tested first**: remove path fallbacks, resolve only
  a parsed run identifier, then apply the existing run authorization decision
  before any consumer runs.
- **Real acceptance condition**: anonymous/unrelated users cannot observe or
  mutate a private run, while owner/Admin/Root and contracted public reads still
  work through the direct query-engine path.
- **Evidence required before escalation**: retained direct tests showing the
  existing shared auth/token components cannot represent a required valid case.
- **Explicitly prohibited expansion**: new queues, services, datastores,
  dependencies, privileges, protocols, or deployment topology.

## Generated Artifact Validation Gate

- **Applicable**: yes; query catalog activation writes `_query_engine` cache and
  metadata artifacts even though analytical datasets are read-only.
- **User-visible failure/outcome**: unauthorized clients currently can reach
  private query data or activation; afterwards they receive a bounded denial and
  authorized clients receive the same query results.
- **Intent evidence**: exact HTTP route, method, run identifier, config, token
  class, and public/private state.
- **Persisted-state evidence**: run ownership/public state and session marker
  reloaded through canonical readers.
- **Generated-intermediate evidence**: catalog manifest readback for an
  authorized request; hash/absence proof for denied requests.
- **Prepared/consumed-input evidence**: exact dataset path admitted under the
  authorized run root.
- **Execution/output evidence**: query response semantics and catalog revision
  tied to the candidate application revision.
- **User-facing result evidence**: browser dashboard/query-console behavior for
  public, owner, unrelated, anonymous, and stale-token cases.
- **Direct unmocked boundary**: real path resolution plus JWT verification and
  real temporary run roots; production-equivalent Caddy/Compose HTTP checks.
- **Actual-project/environment gate**: forest or equivalent first, then a
  controlled wepp1 public/private fixture after explicit deployment approval.
- **Highest completion claim currently supported**: implemented; local validation in progress.

## Stakeholders

- **Primary**: WEPPcloud maintainers and wepp1 operator.
- **Reviewers**: query-engine, WEPPcloud auth, correctness/UX, QA, and security.
- **Security Reviewer**: required and independent of the implementation author.
- **Informed**: feature-access-governance and query-catalog-refresh owners.

## Success Criteria

- [ ] A ratified canonical contract defines public/private reads, explicit
      activation, token classes/scopes, composite run forms, and safe errors.
- [ ] Absolute, root-relative, traversal, encoded-separator, NUL, symlink, and
      poisoned-cache path cases fail before filesystem/catalog access.
- [ ] Anonymous and unrelated clients cannot discover, query, activate, or append
      exception logs for private runs.
- [ ] Owner, Admin, Root, service-token, and public-run cases behave exactly as
      the ratified matrix requires.
- [ ] Ordinary, legacy, batch, culvert, Omni, and profile-playback cases are
      directly dispositioned; no untested case is labeled unaffected.
- [ ] Browser dashboards keep calling query-engine directly and never expose the
      HttpOnly token to JavaScript.
- [ ] Explicit forced activation is no longer a state-changing GET.
- [ ] Query-engine CORS admits only contracted origins and clients.
- [ ] Focused, broad, browser, security, and production-equivalent checks pass;
      all medium/high correctness, QA, and security findings are closed.
- [ ] wepp1 deployment and rollback evidence proves containment remains effective.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: N/A.
- **Decision provenance captured**: yes, in the draft contract decision and
  future checkpoint review disposition.

## Dependencies

### Prerequisites

- A contract-first checkpoint following
  `docs/standards/contract-first-change-standard.md` before implementation.
- Reconciliation with fetched `origin/master` revision `ef5b4e289`; the local
  branch was not merged or switched during scaffolding.
- An operator decision on immediate Caddy containment and later wepp1 rollout.

### Blocks

- Closure of security audit finding F1/SEC-01.
- Any claim that the public query-engine route is safe for private run data.

## Related Packages

- **Related**:
  [Feature access governance](../20261001_feature_access_governance/package.md)
  owns entitlement policy but does not close this missing route guard.
- **Related**:
  [Query catalog asynchronous refresh](../20261023_query_catalog_async_refresh/package.md)
  owns refresh orchestration and must not be regressed.
- **Historical precedent**:
  [JWT browse authorization](../../mini-work-packages/completed/20260209_browse_jwt_auth.md).
- **Canonical identifier rules**:
  [Composite runid slugs](../../composite-runid-slugs.md).

## Timeline Estimate

- **Expected duration**: 1-2 weeks including contract and deployment gates.
- **Complexity**: high because the fix spans direct browser auth and multiple run
  layouts, despite a deliberately small implementation.
- **Risk level**: Critical security finding; high compatibility risk if valid
  query paths are not exercised.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: public route authorization, JWT/session cookies,
  filesystem path handling, CORS, and production ingress all change.
- **Security review artifact**:
  [artifacts/20261110_security_review.md](artifacts/20261110_security_review.md).

## Hardening and Callus Softening

- **Failure signatures**: an unauthenticated ordinary-run request reaches
  `resolve_run_context`; `resolve_run_path` accepts absolute or root-relative
  existing directories; `require_root` checks only batch/culvert roots.
- **Scope boundary**: fix the confirmed query-engine access class without
  redesigning WEPPcloud identity or unrelated query response behavior.
- **Health signals**: private anonymous/unrelated denials, zero denied-request
  catalog/log writes, and stable authorized query success.
- **Danger signals**: owner/public false denials, redirect loops, broken composite
  run queries, catalog-refresh regressions, or tokens visible to JavaScript/logs.
- **Observation window**: 14 days after wepp1 rollout, plus immediate recurrence
  review for any cross-run query or unexpected authorization denial.
- **Temporary calluses introduced**: none yet. Any Caddy containment must name an
  owner and be removed only after the deployed application gate passes.

## References

- `wepppy/query_engine/app/server.py` - public Starlette route handlers.
- `wepppy/query_engine/app/helpers.py` - permissive route-to-path resolver.
- `wepppy/query_engine/app/feature_access.py` - current group-only guard.
- `wepppy/microservices/browse/auth.py` - reusable run authorization mechanics.
- `wepppy/weppcloud/routes/run_0/run_0_bp.py` - HttpOnly run-session token minting.
- `docker/caddy/Caddyfile.wepp1` - wepp1 query-engine ingress.
- `docker/docker-compose.prod.yml` and `docker/docker-compose.prod.wepp1.yml` -
  production runtime and mounts.
- [Active ExecPlan](prompts/active/implementation_execplan.md).
- [Failure-class matrix](artifacts/20261110_failure_class_matrix.md).
- [Draft contract decision](artifacts/20261110_contract_decision.md).
- [Correctness review](artifacts/20261110_correctness_review.md).

## Deliverables

- Ratified canonical query-engine HTTP access contract and ancestor checkpoint.
- Minimal implementation with focused resolver/auth/browser regressions.
- Correctness, QA, code, and security review artifacts with findings closed.
- Production-equivalent validation, wepp1 rollout/rollback evidence, and operator
  documentation.

## Follow-up Work

Findings F2-F8 remain separate. Discoveries outside the shared missing-auth/path
assumption require a new package or explicit scope amendment; they do not expand
this package automatically.
