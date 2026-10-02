# Milestone 3 service and browser acceptance

Date: 2026-10-02 UTC. Base revision: `794c26c42`; the subject and Compose
corrections described here were uncommitted during the retained run.

## Boundary exercised

The local development stack uses the production service processes, container
identities, `/wc1` mount, Caddy routes, Redis revocation store and PostgreSQL
account database. Only `browse`, `dtale`, and `query-engine` were recreated from
the canonical development Compose file after their configuration changed.
Production was not accessed or changed.

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
`/wc1` fixtures. The fixtures and temporary token file were removed after the
run; D-Tale's in-memory disposable dataset entries disappear on its next
recreation.

## Configuration and focused regression

Compose rendering passed for development, HPC development, production, and the
combined production/wepp1 overlay. The new dependency contract and affected
token routes passed 61 tests; the broader token/fork/create route run passed 75
tests. Frontend lint and all 112 Jest suites / 919 tests passed. Full repository
and final independent review results are recorded in the ExecPlan when they
complete.
