# Design security review — Single User-Defined landuse and soils

## Metadata

- **Package**: `docs/work-packages/20260925_single_user_defined_landuse_soils/`
- **Date**: 2026-09-25 UTC
- **Prepared by**: Codex; independent security reviewer not yet assigned
- **Stage**: Pre-checkpoint design artifact, based on `docs/prompt_templates/security_review_template.md`
- **Baseline**: `b96f77e589ec033853970ac90fdab945490c6553`; implementation not started
- **Related evidence**: [dependency trace](20260925_dependency_review.md), [package review](20260925_work_package_review.md)

## Security triage decision

**Impact: high. Dedicated independent security review required before the canonical
contract checkpoint.** The feature introduces untrusted management/soil uploads,
parser work, run-scoped file publication, NoDb metadata mutation, and a new
configuration policy enforced across Builder, run features, and worker entry points.

Authorization remains the existing run/session-token boundary. Checking the Builder
option changes project capabilities; it grants no new user role, run access, or
filesystem privilege. It excludes Disturbed/SBS/dependents and buffer OFEs while
preserving compatible features and unchecked/legacy behavior. No new service,
external dependency, secret, network destination, or deployment topology is proposed.

## Valid-state and error policy to review

| State | Required behavior | Evidence stage |
| --- | --- | --- |
| Fresh project; no source metadata/directory | Create accepted input under normal project rules; Build without any source gets a clear validation error | Design now; unmocked filesystem/runtime tests later |
| Existing valid accepted source | Reload/display/reuse; failed replacement preserves source and metadata | Design now; failure/concurrency tests later |
| Legitimate NoDir projection/archive | Work within canonical materialized run scope; do not reject valid roots merely for being projections | Design now; direct archive/restore evidence later |
| Unchecked or legacy project | Preserve existing defaults, controllers, buffers, and artifacts; reject new upload modes | Design now; compatibility tests later |
| Opted-in project with ordinary database modes | Keep Disturbed, dependent features, and buffers disabled without requiring uploads | Design now; UI/API/build tests later |
| Malformed/hostile upload or unsupported format | Bounded rejection before active-file/state publication or build enqueue | Design now; real parser/filesystem tests later |
| Forbidden feature, SBS, or buffer request | Explicit canonical policy error before mutation/enqueue; do not initialize a controller to satisfy it | Design now; direct/indirect API/task tests later |

Expected absence is not corruption. Filename feedback uses escaped text, never raw
HTML. Validation errors must not expose internal paths, uploaded contents, tokens,
or full parser tracebacks to ordinary users. Logs retain run/request context and
bounded diagnostics. Exact codes/messages belong in the canonical checkpoint.

## Surface checks and required design controls

### Authorization and feature policy

Preserve authentication, run ownership/scope, read-only restrictions, and the
canonical CSRF/session-token contracts. Derive policy from trusted persisted
configuration, not user-submitted run form values. Validate the entire feature
activation/dependency closure before changing module lists or restoring backups.
Enforce feature/SBS/buffer exclusions at direct mutation and execution boundaries,
not only in menus. Recheck policy before build operations; invalid stored buffer
state must not be silently used. Preserve the creation-time flag through config
refresh, clone, and archive/restore. Preserve valid legacy BAER alternatives.

### Input validation and parser resource bounds

Allow exactly one plain-text file of the expected extension and approved format
subset. Enforce streaming/multipart byte limits before unbounded reads, and finite
record/OFE/layer/rotation/scenario/reference counts before expensive parsing or
replication. Extension, MIME, and successful parsing alone do not prove safety.
Reject invalid encodings, binary/empty/truncated files, malformed references,
non-finite numbers, and unsupported content with bounded errors. No evaluation,
shell invocation, object deserialization, or uploaded-path dereferencing is needed.

Audit owned parsers for count-driven allocation and loops, silent numeric repair,
and ignored trailing input. Finalize exact byte/count/encoding/trailing-data rules
before design approval; management 5 MiB is only an existing precedent, not an
approved new threshold. Avoid arbitrary bounds that reject supported valid files.

### Filesystem and publication

Separate original display names from storage identities. Prevent traversal,
absolute-path writes, child symlink escapes, generated-file collisions, and
same-normalized-name confusion. Account for legitimate projection roots. Validate
and publish the same bytes so replacement cannot change content between checks.
Use canonical NoDb locking/cache invalidation and existing publication primitives.
Define failure recovery across staging, publication, metadata, and queue submission.
A running build must consume one consistent accepted source generation.

### Queue and execution

No new queue topology is planned. Enqueue only after input acceptance and policy
validation. Worker parameters must remain trusted run identifiers/validated state;
never concatenate uploaded filenames into shell commands. Queued work must not
bypass policy after state changes. Retry/cancel/failure behavior must preserve source
and explicit status. Apply graph/catalog/live-job-tree checks if wiring changes.

### Integrity, visibility, and recovery

Preserve original accepted bytes and modifier provenance. Define visible module
paths for inputs, intermediates, failed-build diagnostics, and final outputs under
normal project authorization and archive coverage. Resolve bounded handling of
rejected hostile bytes separately; observability is not permission to install them
as active inputs or retain unlimited uploads. Rollback affects candidate code/new
creation behavior; existing projects are not silently migrated or repaired.

### Other template surfaces

No new secrets, MCP/agent execution, external integrations, or CI/CD permissions are
in scope. Review any actual implementation delta before marking these surfaces
not applicable. No new dependency is budgeted. Preserve existing runtime identities,
groups, permissions, mounts, and umask, and validate the real workflow before ship.

## Open design review items

These are explicit design obligations, not independent findings or completed tests.

| ID | Surface | Required resolution before checkpoint | Status |
| --- | --- | --- | --- |
| DS-01 | Parser envelope | Finalize supported versions/content, source OFE count, byte/count bounds, encoding, and trailing-content rules using representative fixtures | Pending |
| DS-02 | Source lifecycle | Finalize storage names/layout, replacement/concurrency consistency, publication rollback, enqueue failure, and rejected-byte retention | Pending |
| DS-03 | Policy enforcement | Finalize exact current-contract/source matrix and errors for Builder/refresh, dependency activation, direct tasks, and buffer exclusion | Pending |
| DS-04 | Compatibility | Complete valid-state/noninterference and data-schema regression matrix, including projected roots and unchanged legacy BAER/buffers | Pending |

## Findings and verdict

Independent review findings have not yet been produced. No finding counts or pass
verdict are claimed. **Gate: pending; hold the canonical checkpoint until design
review and dispositions are complete.** This artifact corrects the review sequence;
its existence alone is not design approval. Runtime release readiness is also pending.

## Validation evidence and continuation

At design stage, evidence consists of source tracing, document checks, and the
approved product direction. No production-path tests were performed. Before the
checkpoint, attach independent security review findings, exact contract versions,
and disposition/post-fix confirmation. No unresolved medium/high design finding
may be carried into the checkpoint as implicitly accepted.

During implementation, append direct unmocked valid/hostile upload and filesystem
results, concurrency/recovery tests, UI/API policy checks, generated-input semantic
readback, and production-equivalent execution/archive evidence. Use the separate
correctness/UX review for valid user outcomes; security review does not replace it.
Complete scoped/full test gates as required by the final changes, not by this draft.

## Residual risk and sign-off

No residual risk has been accepted. Remaining design items, source/content support,
and implementation behavior require evidence. Independent security reviewer sign-off
and exact canonical checkpoint approval are pending. Operator product decisions on
Builder policy and buffer exclusion are recorded in the package; they do not claim
approval of an unfinished security assessment.
