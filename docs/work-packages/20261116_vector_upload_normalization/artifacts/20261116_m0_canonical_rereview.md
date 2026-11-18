# M0 canonical contract re-review

Date: 2026-11-16  
Reviewer: independent `m0_canonical_rereview` correctness reviewer  
Starting implementation revision: `05e3450fa7d3b24572e65161100670ae542a6ea8`  
Verdict: **HOLD pending the known raw-binary operator decision**

## Scope reviewed

This is the second read-only contract review required by the contract-first
standard. It reviewed the amended canonical normalization contract, upload
endpoint contract, shape-converter specification, accepted ADR-0145, dependency
precedent entry, VUN-01 contract decision, source/state/threat matrices, fixture
receipt, and independent correctness, QA, operations and Daybreak security
reviews. No runtime implementation or production dependency was reviewed or
approved.

## Findings

| ID | Severity | Finding | Required disposition | Status |
| --- | --- | --- | --- | --- |
| VUN-CAN-M0-01 | Medium | The shape-converter specification said the exact graph was bound to a lock hash recorded only in the active dependency-evaluation artifact. The contract-first standard permits work packages as historical evidence, but canonical behavior cannot depend on a mutable/closed package. | Put the exact accepted lock SHA-256 `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13` directly in the canonical shape-converter specification and make graph/version/feature/hash changes reopen review. | Resolved by canonical direct binding; focused re-review passed |
| VUN-CAN-M0-02 | Medium | The normalization contract deletes original binary uploads after request cleanup. The artifact-observability standard requires explicit operator approval for this exact departure because project archives cannot reproduce the original submitted input. | Record whether raw Shapefile ZIP/GeoParquet bytes are deleted or retained. If deletion is approved, name the exact departed artifact class and preserve the already-specified source hash/size, parser provenance, stable diagnostics, accepted canonical GeoJSON, and rejected normalized candidate. | Open; known operator decision |

No other High or Medium contract finding remains. In particular:

- ADR-0145 and both canonical specifications now make the owned bounded
  same-open-descriptor preflight normative before every upstream Parquet decoder;
  they explicitly reject direct `SerializedFileReader` use on unpreflighted data.
- The exact package/version/feature selection, receiving extension matrix,
  endpoint byte caps, stable error translation, no-fallback behavior and M2
  exact-image gates agree.
- Roads remains line-only. AgFields and Omni explicitly require polygonal input.
  Batch applies Polygon/MultiPolygon admission to new uploads without tightening
  saved-project reload or migrating existing projects.
- Missing GeoParquet CRS means CRS84, explicit null is rejected, projected CRS
  transformation is offline and rejects ballpark/missing-best-grid fallback, and
  normalized binary content reaches receiving validation with authoritative WGS84
  context.
- Failed replacement is ordered before accepted resource/state mutation.
  Normalized candidates rejected by receiving validation remain visible and
  archivable; direct GeoJSON behavior, authentication, CSRF, scope, locks, byte
  policies, response envelopes and queue topology remain preserved.

## Evidence and residual gates

The 46-file corpus and allocation probes support contract design but do not prove
the future implementation. M1 must assert the enforcement stage and stable error
for each hostile class, including exact-edge and limit-plus-one cases. M2 must
prove the accepted aggregate envelope, same-descriptor implementation,
cancellation/process drainage, cleanup, readiness, provenance, SBOM/advisory
state and recovery in the exact image. M3/M4 must prove receiving-boundary bypass
resistance and failed-replacement safety. M5 must perform semantic artifact
readback through reload and the next actual downstream artifact for all formats.

Focused re-review confirmed that the canonical shape-converter specification now
names the exact accepted lock SHA-256 and requires a new dependency review for
any graph, feature, version or lock-hash change. VUN-CAN-M0-01 is closed.
VUN-CAN-M0-02 cannot be inferred from security preference or the implementation
plan; it needs the operator's explicit retention disposition before the standalone
checkpoint commit. No other High or Medium contract finding remains. No
implementation ancestor is approved while VUN-CAN-M0-02 is open.

## Operator disposition and final M0 addendum

The operator subsequently required retention of complete within-limit originals,
source SHA-256 provenance and quarantined failed/hostile files for review. The
canonical contract now specifies private neutral-suffix storage, explicit owner/
root or Batch group authorization, download-only handling, bounded atomic project
and filesystem admission, recoverable receipts and no automatic ban. Independent
focused retention correctness and security re-reviews report no unresolved High
or Medium finding. VUN-CAN-M0-02 is therefore closed and this canonical checkpoint
is ratified for the standalone implementation ancestor; runtime and exact-image
conformance remain later gates.
