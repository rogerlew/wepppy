# Correctness and user-experience review — freshness first wave

## Metadata

- Package: `docs/work-packages/20260916_file_dependency_freshness/`.
- Reviewer: independent `freshness_correctness` agent, 2026-09-17 UTC.
- Base: `adb4f9b004459fc578460a95f30ac01ae1421f36`; review precedes implementation.
- Scope: proposed `docs/schemas/file-dependency-freshness-contract.md`,
  `artifacts/contract_decision.md`, appended production M1/M3 contract amendments,
  current source/artifact/get-state/download callers and compatibility tests.
- Authority: proposed freshness contract §§ Post-fire adoption, Cached digest,
  Compatibility; production M1 §§ live state/publication and accepted-file access;
  M3 soil snapshot authority; report contract §§ freshness and opened-file reads.
- Related evidence: `m1_correctness_inventory.md`, `m1_correctness_probe.json`,
  `digest_baseline.json`; independent security review is a separate gate.

## User outcome and scope

After a new accepted assessment, ordinary WEPP climate hard-link preparation
must preserve accepted currentness. Different bytes, settings, source provenance,
or engine identity remain grounds for stale output. Status reads do not rewrite
acceptance or prepare missing sources. A changed/failed build leaves previous
accepted outputs browsable; explicit rerun is the recovery for legacy metadata
drift. First-wave success does not satisfy the package's repository-wide goal.

The checkpoint correctly separates scientific equivalence from in-progress
worker snapshots and rollback/SQLite identity. Retaining strict admission and
publication checks is conservative but compatible with the authorized bounded
fix. M3 soil dependencies and CLI/parquet prerequisite ordering remain distinct
open consumers; do not present this checkpoint as resolving those paths.

## Valid-state matrix

| State | Valid? | Required behavior | Evidence / required implementation proof |
| --- | --- | --- | --- |
| Feature never used or optional dependency absent | Yes | No accepted-result claim; null source entry stays null; no acquisition from status reads | Contract explicitly preserves absent optional input; tests must call `sources/get_state`, not only a comparator |
| Present-empty ordinary file | Domain-dependent | Real empty-byte SHA-256 distinct from absence; existing parser/readiness policy decides usability | Checkpoint states this explicitly; direct empty-file test required |
| Populated new accepted snapshot | Yes | Complete names/path/size/hash and selections match; link/touch/same-byte replace preserves content currentness | Trigger reproduction plus non-postfire probe demonstrates stat limitations; new get-state/report/download regressions required |
| Legacy source snapshot without hash map | Yes | Compare old stat records exactly after projecting away newly added hash map; no invented historical digest | Contract requires strict-stat legacy behavior; mixed old/new snapshots need direct coverage |
| Accepted artifact with valid SHA-256 | Yes | Same-byte restore/link metadata churn stays accessible; changed bytes rejected; verify and stream same descriptor | Existing report `open_attachment` already separates accepted size/hash from read-time timestamps; route parity required |
| Four-field hashless artifact record | Readable metadata; not valid strong download proof | Existing metadata interpretation remains; published SHA requirement governs downloadable scientific artifact | Canonical M1 already requires SHA-256; existing route test uses a weaker synthetic fixture, noted below |
| Incomplete/malformed added hash map | No | Stale/unavailable, never silently downgraded to legacy | Exact key inventory and valid hashes required by checkpoint; missing, extra, null-for-present and malformed hashes need tests |
| Replaced input, escaped path, symlink or unreadable file | No or transient unavailable | Existing authorization/containment failures; no cache-based bypass; fail coherently on concurrent mutation | Descriptor/path before-after checks and access revalidation required; real filesystem tests pending |

## User-reachable error policy

| Condition | Classification | Required projection | Contract basis |
| --- | --- | --- | --- |
| Optional file was never present | Expected | Null/absent state, existing readiness policy | Freshness valid-state matrix and existing domain contract |
| Legacy acceptance metadata drift | Expected stale state | Retain historical results/downloads when accepted artifacts verify; explicit rerun to accept new provenance | Freshness compatibility section |
| Content changes during hash/read | Exceptional/transient | Explicit existing workflow error; no cache insertion or acceptance rewrite | Cached digest/read coherence section |
| No SHA for download | Invalid strong artifact proof | Existing changed-file/unavailable error, without clearing accepted records | Production M1 already requires published SHA-256 |
| Engine source changes during release | Expected stale state | Preserve numerical-engine mismatch; rerun disposable acceptance projects normally | Freshness compatibility section |

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-01 | Medium, resolved by checkpoint revision | Existing 64-entry cache is smaller than one representative M3 input working set, so adding ordinary-source hashes would repeatedly reread large inputs. | Reviewed checkpoint now requires a bounded 512-entry cache and records 179 source files + 26 engine files + artifacts. This addresses the concrete working-set issue without a new framework. Validate two interleaved project state reads, not just one-file cache hits. |
| COR-02 | Low, contract/test discrepancy | `tests/microservices/test_rq_engine_postfire_debris_flow.py:test_download_acceptance_and_changed_file` expects success from a synthetic four-field record; current route accepts it. | Current production M1 contract already requires SHA-256, and accepted upload/M1/M3 producer paths use `signature(..., strong=True)`. Treat the fixture as drift from that requirement; document the distinction when replacing it and add explicit hashless rejection plus valid legacy-source/hashful-artifact coverage. This is not evidence that legacy source snapshots may lose normal downloads. |
| COR-03 | Medium, outside first-wave scope | `production.sources` still uses CLI/parquet mtime ordering for Climate prerequisite readiness. A touch can therefore leave accepted content current while marking Climate unready. Soil inventories also retain their separate metadata identity. | Keep these consumers in the M1 inventory with explicit later-wave disposition. First-wave accepted-currentness tests must not claim full readiness equivalence or repository-wide resolution. |
| COR-04 | Low, acceptance gap | Benchmarks are single-file page-cache measurements, including only a 4 KB immutable SQLite snapshot. | Checkpoint correctly labels these limits. Whole-state warm reads, concurrent cache working sets, coherent SQLite/WAL cases, restored-mtime changes and live UI/RQ acceptance remain release gates, not completed evidence. |

No unresolved high or medium finding blocks this first-wave contract checkpoint.
The remaining open implementation/acceptance requirements are explicit and
cannot be substituted with mock-only helper tests.

## Review checks and verdict

- [x] Canonical intended delta and rationale are stated outside the work package.
- [x] Valid, absent, empty, legacy and hostile states have distinct requirements.
- [x] Source equivalence does not weaken locks, ownership, paths or coherent snapshots.
- [x] No silent migration, rerun or accepted-state rewrite is permitted.
- [x] Partial failure retains prior accepted files and diagnostics.
- [x] First-wave scope and open non-postfire findings are explicit.
- [ ] Direct unmocked tests for every changed boundary: implementation pending.
- [ ] Whole-working-set performance, stack restart and live UI/RQ/WEPP acceptance: pending.
- [ ] Final implementation correctness/security reviews: pending.

**Gate status: pass for the proposed first-wave contract checkpoint.**
**Release recommendation: hold pending implementation and acceptance gates.**
Reviewer sign-off: `freshness_correctness`, 2026-09-17 UTC. This sign-off does not
approve unrelated consumers or package closeout. The reviewed checkpoint must be
committed as an ancestor before production implementation edits.

## Artifact observability

The checkpoint retains the existing postfire attempts/source/predictor/results
inventory under normal browse/archive paths and introduces no hidden project
cache files. This satisfies the proposed design requirement. Writer-failure
retention, archive member equality and live browser/download evidence are still
required before completion; no such validation is claimed by this review.
