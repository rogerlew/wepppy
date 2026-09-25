# Disturbed dependency review

**Date**: 2026-09-25 UTC
**Revision inspected**: `b96f77e589ec033853970ac90fdab945490c6553`
**Reviewers**: delegated explorer `trace_disturbed_dependencies`; Codex parent
**Scope**: proposed upload-enabled, non-disturbed Config Builder projects
**Evidence**: static source tracing; no runtime tests or security sign-off

## Findings from parent boundary review

The exclusion policy must reach the run-level feature interfaces. Builder-only
filtering cannot enforce it. Current Builder capability graphs use `mods=()` in
`wepppy/nodb/locales/capability_graph.py:824` and `:914`; the observed continental-US
profile has `allowed_mods=[]`. The current operational feature selection surface
is therefore especially important; do not assume Builder's optional-module list
already represents everything that users can enable later.

| Finding | Evidence | Required disposition |
| --- | --- | --- |
| Header menu has no project policy input | `wepppy/weppcloud/feature_registry/runtime.py:191`, `build_header_mod_options` accepts active mods, role, backend, and include-all | Thread the opted-in exclusion policy through normal menu construction without removing compatible features. |
| Enable preconditions inspect only direct prerequisites | `wepppy/weppcloud/routes/nodb_api/project_bp.py:91`, `_validate_feature_enable_preconditions` | Enforce the policy for the requested feature and its dependency closure before mutation. |
| Automatic dependencies bypass their own precondition validation | `project_bp.py:178`, `_enable_mod_for_run` appends and restores/initializes dependencies | Validate the complete operation before appending any mods or restoring controller backups. This is a proposed-policy gap, not evidence of unauthorized access under today's contract. |
| Run sections are a separate presentation path | `wepppy/weppcloud/routes/run_0/run_0_bp.py:2259` onward checks individual mod/controller state | Apply the same policy to sections, navigation, and applicable reports; do not rely solely on header visibility. |
| SBS route assumes a controller is available | `wepppy/microservices/rq_engine/upload_disturbed_routes.py:81` chooses BAER or unconditionally loads Disturbed | Reject policy-incompatible SBS requests explicitly before controller access, upload writes, or mutation. Controller absence causing an exception is not the intended feature gate. |
| Refresh reconstructs selections and graph | `wepppy/nodb/project_config_update.py:511`, `:785`, `:870`, `:920` | Persist/reload the upload choice, derive the graph under that choice, and amend unconditional Disturbed congruence assumptions. Do not claim the current refresh necessarily rewrites mods: it presently preserves current mods in its payload; the new policy must survive both resolution and validation. |

The `include_all` Playwright presentation path is a test facility, not authority to
execute a forbidden feature. Direct feature/task APIs must enforce policy even
when a control is rendered through that facility.

## Delegated runtime dependency tracing

Final agent findings are recorded below after review. Exclusions concern the
new opted-in configuration only; they do not remove features from existing projects.

| Feature / workflow | Dependency and evidence | Recommended disposition for opted-in projects |
| --- | --- | --- |
| Treatments | Nonempty build loads Disturbed unconditionally at `wepppy/nodb/mods/treatments/treatments.py:271`; later soil rebuild consumes its replacement tables and MOFE writer at `:410` | Exclude `treatments`. |
| Omni Scenarios | All scenario execution loads Disturbed at `wepppy/nodb/mods/omni/omni_run_orchestration_service.py:274`; sibling cloning copies its state/directory at `mods/omni/omni.py:535` | Exclude `omni`, including its “undisturbed” scenario, which still uses the controller. |
| Omni Contrasts | Declared prerequisite `omni` at `feature_registry.yaml:93` | Exclude `omni_contrasts` transitively. |
| PATH Cost-Effective | Requires Omni scenario summaries and contrasts at `wepppy/nodb/mods/path_ce/preconditions.py:110`; default scenario names at `presets.py:22` | Exclude `path_ce`; its empty prerequisite declaration is incomplete for these workflows. |
| Legacy Debris Flow | Uses BAER if enabled, otherwise Disturbed and SBS coverage at `wepppy/nodb/mods/debris_flow/debris_flow.py:209` | Exclude `debris_flow` because this policy excludes both SBS sources. Keep separate from the newer post-fire feature. |
| RUSLE | Declared Disturbed prerequisite at `feature_registry.yaml:208`; also consumes landuse raster at `wepppy/nodb/mods/rusle/rusle.py:937` | Exclude `rusle`; a future independent version would also need raster compatibility work. |
| Post-fire debris flow | Declared Disturbed prerequisite at `feature_registry.yaml:224`; SBS consumer at `wepppy/nodb/mods/postfire_debris_flow/production.py:236` | Exclude `postfire_debris_flow`. |
| Revegetation transforms/scenarios | Fire date and burn-class dependency at `wepppy/nodb/mods/rap/rap_ts.py:395`; unconditional fire-date prep at `wepppy/nodb/core/wepp.py:1728` | Exclude revegetation initialization, controls, cover-transform upload, and execution paths. This is not a registry feature row; menu filtering alone misses it. |

Treatments, Omni, legacy Debris Flow, and PATH CE currently omit relevant runtime
dependencies from their registry declarations. Update canonical declarations
carefully: legacy Debris Flow's BAER alternative means a blanket global
`requires_features: [disturbed]` would incorrectly restrict valid existing BAER
projects. Record its actual prerequisite alternatives and enforce the opted-in
policy without narrowing unrelated existing workflows.

## Features to retain and conditional paths

**RAP Time Series analysis:** raw analysis is independent (`mods/rap/rap_ts.py:255`).
The direct `prep_cover` method loads Disturbed, but normal WEPP preparation enters
revegetation only when Disturbed exists with soil version 9005
(`wepppy/rq/wepp_rq_stage_prep.py:163`, `core/wepp_prep_service.py:57`). Do not
remove all RAP functionality or introduce a broad RAP refactor to address a
revegetation path that the new configuration excludes. Verify ordinary WEPP
preparation and intended existing cover modifiers separately.

**Ash Transport:** no hard Disturbed dependency was found in traced execution.
Burn severity is inferred from management descriptions
(`core/landuse.py:1833`); `mods/ash_transport/ash.py:752` also supports explicit
ash-type maps. Preserve dependency-wise. Test the no-map/unburned no-ash result
and filename/description choices that contain fire/severity words, since those
may affect classification without SBS.

**Geneva:** its optional SBS discovery returns no adjustment when Disturbed is
absent (`mods/geneva/collaborators/hsg_assignment_service.py:121`). Preserve and
verify its no-SBS hydrologic soil-group path with uploaded soils.

Searches did not reveal hard Disturbed dependencies in Roads, Observed Data, DSS
Export, OpenET, or Agricultural Fields. Do not exclude them solely because of
this option. These are preservation candidates, not certificates of full custom
management/soil compatibility; required source metadata may introduce separate
integration constraints.

## Implementation risks and bounded follow-up

The existing registry is insufficient as the sole input to an exclusion list.
Retain the direct and transitive matrix above, align current declarations with
runtime evidence, and apply one resolved project policy across menu, sections,
feature activation, direct tasks, and refresh. Avoid ad hoc lists that drift
independently. Do not build a general dependency framework unless the existing
mechanisms prove insufficient for this finite set.

Validate the complete enable operation before any mutation, including automatic
dependencies and controller backup restoration. An absent Disturbed controller
must not cause a late internal error after an unsupported request has written
files. No ordinary request may initialize it to satisfy an excluded feature.

Config refresh must preserve the selected policy through manifest reconstruction,
graph resolution, congruence checks, and review/apply. Existing Builder projects,
legacy BAER alternatives, and unchecked configurations retain their behavior.
Creation-time selection avoids destructive migration of existing state.

Required runtime evidence before implementation closeout:

1. Each excluded feature is absent from the run UI and rejected through direct
   and transitive activation/task requests before mutation or enqueue.
2. Revegetation/cover-transform surfaces cannot survive creation or refresh.
3. Raw RAP analysis and ordinary WEPP preparation work without Disturbed and do
   not produce unintended fire/recovery artifacts.
4. Ash works with explicit maps and reports an understandable no-ash state without
   a burn/type source; Geneva works without SBS.
5. Reload, capability refresh, clone, and archive/restore preserve exclusions and
   compatible features. Unchecked and legacy projects retain their semantics.
6. Independent uploaded/database input combinations and every OFE produce the
   intended consumed files. The non-disturbed soil-stack writer remains necessary.

## Assessment outcome

The proposed Builder option remains feasible and cleaner than class-selector
semantics. The primary extra scope is consistent feature-policy enforcement and
correction of missing dependency declarations, not new modeling infrastructure.
Static review is complete; all runtime evidence above is pending. This artifact
is a dependency assessment, not a contract approval or security review.
