# Roads settings proposal checkpoint

Status: proposal reviews complete; **human specification/layout approval absent**.
This is a proposal checkpoint, not an accepted implementation ancestor. The
operator explicitly authorized defect work, bounded studies and a concrete
reviewable design in `/tmp/weppcloud_roads_revised_completion_handoff.md`.
The durable authority is [Roads adjudication](../../../schemas/roads-parameterization-adjudication-contract.md#end-user-workflow-and-closure).
That authority requires approval of both specification and layout before production
view or persistence/application wiring. Neither this completion request, AI review
nor a commit substitutes for that approval.

## Starting revision and exact proposed delta

Starting implementation: `e0308765c6da2e8ec73c88208abcb0d98bd684e8`.
The separately reviewed resolver conformance repair is `6cf8dcad6`; it fixes invalid
optional attributes and truthful provenance under unchanged intent. The particle
disposition checkpoint is `68d93809b`. Neither implements the settings editor.

Proposed canonical specification:
[Roads settings contract](../../../schemas/roads-settings-contract.md).
Proposed decision rationale:
[ADR-0135](../../../adrs/ADR-0135-roads-settings-controls.md).
Concrete [static layout](revised-settings-layout-draft.html) places five fallbacks
in the existing Roads panel: surface, traffic, width, fill length and fill slope.
Edit/Save/Cancel/Reset use the existing request path; Reset changes the local draft
until Save. Valid feature attributes retain precedence. No generated-soil policy,
scientific default, native formula or geographic buffer override is adopted.

The mapping action submits mapping only after surface/traffic fallbacks move into
the settings editor. Dirty settings drafts block adjacent mutations with inline
Save/Cancel guidance; passive summary responses cannot save or discard drafts.
Pending Save disables editor actions, and only the matching response hydrates.
These are explicit prospective client behavior changes, not existing conformance.

The exact normative changes are UI exposure/actions, additive server-owned settings
provenance, per-record execution provenance/usage presentation, and explicitly
specified malformed/null/boolean handling for the five fields. The latter is a
prospective API validation change and must be approved as such; it is not covered
by the earlier optional-feature conformance repair. All precise response, record,
valid-state and compatibility details reside in the proposed canonical contract.

## Applicable contracts and compatibility

The proposed settings contract composes Roads `specification.md`, preparation
lifecycle, modeled-area water accounting, output scope, NoDb persistence/concurrency,
CSRF, shared controller presentation and artifact-observability/generated-validation
standards. Those authorities remain unchanged except for the explicitly proposed
settings extension. Existing lifecycle locking, current-result eligibility,
retention, ordinary browse/download and archive/restore behavior remain mandatory.

Compatibility plan: preserve saved scientific values and existing templates; retain
partial API updates and unrelated parameters; add metadata without duplicate model
values or read-time migration. Keep execution manifest list shape and existing keys.
Legacy missing metadata stays explicit legacy provenance. Unknown/malformed state
must follow the exact proposed policy, not silent coercion. No result certification
from metadata. After approval, validate all downstream prepared inputs and native
artifacts, history, fork/restore and baseline isolation.

Security triage for eventual implementation: **high**, because a public mutation
route, persistence and visible artifacts are affected. No new identity, permissions,
queue, dependency or deployment topology is proposed. Independent security proposal
review cannot replace the later real authorization/CSRF/readonly/concurrency and
archive-boundary tests.

## Required review and regression evidence

Scientific evidence must establish requested/effective/emitted/consumed behavior,
actual roles/aliases/clipping, annual/event and water/sediment responses with actual
modeled area. Passing numerical checks cannot establish field calibration. The
bounded profile and disposable-project studies remain distinct from the future
browser/RQ workflow. The six reserved materials remain untouched.

Independent proposal reviews have passed with all findings dispositioned:
[science](revised-sensitivity-science-review.md),
[correctness](revised-settings-correctness-review.md),
[security](revised-settings-security-review.md), and
[UX/QA](revised-settings-ux-qa-review.md). They bind the concrete final contract,
ADR and layout; none substitutes for human approval. The full repository sanity
run remains active, while focused final helper/controller/publication gates pass. The intended
implementation milestone then requires browser -> request -> saved reload -> native
inputs -> execution -> fresh Roads reports, with reset/cancel/reload, invalid,
readonly, legacy, empty, failed, fork/restore and concurrent states. Real service
identities, mounts, umask and orchestration are required. Tests alone do not certify
artifact consumption or production parity. No deployment is authorized.

## Approval and ancestor status

Operator approval: **not obtained**. Specification approval: **not obtained**.
Layout approval: **not obtained**. Production settings implementation: **not started**.

Commit the reviewed proposal and present exact specification/layout links at the
human gate. If approved, record the explicit decision and final review dispositions,
ratify affected canonical contracts, and commit the accepted standalone ancestor
before implementation. Material subsequent contract/layout changes require review
and renewed human approval. The package remains active at this gate.
