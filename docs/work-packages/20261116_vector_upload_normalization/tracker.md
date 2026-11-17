# Tracker - Vector upload normalization

## Quick Status

**Timezone**: UTC  
**Last updated**: 2026-11-17
**Current phase**: M5 exact-candidate successor review
**Security impact**: high  
**Starting revision**: `05e3450fa7d3b24572e65161100670ae542a6ea8`  
**M0 contract ancestor**: `1aebebfe0`  
**Architecture**: separate bounded `geoparquet_parser_cli` sibling to the existing
`shape_parser_cli`; both normalize through shape-converter to canonical GeoJSON

## Task Board

- [x] Inventory the four first-party user-facing GeoJSON upload workflows.
- [x] Exclude the culvert API and defer D-Tale.
- [x] Record the operator-approved sibling Rust CLI architecture.
- [x] Scaffold package, active ExecPlan, review artifacts, and project tracking.
- [x] M0: verify the upload inventory and current size/geometry/error contracts.
- [x] M0: ratify the normalization, GeoParquet security, CRS, metadata, and error contracts.
- [x] M0: operator selected Polygon/MultiPolygon-only new Batch Runner uploads.
- [x] M0: author and approve the resource-limit ADR.
- [x] M0: conditionally accept the exact Rust dependency graph behind owned preflight.
- [x] M0: retain red tests and hostile fixtures for every accepted/rejected state.
- [x] M1: implement and directly test `geoparquet_parser_cli` at `eb6b0d3fb`.
- [x] M2: final3 qualification passed; readiness-bound final4
      `sha256:ec801ab0c90e…73ce03` supersedes it as the local exact candidate
      with daemon-free SBOM/scan evidence.
- [x] M3-M4: integrate all four browser/workflow upload paths without bypassing
      receiving validation; preserve originals, provenance and failed replacement.
- [ ] M5: final correctness/code/QA/security/operations successor re-reviews.
- [x] M5: prepare local validation and rollout/recovery evidence without
      publishing or deploying.

## Decisions

- **2026-11-16 23:22 UTC** - Follow the shape-converter Rust CLI pattern for
  hostile GeoParquet parsing, but use a separate `geoparquet_parser_cli` binary.
  This keeps format-specific parsers and contracts narrow.
- **2026-11-16 23:22 UTC** - Shapefile ZIP and GeoParquet normalize to canonical
  GeoJSON before the existing workflow validators. The converter is not a trust
  substitute for Roads, AgFields, Omni, or Batch Runner validation.
- **2026-11-16 23:22 UTC** - Culvert API paths are excluded and D-Tale is
  deferred. Neither may be pulled into implementation or closure claims.
- **2026-11-16 23:22 UTC** - No PyArrow hostile-input parser and no new service,
  queue, datastore, daemon, protocol, or deployment topology are authorized.

## Resolved Contract Decisions

- Binary inputs preserve each endpoint source limit and add the independent
  ADR-0145 decoded/canonical-output ceilings.
- Batch Runner geometry resolved: Polygon/MultiPolygon-only new uploads;
  implementation and regression evidence pending.
- The supported GeoParquet metadata/version/codec subset and error translation
  are ratified in the normalization contract and ADR-0145.
- Existing offline PyProj performs CRS transformation; missing best grids and
  ballpark transforms fail closed.
- Canonical GeoJSON remains the visible accepted workflow resource. Complete
  originals, SHA-256 provenance, receipts and failed canonical candidates are
  privately retained under the bounded attempt lifecycle.

## Risks and Blockers

- Binary Parquet metadata, compression, encodings, and WKB can amplify CPU,
  memory, allocation, and scratch use before logical row validation.
- Parquet external file references, encryption, Arrow extension metadata, nested
  schemas, and dataset semantics broaden authority and are rejected by default.
- CRS ambiguity can silently move geometry; explicit unknown CRS cannot be
  treated as WGS84.
- The converter and workflow limits may diverge and create valid-state failures
  unless the contract defines both boundaries together.
- The existing shape-converter hardening has local closure, but production
  rollout is still separate. This package cannot claim a deployed foundation.

## Required Evidence

- Verified source inventory and current endpoint-contract matrix.
- Ratified normalization/security contract and parameterization ADR.
- Exact dependency lock, unsafe/transitive inventory, vulnerability disposition,
  build provenance, and malformed-input evidence.
- Red/green hostile fixture matrix and valid format-equivalence fixtures.
- Exact-image resource, cancellation, cleanup, readiness, and recovery receipts.
- Per-workflow normalized payload and downstream artifact semantic readback.
- Completed correctness, code, QA, security, and operations review artifacts.

## Notes - 2026-11-16 23:22 UTC

- Package scaffolded only. No application code, dependency, image, upload
  contract, or production behavior changed.
- Next action is M0 contract-first work. Do not begin parser implementation until
  the ADR, dependency evaluation, and open contract decisions are approved.



## Execution checkpoint - 2026-11-16

Execution started. Read the active plan, integration/history governance, and
upload endpoint contract. Created task branch `codex/vector-upload-normalization`
in `/tmp/wepppy-vector-upload-normalization` at
`05e3450fa7d3b24572e65161100670ae542a6ea8`.
The package exists in the shared checkout but is absent from that committed
revision. Preserve and transfer the package before implementation; do not assume
the task worktree contains uncommitted predecessor changes.

The operator selected Polygon/MultiPolygon-only Batch Runner uploads; the
active plan records rationale and compatibility/regression coverage. M0 is incomplete;
no parser, workflow, dependency, image, or deployment change has been made.
Next: reconcile required uncommitted source context into the task worktree,
verify the source matrix, and complete M0 contracts and evidence before M1.


## Decision amendment - 2026-11-16

Polygon/MultiPolygon-only Batch Runner admission is authorized. Preserve saved
projects; reject unsupported new uploads before resource replacement. See the
active ExecPlan section "Decision amendment - Batch Runner geometry". The package
has been copied into the isolated task worktree; unrelated shared changes were
not transferred. M0 remains incomplete.


## M0 evidence update - source and dependency audit

Retained partial source verification in `artifacts/20261116_source_checkpoint.md`
and drafted `docs/schemas/vector-upload-normalization-contract.md`. The dependency
evaluation records pre-validation allocation concerns in cached parquet 53.4.1.
No dependency is accepted and M0 remains open. Next work: finish source traces,
evaluate a bounded current dependency candidate, author resource ADR and red
fixtures, then review the complete checkpoint before M1.


Validation checkpoint: direct `markdown-doc lint` from the task worktree passed
for the draft contract (1 file) and package (7 files). Installed `wctl doc-lint`
resolved the shared checkout: an absolute task path panicked and a relative draft
path reported zero files. Those wrapper runs are not candidate validation.
Parquet 60.1.0 source was acquired for evaluation; exact graph and allocation
bounds remain unapproved. No runtime change or milestone completion is claimed.

## Resumed execution evidence

Candidate documentation selection is fixed through explicit
`wctl --project-dir /tmp/wepppy-vector-upload-normalization`; draft contract lint
validated one file without errors. No wrapper implementation change is needed.
Independent correctness, dependency/security, QA and operations M0 reviews are
active. Proposed ADR-0145 and threat matrix retain numeric/resource and
observability decisions. M0 remains open; no runtime implementation has begun.

## External review blocker and retained outcome

The required dependency/security review agent was terminated by an account-
security gate requiring Daybreak Blue eligibility and approved hardware-key
sign-in. See `artifacts/20261116_security_review.md`. Do not bypass that gate or
count partial findings as approval. The operator raw-input deletion exception
is also pending. M0 is not accepted; no standalone checkpoint SHA exists.

Proposed ADR-0145, expanded canonical draft, contract decision, source/state/
threat matrices, evaluation-only lock/tree/audit, deterministic fixture corpus
and isolated candidate Compose harness are retained. Operations/source review
findings remain tracked; none is final implementation acceptance. M1–M5, exact
candidate-image qualification, downstream artifact validation and final five-lane
review have not occurred. No runtime changes, remote integration, image
publication or deployment occurred. Shared unrelated changes were preserved.

## Final retained QA and documentation evidence

QA prepared 46 deterministic fixtures totaling 34,949 bytes. Independent
correctness readback verified hashes/sizes, eight valid semantic controls, seven
metadata-negative controls and zero contradictory outcomes for identical bytes.
Manifest SHA-256: `3cb63c002cd9a5e9eda9c0210ad3f0aa679621e21177cf84a01709cc9378885f`.
Candidate execution is NOT_RUN; hostile decoding, threshold/resource, ZIP
equivalence, lifecycle and workflow acceptance remain pending. See
`artifacts/20261116_qa_checkpoint.md`. Documentation lint and ADR date validation
passed from the task checkout using explicit project selection. These checks
do not advance M0 acceptance. No accepted checkpoint commit was created.

Final fixture expectation amendment: all-null geometry now explicitly expects
CLI rejection because finite observed bounds are required. All 46 fixture byte
hashes are unchanged; regenerated manifest SHA-256 is
`30f5ea40ae35fcd41843ca29e0d75671f32fc8e5a80a024b1965709daeac7bd5`.
The earlier hash records the independently reviewed corpus before this expectation
clarification. Regeneration/readback and QA Markdown lint pass; no runtime test
is implied.

## Daybreak M0 review and canonical amendments

The resumed independent security review conditionally accepts the exact minimal
graph only behind owned same-descriptor structural preflight. Canonical ADR,
dependency, endpoint, normalization and converter documents are amended. The
second canonical re-review closed the lock-hash authority finding. Focused
retention correctness and security reviews pass after closing the explicit
authorization and shared-filesystem admission findings. No unresolved High or
Medium M0 finding remains. The standalone checkpoint commit and revision record
are `1aebebfe0`; runtime implementation may now begin.

## Original and hostile upload retention decision

The operator requires users to recover complete within-limit original files and
requires source SHA-256 provenance for conversion. Complete rejected/hostile
uploads are retained for review and possible human account-governance action.
The canonical design stores neutral-suffix private project artifacts, blocks
anonymous public-run access and every server-side interpretation, and records
minimal verified actor identity without credentials, sessions or client IP.
Explicit owner/root or existing Batch group authority bypasses public-run read
allowance. Existing-Redis atomic admission bounds all projects, principals,
unattributed use and concurrent reservations while preserving 10 GiB free space.
Oversize partial files are deleted and cannot claim a complete hash. No automatic
ban or new datastore is authorized. The final security re-review passed before
the standalone M0 commit.

## M1 and M2 execution update

M1 is complete at `eb6b0d3fb`: 30 locked/offline Rust tests, strict clippy and
format checks, the final 53-file hostile/control corpus, and independent
correctness/security review pass. M2 implementation is committed at
`0e58feced`. Exact local image
`sha256:d131f3df03a12083c138c0ebc65a4576390d90c3ad80352f62a041405b102df4`
passed readiness/provenance, valid/projected conversion, inspect, unavailable-
grid rejection, hostile-limit rejection, containment and scratch readback.
See `artifacts/20261116_m2_validation.md`. Publication and deployment did not
occur. Independent M2 review remains open while M3 source integration begins.

## M3-M5 closure candidate - 2026-11-17

M2 review passed for exact final3. Readiness-bound final4 is the current local
exact candidate. Workflow integration was committed at
`9ac7cb8f6`; the successor closure candidate adds reversible mutation, monotonic
terminal receipts, durable Redis reconciliation/rebuild, private sensitive
archives, resolved-alias protection, verified session-human provenance, bounded
converter responses/error mapping, and independent binary UI/server activation.
The expanded affected suite, exact final4 common-helper test and actual HTTP
boundary tests cover Roads, AgFields, Omni run/dry-run and Batch for GeoJSON,
Shapefile ZIP, `.parquet`, and `.geoparquet`. Final five-lane re-review is
required before M5 acceptance.
Publication, production deploy, and remote-host proof remain outside authority.
