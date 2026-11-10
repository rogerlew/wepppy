# Declarative model build specification: independent review

Date: 2026-11-10. Status: three initial reviews complete; partial design
disposition and subsequent scope revision recorded below.

Subject: [proposed specification](../schemas/declarative-model-build-spec.md).
Source inspection baseline: `da14ef8b1`; draft is uncommitted. This is a design
review, not the implementation contract checkpoint or a deployment approval.

The operator requested independent agent reviews for discussion. Three reviewers
were assigned architecture/identity, on-demand compatibility, and integrity/access.
Findings below retain reviewer recommendations separately from operator decisions.
No implementation, tests, or runtime changes are authorized by this record.

## Findings

References below identify sections in the original proposal; reviewer line
references refer to the 241-line initial draft. All are specification
clarifications for discussion, not demonstrated runtime defects.

### Architecture and identity — declarative_arch_review

| ID | Severity | Reference | Finding and proposed resolution |
| --- | --- | --- | --- |
| ARCH-1 | Medium | Responsibility boundaries; Identity; Planning (lines 42, 61, 93, 180) | Requested output selection is absent from explicit key/eligibility rules. A prior run without an optional export could match a new request needing it. Include output-affecting options in the key or require a validated superset of requested output roles. |
| ARCH-2 | Medium | Planning (lines 176, 185, 211) | Downstream keys depend on outputs that may not yet exist, so pre-execution reuse decisions cannot always be final. Define `reuse`, `execute`, and `pending upstream resolution`; update provisional decisions when upstream artifacts exist. |
| ARCH-3 | Medium | Identity; Environment; Receipt (lines 93, 123, 149, 161) | Recording selected and actual execution identity does not require agreement. Verify execution-affecting identity before reusable success; mismatch must deny reuse or create a newly resolved attempt/key. Include mounted executable overrides. |

The reviewer supports using consumed content identities rather than upstream
attempt IDs for computational keys and keeping diagnostic environment details
separate. Scheduler/storage choices remain appropriately open.

### On-demand compatibility — declarative_compat_review

| ID | Severity | Reference | Finding and proposed resolution |
| --- | --- | --- | --- |
| COMPAT-1 | Medium | Receipt; Planning (lines 146–154, 180–195) | Batch retries can skip completed work. A new receipt must not attribute retained outputs to current parameters as though newly executed. Add `executed/reused/skipped` disposition; reuse references its producer receipt. Hashing legacy output can establish observed content, not historical execution provenance. Test a retry doing no scientific work. |
| COMPAT-2 | Medium | Task contracts; Resources; Receipt (lines 70–79, 110–120, 146–159) | Before/after observations in a mutable workspace may not identify inputs actually consumed. Distinguish `consumed/verified`, `observed`, and `unknown` evidence; capture authoritative identity at the actual input boundary. Test an input-mutation interleaving without imposing blanket computation locks. |
| COMPAT-3 | Medium | Receipt failure policy (lines 161–172) | Optional provenance must not weaken mandatory batch handoff/admission/readiness receipts. Preserve their existing failure semantics even if records are physically combined. Test output success followed by mandatory handoff publication failure. |

Evidence: [batch handoff contract](../schemas/batch-task-boundary-contract.md),
`wepppy/nodb/batch_runner.py:640`, and
`wepppy/rq/wepp_rq_stage_prep.py:43` / `:87`. The reviewer supports incremental
adoption and treats task selection, backend, paths and overhead budget as open
implementation decisions rather than defects.

### Integrity and access — declarative_integrity_review

| ID | Severity | Reference | Finding and proposed resolution |
| --- | --- | --- | --- |
| INTEGRITY-1 | High | Environment; Receipt; Reuse (lines 123–127, 149, 180–181) | Same identity gap as ARCH-3: outputs could be admitted under a selected key although another image/executable/platform or parameter set executed. Require agreement and specify the verifier; changed actual identity requires a newly resolved key. Reviewer rates this High because it can contaminate reuse. |
| INTEGRITY-2 | Medium | Resources; Receipt (lines 110–113, 148–157) | Redaction does not explicitly cover exact specifications, parameters, source references and failures. Keep secret access material in separate runtime references and exclude it from ordinary retained specs, keys and receipts; hashing low-entropy secrets is not safe redaction. Resolve credential-dependent selection to authorized content identity. |
| INTEGRITY-3 | Medium | Responsibilities; Resources (lines 42, 110–127) | Image/resource identity does not authorize arbitrary execution or retrieval. Limit selection to operator-admitted releases and authorized resolvers while preserving mounts, credentials, namespaces and network boundaries. Catalog/resolver mechanics can remain open. |
| INTEGRITY-4 | Low | Identity; Receipt (lines 83–96, 149) | Blanket prohibition on hashing timestamps conflicts with receipt integrity coverage. Limit incidental timestamp/path/attempt exclusions to computational keys; hash the canonical receipt including its recorded metadata, excluding its self-digest/signature fields. |

The reviewer supports the distinction between integrity and authenticity,
dependency closure as a reuse gate, and explicit diagnostic environment policy.
Canonical encoding, resource retention and publication protocol remain legitimate
first-task gates. No additional findings were raised for those acknowledged gaps.

## Disposition

INTEGRITY-2: design direction accepted in discussion on 2026-11-10: keep secrets
out of model/provenance data and use deployment-supplied credentials; defer SOPS
until a concrete need is established. Detailed first-task field exclusions and
runtime validation remain pending; this is not implementation closure.

Scope revision, 2026-11-10: the operator explicitly accepted giving up incremental
rebuilds, deferring reuse from existing projects, and starting declarative builds
from scratch. The revised proposal uses normal canonical project directories,
existing NoDb/RQ tasks and lightweight Git stage checkpoints. It does not require
isolated copied workspaces or strong working-directory immutability. This reduces
storage/network costs and avoids reconciling alternate execution locations.

- ARCH-1's reuse-eligibility issue and ARCH-2's provisional cache planning are
  superseded by full builds. Requested output completeness remains a task contract.
- INTEGRITY-4's computational-key rule is superseded by removal of cache keys;
  exact manifest encoding remains an implementation detail to specify.
- COMPAT-1's legacy adoption path is deferred. Honest attribution of existing
  on-demand skipped work remains required.
- COMPAT-2 remains relevant: Git checkpoints establish recorded boundary state,
  not proof of all consumed bytes or absence of intervening mutations. The draft
  distinguishes consumed, observed and unknown evidence without requiring strict
  immutable snapshots.
- ARCH-3 / INTEGRITY-1 remain applicable to verified full-build execution even
  without reuse. COMPAT-3 and INTEGRITY-3 also remain applicable.

These are scope dispositions, not implementation closure or a new independent
review of the revised proposal. Tracked paths, existing Bootstrap compatibility,
concurrent stage attribution and interrupted commit publication remain open.

Provenance boundary discussion, 2026-11-10: operator requires declarative projects
to support subsequent on-demand frontend/report tasks. Build guarantees end at
the declared graph/products and completion checkpoint; later work retains its own
attribution without rewriting historical completion. Remote source changes do not
trigger retroactive provenance invalidation or an engine monitoring obligation.
Acquisition time and returned content describe external observations; individual
transformation contracts may establish deterministic input/output guarantees.
Independent full builds should be comparable by stable logical graph nodes to
locate evidenced divergence, without reintroducing incremental reuse.

This refines COMPAT-1/COMPAT-2's intended accuracy contract: truthful historical
and subsequent attribution, with explicit observation/consumption evidence and
task-specific reproducibility scope. Exact record fields, comparison rules,
frontend presentation and runtime validation remain implementation prerequisites.
No further independent review or implementation verification is claimed by this
discussion update.

Failure-policy disposition, 2026-11-10: operator accepted the recommendations.
COMPAT-3 is design-dispositioned: optional diagnostic provenance failures preserve
existing on-demand success behavior, mandatory handoff/admission failures retain
their semantics, and missing required declarative evidence prevents verified
completion. Retain outputs on checkpoint failure; stop new scientific dispatch
after required-stage failure; preserve safe running work and failure reporting;
use explicit full-build recovery after old writers stop, without automatic stage
replay. Cancellation remains distinct and later report failures do not change the
historical build outcome. Implementation and validation remain pending.

Read-only finalization direction, 2026-11-10: operator requires lightweight
declarative-aware frontend/views and finalization through the shared project
read-only contract. That contract must permit on-demand report/view processing
while protecting model state, build products and historical records. This replaces
the earlier suggestion that ordinary post-build edits are part of the supported
declarative workflow. Allowed derived writes need explicit contracts and backend
enforcement; report labels alone do not authorize mutation. Existing query-catalog
read-only publication restrictions must be reconciled before implementation.
Finalization protection failure prevents successful build completion. Protection
of failed/canceled projects and exact transition ordering remain to be specified.

Access-authority disposition, 2026-11-10: operator accepted the recommendations.
INTEGRITY-3 is design-dispositioned: deployment-controlled configuration approves
exact image digests and schema/protocol compatibility; initial submission is
operator-only; deployment owns mounts, service accounts, credentials and worker
commands. Resource access uses named datasets, supported providers and explicitly
supported uploads through existing access mechanisms. Private-source visibility
must be preserved. Later report requests retain existing access/feature checks and
the shared read-only permitted-write contract without engine mutation privileges.
No separate catalog service, identity system or general resource-policy framework
is required. Exact formats, supported-source mapping and enforcement validation
remain implementation prerequisites, not unresolved policy alternatives.

Scope simplification, 2026-11-10: operator excludes Bootstrap support for
declarative projects, including enablement, remote push, checkout and no-prep
execution. Local provenance Git does not imply Bootstrap support; ordinary
on-demand Bootstrap behavior is unchanged. Earlier integration/coexistence
prerequisites are superseded. Formal deterministic guarantees and cross-build
comparison rules/interfaces are deferred until the machinery exists; retain
ordinary provenance without making these initial acceptance gates. Frontend/report
runtime compatibility is best effort: accept visible runtime errors and patch
encountered incompatibilities, without a compatibility layer, negotiation,
migration or historical-image renderer selection. This supersedes the earlier
serving-runtime compatibility prerequisite, while preserving image/schema admission,
read-only protection and accurate attribution of later tasks.

ARCH-3 and INTEGRITY-1 describe one issue with different reviewer severities;
retain both assessments pending discussion. Suggested discussion order:
execution identity and admission authority; consumed/observed/skipped provenance;
on-demand versus mandatory receipt failures; stage checkpoint semantics;
redaction and encoding clarification. This order is not a disposition.

## Remaining-decision recommendation pass

Implementation venue, 2026-11-10: operator selected the open-wepp-org cluster for
the implementation and first-slice validation. Use that deployment's existing
mechanisms and production-equivalent runtime evidence. Initial production
wepp.cloud rollout is outside scope; no cluster changes were made in this discussion.

On 2026-11-10 the operator requested dispositions and recommendations for remaining
decision points. The specification now records recommended defaults separately
from accepted policies: a DEM acquisition slice, minimal v1 protocol, deployment-
observed worker image identity, serialized local checkpoints, durable project
lifecycle records, protection of failed/canceled projects, one project per build,
bounded source coverage and existing access/retention mechanisms, lightweight UI,
explicit derived-write permissions and fixed first-slice worker capacity.
ARCH-3 / INTEGRITY-1 has a proposed concrete verifier direction but remains pending
operator disposition and deployment evidence. No new independent review or runtime
verification was performed. Exact schemas and execution mechanics remain first-
implementation-plan work, not implicit authorization for new subsystems.

## Validation and review limits

Schema discussion, 2026-11-10: operator accepted exactly one model-schema version
per execution image, exact admission matching, and explicit model upgrades.
Multiple image releases may implement that schema; image digest still identifies
the implementation. Original definitions and image associations remain retained.
The engine execution protocol is separately versioned. This resolves the schema
compatibility direction, not runtime identity verification or catalog authority.

Execution discussion, 2026-11-10: operator confirmed open-wepp-org Kubernetes as
the declarative deployment, Compose for current wepp.cloud, and a long-term RKE
direction for production. All project RQ attempts should retain actual image
observations for investigation in either mode. Operator proposed schema-versioned
image compatibility; the draft distinguishes compatible schema from trusted
execution admission and proposes an approved digest-to-contract catalog.
At that discussion, INTEGRITY-3 remained open for catalog authority and resource-
resolver policy (subsequently dispositioned above);
ARCH-3 / INTEGRITY-1 remain open for the concrete observation/verification rule.
Existing open-wepp-org worker manifests were read and already pin GHCR digests;
no deployment resources or the infrastructure repository were changed.

Priority discussion, 2026-11-10: operator chose simplicity and reliability over
speed. Initial proposal now favors dedicated per-build queues/workers, fixed
capacity, conservative image identity and explicit recovery ownership. Pooling,
autoscaling and cross-image reuse optimization are deferred. Exact worker count
must follow dependency/deadlock analysis; this update does not close the existing
identity verification findings or authorize deployment.

Execution discussion, 2026-11-10: operator selected whole GHCR execution-image
identity, explicit image compatibility, and Kubernetes containers executing all
build RQ tasks. The spec records this direction and proposed build-queue/worker
bootstrap, leaving queue granularity and compatibility schema open. ARCH-3 /
INTEGRITY-1 remain open for exact actual-versus-resolved verification rules;
selecting an image alone does not prove that every descendant ran in it.

Earlier discussion, 2026-11-10 (superseded by the SOPS deferral above): for
INTEGRITY-2, the operator proposed SOPS with
a deployment-scoped private key dedicated to engine secrets. The specification
now records this candidate and a proposed separation of secret handles, encrypted
storage, restricted runtime delivery and provenance redaction. SOPS adoption,
key mechanism, rotation/recovery and delivery details remain open. INTEGRITY-2
is not closed: encryption at rest alone does not resolve decrypted-data exposure.
Original review line references refer to the initial draft, before this addition.

All reviewers were independent read-only agents. No tests, deployments or
implementation edits were performed. The proposal and review record pass scoped
`wctl doc-lint`; spelling normalization was previewed for the proposal. User
ratification, implementation checkpoint, exact schemas and runtime validation
remain future work.
