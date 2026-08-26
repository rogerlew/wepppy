# Independent Scaffold Review - Fork Skip Omni Reset

**Reviewer**: independent risk-focused agent
**Date**: 2026-08-06
**Gate disposition**: HOLD before checkpoint acceptance

The proposed feature is sound, but the first scaffold omitted contract-critical
details. All findings below are accepted and must be incorporated before the
contract receives its required re-review and standalone checkpoint.

## Findings and Disposition

### REV-01 - Canonical amendment registration (Blocking)

Register this package as `SURF-04B`, a bounded high-security amendment composing
SURF-04, SURF-04A, DOM-25A, and DOM-25B without reopening or advancing those
owners. Update the child-package register and cross-link each owner. A root
project-tracker entry alone is not contract authority.

**Disposition**: accepted; implementation and checkpoint remain blocked.

### REV-02 - Reset ordering (High)

The reset must not hydrate copied `omni.nodb` before destination identity/path
rewrite. Required sequence: rsync exclusions; existing link normalization;
root NoDb identity/path rewrite; inherited filesystem lock and visibility-marker
cleanup; optional undisturbify mutations; clear destination Omni process/Redis
cache and exact Redis lock; one destination-only Omni reset; general inherited
job-marker reset; terminal completion.

**Disposition**: accepted; amend the normative sequence.

### REV-03 - Fresh Omni equivalence (High)

Reset every persisted Omni-owned field initialized by `Omni.__init__`, except
destination identity/config and documented volatile metadata. This includes
scenario/contrast definitions, labels, selection configuration, GeoJSON/upload
references, pairs, batch/output options, dependency trees, and run state. Empty
`_uploads` as well as scenario/contrast children and root `omni/`. Do not model
fresh reset as `clear_contrasts()` plus scenario deletion. Specify whether the
controller is rewritten or atomically replaced and preserve the actual config,
not an assumed `0.cfg`.

**Disposition**: accepted; fresh-state inventory is a checkpoint prerequisite.

### REV-04 - Exclude collection nodes (High)

Exclude the anchored source-relative entries `/_pups/omni/scenarios` and
`/_pups/omni/contrasts` themselves, regardless of source entry type, then
recreate real directories under a verified real `_pups/omni` parent. Excluding
only descendants could copy a symlink or special collection node. Test exact
rsync arguments and real-rsync behavior for directories, symlinks, and special
entries.

**Disposition**: accepted.

### REV-05 - Partial destination semantics (High)

Do not call the operation whole-run transactional. The route creates and may
register the destination before the worker. The exact guarantee is: reset is
idempotent, completes before success, emits `FORK_FAILED` and never
`FORK_COMPLETE` on failure, and leaves readiness false. An unready registered
partial destination may remain under existing behavior. Cleanup/tombstoning is
out of scope unless separately authorized.

**Disposition**: accepted; remove rollback implications.

### REV-06 - Checked-job readiness (Medium)

For checked five-argument jobs, readiness must additionally require a regular
`omni.nodb` and real empty `omni`, `_pups/omni/scenarios`, and
`_pups/omni/contrasts`. Reject symlinks/special entries without following them.
Preserve legacy four-argument readiness behavior.

**Disposition**: accepted.

### REV-07 - Mixed-version RQ rollout (Medium)

A new producer can pass five arguments to an old worker that accepts four.
Require a worker-first drain/restart cutover before enabling the producer, test
legacy four-argument jobs and omitted fields, update the RQ dependency catalog,
and run `wctl check-rq-graph` even if topology is unchanged.

**Disposition**: accepted.

### REV-08 - Exact destination cache/lock sequence (Medium)

Before Omni hydration, clear `omni.nodb` cache for the destination run and its
exact distributed lock. Reset under one canonical NoDb lock/write operation and
clear/reload cache after atomic replacement if replacement is used. Test stale
cache and lock state for a reused `profile;;` target. Never clear unrelated
controller or source state.

**Disposition**: accepted.

### REV-09 - Boundary and accessibility properties (Medium)

The eight valid boolean tuples are necessary but insufficient. Add omitted,
accepted, malformed, and repeated field cases; strict absent/false/true/hostile
query hydration; restored tracked-job behavior without checkbox inference;
returned resolved-value display; semantic label and keyboard operation; and
legacy four-argument job/readiness inspection.

**Disposition**: accepted.

### REV-10 - Source evidence scope (Medium)

Hash source state only in a quiescent fixture. Separately assert that no
reset/cache/lock API receives the source run ID/path. Preserve the existing
no-snapshot-consistency contract during concurrent source editing.

**Disposition**: accepted.

## Re-review Gate

Before checkpoint acceptance, amend the contract, package, tracker, ExecPlan,
child register, and owner cross-links; then obtain independent confirmation for
REV-01 through REV-05 and complete the separate security review. No production
implementation may begin while this gate is on hold.
