# Implement bounded Shapefile and GeoParquet upload normalization

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current. Update this
plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, a user can upload GeoJSON, a Shapefile ZIP, or a single
GeoParquet file in Roads, AgFields, Omni contrasts, and Batch Runner. Binary
files cross one hardened shape-converter boundary and become canonical WGS84
GeoJSON before each workflow performs its existing semantic validation and
persistence. Users receive bounded, actionable errors for unsupported or hostile
files, and failed conversion leaves neither partial workflow state nor scratch
residue.

GeoParquet uses the established short-lived Rust CLI execution pattern, but in a
new format-specific `geoparquet_parser_cli` sibling. It does not become a mode of
`shape_parser_cli`. The binary runs in the existing shape-converter container
with strict data-only JSON IPC, minimal environment, offline operation, explicit
resource limits, process-group timeout/cancellation/drain, provenance, and a real
readiness canary. WEPPcloud, NoDb, rq-engine, and browsers never parse raw
GeoParquet.

## Progress

- [x] (2026-11-16 23:22 UTC) Inventory the four user-facing GeoJSON upload
      workflows; exclude culvert API paths and defer D-Tale.
- [x] (2026-11-16 23:22 UTC) Accept the sibling Rust CLI architecture and
      canonical-GeoJSON normalization direction.
- [x] (2026-11-16 23:22 UTC) Scaffold the package, tracker, dependency gate,
      correctness review, security review, and active ExecPlan.
- [x] (2026-11-16) Operator ratified Polygon/MultiPolygon-only Batch Runner uploads.
- [x] (2026-11-16, resumed) Reconcile both checkouts and correct documentation
      wrapper selection with explicit `--project-dir`.
- [x] (2026-11-16, resumed) Complete source boundary/state matrices and prepare
      isolated candidate test configuration; runtime validation remains pending.
- [x] (2026-11-16, Daybreak resumed) Complete independent M0 dependency/security
      review; conditionally accept the exact graph only behind owned same-descriptor
      preflight and retain hostile allocation evidence.
- [x] (2026-11-16) Record raw-input observability disposition and complete the
      second read-only review of the amended canonical contracts.
- [x] (2026-11-16, focused re-review) Complete second canonical review and close
      its lock-authority finding by binding the exact Cargo.lock SHA in the
      shape-converter specification. Raw-input disposition is the only remaining
      High/Medium checkpoint finding.
- [x] (2026-11-16, operator disposition) Retain complete within-limit original
      uploads with SHA-256 provenance; quarantine rejected/hostile originals as
      private download-only project artifacts for human abuse review. Exclude
      automatic bans and new identity/network stores.
- [x] (2026-11-16, focused correctness review) Ratify the recoverable receipt
      state machine, exact source/converter digest reconciliation, and private
      archive/restore behavior with no unresolved High/Medium correctness finding.
- [x] (2026-11-16, focused security re-review) Close retained-evidence owner/
      group authorization and shared-filesystem admission findings; no unresolved
      High/Medium M0 security or correctness finding remains.
- [x] (2026-11-16) Commit the ratified contracts, ADR, exact dependency decision,
      source/threat/state matrices, and reproducible 46-file red corpus as the
      standalone implementation ancestor `1aebebfe0`.
- [x] (2026-11-17) M1: implement and directly test the bounded
      `geoparquet_parser_cli`; commit `eb6b0d3fb`, 30 locked/offline tests and
      final independent correctness/security review pass.
- [x] (2026-11-17) M2: qualify exact local image
      `sha256:ed4d93692add…c62386`; focused Python/Rust, exact-image resource,
      cancellation, recovery, SBOM and independent M2 reviews pass.
- [x] (2026-11-17) M3: integrate Roads and AgFields with retained originals,
      SHA-256 receipts, receiving validation, reversible replacement and reload.
- [x] (2026-11-17) M4: integrate Omni run/dry-run and Batch Runner with the same
      boundary, polygon-only Batch admission and rollback safety.
- [ ] M5: original six frozen QA findings and Omni evidence cleanup are
      remediated and sharing disposition ratified; copy/reset remediation,
      final combined validation and all-lane acceptance remain.
- [x] (2026-11-17, resumed) Commit recovery/artifact/provenance fixes through
      `1bb088da5`; retain machine-readable per-case validation and the confirmed
      copy/reset failure-class inventory.
- [x] (2026-11-17) Freeze-preparation validation: 384 focused tests pass with
      four skips, and 16 real-controller/exact-final5 downstream cases pass for
      Roads, AgFields, Omni, and Batch across all four admitted formats. Signed
      browser-session provenance, hostile-event minimization, renewable-lease
      cleanup, restore lock ordering, and concurrent rollback regressions pass.

- [x] (2026-11-17) Ratify public/team evidence inheritance and separate copying
      principal accounting at standalone contract ancestor `bbb216c0b`; both
      independent contract checkpoints pass. No operator decision remains open.
- [ ] Complete copy/reset integration and final frozen validation. Real Redis
      tests now cover fork, profile, Batch and Omni consumers; final combined
      gates and independent acceptance remain pending.
## Surprises & Discoveries

- Real fork rsync copies private evidence under ordinary public-run access;
  destination ownership then authorizes its download. Copy/reset consumers also
  bypass retention accounting. The independently retained inventory names each
  confirmed consumer; operator sharing disposition was ratified at `bbb216c0b`.
- Omni cleanup deleted the production retained-attempt directory. Earlier
  downstream fixtures used a generic attempt root and missed it. Fixtures now
  use the exact workflow roots and re-read receipts after real report generation;
  both cleanup loops preserve retained evidence.

- Resumption found the shared checkout scaffold stale; the task branch contains
  the implemented successor and final5 image qualification. Frozen QA found
  whole-Batch deletion omitted from retained-evidence accounting and synthetic
  downstream artifacts that cannot establish acceptance.

- The required dependency/security agent was terminated by an external account-
  security gate (Daybreak Blue eligibility/hardware-key sign-in). Its preliminary
  findings and evaluation lock are retained, but it supplied no acceptance verdict.
- QA fixture readback caught metadata loss in the trusted generator: several
  negative fixtures initially matched a valid control. Regeneration now asserts
  intended footer metadata; independent recheck is required before corpus credit.

- Resuming execution confirmed `wctl --project-dir /tmp/wepppy-vector-upload-normalization`
  correctly selects candidate documentation (one file validated). Container tests
  still require the task checkout mount; no shared-stack remount is authorized.
- Parquet 60.1.0 improves footer list validation but still lacks a page decoded-size
  ceiling. Bounded page/dictionary preflight remains necessary.
- AgFields and Omni source do not currently establish polygon-only validation;
  implement explicit receiving checks rather than assuming existing validation.

- The Batch Runner documentation describes watershed polygons, while current
  structural handling can admit points. The operator resolved this on 2026-11-16: accept Polygon/MultiPolygon
  watersheds only; point admission is intentionally removed for new uploads.
- The existing upload endpoints have different size limits and execution models.
  A single converter limit cannot silently replace their receiving contracts.
- GeoParquet's missing CRS and explicit `crs: null` have different meanings.
  Treating both as WGS84 would silently relocate unknown-coordinate data.
- Existing public-run authorization admits any authenticated reader, so a token
  check alone cannot protect retained hostile evidence. Sensitive paths require
  an explicit owner/root or existing Batch group predicate after classification.
- Project-local quotas cannot protect the shared `/wc1` filesystem across many
  projects. The canonical design now uses existing Redis for atomic filesystem,
  principal and in-flight reservations and fails closed on ambiguous accounting.
- The installed Docker CLI has no SBOM plugin and Syft/Grype/Trivy are absent.
  M2 retained exact Debian, Python and Rust package inventories plus a fresh
  RustSec audit; publication-pipeline image scanning remains a rollout gate.
- Ordinary archive creation is a sensitive evidence boundary. It must acquire
  the upload scope before scanning and publish attempt-bearing archives only
  below `archives/private` with a receipt and digest.
- Redis TTLs cannot be the only recovery authority for charged reservations.
  Durable reservation records plus receipt reconciliation and a bounded
  filesystem rebuild recover crashes, Redis loss, and project deletion.
- A successful workflow callback is not the end of replacement authority. Roads
  and AgFields must retain canonical and NoDb snapshots until the accepted
  receipt is durable; their commit callback now sits inside that rollback scope.
- The Docker-socket SBOM path was denied. Exporting the exact image and scanning
  the read-only daemon-free archive produced equivalent retained Syft/Grype
  evidence without granting a scanner daemon authority.
- Final4's syntactically valid source-revision string did not resolve in Git.
  Final5 uses the real M2 commit, and its seven-file embedded source manifest
  matches that commit byte-for-byte. Final4 is disqualified from publication.
- The first final5 equivalence rerun selected stale first-generation Parquet
  fixtures and correctly failed them. The retained final3-qualified fixture
  generation passed all exact-image selections; the failed run is not counted.
- A long full-suite run observed source while `/tmp/vun-candidate` was being
  updated and therefore is not revision-pure acceptance evidence. Its one
  restore failure exposed an unconditional vector Redis lease for projects with
  retention disabled; the candidate now avoids that new dependency, and the
  revision-pure focused archive suite passes.

- Final review reproduced parent cleanup erasing a complete original held by a
  live Omni child upload. Shared lifecycle and direct run/Batch deletion and
  archive restore now discover descendant reservation scopes before mutation.
- Exact-image downstream fixtures needed real retention configuration and the
  actual Omni workflow transaction after cleanup integration. All 25 real-ledger
  downstream cases pass locally; successor combined gates remain pending.
- Full sanity at `54ee356fd` reached 2,105 passes before the OpenAPI document
  exceeded its existing size budget by 120 bytes. Concise route descriptions
  preserve the response contract and size ceiling; successor rerun is required.
## Decision Log

- **2026-11-17, clone-policy checkpoint** - Do not infer permission to exclude
  private originals from project copies. Ask the operator for source-only
  evidence/provenance references versus authorized quota-accounted copies, while
  repairing independently authorized evidence-preservation defects. Keep M5 held.

- **2026-11-17, resumed QA closure** - Extend the existing destructive retention
  procedure to whole-Batch deletion and fence child-run scopes. Preserve
  sanctioned private receipt filenames while excluding them from security logs.
  Replace synthetic downstream test outputs with actual production generators;
  bind final validation to a committed source snapshot and retained fixture hashes.

- **2026-11-16, review interruption** - Do not bypass the account-security gate
  or substitute author review for the required independent security lane. Retain
  checkpoint work without claiming M0 acceptance or starting dependent M1–M5.
- **2026-11-16, observability** - Retain every complete within-limit original in
  a private neutral-suffix attempt directory, record SHA-256 provenance, and
  quarantine rejected bytes for human review. Oversize partials are removed;
  no automatic ban or new identity/network evidence store is authorized.
- **2026-11-16, retention admission** - Bound retained evidence at project,
  verified-principal/shared-unattributed and filesystem scopes. Use the existing
  Redis authority for owner-bound atomic reservations rather than add a service;
  preserve uncertain charges until explicit receipt/file recovery reconciles them.

- **2026-11-16, resumed execution** - Propose minimal parquet 60.1.0 with Snappy,
  no Arrow/default codecs, and existing offline PyProj for CRS. ADR-0145 records
  proposed structural caps inside the inherited resource envelope; review pending.

- **2026-11-16 23:22 UTC** - Use a separate `geoparquet_parser_cli` sibling.
  Format-specific code, dependencies, limits, provenance, and errors remain
  independently reviewable; `shape_parser_cli` remains Shapefile-specific.
- **2026-11-16 23:22 UTC** - Normalize binary formats in shape-converter and
  retain validation at receiving endpoints. This minimizes parser authority and
  prevents converter calls from bypassing workflow-specific contracts.
- **2026-11-16 23:22 UTC** - Initial GeoParquet scope is one local file, versions
  1.0/1.1, one root primary WKB geometry column, and scalar JSON-compatible
  properties. Reject broader dataset, extension, nested, encrypted, external,
  and remote semantics until separately authorized.
- **2026-11-16 23:22 UTC** - D-Tale and culvert API surfaces are not closure
  consumers. Their omission must remain explicit in tests, reviews, and claims.
- **2026-11-17, activation** - Binary admission defaults off and has one shared
  UI/server flag. Direct GeoJSON remains available during disable/rollback.
- **2026-11-17, recovery** - Preserve charged reservation metadata until an
  idempotent commit or operator reconciliation. Rebuild committed bytes only
  from terminal verified receipts while the filesystem reconciliation lock
  blocks new reservations.
- **2026-11-17, crash ambiguity** - Do not infer acceptance from canonical hash
  alone. Online Roads/AgFields replacement is transactional through receipt
  commit; stale prepared state without a workflow authority adapter remains
  `incomplete` and quarantined.
- **2026-11-17, corrected exact candidate** - Final5 disqualifies final4 and
  supersedes final3 locally. It exposes the verified parser binary and Cargo
  lock with a source revision that resolves in Git and matches the embedded
  seven-file source manifest.
- **2026-11-17, destructive retention repair** - Persist the rebuild obligation
  in both the private filesystem and Redis before deletion/restore. Block new
  reservations and readiness until an exact-root rebuild is read back and both
  markers are cleared. Retry uses the same globally qualified identity.
- **2026-11-17, workflow concurrency** - Hold one renewable run-scope fence
  across the complete Omni parse/build/receipt transaction, and one NoDb lock
  across Batch and AgFields file/state/receipt publication. Competing admission
  receives a bounded conflict; failure restores the latest committed bytes and
  state rather than a stale pre-lock snapshot.
- **2026-11-17, signed-session evidence** - Prove the signed-cookie to JWT to
  upload-auth path while isolating entitlement storage. Receipts retain only
  `{kind: human, user_id}` and security events omit session IDs, email, roles,
  raw claims, and client IP.

## Outcomes & Retrospective

Current disposition: sharing is ratified at `bbb216c0b`; copy/reset integration
is committed through `54ee356fd`. Final review corrections and frozen
verification are in progress. No operator decision remains open.

Historical pre-sharing checkpoint: implementation through `1bb088da5` was committed locally.
The original QA findings and Omni cleanup defect are repaired. Exact source/image
and per-test evidence is in `artifacts/20261117_resumed_validation.json` (452/4
focused predecessor; overlapping 206/0 successor; frontend gates pass). Full
sanity was interrupted at the newly required operator contract decision and is
not accepted. One High fork privacy and one Medium copy/reset accounting class
remained at that checkpoint. The later sharing decision supersedes the privacy
hold; accounting and final gates are tracked above.
No remote integration, publication or deployment occurred.

Current resumption: M0-M4 implementation is retained in the task worktree. M5
remains open while six frozen QA findings are remediated and independently
reviewed. Initial real-Redis deletion/recovery and Batch concurrency validation
passes 50 tests. Earlier milestone statements below are historical checkpoints.

M0 dependency security review resumed under Daybreak and conditionally accepted
the exact graph behind the owned same-descriptor preflight. The canonical
re-review and focused retention correctness/security reviews pass with no
unresolved High/Medium finding. Standalone ancestor `1aebebfe0` completes M0.
No runtime implementation, production
dependency, candidate image, workflow acceptance, remote integration, publication
or deployment is complete.

M1 is complete at `eb6b0d3fb`: the separately locked parser enforces the owned
same-descriptor structural preflight, bounded WKB/JSON output, atomic no-replace
publication, stable errors and no-follow file handling. Thirty direct tests,
strict clippy/formatting, a 53-file deterministic corpus, and independent
correctness/security reviews pass. M2 implementation is committed at
`0e58feced`; its exact local image passes preliminary API/provenance/containment
qualification recorded in `artifacts/20261116_m2_validation.md`. M2 independent
review passed. M3/M4 are implemented at `9ac7cb8f6` plus the current closure
candidate. Exact final5 passes the common helper plus actual Roads, AgFields,
Omni run/dry-run and Batch HTTP boundaries across four supported suffixes. Final
M5 re-review remains open. No image was published and no production deployment
or remote-host acceptance was performed.

The freeze-preparation successor passes 384 focused tests (four skipped) and 16
exact-final5 downstream artifact/readback cases. These results include renewable
lease fault injection, global-before-project destructive lock order,
transactional concurrency rollback, real signed browser-session provenance, and
minimized hostile-upload events. Final five-lane review must bind the next
committed successor before M5 can be marked complete.

Resumed M0 review is active in independent correctness, security/dependency, QA
and operations lanes. Proposed resource ADR and threat matrix now exist; neither
is accepted evidence of a working parser. Shared converter source matches the
starting worktree (apart from caches/build outputs). Shared unrelated work is
preserved. The running converter is not the predecessor final-4 qualified image.

The planning scaffold is complete. No production code, dependencies, images,
contracts, or deployment state changed. Update this section after each milestone
with the supported completion claim, retained evidence, and remaining rollout or
recovery work.

## Context and Orientation

The shape-converter service is under
`wepppy/microservices/shape_converter/`; its specification is
`wepppy/microservices/shape_converter/docs/specification.md`, and its existing
Rust Shapefile binary is under `wepppy/microservices/shape_converter/rust/`.
Read the nearest `AGENTS.md` files before editing.

The four consumers span browser controllers, Flask or rq-engine routes, and NoDb
or build services. The authoritative endpoint inventory is
`docs/schemas/upload-endpoint-contract.md`. M0 must trace each browser entry point
to the exact receiving function, validation, persistence, generated artifact,
and reload path. Do not infer the contract from file accept attributes alone.

The predecessor security package is
`docs/work-packages/20261113_shape_converter_security_conformance/`. Reuse its
accepted launcher, lifecycle, provenance, readiness, exact-image, cancellation,
cleanup, and fail-closed patterns. Do not reopen its GDAL/Fiona architecture or
claim its pending production rollout has occurred.

## Plan of Work

### M0 - Ratify contracts and retain red evidence

First verify the source inventory and create a matrix for Roads, AgFields, Omni,
and Batch Runner covering entry points, auth/CSRF, current extensions and MIME
handling, byte limits, geometry/property rules, CRS behavior, synchronous versus
queued execution, error schema, persistence, reload, and downstream artifacts.
Update `docs/schemas/upload-endpoint-contract.md` from evidence.

Before implementation, author a canonical vector-upload normalization contract
that defines:

- accepted formats and exact admission rules;
- when uploads are staged and when normalization occurs;
- canonical GeoJSON schema, CRS, feature/property, numeric, and ordering rules;
- per-boundary byte/resource limits and stable error mapping;
- raw and normalized artifact retention/observability;
- cancellation, cleanup, retry, idempotency, and partial-state behavior; and
- the invariant that every receiving workflow revalidates normalized content.

Amend the shape-converter specification to include GeoParquet input only after
the contract checkpoint is reviewed. Resolve the Batch Runner point/polygon
question with the operator; do not preserve or remove user-visible admission by
assumption.

Author an ADR for every new numeric default and threshold. Complete
`artifacts/20261116_dependency_evaluation.md` for the exact locked Rust graph.
Retain bounded red fixtures for all valid and hostile states before green code.
The red matrix must include malformed footer/magic, metadata/schema expansion,
declared/actual decompression expansion, external file references, encryption,
unsupported codecs/encodings, extension metadata, WKB length/nesting/vertex
bombs, nonfinite coordinates, CRS absence/null/invalid values, timeouts,
cancellation, process descendants, cleanup, concurrency, and converter bypass.

M0 exits only when contracts, ADR, dependency decision, red matrix, security
threat model, correctness state matrix, and review plan agree. Record the exact
checkpoint revision in this plan and `tracker.md`.

### M1 - Build the GeoParquet Rust CLI

Create `geoparquet_parser_cli` as a separate binary/crate using only the accepted
locked dependencies. Its input is one already-admitted local file plus bounded
configuration supplied by the trusted launcher. Its output is one strict,
versioned, data-only JSON envelope. It must not accept URLs, directories,
datasets, arbitrary output paths, environment-selected plugins, or network
resources.

Enforce limits before allocation/decompression/traversal wherever the format
allows, and enforce measured limits while decoding. Validate exact magic,
footer/metadata, schema, primary geometry column, supported WKB encoding,
properties, codecs, row groups, rows, bytes, geometry, finite coordinates, CRS,
and normalized output. Recompute geometry types and bounds rather than trusting
metadata. Return bounded stable error codes without raw attacker metadata or
filesystem paths.

Add direct Rust unit/integration tests and a bounded deterministic mutation
corpus. Prove valid GeoParquet 1.0/1.1 controls and every M0 rejection class.
Measure CPU, memory, descriptors, scratch, decoded bytes, and output against the
ADR ceilings. No Python fallback is permitted.

### M2 - Integrate and qualify shape-converter

Add a Python launcher following the accepted `shape_parser_cli` lifecycle:
private request scratch, minimal environment, strict argv, no shell, process
group ownership, direct resource limits, wall timeout, cancellation shielding
and drainage, bounded stdout/stderr/IPC, schema validation, cleanup, and stable
API errors. Repeated cancellation must not release ownership before every parser
descendant is drained.

Extend converter inspect/convert contracts only as ratified. Generate canonical
GeoJSON, then parse it back and verify the service's declared counts, geometry
types, bounds, CRS, and hash before returning success. Add runtime-derived
readiness using an actual bounded CLI parse and binary provenance. Build and
qualify the exact candidate image; retain SBOM, vulnerability dispositions,
binary hash/version, resolved Compose, resource probes, cleanup, recovery, and
fail-closed activation evidence.

### M3 - Integrate Roads and AgFields

Update browser accept/help text and submission handling without trusting file
extensions or client MIME. Route Shapefile ZIP and GeoParquet through the
converter, then feed only canonical normalized GeoJSON into the existing
workflow validator and persistence boundary. Preserve auth, CSRF, run scope,
locking, size limits, geometry rules, error schema, retry, and reload behavior.

For Roads prove line-only semantics and the existing size contract. For
AgFields prove polygonal features and required `field_id` semantics. For each,
exercise all three formats through the real browser/API boundary, reload state,
and parse the next consumed/generated artifact.

### M4 - Integrate Omni and Batch Runner

Apply the same contract-preserving integration to Omni contrast run and dry-run
paths. Prove polygon semantics, CRS behavior, 100 MiB endpoint policy, queued
execution behavior, error mapping, and resubmission/reload.

Do not edit Batch Runner until M0 resolves its geometry contract. Once ratified,
cover the browser/controller, upload route, `WatershedCollection`, `BatchRunner`,
and generated per-watershed inputs. Preserve the 30 MiB endpoint policy unless
the ADR explicitly changes it. Prove equivalence and rejection behavior through
the actual downstream run artifact, not only converter output.

### M5 - Validate, review, document, and prepare rollout

Run the narrowest complete affected Python, Rust, frontend, accessibility,
Compose, documentation, dependency, and security checks. Run broader gates only
when required by touched shared code or the repository standards. Complete
independent correctness, code, QA, security, and operations reviews against the
same committed revision and exact image. Resolve every High and Medium finding.

Update user help, operator deployment/recovery guidance, developer contracts,
and the package evidence. Production deployment, image publication, and rollout
remain separate operator actions. A rollout plan must name canaries for each
workflow, health/danger signals, immediate disable/rollback behavior, artifact
readback, and observation duration.

## Validation and Acceptance

At minimum, the final evidence must include:

- direct Rust tests and malformed-input corpus results for the CLI;
- shape-converter API tests for inspect/convert, limits, timeout, cancellation,
  repeated cancellation, process descendants, cleanup, readiness, provenance,
  and recovery;
- per-workflow Python route/service/NoDb tests and frontend tests for selector,
  submission, progress, error, retry, and reload states;
- `wctl check-rq-graph` if any enqueue or dependency edge changes;
- `wctl run-npm lint` and `wctl run-npm test` for frontend changes;
- exact-image semantic readback and resource/concurrency probes;
- direct format-equivalence evidence for every workflow and all three formats;
- `wctl doc-lint` for every changed Markdown document; and
- independent review artifacts with no unresolved High or Medium findings.

All commands, revisions, image digests, fixture hashes, results, skips, and
environment limitations must be recorded. Tests that merely mock the converter,
assert a job succeeded, or check that a file exists do not satisfy artifact
acceptance.

## Idempotence and Recovery

Fixtures and builds must be deterministic and safe to rerun. Request scratch is
unique and removed after success, rejection, timeout, cancellation, or process
failure. Normalization must not mutate workflow state until the complete output
passes receiving validation. Retry must start from a new private request root;
it must not reuse partial parser output.

If the CLI cannot be proven present, authentic, ready, bounded, or cleanly
drained, the GeoParquet path fails closed with a stable unavailable response.
It must not fall back to PyArrow, GDAL/Fiona, `shape_parser_cli`, or in-process
parsing. Rollback disables new binary-format UI admission and restores the prior
GeoJSON-only workflow without changing existing projects.

## Artifacts and Notes

- Package: `docs/work-packages/20261116_vector_upload_normalization/package.md`
- Tracker: `docs/work-packages/20261116_vector_upload_normalization/tracker.md`
- Dependency gate: `artifacts/20261116_dependency_evaluation.md`
- Correctness gate: `artifacts/20261116_correctness_review.md`
- Security gate: `artifacts/20261116_security_review.md`
- Future contract: `docs/schemas/vector-upload-normalization-contract.md`
- Future ADR: allocate the next available number only during M0

## Interfaces and Dependencies

The public converter request/response and every receiving workflow interface
must be specified in M0 before code. The new CLI must expose a versioned JSON
schema rather than a language object protocol. Its executable and adjacent
provenance manifest are image-owned artifacts verified at build, startup, and
readiness.

Any candidate Rust dependency remains unapproved until the package dependency
artifact is complete. Do not add PyArrow or another Python/native parser as a
temporary implementation. Do not introduce a service, queue, datastore, daemon,
socket, privilege, protocol, mount, or network dependency without stopping and
amending the complexity budget with retained evidence and explicit approval.

## Revision Note

2026-11-16 23:22 UTC: Initial plan created from the verified upload inventory and
the operator decisions to use a sibling Rust GeoParquet CLI, exclude culvert API
paths, and defer D-Tale.



## Execution checkpoint - 2026-11-16

Execution started. Read the active plan, integration/history governance, and
upload endpoint contract. Created task branch `codex/vector-upload-normalization`
in `/tmp/wepppy-vector-upload-normalization` at
`05e3450fa7d3b24572e65161100670ae542a6ea8`.
The package exists in the shared checkout but is absent from that committed
revision. Preserve and transfer the package before implementation; do not assume
the task worktree contains uncommitted predecessor changes.

The operator decision is resolved: new Batch Runner uploads accept only
Polygon/MultiPolygon watersheds. Implementation and regression evidence remain pending. M0 is incomplete;
no parser, workflow, dependency, image, or deployment change has been made.
Next: reconcile required uncommitted source context into the task worktree,
verify the source matrix, and complete M0 contracts and evidence before M1.


## Decision amendment - Batch Runner geometry

On 2026-11-16 the operator explicitly selected Polygon/MultiPolygon watersheds.
New uploads in all three supported formats must reject points, lines, geometry
collections, null geometries, and mixed collections containing unsupported
geometries before replacing the accepted resource or registering state. This
aligns admission with watershed polygon semantics; retaining legacy point
admission was considered and rejected by the operator. Existing saved projects
are not migrated or deleted by this decision.

Compatibility and regression plan: exercise Polygon and MultiPolygon success,
Point/MultiPoint/line/collection/null/mixed rejection, failed replacement with
an already accepted resource, reload, and generated per-watershed artifact
readback. Scope validation to Batch Runner admission; do not silently restrict
shared collection consumers. Preserve the existing upload byte policy and
response schema. M0 dependency, resource, fixture, and review gates remain open.


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

## Resumption after external blocker

Restore the review session eligibility through the account-security mechanism
reported by the tool, then complete the interrupted dependency/security lane.
Retained artifacts are under `artifacts/`; review `20261116_contract_decision.md`
and the individual QA/correctness/operations dispositions. Resolve the pending
raw-input observability exception before implementing deletion. Finish empirical
dependency/resource gates and canonical amendments, obtain both independent
checkpoint reviews, and commit a standalone accepted ancestor before M1. Use
explicit `wctl --project-dir /tmp/wepppy-vector-upload-normalization` and the
retained isolated Compose harness for candidate checks. Do not count the shared
running stack as candidate validation. No accepted checkpoint SHA exists yet.

## Daybreak review and canonical amendment checkpoint

Daybreak-enabled independent review conditionally accepts Parquet 60.1.0 with
defaults disabled and Snappy only, plus serde_json 1.0.145, at lock SHA-256
`ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`.
Direct upstream decoding of unpreflighted hostile bytes is rejected. The review
reproduced 64 GiB and 2 GiB allocation attempts and requires complete owned
same-descriptor preflight. ADR-0145 is accepted for implementation; endpoint,
normalization, dependency and converter specifications are amended and lint
clean. The second focused re-review has no remaining High/Medium finding except
the operator's explicit raw-binary retention/deletion disposition. M0 and its
standalone ancestor remain held only on that decision.

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


2026-11-17 resumption revision: recovered the correct execution session and
continued the six frozen QA findings; no shared checkout or deployment changes.


2026-11-17 resumption handoff: retained exact revision/test evidence, fixed the
confirmed Omni cleanup defect, and recorded the independently reproduced copy
privacy/accounting blocker. Continue from the operator clone-policy decision;
do not restart M0 or interpret prior PASS artifacts as package acceptance.


## Operator sharing decision - 2026-11-17

The operator rejected the proposed fork privacy restriction: public sharing or
team access permits ordinary authorized copies to inherit the complete project.
Canonical authority is the normalization contract section “Sharing, copies, and
existing workspace resets”; rationale/checkpoint is
`artifacts/20261117_sharing_contract_decision.md`. Do not ask this question again
or exclude originals from forks. The privacy finding is resolved by this policy;
physical copy/reset accounting and final validation remain to be completed.
