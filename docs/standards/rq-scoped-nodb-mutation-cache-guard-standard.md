# RQ Scoped NoDb Mutation Cache Guard Standard

Canonical contract for run-scoped RQ mutation paths that hydrate NoDb controllers from Redis-backed cache and then persist `.nodb` state.

## Purpose

Prevent stale-write signature mismatch in mutable RQ tasks by requiring scoped cache invalidation immediately before mutable hydration.

This standard defines when scoped cache invalidation is required, where it must be placed, and how to verify it with tests.

## Contract Classification

This is a canonical mutation-path coherence contract, not incident hardening.

Use incident packages to discover candidate call sites, but treat adoption as contract conformance across qualifying RQ paths.

## Applies When

Apply this standard to an RQ task path only when all conditions are true:

1. The path hydrates a run-scoped NoDb controller from the cache-backed loader (`getInstance(...)` or equivalent).
2. The same path performs mutable operations that can persist the controller's `.nodb` state (directly or through called methods).
3. Stale signature mismatch on write is part of the controller's correctness boundary.

## Must Not Apply

Do not apply scoped cache guards when any condition below holds:

- The path is read-only with no `.nodb` persistence side effect.
- The path operates on non-runid or ephemeral workspaces where `clear_nodb_file_cache(runid, ...)` is not the correct keying model.
- The path is a lifecycle flow whose contract already performs explicit broad cache/lock reset for the same run tree (for example delete/archive/restore class flows).

## Required Placement

For qualifying paths, the guard must execute:

1. After precondition checks (including directory-root/archive-root rejection where applicable).
2. Immediately before the first mutable controller hydration for the target scope.
3. With exact scoped `pup_relpath` covering only the controller(s) mutated in that step.

Preferred shape:

```python
def _mutate() -> None:
    clear_nodb_file_cache(runid, pup_relpath="controller.nodb")
    controller = Controller.getInstance(wd)
    controller.mutate_and_persist(...)
```

When a directory-root lock helper exists, place the guard inside the callback so archive/root rejection ordering remains unchanged.

## Scope Rules

- Use explicit file scope (`"soils.nodb"`, `"landuse.nodb"`, etc.) by default.
- For multi-controller mutation steps, issue one scoped clear per target file (for example `clear_nodb_file_cache(runid, pup_relpath="landuse.nodb")` and `clear_nodb_file_cache(runid, pup_relpath="soils.nodb")`), never run-wide clear.
- Avoid speculative scope broadening for prerequisite read paths that do not persist.

## Verification Requirements

Each newly guarded path must include targeted regression coverage asserting:

1. Exact `pup_relpath` value(s) passed to `clear_nodb_file_cache`.
2. Ordering: precondition checks occur before guard on rejection paths; guard occurs before mutable hydration on success paths.
3. Existing status/timestamp/enqueue/trigger behavior remains unchanged.

Recommended validation gates:

- `wctl run-pytest <targeted suites> --maxfail=1`
- `wctl doc-lint --path <touched docs>`
- `git diff --check`

## Adoption Guidance

Roll out this standard by auditing `_rq` call sites and classifying each path:

- `required`: meets all apply conditions and must be guarded now,
- `defer`: mutation boundary is real but needs separate package/test scope,
- `not_applicable`: read-only, non-runid workspace, or lifecycle reset path.

Record classifications in package docs with file-level evidence.

## References

- `wepppy/nodb/base.py::clear_nodb_file_cache`
- `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/package.md`
- `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/package.md`
