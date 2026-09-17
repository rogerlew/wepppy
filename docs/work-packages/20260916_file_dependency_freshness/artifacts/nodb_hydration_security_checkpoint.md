# NoDb hydration conformance security checkpoint

Reviewer: independent `freshness_security`, 2026-09-17 UTC.
Scope: `artifacts/nodb_hydration_conformance.md`, current `_read_retry.py`, both
NoDb disk loaders, and `docs/schemas/nodb-persistence-concurrency-contract.md`.
No NoDb implementation change has been reviewed or approved. The final proposal
was independently reread before this checkpoint disposition.

## Verdict

**PASS for the bounded checkpoint. The payload/descriptor-signature pairing
restores unchanged disk-authority intent; the explicit read-drift error
classification is now documented in the amended canonical contract.**
The remedy directly addresses SEC-M1-01 without changing persisted JSON fields,
Redis authority, cooperative writer ownership, file mode, locking or atomic
publication. A complete earlier payload associated with its own version is
permitted; A associated with replacement B's version is not.

| ID | Severity | Issue and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| NODB-S01 | Medium, valid-state noninterference | The initial proposal did not specify its time fields. Atomic replacement can change the old inode's ctime/link count even while its descriptor supplies a complete unchanged older payload. | Specify guard fields and preserve complete earlier descriptor reads; require real replace-during-open/read regression separately from replace-during-decode. | Resolved: canonical Coherent disk-read versions specifies device/inode/size/mtime_ns and explicitly excludes ctime-only rejection; proposal requires both replacement tests. |
| NODB-S02 | Low, contract alignment | Synthetic ESTALE for observed read drift is a newly selected error classification; canonical Change Management requires same-set documentation. | Document read-only retry scope, errors and optional absence in the canonical contract. | Resolved in Coherent disk-read versions: only existing opt-in read retry, immediate propagation outside it, unchanged optional ENOENT and permission/error classification. |

Unresolved checkpoint findings: high 0, medium 0, low 0. The canonical update is
`docs/schemas/nodb-persistence-concurrency-contract.md`, Hydration and Cache
Contract / Coherent disk-read versions (implementation pending). It documents
both the durable payload/version association and why ctime-only drift is not
evidence of mixed content under cooperative atomic writers. Commit this reviewed
checkpoint before implementation; SEC-M1-01 itself closes only after code and
regression verification.

## Concrete valid-state evidence

A disposable local real-file probe opened A, atomically replaced its pathname
with B, read A through the original descriptor, then compared descriptor stats.
It observed on iteration 1:

```json
{
  "old_descriptor_content": "complete old payload",
  "path_content": "complete new payload",
  "descriptor_size_unchanged": true,
  "descriptor_mtime_unchanged": true,
  "descriptor_ctime_changed": true,
  "link_count_before": 1,
  "link_count_after": 0
}
```

No mocked timestamps, named project, Redis state or production file was involved.
This is harmless atomic replacement, not in-place content mutation. The proposed
fix must not conflate its ctime change with a partial/mixed JSON read.

## Required closure evidence

- Existing retained SEC-M1-01 probe must return A with A's descriptor signature,
  not B's pathname metadata, in both `_hydrate_instance` and `load_detached`.
  Normal cache validation/stale-write behavior must reject or refresh that older
  state when compared with a later cooperative writer's distinguishable version.
- Test normal and empty/malformed reads, required errno/filename preservation,
  immediate optional absence, observable in-place read drift, and opt-in scoped
  retry. Synthetic instability must not hide EACCES/EIO or decode failures.
- Preserve read-only and detached behavior, existing `read_text` callers,
  initial-read deadline/backoff, Redis mirror handling, and failed-read cache
  behavior. Do not expand the NoDb freshness key or introduce global invalidation.
- Run focused NoDb/retry and API/stub gates and retain actual atomic-replacement
  evidence. This checkpoint cannot close SEC-M1-01 before implementation review.

The ordinary cooperative atomic writer contract remains the scope. This bounded
fix does not promise isolation from arbitrary out-of-band in-place writes or
equal-metadata rewrites, and does not waive any first-wave post-fire or final
runtime acceptance gate.
