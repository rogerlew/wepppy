# Contract Decision - Fork Skip Omni Scenarios/Contrasts and Reset

**Status**: Amended; implementation blocked pending follow-up reviews and checkpoint
**Base revision**: `0ba059521`
**Operator direction date**: 2026-08-06
**Package ID**: SURF-04B
**Composed owners**: SURF-04, SURF-04A, DOM-25A, DOM-25B

## Decision

The fork console gains a checkbox labeled **Skip Omni Scenarios/Contrasts and
reset controllers**. Its canonical field is
`skip_omni_scenarios_contrasts`, its default is `false`, and omission is
equivalent to `false` at every boundary.

## Normative Contract

1. The server renders the checkbox from a strict boolean initial value. The
   client serializes exactly `"true"` or `"false"`; it never infers this option
   from either existing fork checkbox.
2. rq-engine parses the field as a boolean, returns its resolved boolean value
   in the accepted response, and passes it as an explicit final argument to
   `fork_rq`. Existing response/error/auth contracts remain unchanged.
3. When `false`, rsync arguments, copied paths, controller state, status events,
   and completion behavior remain unchanged.
4. When `true`, rsync excludes the anchored source-relative collection entries
   `/_pups/omni/scenarios` and `/_pups/omni/contrasts` themselves, regardless
   of source entry type. No other `_pups` child or root project path is excluded.
5. Before fork success, the destination contains real, empty directories at
   `_pups/omni/scenarios`, `_pups/omni/contrasts`, and `omni`. The worker must
   open and verify the destination root, `_pups`, and `_pups/omni` ancestors
   with no-follow real-directory checks before recreating the collections. It
   rejects symlink or special-entry ancestors/reset roots without following or
   mutating their targets.
6. The destination `omni.nodb` is behaviorally and serially equivalent to a
   newly initialized Omni controller using the destination's actual config,
   run identity, and version contract. Reset covers every persisted Omni-owned
   field initialized by `Omni.__init__`: scenarios, contrasts, labels,
   selection configuration, GeoJSON/upload references, pairs, batch/output
   options, dependency trees, and run state. Comparisons exclude only
   documented volatile metadata such as timestamps, version/commit provenance,
   and file signatures. `_uploads` is not preserved. Implement one public
   `Omni.reset_for_fork()` operation that loads the already identity-rewritten
   destination controller using its persisted actual config, resets every
   Omni-owned field to the same values assigned by `Omni.__init__`, and persists
   once with the canonical lock/dump transaction. It rewrites the existing
   `omni.nodb`; it does not replace the file and is not `clear_contrasts()` plus
   scenario deletion. Clear the destination cache before loading and again
   after persistence, then reload once to prove persisted fresh equivalence.
7. The checked sequence is: rsync exclusion; existing link normalization;
   existing root NoDb identity/path rewrite; inherited filesystem lock and
   visibility-marker cleanup; optional undisturbify destination mutations;
   clear destination Omni in-process/Redis cache and exact Redis lock; perform
   one destination-only Omni reset under the canonical NoDb lock/write
   transaction; remove exactly the `run_omni_scenarios` and
   `run_omni_contrasts` RedisPrep timestamps; invalidate copied query-engine
   `catalog.json` and `cache` with the existing bounded helper; reset inherited
   general job markers; then publish or enqueue terminal completion. Copied
   `omni.nodb` is never hydrated before destination identity rewrite. Unrelated
   RedisPrep timestamps and query-engine source data remain unchanged; normal
   catalog regeneration rediscovers retained datasets.
8. Reset is destination-only, idempotent for an unready destination, and must
   complete before success. Failure emits `FORK_FAILED`, never `FORK_COMPLETE`,
   and checked readiness remains false. Existing behavior may retain an unready
   registered partial destination; cleanup, tombstoning, and whole-run rollback
   are out of scope. No source reset/cache/lock API is invoked.
9. The option composes independently with `undisturbify` and
   `skip_wepp_runs_output`. Those existing flags retain their current behavior;
   all eight boolean combinations are valid.
10. The option does not enqueue an Omni rebuild and does not reset any controller
    other than Omni. Removing the two Omni lifecycle timestamps is a narrowly
    scoped RedisPrep metadata mutation, not a general RedisPrep reset.
11. Legacy four-argument job readiness remains unchanged. For a checked
    five-argument job, readiness additionally requires regular `omni.nodb` and
    real, empty `omni`, `_pups/omni/scenarios`, and `_pups/omni/contrasts`;
    symlink and special entries are rejected without following them.
12. Deployment is worker-first. Drain/restart the fork/archive workers with the
    backward-compatible fifth-argument default before enabling the updated
    producer. Omitted API fields and legacy four-argument jobs resolve to
    `false`. Update the RQ catalog and run `wctl check-rq-graph` even if graph
    topology is unchanged.

## Property and Regression Contract

Tests generate the Cartesian product of the three fork booleans. For every
combination they prove:

- rendered initial state equals the server boolean;
- submitted payload and parsed value preserve each boolean independently;
- schema/default and success response expose the new field as a boolean with
  default `false`;
- enqueue argument order and worker decisions preserve the complete tuple;
- Omni exclusions/reset occur if and only if the new field is `true`;
- WEPP exclusions occur if and only if the existing WEPP rule requires them;
- undisturbify rerun behavior occurs if and only if `undisturbify` is `true`;
- unrelated `_pups` sentinels and quiescent-fixture source hashes are invariant;
- no reset/cache/lock helper receives the source run ID or path.
- exactly the two Omni RedisPrep timestamps are absent if and only if the new
  option is true, while unrelated timestamps are invariant;
- copied query-engine catalog/cache is invalidated if and only if required by
  undisturbify or the new option, and regenerated discovery retains unrelated
  datasets without stale Omni entries.

Additional integration tests populate scenarios, contrasts, aggregate files,
sidecars, `_uploads`, every persisted initialization field, stale destination
cache/lock state for a reused `profile;;` target, and unrelated siblings. The checked fork
must load a fresh Omni controller and contain empty real collection/aggregate
directories; the unchecked fork must retain the populated fixture. Injected
reset failure must produce the canonical failed job behavior without a success
trigger.

Boundary properties cover omitted fields; all accepted boolean encodings;
rejected malformed and repeated values according to the common parser contract;
absent/false/true/hostile query hydration; restored tracked-job sessions without
checkbox inference; display of the returned resolved value; native checkbox
label and keyboard accessibility; and legacy four-argument job/readiness
inspection. Real-rsync tests cover ordinary, symlink, and special collection
entries and prove only the two anchored nodes are excluded.

Fresh-equivalence tests compare every Omni-owned persisted field assigned by
`Omni.__init__` against a fresh controller created with the same destination
working directory and config. Only named NoDb base/provenance metadata is
excluded. Tests prove one rewrite/dump, pre-load and post-persist cache clears,
exact destination lock use, and successful reload; file replacement is forbidden.

## Compatibility and Rationale

The default is `false` to preserve existing clients and fork behavior. Source
hash evidence uses a quiescent fixture and does not add snapshot locking or
change the existing warning against concurrent source edits. Merely
excluding child directories was rejected because copied `omni.nodb` and
aggregate outputs would advertise child projects that do not exist. Deleting
all `_pups/omni` was rejected because the contract is explicitly limited to
scenario/contrast projects and must recreate a canonical empty structure.

## Required Checkpoint Gate

Before implementation:

1. confirm the exact fresh-state field inventory and reset/cache/lock sequence;
2. obtain two independent read-only reviews, including security;
3. disposition every finding and obtain post-fix confirmation for medium/high
   findings;
4. record explicit operator acceptance of the final matrix; and
5. commit this decision, reviews, disposition, package, tracker, and plan as a
   standalone ancestor.
