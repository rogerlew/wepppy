# Discovery and decision register

**Inspected**: 2026-09-25 UTC
**Starting revision**: `b96f77e589ec033853970ac90fdab945490c6553`
**Evidence level**: source inspection only; no parser experiments or runtime validation

Paths below are repository-relative. Findings describe current implementation;
they do not make existing behavior the specification for this feature.

## Current implementation and challenges

| Surface | Source evidence | Consequence |
| --- | --- | --- |
| Mode identities | `wepppy/nodb/core/landuse.py::LanduseMode`: `UserDefined = 4` is raster upload; `wepppy/nodb/core/soils.py::SoilsMode`: `SingleDb = 2`, `UserDefined = 2` | Use additive identities; do not reuse the existing names/values with changed meaning. |
| UI primitives | `wepppy/weppcloud/templates/controls/landuse_pure.htm`, `soil_pure.htm`, `disturbed_sbs_pure.htm`, `_pure_macros.html` | Reuse `ui.file_upload` and `ui.text_display`, including the SBS `<code>` feedback pattern. |
| Transport | `wepppy/weppcloud/controllers_js/landuse.js` submits FormData; `soil.js::build` uses URL-encoded form serialization | Soil upload needs multipart transport and matching route parsing. A file input alone will not send bytes. |
| Endpoint boundary | `wepppy/microservices/rq_engine/landuse_routes.py`, `soils_routes.py`, `schema_defaults_routes.py` | Update payload validation, mode checks, session-token behavior, schemas, error responses, and hydration together. |
| Existing management validation | `wepppy/weppcloud/routes/nodb_api/landuse_bp.py::_validate_management_file` calls `read_management`; `_LANDUSE_MAN_UPLOAD_MAX_BYTES` is 5 MiB | Useful precedent, not evidence that parsing alone is a complete security policy. Existing catalog ZIP/multi-upload behavior is outside this scope. |
| Parser versions | `wepppy/wepp/management/managements.py` handles multiple management versions; `wepppy/wepp/soils/utils/wepp_soil_util.py` parses version/OFE counts and has separate serialization/version conversion paths | Define support based on parse-to-consumer evidence. A parseable file may still be incompatible with preparation or the chosen WEPP binary. |
| Uniform assignment | `Landuse._build_single_selection` assigns a catalog key to all hillslopes; `Soils._build_single` retrieves a Mukey from SSURGO | Existing “single” builders do not directly implement uploaded-file sources. Summary objects and stable assignment keys are required. |
| Cleanup | `Landuse.clean` preserves `user-defined/` and the custom mapping JSON; `Soils.clean` clears its directory | A directly uploaded source can disappear during rebuild unless preservation is deliberate. Inspect all callers and mode transitions. |
| Filesystem projections | Both controllers have `_clear_directory_preserving_symlink_mount` helpers | Containment must distinguish a legitimate NoDir projection root from attacker-controlled child symlinks. A blanket symlink prohibition could break valid projects. |
| Builder precedence | `Soils.build` checks Chile, configured soils maps, and Alaska before ordinary mode dispatch | Explicit upload selection must not silently run a locale/database builder; decide supported capability combinations and routing order. |
| Disturbance during building | `wepppy/nodb/mods/disturbed/disturbed.py::on` handles `LANDUSE_DOMLC_COMPLETE` and `SOILS_BUILD_COMPLETE` | Opted-in Builder projects exclude Disturbed; preserve ordinary completion hooks and unchanged unchecked/legacy behavior. |
| Later transformations | `wepppy/nodb/core/wepp_prep_service.py::prep_managements` applies disturbed replacements; `prep_soils` passes saturation, depth clipping, and conductivity settings downstream | Checked projects must exclude disturbed transformations through final preparation; preserve compatible modifiers on generated copies. |
| Multi-OFE | Landuse template disables current Single mode when `wepp.multi_ofe`; `Landuse.validate_landuse_mode_for_mofe` enforces it | Multi-OFE means multiple overland flow elements within a hillslope. Uniform uploaded material does not automatically supply the grids/segment assembly current builders expect. |
| Configuration authority | `wepppy/nodb/project_config_capabilities.py`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`, both templates and RQ routes | New modes must exist in resolved capability relations and UI/API allowlists, not only enums. Legacy and project-owned configurations need explicit treatment. |

## Settled decision: independent mode selection under Builder policy

The operator directed reconciliation around the Builder checkbox on 2026-09-25.
The earlier per-input disturbance-bypass matrix is superseded. Independence means
users select landuse and soil input modes independently within a project whose
creation-time policy is already fixed.

| Builder option | Run input modes | Required behavior |
| --- | --- | --- |
| Unchecked or existing legacy project | Existing modes | Preserve current disturbance, features, and buffer behavior; no new upload capability. |
| Checked | Both existing modes | Disturbed/SBS, dependent features, and buffer OFEs remain disabled. |
| Checked | Uploaded landuse, existing soil | Replicate uploaded landuse across all non-buffer OFEs; use selected ordinary soil builder without Disturbed. |
| Checked | Existing landuse, uploaded soil | Use selected ordinary landuse builder without Disturbed; replicate uploaded soil across all non-buffer OFEs. |
| Checked | Both uploaded | Replicate both sources across all hillslopes and non-buffer OFEs; retain compatible modifiers. |

Class selectors, inheritance, SBS-remapping choices, and legacy-only availability
are excluded from this package. See the [Builder design](builder_upload_option_assessment.md).
Product scope is settled; canonical contract amendments and approval remain pending.

## Buffer OFE policy

The operator specifically requires buffer OFEs disabled whenever the Builder
feature is enabled. This excludes buffer geometry, not merely its catalog
management override. Set `watershed.mofe_buffer = false` in resolved state, disable
buffer controls, reject attempts to enable them through APIs, and verify no buffer
segment in generated slope/management/soil inputs. Run-mode switches, refresh,
clone, and restore must preserve the policy. Ordinary/legacy buffer behavior is
unchanged. This is the explicit exception to retaining other compatible modifiers.

## Decision register

Rows marked settled reflect operator decisions; remaining recommendations need
resolution and evidence before the implementation checkpoint.

| ID | Choice or challenge | Recommendation / evidence needed |
| --- | --- | --- |
| D1 | Supported `.man`/`.sol` versions, WEPP binary compatibility, one versus multiple OFEs, management rotation length | Recommend management 98.4/2016.3 and soil 7778 for the non-disturbed Builder scope, with one-OFE source files replicated across the project. Prove supported content and binary compatibility; see the current assessment. Do not truncate multi-OFE uploads. |
| D2 | Do non-disturbed modifiers still apply (soil saturation, `kslast`, depth clipping, cover overrides, RAP/tree canopy, irrigation, management year expansion)? | Settled: compatible non-disturbed modifiers remain functional, except buffer OFEs are disabled at project scope. Preserve source bytes; document transformations on generated copies and test every OFE. Do not promise identical final parameters where modifiers vary. |
| D3 | Availability in multi-OFE projects and special configurations | Settled: multi-OFE must work, replicating the source across every hillslope and OFE. Build a non-disturbed soil-stack path; retain mode independence. Builder scope is settled; buffer OFEs are disabled, while ordinary multi-OFE support remains mandatory. |
| D4 | Metadata for ordinary disturbed soils paired with uploaded landuse | Closed by scope: the Builder policy disables Disturbed for the whole opted-in project. No class selectors, inheritance, or mixed-disturbance metadata contract is required. |
| D5 | Upload on file selection versus existing Build action | Prefer upload/validate on Build, matching the landuse flow, with reload showing the last accepted server filename. Distinguish a newly selected local filename, an accepted upload, and a completed build. |
| D6 | Missing input, replacement, concurrent jobs, switch away/back, delete | Prefer reuse of an accepted source when no new file is sent, explicit validation error if none exists, atomic replacement, and retaining source on mode switches. Resolve whether a remove action is needed; do not add one by assumption. A running build must not mix old and replacement bytes. |
| D7 | File naming and directory layout | Separate escaped original display name from a server-controlled storage name, preserving the accepted source under its module directory. Decide direct child versus visible input subdirectory and retention across clean/archive/clone. Guard collisions with generated files and same sanitized names. |
| D8 | Bounds, encoding, validation strictness, and failures | Reuse the 5 MiB management limit as a candidate; measure soil fixtures before choosing a soil limit. Specify byte/record/count limits, accepted text encodings, finite numbers, structural references, unsupported/trailing content policy, and safe error detail. Bounds must preserve valid formats. |
| D9 | Capability IDs and configuration migration | Add distinct unused mode values and capability IDs. Decide supported locale/representation/binary combinations and legacy defaults; do not bypass config authority globally to expose the radio buttons. |
| D10 | Interaction with treatments, Omni scenarios, batch projects, reports, and optional mods | Exclude dependent features listed in the completed dependency review. Preserve and validate compatible features and modifiers; enforce exclusions in activation, tasks, and refresh. Treatments/Omni are not supported in opted-in projects. |
| D11 | Failed-upload retention versus artifact observability | Keep accepted sources and useful failed-build diagnostics inspectable/archivable. Decide bounded handling of rejected untrusted bytes without installing them as active input or retaining arbitrary hostile content indefinitely. |

## Secure-upload acceptance envelope

Treat extension and browser `accept` as usability checks, never security proof.
At the authenticated, run-authorized boundary enforce read-only restrictions and
existing CSRF/session-token contracts. Limit multipart and streaming bytes before
full buffering, accept one plain text file of the expected type, and reject empty,
malformed, or incompatible input with actionable bounded error details.

Audit the owned parsers for count-driven resource use, malformed references,
non-finite numeric values, unexpected file/network access, and trailing payloads.
No shell execution, dynamic evaluation, or untrusted object deserialization is
needed. Do not claim malware detection from successful parsing. Prefer bounded
validation with existing dependencies over a new scanner/service.

Stage before publication; prevent traversal, absolute-path writes, child symlink
escapes, and generated-file collisions. Validate and install the same bytes.
Coordinate filesystem publication with NoDb locking/cache invalidation; failed
validation or publication must leave the previous valid source and metadata
usable. Do not enqueue a build until the upload is accepted. Specify enqueue
failure separately so a saved source is not mislabeled as a completed build.

## Required state and regression coverage

Test never-used/absent metadata, empty module roots, populated sources, legacy
saved modes, missing referenced source, hostile paths/content, read-only projects,
and legitimate archive projections independently from mode combinations.
Inputs include lower/uppercase suffixes, rejected types, truncated files,
oversize uploads, invalid references/counts, unsupported versions, non-finite
values, unusual filenames, same-name replacements, and concurrent upload/build.
Decide mixed-case suffix handling explicitly; lower/uppercase support is required.

Verify refresh and failure feedback in the browser; keyboard labels, themes,
read-only filename visibility, and escaped names must match existing conventions.
Read accepted bytes, summary parquet, and every hillslope's prepared input using
real parsers. Run fresh WEPP execution with independent uploaded/database combinations in
opted-in non-disturbed projects and separate unchecked/legacy regressions,
and demonstrate source survival through repeated builds, mode switches, clones,
and archive/restore. Use all-hillslope assignment checks, not only one sample.

## Candidate canonical contract matrix

The implementation checkpoint must record exact sections and normative deltas
for shared `docs/ui-docs/controller-contract.md`; project authority in
`docs/schemas/project-owned-config-contract.md`; NoDb persistence/concurrency;
RQ responses and controller state; CSRF; `docs/schemas/wepp-run-input-contract.md`;
the feature-registry specification, watershed/buffer specifications, and affected
landuse modification contracts. Inventory nearest
AGENTS-named specifications before finalizing this matrix.

No dedicated current landuse-build/soils contract was found in
`docs/ui-docs/contracts/` during this inspection. Historical July UI packages are
provenance only. Propose a current
`docs/ui-docs/contracts/single-user-defined-landuse-soils-contract.md` for the
accepted source lifecycle, Builder policy, independent mode choices, and buffer exclusion, cross-linked from affected
current contracts. Do not treat this discovery note as that canonical contract.
