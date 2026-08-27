# Deliver the crash-recoverable project config update backend

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, an authorized project owner or administrator can ask whether
a flattened project config is missing newly registered attributes, review the
complete proposed addition, and explicitly enqueue one update. The worker adds
only those missing values and records provenance while preserving every
existing value. Merely opening or reading a project never changes it.

## Progress

- [x] (2026-08-26 23:15 UTC) Read the roadmap, PC-14/PC-15 contract, prerequisites, and subsystem instructions.
- [x] (2026-08-26 23:15 UTC) Scaffold the package and record compatibility, concurrency, and security plans.
- [x] (2026-08-26) Implement pure parent-chain reconstruction, complete preview, and opaque preview identity.
- [x] (2026-08-26) Implement locked journaled apply and deterministic interrupted-transaction recovery.
- [x] (2026-08-26) Implement authenticated rq-engine routes, async worker, reauthorization, and queue catalog wiring.
- [x] (2026-08-26) Add regression tests and generated-artifact evidence.
- [x] (2026-08-26) Run gates, reviews, archive, close, and commit.

## Surprises & Discoveries

- WP02 already exposes `updates_enabled`: a valid schema-v1 manifest enables
  updates even when its config digest differs, while malformed or newer
  manifests disable them.
- WP03 registry definitions contain stable component IDs, revisions, declared
  ownership, values, and constraints; preset parent chains instead refer to
  the checked-in shared defaults and preset config files created by WP04.
- The frozen route contract has explicit success/error classifications; WP08
  needed to register apply as `202` plus its `400`/`409` responses instead of
  accepting the generic POST `200` classification.

## Decision Log

- Decision: implement the backend in a dedicated NoDb-adjacent module with a
  pure preview boundary and a separate persistence boundary.
  Rationale: availability must be demonstrably read-only, while lock/journal
  behavior needs focused fault injection without route machinery.
  Date/Author: 2026-08-26, Codex.
- Decision: keep UI work out of WP08.
  Rationale: the ratified roadmap assigns header notice, digest warning, modal,
  and job-status UX to WP09; WP08 must expose the backend contract it consumes.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP08 delivered the dormant backend defined by PC-14/PC-15: pure complete
previews, owner/Admin/Root enqueue authority, worker-time reauthorization,
merge-only amendment provenance, project locking, and deterministic journal
recovery. The implementation adds no dependency and changes no deployment
default. The full suite passed (`6925 passed, 63 skipped`), and the focused
isolation quick gate found no issues. Diagnostic isolation executions also all
passed; its optional state-diff phase reported the existing common
`pyexpat.errors` and environment-baseline noise for every selected file.

The largest implementation lesson was that the route contract's success/error
classification table is authoritative alongside OpenAPI decorators. New async
routes must register their `202` and conflict/validation responses there in the
same change.

## Context and Orientation

`wepppy/nodb/project_config_reader.py` recognizes flattened configuration and
reports whether updates are safe. `wepppy/nodb/config_builder/registry.py`
loads current registered builder components. `wepppy/nodb/project_config_snapshot.py`
owns current named-preset sources and the manifest-v1 creation shape.
`wepppy/project_config_serialization.py` parses and serializes canonical config
bytes. WP08 will add a project update service beside those modules, an RQ job
under `wepppy/rq/`, and routes under `wepppy/microservices/rq_engine/`.

A preview identity is an opaque SHA-256-derived token binding the authority,
current config/manifest bytes, and exact proposed additions. A pending journal
is a small project-root JSON file containing enough validated prior/resulting
bytes and hashes to finish or reverse an interrupted two-file replacement
without re-resolving registry sources.

## Plan of Work

First implement source reconstruction for builder and preset manifests. Reject
invalid chains, inactive builder components, unknown preset sources, additions
outside declared ownership, overwrites, and unsafe values. Compare the current
canonical config with the complete current chain and return every missing
attribute plus source ID/revision and an opaque identity, without writing.

Then implement apply under one project-scoped amendment lock. Re-read and
re-preview after acquiring the lock, compare the submitted identity, serialize
the complete merged config, append one secret-safe amendment entry, write and
fsync temporary files, persist a journal containing expected hashes and file
images, replace config then manifest, and remove the journal. Recovery examines
hashes and deterministically finishes the recorded transaction or restores the
recorded prior pair. Concurrent requests that find no remaining delta return a
non-mutating unavailable result.

Finally add rq-engine availability, preview, and apply routes. Use canonical
JWT/run authorization plus owner/Admin/Root mutation authorization. Apply
enqueues one RQ job with the authenticated actor recorded in job metadata; the
worker rechecks authority before calling the service. Update the job dependency
catalog and prove the route/error/job contracts.

## Concrete Steps

Work from `/home/workdir/wepppy`. Iterate with focused `wctl run-pytest` calls.
After queue edits run `wctl check-rq-graph`, regenerating the canonical catalog
only through `python tools/check_rq_dependency_graph.py --write` if required.
Finish with stub/test-isolation checks, broad-exception enforcement,
documentation lint, and `wctl run-pytest tests --maxfail=1`.

## Validation and Acceptance

Tests must snapshot directory metadata around availability and preview to show
no writes. A generated flattened fixture must gain all currently missing
registered attributes in one apply while retaining every original value. The
manifest must contain one ordered amendment with source/value/revision and
prior/resulting digests, and no secret. Replaying the same preview, racing two
applies, using a stale preview, losing authorization, and injecting failure at
each replacement boundary must never produce a duplicate or inconsistent
pair. Routes must return canonical synchronous responses and a `202` apply
response containing `job_id`.

## Idempotence and Recovery

Preview is pure and repeatable. Apply is idempotent for one reviewed delta
because identity is bound to both starting files and exact additions. Retrying
after a crash first recovers the journal. Recovery never reads current source
definitions. The update feature flag remains absent/default-off, so merging
the code cannot expose updates before WP09/WP10/WP11 acceptance.

## Artifacts and Notes

Record focused/full test counts, route/error examples, queue graph results,
fault-injection cases, and review dispositions under this package's
`artifacts/` directory.

## Interfaces and Dependencies

Add no external dependency. Reuse canonical config parsing/serialization,
sanitization, RQ response helpers, auth helpers, Redis/RQ setup, and NoDb lock
patterns. Public types must describe preview additions and results without
exposing paths or config contents beyond the reviewed serialized values.

Plan revision note (2026-08-26): initial executable plan.
