# PF-R02 lineage checkpoint correctness review

Independent review by `freshness_correctness`, 2026-09-17. Scope:
`docs/schemas/climate-parquet-lineage-contract.md`,
`artifacts/cli_lineage_contract_decision.md`, and the publication-verification
amendment in post-fire `docs/production_m1.md`. No production/test edits.

**Checkpoint PASS after the recorded refinements and measured budget amendment.**
The original pending performance gate is resolved by the final review below;
the contract may proceed to its ancestor checkpoint. No remaining major
correctness objection to the current bounded contract was identified.

## Findings and dispositions

| Review point | Disposition in revised canonical contract |
| --- | --- |
| Rows must represent the recorded CLI bytes, not a later live-path hash | Parse the retained verified snapshot; capture selected/resolved portable identities and compare fresh selection/content before publication |
| A stale Climate object is not authoritative after another process changes selection | Freshly reload the owner before final comparison. Actual build-router and defined-climate export call sites run after the relevant owner transactions, so this does not require publishing unsaved transient selection |
| Interchange is a second real producer with a different source selector | Reapply its captured hint/first-sorted fallback rule; record what it actually parsed without asserting that it selected the Climate owner. Preserve the existing-file calendar fast path |
| Ambiguous proof schema could allow an unknown/malformed receipt to pass | Exact fields/types, integer-not-bool version, producer/interpretation allowlist, duplicate/extra-key rejection and bounded footer/proof parsing are explicit |
| Footer proof and source inventory could observe different Parquet generations | Same-generation coherence applies to both full-content and `content=False` authority checks; disabling the full hash map never disables active CLI lineage verification |
| Broad logged-None language would change actual parser errors | Existing caught exceptions retain logged-None; uncaught parser errors retain their types and propagate with retained attempt evidence |
| Atomic replacement could bypass the previous output inode's write denial | Require a nontruncating write-open of an existing target, in addition to preserving its mode and resolved symlink destination |
| A failed redundant export could incorrectly revoke a still-valid old generation | Older matching successful proof remains valid; failure itself cannot create proof or label mismatched rows current |
| Climate rebuild cleanup would remove failed attempts stored below `climate/` | Use `climate_artifacts/cli_parquet/attempts/` and extend the canonical skeleton allowlist; preserve existing build cleanup behavior |

The revised schema is additive and does not change columns, formulas, peak
intensity calculations, duration interpretation or calendar ordering. A separate
mutable sidecar would weaken generation association; embedding the proof in the
same atomic candidate is the smaller correct design.

## Independently retained current-boundary evidence

`cli_lineage_correctness_boundaries.py/.json/.log` invokes the actual Climate
exporter, ClimateFile and pandas/PyArrow stack on a disposable project under UID
1000. It confirms:

- Empty CLI raises `IndexError`; an invalid column header raises `AssertionError`.
  Both leave prior Parquet bytes intact. These are real preexisting boundaries,
  not assumptions that every invalid input returns None.
- A 0444 canonical output with a writable parent returns None and logs
  `PermissionError`, preserving the previous bytes. The actual failure occurs at
  pandas' nonpermitted open before the PyArrow writer is constructed. New atomic
  publication must retain denial while keeping the prior output intact.

The security discovery's ten actual producer cases and two candidate cases are
also reviewed: parsed precipitation 4 mm can be published while the current
selection/bytes represent 8 mm; failed native writing can remove the old output;
an opened candidate handle retains partial backend work; one opened Parquet
descriptor preserves the rows/proof association during atomic path replacement.
Those cases justify this change but are not implementation acceptance.

## Compatibility and implementation checks

Proofless legacy rows remain usable for reports, calendar lookup, archive and
downloads. New post-fire execution becomes unready until an ordinary successful
export establishes producer lineage. That is an explicit intended behavior
change, justified because present-day source/output hashes cannot prove how
legacy rows were produced. Polling does not migrate, regenerate or fabricate
proof. Existing accepted post-fire result validation remains independent; adding
new receipt fields to its source snapshot comparison would require separate
compatibility handling and is not authorized implicitly by this checkpoint.

For the owner producer, verify a concurrent durable `cli_fn` change through a
different owner instance, not only a mutation of the object passed to export.
For interchange, verify an earlier-sorted CLI appearing during snapshot parsing
and a captured hint disappearing. Both producers must preserve current source
selection precedence and their existing failure/return contracts.

Use an already-open candidate handle so backend failure cleanup cannot unlink
the prior canonical path or erase retained partial work. Keep source snapshots
private from creation; post-write chmod is insufficient. Output target selection
and write authorization need final rechecks. The atomic replace is the commit:
later notification/status failure logs the issue and returns the committed
outcome rather than claiming no export happened or deleting a concurrent result.

Implementation must demonstrate actual breakpoint/non-breakpoint parser output,
nullable types, peak intensity aliases, duration, calendar indices and downstream
generated model artifacts. Include snapshot parse-time change/restore, durable
selection drift, source growth/truncation/read denial, valid/malformed footer
bounds, concurrent publications, old opened generation, source/output links,
0444/0640 modes, and prior-output retention. The new artifact root must survive
actual ordinary cleanup, skeletonize and canonical archive/restore, and remain
available through existing authorized artifact browse/download.

## Remaining gates and limits

The measured budget is now ratified below. Final implementation measurements
must include footer reads and active CLI verification in `content=False` calls,
normal admission/eviction behavior, and realistic long/breakpoint records.
Settled readiness may read bounded metadata, but performs no producer work or
full content rereads beyond the existing digest admission contract. No new cache
policy is justified by this review.

Cross-filesystem output links, managed NoDir layouts and real runtime identities
remain implementation/runtime acceptance risks. Explicit EXDEV failure preserving
the prior file is the intended bounded behavior; no alternate staging topology
is authorized. The contract correctly limits rollback to artifacts present at
the export entrypoint, not earlier climate-build cleanup. It also makes no
transactional guarantee against arbitrary source changes after the last check.
This review approves neither deployment nor full work-package closure.

## Final measured-budget review

Reviewed `benchmark_cli_lineage.py`, `cli_lineage_performance.json` and its log,
then the appended canonical/decision budget. Actual copied 46-year/1,177,082-byte
and 120-year/3,112,776-byte CLI records exercise both existing producers. Rows
and Arrow types agree between producers and with the annotated compositions;
named source generations/bytes remain unchanged. The prototype is explicitly
separate from the production implementation and its final proof schema.

For 100 settled readiness calls per record, metadata plus active-source digest
checks average 1.441/1.253 ms with zero CLI payload reads and 65,536 Parquet bytes
per call. Cold checks measure 5.696/12.009 ms; admission measures 14.300/22.684 ms.
The 5 ms settled and 40 ms cold/evicted mean budgets are defensible local
acceptance targets. Actual post-eviction execution remains an implementation
gate: this prototype clears caches and exercises admission, but does not itself
run 512 competing paths. Existing whole-project owner/raster/state checks remain
outside this component budget and retain their separate acceptance gate.

The complete composed 120-year snapshot/parse/export/metadata/publication path
averages 0.9112 seconds against the actual prior producer's 0.8103 seconds
(100.9 ms added). The 1.5-second total and 200-ms additional budgets leave
measurable headroom for final owner/authorization/status checks. Implementation
must repeat the actual complete path; the prototype does not stand in for it.
The measurements use warmed OS caches on disposable copies under UID 1000/GID
993. They establish neither physical cold-storage/NFS latency nor live route
acceptance. With those explicit limits, the checkpoint budget gate is satisfied.
