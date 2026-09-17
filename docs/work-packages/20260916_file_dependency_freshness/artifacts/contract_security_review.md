# Security review: first-wave freshness contract

## Findings

| ID | Severity | Surface / evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-C01 | Low, contract precision | `production.artifacts_current(strong=False)` is shared by accepted-state reads and locked publication. A content-equivalence change to this helper could inadvertently change finalizer behavior. | State explicitly that finalizer/admission call sites retain strict generation comparison and uncached full-hash checks at their existing execution boundaries; a reused flag must not silently weaken them. | Resolved in canonical Post-fire adoption section; implementation verification remains required. |
| SEC-C02 | Low, contract precision | RQ download currently uses `production.safe` followed by `Path.open`; report attachment uses `rainfall_io.open_local`, which rejects symlinks at descriptor admission through every path component. | Require the existing all-component no-follow descriptor admission or equivalent for changed download code, independently of accepted digest equality. | Resolved by explicit `rainfall_io.open_local` or equivalent admission requirement. |

The source-level findings in [M1 security inventory](m1_security_inventory.md)
remain independently tracked. In particular, SEC-M1-01 (NoDb mixed-generation
hydration) is outside this implementation wave and remains a package closeout
blocker. Checkpoint approval cannot close it. SEC-M1-02 (metadata-only post-fire
false staleness) is the intended first-wave correction, not yet implemented.

## Metadata and triage

- Reviewer: independent `freshness_security` agent, 2026-09-17 UTC.
- Implementation baseline: `adb4f9b004459fc578460a95f30ac01ae1421f36`.
- Reviewed: `docs/schemas/file-dependency-freshness-contract.md`, package
  `artifacts/contract_decision.md`, and File-content currentness refinement
  amendments in post-fire `docs/production_m1.md` and `docs/production_m3.md`.
- Related evidence: [correctness inventory](m1_correctness_inventory.md),
  [security inventory](m1_security_inventory.md),
  [performance baseline](digest_baseline.json), and
  [operation matrix](operation_matrix.md).
- Security impact: **high**. Dedicated review is required because changed
  digest/currentness and download admission affect file integrity and races.
- Stage: contract-only gate before implementation; final correctness, QA and
  security review of actual changes and restarted-stack evidence remain open.

## Threat model and valid states

An authenticated run user can select supported inputs; owners/workers can create
hard links, restore bytes, replace files or change permissions. Concurrent
cooperative writers can race readers. A process already able to alter run files
can attempt symlink replacement, same-size/restored-mtime changes or malformed
persisted records. Hash equality does not confer authority to read a path.
Privileged falsification of ctime/device/inode and simultaneous rewriting of
all trusted provenance is outside the ordinary filesystem model stated by the
contract.

The reviewed state matrix preserves absent optional inputs, present-empty bytes,
new populated snapshots, accepted historical values, and supported legacy
records. New malformed or incomplete hash maps are stale. Legacy snapshots keep
strict metadata behavior and do not gain inferred acceptance-time hashes.
Hashless legacy attachments are explicitly unavailable. This restores the
existing production M1 download requirement to validate accepted SHA-256; the
current four-field streaming fixture does not establish a contrary contract.
Hashless currentness remains strict metadata comparison. Changed metadata can
invalidate a cache entry without invalidating an equal accepted content digest.
Source/model/path/settings changes remain independent invalidators.

## Surface checks

| Surface | Assessment and required implementation evidence |
| --- | --- |
| Valid-state noninterference | Hard-link add/remove, chmod/touch and same-byte replace must preserve new accepted currentness when access/provenance remain valid. Legacy metadata drift remains conservatively stale. Verify real state/report/download paths, not only tuple equality. |
| Authentication, sessions, JWT, CSRF | No auth authority changes are proposed. Preserve existing `rq:export`, run access and config checks and browser authorization. Current content is not authorization. |
| Input/path/download safety | Preserve path/attempt/file allowlists, bounded regular files and nonsymlink admission; stream the verified descriptor. Missing/unreadable input or concurrent descriptor change fails explicitly. Test symlink swap and equal-size/restored-mtime replacement on real files. |
| Cache integrity | Absolute path/device/inode/size/mtime/ctime keys retain change detection. A miss must bind pre/post descriptor and pathname identity; failed reads never cache. Warm access checks remain required even when no bytes are rehashed. |
| Data integrity and concurrency | Strict attempt/publication comparisons and uncached execution hashes remain separate from accepted-result equivalence. NoDb locks, SQLite main/WAL/SHM/journal guards, rollback ownership and source-set closure are not amended. |
| Resource limits and availability | Existing bounded cache grows to 512 entries with an explicit representative-working-set rationale and retained timing budget. No persistent index, daemon, watcher or dependency is introduced. Repeated state-read and eviction evidence remains required. |
| Queue/worker/subprocess | No enqueue edges, worker identity, executable source, privilege or subprocess protocol changes are proposed. Tool/engine fingerprints remain authoritative; new production code can independently stale older results. |
| Secrets, tooling, network, supply chain | No secrets, tool scopes, outbound access, dependency or CI/CD changes are proposed. Disposable acceptance does not authorize mutations to named investigation runs or production deployment. |
| Logging/recovery/observability | Retain prior accepted results, attempt files, NoDb evidence and failures in normal browse/archive paths. No GET-time persistence migration or silent cache flush. Old readers conservatively treat additive snapshots as stale. |

## Validation evidence and limits

This review inspected current consumers and contracts, compared the proposed
semantics with existing report attachment behavior and tests, and reviewed the
first-wave benchmark and legacy/operation matrix. The M1 probe executed actual
NoDb hydration functions in the canonical container with real temporary files;
it establishes a separate open defect, not first-wave acceptance.

Required implementation validation includes real filesystem link/replace/touch,
missing/empty/legacy/hostile inputs, failed hash reads, concurrent replacement,
the public state/report/download paths, unchanged strict publication, actual
warm working-set behavior, and canonical archive/restore. The development
UI/RQ/WEPP acceptance must follow a rebuild/restart using normal identities,
groups, mounts and umask. These tests have not run against an implementation
because implementation has not begun at this checkpoint.

## Verdict and sign-off

Gate status: **PASS for the first-wave contract checkpoint**. Both identified
clarifications were incorporated and independently reread before this sign-off.
Unresolved checkpoint findings: high 0, medium 0, low 0.
No medium/high defect is identified in the proposed first-wave design. This is
not final package approval: known source-level defects remain open, later waves
need separate owner-contract decisions, and no implementation or live workflow
has been reviewed here.

Security reviewer: `freshness_security`, 2026-09-17 UTC. Package owner must retain
the independent correctness review and commit the accepted checkpoint as a
standalone ancestor before implementation. There is no risk acceptance in this
artifact and no permission to close the package with unresolved medium/high
findings.
