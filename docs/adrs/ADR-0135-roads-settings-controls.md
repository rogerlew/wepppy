# ADR-0135: Roads-owned parameterization and dedicated view

Status: **accepted 2026-11-03; implementation pending**. Operator approval applies
to the replacement specification and dedicated layout at `9532a2968`. This replaces
the former five-fallback editor proposal; its text remains historical evidence.

## Decision provenance

Decision venue: operator/Codex task conversation, 2026-11-03, operator timezone
America/Los_Angeles. Decision owner: Roger Lew. Implementer: Codex after review and
human specification/layout gate. The operator explicitly requested driver overrides,
a dedicated view, a Disturbed-like lifecycle, authoritative project state written
with Roads, and contractual repository defaults. The operator subsequently stated "I approve. please proceed with implementation"
after the reviewed replacement specification/layout were presented at9532a2968.
The explicit human gate is satisfied; deployment remains separate.

## Proposed decision

Repository baseline authority consists of bundled Roads soil/management templates
and the documented selection/assembly rules, as specified in the
[baseline contract](../schemas/roads-parameterization-baseline-contract.md).
Project authority is one additive `_parameterization` object in `roads.nodb` with
schema version, retained baseline contents and role-scoped overrides. The existing
`_roads_params` remains authoritative for existing physical/mapping settings.
The [project/view contract](../schemas/roads-settings-contract.md) defines exact
keys, precedence, lifecycle, transport and valid states.

Retain all current template texts and hashes inside the NoDb baseline, bound to
resolver version1 and a deterministic manifest identity. This lets an old project
reproduce its baseline after repository changes without a separate mutable CSV or
multi-file configuration commit. Copies emitted for execution are derivatives.
Read-only access never enrolls legacy projects. First explicit Save/Prepare binds
the baseline; subsequent operations retain it. Reset removes overrides against that
baseline; adoption of newer repository defaults is a separate future operation.

Expose default/multiply/absolute overrides for baseline conductivity, Ki, Kr and
critical shear, separately for template-owned road/fill/buffer roles. Apply after
ordinary template and traffic adjustments, before native serialization. Positive
finite native-representable values are required; zero is a native estimation/bypass
sentinel, not an off switch. Retain source values and distinguish input validity,
study coverage and calibration claims. No universal response direction or arbitrary
field-calibrated range is asserted.

The dedicated view shows source -> adjustments -> override -> emitted values,
including mixed-template groups and role applicability, plus actual compatible
run comparisons. Existing Roads lifecycle guards, NoDb locking, auth, CSRF,
readonly, history and baseline-output isolation apply. Save invalidates Roads
preparation/results and requires explicit Prepare/Run; it never implicitly reruns.

## Exact delta and compatibility

Currently Roads stores ordinary settings and reads live repository templates during
assembly. Users cannot independently override these native drivers. After approved
implementation, bound projects use retained templates and saved driver overrides.
Default-only generation must match current production output bytes across supported
branches. No scientific default, native formula, binary, source soil, shared
Disturbed table or baseline WEPP output changes in this proposal.

Add schema and request fields without removing existing keys. Existing unbound
projects remain readable and historical results remain governed by current lifecycle
admission. Additive provenance records distinguish legacy/unbound data from actual
bound readback. An already-prepared unbound legacy project must explicitly Prepare
before a new Run can bind to the new configuration; historical result viewing is
preserved. This one-time Run preflight change is part of the approval scope.
Geometry preparation and native soil/management assembly during Run are separate
phases; the view must not claim native input readback after geometry preparation. The old proposed five-field API tightening and metadata-only object
are withdrawn; ordinary API behavior remains unchanged outside the new payload.

## Rationale and alternatives

The user needs controllable physical drivers, not just geometry fallbacks that may
be unused or alter modeled area. Native Ki/Kr/shear and conductivity have traceable
consumers. Separate role controls avoid a blanket change to unrelated landuse soils.

Reject editing generated `.sol`/`.man` as the authority: preparation would overwrite
intent. Reject a second editable CSV: it splits project configuration across mutable
stores. Disturbed provides a lifecycle analogy, not a requirement to duplicate its
CSV storage. Reject repository-only hashes: they detect drift but cannot recover
old content. Reject copying executable Python into state: bind a supported resolver
version instead. Reject automatic rebase/reset-to-latest: it changes saved projects.
Reject a generic optimizer or output multiplier: neither supplies the requested
transparent input parameterization. No new dependency, queue or service is needed.

## Evidence and validation

The [baseline inventory](../work-packages/20261029_roads_parameterization_program/artifacts/parameterization-baseline-inventory.json)
binds all18 template assets, role values and source/native identities. Source audit
shows zero estimation sentinels, traffic Ki/Kr adjustment and management coupling.
The existing 47-profile/four-project studies characterize geometry/traffic; they do
not certify the new overrides. New bounded override and retained-baseline prototype
results must be independently reviewed before the replacement approval request.

After approval, required evidence includes default byte parity, actual Roads NoDb
persistence, all native writer paths, actual input readback, mixed-role no-op checks,
invalid atomic saves, lifecycle invalidation, fork/archive/restore, and browser to
native to fresh report propagation under production-equivalent identities/mounts.
Independent scientific, correctness, security and UX reviews are required. Static
prototype and isolated native runs do not substitute for implemented workflow proof.

## Risks and rollback

Extreme input values or coupled processes can fail native execution or produce
unhelpful responses even when parser-valid; preserve failures and never publish
incoherent results. Retained templates enlarge the NoDb payload modestly; prototype
roundtrip/size evidence must be retained. Resolver versions require ongoing support
for bound projects. Unknown versions or corrupt content fail explicitly rather than
silently adopting defaults. Plain-text rendering and strict materialization allowlists
prevent saved source content from becoming executable markup or arbitrary file paths.

Rollback of a future implementation must preserve saved state and historical
artifacts, avoid interpreting new state as old defaults, and disable unsupported
execution explicitly. No deployment or old-state migration is authorized here.
