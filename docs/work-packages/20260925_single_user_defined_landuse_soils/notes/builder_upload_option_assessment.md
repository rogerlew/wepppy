# Assessment: Config Builder single-input upload option

**Date**: 2026-09-25 UTC
**Status**: Builder scope and buffer exclusion approved by operator; canonical checkpoint pending
**Evidence**: Source inspection and local file-header inventory; no runtime validation

## Accepted direction

Add the operator-proposed checkbox **Enable single landuse and soils upload** to
Config Builder as an explicit creation-time option. Unchecked preserves current
Builder behavior. Checked enables both Single User-Defined modes and creates a
project without Disturbed, SBS upload, or buffer OFEs. The two run controls choose
their modes independently; enabling the capability does not require uploading both files
or automatically switch either control to upload mode.

The operator selected this direction when resolving WPR-01 on 2026-09-25.
It is cleaner than coupling the feature to deprecated `0.cfg`, and substantially
simpler than per-input Disturbed Class selectors. It requires a bounded exception
to the current Builder Disturbed default, not a project-wide runtime toggle on
existing runs. The prior question about SBS remapping explicitly selected classes
is unnecessary for the accepted direction; class selectors are out of scope.

Suggested help text: “Allow one management file and one soil file to be uploaded
and used across all hillslopes and OFEs. Disables SBS upload, disturbed
parameterization, features that require Disturbed, and buffer OFEs for this
project. Existing landuse and soil options remain available.” Show the consequences again in the existing configuration review.

## Confirmed requirements retained

The operator requires functional multi-OFE support: replicate the uploaded single
landuse/soil source across every hillslope and every OFE. The operator subsequently
excluded buffer OFEs whenever this feature is enabled; other compatible
non-disturbed modifiers remain functional. Thus uniform source assignment does
not promise identical final parameters when existing modifiers vary by hillslope or OFE.
Keep accepted source bytes intact and apply modifiers to generated copies.

No new numerical defaults or version conversions follow merely from enabling
uploads. Upload safety, theme-aware controls, SBS-style accepted-filename feedback,
source retention, and independent selection of landuse/soil modes remain required.

## Source evidence and necessary changes

| Boundary | Evidence | Required implementation change |
| --- | --- | --- |
| Builder selection schema | `wepppy/nodb/config_builder/schema.py::BuilderSelections` has no upload option; `snapshot.py::parse_builder_selections` rejects unknown fields | Add one strictly validated boolean with absent meaning false; persist it in selection serialization, review, manifest, and generated config. Do not represent it as a runtime mod. |
| Default mods | `wepppy/nodb/config_builder/resolver.py` unconditionally writes `['disturbed', ...]` with writer `builder:sbs-support` | Conditional effective mods: keep existing behavior when false; omit Disturbed when true. Preserve unrelated compatible modules. |
| Canonical intent | `docs/adrs/ADR-0064-builder-disturbed-default.md` and `docs/schemas/project-owned-config-contract.md`, “Builder Soil Burn Severity Support (2026-09-10)” require Disturbed for every Builder project | Record and ratify the explicit opt-in exception, including scientific consequences when no SBS map exists. Leave unchecked behavior unchanged. |
| Configuration updates | `wepppy/nodb/project_config_update.py` reconstructs effective mods with Disturbed and validates manifest/config parity | Recognize and preserve the new selection in preview/apply, refreshed capability graphs, and consistency checks; never reintroduce Disturbed to opted-in projects. |
| Capability graph | `wepppy/nodb/project_config_capabilities.py` resolves landuse methods by dataset/representation and soil builders by dataset | Add distinct upload modes only to opted-in capability graphs, including multiple-OFE representation. Preserve current default methods and dataset choices. UI, API, and build checks must share the rule. |
| Landuse mapping | `wepppy/nodb/config_builder/registry.py` assigns disturbed-compatible mappings for Builder landuse datasets | Audit mapping initialization/consumers without Disturbed. Do not automatically change mapping or numerical defaults; explicitly record any required difference. A mapping name alone is not a runtime disturbance switch. |
| UI | `wepppy/weppcloud/templates/config_builder.htm` and `controllers_js/config_builder.js` serialize selections, validate combinations, and render review | Add the checkbox and help, round-trip it through validation/create, and invalidate a stale review whenever it changes. |
| SBS/runtime boundary | Shared SBS control relies on Disturbed/BAER controllers; preparation sometimes retrieves Disturbed by controller-file existence | Hide SBS features and reject unsupported mutations server-side. New opted-in projects must not initialize Disturbed/BAER or other conflicting disturbance dependencies. Do not rely on hiding the control alone. |
| Multi-OFE soils | `core/wepp.py::prep_multi_ofe_hillslope` consumes `soils/hill_<id>.mofe.sol`; the inspected core build has no equivalent to Disturbed's soil-stack publisher | Provide non-disturbed source replication/assembly using the owned utility. It must also cover ordinary soils paired with uploaded landuse; do not require users to enable both upload modes. |

The implementation checkpoint must enumerate conflicting optional modules and
binary requirements using actual registry constraints. Explain conflicts during
Builder validation and reject forged create requests; do not silently deselect a
requested module or expand this option into a general module-management feature.
No new queue, service, or dependency is needed for the proposed configuration choice.

## Required exclusion of Disturbed-dependent features

The operator explicitly required on 2026-09-25 that selecting the upload option
also removes features that depend on Disturbed. This requirement applies to direct
and indirect dependencies, including dependencies that would automatically
re-enable Disturbed. It is not satisfied by removing the SBS upload control alone.

Exclude incompatible features from the opted-in project's resolved capabilities,
initialized modules, feature menu, navigation, controls, and applicable reports.
Enforce the same exclusion in Builder validation/create, feature-enable APIs,
direct task submissions, and config refresh. Never restore Disturbed through an
auto-enabled dependency. Unsupported requests must fail explicitly before state
mutation or enqueue. Preserve compatible features and unrelated settings.

The registry currently declares `requires_features: [disturbed]` for **RUSLE**
and **Post-fire debris flow**, so those are confirmed exclusions. The feature
runtime normally renders missing-prerequisite features disabled; this option's
requirement is to remove incompatible features from its available feature set.
Record that scoped presentation exception in the feature-registry specification.

The delegated [dependency review](../artifacts/20260925_dependency_review.md)
is complete at the static-analysis level. It additionally identifies Treatments,
Omni Scenarios, Omni Contrasts, PATH Cost-Effective, legacy Debris Flow, and
revegetation workflows as exclusions (the controller identifier is
`revegetation`). RAP analysis, Ash, and Geneva have independent/optional paths
and should remain, subject to the targeted runtime checks in that review.
Missing registry declarations and activation/refresh enforcement gaps are recorded
with source references. No runtime compatibility is claimed.

Retain a dependency matrix with feature ID, direct/indirect dependency, source
boundary, affected UI/API/job surfaces, disposition, and regression evidence.
Update canonical dependency declarations where inspection confirms a missing
contract; do not use an ad hoc UI-only blacklist as the authority. A dependency
on an unrelated module alone is not a reason to remove that module.

If a user checks the option after choosing an incompatible Builder module, explain
the conflict in the existing validation/review flow and require a valid selection
before creation; do not silently retain the incompatible choice. Existing projects
are not stripped of modules or artifacts by this creation-time feature.

Acceptance must prove both that all excluded features are absent from the opted-in
UI and inaccessible through direct APIs/jobs, and that checked/unchecked creation,
refresh, clone, and archive/restore preserve the policy. Negative tests cover
transitive dependencies and attempts to auto-enable Disturbed; positive tests
retain compatible features and unchanged behavior for ordinary Builder projects.

## Required buffer exclusion

The operator resolved WPR-02 by instructing “disable the buffer ofe when this
feature is enabled.” The policy applies to the Builder option, not current run
input modes. Set `watershed.mofe_buffer = false` in generated config and durable
state. Disable “Apply buffers” and buffer-specific configuration controls in
`subcatchments_pure.htm`, plus `mofe_buffer_selection` in `landuse_pure.htm`, with
an explanation. Do not merely keep buffer geometry and change its management.

Enforce the same rule in `wepppy/microservices/rq_engine/watershed_routes.py`,
NoDb mutation/build boundaries, schema/default metadata, and config refresh.
Reject requests to enable buffer OFEs before state mutation or enqueue. Reject
inconsistent buffer-enabled build state explicitly; do not silently change
existing topology. Opted-in projects must generate no buffer OFE, including when
both input modes use ordinary datasets. Mode switching, clone, archive/restore,
and refresh preserve the rule. Unchecked and existing projects retain their
buffer behavior. This is the specific exception to retained compatible modifiers.

## Multi-OFE implementation boundary

Build uniform landuse assignments from the watershed's actual non-buffer hillslope/OFE
structure, rather than requiring a landcover raster solely to obtain the same
uploaded source everywhere. Match the ordered OFEs in each hillslope slope file.
Reuse `Management.make_multiple_ofe` or `ManagementMultipleOfeSynth` as appropriate;
verify rotations, references, independent segment copies, and scenario limits.

Reuse `SoilMultipleOfeSynth` for repeated single-OFE soil definitions, preserving
source version and explicitly passing the intended `ksflag` (its default is zero).
The current writer requires a same-version stack. Generated landuse, soil, and
slope files must agree on OFE count/order. Verify ordinary-landuse/uploaded-soil
and uploaded-landuse/ordinary-soil combinations, not only both uploaded.

Do not disable multi-OFE to simplify the first implementation. Support for a
multi-OFE project is distinct from accepting an already heterogeneous multi-OFE
upload: recommend one-OFE source files for this uniform-input mode and replicate
them to the project's topology. Reject multi-OFE source files with an explanation
rather than silently taking their first OFE. This upload-format restriction remains
a recommendation pending the accepted contract.

## Recommended initial file versions

For this non-disturbed Builder scope, recommend **management 98.4 and 2016.3**
and **soil 7778** as the intended initial allowlist, with each version gated by
real parser/serializer/preparation/binary fixtures before release. Treat 7778 as
the simple soil input recommendation. The corpus inventory found 187 `.man`
files in `wepppy/wepp/management/data`, all labeled 98.4; the parser has explicit
2016.3 handling, but that branch needs representative external-format fixtures.
Version-only acceptance is insufficient: `ManagementSummary` currently requires
cropland-style initial conditions, and several management sections have narrower
support than the overall format. State the supported content subset explicitly.

The USDA [2024 WEPP user summary](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum2024.pdf)
documents 95.7, 98.4, and 2016.3 management formats. Repository support and the
selected executable, rather than that list alone, determine upload eligibility.
Defer 95.7 and native `ow-lanuse-1` until their specific preparation/summary/binary
paths are validated; do not accept arbitrary versions via a numeric comparison.

Soil `WeppSoilUtil.__str__` supports 7778, 9001, 9002, 9003, and 9005, but that is
not evidence of lossless upload support. The 900x formats encode disturbance/model
behavior inside the file even without the Disturbed controller. Parsing does not
retain every extended field verbatim: the writer regenerates burn codes, 9005
texture enums, and Rosetta values for versions >=9002. The preparation service
also derives its revegetation flag from a Disturbed controller's soil version.
These are reasons to defer 900x uploads for the simplest initial non-disturbed
scope, not a claim that the model cannot read them.

Defer legacy soil 95.1/97.5, 2006.2, and 7777 until conversion semantics are
explicitly supported. The writer cannot emit these formats directly; conversion
can estimate missing hydraulic parameters. Existing modifiers being allowed does
not automatically approve such new inference. The soil corpus includes 95.1,
2006.2, and 7778 examples, but no upload-to-execution tests were run in this review.

## Remaining scope decisions and acceptance

The accepted scope uses a creation-time choice only. Existing Builder projects and legacy manifests
without the flag retain their current semantics; absence must not silently add or
remove controllers on load. Changing an existing project's disturbance policy
requires a separate migration/rebuild contract and is not necessary for this UI.
Config-update compatibility must still be implemented for newly opted-in projects.

The flag enables choices; keep normal dataset selectors and defaults
available because either uploaded domain can be used independently. Document that
Disturbed remains disabled even while both run controls use normal database modes.
All new modes must be unavailable when the flag is false, including direct API
requests. Legacy `0.cfg` support can be considered separately, not implicitly added.

Acceptance covers checked/unchecked creation, omitted/invalid boolean input,
validation-review-create parity, controller initialization, SBS UI/API absence,
buffer controls/API exclusion and generated topology, conflicting modules, refresh preservation, both representations, all four run-mode
combinations, modifiers, rebuild/clone/archive/restore, and final generated inputs.
Existing unchecked Builder behavior must retain its current disturbance results.
The normal upload/security/NoDb/RQ/artifact contracts remain necessary; class
inheritance and SBS-remapping contracts do not enter the recommended scope.

## Pre-checkpoint security sequence

The [design security artifact](../artifacts/20260925_security_review.md) is created
before the canonical checkpoint. Finalize its pending design decisions and obtain
independent security review together with the required contract reviews before
committing that checkpoint. Extend the same artifact with runtime evidence during
implementation and closeout. Scope approval is not security sign-off.
