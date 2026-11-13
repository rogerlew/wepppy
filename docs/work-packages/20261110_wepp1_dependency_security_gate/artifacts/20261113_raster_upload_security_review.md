# Security review - raster upload format and driver boundary

## Metadata

- **Package:** `docs/work-packages/20261110_wepp1_dependency_security_gate/`
- **Reviewer:** independent Codex security reviewer
  `/root/raster_contract_security_review`
- **Date:** 2026-11-13
- **Scope reviewed:** `F6-RU-01`; DEM, SBS, landuse, treatments, Ash, and Omni
  upload/consume boundaries; persisted reuse and request failure atomicity
- **Starting revision:** `419fa0b320d83456cbbd6fc7ad3b6119108da015`
- **Related artifacts:**
  `artifacts/20261113_raster_upload_contract_decision.md` and
  `artifacts/20261113_raster_upload_correctness_review.md`

## Security triage decision

- **Security impact:** high
- **Dedicated review required:** yes
- **Rationale:** authenticated users control bytes passed to native GDAL parsers.
- **Assumptions:** existing authentication/run authorization remains unchanged;
  multipart size limits remain enforced; accepted GTiff/HFA parsers remain
  native residual attack surface; run-root locks remain authoritative.
- **Valid states:** self-contained GTiff/HFA, absent optional upload with one
  authoritative reusable file, rejected malformed/mismatched/escaped/legacy
  state, and unchanged generated/internal plus dNBR VRT workflows.

## Findings

| ID | Severity | Surface | Required action and disposition | Status |
| --- | --- | --- | --- | --- |
| F6-RU-S1 | High | Operator authority | Correct false active records and explicitly supersede the earlier agent interpretation | Resolved |
| F6-RU-S2 | High | Native parser chain | Restricted decode, identity receipts, complete companion rejection, and restricted touched opens preserve the validated snapshot | Resolved |
| F6-RU-S3 | Medium | Persisted/Omni reuse | Server-derived run-owned candidates are trusted-root-contained and reasserted under the Omni lock | Resolved |
| F6-RU-S4 | Medium | Multi-file requests | Every new/persisted request raster is prevalidated before publication or controller mutation | Resolved |
| F6-RU-S5 | Medium | Review governance | Dedicated checkpoint and iterative post-fix security re-reviews are retained | Resolved |

## Surface checks

- Auth/JWT/CSRF, secrets, queue topology, Redis contracts, subprocesses, network
  integrations, dependencies, and CI permissions are unchanged.
- File validation must reject path escape, symlinks, sidecar dependency, driver
  mismatch, malformed/truncated content, and general VRT before publication.
- Request scratch must be private and cleaned on all exits. Existing accepted
  destinations and controller state must survive any format failure.
- No new broad exception handler or silent validation fallback is authorized.
- Direct real-driver tests, request-wide failure tests, path-containment tests,
  broad-exception enforcement, full Python/frontend gates, and
  production-equivalent identity/mount workflow evidence are release gates.

## Verdict

- **Checkpoint gate:** pass after post-fix security confirmation
- **Implementation gate:** pass at `cb839e7d7` after independent security
  re-review
- **Release recommendation:** production-equivalent deployment evidence and the
  separate time-bounded native advisory disposition remain required
- **Unresolved design findings:** High 0; Medium 0; Low 0

## Residual risk

Accepted GTiff/HFA parsers still process attacker-controlled content, and bounded
uploads may still consume significant CPU/memory during decode. `F6-RU-01` is
input containment, not proof that the pinned GDAL stack is vulnerability-free
and not the time-bounded advisory exception required for M4. Any later exception
must separately bind advisory aliases, exact image/install identities, approver,
expiry, review triggers, and compensating-control evidence.

No new artifact class is created. Existing project authorization, run artifact
visibility, archive/restore membership, and recovery mechanics remain applicable;
implementation tests must retain visible failing-boundary evidence without
publishing hostile inputs into accepted run state.

## Implementation re-review

The security reviewer reproduced and rejected intermediate sidecar bypasses at
the accepted destination and cloned Omni target. The approved implementation
uses the repository-authoritative case-insensitive GDAL companion inventory for
upload publication, persisted reuse, identity assertion, async Omni copy, and
final admission. Real external-mask, HFA spill, trusted-root, identity-race, and
late-request regressions pass in the 239-test focused receipt. No implementation
security blocker remains for `F6-RU-01`.
