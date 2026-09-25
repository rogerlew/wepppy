# SUDI-01 contract checkpoint

## Authority, revision and classification

Starting implementation: `cb09ab422` (all-worktree snapshot requested by operator;
prior runtime baseline `b96f77e589ec033853970ac90fdab945490c6553`).
Operator explicitly instructed “commit everything in the worktree and then execute
the work package” on 2026-09-25, following approval of independent upload modes,
Builder-wide Disturbed/dependency exclusion and disabled buffer OFEs. This is
execution/commit authority for that finite cross-owner composition, not deployment
or advancement/closure of unrelated owner packages. Engineering choices below
resolve the approved plan's remaining details. No runtime edits precede checkpoint.
Classification: intended enhancement; conflicts with unconditional Builder
Disturbed and buffer preservation are explicit opt-in exceptions, not incidental
conformance fixes. Security impact: high (untrusted text and filesystem publication).

## Exact contract/source matrix

| Current contract | Normative delta | Covered implementation boundary |
| --- | --- | --- |
| `docs/schemas/single-user-defined-inputs-contract.md` (new) | Exact flag, mode identities, capabilities, formats/bounds, source lifecycle, errors, independent choices, valid states and acceptance | New bounded upload/policy helpers; `nodb/core/{landuse,soils,watershed,wepp,wepp_prep_service}.py`; owned management/soil parsers/synthesizers only where required for strict validation and replication |
| `docs/schemas/project-owned-config-contract.md`, ADR-0064, new ADR-0075 | Checked creation-time opt-in exception, strict boolean, manifest/config/provenance, refresh and capability relations | `nodb/config_builder/{schema,snapshot,resolver,registry}.py`, `nodb/locales/capability_graph.py`, `nodb/project_config_{capabilities,update}.py`; Builder routes, template and controller |
| `wepppy/weppcloud/feature_registry/specification.md` | Project policy exclusion precedes activation/dependency restoration and discovery | Feature registry metadata/runtime; `routes/nodb_api/project_bp.py`, `routes/run_0/run_0_bp.py`; SBS/dependent routes and RQ workers from retained dependency matrix; module entry methods as defense against direct calls |
| `docs/ui-docs/controller-contract.md` | Checkbox, Pure upload and filename feedback, multipart soil submission and policy/refresh presentation | `controllers_js/{config_builder,landuse,soil}.js`, affected tests/generated bundle; `templates/{config_builder,controls/landuse_pure,controls/soil_pure,controls/subcatchments_pure}.htm`, shared context and request metadata |
| `docs/schemas/mofe-management-artifact-contract.md`, `landuse-modification-contract.md`, `wepp-run-input-contract.md` | Uniform source across non-buffer topology, compatible modifiers, retained soil flag/version, policy enforcement before preparation | Core builders/preparation, watershed buffer setter/build, rq-engine watershed/schema defaults, ordinary cover/summary regeneration |
| `docs/schemas/rq-response-contract.md`, `weppcloud-csrf-contract.md`, `nodb-persistence-concurrency-contract.md` | No exception: retain envelopes/auth/locks/fresh hydration/cache and errors | Existing build routes/jobs and NoDir scoped mutation; no new queue topology or privilege |
| `docs/standards/artifact-observability-standard.md`, `generated-artifact-validation-standard.md` | No exception: visible input/output/status and real consumed-file evidence | Normal browse/download/clone/archive/restore, summaries/parquet and `wepp/runs/*` acceptance |

The concrete feature exclusion set is Disturbed/SBS, Treatments, Omni and
contrasts, Path CE, legacy debris flow, RUSLE, postfire debris flow and
fire/revegetation transforms. RAP analysis, Ash, Geneva and compatible features
remain. No new external dependency, queue/service/store, numerical formula,
lookup contents, authentication, unrelated capability domain, existing-project
migration, or production deployment is in scope. Helper extraction is limited to
this policy and upload boundary. Existing parser behavior for trusted/catalog
files remains compatible; strict validation belongs to uploaded sources.

## Concrete design resolution and rationale

The new canonical contract is the normative source. Mode5 is unused in both
enums. Stable ID `single-user-defined` distinguishes new file sources from raster
upload and database aliases. Strict optional boolean defaults false and preserves
existing behavior. Each source has one OFE; owned synthesis replicates it, avoiding
ambiguous multi-profile assignment. Soil7778 avoids legacy parameter estimation
and disturbed900x transforms. Management98.4 matches owned/native support;2016.3 is rejected because the native
reader drops modern fields, despite Python support. Resource bounds use
5MiB existing management precedent, physical row/token limits, bounded reference
collections and 10 soil horizons. Parser audit and direct fixtures refine evidence
before checkpoint approval; tests must prove no silent repairs or trailing input.

Immutable hash-named sources separate display names from storage and prevent
partial overwrite of active input. Metadata publication selects the generation;
canonical locks and active-job exclusion protect consistency. Keep current plus
previous generation and clean only unreferenced idle generations. Queue failure
after accepted input does not roll back accepted bytes; explicit retry reuses them.
Rejected bytes are not retained. Raw inputs remain visible and archive-covered.
No hidden staging service or alternative source inventory is introduced.

## Compatibility and regression plan (before schema mutation)

Add only boolean selection/config/capability values, mode5 and optional source
metadata; no existing key, enum, parquet column or output path is renamed. Absent
metadata/flag remains valid. Preserve config digest/manifest validation and exact
module congruence, with explicit checked effective list. Source filenames and
summary IDs are distinct from storage paths. Test new flag through review/create,
refresh/clone/restore, absent/false legacy cases and invalid booleans. Test four
input combinations and both representations; match final slope/management/soil
counts/content, flags, cover/saturation/depth modifiers and source hashes. Separate
unchecked Disturbed/BAER/buffer acceptance prevents global regressions.

## State and error matrix

The canonical contract's UI/state/error table is the required state matrix:
never-used and optional empty, accepted valid, supported legacy, malformed/hostile,
missing populated source, concurrent use, enqueue/build failure and restored state.
Cross it with flag absent/false/true; both mode choices independently; authorized/
read-only; ordinary/projected roots; single/multiple OFEs. Expected absence is a
normal create/reuse/no-op or explicit missing-upload validation, never corruption.
Every changed safety/persistence boundary requires direct unmocked valid and hostile
tests. Real generated files and fresh execution are required in addition to state
or successful job status. Working/failed/completed artifacts remain visible.

## Review and checkpoint

Independent security and both read-only contract reviews approved the final
design by2026-09-25 21:58 UTC. All medium/high findings are closed; see
[review dispositions](20260925_contract_reviews.md). No runtime implementation
or conformance claim yet. The ancestor SHA
will be recorded in tracker after commit; final review checks its ancestry.

## Parser discovery evidence

Read-only probes parsed the repository canola management fixture (98.4, one OFE,
two one-year rotations) and synthesized 40 identical OFEs with deduplicated
scenarios. `Management.make_multiple_ofe` incorrectly indexes that rotation, so
use `ManagementMultipleOfeSynth(..., deduplicate_scenarios=True)`. Forest loam.sol
parses/serializes as7778 with ksflag1, which the soil synthesizer caller must pass
explicitly. Strict validation rejects ignored fields, trailing data, nonnumeric
saturation and sand+clay repair. Lowercase staging extensions avoid .SOL dispatch
failure. Forest source pmxnsl.inc declares10 layers; use a conservative10 input
limit and verify selectable binaries in acceptance. Modern2016.3 fixture/runtime
verification is mandatory before claiming that version supported.

## Design review corrections in progress

Both independent reviewers identified the pre-parser multipart resource gap.
The canonical interface now requires streaming envelope, part/header/field limits,
per-file callback limits and partial-spool cleanup, preserving500MiB raster input.
Tests include chunked/false Content-Length and native FormData inactive inputs.
The correctness reviewer identified uniform assignment versus existing class
modification ambiguity. The contract and affected modifier contracts now state
that uniformity is the Build outcome, later deliberate edits remain functional,
and rebuilding mode5 restores uniform source assignments without Disturbed.
Independent post-fix confirmation is pending.

The reviewer also identified that32 is a yearly-scenario limit, not a universal
section limit. Admission now uses plant20 (owned rotation_stack), yearly32 (owned
multi_ofe), surface30, tillage40, grazing20, cuttings25 and crops/year40, with
source/combined selected-binary verification and maxima/maxima+1 fixtures. Forest
source `pmxtls.inc`, `pmxtil.inc`, `pmxgrz.inc`, `pmxcut.inc` corroborate these
event/sequence ceilings; owned plant20 is conservatively below Forest mxcrop40.

## Native-reader safety refinement

Security review traced the default260803 sidecars to Forest commit
`f24c957e3633898e0fd4cbbea5ae08c781f29dba`: mxcrop6, mxtill20, mxgraz10,
mxcut25, mxtlsq30; hillslope mxplan/ntype32. Earlier working-tree Forest-revegetation
limits were not the selected binary provenance and are superseded. The canonical
contract lowers event limits accordingly and restricts initial checked projects
to the current Builder default260803, with both native roles validated. It rejects
unsupported binary/topology before execution; no geometry is silently changed.
This resolves plan Milestone1 supported binary/config combinations; other binaries
remain available to unchecked/legacy projects.

## Final format recommendation

Initial support is management98.4 and soil7778 on260803. Security review of
pinned infile.for543–545 and787 found modern2016.3 rcc/usinrco/usrilco fields
ignored by the native reader, so prior2016.3 recommendation is withdrawn despite
Python support. No parser-success or successful execution claim may substitute
for semantic preservation. Future version expansion is separate certified work.

Final correctness reviewer readback approved the finite260803/98.4/7778 support
and lower native event/OFE bounds. Both independent approvals precede runtime
edits. Checkpoint prepared2026-09-25 21:58 UTC; ancestor commit follows.
