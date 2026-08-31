# WP12D Amendment 5 Reader-Floor Forest Acceptance

**Observation time**: 2026-08-28 17:03 UTC
**Host**: `forest`
**Branch**: `feature/project-owned-config`
**Reader-floor revision**:
`d68d94816a6d21276a596b1c9d3b21c985135b2b`
**Deployed provenance revision**:
`83165fd1b8cf6ebacf728daad6d22fc08052959e`
**Production scope**: none; merge and production remain reserved to WP12

## Deployment

The branch was pushed through deployed revision `83165fd1b8`. Only
`weppcloud` and `rq-engine` were force-recreated from the development Compose
topology with `--no-build --no-deps`; no worker, dependency, image, registry,
or production action occurred. Both services retained image digest
`sha256:6ac7e71030467a10e5d73dc18893cbd85c9202976d4b1b561a19dbb0d7ef2b75`
and reported the exact deployed Git revision.

Direct health checks returned HTTP 200 with `"OK"` and
`{"status":"ok","scope":"rq-engine"}`. Startup logs contained no error,
traceback, critical event, or startup failure.

## Reader-First Proof

The production stored-authority reader reopened real historical schema-v2 run
`matted-smooth` at structure
`aa548c9c4bc792b44fc89b97e2b71270d2bbf1002cc960aac005b6d52c351bc6`
and prior schema-v3 run `biomedical-sharp` at structure
`5296d3519d578164b6a5874a820991c935b394e5336aba41fe3e8f8d0dd4e29b`.

The live Builder resolver still emitted only the pre-amendment-5 identities:

- Continental US: `5296d3519d578164b6a5874a820991c935b394e5336aba41fe3e8f8d0dd4e29b`
- Europe: `c05b6a66f823f69cf8f1d44b69c206da1dc9449b278662c680248a3f3b755aeb`
- Canada: `dd7f7cdb0d861a159df64a4806ee5585f0208b93982990e30974055b1f2a41e7`
- Australia: `bb4bdde8740d689aa378bcf744a942d997b9c69cdc445d80be07c749635efc9a`
- Global Earth: `db1c185cf6b5def23064752847f585f3522c0b971460d9c688b424cb04c706ae`

The in-container reader-floor suite passed all 74 tests. Independent binding
correctness and security reviews reported READY with High 0, Medium 0, and Low
0 findings. The new append-only identities are therefore readable before any
locale profile or graph writer may emit them.
