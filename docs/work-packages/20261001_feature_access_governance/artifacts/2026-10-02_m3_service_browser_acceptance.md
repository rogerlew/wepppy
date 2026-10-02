# Milestone 3 service and browser acceptance

Date: 2026-10-02 UTC. Candidate revision: `23c2f27fe`. The service dependency
and subject corrections were checkpointed in `03fc3eae6`; the private proxy
redirect correction is part of the candidate revision.

## Boundary exercised

The local development stack uses the production service processes, container
identities, `/wc1` mount, Caddy routes, Redis revocation store and PostgreSQL
account database. Only `browse`, `dtale`, and `query-engine` were recreated from
the canonical development Compose file after their configuration changed.
Production was not accessed or changed.

Runtime readback for Browse, D-Tale and Query Engine reported UID 1000, GID 993,
umask `0022`, and the same read/write NFS4 `/wc1` mount. Each process was
recreated after the checkpoint before the exact-revision run.

Two disposable Batch roots were created under `/wc1/batch`: one private and one
public. Their CSV cells contained unique synthetic canaries. A third private
Batch root contained a one-row admitted Parquet file and query catalog. A
separate synthetic Parquet canary was used as an undeclared external source.
No user run data was read.

The designated local account was resolved by `rogerlew@gmail.com` as active
account ID 1. Its existing sole Batch membership was read from PostgreSQL. The
normal UI token issuer minted the bearer credential; no token value was retained
in this artifact. Membership removal and restoration used
`FeatureAccessStore.change_membership_status`, so both reasons and times remain
auditable. Final readback confirmed the account is again the sole active Batch
member.

## Discovery and corrections

The first service attempt denied the valid member as `human identity required`.
`issue_user_rq_engine_token` was signing Flask-Security's opaque
`fs_uniquifier` as `sub`, although the trusted feature principal contract reads
the numeric account ID from `sub`. The issuer now requires a positive integer
account ID and signs its decimal representation.

The next attempts failed closed because Browse lacked the Postgres secret and
Query Engine lacked both the Postgres secret and WEPP user-token verification
secret. Browse, D-Tale and Query Engine now receive the existing Postgres secret
and wait for healthy Postgres. Query Engine additionally receives the existing
WEPP JWT verification secret for its browser-facing routes; its separate MCP
secret and middleware remain unchanged. No new credential or service was added.
The explicit Compose startup maps retain Redis (`service_started`) alongside
Postgres (`service_healthy`) so revocation checks do not lose their inherited
dependency.

The first clean-process proxy run then set the private capability cookie but
redirected to `/weppcloud`. Upstream `DtaleData.build_main_url()` consulted the
guarded dataset listing before that new cookie existed and saw no visible keys.
The launch handler now constructs the already-verified dataset route with
D-Tale's own double-quoting convention after ticket and live-capability checks.
The exact proxy `Location` has a focused regression assertion.

## Retained browser and service result

Run:

    node docs/work-packages/20261001_feature_access_governance/artifacts/2026-10-02_m3_service_browser_acceptance.mjs

The retained Playwright harness used the real Caddy routes and browser cookie
jar. Its final result was:

    {
      "privateAnonymousLaunch": 401,
      "privateMemberGrid": 200,
      "privateMemberCanary": true,
      "privateAnonymousGrid": 403,
      "declaredQuery": 200,
      "declaredQueryValue": 1,
      "externalQuery": 500,
      "externalQueryCanary": false,
      "privateRemovedMemberGrid": 403,
      "removedMemberQuery": 403,
      "privateRestoredMemberGrid": 200,
      "privateRestoredCanary": true,
      "restoredMemberQuery": 200,
      "publicAnonymousGrid": 200,
      "publicAnonymousCanary": true
    }

The external-query failure was DuckDB's expected permission error after external
access was disabled. The response did not contain the synthetic private cell.
The declared catalog relation remained readable. D-Tale set its scoped viewer
cookie through the reverse proxy, returned private cells only to the current
member, denied the same live cookie immediately after membership removal, and
accepted it again after the audited restoration. A separate anonymous browser
continued to read the public Batch table.

The script is a retained reproduction rather than an automatic test because it
requires the running Compose stack, local account initialization and disposable
`/wc1` fixtures. It resolves the designated account, holds the token only in
process memory, creates its fixtures, restores membership in a `finally` block
and removes its fixtures. Final filesystem readback found none of the four
synthetic paths, and final database readback found only account ID 1 with an
unexpired Batch membership. D-Tale's in-memory disposable dataset entries
disappear on its next recreation.

## Configuration and focused regression

Compose rendering passed for development, HPC development, production, and the
combined production/wepp1 overlay. The new dependency contract and affected
token routes passed 61 tests; the broader token/fork/create route run passed 75
tests. The proxy redirect suite passed 10 tests. Frontend lint and all 112 Jest
suites / 919 tests passed. Independent correctness and security reviewers
accepted the deployment and redirect corrections with no remaining finding;
the security review also passed 152 focused cases. The final full repository
run passed **10,246 tests with 126 skipped and 12 subtests passed** in 2,668.41
seconds (44:28).

The first full runs exposed a test-isolation defect in this acceptance test:
`rq_engine.auth` captures its Redis client class at import time, but the test
patched only the later `redis.Redis` module attribute. Full collection therefore
allowed the fork-preparation check to contact the real password-protected Redis
and return a generic 401. The test now replaces the captured client directly.
The all-collection focused reproduction and the final full run pass; production
code and Redis configuration were unchanged by this test correction.
