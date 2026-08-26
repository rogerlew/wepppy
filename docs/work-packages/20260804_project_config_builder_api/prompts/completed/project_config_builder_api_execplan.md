# Deliver the authenticated project config builder API

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

WP06 lets an authenticated client retrieve the registered builder vocabulary,
validate a complete proposal, and synchronously create one project-owned
`config.cfg` project. The same server resolution drives review and creation;
stale schemas and unauthorized resolution overrides fail before allocation.

## Progress

- [x] (2026-08-26 22:05 UTC) Verify prerequisites, contract, checklist, auth, registry, and creation primitives.
- [x] (2026-08-26 22:05 UTC) Scaffold package and record compatibility/security plans.
- [x] (2026-08-26 22:32 UTC) Implement builder manifest/materialization service.
- [x] (2026-08-26 22:32 UTC) Wire authenticated description/validation/create endpoints.
- [x] (2026-08-26 22:32 UTC) Add API, generated-output, failure, role, and idempotency tests.
- [x] (2026-08-26 22:32 UTC) Run gates, review, archive, close, and commit.

## Surprises & Discoveries

- WP03 already resolves complete canonical bytes and provenance, while WP04
  already provides safe atomic pair writes and Redis creation reservations.
- Rq-engine normalizes string and named-role claims case-insensitively in its
  authentication module, matching the cell-size contract.
- Adding agent-facing routes also requires synchronized endpoint inventory,
  route checklist, response-rule, count, and OpenAPI budget updates; the full
  suite exposed the inventory guard omitted by the initial focused selection.

## Decision Log

- Decision: add one builder router under `/api/project-config/builder` and reuse
  the current bearer JWT `rq:enqueue` scope.
  Rationale: it is additive, synchronous, and compatible with the established
  browser session-token bridge.
  Date/Author: 2026-08-26, Codex.
- Decision: place exact payload parsing and manifest construction in a pure
  builder service, leaving HTTP/auth/cleanup translation in the router.
  Rationale: validation and creation can prove byte-identical resolution.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP06 delivers three authenticated synchronous builder routes, a pure candidate
and manifest service, strict default-off creation, current-role override
authorization, atomic project-owned artifacts, and WP04 idempotency/cleanup.
Generated output reopens through WP02 without fallback. Correctness and
high-security reviews have no unresolved findings, and the exact full suite
passed with 6,898 tests and 63 skips.

## Context and Plan

`wepppy/nodb/config_builder/registry.py` loads immutable registered components;
`resolver.py` produces canonical bytes and a complete provenance chain.
`wepppy/microservices/rq_engine/creation_idempotency.py` and WP04 route helpers
own once-only creation and cleanup. Add a builder snapshot service that parses
an exact selection object, resolves it, creates schema-v1 builder manifest
bytes, and adapts the pair to WP04's atomic materializer. Add three router
operations: GET description, POST validation, and POST creation. All require
current JWT scope, use canonical envelopes, and reject unknown payload fields.

Creation checks the submitted opaque revision, role permission, and complete
proposal before reserving/allocating. It then writes both files, constructs Ron
with `config.cfg`, initializes ownership/readme/TTL, completes idempotency, and
returns run ID plus `/config` location. Every post-allocation failure invokes
the existing scoped cleanup and reservation release.

## Validation

Run focused builder service and route tests, stubtest new modules, microservice
and NoDb suites, broad-exception enforcement, docs lint, and the exact full
suite. Acceptance requires real generated `config.cfg`/manifest reopening
through WP02, field-addressable 400s, stale 409, forbidden 403, replay/conflict,
and default-off behavior.

## Recovery and Handoff

All resolution is read-only and repeatable; materialization refuses overwrite.
The disabled writer publishes no project. WP07 receives endpoint/payload
evidence; WP11 owns Forest and mixed-version validation. No new dependency,
queue edge, config token input, or deployment default is introduced.

Plan revision note (2026-08-26): initial executable plan.

Plan revision note (2026-08-26): completed implementation, contract inventory
reconciliation, review, and validation evidence; ready to archive.
