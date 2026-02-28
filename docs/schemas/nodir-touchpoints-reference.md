# NoDir Touchpoints Consolidated Reference
> **Archived / Deprecated (Historical, 2026-02-27):** This NoDir specification is retired from active contract flow after the directory-only reversal. It is retained only for historical/audit reference.

> Authoritative module-by-module audit reference for NoDb/NoDir touchpoints across mutation sessions, read projections, and materialization boundaries.
>
> Historical implementation evidence remains under `docs/work-packages/20260214_nodir_archives/artifacts/`.
>
> **See also:** `docs/schemas/nodir-contract-spec.md`, `docs/schemas/nodir-thaw-freeze-contract.md`, `docs/schemas/nodir_interface_spec.md`, `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`

## 1. Normative Status and Scope
- This document is normative for touchpoint classification and audit expectations.
- In-scope allowlisted roots are `landuse`, `soils`, `climate`, and `watershed`.
- This document does not redefine canonical NoDir errors or filesystem contracts.

Conflict precedence (highest to lowest):
1. `docs/schemas/nodir-contract-spec.md`
2. `docs/schemas/nodir-thaw-freeze-contract.md`
3. `docs/schemas/nodir_interface_spec.md`
4. `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
5. `docs/schemas/nodir-touchpoints-reference.md`

## 2. Contract-Version Mapping
Phase 6 artifacts record historical thaw/freeze semantics. Phase 9+ operational behavior is projection-session based.

Interpretation mapping:

| Historical Phrase | Operational Phrase (Phase 9+) |
| --- | --- |
| `materialize(root)+freeze` | `projection(mode="mutate")+commit` |
| `requires thaw` | `requires mutation session` |
| root thaw for path-heavy reads | `projection(mode="read")` |
| ad hoc per-file extraction | explicit compatibility fallback only |

## 3. Classification Legend
- `mutation session owner`: the canonical boundary that owns archive-form writes for an allowlisted root.
- `read projection`: preferred path for path-heavy read consumers that need canonical filesystem paths.
- `materialization boundary`: explicit FS-boundary fallback when a specific file must exist on disk.
- `archive-native`: list/stat/read surfaces that do not project or materialize roots.
- `rapid-cycle risk`: avoid repeated mutation-session acquire/commit loops for read-only flows.

## 4. Consolidated Touchpoint Matrix

| Module or Surface | Primary Touchpoints | Roots | Mutation Session Owner | Read Projection Touchpoints | Materialization Touchpoints | Rapid-Cycle Audit Focus | Historical Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Landuse core | `wepppy/nodb/core/landuse.py`, `wepppy/rq/project_rq.py:build_landuse_rq`, `wepppy/rq/project_rq.py:build_treatments_rq`, `wepppy/microservices/rq_engine/landuse_routes.py` | `landuse` (+ cross-root with `soils`) | `build_landuse_rq`, `build_treatments_rq`, and route-owned UserDefined write callbacks | WEPP management/template reads that require path semantics | Explicit fallback only for FS-boundary consumers that cannot consume archive-native streams | Ensure route preflight gates run before enqueue/write; avoid nested mutation wrappers in callbacks | `landuse_touchpoints_stage_a.md`, `landuse_mutation_surface_stage_b.md` |
| Soils core | `wepppy/nodb/core/soils.py`, `wepppy/rq/project_rq.py:build_soils_rq`, `wepppy/rq/project_rq.py:build_treatments_rq`, `wepppy/microservices/rq_engine/soils_routes.py` | `soils` (+ cross-root with `landuse`) | `build_soils_rq` and `build_treatments_rq` | WEPP `.sol` path-based reads | Explicit fallback for FS-boundary file consumers and exports | Ensure single owner boundary per request/job; no read-only wrappers that mutate | `soils_touchpoints_stage_a.md`, `soils_mutation_surface_stage_b.md` |
| Climate core | `wepppy/nodb/core/climate.py`, `wepppy/rq/project_rq.py:build_climate_rq`, `wepppy/rq/project_rq.py:upload_cli_rq`, `wepppy/microservices/rq_engine/upload_climate_routes.py` | `climate` | `build_climate_rq`, `upload_cli_rq`, and route-owned upload write callback | Path-heavy climate file reads (`.cli` and report artifacts), including downstream WEPP/Ash usage | Explicit fallback only for consumers that require a real file path | Upload flow must stay in one owner boundary; avoid split write/assign cycles that reacquire mutation sessions | `climate_touchpoints_stage_a.md`, `climate_mutation_surface_stage_b.md` |
| Watershed core | `wepppy/nodb/core/watershed.py`, watershed RQ owners in `wepppy/rq/project_rq.py`, `wepppy/microservices/rq_engine/watershed_routes.py` | `watershed` | `build_channels_rq`, `set_outlet_rq`, `build_subcatchments_rq`, `abstract_watershed_rq` | Path-heavy slope/network reads in WEPP and downstream mods | Explicit fallback for FS-boundary file consumers; avoid root-level read mutations | Highest risk area; avoid read-stage mutation loops and stale mixed-state retries | `watershed_touchpoints_stage_a.md`, `watershed_mutation_surface_stage_b.md` |
| WEPP prep/read orchestration | `wepppy/nodb/core/wepp.py`, `wepppy/rq/wepp_rq.py`, `wepppy/nodir/wepp_inputs.py` | `landuse`, `soils`, `climate`, `watershed` | None for read-only prep stages; true root writes remain in owning mutation jobs | Canonical path helpers should use projection-first reads | `materialize_input_file(...)` remains explicit fallback only | Read-only stages must not churn mutation sessions (`mutate_root(s)`) | `wepp_nodir_read_touchpoints_phase8a.md`, `phase8_wepp_nodir_refactor_review.md`, `phase9_projection_sessions_rollout_review.md` |
| Treatments mod | `wepppy/nodb/mods/treatments/treatments.py`, `wepppy/rq/project_rq.py:build_treatments_rq` | `landuse`, `soils` (reads `watershed`) | `build_treatments_rq` | Read projection for dependent read paths that assume direct root paths | File-level materialization only when a tool boundary requires on-disk files | Cross-root lock ordering must remain deterministic and single-pass | `phase10_mod_workflow_touchpoints_stage_a.md`, `phase10_mod_workflow_contract_notes.md` |
| Ash transport mod | `wepppy/nodb/mods/ash_transport/ash.py`, `wepppy/rq/project_rq.py:run_ash_rq`, `wepppy/microservices/rq_engine/ash_routes.py` | `climate`, `watershed`, `landuse` | No allowlisted-root mutation owner currently defined for read paths; route/job preflight required | `Ash.run_ash` climate CLI reads are projection-required touchpoints | Fallback materialization must remain explicit and fail-fast if disabled | Prevent implicit thaw/mutate wrappers around read-only ash flows | `phase10_mod_workflow_touchpoints_stage_a.md`, `phase10_mod_workflow_contract_notes.md` |
| Debris flow mod | `wepppy/nodb/mods/debris_flow/debris_flow.py`, `wepppy/rq/project_rq.py:run_debris_flow_rq`, `wepppy/microservices/rq_engine/debris_flow_routes.py` | `watershed`, `soils` | No dedicated root mutation owner required for current read-only usage | Current dependency is mostly controller-attribute reads; projection may be optional | Materialization not expected for current primary path | Keep route/job preflight coverage for future path-based expansions | `phase10_mod_workflow_touchpoints_stage_a.md`, `phase10_mod_workflow_contract_notes.md` |
| Omni mod | `wepppy/nodb/mods/omni/omni.py`, `wepppy/rq/omni_rq.py`, `wepppy/microservices/rq_engine/omni_routes.py` | `landuse`, `soils`, `climate`, `watershed` | Owner boundaries currently distributed and under normalization | High-priority projection touchpoints for clone and contrast workflows | Materialization fallback only where compatibility requires it | Highest mod-level rapid-cycle and mixed-state regression risk; audit per wave | `phase10_mod_workflow_touchpoints_stage_a.md`, `phase10_mod_workflow_contract_notes.md`, `phase10_mod_workflow_rollout_review.md` |
| Browse/files/download and FS-boundary tools | `wepppy/microservices/browse/*`, `wepppy/microservices/_gdalinfo.py`, `wepppy/microservices/browse/dtale.py`, export/query surfaces | all allowlisted roots | None | Browse/files/download stay archive-native and do not require projection | `dtale`, `gdalinfo`, and similar FS-boundary tools use explicit materialization paths | Enforce no request-surface thaw/freeze cleanup and no hidden fallback writes | `nodir_behavior_matrix.md`, `nodir_materialization_contract.md`, `touchpoints_inventory.md` |

## 5. Administrative Update Policy

### 5.1 Policy Objective
Keep one maintained operational reference while preserving work-package artifacts as immutable historical evidence.

### 5.2 Required Update Triggers
Update this document in the same change when touching any of:
- `wepppy/nodb/core/{landuse,soils,climate,watershed,wepp}.py`
- `wepppy/nodb/mods/{treatments,ash_transport,debris_flow,omni}/**`
- `wepppy/rq/project_rq.py`, `wepppy/rq/wepp_rq.py`, `wepppy/rq/omni_rq.py`
- `wepppy/microservices/rq_engine/{landuse_routes,soils_routes,climate_routes,upload_climate_routes,watershed_routes,ash_routes,debris_flow_routes,omni_routes}.py`
- `wepppy/nodir/{mutations,projections,materialize,wepp_inputs,thaw_freeze,state}.py`
- Any schema/contract file listed in Section 1.

### 5.3 Required Same-PR Actions
1. Update affected matrix rows in Section 4.
2. Update `Last Reviewed` metadata in Section 8.
3. Add or refresh references in Section 7 if new artifacts/contracts were introduced.
4. If behavior changes, include a short audit note in PR text:
   - whether change shifts a touchpoint among mutation, projection, materialization
   - whether rapid-cycle risk increased, decreased, or is unchanged
5. Run:
   - `wctl doc-lint --path docs/schemas/nodir-touchpoints-reference.md`
   - targeted tests for changed touchpoints (minimum: relevant `tests/nodir/*` or route/mod suites)

### 5.4 Historical Artifact Policy
- `docs/work-packages/20260214_nodir_archives/artifacts/*` remain historical evidence.
- Do not rewrite historical findings to match later contract wording unless correcting factual errors.
- New implementation waves should append new artifacts and update this reference, not overwrite earlier evidence.

### 5.5 Audit Cadence
- Transactional: every PR that touches trigger files above.
- Periodic: monthly audit of all Section 4 rows.
- Release gate: confirm no unreviewed rapid-cycle risks before release cut.

## 6. Audit Procedure (Projection vs Mutation vs Materialization)
Use this checklist for touchpoint audits:

1. Identify root interaction type:
- read-only
- root mutation
- FS-boundary file handoff

2. Confirm expected boundary:
- read-only path-heavy -> `projection(mode="read")`
- root mutation -> `projection(mode="mutate")+commit`
- FS-boundary isolated file need -> explicit materialization fallback

3. Reject anti-patterns:
- hidden fallback writes after projection/read failure
- request-layer thaw/freeze cleanup
- repeated mutation-session loops in read-only stages

4. Verify canonical errors are preserved:
- `409 NODIR_MIXED_STATE`
- `500 NODIR_INVALID_ARCHIVE`
- `503 NODIR_LOCKED`
- `413 NODIR_LIMIT_EXCEEDED` where materialization limits apply

Recommended discovery commands:

```bash
rg -n "mutate_root|mutate_roots|with_root_projection|acquire_root_projection|materialize_file|materialize_path_if_archive|thaw|freeze" \
  wepppy/nodb wepppy/rq wepppy/microservices wepppy/nodir

rg -n "\\b(lc_dir|soils_dir|cli_dir|wat_dir)\\b" wepppy/nodb wepppy/rq wepppy/microservices wepppy/nodir

rg -n "_join\\([^\\n]*(landuse|soils|climate|watershed)" wepppy
```

## 7. References

Normative contracts:
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

Consolidated and root-stage artifacts:
- `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase6_all_roots_review.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase6_revision_assessment_closeout.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/landuse_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/soils_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/climate_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/watershed_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/watershed_mutation_surface_stage_b.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/wepp_nodir_read_touchpoints_phase8a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase8_wepp_nodir_refactor_review.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase9_projection_sessions_rollout_review.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase10_mod_workflow_touchpoints_stage_a.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase10_mod_workflow_contract_notes.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/phase10_mod_workflow_rollout_review.md`

## 8. Administrative Metadata

| Field | Value |
| --- | --- |
| Owner | WEPPpy maintainers touching NoDir/NoDb touchpoints |
| Last Reviewed | 2026-02-19 |
| Review Cadence | Per touching PR + monthly audit |
| Historical Artifact Policy | Work-package artifacts are evidence records; this document is the maintained operational reference |

## 9. Change Log

| Date | Change | Author |
| --- | --- | --- |
| 2026-02-19 | Initial consolidated reference with administrative update policy and contract references. | Codex |

