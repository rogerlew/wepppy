# WP06 Builder API Evidence

The rq-engine now exposes authenticated description, validation, and creation
at `/api/project-config/builder`, `/validate`, and `/create`. Description and
validation share the opaque registry digest. Exact payload parsing rejects
arbitrary fields and the reserved token/filename remain server-owned.

Generated-output tests resolve the registered continental-US family, write
`config.cfg` plus schema-v1 manifest through WP04's atomic materializer, and
reopen the pair through WP02 without shared fallback. Route tests cover stale
revision, ordinary-user override denial, named/case-insensitive privileged
roles, default-off creation, fixed-token creation, and idempotent replay.

Focused builder/registry/idempotency tests passed (48), focused generated/API
tests passed (9), and OpenAPI contract tests passed (13 including builder
routes). The final focused builder/route/OpenAPI selection passed 20 tests; the
endpoint inventory, checklist, and OpenAPI guard selection passed 12 tests.
The NoDb and microservice regression selection passed 3,028 tests with 30
skips. Stubtest, stub consistency, rq-contract guards, broad-exception
enforcement, diff checks, and documentation lint passed. The exact full suite
passed 6,898 tests with 63 skips.

The final boundary regression supplies one immutable registry snapshot to both
staleness comparison and resolution, avoiding registry reload races. An
injected unexpected Ron failure proves the creation boundary removes the
partial generated pair and releases its idempotency reservation.
