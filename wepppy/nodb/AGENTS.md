# NoDb Agents Guide

This file captures the operational quirks of `NoDbBase` so debugging (and test
harnesses) stay consistent across agents.

Canonical behavioral contract:

* Follow `docs/standards/contract-first-change-standard.md`, including its finite
  canonical-authority set, conflict handling, and ancestor-checkpoint gate.
* `docs/schemas/nodb-persistence-concurrency-contract.md` is the authoritative
  lock/persistence/cache specification for `NoDbBase`.
* Applicable current canonical domain and shared/cross-cutting contracts are
  normative for UI-coupled NoDb inputs, mutation, persistence, and reload.
  Historical and archived plans are context only.
* Before an intended behavior change, complete the accepted contract-decision
  checkpoint and amend every applicable contract in its ancestor revision; then
  update NoDb code, tests, and this playbook. If code diverges from an unchanged contract, restore
  conformance and add regression evidence without rewriting normative behavior.
  If contracts conflict or intent is unclear, stop and ratify the resolution
  before editing implementation.

## Facade + Collaborator Standard

* Canonical Option-2 extraction guidance lives at
  `docs/standards/nodb-facade-collaborator-pattern.md`.
* Use that standard when refactoring a NoDb controller into collaborators while
  preserving facade contracts.
* Keep the extraction order consistent: input parser -> build
  router/orchestrator -> mode-specific builders -> scaling -> artifact export ->
  station/catalog resolution.

## Task Start: `nodb/core` Bugfixes

* First-hop files:
  * `wepppy/nodb/base.py` (locking, serialization, cache behavior)
  * `wepppy/nodb/core/*.py` (controller-specific behavior)
  * `tests/nodb/` (unit/integration expectations for NoDb flows)
* Iteration checks:
  * `wctl run-pytest tests/nodb --maxfail=1`
  * `wctl run-pytest tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py --maxfail=1`
* Handoff checks:
  * `wctl run-pytest tests --maxfail=1` (or document why not run)
* For shared fixtures, markers, and stub isolation expectations, read
  `tests/AGENTS.md`.

## Project Data / Schema Mutations (Required)

* Applies to lookup-table headers, NoDb keys, route payload contracts, and
  generated artifact schemas.
* Before edits, write a short downstream-impact and backward-compatibility plan.
  If operator intent is unclear, ask before mutating schemas.
* Prefer additive compatibility. Do not rename/remove user-visible columns or
  keys unless explicitly approved by the operator.
* Validation must include both:
  * regression tests for the mutated path, and
  * propagation evidence that mutations reach expected generated outputs (for
    disturbed flows, this includes `wepp/runs/*` artifacts when applicable).
* Update related docs in the same change set (`README`, `ENDUSER`, usersum/API
  docs as relevant).

## Locking & TTL Notes

* Every NoDb controller serializes state to `<wd>/<controller>.nodb` and keeps a
  distributed lock in Redis (`nodb-lock:<runid>:<relpath>`). The default TTL is
  read from `WEPPPY_LOCK_TTL_SECONDS` (6 hours if unset).
* Current implementation has no built-in heartbeat/renewal. Lock ownership is
  checked before persistence, but long critical sections that exceed TTL can
  still be contended by another participant after expiry.
* For TTL-sensitive tests, patch `LOCK_DEFAULT_TTL` or pass `ttl=` to `lock()`
  in targeted unit tests; do not assume additional TTL override helpers exist.

## Cache Refresh Semantics

* Instances are cached per working directory. Cache reuse is gated by on-disk
  `os.stat` signature checks (`mtime` + `size`); writable `getInstance()`
  refresh checks use strict signature comparison, while Redis/detached cache
  signature checks use mtime epsilon tolerance for precision drift.
  There is no SHA-256 digest gate in the current path.
* When a writable cached instance drifts from disk, `getInstance()` rehydrates
  and updates the cached object in place so existing references see refreshed
  attributes.
* Redis cache payloads are treated as a fast path, but stale-signature payloads
  are ignored and refreshed from disk.

## Persistence Semantics (Atomic Write Path)

* `NoDbBase.dump()` persists via temp-file write + `os.replace()` in the same
  directory, not in-place truncate/write. This is required so concurrent readers
  do not observe empty/partial JSON windows.
* Parent directory fsync can fail on NFS after replace (for example stale handle
  interruptions). Treat that as a durability warning path: the content replace
  may already be committed and should not be reclassified as a stale-write
  rejection.
* Replace failures must not poison `_nodb_mtime`/`_nodb_size`; signatures are
  assigned only after commit so retry attempts are not falsely rejected.
* Mode semantics:
  * rewrites preserve existing file mode,
  * first-create uses umask-derived mode (`0o666 & ~umask`).
* Regression coverage anchor:
  `tests/nodb/test_base_boundary_characterization.py` (atomic contention,
  legacy truncate deficiency characterization, replace-failure cleanup/retry,
  mode semantics, and ESTALE post-commit fsync behavior).

## Common Debug Hooks

* `lock_statuses(runid)` reports distributed-lock-derived lock status and
  normalizes legacy `locked:*` compatibility flags.
* `clear_locks(runid, pup_relpath=...)` and
  `clear_nodb_file_cache(runid, pup_relpath=...)` are the canonical recovery
  hooks for lock/cache cleanup during triage.
* `redis_lock_client` is expected to exist for tests that exercise locking; the
  test harness stubs the client when running without Redis.

## When Adding Features

* Make sure every new public helper is exported via `__all__` so tests can opt
  in explicitly.
* If you add behaviors that depend on environment variables, also expose a test
  seam so targeted pytest modules can simulate edge cases without rewriting
  global process state.
