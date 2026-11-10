# Declarative model builds and shared task provenance

## Status

Proposed specification, 2026-11-10; discussion and review disposition in progress.
This records operator direction and proposed design, not implementation
conformance or authorization to change runtime behavior. Implementation requires
the applicable contract-first checkpoint and an execution plan.

Source inspection baseline: `da14ef8b1`. Existing on-demand, batch, NoDb,
authorization, artifact and deployment contracts remain authoritative.
[Independent reviews and discussion](../reviews/declarative-model-build-spec-review.md)
retain findings against earlier drafts; superseded assumptions are identified.

## Operator direction and scope

- Preserve WEPPcloud's mutable on-demand modeling workflow.
- An independent engine resolves a declarative model and executes a full build
  using common individual RQ processing tasks and existing NoDb/project layouts.
- All declarative builds start from scratch. Importing/reusing existing project
  results and incremental rebuilding after specification edits are deferred.
  This supersedes the earlier content-addressed reuse/invalidation proposal.
- Keep provenance lightweight and available to both orchestration modes.
  Record image identity for every project-associated RQ task attempt, with richer
  scientific provenance adopted task by task.
- Use the project's canonical directory. Do not add isolated per-node/per-attempt
  workspaces, copy trees or immutable staging as prerequisites.
- Use Git stage-boundary checkpoints to associate task identities with recorded
  project state. Strong working-directory immutability is not required.
- Fingerprint external resources; collect library/environment observations for
  diagnosis without introducing incidental dependency invalidation rules.
- Favor simplicity and reliability over speed. Do not build cache lookup,
  selective rebuilding, worker pooling or autoscaling in the initial engine.

Rationale: full builds and stage history meet the current need without a general
build cache or duplicate workspaces. Copying large resources adds storage/network
cost and complicates canonical project paths. Git records attributable boundary
states; NoDb and existing task coordination continue owning live project state.

## Deployment and image compatibility

`/workdir/open-wepp-org` owns the Kubernetes deployment that will support the
engine; its current cluster is Talos. Production wepp.cloud remains Docker
Compose. Moving production to RKE is a long-term operator direction outside this
scope. The shared image-observation contract must work before that migration.

The operator selected the open-wepp-org cluster for implementation validation,
including the first vertical slice. Plan and verify actual image observations,
worker routing, canonical storage, read-only finalization and subsequent viewing
there using its existing deployment entry points. Production wepp.cloud rollout
is outside this initial scope. Cluster selection establishes the validation
target; it does not assert readiness or authorize unrelated deployment changes.

Each model pins one schema version and one GHCR image resolved to an immutable
digest. Each execution image supports exactly one model-schema version; admission
requires an exact match. Multiple image releases can implement the same schema
with different scientific behavior, distinguished by digest.

Schema upgrades are explicit model-definition migrations. Preserve original
specifications and image associations. Older pinned releases remain executable
only while available and authorized; never silently substitute a different image.
Keep the small engine-to-image protocol separately versioned from the model
schema. Image-local code owns schema-specific task translation.

Accepted admission rule: a deployment-controlled, version-controlled file or
configuration lists approved exact GHCR image digests and their one model schema,
execution protocol and task contracts. No catalog service is required. Repository
membership or self-declared compatibility alone does not authorize an image.
Removing approval prevents new builds without rewriting historical records.
The exact file format and admission implementation remain to be specified.

## Access authority

Initial build submission is restricted to deployment operators. Broader user
submission is deferred; any later expansion should reuse existing identities,
project authorization and feature permissions rather than introduce a separate
engine account system. The engine's infrastructure credentials do not confer
their authority on a submitter.

Model definitions select admitted images, supported operations and permitted
resources. Deployment configuration owns mounts, Kubernetes service accounts,
secret delivery and worker commands; model fields cannot override these execution
boundaries. Preserve existing namespace, network and credential restrictions.

Initially support named datasets, supported providers and explicitly supported
uploaded inputs through existing acquisition tasks and access checks. Arbitrary
URL/path retrieval and a general resource-policy framework are outside initial
scope. The definition describes resource selection; the deployment supplies
credentials. A resource or credential reference does not itself grant access.
Preserve source access and intended project visibility, including browser/download
surfaces: private retained source content must not become public as a side effect
of build creation. Exact supported sources and visibility mapping require an
implementation contract before admission.

Subsequent report/view requests use existing project access and feature permissions
plus the shared read-only permitted-operation contract. A report task may write
only its authorized derived artifacts and operational records, cannot clear
read-only, and does not inherit the engine's build-stage mutation authority.
Enforce these boundaries at backend admission and execution, including queued jobs;
frontend declarative/read-only awareness is presentation, not authorization.

Rationale: explicit deployment approval, operator-only submission and existing
resource/access mechanisms bound the initial engine without adding a catalog
service, independent identity system or general policy framework.

## Responsibility boundaries

| Component | Responsibility |
| --- | --- |
| Model specification | Resources, operations, parameters, requested products and selected image/schema |
| Independent engine | Resolve inputs; validate graph; allocate a normal project; dispatch full build; track attempts and final outcome |
| Image-local adapter | Interpret the supported schema and call that image's shared RQ implementations |
| Shared task | Existing scientific processing, effective-input observations, output validation and task provenance |
| NoDb/project filesystem | Existing mutable state authority and canonical artifact organization |
| Git checkpoints | Attributable stage snapshots and versioned provenance records |
| Execution backend | Launch selected workers; supply observed runtime identity and existing credentials |

Do not fork scientific implementations for declarative execution or force every
function/output file into a separate graph node. Existing coarse orchestrators
may compose processing tasks. Preserve normal on-demand signatures and defaults
through adapters where necessary. On-demand operation must not require an engine
service, registry lookup, Kubernetes or a new provenance datastore.

## Full-build execution and project ownership

A new declarative build allocates a fresh normal project through existing project
creation mechanisms. It does not seed results from an existing interactive run.
Source datasets may remain at their established locations; starting from scratch
means recomputing requested model work, not duplicating all external source bytes.
A specification edit requests another full build, not incremental repair.

The canonical project is the execution and browse/archive location. No copy-back
or alternate workspace reconciliation phase is required. Mapping model revisions
to normal project IDs and the UX for repeated builds remain to be specified.
Existing results are not deleted to satisfy this proposal.

Use existing run/task admission and ownership controls. A Git commit is not a
lock. Do not run overlapping full builds against the same project state. Parallel
stages may retain existing disjoint-output patterns, with serialized Git index/
commit operations and precise task-owned paths. Avoid blanket `git add .` that
could attribute another stage's changes or include secrets.

The initial routing proposal is a build-specific RQ queue and dedicated workers
running the selected image, with fixed capacity. Choose worker count after
checking whether parent jobs wait for children; one worker is not automatically
safe. Every descendant must retain the build routing context. Existing
`Queue(connection=...)` calls must not send declarative children to ordinary
on-demand queues. Preserve on-demand queue defaults.

Queue emptiness and container exit are not build success. Graph completion and
required outputs determine the outcome. Define one retry/recovery owner across
engine, RQ and Kubernetes. Initially a failed build may require an explicit full
restart in a new normal project; do not silently infer resumability from old files
or timestamps. Infrastructure redelivery still needs duplicate-attempt handling.

## Build completion and subsequent on-demand processing

Declarative projects must support the normal frontend and subsequent on-demand
tasks, including reports generated when requested. The model declares the build
graph and required products. Successful completion attests to those products and
their validation/provenance at the completion boundary; it does not promise that
every possible frontend report has already been generated.

Retain a completion record identifying the model definition, resolved graph,
selected successful attempts, required artifact fingerprints and stage checkpoints.
Later processing is outside that completed build unless explicitly included in
its declared graph. Record subsequent tasks as on-demand attempts with their own
actual image, inputs, outputs and linkage to the build artifacts they consume.
They need not use the build's image. Serving/report compatibility is best effort:
no compatibility layer, version negotiation, artifact migration or historical-image
renderer selection is required. Runtime incompatibilities may surface as ordinary
report/view errors and be fixed when encountered. Do not attribute the serving
runtime to the original build or modify protected build artifacts to hide an error.
This accepts compatibility failures to avoid complexity and regression risk; it
does not relax the model-schema/image admission contract.

Finalization marks the declarative project read-only through the shared project
read-only contract. Successful build completion requires this protection to be
established; a failed transition leaves finalization incomplete. Finish required
build writes and coordinate active writers before publishing completion. Do not
implement the transition by merely disabling frontend controls.

Read-only protects model configuration, scientific inputs, declared build products
and historical build records from ordinary mutation. It must contractually allow
the on-demand tasks needed for interactive reports and project viewing, including
their explicitly permitted derived artifacts, caches and operational records.
These tasks must not modify protected build state, silently rerun model stages,
or temporarily clear the project's read-only flag. A task that combines reporting
with protected mutations needs a bounded compatible path before it is permitted.
Apply this distinction through the shared read-only contract, not a separate
declarative bypass; existing authorization and feature restrictions still apply.

Keep the frontend contract lightweight: views know that the project is declarative
and honor its read-only state, while existing report/task status and freshness
surfaces describe subsequent processing. No graph inspector or separate provenance
dashboard is required. Server-side admission and task execution enforce permitted
operations, including direct API calls and jobs queued before finalization.
A later report failure does not retroactively fail the build or rewrite history.

Existing surfaces do not yet uniformly implement this proposed read-only task
contract. In particular, generic read-only query-catalog refresh currently forbids
publication. Inventory actual viewer/report writes and reconcile the affected
contracts explicitly before implementation; do not assume all report-labeled jobs
are safe or grant a generic catalog-write exception. Ordinary editing/unlocking of
finalized declarative projects is outside the supported viewing workflow. Any
future authorized conversion to mutable use must explicitly leave the protected
declarative scope rather than silently retain its guarantee.

Rationale: the canonical project remains usable interactively while the engine's
guarantee has a precise, bounded scope. Serving a project is not a perpetual
declarative build, nor a promise to monitor all upstream sources.

## Execution identity observations

Record per task attempt, not as one overwriteable project image value: project,
operation, RQ job/attempt IDs, queue, actual image identity, platform, source
revision when available, timestamps and outcome. Persist in visible archivable
project records without competing whole-object NoDb dumps.

Bind deployment/runtime evidence to the actual worker. A tag or user-supplied job
argument alone cannot establish identity. Distinguish OCI index, platform manifest
and local image/config digests. Images cannot embed their final registry digest
before publication. Compose observations may explicitly record an unavailable
registry digest alongside the actual local identity; do not invent GHCR provenance.
Projectless jobs use an existing operational record destination.

Declarative execution must verify that actual workers satisfy the resolved image/
platform contract. Code or executable mounts outside that image need explicit
identification; no silent implementation overrides. Mismatches prevent a successful
verified build, with artifacts retained for diagnosis. Exact runtime verification
mechanics remain an implementation prerequisite, not satisfied by queue naming.

## Lightweight stage provenance and Git

At task admission/start, record the task/attempt identity, effective parameters,
image observation and preceding input checkpoint when available. At the stage
boundary, commit its eligible input/configuration changes and provenance record,
including output identities, validation results and outcome. Commit metadata
must associate the project, stage, build and exact RQ task/attempt IDs; stage
names alone cannot distinguish retries.

Commit selected compact model/configuration inputs and provenance manifests.
Keep large rasters, external datasets and bulky outputs in their canonical
locations; record fingerprints and relative/resource references rather than
requiring those bytes in Git. The precise tracked path set is a first-task
contract decision. No Git LFS, alternate artifact store or network push is required.
Git still retains historical bytes for tracked changes; measure that cost.

Declarative projects do not support Bootstrap. Their local Git checkpoints are
provenance records, not Bootstrap repositories: do not expose Bootstrap enablement,
remote push, checkout or no-prep execution for these projects. Enforce this exclusion
through backend admission as well as frontend controls. Existing Bootstrap behavior
for ordinary on-demand projects remains unchanged. No Bootstrap integration or
allowlist reconciliation is required for the declarative engine.

Git snapshots identify recorded boundary state, not guaranteed consumed bytes
throughout execution. A tracked file changed and restored between checkpoints
may leave no trace. Untracked products are not preserved merely because their
hashes were committed. Do not call this strong or tamper-proof immutability.
Normal producer coordination and honest evidence labels suffice for this scope.

Receipt fields distinguish verified consumed inputs, boundary observations and
unknowns. Capture effective parameters at the task's actual resolution boundary
where practical; do not report a later NoDb reload as the settings consumed.
Record `executed`, `skipped`, or `observed/imported` disposition separately from
success/failure. Existing on-demand skips may retain their behavior, but a new
commit must not claim an old output was generated by today's task/image.
Declarative full builds do not skip model computation on the strength of legacy
project completion markers.

A task record cannot contain its own enclosing Git commit ID without circularity:
associate the resulting commit externally in execution metadata or by lookup of
its unique recorded task/attempt ID. Define handling of crashes between task
completion, receipt publication and commit; missing checkpoints remain explicit.
Serialize Git publication but do not turn commit success into scientific success.

## External resources, parameters and diagnostics

Record resource source/version where available, selection details and fingerprints
of actual consumed content where practical. URLs and mtimes alone are not content
identities. Use SHA-256 for resource/artifact manifests independently of Git's
configured object format. For large sources, identify the selected data and its
source manifest; relevant sidecars/VRT members must be accounted for or listed as
unverified dependencies. No global fingerprinting/reproducibility guarantee is
implied for unadopted tasks.

For remote acquisitions, record retrieval time (with timezone), source/request
selection, provider version or as-of time when supplied, and the retrieved content
fingerprint where available. Task execution time and data observation time are
distinct fields. Time is part of provenance when a source's answer depends on
when it is queried; a timestamp alone cannot identify the returned dataset.
Redact credential-bearing request fields.

A provider changing its dataset later does not invalidate a historical observation
or require the engine to monitor or rebuild completed projects. A later full build
records its own acquisition. If original bytes are unavailable, provenance may
explain the difference without enabling exact replay. The engine guarantees only
the recorded evidence and declared validation, not future provider availability.

Formal deterministic guarantees and scientific equality/tolerance rules are
deferred until the execution/provenance machinery is in place. Initially record
actual inputs, effective parameters, outputs and available execution evidence,
distinguishing acquisition observations and unknown dependencies honestly. A pinned
image or matching fingerprints alone must not be presented as a determinism
certification. Existing task/output validation remains required.

Library inventory, hardware and environment details are diagnostic observations,
collected with bounded cost and without secrets. Whole-image pinning identifies
the intended execution release. No per-library cache invalidation system is needed.

CLIGEN is the identified seeded computation. Record effective seed and generator
identity; verify other operations during task adoption rather than asserting a
complete seed inventory. Unresolved implicit seed behavior must remain explicit.
Do not alter on-demand random-seed defaults without separate approval.

## Deferred build comparison

Locating divergence between independent full builds remains a future goal.
Comparison algorithms, node-alignment/equality rules, scientific tolerances and
comparison interfaces are deferred until the machinery is in place; they are not
initial acceptance gates. Retain the model definition, resolved graph, task/node
associations, parameters and available input/output fingerprints as useful ordinary
provenance. Do not build a comparison subsystem or promise automatic divergence
localization in the initial engine. This deferral does not introduce incremental
rebuilding or reusable-output caching.

## Secrets and provenance failure policy

Model definitions reference authorized resources; deployment mechanisms supply
required credentials. No demonstrated need for SOPS exists. Evaluate it only if
existing delivery mechanisms cannot meet an actual encrypted-storage need. If
selected, a decryption identity would be deployment-scoped and dedicated to engine
secrets, never distributed as a model task's general credential.

Exclude secret values, secret hashes, signed URLs and credential-bearing arguments
from retained specifications, Git, receipts, logs and environment observations.
Resource fingerprints identify authorized content, not access credentials.

Accepted on-demand policy: failure to write new diagnostic provenance is visible
but preserves existing output/success behavior. This cannot weaken mandatory
batch handoff, admission or artifact-readiness receipts, even if records are
combined. Declarative completion requires its agreed stage provenance; missing
records leave an explicit incomplete/unverified outcome rather than a fabricated
history.

Accepted initial failure/recovery policy:

- If computation and output validation succeed but a required Git checkpoint or
  completion publication fails, retain outputs and the error; the declarative
  build remains incomplete. Do not automatically rerun scientific processing or
  reconstruct historical evidence from subsequently changed files.
- A scientific task exception or invalid required output prevents build success.
  Stop new scientific dispatch; dependent tasks cannot consume failed outputs.
  Already-running work may finish where safe. Failure reporting and finalization
  still run, retaining partial artifacts without claiming successful completion.
- Worker loss or uncertain execution leaves the build interrupted until its state
  is established. Engine reconnection may observe surviving work but does not
  resubmit uncertain attempts. Kubernetes worker replacement is not permission to
  execute a task twice. Keep one recovery owner across engine, RQ and Kubernetes.
- Initial recovery is an explicit full build in a fresh normal project after old
  writers have stopped. Automatic stage repair, scientific retries and checkpoint
  reconstruction are deferred. User cancellation is distinct from failure and
  never triggers an automatic restart.
- Later on-demand report failures belong to their own attempts and preserve the
  original build outcome. Existing on-demand/batch retry behavior remains intact.

Rationale: strict declarative completion and explicit recovery avoid uncertain
replay while retaining useful diagnostics and established on-demand availability.
Exact durable state transitions, failed/canceled-project read-only finalization
and crash reconciliation remain implementation contract decisions; absence of a
successful completion record must never be presented as successful completion.

## Incremental adoption and acceptance

1. Select one existing task and inventory actual reads, writes, callers and costs.
2. Ratify its compact provenance/trackable-path contract and capture baseline
   on-demand behavior, including valid skips and mandatory lifecycle receipts.
3. Add shared task/image observations and local stage commits using existing
   project/NoDb coordination. Verify unchanged scientific outputs and overhead.
4. Run the same task through the independent engine's full-build path in a normal
   newly allocated project using selected-image workers.
5. Verify image mismatch rejection, task-to-commit association, truthful consumed/
   observed labels, failure/commit interruption visibility, parallel attribution,
   and project browse/archive continuity, including a subsequent on-demand report.
   Verify read-only finalization, allowed derived writes, rejected protected writes
   through UI/API/queued tasks, and incomplete status if finalization fails.
6. Verify Bootstrap operations are unavailable for declarative projects, later
   reports and provider changes do not rewrite historical completion, and report
   runtime errors remain visible without modifying protected build state. Formal
   determinism, cross-build comparison and incremental-reuse tests are deferred.

Use real generated-input/output readback at changed boundaries and representative
identities/mounts. Broad historical fixture campaigns are outside this initiative.
No new dependency, service or storage mechanism is authorized merely by this draft.

## Remaining decision dispositions and recommendations

The following are recommended initial defaults, recorded for operator review on
2026-11-10. Previously accepted policies remain authoritative; these recommendations
are not implementation approval or evidence of conformance.

| Decision | Recommended disposition | Rationale / implementation prerequisite |
| --- | --- | --- |
| First task | Start with existing `fetch_dem_rq` in a fresh normal project, one supported source and bounded extent. | Exercises NoDb effective settings, external acquisition, raster fingerprints, RQ identity and viewing without first implementing a full watershed pipeline. Inspect actual artifact reads/writes before selecting the exact fixture. |
| Definition and execution protocol | Define only schema v1 operations needed for that slice. Use a small versioned structured request/result contract to the image-local adapter. | Defer a general workflow language, plugin system and speculative operations. Exact field names/serialization are implementation details using existing owned tooling. |
| Image admission and observation | Keep the approved-digest list in deployment version control. The engine obtains actual runtime evidence from the deployment control plane and binds task attempts to the worker/container instance. | Compare the selected platform-specific image identity with observed identity; missing or mismatched evidence prevents verified completion. Queue names or worker-supplied image strings alone are insufficient. Exclude executable/code mount overrides initially. Validate runtime evidence availability on the real cluster. |
| Git paths and publication | Use a small local provenance directory plus explicitly selected compact input/configuration files; one serialized publisher per project. | Keep raster/bulk artifacts out of Git. Capture task evidence at its boundary; commit exact owned paths. On interruption reconcile an existing commit by unique attempt identity; do not reconstruct missing historical evidence from current files or rerun science automatically. |
| Durable lifecycle | Keep a compact durable build record in the canonical project using existing NoDb/filesystem ownership patterns. Track processing outcome and finalization outcome separately. | Write verified completion last, after required evidence and read-only protection. Reconnection observes known attempts; uncertain execution stays interrupted. Do not use Redis-only state as historical authority or add a second project-state datastore. |
| Failed/canceled project protection | After writers stop, finalize retained failed/canceled projects read-only as well, preserving their original outcome. | Protect diagnostics and prevent accidental continuation. If protection itself fails, record incomplete finalization and keep ordinary mutation admission blocked by declarative lifecycle state. Never relabel failure as success merely because protection succeeded. |
| Project identity and duplicate attempts | Allocate one normal project per build invocation, retaining model definition/version, build ID and attempt IDs. Bind submission identity to one build. | A repeated submission with the same identity resolves to its existing build; a deliberate full rerun gets a new identity/project. Guard duplicate task execution; never infer exactly-once behavior from queue/job naming. Exact atomic admission mechanism is an implementation gate. |
| Resource coverage and retention | Start with the first task's supported provider. Hash fetched/selected bytes and generated required outputs, recording source selection and retrieval time. | Do not hash entire shared dataset catalogs or create a new retention store. Use ordinary project retention/archive behavior; hashes do not guarantee replay after bytes disappear. Measure hashing cost on the chosen fixture before expanding coverage. |
| Resource visibility | Preserve existing project access decisions; admit only sources whose retained content is compatible with that visibility. | Reject an unsupported private-source/visibility combination rather than inventing new per-artifact ACLs. Broader provider/upload coverage follows actual tasks. |
| Frontend and completion record | Expose declarative origin, existing read-only state and ordinary build/task outcome. Link to retained diagnostics through existing project browsing. | No new dashboard, graph UI or runtime compatibility layer. Store model/image identity, selected attempts, required products, checkpoints and completion outcome in the durable record. |
| Read-only derived writes | Inventory the first viewer/report path and explicitly authorize its bounded derived writes under the shared contract. Prepare necessary catalogs before freezing where practical. | Avoid a generic read-only bypass. Amend catalog publication rules only for demonstrated viewing requirements; verify direct APIs and queued execution as well as controls. |
| Kubernetes capacity | Keep deployment ownership in open-wepp-org, with one build-specific queue and one worker for the first individual-task slice. The engine sequences work without occupying that worker while waiting. | This default applies only after confirming that selected tasks do not enqueue children and wait. Later composites require dependency/deadlock analysis and a fixed adequate worker count. Defer pooling/autoscaling. |
| Cost budget | Measure added record, hash and commit time/storage on the first slice and retain the measurements. | Choose a numeric budget from that evidence rather than an arbitrary global threshold. Avoid whole-project rescans and bulk copies on every stage. |

For ARCH-3 / INTEGRITY-1, the proposed verifier above supplies the missing design
mechanism. The finding remains pending operator disposition and real runtime
verification; no Kubernetes API field, runtime digest equivalence or task binding
is assumed proven by this specification. On-demand Compose image observations
remain diagnostic and must honestly report unavailable registry identity.

Formal determinism, build-comparison rules, incremental reuse, Bootstrap support,
frontend compatibility machinery and broader submission access remain deferred or
excluded as specified above. Remaining field layouts, locking/publication mechanics
and task-specific artifact inventories belong in the first implementation plan;
they need not become additional architecture subsystems.

## Implementation work package

The [declarative DEM vertical slice](../work-packages/20261110_declarative_dem_vertical_slice/package.md)
scaffolds the first end-to-end implementation and cluster validation. Its active
ExecPlan is planning material; the contract checkpoint and implementation evidence
remain pending.

## Related contracts

- [Bootstrap input Git workflow](../weppcloud-bootstrap-spec.md)
- [Batch task boundary](batch-task-boundary-contract.md)
- [NoDb persistence](nodb-persistence-concurrency-contract.md)
- [RQ responses](rq-response-contract.md)
- [File dependency freshness](file-dependency-freshness-contract.md)
- [Artifact observability](../standards/artifact-observability-standard.md)
- [Generated artifact validation](../standards/generated-artifact-validation-standard.md)

## DEM v1 execution checkpoint

The [DEM v1 contract](declarative-dem-v1-contract.md) defines the bounded initial
implementation: exact fields, public fixture, operator-side runtime verifier,
visible records, lifecycle and zero-write HTTP elevation viewing. Conformance is
pending; execution authorization does not authorize deployment or establish live
identity evidence. Broader schema/source/task enrollment remains deferred.
