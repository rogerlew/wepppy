# Independent scope and governance review: per-run culvert pruning

Reviewer: governance control agent, independent of contract author.  
Date: 2026-11-16 UTC.  
Disposition: **approve amended contract checkpoint**, subject to required commit
authority and standalone ancestor sequencing. Initial medium findings are closed
by the re-review below.
This is a contract checkpoint review, not implementation or deployment approval.

## Reviewed authority and evidence

Reviewed `docs/schemas/culvert-stream-selection-contract.md`, ADR-0144,
`artifacts/20261116_contract_decision.md`, integration specification transition,
retained outlet-fidelity findings, and the contract-first, parameterization ADR,
artifact-observability, and NoDb persistence standards.

The operator expressly requested per-run selection, starting at four passes for
nominal 1 m and descending through three/two/one/zero when culverts are missed,
with corresponding schemes at 2/4/8/10 m and a performance-first bias. This is
sufficient authority to prepare and implement the bounded selection change once
the required contract checkpoint is committed. The proposed 4/3/2/1/1 mapping
and 1.5/3/6 m effective-resolution boundaries are reasonable bounded implementation
choices under that direction; do not ask for redundant approval of the general
approach. Record their heuristic, Santee-based status, as the draft does.

The prior experiment supports the selected mechanism: four passes improves1040's
counts but loses seven other outlets; three retains all39. It does not establish
universal calibration or prove that the 4 m TOPAZ failure is resolved. The draft
correctly retains those limits and excludes DEM coarsening, stream re-extraction,
new snapping, queue wiring, auth, identities, and unrelated projects.

## Medium findings requiring contract amendments

### G1: New artifact visibility and archive lifecycle are unspecified

The draft introduces versioned batch manifests, per-run receipts and immutable
candidate raster/junction files, but does not define their normal visible paths,
failed/partial states, retention, or archive/restore behavior. Publishing a receipt
only after success is sound for a completed receipt, but does not satisfy retention
of the failed attempt and diagnostics by itself.

`docs/standards/artifact-observability-standard.md` requires a concrete inventory,
existing layout/browser precedent, useful failure evidence and regression coverage
for actual archive member paths and byte-preserving restore. The checkpoint's
valid-state inventory must also name working, failed, completed, and restored
artifact states. This is not a reason to invent a new UI or archive workflow.

Required correction: specify visible batch/run paths using the existing culvert
layout, distinguish completed selection receipt from inspectable failed attempt
records, retain partial artifacts with explicit status, and add normal browser,
download and canonical archive/restore regression obligations to the checkpoint.
All artifacts remain under existing culvert authorization; credentials are excluded.

### G2: Missing-manifest compatibility can conceal new-policy failure

The draft says that existing batches without a manifest use legacy behavior,
while partial generation must fail explicitly. Manifest absence alone cannot
distinguish an actual legacy batch from a newly admitted batch whose generation
failed before manifest publication or whose manifest is later missing.

Required correction: define a durable new-policy intent/version before generation
and distinguish never-opted-in legacy state from new-policy incomplete/corrupt
state. Use existing batch metadata/NoDb persistence conventions, not a new service.
A missing/malformed manifest after recorded new-policy intent must be explicit
incomplete preparation or integrity failure and must not silently downgrade to
legacy selection. Archive/restore must retain the discriminator. Include failure
injection before manifest publication and missing-manifest resume coverage.

## Authority, security, and implementation gate

No high security, stakeholder legitimacy, ethics, or legal issue is identified in
the bounded internal selection change. This review requires no break-glass action
and grants no new identity, privilege, token scope, service, or deployment authority.
Existing forest replay authority remains environment-specific; production rollout
is not inferred from this review.

The fixed/explicit count becoming a starting maximum and zero selecting original
streams are visible compatibility changes, and the draft appropriately records
them. Retained legacy batches must not have scientific outputs rewritten when
opened or resumed. Record selected pass and rejected-candidate reasons so operators
can understand which parameterization actually reached the generated model inputs.

Commit authority has not been granted for this new checkpoint. Follow the standard:
finish the two read-only reviews, disposition findings, prepare a concrete narrow
standalone documentation commit, then request the required commit authority.
Do not include unrelated dirty files or prior experimental implementation patches
in that checkpoint. No new per-run implementation edits before its ancestor commit.

## Follow-up review obligations

Obtain post-amendment confirmation for G1/G2. Implementation review must verify
real raster selection, visibility/restore, deterministic resume, invalid-state
failure, and new-policy versus legacy separation. Forest RQ acceptance must
include both a retained four-pass outlet and a smaller fallback case, with parsed
consumed/generated topology. Until those gates pass, describe the change as
implemented or tested only to the extent the evidence supports.

## Post-amendment re-review

Re-read the amended canonical contract and checkpoint on 2026-11-16 UTC.

- **G1 closed.** The contract now names visible policy/manifest/candidate/receipt
  paths, preparing/ready/failed or selected/failed states, atomic JSON publication,
  ready-set immutability, browse/download access, and archive/restore obligations.
  It explicitly refuses to call standalone run archives self-contained without
  their referenced topology. These are test obligations, not claims already met.
- **G2 closed.** The admission-time `stream_selection_policy.json` marker records
  new-policy intent before preparation or child enqueue, independently of the
  completed candidate manifest. A marker with absent/not-ready manifest is an
  explicit incomplete state, never legacy. The narrow internal marker write is
  now enumerated in the source scope without changing client/API/auth contracts.

The amended direction fits the operator's implementation authorization. The
new marker is a necessary bounded compatibility mechanism, not authority to
redesign route admission or enqueue dependencies. Existing auth, client payload,
response, and service identities remain unchanged.

One consistency case should be covered while implementing the specified integrity
checks: a new-policy manifest/receipt with a missing or malformed policy marker
must be treated as inconsistent new-policy artifacts, not a valid legacy batch.
This follows the contract's no-silent-topology-change and identity-verification
requirements; add it to the negative-state tests. Genuine legacy means no
new-policy evidence, not merely a failed lookup of one file.

No remaining medium/high governance finding blocks preparation of the narrow
checkpoint commit. Commit authority and the second independent review remain
required; this approval does not authorize production deployment or waive real
artifact, visibility/restore, and forest RQ acceptance gates.
