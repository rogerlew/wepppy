# AgFields Routing Scheme Artifact Compatibility Plan

**Status**: Required pre-implementation contract
**Date**: 2026-07-14
**Timezone**: UTC

## Purpose

This plan is the compatibility and regression contract for changing AgFields from
one singular Concept 2 watershed-integration result to three independently
selectable routing schemes. It must be updated before any directory, manifest,
NoDb, API, or state shape below changes.

The change is additive. Baseline WEPP artifacts, independent AgFields artifacts,
and the completed unscoped Concept 2 tree are protected inputs/evidence, not
migration targets.

## Existing Contract

The completed Concept 2 implementation uses:

```text
wepp/ag_fields/watershed/runs/
wepp/ag_fields/watershed/output/
wepp/ag_fields/watershed/manifest/
```

`AgFields` persists a singular `_watershed_integration_*` state, the rq-engine
route accepts an optional `max_workers`, and an empty request runs Concept 2. The
runs page tracks one `agfields_run_watershed` job and one result/clear state.

These legacy artifacts and state are valid historical Concept 2 evidence. This
package does not rename or delete them automatically.

## Target Directory Contract

Every current scheme owns the same relative structure beneath a fixed allowlisted
slug:

```text
wepp/ag_fields/watershed/concept-1/runs/
wepp/ag_fields/watershed/concept-1/output/
wepp/ag_fields/watershed/concept-1/manifest/

wepp/ag_fields/watershed/concept-2/runs/
wepp/ag_fields/watershed/concept-2/output/
wepp/ag_fields/watershed/concept-2/manifest/

wepp/ag_fields/watershed/hybrid/runs/
wepp/ag_fields/watershed/hybrid/output/
wepp/ag_fields/watershed/hybrid/manifest/
```

The mapping is fixed:

| API/NoDb identifier | Filesystem slug | Physical interpretation |
| --- | --- | --- |
| `concept_1` | `concept-1` | Field-aware parent OFEs route fields through downstream OFEs |
| `concept_2` | `concept-2` | Independent sub-field PASS sources are injected at the parent outlet |
| `hybrid` | `hybrid` | Connected sub-fields use outlet injection; all other sub-fields use field-aware OFEs |

`all` is a UI/request convenience only. It expands to the three identifiers in
the table and must be rejected if used as a filesystem slug, manifest scheme, or
NoDb scheme key.

Every path construction and clear operation must begin from the identifier enum,
not from caller-supplied path text. Resolved paths must remain below
`<wd>/wepp/ag_fields/watershed/`, and existing symlink protections must be applied
to the scheme root and its parents.

## Protected Trees

Before generated-output acceptance, capture a deterministic inventory containing
relative path, file size, and SHA-256 for:

- `wepp/runs/` and `wepp/output/`;
- `wepp/ag_fields/runs/` and `wepp/ag_fields/output/`;
- `ag_fields/` inputs and sub-field metadata; and
- the legacy unscoped Concept 2 directories
  `wepp/ag_fields/watershed/{runs,output,manifest}`.

Ignore only documented ephemeral lock/cache files. After one-scheme runs, Run All,
scheme clears, failed/retried jobs, and final comparison generation, the protected
inventory must have no missing, added, or changed files.

## Per-Scheme Required Artifacts

Every successful scheme root must contain:

- `runs/` with a complete, isolated parent/watershed run workspace;
- `output/` with exactly one staged PASS per parent and complete watershed WEPP
  outputs;
- `manifest/integration_summary.json` with schema version, scheme identifier,
  scheme slug, algorithm/native versions, source signature, timestamps, counts,
  limitations, and required-artifact inventory;
- `manifest/pass_sources.parquet` with one row per weighted source;
- `manifest/parent_routing.parquet` with one row per parent and stable status and
  reason codes;
- event/run closure artifacts for any weighted merge;
- the required watershed interchange resources; and
- a scheme-specific README that states the physical interpretation and
  limitations in ordinary language.

Concept 1 and hybrid additionally require
`manifest/ofe_plan.parquet`. Hybrid additionally requires
`manifest/subfield_routing.parquet`. Concept 2 may write
`subfield_routing.parquet` for comparison but every retained sub-field must be
marked as the outlet-injection branch.

`subfield_routing.parquet` must include, at minimum:

- `field_id`, `sub_field_id`, parent `topaz_id`, and parent `wepp_id`;
- `channel_connected` and `direct_channel_outlet_cells` from the canonical Peridot
  classifier;
- `routing_branch` with the closed values `concept_1` or `concept_2`;
- classifier definition/version and channel-detection source; and
- input resource identities or hashes sufficient to reproduce the classification.

`ofe_plan.parquet` must include, at minimum, parent identity, ordered OFE identity,
normalized start/end, source kind/identity, raster and modeled areas, signed area
error, classification agreement, downstream-background length, plan/version, and
eligibility/rejection reason.

All additive Parquet schemas must be versioned and documented in the generated
README. Column removal, renaming, or type narrowing requires explicit operator
approval and a new compatibility plan.

## Hybrid Area and Source Contract

For parent raster area `A_parent`, connected retained sub-field areas `A_c`, and
the Concept 1 residual source area `A_residual`:

```text
A_residual = A_parent - sum(A_c)
A_target = A_residual + sum(A_c) = A_parent
```

The residual Concept 1 source contains non-connected fields and uncovered
background. Connected sub-field cells are excluded from its geometry and source
assignment. Connected independent PASS files are then merged with that residual
source through the accepted ADR-0018 weighted combiner.

Parent cases are explicit:

- No connected sub-fields: the hybrid parent is a pure Concept 1 parent and has no
  injected field sources.
- Connected sub-fields plus residual area: generate a residual-area Concept 1
  source, inject the connected sources, and prove exact source-area closure.
- Connected sub-fields cover the complete parent: use pure Concept 2 composition
  with zero residual source.
- Any overlap, negative residual, missing cell ownership, ineligible residual OFE
  plan, or incomplete source must fail that parent/scheme before replacement.

It is incompatible with this contract to add connected sources to a full-area
Concept 1 parent or to uniformly scale an unchanged whole-parent Concept 1 PASS to
`A_residual`. There is no silent fallback to Concept 2.

## Persisted State Compatibility

Replace the singular logical state with an additive mapping keyed by the three API
identifiers. Each entry independently carries status, phase, stale flag, source
signature, summary, error, root/browse path, limitation, and job id.

Historical NoDb payloads without the mapping must load without mutation failure:

- Singular completed state plus the legacy required artifacts is exposed as
  read-only legacy Concept 2 evidence.
- Singular nonterminal/default fields map to the Concept 2 default only when doing
  so cannot claim nonexistent current artifacts.
- Missing state for Concept 1 or hybrid hydrates as `not_run`.
- A current `concept-2` run is distinguished from the legacy unscoped tree by its
  scheme-specific root and source signature.

Do not delete the legacy `_watershed_integration_*` fields during this package.
They may remain as read compatibility fields until a separately approved migration
proves all supported persisted payloads can be upgraded safely.

Staleness is calculated independently per scheme. A rerun or clear of one scheme
must not make a current sibling scheme appear absent, although any shared upstream
input change may mark all three stale.

## API and RQ Compatibility

The run route accepts an additive `scheme` value:

```text
concept_1 | concept_2 | hybrid | all
```

An omitted or empty value means `concept_2`, preserving the completed endpoint's
behavior. Unknown strings, arrays, path separators, filesystem slugs, and mixed
case are rejected with the canonical 400 error payload; they are not normalized
into valid values.

A one-scheme response retains the canonical `job_id` and may add
`job_ids: {<scheme>: <job_id>}`. An `all` response returns the additive `job_ids`
mapping for all three schemes and may set `job_id` to the first queued job for old
response consumers. The OpenAPI/agent API contract and contract tests must record
the exact response.

Run All enqueues three independent jobs in stable Concept 1, Concept 2, hybrid
order. Dependency edges serialize them and allow a later scheme to run after an
earlier scheme fails. This preserves independent RQ terminal status without
concurrent full-watershed memory peaks. The job dependency catalog and generated
graph must be updated together.

Job keys become scheme-specific while the historical
`agfields_run_watershed` key remains readable as the Concept 2 compatibility key.
An active job in any AgFields stage continues to protect input mutation. Scheme
run/retry/clear rules must be explicit under queued, deferred, started, finished,
failed, canceled, and missing-job states.

The clear route accepts one scheme or explicit `all`. Omission means Concept 2 for
compatibility. It removes only current allowlisted scheme roots/states; the legacy
unscoped tree is preserved unless a future, separately named legacy-clear action
is explicitly approved.

## UI Compatibility

Stage 5 remains in the same page position. Its initial selected value is Concept 2
for both new and historical projects. The visible option text is the exact
description-first contract from `package.md`; a user must not need internal
concept numbers to understand the routing behavior.

The state snapshot exposes all three scheme entries and the relevant job-id map.
The UI renders per-scheme status/results when Run All is selected and retains
independent browse and clear actions. Existing readiness gates remain shared:
current independent AgFields results, observed continuous climate, watershed
abstraction, and prepared parent WEPP inputs.

Frontend tests must assert labels by complete visible text, request payloads,
default hydration, partial Run All results, independent clears, limitations, stale
state, and legacy Concept 2 display.

## Failure, Retry, and Partial Output

Each scheme writes through a run-local temporary/staging root and publishes its
terminal manifest/result atomically. A failed current attempt must not overwrite a
previous completed result without preserving enough attempt provenance to
diagnose/retry it.

Run All may finish with any combination of successful and failed scheme jobs.
Later jobs still run. UI and state must show each terminal result rather than
collapsing the group to one generic failure.

An ineligible parent is a scheme failure unless ADR-0019 later defines and accepts
a complete-result policy for constrained eligibility. Such a policy may not be
introduced as an undocumented fallback during implementation.

## Downstream Compatibility

Standard baseline and Roads output scopes do not consume these scheme trees. If a
scheme becomes selectable in standard reports, add explicit scheme-aware
`ag_fields` scope semantics to `docs/schemas/output-scope-contract.md` and update
all report/query/download consumers and route tests in the same change.

Browse links may expose only the selected fixed scheme root. Generated evaluation
comparisons must refer to scheme roots explicitly and must not write derived data
into protected baseline or independent output directories.

## Regression Matrix

The implementation must cover at least:

| Case | Expected result |
| --- | --- |
| Old run request without `scheme` | One Concept 2 job and `concept-2` current output |
| Explicit one-scheme request | Only that scheme root/state/job changes |
| `all` request | Three serialized independent jobs and three scheme roots when successful |
| Invalid scheme or slug/path input | Canonical 400; no job or filesystem change |
| Clear one scheme | Only that current scheme root/state is removed |
| Clear all | All three current roots removed; legacy and protected trees unchanged |
| Historical singular NoDb plus legacy tree | Loads as legacy Concept 2 evidence without rewrite |
| Upstream Stage 4/input change | All completed current scheme states become stale |
| First Run All job fails | Later scheme jobs still execute; states remain independent |
| Mixed hybrid parent | Residual plus connected areas close exactly; no source overlap |
| Full connected coverage | Pure Concept 2 parent with zero residual source |
| No connected sub-fields | Pure Concept 1 parent with no injected sources |
| Ineligible Concept 1/residual plan | Explicit stable failure; no fallback result |

## Generated-Output Acceptance

On `/wc1/runs/sa/sacral-self-discipline`:

1. Capture protected-tree inventory before execution.
2. Run Concept 1 alone, inspect its scheme state and required artifacts, then
   clear/retry it and prove sibling/legacy trees are unchanged.
3. Run Concept 2 alone and compare its source/closure accounting with the completed
   legacy result within the existing serialization-derived budgets.
4. Run hybrid alone and audit every sub-field branch against the Peridot details,
   every mixed-parent area identity, and all weighted water/sediment closures.
5. Run all through the authenticated UI/API/RQ path and record job ordering,
   terminal states, elapsed time, peak memory, disk usage, and required artifacts.
6. Recompute protected-tree inventory and require byte identity.
7. Publish a comparison bundle with identical calendars and clearly separated
   engineering closure from Mariana's later scientific disposition.

The package cannot close on fixtures alone or on planner output without a current
generated watershed result for all three schemes.
