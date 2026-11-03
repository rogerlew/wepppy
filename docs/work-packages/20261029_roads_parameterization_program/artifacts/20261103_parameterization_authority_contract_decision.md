# Roads repository/project parameterization contract decision

Status: **accepted contract-first checkpoint, 2026-11-03**. The operator explicitly
approved the reviewed replacement specification and dedicated layout at `9532a2968`:
"I approve. please proceed with implementation". Independent reviews bound to
ledger v39 precede this ratification. No normative behavior changes in this status
commit. Starting implementation revision: `9532a2968`; current branch preserved.

## Authority and intended outcome

The operator requested explicit driver overrides, their own view, transparent
source/adjustment/native values, Roads-owned authoritative project state, and
contractual repository defaults/project parameters. The current instruction is to
make the necessary documentation changes and execute. These directions authorize
concrete design, bounded studies and independent reviews. The handoff and
[adjudication](../../../schemas/roads-parameterization-adjudication-contract.md#end-user-workflow-and-closure)
explicitly retain human approval of the actual specification and layout before
production persistence/application/UI wiring; no replacement layout was previously
approved. Do not turn agreement to ownership into approval of unseen details.

## Applicable contract matrix

| Canonical document | Exact delta or retained obligation |
| --- | --- |
| [Repository baseline](../../../schemas/roads-parameterization-baseline-contract.md) | New explicit 18-asset authority, full four-driver matrix, selection/traffic/management/fragment/native rules and change control |
| [Project/view](../../../schemas/roads-settings-contract.md) | Replaces five-field proposal; NoDb schema, retained content, role overrides, validation, transport, dedicated view and provenance |
| [ADR-0135](../../../adrs/ADR-0135-roads-settings-controls.md) | Revised proposed decision, alternatives, compatibility and risks |
| [Adjudication](../../../schemas/roads-parameterization-adjudication-contract.md) | Links two distinct default/project authorities; human gate unchanged |
| [Preparation lifecycle](../../../schemas/roads-preparation-lifecycle-contract.md) | Proposed parameterization identity participates in existing admission/invalidation; legacy read does not migrate |
| [Roads specification](../../../../wepppy/nodb/mods/roads/specification.md) | Links baseline authority; corrects false blanket 200 mm no-op description |
| [NoDb persistence](../../../schemas/nodb-persistence-concurrency-contract.md) | Unchanged single durable owner, refresh-under-lock, atomic persistence/cache rules |
| [CSRF](../../../schemas/weppcloud-csrf-contract.md), [controller](../../../ui-docs/controller-contract.md) | Existing auth/CSRF/readonly/error/draft/request ownership apply to new view and payload |
| [Output scope](../../../schemas/output-scope-contract.md), [artifact observability](../../../standards/artifact-observability-standard.md) | Baseline independence and visible failed/historical/readback evidence retained |

## Exact proposed behavior and rationale

A single new `_parameterization` in `roads.nodb` retains all 18 baseline source
texts, hashes, deterministic identity and resolver version, plus four driver entries
for each template-owned role. Existing `_roads_params` remains physical/mapping
state. Overrides default/multiply/absolute apply after traffic, never twice.
Raw restored content is validated before parser normalization/materialization;
positive native-representable parameters cannot become zero estimation sentinels.

Retained text occupies 167705 bytes before JSON overhead; this avoids a separate
mutable CSV/file transaction and survives repository template replacement. No
native executable or Python implementation is embedded in state. Versioned resolver
interpretation must remain supported. Default-only writer parity is evidenced by
168 cases and336 byte-identical soil/management pairs, not a new defaults policy.

The dedicated view separates saved intent, unprepared preview and actual emitted
readback. Mixed groups expose differing template resolution; role-wide overrides
do not alter unrelated upstream landuse. Reset removes overrides against the
bound baseline. New-baseline adoption is explicitly outside version 1 functionality.

## Compatibility and regression plan before schema changes

No production schema is changed by this checkpoint. Future implementation adds
fields without removing old settings or wrapping the existing manifest list.
Unbound legacy reads do not write. First Save binds submitted validated overrides;
first Prepare binds defaults. Already-prepared unbound projects require Prepare
before a new Run, while completed historical viewing remains available. Native
soil/management assembly occurs during Run, so geometry Prepare alone cannot
populate actual emitted values. This is a documented compatibility delta for review.

The former five-field validation tightening and metadata-only record are withdrawn.
Current source baselines, shared Disturbed defaults, baseline outputs and binary
identities remain unchanged. Postapproval regression work must exercise all writer
paths, role-specific input readbacks and failure/no-op cases, actual persistence,
cache/concurrency, browser requests, Prepare/Run admission, fork/archive/restore,
report freshness and production-equivalent identities/mounts. Isolated artifact
parity and static render tests do not certify these future boundaries.

## Security impact and review scope

New attack surface is an authenticated view, nested overrides and persisted source
content. Reuse existing authorization/CSRF/readonly protections; reject client
baseline contents/paths. Validate exact allowlist, bytes/counts, raw numeric fields,
formats, role markers and self-consistent hashes; use contained fresh paths and
escaped display. Hashes are integrity evidence, not trust. Explicit repair is
limited to invalid states and all-default replacement; it cannot bypass adoption.
Absent/disabled GET remains nonmutating and valid enabled first-use initialization
is explicit. Dedicated security review assesses these proposal contracts, not an
unimplemented runtime boundary.

## Evidence and remaining gate

- [Source inventory](parameterization-baseline-inventory.json) and
  [scientific/source review](parameterization-baseline-science-review.md).
- [Embedded-baseline prototype](parameterization-binding-results.md) and
  [independent correctness readback](parameterization-contract-correctness-review.md).
- [Override protocol](parameterization-overrides-protocol.md) and
  [protocol review](parameterization-overrides-protocol-review.md); retained raw
  root is `/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1`.
- [Dedicated layout](parameterization-view-draft.html),
  [design notes](parameterization-view-notes.md), and
  [UX review](parameterization-view-ux-review.md).
- [Security/noninterference review](parameterization-security-review.md).

Ledger v39 records exact hashes and final review results. All 18 native profiles
passed declared checks and independent readback; response evidence is limited to
road overrides in one climate/texture/surface/traffic and two geometries. Human approval
of both replacement specification/layout is the remaining prerequisite for
ratification and production implementation. Program remains active; no deployment,
default adoption, reserve-material use or real-project regeneration occurred.

## Approval ratification

The later explicit approval above satisfies the prerequisite described in the
historical proposal rationale. Proceed with implementation after this standalone
checkpoint commit. No further specification/layout approval is needed for faithful
implementation. Material contract changes require their applicable review; routine
implementation choices do not reopen approval. Program completion still requires
real workflow validation and independent final reviews. Deployment is not authorized.
