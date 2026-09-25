# Add Builder-enabled Single User-Defined landuse and soils


Maintain this living plan under `docs/prompt_templates/codex_exec_plans.md`, including
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective.
This is the active plan for `20260925_single_user_defined_landuse_soils` only.
Current work resolves planning findings; production implementation and deployment
have not started and are not authorized by this documentation revision.

## Purpose / Big Picture


A user checks “Enable single landuse and soils upload” while creating a Builder
project. That project excludes Disturbed, SBS (soil burn severity), dependent
features, and buffer OFEs (extra overland-flow segments used for buffers). The
user can then independently choose “Single User-Defined” landuse, soils, or both.
A validated `.man`/`.MAN` or `.sol`/`.SOL` source is replicated across every
hillslope and OFE in the non-buffer topology. Existing compatible modifiers still
operate on generated copies. Source filenames use the standard SBS feedback style.

The checkbox is a creation-time policy, unchecked by default. Unchecked preserves
current Builder behavior and does not expose new upload modes. Checked keeps
Disturbed/SBS and buffers disabled even if neither run control currently uses an
upload. Independent mode selection does not mean independent disturbance policy.
Existing projects are not converted, and no Disturbed Class selectors are needed.

## Progress


- [x] (2026-09-25 UTC) Inspect mode enums, parsers, builders, controls, configuration authority, and final preparation.
- [x] (2026-09-25 UTC) Complete delegated dependency review and independent work-package review.
- [x] (2026-09-25 UTC) Operator directs Builder-scope reconciliation and disables buffer OFEs whenever the feature is enabled.
- [x] (2026-09-25 UTC) Rewrite plan around Builder policy; create pre-checkpoint design security artifact.
- [x] (2026-09-25 UTC) Reviewer confirms WPR-01, WPR-02, and WPR-03 planning findings closed.
- [ ] Finalize format/content, source OFE count, upload lifecycle/bounds, and exact interfaces.
- [ ] Complete canonical amendments, ADR, independent design security and contract reviews, and contract ancestor checkpoint.
- [ ] Implement Builder serialization/resolution, feature/buffer policy, and refresh preservation.
- [ ] Implement validated source lifecycle, additive modes, and non-disturbed single/multiple-OFE preparation.
- [ ] Implement themed run controls and user-visible error/filename round trips.
- [ ] Complete artifact/environment acceptance, implementation reviews, and documentation closeout.

## Surprises & Discoveries


`LanduseMode.UserDefined = 4` already means raster upload; `SoilsMode.UserDefined =
2` aliases a database mode. Soil form submission is URL-encoded. Module cleanup can
remove uploaded files. Current MOFE soil assembly occurs in Disturbed, so the new
non-disturbed path needs explicit assembly even when only landuse is uploaded.

Feature dependencies are incompletely declared. The retained dependency review
identifies actual runtime prerequisites and distinguishes RAP analysis, Ash, and
Geneva from workflows that require Disturbed. Menu, section visibility, feature
enabling, and direct task submission are separate policy boundaries.

Buffer source override occurs independently of Disturbed in
`wepppy/nodb/core/landuse.py`. The operator resolved this by disabling buffer OFEs
for the entire opted-in configuration. The old per-domain bypass plan and its
mixed-SBS acceptance matrix are superseded, not additional implementation duties.

## Decision Log


On 2026-09-25 the operator initially requested independent uploaded inputs without
disturbed parameterization. After exploring class selectors and legacy-only scope,
the operator directed reconciliation around the Config Builder checkbox. Independent
landuse/soil run-mode choice remains; project-wide exclusion of Disturbed/SBS and
dependent features is now explicit. This avoids class inheritance and SBS-remapping
contracts while preserving unchecked/legacy behavior.

On 2026-09-25 the operator required multi-OFE replication and retained compatible
modifiers, then explicitly instructed “disable the buffer ofe when this feature is
enabled.” Buffer geometry and its management override are both disabled, not merely
reassigned to the uploaded management. This applies regardless of current run modes.

On 2026-09-25 the operator directed immediate correction of WPR-01 and WPR-03.
Design-level security review is a pre-checkpoint obligation. Runtime validation
extends that artifact later; documentation correction is not security sign-off.

Use existing parsers, jobs, transport, locks, and UI macros, with additive enum
identities. No new service, queue, datastore, dependency, or deployment topology
is budgeted. Format and lifecycle recommendations require explicit checkpoint
resolution and evidence before implementation.

## Outcomes & Retrospective


Source discovery and static dependency review are complete. The package now has
one Builder policy and explicit buffer exclusion. The reviewer independently confirmed all three planning corrections. No production code or live projects changed. Pending
format/lifecycle decisions and the canonical checkpoint still prevent claiming
implementation readiness or a working feature.

## Context and Orientation


Work from `/home/workdir/wepppy`; starting revision is
`b96f77e589ec033853970ac90fdab945490c6553`. Read nearest AGENTS for NoDb, WEPPcloud,
controllers JS, rq-engine, and tests before editing those subsystems.

Builder selection and snapshots live in `wepppy/nodb/config_builder/schema.py`
and `snapshot.py`; `resolver.py` currently injects Disturbed unconditionally.
`wepppy/nodb/project_config_update.py` reconstructs selections and refreshes the
capability graph. `wepppy/nodb/project_config_capabilities.py` gates run modes.
Builder UI is `wepppy/weppcloud/templates/config_builder.htm` and
`wepppy/weppcloud/controllers_js/config_builder.js`.

Feature metadata/runtime live in `wepppy/weppcloud/feature_registry/`; activation
is in `routes/nodb_api/project_bp.py`, and run-section visibility is in
`routes/run_0/run_0_bp.py`. All paths below with `routes/` are under
`wepppy/weppcloud/`. SBS upload is in
`wepppy/microservices/rq_engine/upload_disturbed_routes.py`. The dependency review
names the other affected feature/task boundaries; do not rely on registry entries
alone or overwrite valid legacy BAER alternatives with a global dependency rule.

Buffer controls are in `templates/controls/subcatchments_pure.htm` and
`landuse_pure.htm` under WEPPcloud. Watershed state is in
`wepppy/nodb/core/watershed.py`; payload parsing is in
`wepppy/microservices/rq_engine/watershed_routes.py`, with schema metadata in
`schema_defaults_routes.py`. Builder resolution must set `watershed.mofe_buffer`
false and runtime mutation/build paths must enforce the selected policy.

Run upload controls are `landuse_pure.htm` and `soil_pure.htm`; their JS is
`controllers_js/landuse.js` and `soil.js`. Reuse `_pure_macros.html::file_upload`
and `text_display` as used by `disturbed_sbs_pure.htm`. Build routes are
`wepppy/microservices/rq_engine/landuse_routes.py` and `soils_routes.py`;
`wepppy/rq/project_rq.py` owns existing build jobs.

Source state/builders live in `wepppy/nodb/core/landuse.py` and `soils.py`.
Management parsing is `wepppy/wepp/management/managements.py`; soil parsing is
`wepppy/wepp/soils/utils/wepp_soil_util.py`. Owned multi-OFE synthesis utilities
compose files for the real watershed topology. `core/wepp.py` and
`core/wepp_prep_service.py` under NoDb prepare the files consumed by WEPP.

## Plan of Work


### Milestone 1: complete the design and pre-implementation checkpoint


Use `notes/discovery.md` and `notes/builder_upload_option_assessment.md` to resolve
remaining format/content, one-OFE source, byte/count bounds, encoding, publication,
concurrency, retention, and interface decisions. Recommended initial versions
are management 98.4/2016.3 and soil 7778; parser acceptance alone is insufficient.
Define enum values, strict Builder boolean serialization, capability IDs, form
fields, metadata, summary keys, canonical errors, and supported binary/config
combinations before coding. Preserve existing schema keys and write the brief
compatibility/regression plan before any data mutation.

Prepare `artifacts/20260925_contract_decision.md` with baseline revision, stable
amendment ID, exact current-contract/source matrix, operator decisions, security
impact, compatibility, valid states, error policy, and generated-input acceptance.
Amend current canonical contracts outside the package, including the explicit
exception to ADR-0064's unconditional Builder Disturbed policy, buffer exclusion,
feature-registry semantics, and upload lifecycle. Capture scientific rationale
and operator provenance in the parameterization ADR. Mark conformance pending.

The dedicated `artifacts/20260925_security_review.md` already contains the design
review scope. Finalize unresolved design choices and obtain independent security
review before the canonical checkpoint. Record findings/dispositions without
claiming runtime evidence. Obtain the required two independent contract reviews
and exact operator approval under `docs/standards/contract-first-change-standard.md`.
Close medium/high design findings and obtain post-fix confirmation, then record
the standalone contract ancestor before implementation. If commit authority is
missing, prepare the complete reviewable checkpoint before requesting it.

### Milestone 2: Builder policy, exclusions, and refresh


Add the strictly validated creation-time boolean, default false when omitted,
to Builder parsing, review/create serialization, generated config, manifest, and
provenance. Checked enables additive upload capabilities for both representations;
unchecked preserves current defaults and effective Disturbed modules. Do not force
a run mode or upload. Preserve dataset selections and compatible modifiers.

For checked projects omit Disturbed/SBS dependencies, exclude the direct/transitive
features in the reviewed matrix, and enforce the policy across menus, sections,
feature enabling, and direct tasks. Validate the whole dependency-enable operation
before changing mods or restoring backups. Do not re-enable excluded controllers
to satisfy a request. Keep compatible RAP analysis, Ash, Geneva, and independently
supported features available; retain their specific acceptance checks.

Set `watershed.mofe_buffer = false` in resolved configuration. Disable buffer
geometry controls and the buffer-landuse selector with an explanation. Reject API
attempts to enable buffers before mutation/enqueue. Existing disabled buffer settings
may remain for compatibility, but cannot create geometry or apply source overrides.
At build/rebuild boundaries reject inconsistent enabled-buffer state explicitly;
do not silently regenerate topology under a different policy. No buffer OFE may be
emitted, whether neither, one, or both run controls select uploaded inputs.

Extend config-update selection reconstruction, graph resolution, congruence checks,
preview/apply, and source preservation so refresh cannot drop the flag, restore
Disturbed/dependents, or enable buffers. Creation-time-only scope does not migrate
existing projects. Acceptance covers checked/unchecked/omitted/invalid booleans,
review-create parity, forbidden API calls, dependency closure, refresh, and legacy
BAER/buffer behavior. No runtime flag-toggle workflow is introduced.

### Milestone 3: accepted sources and non-disturbed build/preparation


Add unused mode values and optional source metadata with legacy absent-state reads.
Use stable summary keys and distinguish escaped display names from storage names.
Stage bounded uploads, validate syntax/semantics against the allowed subset, and
publish the exact validated bytes within the proper module directory under normal
NoDb locking/cache contracts. Preserve the previous source/state after rejection,
conflict, or disk failure. Specify enqueue failure separately from upload acceptance
and keep useful diagnostics inspectable under the approved retention policy.

Extend builders to assign accepted sources to every hillslope and every OFE in
the actual non-buffer topology. Do not let locale/map precedence silently override
upload mode. Retain accepted sources through clean/rebuild and mode switches.
Provide the non-disturbed MOFE soil-stack writer, including ordinary soil modes
paired with uploaded landuse. Reuse owned synthesis utilities, verify management
rotation references/counts, and preserve intended soil `ksflag` and file version.
Slope, management, and soil OFE count/order must match without buffer segments.

Preserve compatible modifiers on generated copies and ordinary completion effects.
Do not add per-domain Disturbed bypass or mixed-SBS behavior. Test all four input
combinations in opted-in projects and separately verify unchecked/legacy controls
retain existing disturbance and buffer semantics. Direct parser/filesystem/build/
serializer evidence must compare semantic content at the consumed-file boundary.

### Milestone 4: themed controls and round trips


Add “Single User-Defined” and the standard themed file-upload controls. Explain
accepted file types, replication across all hillslopes/OFEs, and no disturbed
parameterization in this project. Show the accepted filename with escaped `<code>`
in `ui.text_display`, including read-only views and reload. Proposed labels are
“Current landuse file” and “Current soil file.” A local file chooser cannot be
rehydrated; server feedback must be separate.

Implement the approved upload timing and soil multipart transport. Preserve
session-token/CSRF behavior, canonical errors, schema metadata, status updates,
and failure/retry behavior. Keep capabilities synchronized with the Builder policy.
Changing a run input mode must not restore disabled features or buffer controls.
Add tests before controller changes and verify keyboard/theme behavior and current
filename retention after rejected replacements.

### Milestone 5: evidence and closeout


Use a representative production-equivalent development project and record revision,
config, identities/groups, mounts, source hashes, and job tree. Exercise request,
durable state, summaries, all-hillslope/OFE prepared inputs, fresh execution, and
filename/report readback. Include compatible modifiers, mode switches, repeated
builds, clone/archive/restore, and no-buffer geometry checks. Compare unchecked
and legacy workflows separately; tests must not submit valid uploads with SBS in
an opted-in project because that combination is excluded by contract.

Extend the existing security artifact with real boundary/environment evidence and
complete the separate correctness/UX artifact. Resolve medium/high findings before
closeout. Update affected user/operator/developer docs, canonical contracts, plan,
tracker, and PROJECT_TRACKER. Distinguish locally/environment validated from deployed;
deployment remains outside this request.

## Concrete Steps


From `/home/workdir/wepppy`, start with focused existing suites plus new tests
for the accepted Builder/feature/buffer contracts:

    wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py tests/microservices/test_rq_engine_soils_routes.py
    wctl run-pytest tests/nodb/test_landuse_build_event_contracts.py
    wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py tests/test_managements_module.py
    wctl run-npm lint
    wctl run-npm test

Locate existing Builder, config-update, feature-enable, and watershed tests using
`rg --files tests` and add focused policy regressions beside those tests. After
substantive implementation passes focused gates, run:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Run applicable stub checks. If queue wiring changes, update the dependency catalog,
run `wctl check-rq-graph`, and inspect a live job tree. Rebuild generated browser
assets according to controller instructions. Run scoped documentation lint and
spelling previews. Capture actual outcomes; no implementation gates have run yet.

## Validation and Acceptance


Separate project policy, input choices, and source states. Test checked, unchecked,
and legacy/absent flag; all four uploaded/database combinations where allowed;
never-used, empty, populated, legacy, missing-source, and hostile state; authorized
and read-only access; ordinary and legitimate projected module roots. Reject
unsupported types/versions, invalid references/counts, oversize/truncated input,
non-finite values, path escapes, forbidden features, and buffer-enable requests.
Security controls must also preserve valid fresh uploads and independent choices.

Read accepted hashes and semantic content of the actual consumed files under
`wepp/runs/`. Match OFE counts/order across slope, management, and soil; establish
no buffer OFE was produced. Repeat after changing either run mode, refresh, clone,
and restore. Unchecked/legacy projects keep their permitted buffers and disturbance
behavior. Validate all-hillslope assignment, not only one sample.

## Idempotence and Recovery


Repeat builds reuse accepted sources without deleting them or accumulating
transformations. Failed replacement leaves prior source/metadata usable. Resolve
partial publication/state/queue recovery before implementation. Reject inconsistent
policy explicitly rather than initializing Disturbed, adding buffer geometry, or
falling back to a catalog source. Preserve compatible settings and existing runs;
this is not a migration or fleet repair.

## Artifacts and Notes


The brief records current requirements; discovery lists remaining choices; the
Builder design and dependency artifact locate implementation boundaries. The
work-package review retains initial findings and correction disposition. The
security artifact exists at design stage with independent approval pending.
No runtime or deployment evidence is claimed.

## Interfaces and Dependencies


Reuse existing Pure macros, owned parsers/synthesis utilities, build routes/jobs,
NoDb locks/scoped mutation, feature registry, and capability resolution. Specify
all concrete new field names/values and error contracts during Milestone 1.
Amend schema/stubs and API metadata together. No external dependency is proposed.

Revision note (2026-09-25 UTC): Replaced the superseded per-domain disturbance
plan with the operator-selected Builder policy; disabled buffer OFEs at project
scope; moved design security review before the checkpoint and made Builder,
feature, buffer, and refresh implementation explicit. Independent re-review confirmed all three planning
findings closed; security approval and the canonical checkpoint remain pending.
