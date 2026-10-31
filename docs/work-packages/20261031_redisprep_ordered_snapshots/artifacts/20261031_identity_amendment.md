# RPS-01A bounded identity amendment

2026-10-31 UTC. Parent checkpoint 88b5c174f. Implementation review found that
binding a markerless wrapper to None rejects later normal catalog initialization.
Security review reproduced a healthy loaded reader in a mode-0555 directory
failing because the new constructor tried to create coordination directories.

The simpler schema-free approach misses successful-path acceptance. Initialize-
before-binding would force writes on healthy readers; comparing only directory
inodes misses archive replacement. Proposed smallest escalation: one additive
`initialization_only: true` field in the existing catalog incarnation JSON,
written solely on initial creation, never on destructive rotation. No new file,
Redis key, service, lock, privilege, mount or snapshot envelope. Missing bit is
false. Existing readers ignore unknown JSON fields. Operational cost is one
boolean read, with no scan or retention obligation. Mixed older marker producers
may require wrapper reload rather than inferred provenance.

Operator authorized the bounded coherent-recovery correction and checkpoint
commit/proceeding. This refinement preserves that requested behavior and healthy
read access; no separate runtime workflow change is proposed. Amend both current
contracts and obtain two read-only reviews before implementation of this bit.
Regression: loaded reader under UID1000 mode0555; wrapper constructed before
normal catalog initialization accepts completion; in-place restore still fences
old wrapper; legacy missing bit stays conservative.

Security review correction: an interrupted restore must not delete the replacement
fence and later appear initially markerless. Both contracts now require durable
pre-destructive rotation and retention of the incarnation/held coordination inode
through cleanup, extraction and failure. Archive markers cannot overwrite them.
Failure before durable fencing prevents destruction. Kill regression must cover
old markerless wrapper -> interrupted restore -> initial catalog request -> stale
write rejection. This reuses existing metadata, not another marker.

Independent read-only reviews: contract_correctness approved; contract_security
initially found interrupted replacement provenance loss, then approved after
pre-destructive fence retention became mandatory. Both re-reviews approve the
bounded amendment; implementation and environment evidence remain pending.
