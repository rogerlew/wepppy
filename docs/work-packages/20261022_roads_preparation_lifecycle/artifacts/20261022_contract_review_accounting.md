# Independent Roads lifecycle correctness contract review

## Verdict and scope

**APPROVED for the standalone contract checkpoint.** No unresolved high or
medium correctness finding remains. This approves implementation of the bounded
lifecycle, not runtime correctness, generated outputs or deployment.

Reviewer: independent `accounting_contract_review` agent, 2026-10-22.
Starting runtime revision: `c3ac573e3123ab4680b9e0130918043809331eb0`.
Runtime files and canonical contracts were read only. This artifact is the
reviewer's only edit in this package.

Reviewed the [canonical lifecycle](../../../schemas/roads-preparation-lifecycle-contract.md),
[decision](20261022_contract_decision.md), package, active ExecPlan and applicable
output-scope, water-accounting, segment-summary and Roads specifications. Inspected
the controller mutation/preparation/run paths, current profile manifest handling,
report regeneration, query source resolution, deferred downloads, RQ locking and
the existing filesystem-lock precedent.

## Findings and disposition

| Finding | Severity | Contract disposition |
| --- | --- | --- |
| RQ-only locking leaves direct controller mutations and late publication unprotected. | High | A persistent project-root flock covers all direct and queued writers through publication. Readers share the same lock through actual consumption. |
| Clearing NoDb or discovery cannot stop direct reads, cached query plans, parent-source reads or deferred HTTP streaming. | High | Admission covers logical and resolved physical sources, actual query execution, streaming and external Roads report caches. A current logical source cannot resolve into history. |
| Retaining output without prepared context loses the meaning of reused local segment IDs. | Medium | History retains corresponding geometry, preparation summary, original manifest, accounting ledger and run inputs, with source-relative layout. Failed partial outputs remain diagnostic evidence. |
| A segment_id-keyed dictionary collapses valid multiple profiles and rejects valid synthetic remainders if used as a publication oracle. | Medium | Validate original manifest rows by unique segment_run_id; repeated parents and synthetic replacement remainders are explicitly valid. |
| A readiness list supplied by the receipt could certify itself with an empty or shortened resource set. | Medium | Receipt fields and types are explicit; admission independently requires the mode-specific mandatory set and applicable accounting/channel-water resources. |
| Restore can expose a receipt before completion or replace the lock inode while it is held. | High | Hold the writer guard throughout restore, preserve its inode, validate the complete restored set and revoke any extracted receipt on failure. |
| Failed-work wording conflicted with a retention rejection before any accepted invalidation. | Medium | Rejected preflight or retention leaves an untouched coherent prior set eligible; after invalidation, every failure remains non-current. No readiness rollback after partial mutation. |
| Producer validation could contend with its own exclusive lock or require a receipt that it has not yet published. | Clarification | Trusted producer readback uses the already-held exclusive operation guard; it does not admit external readers or publish readiness. |

The corrected ledger path is `wepp/roads/segments/roads.accounting.json`.
The external cache inventory explicitly covers the Roads hillslope summary,
metadata sidecar and attempts tree under `wepp/reports/cache`; baseline siblings
remain independent. Earlier historical parsing rules do not override current
admission under the amended water-accounting and output-scope contracts.

## Design assessment

The receipt is a completion boundary, not an identity system. With invalidation
before accepted source writes and one writer guard spanning the full operation,
local segment IDs can safely be reused without preparation versions, lineage
matching or source-name inference. Only the fresh full producer writes readiness,
after generated readback and completed-state persistence. Postprocessing cannot
upgrade old beta outputs.

Prepared geometry and lifecycle logs remain usable before a successful run.
Segment detail withholds execution enrichment while results are unavailable.
Explicit historical browsing remains diagnostic access; current reports cannot
fall back to historical files or baseline results. Continuous runs require the
typed segment summary, including valid empty summaries. Single-storm resource
requirements remain distinct.

Retention is required before destructive workspace replacement. Once current
output moves, any later error leaves the project non-current and retains partial
history. A rejection before that accepted transition may leave the unchanged prior
set current. This distinction preserves a useful failure contract without adding
a rollback or multi-file transaction mechanism.

## Required implementation evidence

These are acceptance obligations, not completed runtime checks:

- Exercise the actual full producer: successful run, prepare again with reused
  IDs, every current reader unavailable, fresh run, new results only. Preserve
  baseline hashes and inspect generated report values on isolated UM1.
- Cover multiple profiles per segment, synthetic remainders, valid empty
  diagnostics, single storm, absent Roads state, legacy files and malformed or
  incomplete receipts. Fabricated receipts are parser tests, not producer proof.
- Exercise direct setters/upload/preparation against queued execution, separate
  process contention, nested producer calls, late completion, failure before and
  after invalidation, failed publication and retry. No failure may promote old
  files or delete useful diagnostic evidence.
- Use stale catalogs and already-built query plans, physical/parent aliases,
  external report caches and deferred binary/CSV reads. Hold admission until
  materialization or stream completion and release it after errors/disconnects.
- Verify actual HTTP 409 codes and no-store after ordinary authorization; do not
  let existing broad report catches convert rejection into an empty success.
  Check initiating-client cache clearing and suppression of older responses.
- Exercise ordinary authorized historical browse/download and archive/restore,
  including interruption after receipt extraction, preserved lock inode,
  legacy archives and coherent successful restoration. Verify retained bytes,
  effective access restrictions and service identities on the real mount.

## Residual risks and limits

The existing flock precedent establishes an available mechanism, not proof of
cross-service locking on every deployed mount. Production-equivalent identity,
mount and stream-lifetime tests remain necessary. A broad consumer inventory is
the main regression risk; wrapper-only tests cannot establish closure.

This review does not certify numerical hydrology, cross-session live UI updates,
writers outside the guarded lifecycle or production rollout. Those limits do not
justify adding stable IDs, a generation subsystem or a new service. Commit this
review with the canonical checkpoint before runtime edits; substantive contract
changes require renewed independent review.

## Reviewed fingerprints

| Document | SHA-256 |
| --- | --- |
| roads-preparation-lifecycle-contract.md | `8d1ff31251de6b8223bf0e7f549cbaefb330a65e698c64017ec780e682494e67` |
| output-scope-contract.md | `e21662e174c2038831500a85967e6c5f0f198d726305a6a607da0a642bcfb575` |
| roads-water-accounting-contract.md | `29d849a2461c91e5df6ebfbe6a735681b6d245b8cc8f18fcc62758d099f791d1` |
| roads-segment-loss-summary-contract.md | `edf90ac20d033dc77ddaf79f32d206bee048778d5c88f2514d3b132cb5cddbd6` |
| Roads specification.md | `d5abd4e7e9e808ab22e716abde292536956c8dad4e116e4177a09e0e3f3cca2d` |
| 20261022_contract_decision.md | `76b88ee8f3140fd3b9fc8e7b36f3e660452c91a49ed7c5cc9e3a8dfff5e0e7c0` |
| repair_execplan.md | `79c44df7e96c08fc38a6c0816cf7502ec369306d4e23588cf5c57fd27fd4367a` |
