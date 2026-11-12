# F7 test-support and deployment-profile contract decision

**Status**: Ratified in standalone ancestor 21a75b794; implementation follows
**Date**: 2026-11-12 UTC
**Starting revision**: `cfa1fc6e79ad1db643bd70c95bc8d44dc7083367`
**Remediation**: F7 / SEC-07

## Operator Authority

The operator selected the following behavior in the 2026-11-11 conversation:

- `WEPPCLOUD_DEPLOYMENT_PROFILE` defaults to production.
- Authentication must remain low friction for authorized agents.
- Smoke markers and their lifecycle are disproportionate and excluded.
- F7 completion should wrap the F1-F7 remediation set and leave deployment
  validation checks planned.

This authority permits the bounded contract and implementation described here.
It does not authorize deployment, service restarts, production test-route
enablement, production mutation, ordinary run-policy changes, F8 work, or a new
identity system.

## Proposed Canonical Delta

Create `docs/schemas/weppcloud-test-support-contract.md` and amend
`docs/infrastructure/weppcloud-web-runtime-contract.md` plus
`docs/schemas/weppcloud-csrf-contract.md` before implementation.

The proposed rules are:

1. `WEPPCLOUD_DEPLOYMENT_PROFILE` accepts only `production`, `development`, or
   `test`. Missing or empty means `production`; unknown non-empty input fails
   startup.
2. `TEST_SUPPORT_ENABLED` keeps its current false default.
3. Production plus enabled test support fails startup before blueprint
   registration. The production Flask URL map contains no `/tests/api/*` route.
4. Development/test plus disabled support does not register the blueprint.
5. Development/test plus enabled support registers the existing ping, create,
   and delete routes.
6. Every registered route requires a valid short-lived WEPP_AUTH bearer with
   audience `weppcloud-test-support` and scope `test:support`.
7. Missing, malformed, invalid, expired, or wrong-audience bearer returns 401.
   A valid bearer missing the required scope returns 403. Authentication occurs
   before payload parsing or filesystem access.
8. These bearer-only views are exempt from cookie CSRF checks. A browser
   session/cookie alone grants no test-support authority.
9. `wctl run-playwright` mints the token inside the WEPPcloud container and
   injects it automatically into the support ping and Playwright child. No raw
   token appears in argv, URLs, logs, reports, profiles, or retained artifacts.
10. A valid bearer is an environment-wide capability in development/test. It
    may create and delete any resolvable run through these existing routes. No
    smoke marker, run registry, ownership record, or cleanup capability is
    added.
11. Production never registers the routes, even if a bearer is otherwise valid.

## Compatibility and Intentional Changes

- Raw local Flask starts that previously enabled test support without a profile
  now fail because absence means production. Dev/test launchers must set an
  explicit non-production profile.
- Existing successful endpoint paths and payloads remain unchanged.
- Anonymous smoke calls intentionally stop working. The canonical wctl workflow
  absorbs the authentication step so authorized agents do not gain manual work.
- Direct `npm`/Playwright invocations must receive a transient token through the
  documented test harness or use `wctl run-playwright`.
- Delete remains immediate and environment-wide in non-production. This is an
  explicit privileged support capability, not ordinary run authorization.

## Alternatives Rejected

- A static `TEST_SUPPORT_TOKEN_FILE`: rejected because WEPP_AUTH already owns
  signing, validation, rotation, and container-local issuance.
- Root/session login: rejected because it adds password, cookie, CSRF, and
  ownership ceremony to test provisioning.
- Smoke markers or registry: rejected by the operator as disproportionate.
- Normal asynchronous run deletion: rejected because it changes deterministic
  smoke cleanup and requires ownership state.
- Production registration with authenticated denial: rejected because route
  absence is a stronger and simpler production invariant.
- F7/F8 combined implementation: rejected because route auth and port exposure
  have different owners, validation, and rollback boundaries.

## Regression Evidence Required

- Configuration and startup tests for every profile/flag state.
- Actual Flask URL-map evidence for production route absence.
- Missing/invalid/expired/wrong-audience/wrong-scope token tests with direct
  no-side-effect assertions.
- Cookie-without-bearer denial and bearer-without-CSRF success in an actually
  configured Flask app.
- wctl token capture/injection/error tests proving no token output.
- Shared Playwright helper tests proving the bearer reaches only support routes.
- Unmocked create/load/delete and filesystem readback in non-production.
- Rendered production Compose proof that env-file values cannot enable support.
- One final combined F1-F7 full Python/frontend receipt after F6 M4.

## Checkpoint Gate

Before implementation:

- [x] Author the canonical documents and exact error/TTL contract.
- [x] Matrix unchanged; user execution authority covers the checkpoint.
- [x] Obtain two independent read-only contract reviews.
- [x] Disposition every review finding.
- [x] Commit package decision, canonical contracts, reviews, and disposition as
      a standalone ancestor.
- [x] Record the full checkpoint revision in tracker and ExecPlan.

No code edit may precede this gate.


## M0 execution amendment

The user explicitly instructed execution of this plan on 2026-11-12, including
its standalone checkpoint commit and independent reviews. Canonical normative
text is now in `docs/schemas/weppcloud-test-support-contract.md`, with reciprocal
CSRF/runtime links. Implementation remains pending. This intended behavior
change has high security impact and no data/schema migration.

The exact parser exception is `ValueError`; messages and full state matrix are
in Runtime states. Tokens require finite iat/exp and a maximum one-hour lifetime
because the existing decoder permits absent expiration. wctl mints exactly
3600 seconds. The mandatory ping remains for --no-create-run to preserve the
existing wrapper contract. Support HTTP requests must avoid traced Playwright
contexts and redirects to satisfy non-retention. These specify the existing
short-lived/narrow-token decisions without broadening operator authority.

Residual environment-wide delete authority is acknowledged by the package
owner executing the operator's explicit no-marker decision. Independent
security review must assess this tradeoff; production absence is mandatory.

Review amendment: remote support bearer transport requires verified HTTPS;
localhost/loopback HTTP remains supported and URL userinfo is rejected before
minting. Both ping and helper reject redirects. This confines the newly added
credential rather than changing normal application transport.

## Independent M0 review disposition (2026-11-12 UTC)

`contract_correctness` (reviewer) approved: no medium/high findings. Preserve
early-secret ordering, audience membership and mixed path normalization.
`contract_security` (security_reviewer) approved after the remote plaintext
transport medium finding and ping redirect clarification were fixed and
rechecked. No open medium/high findings. Both reviews were read-only and
independent of the author. Approval is contract-only, not runtime acceptance.

Owner acknowledgment: accept environment-wide non-production deletion under
the recorded operator no-marker decision, bounded by production absence,
one-hour expiry, protected transport and non-retention. Required executable
evidence remains M4/M5. Commit authority is supplied by execution of the plan's
explicit M0 commit step.
