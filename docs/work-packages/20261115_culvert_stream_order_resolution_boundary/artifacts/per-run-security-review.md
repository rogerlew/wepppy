# Security Review - Per-run culvert stream selection

## Metadata

- **Package**: `docs/work-packages/20261115_culvert_stream_order_resolution_boundary/`
- **Reviewer**: independent implementation/security reviewer agent
- **Date**: 2026-11-16
- **Scope reviewed**: culvert upload admission, candidate/receipt generation and
  consumption, artifact resolution, skeleton retention/export, and worker locks.
- **Commit context**: implementation `4266e740a`; security correction `d0732a4d2`;
  accepted contract ancestor `61645e8a1`.
- **Related artifacts**: `per-run-implementation-review.md`,
  `per-run-security-path-probes.json`, `per-run-review-artifact-readback.json`,
  `per-run-live-reserved-receipt-rejection.json`, `per-run-validation.md`.

## Security Triage Decision

- **Security impact level**: high, by the work-package default classification.
- **Dedicated security review required**: yes.
- **Triage rationale**: the final scope changes public upload admission and
  server-owned artifact/path handling; the earlier numeric-only triage is obsolete.
- **Threat model assumptions**: authorized submitters can supply hostile ZIP
  members and metadata. ZIP contents remain untrusted. Workers and their server
  filesystem identity are trusted; arbitrary compromise of that identity is
  outside this change. Existing batch authorization remains mandatory.
- **Valid states preserved**: a valid new upload without internal artifacts;
  legacy batches without new-policy evidence; populated ready candidates;
  zero-pass selection; recoverable preparation without receipts; explicit failed
  selections; and deterministic resume of valid receipts. Missing or incomplete
  manifests with receipts, altered identities, escaped paths, and caller-owned
  selection state are invalid states, not supported legacy states.

## Findings

| ID | Severity | Surface | Description and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Uploaded base receipt | The initial guard rejected run receipts but allowed `_base/stream_selection.json`. `_ensure_base_project` reuses an existing base and `create_run_if_missing` copies it into a run, allowing supplied receipt state to reach the trusted resume branch. | Reject the base receipt before enqueue and cover the real extraction/admission boundary. | Resolved by `d0732a4d2`; route regression and actual forest HTTP 400 evidence retained. |

No risk acceptance is requested. No unresolved high, medium, or low security
finding remains in the reviewed delta.

## Verdict

- **Code security gate**: pass.
- **Unresolved findings**: high 0; medium 0; low 0.
- **Release recommendation**: code security and completed archive integrity pass.
  Both runs and the finalizer finished successfully. Authenticated manifest/receipt
  and whole-archive downloads passed. All security and artifact-observability
  checks in this review are closed. This is not production deployment approval.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] The state inventory above and implementation review distinguish valid,
  legacy, incomplete, failed, and hostile states.
- [x] Valid admission and reserved-artifact rejection exercise real extraction
  and payload validation. Existing user errors remain canonical HTTP 400 responses;
  missing optional policy on a genuine legacy batch remains valid.
- [x] Security approval does not replace correctness or runtime acceptance.

### 1) Auth, Session, and Authorization

- [x] Admission still requires JWT scope `culvert:batch:submit` and feature access
  before staging. No token mint/verify, role, session, CSRF, or browse authorization
  behavior changed. Tests cover missing authentication and missing scope.

### 2) Secrets and Credential Handling

- [x] No new secrets or secret dependencies. Receipts, manifests, and logs retain
  paths, hashes, point coordinates, passes, and reasons within normal project
  authorization; no credentials are added to them or subprocess arguments.

### 3) Input Validation and Output Safety

- [x] Existing ZIP member normalization rejects traversal, duplicates, symlinks,
  special files, nested archives, unsupported compression, and quota abuse.
  Metadata paths remain constrained to canonical payload members.
- [x] Reserved marker, manifest, candidate directory, run receipts, and base
  receipt are rejected before internal intent is written or jobs are enqueued.
- [x] JSON uses ordinary parsing rather than executable deserialization. No new
  shell interpolation, rendered markup, or URL-fetch surface was introduced.

### 4) File System and Run-Tree Boundaries

- [x] Candidate/receipt writes stay within the existing batch/run roots. The
  resolver rejects absolute paths, parent traversal, and symlinks resolving out
  of the batch; the same resolver protects new archive members.
- [x] Direct filesystem probes confirmed valid in-root access, explicit missing
  file errors, hash mismatch rejection, mode `0600` JSON creation, and cleanup
  after a failed atomic write while preserving the previous JSON.
- [x] Existing archive run-tree walking is unchanged. New manifest inputs and
  candidates are checked for containment and identity before archive inclusion.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No enqueue/dependency edges or cancellation authorization changed; no new
  queue graph gate is triggered. WBT receives server-resolved raster paths through
  its existing API. Preparation failures propagate with bounded failure metadata.

### 6) Agentic Tooling and MCP Surfaces

- [x] No production agent/MCP capability, credential scope, or tool execution
  permission changed. Reviewer actions were read-only inspection, isolated probes,
  scoped tests, and retained review artifacts; production source was not edited
  by this reviewer.

### 7) Network and External Integrations

- [x] No new endpoint, egress integration, or dependency. Existing upload quotas
  and authenticated submission limits remain. High-cost hydrology work remains
  behind the existing feature/scope boundary.

### 8) CI/CD and Supply Chain

- [x] No workflow permissions, deployment topology, third-party dependency, or
  self-hosted runner access changed. Existing owned WBT/raster tooling is reused.

### 9) Data Integrity, Locking, and Concurrency

- [x] Batch topology/candidate publication and per-run receipt selection have
  filesystem locks; JSON publication is atomic. Ready retries verify inputs and
  do not rewrite shared topology. Incomplete states with receipts reject before
  mutation. NoDb mutations retain existing lock boundaries and Redis contracts.
- [x] Helper-level retry and failed-write regressions/probes are retained.
  Process-level lock contention and crash injection remain coverage limits,
  without a known remaining race in the changed path.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Selection logs contain starting/selected passes and rejection reasons.
  Failed preparation is explicit; integrity errors do not become finer-network
  fallbacks. Contract/ExecPlan recovery preserves ready topology and distinguishes
  incomplete new preparation from legacy absence.

## Validation Evidence

- Reviewer execution: `wctl run-pytest tests/microservices/test_rq_engine_culverts.py
  -k 'ingest_success or requires_auth or missing_scope or caller_selection_artifacts
  or invalid_zip_member_path' -q`: **9 passed**, 21 deselected.
- Parent execution: all **30 admission route tests passed** after SEC-01; prior
  focused selection/culvert gates and real WBT parity are recorded separately.
- Direct unmocked containment/atomic-write probes inside the Compose weppcloud
  service: all expected results passed; `per-run-security-path-probes.json`.
- Actual forest HTTP request with a valid two-point raster payload plus a supplied
  base receipt: **400**, canonical `validation_error` / `reserved_artifact`, no
  job response; `per-run-live-reserved-receipt-rejection.json`.
- Independent candidate hashes, consumed VRT windows and outlet intersections:
  `per-run-review-artifact-readback.json`.
- Parent-retained authenticated manifest and both receipt downloads: HTTP 200
  with byte-hash equality; `per-run-authenticated-downloads.json`, inspected by
  this reviewer. The existing service principal was used without a human account.
- Independent completed archive readback: all 20 required dependency/provenance/
  receipt/run-metadata members present with matching SHA-256 values; both receipt
  links match the manifest. All 204 member names are unique and contained;
  `per-run-review-archive-readback.json`.
- Authenticated complete-archive download: HTTP 200, 845,228,899 bytes, SHA-256
  `717fbd022453682b13e073dc5b68b6467bcd03739e120bd4503c907055410e5d`,
  matching the server artifact; `per-run-authenticated-archive.json` inspected.

## Residual Risk

No exceptional security-risk acceptance is requested. The implementation assumes
the established trusted worker identity owns the batch tree; hashes and path
checks are integrity controls, not a defense against that identity being
compromised. Native raster parsing and resource-intensive authorized submissions
remain existing surfaces. Process-level contention/crash injection and complete
restored-project execution are not established by this review.

## Sign-off

- **Security reviewer**: independent implementation/security reviewer agent,
  2026-11-16; code findings closed through `d0732a4d2`.
- **Package owner**: parent implementation agent supplied final successful-job
  and authenticated-download evidence on 2026-11-16 and retains package closeout
  responsibility; no finding waiver.

## Artifact Observability Gate

- [x] Comparable surface: existing culvert batch manifests, run metadata and
  skeleton ZIP. Canonical new inventory: policy marker, candidate manifest,
  candidate inputs/rasters/junctions and per-run selection receipts.
- [x] Real writers and archive/restore tests retain selection metadata and verify
  artifact identities. Failed preparation/selection remains explicit.
- [x] Authenticated live manifest/receipt downloads return HTTP 200 and bytes
  matching the canonical files; filesystem access alone is not the evidence.
- [x] Completed batch archive download and independent member readback pass;
  `per-run-authenticated-archive.json` and `per-run-review-archive-readback.json`.
- [x] No hidden-only project record or unapproved observability exclusion is
  introduced. Filesystem lock files are synchronization internals, not substitutes
  for the visible policy/manifest/receipt records.
