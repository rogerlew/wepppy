# Per-run stream selection implementation review

Reviewer: independent implementation reviewer, 2026-11-16.
Contract ancestor: `61645e8a127b02a230fb5fa2d33b0bbdc378f026`.
Implementation: `4266e740a`; admission security follow-up: `d0732a4d2`.
Scope: candidate generation/selection, CulvertsRunner integration, batch
orchestration, admission marker, skeleton retention/export, and regressions.

## Disposition

No open code finding remains in the inspected revision after the retry and
observability fixes below. Independent forest readback confirms the intended
four-pass and three-pass selections and their actual consumed stream rasters.
Both runs and the finalizer finished successfully, and the completed archive
retains every required dependency with matching hashes. Forest computation,
topology, archive integrity, and authenticated download acceptance pass. This
review does not establish production rollout readiness.

## Findings and resolution

1. **High, resolved: ready retry replaced shared topology before verification.**
   `wepppy/rq/culvert_rq.py:241` previously regenerated and unlinked the batch
   flow-pointer raster before checking the ready candidate manifest. Existing
   run VRTs reference that raster. The new topology lock and `reuse_ready`
   verification run before mutation; ready retries preserve topology, and
   receipt-bearing missing/incomplete manifests reject before reconstruction.
   `test_ready_retry_preserves_inputs_and_candidates` and
   `test_incomplete_receipt_state_cannot_rebuild_shared_topology` retain helper
   regressions in `tests/culverts/test_stream_selection.py`.

2. **Medium, resolved: ready candidates still depended on later legacy outputs.**
   A crash after candidate publication but before legacy root junction generation
   could leave a ready manifest whose runs failed the legacy prerequisite check.
   `wepppy/nodb/culverts_runner.py:390` now obtains new-policy prerequisites from
   the candidate manifest; `wepppy/rq/culvert_rq.py:313` limits legacy pruning and
   root junction generation to legacy batches. New candidates are therefore the
   complete stream/junction prerequisite for this path.

3. **Low, resolved: missing grid/policy metadata and selection logging.**
   The manifest now serializes width, height, transform, CRS, and the named
   generation policy; `ready_manifest` verifies the serialized grid against the
   actual raster and rejects unknown policies. The runner logs starting and
   selected passes, every attempted candidate/reason, and the selected path.
   The forest batch manifest and its Point_ID2913 log confirm these fields are
   emitted by the actual workers.

## Correctness and security assessment

- New admission rejects caller-supplied policy, manifest, candidate-directory,
  and receipt artifacts before writing internal intent. Existing authorization
  and queue dependencies remain unchanged. Artifact resolution rejects absolute
  paths and resolved paths escaping the batch directory.
- Candidate preparation and per-run receipt publication use filesystem locks.
  JSON publication uses same-directory replace, and temporary cleanup covers
  serialization failures. Selected and examined candidates are hash checked;
  missing files/grid errors are explicit errors, not normal fallback reasons.
- Ready preparation verifies source identities and pass count. Resume checks
  point, CRS, selected manifest entry, and selected raster identities. Legacy
  batches retain their prior map thresholds and polygon-only selection path;
  inconsistent new-policy evidence cannot masquerade as legacy.
- Skeletonization retains receipts. The batch ZIP includes policy, manifest,
  manifest inputs, candidate streams/junctions, and run receipts. The restore test
  checks ready input resolution and recorded selection identity. Documentation
  correctly limits this to a skeleton export, without claiming a fully executable
  standalone restored project.

## Coverage and residual risk

Reviewed real WBT regressions cover multi-level fallback, a point miss despite
polygon coverage, terminal failure, zero override, absent watershed coverage,
selected-artifact loss/change, ready retry identity preservation, inconsistent
intent, and archive/restore. Reviewed API regressions cover reserved-artifact
admission. Test execution and broader-suite results are owned by the parent
implementation run; this reviewer did not duplicate those suite executions.

The additional `test_four_to_three_preserves_trunk_and_matches_wbt` fixture has
eight converging branches and an order-four trunk. It exercises four-to-three
selection and compares each of the four binary candidate masks with repeated
real WBT pruning. Parent reports 103 focused tests passed and one opt-in live test
skipped; this reviewer inspected the assertions and final source delta. The
retained broad gate reports 13,991 passed and 440 skipped. All 30 admission tests
passed after the separately reviewed security correction `d0732a4d2`.

Independent replay evidence is retained in
`per-run-review-artifact-readback.json` and `per-run-review-job-readback.json` for
batch `e4eb3edf-0bba-457f-adf0-17eeb61d85b8`:

- Point_ID1040 selects four. The supplied point is positive on all five networks;
  the consumed VRT references pass four and every consumed pixel equals the
  corresponding source window. Both selected hashes match. Its resolved outlet
  lies on a consumed stream, within 0.00353 m of the supplied point; its junction
  value is one, with no positive junction outside the consumed stream network.
  Final parquet counts are 783 hillslopes and 313 channels. The native watershed
  error file contains the WEPP successful-completion marker after 51 years.
- Point_ID2913 rejects four because its supplied point is off-stream and selects
  three. Both selected hashes match, and its consumed VRT pixels equal pass three.
  Its outlet lies on the consumed stream in the containing point cell, with
  center distance 0.46686 m. Parsed parquet counts are three hillslopes and one
  channel; per-run metadata reports success.

Both selected stream/junction hashes still match on the final processing
readback. The parent, both children, and finalizer are finished without retained
exceptions. Both per-run metadata records report success; the final batch summary
is two succeeded, zero failed, zero skipped. The large child finished at
04:07:21 UTC and the finalizer at 04:12:53 UTC on 2026-11-16.

Independent `per-run-review-archive-readback.json` records the completed
845,228,899-byte archive with 204 unique, contained member names. All 20 required
input/candidate/provenance/receipt/run-metadata members match their recorded or
persisted hashes. Both archived receipts link to the exact archived manifest
candidate. These checks supplement the real archive/restore regression; they do
not claim the skeleton is a standalone executable restored project.

`per-run-authenticated-archive.json` records HTTP 200 and byte equality for the
complete downloaded archive: SHA-256
`717fbd022453682b13e073dc5b68b6467bcd03739e120bd4503c907055410e5d`.
The reviewer inspected this evidence alongside the independent member readback.

Residual coverage gaps: process-level lock contention and crash injection around
the orchestration guard; a full new-policy CulvertsRunner resume with actual VRT
consumption; corrupted unselected candidates; and direct candidate junction parity
assertions. The new helper-level retry tests do not
by themselves prove the entire RQ caller preserves shared sources.
