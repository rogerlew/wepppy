# Culvert catalog/RedisPrep contention repair

Status: completed and verified on forest; production unchanged.
Broad suite retains one confirmed unrelated baseline template failure.

The operator identified parallel culvert `BlockingIOError` failures as a defect.
Forest batch `cbdb8928-114f-4b8f-8c79-f46ecf354f24` needed three serial retries.
A real two-process sibling-scope probe reproduced errno 11 at the nonblocking
catalog lifecycle acquisition. Ordinary catalog writes bypass the serializer
already used by RedisPrep setters.

This is a conformance repair to unchanged catalog fencing and RedisPrep
setter-serialization requirements. Preserve the managed-owner lifecycle lock,
stale-wrapper rejection and immediate genuine lifecycle conflicts. Coordinate
short metadata critical sections through the existing serializer. No new service,
dependency, queue, lockfile class, model parameter or artifact schema is authorized.

Security impact: high after operator-authorized WBT subprocess/configuration expansion.
See [dedicated security review](artifacts/security-review.md). Independent correctness/security review must prove valid
concurrent writes complete and destructive replacement remains fenced. No auth,
access, permissions or deployment topology change. Production deployment excluded.

Acceptance: deterministic real Redis/filesystem/process races; retained lifecycle
and stale-writer tests; fresh parallel forest payload replay without retries;
generated-output readback and authenticated archive comparison.

Authority: [RedisPrep snapshots](../../schemas/redisprep-snapshot-contract.md) and
[catalog refresh](../../schemas/query-engine-catalog-refresh-contract.md).
Execution: [active plan](prompts/active/implementation_execplan.md).
Prior evidence: [clone regression](../../dev-notes/culvert-catalog-clone-regression.md).

The active plan now also repairs shared WBT settings and parent-cwd mutation in
all bindings and bundled plugins. No new dependencies or private-binary workaround.
See [correctness review](artifacts/correctness-review.md) and
[live regression](live-regression.md).
