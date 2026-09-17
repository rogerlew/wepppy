# File dependency freshness audit and fixes

**Status:** Executing M1, 2026-09-17 UTC (2026-09-16 Pacific).

## Purpose

Inventory repository-wide file-based dependency tracking and fix demonstrated
false-stale and false-current decisions. The trigger is a post-fire M3 report
marked stale after WEPP created a hard link to an unchanged climate file.
The owner authorized execution of this package on 2026-09-17 UTC. Proceed
through the staged acceptance gates, including independent reviews and
development-stack acceptance on disposable projects. Production deployment
and mutation of named investigation runs remain excluded.

## Scope and intended behavior

Classify every discovered freshness/signature consumer and its writers across
`wepppy/`, `services/`, `tools/`, browser source and operational scripts. Trace
NoDb/RQ/preflight/report propagation, digest caches, file materialization,
archive/fork/restore, external raster masks, and SQLite main/WAL snapshots.
Search ctime/mtime, size/inode identity, signatures/fingerprints, hashes/digests,
manifest comparisons, completion timestamps, ETags and language equivalents.
Do not limit discovery to `st_ctime` or assume every timestamp is a defect.

For dependencies whose contract is content equivalence, harmless link or
metadata operations must not alone invalidate accepted output. Real content
changes must still invalidate output, including equal-size rewrites and restored
mtime. Path, source provenance, scientific settings, permissions, containment,
concurrency and snapshot identity remain separate obligations. A matching file
hash cannot bless an unauthorized path or a mixed-generation input set.

Runtime identity, metadata and content serve different roles. Keep identity checks
needed to avoid races; metadata may trigger content revalidation without deciding
scientific staleness. Decide raw-byte versus semantic identity per consumer;
semantic parsing is not a repository-wide default and must not hide meaningful
changes in headers, units, encodings or provenance.

## Complexity budget

Reuse current signature/hash, manifests, locking and archive mechanisms. Start
with a bounded regression for the observed post-fire/WEPP path, then fix other
confirmed consumers in coherent groups. New services, queues, databases,
watchers, hashing daemons, dependencies and deployment topology: none. Do not
replace all signatures with a universal framework or hash all large inputs on
every browser poll. Shared helpers require actual repeated semantics and retained
performance evidence. Record every inventory entry as fixed, verified-safe,
nondependency or a justified unresolved finding; do not silently omit hotspots.

## Compatibility and authority

Before persisted signature/schema changes, document old/new reader and writer
behavior, cache invalidation, rollback and generated-artifact propagation.
Prefer additive/versioned evolution. Do not rewrite accepted scientific results
or closed packages. Legacy records lacking hashes must not be silently blessed
as current; choose and document an explicit compatible behavior at the contract
checkpoint. Do not clear caches or rerun user projects to hide defects.

Canonical changes belong in the contracts named by each subsystem AGENTS.
If no suitable cross-cutting contract exists, propose
`docs/schemas/file-dependency-freshness-contract.md` during execution, ratify it
and link affected domain contracts. This proposed file does not exist yet and
this scaffold does not replace current authority. For UI-coupled changes, follow
the full contract-first checkpoint, independent reviews and ancestor commit.

## Security impact and reviews

**Impact: high.** Signature changes can affect integrity, concurrency, path
identity and hostile file replacement. Dedicated security and correctness
reviews are mandatory before implementation checkpoint and final closeout;
retain artifacts using repository review templates. Review valid-state
noninterference alongside rejection of malformed/hostile states. No review
has been conducted or approval granted by this scaffold.

## Mandatory acceptance

- Complete discovery and disposition of dependency consumers, with search scope
  and exclusions retained; demonstrate every claimed fix with a failing baseline.
- Preserve true-content invalidation and publication/read race safeguards.
- Verify legacy signatures, missing/empty/optional inputs and failed replacements.
- Benchmark representative climate, large raster and SQLite paths, including
  repeated status/report reads and cold/warm digest behavior.
- Update all affected contracts and user/operator/developer documentation.
- Run appropriate focused gates and required pre-handoff regressions.
- **Rebuild affected assets/services, restart the development stack, then run
  real end-to-end acceptance through UI/RQ and WEPP preparation.** A successful
  restart or mocked tests alone cannot close this package. Use disposable
  projects/clones; existing named runs remain read-only unless specifically
  included in execution authorization. No production deployment is implied.
- Validate generated artifacts, browser/report/preflight agreement, and canonical
  archive/restore on isolated copies. Retain failure and recovery evidence.

## Hardening lifecycle

Confirmed symptom: accepted M3 currentness changes after active CLI ctime changes;
all parsed climate columns still match the accepted input. Hard-link preparation
is strongly supported by inode identity, code path and timing; exact historical
syscall attribution is not claimed. Reproduce it deterministically first.
Health: unchanged-content operations preserve current results; content changes
invalidate them; performance stays within a recorded budget. Danger: stale
results accepted after rewrites, transient mixed snapshots, security checks
removed, or repeated large reads on status polls. No temporary bypass or global
cache flush is planned. Exercise the entire operation matrix before closeout;
record a follow-up observation checkpoint after the next ordinary WEPP run.

## Deliverables and references

Deliver a complete inventory, per-consumer contract decisions, compatibility and
operation matrices, reviewed checkpoint, staged fixes/tests, benchmarks, restarted
stack evidence and final review disposition. No scientific parameterization change
is intended; any formulas/defaults/unit-policy change requires a separate ADR.

- [Seed inventory](artifacts/seed_inventory.md)
- [Operation matrix](artifacts/operation_matrix.md)
- [Trigger evidence](../../investigations/20260917_dead_horse_cli_freshness/findings.md)
- [Tracker](tracker.md)
- [ExecPlan](prompts/active/file_dependency_freshness_execplan.md)
