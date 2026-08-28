# WP12D Climate and Land-Cover Authority Correction

**Amendment ID**: `PC-24/WP12D-20260828-5`
**Status**: ratified exactly by the operator, 2026-08-28 16:29 UTC; binding
correctness/governance/security READY; standalone checkpoint pending
**Starting revision**: `0ad76c547145bbe323148bac73410ff9cfcd01ef`
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Production authority**: none; parent WP12 retains merge and production

## Discrepancy and operator direction

The original climate-mode audit omitted three supported choices from the
current five-locale authority. Continental US must also expose DEP NEXRAD
Breakpoint and Future CMIP5, and every exposed locale must expose User-Defined
Climate. The `closing-plump/eu-disturbed` Forest run demonstrates the paired
compatibility defect: its flattened schema-v1 preset snapshot advertises ten
climate datasets, so its Europe run page renders modes outside the locale.

The operator also clarified that a Config Builder Land-cover dataset selection
sets the project's selected default; it does not narrow the run's locale-wide
land-cover envelope. The run control must retain every land-cover dataset
applicable to its locale.

This is an intended compatibility and parameterization correction, not a
conformance fix. The current canonical contract explicitly preserves flattened
schema-v1 catalogs without live locale projection and records the older climate
matrix. Implementation therefore remains blocked until this amendment is
ratified, independently reviewed, and committed as a standalone ancestor.

## Exact normative delta

The current Builder-exposed locale climate matrix becomes:

| Stable profile | Exact climate dataset IDs | Default |
| --- | --- | --- |
| `continental-us` | `vanilla_cligen`, `prism_stochastic`, `observed_daymet`, `observed_gridmet`, `dep_nexrad`, `future_cmip5`, `user_defined_cli` | `vanilla_cligen` |
| `europe` | `vanilla_cligen`, `eobs_modified`, `user_defined_cli` | `vanilla_cligen` |
| `canada` | `vanilla_cligen`, `observed_daymet`, `user_defined_cli` | `vanilla_cligen` |
| `australia` | `vanilla_cligen`, `agdc`, `user_defined_cli` | `vanilla_cligen` |
| `global-earth` | `vanilla_cligen`, `user_defined_cli` | `vanilla_cligen` |

Europe therefore presents exactly Vanilla CLIGEN, E-OBS Modified (Europe), and
User-Defined Climate. The numeric runtime modes remain unchanged: DEP NEXRAD
Breakpoint is 13, Future CMIP5 is 3, and User-Defined Climate is 12. Dataset-
specific station/spatial relations and upload requirements remain those owned
by the canonical climate catalog; no climate algorithm, provider, year bound,
or file-validation rule changes.

For land cover, each schema-v3 locale graph stores the complete locale-
applicable land-cover envelope, while
`capability_defaults.landuse_dataset` stores the Builder selection. Resolution
materializes that selected dataset into the runtime config but MUST NOT remove
other locale-applicable IDs from `capabilities.landuse_datasets`. Continental
US uses the complete canonical `us` land-cover catalog: annual NLCD and NLCD
Ever Forest for 1985 through 2024 plus eMapR vote for 1984 through 2017. Europe
uses CORINE 1990/2000/2006/2012/2018; Canada and Global Earth use C3S 1992
through 2020; Australia uses Australia Land Use 2010-2011. Canada runtime token
`canada` must resolve the global C3S catalog rather than the default US catalog.

The Builder validates its selected default against that locale envelope. Run
presentation, discovery, setter, and build boundaries expose and enforce the
whole envelope, not a singleton derived from the selected default. A persisted
current value outside the current envelope remains visible only through the
existing disabled exact-current compatibility carveout.

## Flattened schema-v1 preset correction

A flattened schema-v1 project is projection-eligible only when all of these
conditions hold: the canonical reader accepts its schema-v1 manifest; the
declared config digest exactly matches current config bytes; `source_kind` is
`preset`; `source_preset` is a canonical active named-preset token and equals
the config filename without `.cfg`; `parent_chain` is exactly
`defaults/shared-defaults` followed by `preset/<source_preset>`; both parent
revisions equal SHA-256 of the current server-owned canonical source files;
replaying the manifest's recorded allowlisted query overrides through the
canonical preset snapshot resolver reproduces the current flattened config
bytes exactly; and both that rematerialized config and effective stored config
contain the same one recognized Builder base locale (`us`, `eu`, `canada`,
`au`, or `earth`) with no locale overlay. `source_revision` is descriptive
provenance, not authentication. Such a project uses the
current locale graph only for climate and land-cover presentation, discovery,
setter, and build authority. It does not rewrite its `.cfg`, manifest, or NoDb
files. Its stored coarse climate/landuse lists remain provenance evidence but
no longer broaden or narrow those two live domains. Its schema-v1 soil, model,
mod, and other compatibility behavior remains unchanged.

This projection is fail-closed and bounded:

- the exact eligible preset state above uses the live graph;
- absent, malformed, newer, digest-mismatched, or non-preset manifests retain
  existing schema-v1 behavior;
- missing, malformed, unknown, inactive, filename-incongruent, or parent-chain-
  incongruent `source_preset` identity retains existing schema-v1 behavior;
- parent-revision drift, invalid/non-allowlisted override provenance, canonical
  rematerialization mismatch, or rematerialized/stored locale mismatch retains
  existing schema-v1 behavior;
- an unavailable, malformed, or inconsistent canonical preset-policy corpus is
  not an unknown/inactive compatibility fallback; after auth/run access it
  returns diagnostic `503 builder_registry_error` with `Retry-After: 5` and no
  multipart read/save, timestamp removal, reservation, mutation, or enqueue;
- absent, empty, unknown, overlay, non-Builder, Turkey, and RHEM locale states
  retain existing compatibility behavior without live-registry consultation;
- live-registry failure for an eligible preset returns the existing diagnostic
  `503 builder_registry_error` contract without a global fallback; and
- an outside-authority persisted current climate or land-cover selection
  remains disabled exact-current and may rebuild unchanged, but cannot
  authorize a different unsupported selection.

Complete schema-v2/schema-v3 stored graphs remain frozen by default. Existing
schema-v3 projects obtain this expanded matrix only through the already-
ratified acknowledged capability-refresh workflow. Schema-v2 remains frozen
and ineligible for refresh. No project migration or bulk rewrite is authorized.

## Valid-state matrix

| Runtime state | Climate/land-cover authority | Mutation policy |
| --- | --- | --- |
| New Builder schema-v3 | Current selected locale graph; selected land cover is default only | Enforce complete locale envelope |
| Existing valid Builder schema-v3 | Stored graph until acknowledged refresh | Enforce stored envelope; refresh remains explicit |
| Complete schema-v2 | Frozen stored graph | Existing behavior unchanged |
| Projection-eligible schema-v1 named preset | Current locale climate and land-cover projections; other v1 axes unchanged | Enforce projections with exact-current carveout |
| Structurally loadable but digest-mismatched preset manifest | Existing schema-v1 compatibility catalog | Preserve reader warning; no registry call |
| Missing/unknown/inactive/filename- or chain-incongruent preset identity | Existing schema-v1 compatibility catalog | Preserve compatibility; no registry call |
| Parent hash, recorded override, canonical rematerialization, or rematerialized/stored locale mismatch | Existing schema-v1 compatibility catalog | Preserve compatibility; no registry call |
| Canonical preset policy unavailable, malformed, or inconsistent | No fallback authority | Diagnostic 503 after auth; no side effect |
| Non-flattened recognized legacy base | Current locale graph | Existing WP12D behavior |
| No capability, invalid/non-preset schema-v1, overlay, non-Builder, Turkey, or RHEM | Existing compatibility catalogs | Existing behavior unchanged |
| Required live registry unavailable | No fallback authority | Diagnostic 503 before mutation/enqueue |

## Compatibility, data, and security impact

Compatibility is additive for current Builder description and explicit
schema-v3 refresh, restrictive for incorrectly broad schema-v1 preset climate
lists, and expansive for schema-v1 preset locale land-cover options that were
incorrectly narrowed. Existing files are read without mutation. Stored
schema-v2/schema-v3 authority remains valid, including all append-only prior
structure identities.

This changes dataset parameterization and schema-v3 structure identities, so
ADR-0047 and the append-only structure catalog must be amended. Before any
writer or Builder description can emit the new graphs, a standalone reader
floor must contain all five resulting structure identities and must reopen
every prior v3 identity. Forest must deploy that reader floor first, then the
writer candidate, then prove the exact Europe schema-v1 projection and one new
schema-v3 graph/refresh/rollback path without rewriting run data.

The deterministic structural transitions are:

| Locale | Prior identity | Resulting identity |
| --- | --- | --- |
| `continental-us` | `5296d3519d578164b6a5874a820991c935b394e5336aba41fe3e8f8d0dd4e29b` | `3151e7e11be97967b32b887c6832b5286d252bf9b85841b889d5dcfbb24a8faf` |
| `europe` | `c05b6a66f823f69cf8f1d44b69c206da1dc9449b278662c680248a3f3b755aeb` | `18eda2d24f57be54993d2f0b609c59de6c26a17632d8653cc62b5a926e66f2c7` |
| `canada` | `dd7f7cdb0d861a159df64a4806ee5585f0208b93982990e30974055b1f2a41e7` | `07f733c2b13589ac637fc898859b8e3eac4902199606a2580796eec47765d7b4` |
| `australia` | `bb4bdde8740d689aa378bcf744a942d997b9c69cdc445d80be07c749635efc9a` | `1fd066a9e5bef26373414988d9f98e04fb84a8d0d08f7af280eef7cb1779a497` |
| `global-earth` | `db1c185cf6b5def23064752847f585f3522c0b971460d9c688b424cb04c706ae` | `b1bbcd60e71b65064455da3abaacdb239a433bafe08c46854a2ffcfc9c50de92` |

These identities derive from the exact axes and catalog-owned method relations
in this amendment. Any implementation that produces a different resulting
identity stops for contract correction and re-ratification rather than
silently updating this table.

Security impact remains high under WP12D's package-level classification even
though no authentication, authorization, upload limit, path containment, queue
topology, or secret boundary changes. A fresh dedicated amendment-5 security
review is required before checkpoint. The main risks are a forged preset
classification broadening schema-v1 authority, divergence
between UI and paired mutations, and unsafe fallback when the live registry is
unavailable. Exact rematerialization from server-owned current parent sources,
manifest validation, shared server-side authority helpers, fail-closed registry
errors, and direct no-mutation/no-enqueue tests contain those risks. A run-local
actor who can change only project artifacts cannot satisfy rematerialization by
recomputing self-asserted hashes. Modification of canonical deployed config
sources is outside the run-artifact threat boundary and remains controlled by
the deployment/revision integrity gate.

## Exact source boundary

Production implementation may change only these exact paths:

- `wepppy/nodb/locales/__init__.py`;
- `wepppy/nodb/locales/climate_catalog.py`;
- `wepppy/nodb/locales/landuse_catalog.py`;
- `wepppy/nodb/locales/locale_profiles.py`;
- `wepppy/nodb/locales/capability_graph.py`;
- `wepppy/nodb/locales/capability_structures/catalog.json`;
- `wepppy/nodb/locales/capability_structures/README.md`;
- `wepppy/nodb/project_config_capabilities.py`;
- `wepppy/nodb/project_config_capabilities.pyi`;
- `wepppy/nodb/project_config_reader.py`;
- `wepppy/nodb/project_config_reader.pyi`;
- `wepppy/nodb/project_config_snapshot.py`;
- `wepppy/nodb/core/climate_station_catalog_service.py`;
- `wepppy/nodb/core/landuse.py`;
- `wepppy/nodb/core/landuse.pyi`;
- `wepppy/nodb/config_builder/registry.py`;
- `wepppy/nodb/config_builder/resolver.py`;
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`;
- `wepppy/weppcloud/routes/nodb_api/climate_bp.py`;
- `wepppy/weppcloud/routes/nodb_api/climate_bp.pyi`;
- `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`;
- `wepppy/microservices/rq_engine/climate_routes.py`;
- `wepppy/microservices/rq_engine/upload_climate_routes.py`;
- `wepppy/microservices/rq_engine/landuse_routes.py`;
- `wepppy/microservices/rq_engine/schema_defaults_routes.py`; and
- `wepppy/microservices/rq_engine/orchestration_read_routes.py`.

Direct regression changes may occur only in:

- `tests/nodb/test_climate_catalog.py`;
- `tests/nodb/test_landuse_catalog.py`;
- `tests/nodb/test_locale_capability_authority.py`;
- `tests/nodb/test_project_config_capabilities.py`;
- `tests/nodb/test_project_config_reader_foundation.py`;
- `tests/nodb/test_project_config_builder_snapshot.py`;
- `tests/nodb/test_project_config_registry_serializer.py`;
- `tests/nodb/test_project_config_preset_snapshot.py`;
- `tests/nodb/test_project_config_update.py`;
- `tests/nodb/test_climate_station_catalog_service.py`;
- `tests/nodb/test_landuse_build_event_contracts.py`;
- `tests/weppcloud/routes/test_config_builder_ui.py`;
- `tests/weppcloud/routes/test_pure_controls_render.py`;
- `tests/weppcloud/routes/test_climate_bp.py`;
- `tests/weppcloud/routes/test_landuse_bp.py`;
- `tests/microservices/test_rq_engine_climate_routes.py`;
- `tests/microservices/test_rq_engine_builder_routes.py`;
- `tests/microservices/test_rq_engine_upload_climate_routes.py`;
- `tests/microservices/test_rq_engine_landuse_routes.py`;
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`; and
- `tests/microservices/test_rq_engine_orchestration_read_routes.py`.

The canonical and work-package promotion map is exactly:

- this decision artifact owns the exact delta, state matrix, source boundary,
  review sequence, and ratification text;
- `docs/schemas/project-owned-config-contract.md` owns stored/live authority,
  exact matrices, structural identities, rollout, and regression evidence;
- `docs/adrs/ADR-0047-project-config-locale-authority.md` owns parameterization,
  stable/runtime mappings, relations/defaults, rationale, and rollback;
- `docs/schemas/project-owned-config-implementation-roadmap.md` owns WP12D,
  PC-24, and the WP12 promotion dependency;
- `docs/schemas/rq-controller-state-contract.md` and
  `docs/schemas/rq-engine-agent-api-contract.md` own RQ discovery/mutation
  parity; `docs/schemas/rq-response-contract.md` remains the unchanged error
  envelope;
- `docs/ui-docs/controller-contract.md` owns server-authority rendering and the
  land-cover default/non-restriction rule;
- `docs/work-packages/20260827_project_config_run_ui_authority/package.md`,
  `tracker.md`, the active ExecPlan, `artifacts/20260827_contract_decision.md`,
  and `artifacts/20260827_surface_matrix.md` own package scope, chronology,
  execution sequencing, supersession, and surface inventory; and
- `PROJECT_TRACKER.md` owns initiative status and the production hold.

The review records are exactly
`artifacts/20260828_amendment5_contract_correctness_review.md`,
`artifacts/20260828_amendment5_contract_governance_review.md`, and
`artifacts/20260828_amendment5_security_contract_review.md`. After advisory
reviews report READY, the operator must ratify the exact amendment. Codex then
records ratification status/time and obtains fresh binding READY reviews in all
three artifacts. Only then may a documentation-only checkpoint commit. Its
exact revision must be an ancestor of every amendment-5 production or test-code
change. The append-only structural reader floor is a later standalone commit
and must precede every graph writer change and Forest writer deployment.

The climate and landuse controller JavaScript and templates are non-change
assertions. Config links, soil behavior, model tuples, feature flags,
authentication, queue topology, provider algorithms, migrations, production
deployment, and unrelated dirty files are excluded. A needed change outside
these exact paths stops work for amendment and re-ratification.

## Required regression and Forest evidence

- Lock the exact five-row climate matrix, numeric mappings, method relations,
  Vanilla defaults, and User-Defined upload behavior.
- Lock the expanded synthesized registry component inventory and deterministic
  registry digest for every newly Builder-exposed climate and land-cover ID.
- Lock the rq-engine Builder description's exact five-locale climate/land-cover
  graph envelopes and create one project with a non-default land-cover selection,
  proving its runtime/default selection changes while the complete locale graph
  persists.
- Prove `closing-plump/eu-disturbed`-equivalent schema-v1 preset state renders,
  advertises, and accepts exactly Vanilla, E-OBS Modified, and User-Defined,
  while rejecting PRISM, Daymet, gridMET, DEP NEXRAD, Future CMIP5, AGDC, and
  deprecated storm modes before mutation or enqueue.
- Prove non-preset/invalid/unknown schema-v1 states, digest mismatch, and shape-
  valid hostile manifests with forged or filename/parent-chain-incongruent
  preset identity retain compatibility and do not consult the live registry.
- Prove a fully self-consistent forged manifest/config pair with recomputed
  project-local hashes fails canonical rematerialization; parent-source drift,
  non-allowlisted/forged overrides, and rematerialized/stored locale mismatch
  also remain compatibility-only with zero registry calls.
- Prove unavailable/malformed/inconsistent preset policy is diagnostic 503,
  never compatibility fallback, and has zero file/timestamp/reservation/
  mutation/enqueue side effects after auth/run-access precedence.
- Prove every locale's Builder land-cover selection changes only the serialized
  runtime/default selection while its stored graph and run control retain the
  complete locale envelope; specifically prove Canada resolves C3S, not US.
- Append and validate all new schema-v3 structure identities, reopen every old
  identity, and preserve the historical schema-v2 graph byte-for-byte.
- Prove paired run page, Flask, rq-engine, schema/default/error, operation,
  pipeline, and readiness surfaces advertise exactly what mutation enforces.
- For a graph-authoritative run, `/tasks/upload-cli/` MUST require
  `user_defined_cli` in the same resolved climate axis before reading or saving
  the multipart file, removing timestamps, reserving, or enqueueing. It has no
  outside-authority exact-current carveout because uploading replaces climate
  content rather than rebuilding unchanged. Compatibility states with no graph
  retain their established upload behavior. Test stored schema-v2/v3 denial,
  projected/live allowance, registry/authority errors, and zero file/timestamp/
  reservation/enqueue side effects on denial.
- Exercise malformed submissions and registry failure directly and prove no
  NoDb mutation, run-file write, reservation, or enqueue.
- Deploy the reader floor and then writer candidate only to exact host
  `forest`, without rebuilding the source-mounted image; prove reader-floor
  rollback reopens the newly refreshed graph unchanged. Production remains
  excluded.
- Bind Forest evidence to the exact candidate registry, provider, and deployed
  revision. Execute real, unmocked DEP NEXRAD, Future CMIP5, and User-Defined
  `.cli` upload/validation/build paths. For the expanded US land-cover envelope,
  validate provider availability for every advertised year and perform a real
  fetch/build for one annual NLCD, one NLCD Ever Forest, and one eMapR vote
  dataset. Reused evidence is allowed only when its recorded registry,
  provider, and deployment revisions exactly match the candidate; otherwise
  the executions must be repeated. Mocked executable/provider-call assertions
  do not satisfy this gate.

## Exact ratification

The operator supplied this exact ratification on 2026-08-28 16:29 UTC:

> I explicitly ratify amendment PC-24/WP12D-20260828-5 exactly as currently
> documented, authorize its standalone checkpoint and subsequent
> implementation, preserve all existing commits and stored graph identities,
> and keep merge and production reserved to WP12.
