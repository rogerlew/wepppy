# Scientific integration contract checkpoint

Status: checkpoint prepared 2026-09-14 UTC; independent final contract reviews
and standalone commit pending. Implementation base: `c81635b43804a11642e6c777ae725aa4a7fa7b78`.

## Authority and classification

The owner accepted the explained common analysis support, then requested this
scaffold, soil-model/SSURGO research and particular care against regressions in
SSURGO/STATSGO soil building. Earlier accepted direction retains SSURGO primary,
original THICK fallback, configured 10 m NED13/2022 for M3, existing UI/RQ and
observable artifacts. Exact soil policies have not been approved by this request.
Subsequent owner direction explicitly rejects strict material rules as non-viable
and authorizes depth-based replacement investigation. The [replacement
assessment](depth_policy_assessment.md) documents NRCS support for H and measured
candidate effects. Acquisition remains unapproved.

This is an intended scientific/runtime behavior change: replace M3's scaffold
failure with actual results; replace M1 all-or-nothing point availability with
common valid support. Historical coefficients, Horn and upstream soil building
remain unchanged. It is not restoration of already-implemented M3 calculations.

## Canonical authorities to synchronize

The owner subsequently answered “proceed” to the explicit replacement-policy
ratification question. ADR-0067 is accepted. Executing the requested plan
includes its standalone checkpoint commit; no source acquisition is inferred.
The canonical [runtime detail contract](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3_runtime.md)
specifies schemas, prepared-source inputs, limits and compatibility. The exact
source-delivery implementation uses prepared local files only. Missing prepared
lineage/THICK remains an acceptance limitation, not permission for acquisition.

Repository-relative authority set: module `specification.md`, detailed
`docs/production_m3.md`, `docs/model_selection.md`, `docs/production_m1.md`,
`docs/m1_predictors.md`, `docs/m3_soil_thickness.md`, `docs/m3_terrain.md`,
`docs/slope_sbs.md`, `docs/dnbr_upload.md`, `docs/rainfall_results.md`,
`docs/staley2017_engine.md`, ADR-0053 and ADR-0066; shared
`docs/schemas/nodb-persistence-concurrency-contract.md`,
`docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`,
`docs/standards/artifact-observability-standard.md`,
`docs/ui-docs/controller-contract.md`,
`docs/ui-docs/contracts/postfire-debris-flow-control-contract.md` and the
feature-registry specification. Detailed module paths are relative to
`wepppy/nodb/mods/postfire_debris_flow/`.

Audit unchanged shared contracts for conformance; amend only affected obligations.
Resolve old independent-support/full-K wording explicitly for new production
results while preserving raw tool and version-1 offline semantics. Update the
README, roadmap and user/operator guidance with final behavior before closure.

## Decision register

| ID | State | Decision / next evidence |
| --- | --- | --- |
| S01 | Accepted | Common M1 support: determined slope/SBS + valid dNBR + valid K; M3: valid SBS + usable thickness. Include valid unburned cells. |
| S02 | Accepted | Full contributing-basin relief/area for M3 T; full project area for applicability warnings. No soil-mask redefinition of geometry. |
| S03 | Accepted | Exact visible mask, spatial coverage/counts, zero-support unavailability, no minimum percentage threshold or uncertainty-interval UI. |
| S04 | Accepted | M3 is a read-only downstream soil consumer; no shared builder validity, donor, clipping, cache or `.sol` changes. |
| S05 | Accepted | Recorded-depth replacement approved by owner; ADR-0067 includes H/Cr, endpoint disagreement warnings and bounded legacy combination pairs. Offline defaults preserved. |
| S06 | Accepted | Positive usable-weight map-unit mean; disclose known/usable/nonsoil/rejected weights; individual invalid weights reject, totals above 100 alone do not. Binary spatial support. |
| S07 | Accepted | Per-cell usable primary then original THICK, nearest-neighbor, finite zero THICK valid and missing values excluded. No component-fraction spatial weighting. |
| S08 | Prepared-only contract | Inventory complete. Optional local soil_sources.json supplies verified primary keys and/or original THICK window. Missing delivery blocks corresponding real acceptance. Acquisition remains unapproved. |
| S09 | Specified, review pending | Canonical production_m3_runtime.md specifies snapshots, schema versions, artifacts, limits, freshness and coverage. Resource and runtime evidence remain implementation gates. |

## Compatibility, risk and regression

Keep selectors, endpoints, immutable model/frequency attempts and single-latest
accepted result layout. Add coverage and source provenance; never relabel or
rewrite old M1 results. Policy identity invalidates predictor reuse. New partial
M1 probabilities are intended; complete-support parity is required. M3 has no
K/dNBR dependency. Exact schema deltas and generated-artifact propagation evidence
must be appended before this checkpoint is accepted.

Security impact high: raw SQLite/file intake, WBT execution, source delivery,
worker/publication paths and user-visible downloads. Preserve authorization,
bounded admission, existing lock order, ownership and artifact observability.
Use the [soil regression plan](soil_regression_plan.md) and the ExecPlan's state
matrix. Explicitly exercise absent, empty, populated, supported legacy and hostile
states. Corrupt source files and normal scientific missing values have distinct
failure contracts; runtime/path failures must not silently become fallback data.

## Checkpoint completion

Execution update, 2026-09-14: [source inventory](source_inventory.md) and
[bounded proposal](source_delivery_proposal.md) now supply actual development
evidence. Strict material policy was rejected; the recorded-depth replacement
is approved in ADR-0067. Collection lineage and an original THICK window are
still missing for live acceptance. S05–S07 are accepted; S08 specifies prepared
local sources only; S09 fixes runtime/schema details. Independent final contract
reviews and their disposition govern the standalone ancestor commit.

After bounded evidence, record exact S05–S09 resolutions and operator approval of
unresolved scientific/acquisition choices. Obtain two independent read-only
contract reviews, disposition findings, amend canonical contracts and the soil
parameterization ADR, and commit a standalone checkpoint ancestor before code.
No reviews or checkpoint commit have occurred during scaffolding. Final QA,
correctness and dedicated security review remain separate execution gates.
