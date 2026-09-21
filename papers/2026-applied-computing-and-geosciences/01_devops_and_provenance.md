# Paper scope: operation, provenance, and two execution modes

> Editorial decision: Roger Lew, 2026-09-21. This is the current scope authority
> for this manuscript; it supersedes the June feature-centered outline where
> they conflict. Architecture below is a research direction, not an implemented
> backend contract or authorization to change production.

## Thesis and rationale

An evolving interactive watershed-modeling service and a replayable scientific
experiment have different lifecycles. WEPPcloud should retain its on-demand
experience while a secondary declarative backend provides stricter provenance
and replicability. The paper connects operational lessons to this distinction:
responsive execution, portable state, controlled deployment, and evidence of
what actually produced a result.

A project can begin under one software revision and continue under another.
Users change parameters, rebuild selected inputs, and inspect new results.
Consequently, a project creation commit or the currently deployed image cannot
by itself identify the dependencies of every retained result. The central unit
of provenance should be the individual execution and its consumed artifacts.

**Clarification (Roger, 2026-09-21):** interactivity makes reproducibility and
provenance substantially more challenging. Parameter changes, selective reruns,
retained intermediate files, and projects spanning deployments complicate both
reconstructing execution history and enforcing consistent pipeline dependencies.
The tension is practical and architectural; the claim is not impossibility.
The proposed separation preserves the existing user workflow while assigning
different provenance and replication goals to the two execution modes.
Requiring all users to work exclusively through frozen batch specifications was
rejected because exploration and rapid parameter adjustment remain core needs.

## Interactive provenance goal: job to container to source

For any interactive job, identify the container that actually executed it and
its immutable image digest. Container metadata should identify versions across
the entire software stack so that the corresponding source can be retrieved
and reviewed. The [stack map](../../docs/weppcloud-stack.md) defines the starting
inventory: application and orchestration code, Python/Rust components, terrain
and climate tools, model executables, and supporting runtime dependencies.
Account for separate service containers when a job delegates execution.

The intended chain is **job -> executing container/image -> stack version
metadata -> retrievable corresponding source**. Repository identities and exact
revisions must describe the packaged components, including vendored binaries;
the WEPPpy commit alone is insufficient. Build/runtime dependency versions and
binary identities are needed to connect source review to the executed stack.
Metadata must describe what actually ran, including any code supplied outside
the image. A deployment's current desired state is not a historical job record.

This is the interactive mode's software-provenance goal, not a claim that every
interactive project will have an enforced, replayable dependency graph. It lets
a reviewer inspect the software responsible for each job while preserving the
user's freedom to explore. The declarative mode adds runtime pinning and enforced
pipeline dependencies to pursue stronger replicability guarantees.

The stack document is a source inventory, not a deployed-version attestation.
Its existing WEPP binary sidecars provide a component-level precedent; the
document explicitly distinguishes them from a complete image provenance
manifest. Whole-stack metadata and universal job association remain goals to
verify, not capabilities established by that inventory.

## Two papers

| Paper | Main question | Included evidence |
| --- | --- | --- |
| This paper: operations and provenance | How can a continuously evolving modeling service support responsive exploration and rigorously specified executions? | Operational pressures, service/state boundaries, Talos experience, deployment control, execution provenance, replay experiments when available |
| [Companion feature paper](../2026-weppcloud-scenarios-and-contrasts/00_planning.md) | How do scenarios, contrasts, and interactive analysis support watershed decisions? | OMNI methods, comparison semantics, dashboard/analysis workflows, scientific case study |

OMNI implementation detail, contrast methods, feature screenshots, and the
scenario-efficiency evaluation move to the companion paper. This paper may use
scenario fan-out as a workload characteristic without developing the feature
contribution. Keep each paper independently understandable and avoid presenting
the same evaluation as two separate contributions.

## Evidence status as of 2026-09-21

| Subject | Status and manuscript treatment |
| --- | --- |
| WEPPcloud on-demand service | Existing system; audit exact source revisions and retained telemetry before quantitative claims |
| Interactive job/container/stack/source association | Required direction established 2026-09-21; audit existing coverage and gaps before claiming universal tracking |
| Bare-metal Talos cluster and Flux | Documented in `open-wepp-org`; its roadmap records completed infrastructure and public WEPPcloud deployment, with application validation and performance work still open |
| Production `wepp.cloud` migration to RKE2/GitOps | Operator-stated direction; migration and benefits are not demonstrated results |
| Declarative modeling as digest-pinned Kubernetes Jobs | Proposed secondary backend, resembling batch; implementation and replay evidence remain outstanding |
| Cryptographic dependency tracking | Proposed execution requirement; do not imply that current run archives already provide complete dependency closure |

Local source map (sibling repository; not publication citations):

- `open-wepp-org/docs/planning/open-wepp-org-deployment-roadmap.md`:
  milestone status and links to operational evidence.
- `open-wepp-org/docs/planning/weppcloud-deployment-architecture.md`:
  application/runtime boundaries and preservation of Compose deployments.
- `open-wepp-org/docs/decisions/0001-github-centered-gitops-with-flux.md`:
  separation of image build and deployment authority.
- `open-wepp-org/docs/planning/weppcloud-performance-optimization.md`:
  measured storage and execution constraints; retain experiment scope when citing.

Talos at `openwepp.org` and the intended RKE2 production deployment are distinct
environments. Do not collapse them into a completed migration story. Before
submission, retain the source commits and specific evidence artifacts used for
each claim. The earlier published reference is Lew et al. (2022); this ACG
manuscript remains a draft.

## Proposed execution boundary

The secondary backend accepts an explicit experiment specification, resolves
and enforces its pipeline dependencies, and executes a fixed image as a Kubernetes Job. An execution
record should bind the specification, image digest, consumed data, generated
model inputs, and outputs. This is a minimum research target, not a selected
manifest schema, hashing algorithm, storage service, or queue redesign.

Distinguish three records:

1. **Deployment record:** desired-state revision and deployed image identities.
2. **Experiment record:** resolved parameters and defaults, data content hashes,
   preprocessing/model dependencies, random seeds where applicable, and the
   relationships between these inputs.
3. **Execution record:** actual runtime/image identity, relevant hardware and
   numerical settings, attempts and completion, consumed input hashes, output
   hashes, and semantic validation results.

Image pinning must use a digest, not only a mutable tag. An image digest does
not identify data fetched from an external API or supplied by a mounted volume.
Hash the actual consumed artifacts, including generated model-input files;
retain the bytes or a demonstrated retrieval mechanism. A hash identifies
content but cannot recover missing content, prove scientific correctness, or
authenticate its author. Signing/attestation is a separate decision if origin
authentication becomes a requirement.

Inputs prepared under an older revision must retain that lineage. Running
those inputs in a new pinned image does not retroactively make their preparation
part of that image. Distinguish replay from prepared inputs from reconstruction
of the full acquisition/preprocessing/modeling pipeline.

Treat exporting an interactive project into a frozen experiment as a candidate
bridge to evaluate, not an existing feature or an agreed implementation. Once
frozen, changed parameters or dependencies identify a new experiment revision.

## Evaluation and claim limits

Use a representative watershed for a bounded execution study:

- Continue an interactive project across two revisions; inventory which result
  dependencies the current records establish and which remain ambiguous.
- For jobs on either side of a deployment change, resolve the actual executing
  image and stack metadata and retrieve corresponding component source. Check
  delegated service execution separately from the submitting worker.
- Execute a frozen specification twice under the same declared environment;
  compare actual model inputs and scientific outputs.
- Replay on another worker, then across a deployment update while retaining the
  selected image; record hardware, threading, and other relevant differences.
- Change one parameter or input; show that dependency tracking distinguishes
  the changed execution and identifies affected products.
- Supply a mismatched or unavailable dependency; show explicit rejection or
  failure before claiming a valid scientific result.
- Measure capture, storage, verification, and execution overhead alongside the
  operational cost of retaining old images and data.

Define terms explicitly in the manuscript. Separate byte-identical replay,
numerical agreement within declared tolerances, and independent scientific
replication. Tolerances must follow the scientific quantities and numerical
behavior; do not infer them after observing discrepancies. Successful scheduling
or a matching output hash alone cannot validate scientific meaning.

If the backend is not implemented and evaluated before submission, keep it in
discussion/future work and ground the title, abstract, and conclusions in the
demonstrated operational system. If replay becomes a central evaluated
contribution, revisit the application-article choice and rebalance the outline.
Do not make completion of the RKE2 migration a prerequisite solely for the paper.

## Literature positioning

The contribution must be the operational problem, execution boundaries, and
evidence. Containerization, Kubernetes, and GitOps alone are not novelty claims.
[eWaterCycle](https://gmd.copernicus.org/articles/15/5371/2022/) combines
interactive notebooks and containerized hydrological models. This does not
resolve the tension: a notebook interface alone does not enforce pipeline
dependencies, and model containerization alone does not establish immutable
pinning of the complete experiment runtime. Distinguish model-image selection
from pinning notebook execution, orchestration, preprocessing, and model code
together with their dependencies.

Roger identifies absent runtime pinning as an additional comparison point.
The inspected [system setup documentation](https://ewatercycle.readthedocs.io/en/latest/system_setup.html)
uses a Conda lockfile downloaded from `main`, followed by unversioned installation
commands for eWaterCycle and its plugins; model-image examples use tags.
Thus the documented setup includes some dependency locking but does not specify
one immutable, experiment-bound identity for the whole runtime. This is the
supported comparison, rather than an assertion that no version pinning exists.
Evaluate mandatory guarantees, not just whether a user can manually select
versions. Before publication, pin the
eWaterCycle release/source under review and verify what is enforced. Do not
turn the absence of a demonstrated whole-runtime guarantee into a blanket claim
that eWaterCycle cannot select model versions or be configured reproducibly.
[Kubernetes image documentation](https://kubernetes.io/docs/concepts/containers/images/)
distinguishes immutable digests from tags. Revisit the existing bibliography's
eWaterCycle, Galaxy, Pegasus, and A-KBS entries against the revised scope before
making comparative claims.
