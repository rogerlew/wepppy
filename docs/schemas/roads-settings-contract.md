# Roads parameterization project and view contract

Status: **revised proposal; implementation pending; replacement specification and
layout not yet approved**. Operator-approved direction is a default-settings
harness, explicit driver overrides, a dedicated view, and authoritative project
parameterization written with Roads. The exact schema/layout below require the
explicit gate in [adjudication](roads-parameterization-adjudication-contract.md#end-user-workflow-and-closure).
This replaces the five-fallback-only and inline-editor proposal, whose reviews
remain historical evidence at commit `8b02c5fb1`.

## Operator clarification: default settings and user overrides

Users must be able to adjust key runoff and sediment drivers toward observations
or expectations without changing physical geometry merely to tune outputs.
Observations and expectations are different targets; matching either does not
establish physical validity. This is a default-settings and override harness,
not an automatic calibration optimizer. Lack of field calibration does not exclude
an otherwise supported driver. Existing numerical findings and study limits remain
visible; no default adoption, generated-soil policy adoption or deployment follows.

## Contract authorities

The [repository baseline contract](roads-parameterization-baseline-contract.md)
defines default assets, values, units, selection, transformations and native
consumption. This contract defines project state, overrides, lifecycle and view.
The [Roads specification](../../wepppy/nodb/mods/roads/specification.md),
[preparation lifecycle](roads-preparation-lifecycle-contract.md),
[NoDb persistence](nodb-persistence-concurrency-contract.md),
[CSRF](weppcloud-csrf-contract.md), [output scope](output-scope-contract.md),
[artifact observability](../standards/artifact-observability-standard.md), and
[controller contract](../ui-docs/controller-contract.md) remain applicable.
[ADR-0135](../adrs/ADR-0135-roads-settings-controls.md) records this proposed delta.
Conflicts must be resolved before implementation, not hidden in a builder.

## Parameterization ownership and lifecycle

`Roads` owns authoritative project parameterization in `<wd>/roads.nodb`, under
new additive `_parameterization`. Existing `_roads_params` continues to own geometry,
surface/traffic/texture fallbacks, mapping and other existing settings. The new
object must not duplicate these values. One Roads transaction serializes both;
the UI, exports, caches and generated files are consumers, not parallel authorities.

Disturbed is a lifecycle analogue, not an identical storage model: its controller
state is in `disturbed.nodb`, while its editable lookup is a project-local CSV.
Roads does not add a second editable CSV or mutable defaults table.

### Saved schema version 1

`_parameterization` contains exactly these fields:

| Key | Shape and meaning |
| --- | --- |
| `schema_version` | Integer `1`, server owned |
| `baseline` | Server-owned retained baseline object below |
| `overrides` | Object with `road`, `fill`, `buffer`; each contains the four parameter entries below |

`baseline` contains `id` (repository baseline identifier), `resolver_version`
(integer `1`), and `assets` (object keyed by allowlisted relative template paths
`soils/<name>.sol` and `managements/<name>.man`). Every asset contains exact UTF-8
`text` and lowercase `sha256` of its UTF-8 bytes. Retain the complete current set
of bundled templates, including both management choices and all textures/designs,
so a later existing surface/traffic/design change does not need a newer repository
asset. The baseline identifier binds the ordered path/hash manifest and the
resolver version; identical content must have identical identity. Exact encoding:
SHA256 of UTF-8 JSON with sorted keys, separators `,` and `:`, containing
`resolver_version` and `assets` mapped from relative path to hash; prefix the hex
with `roads-legacy-v1-`. No absolute path, executable code or client-supplied asset
content belongs in this object. Validate baseline identity by recomputation and
require exactly the 18 paths enumerated in the baseline contract (16 soil, two
management files); reject missing/extra names, aliases, absolute paths and traversal.
Do not derive allowed names from a client payload or restored manifest.

Preserve the first resolver's interpretation when introducing a later resolver;
unsupported versions fail explicitly rather than silently using current formulas.
A baseline hash detects content changes but cannot restore content: retaining the
small template text set in the same NoDb payload makes persistence atomic and
archive/fork self-contained. Generated temporary copies are disposable derivatives.
Do not execute source text or load arbitrary paths from the baseline.

Restored NoDb is an input boundary, even when hashes are self-consistent. For
resolver version 1, accept only UTF-8 plain text without NUL, with each asset at
most 256 KiB and total embedded text at most 1 MiB. These are storage/parser limits,
not parameter ranges; current assets total 167,705 bytes, with largest 77,824 bytes. This margin permits
retained historical comments without unbounded parsing; future expansion requires
a contract amendment. Parse soils using the owned soil parser and require
the 98.4 format, three expected source role records and supported horizon shapes;
validate raw soil numeric fields before any permissive parser normalization, and
require the exact fragment marker by source role (`urr`, `ufr`, `ubr`). A parser
that preserves strings or substitutes saturation/texture values does not prove
validity. Disable erodibility/conductivity computation while parsing retained
baseline text; retain explicit source numbers. Parse management using the owned management parser and require the supported
version 97.3 and three-OFE template structure (the owned legacy parser, not its
98.4-only strict-upload mode). Reject malformed/nonfinite native
fields before any materialization. Hashes prove integrity, not trusted origin.
Do not use an external path embedded in a native text file. Materialize only fixed
allowlisted basenames inside an owned fresh Roads scratch directory; refuse
symlinks/path escapes and never overwrite baseline or unrelated run inputs.

### Legacy and first-use binding

An absent `_parameterization` is a supported legacy state, not corruption.
Read-only display computes a clearly labeled **unbound repository preview** and
performs no persistence, input regeneration or old-result invalidation. Existing
completed results retain their existing eligibility; new provenance is unavailable
for historical runs. The first explicit parameterization Save or Prepare binds the
current repository baseline within the Roads mutation lifecycle. First Save binds
the submitted validated overrides atomically; first Prepare binds default entries
when no saved overrides exist. Prepare records the binding before generating parameterized artifacts;
a failed subsequent preparation retains the binding and explicit failure evidence.
Existing bound projects never refresh their baseline merely on read or preparation.
A legacy already-prepared unbound project must Prepare before a new Run; reject
Run preflight with that actionable instruction, preserving completed historical
result viewing. This is an intentional one-time compatibility delta, not a claim
that existing Run already performs baseline enrollment. Geometry Prepare binds
configuration; soil/management input assembly currently occurs during Run. Show
actual emitted parameter values only after that assembly phase, never merely
because geometry preparation succeeded.

A present malformed object or mismatched asset hash fails visibly before native
execution; do not replace it with current defaults. Permit an explicit authorized
repair only after retaining the corrupt state as diagnostic history and validating
a complete replacement; the UI must label this **Repair parameterization**, distinct
from Reset. Reject `repair:true` for valid bound or unbound state; it is not an
adoption shortcut. Repair binds repository defaults and removes overrides, with a review
of that consequence before Save. Readonly projects remain inspectable without writes.

## Parameter fields, scope and resolution

Each role contains `ksat_mm_h`, `ki_kg_s_m4`, `kr_s_m` and `critical_shear_pa`.
The conductivity label is **Baseline effective hydraulic conductivity**, not measured
instantaneous infiltration or an arbitrary deep-layer conductivity.

| Key | Unit | Meaning |
| --- | --- | --- |
| `ksat_mm_h` | mm/h | Legacy AVKE baseline effective conductivity |
| `ki_kg_s_m4` | kg s/m4 | Interrill erodibility |
| `kr_s_m` | s/m | Rill erodibility |
| `critical_shear_pa` | Pa | Concentrated-flow detachment threshold |

Each entry is either `{"mode":"default"}`, `{"mode":"multiply","value":NUMBER}`,
or `{"mode":"absolute","value":NUMBER}`. No extra keys, booleans, nulls, numeric
strings, NaN or infinity are accepted by this new payload. Missing role/parameter
entries in an explicit Save fail; the editor submits one complete 12-entry object.
This strict new payload does not tighten unrelated existing `set_params` coercions.

Values must be positive. Validate both the requested value and every resolved
value: unit conversion, native real representation and emitted numeric formatting
must retain a finite positive value. Zero/underflow cannot silently activate native
parameter estimation; overflow fails before invalidation. These are representation
and input-validity limits, not field-calibrated ranges. Show tested contrasts
separately; do not invent recommended intervals from parser limits. Extremely
large positive valid values are not guaranteed to produce successful native runs.
Native failure remains explicit and never publishes current results.
Validate the complete saved override object against every selectable retained
soil-template/traffic combination for each role, even with no upload or an absent
role. This makes later surface/mapping choices safe within the same baseline.
Recheck actual serialized native inputs during native input assembly in Run; a saved valid number
is not proof of correct writer propagation.

Scope is all executed template-owned rows of the selected role in the project.
`buffer` denotes the template Forest row, not every upstream landuse OFE. Apply the buffer override to every template
scenario 3 Forest row, including upstream/remainder template Forest in unrutted
assembly; exclude independently sourced, non-template landuse. Do not
alter source hillslope/landuse soils, shared Disturbed defaults or baseline WEPP.
Absent roles retain saved intent and display **Not used in this configuration**.
Role-wide scope is intentionally the first version: no stable segment identifiers,
per-segment override maps, generic expressions or geometry overrides are added.

Resolution order is contractual:

1. Resolve feature attributes and existing fallbacks through the Roads resolver.
2. Select retained template and management using the bound resolver rules.
3. Apply existing surface, traffic, design and role adjustments, including road
   Ki/Kr division by four for low/no traffic. This gives the resolved baseline.
4. Apply the role override: default preserves it, multiply scales it once, absolute
   replaces it. Do not apply traffic again or overwrite it downstream.
5. Apply required format/boundary assembly and serialize native inputs; read them
   back and bind the actual emitted values to the execution manifest.

Overrides do not change management choice, traffic labels, surface class, rock
fragments or physical geometry. Show coupled management effects separately.
Conductivity updates the actual AVKE consumed in the legacy soil path; never
apply it to an unrelated horizon column merely because it is named Ksat.
Default-only assembly must be byte-identical to current production soil and
management outputs for every supported role/design/traffic branch.

## Save, reset, adoption and transport

Add a dedicated GET view `/runs/<runid>/<config>/roads/parameterization` and reuse
existing Roads query and POST `tasks/roads/set_params` routes. Add request key
`parameterization` containing only `overrides`, plus optional `repair: true` for
the explicit repair workflow. When present, `repair` must be JSON boolean true,
not false, a string or a number. Repair requires all 12 entries in default mode;
reject custom repair entries rather than silently discarding them. Ordinary requests cannot supply baseline assets,
identity, resolver version or schema version. Reject unknown keys inside this
object. Existing ordinary parameter keys and partial updates remain supported.
The view GET and its query path must not create or enable a missing Roads controller:
render an absent/disabled read-only explanation with a link to the existing Roads
enablement workflow. For enabled but absent state, explicit authorized Save/Prepare
may initialize Roads through the existing controller-creation boundary and bind
configuration; absence alone is not an error or a silent GET-time mutation.
A request combining existing parameter keys with the new object validates the
whole combined prospective state before mutation and resolves overrides against it.

The dedicated view submits parameterization only. Existing geometry/fallback
settings remain in the Roads workflow and retain their API behavior. Mapping
must not accidentally submit a parameterization draft. Mutation authorization,
CSRF, readonly/enabled checks and existing error envelopes remain unchanged.

Acquire the existing lifecycle guard and Roads lock in canonical order, refresh
from durable state, validate against that state, retain history/invalidate Roads
admission, then persist the intended delta with unrelated fields preserved.
Do not claim a distributed rollback: failures after invalidation remain explicit
and fail closed. Reject invalid requests before invalidation. Do not introduce
new queues, lock ordering or background writers. Successful Save tells users to
Prepare and run Roads; it never starts an unrequested native execution.

**Reset overrides** sets all draft entries to default; Save persists that choice.
Reset preserves the bound baseline, mapping and physical settings. **Cancel**
discards the draft and reloads authoritative state without mutation. **Adopt newer
repository defaults** is distinct and not implemented in version 1; show drift
information but no functional adoption button. Later adoption needs a reviewed
contract and explicit user action. Do not silently equate reset with adoption.

## Dedicated parameterization view and visibility

Link the dedicated view from the Roads panel, with a return link to Roads status
and Prepare/Run. Use familiar shared page/field/button patterns. Show three role
sections and the four drivers with units and physical meaning. Mixed projects
must group identical resolutions with segment counts and member inspection; a
single value must never imply uniformity when source templates differ.

For each parameter display source template baseline, selection reason, adjustment
arithmetic, override mode/value, and final resolved value. For example gravel/loam
road Ki is 2,000,000, low traffic divides by four to 500,000 before an override;
fill Ki 2,000,000 and buffer Ki 120,000 do not receive that division. Values must
come from the bound source, not a separately maintained UI defaults table.

Separately show **Saved configuration**, **Preview (not prepared)** and **Used in
last completed run**. Prepared values are actual file readbacks, not merely a
repeat of saved intent. Show template hashes, paths and native unit conversions
in expandable details. File suffixes cannot substitute for reading their contents. Render saved values,
template names/excerpts, uploaded segment labels and all diagnostics as escaped
text, never executable HTML. Use the established safe JSON embedding mechanism;
no raw JSON/text interpolation into script markup or unsafe innerHTML.
Before preparation, say no prepared values exist. Old results retain their own
snapshot and must never be relabeled with the currently edited configuration.

Edit uses a local unsaved draft. Save submits once; matching successful response
owns hydration. Passive query/job updates cannot overwrite a dirty draft. Lock
editing and Save/Cancel/Reset during pending Save. Failure preserves the draft;
Cancel reload failure remains explicit. Dirty state blocks local Prepare/Run and
navigation offers Save/Discard/Stay; do not add browser storage. Other sessions
remain governed by existing last-accepted-write semantics, without a promise of
cross-tab draft synchronization. Readonly users can inspect but not mutate.

Baseline/custom comparison displays runoff and sediment totals and area-normalized
quantities with climate period, area, run identity and parameter snapshot. Only
compare retained actual runs with compatible climate/geometry/report scope;
otherwise explain the mismatch. Never generate baseline results implicitly or
invent comparison numbers before runs exist. Preserve PASS versus terminal
sediment report-support distinctions and do not present output rescaling as a
model parameter change.

## Provenance, currentness and restoration

Add query field `parameterization` with status (`unbound`, `bound`, `invalid`),
server-owned baseline identity, override entries, representation diagnostics and
resolved groups. Public queries omit full retained template texts; authorized
artifact browsing retains normal project access. Legacy original keys remain.
Invalid saved fields return explicit diagnostics, never nonfinite JSON.

Extend preparation identity with a hash of canonical saved parameterization; an
absent legacy record must not masquerade as the bound version. All existing
Roads result-admission checks must consume this identity. Preserve old execution
manifest as a JSON list and add per-row `parameterization` containing baseline
id, configuration hash, role, source asset hashes, baseline/adjusted/requested/
resolved/emitted four-parameter values, input relative paths and actual hashes.
For multiple OFEs use an `ofes` list with actual 1-based indices and roles. Keep
source segment IDs local to the preparation; no cross-preparation identity claim.
Failed attempts retain partial provenance with reasons, not fabricated values.

Historical outputs stay inspectable but unavailable as current after accepted
changes. Fork/archive/restore carry the single NoDb payload with retained template
contents and ordinary generated evidence. Test under actual canonical operations
and identities; do not certify this from serialization equality alone. Repository
asset drift does not rebase a restored project. Unknown resolver versions are an
explicit unsupported state; existing diagnostic artifacts remain browseable
without evaluating unknown rules. Block ordinary Save and Run. Only the explicit
repair path may replace this state, after retaining it and reviewing the reset
consequence; no automatic downgrade is permitted.

## Compatibility and regression plan

This is an additive schema and request key. No existing key, manifest list shape,
source file or baseline output is removed. Existing projects remain unbound until
an explicit Save/Prepare; no read-time migration or automatic rerun. Old reports
retain old provenance and eligibility under the existing lifecycle. The prior
five-field boolean/null tightening and `_roads_settings_metadata` proposal are
withdrawn; they are not prerequisites of this replacement design.

Before implementation, test baseline binding/default parity as an isolated
prototype, then review the exact schema/layout and commit the approved ancestor.
After approval, cover real NoDb save/reload with another process, invalid atomic
save, lock/conflict handling, unrelated-state preservation and stale cache guards.
Validate every native writer and role mapping, including inslope single-OFE,
road/buffer, rutted road/fill/buffer, unrutted and routed combined profiles. Confirm
source hashes and actual emitted values; no-op tests must catch wrong-role controls.

Valid-state matrix: absent Roads; enabled with no upload; legacy unbound;
bound default; bound custom; absent selected role; mixed templates; prepared;
completed; dirty draft; pending save; invalid payload; corrupt saved schema/hash;
readonly/unauthorized; concurrent mutation; native failure; archived/restored;
repository drift; unsupported resolver. Each valid state must reach its intended
outcome; malformed states must fail without silent replacement or boundary escape.

Browser -> request -> durable reload -> actual prepared inputs -> native execution
-> fresh reports is required after wiring, with production-equivalent service
identity, groups, mounts, umask and orchestration. Use canonical wctl focused,
frontend and substantive full-suite gates and independent correctness, scientific,
security and UX reviews. Preapproval studies and static layout reviews cannot
certify that future workflow. No deployment is authorized.
