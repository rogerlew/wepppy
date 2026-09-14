# Scientific integration contract checkpoint

Status: draft 2026-09-14 UTC; no implementation authorization/checkpoint commit
claimed. Starting implementation revision: `97800607c30c0979d422f99b1e2c65f1b8a89ab5`.

## Authority and classification

The owner accepted the explained common analysis support, then requested this
scaffold, soil-model/SSURGO research and particular care against regressions in
SSURGO/STATSGO soil building. Earlier accepted direction retains SSURGO primary,
original THICK fallback, configured 10 m NED13/2022 for M3, existing UI/RQ and
observable artifacts. Exact soil policies have not been approved by this request.

This is an intended scientific/runtime behavior change: replace M3's scaffold
failure with actual results; replace M1 all-or-nothing point availability with
common valid support. Historical coefficients, Horn and upstream soil building
remain unchanged. It is not restoration of already-implemented M3 calculations.

## Canonical authorities to synchronize

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
| S05 | Open | Material and interval policy. Evaluate O/ordinary soil, R/Cr/ambiguous layers, legitimate paired horizons versus conflicts/gaps. Preserve offline defaults. |
| S06 | Open | Component weighting and incomplete/above-100 totals. Proposed usable-weight mean with explicit component completeness, independent of binary spatial coverage. Quantify and ratify. |
| S07 | Open | Proposed cellwise selection of usable SSURGO estimate then original THICK; ratify fallback trigger, residual missing data and resampling. No arbitrary complete-only rule. |
| S08 | Open | Audit source availability and original spatial keys in actual projects; define bounded THICK delivery. No implicit soil rebuild/acquisition. |
| S09 | Open | Final additive artifact/schema versions, source fingerprints/WAL snapshot semantics, numerical reuse invalidation, coverage display precision and resource evidence. |

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

After bounded evidence, record exact S05–S09 resolutions and operator approval of
unresolved scientific/acquisition choices. Obtain two independent read-only
contract reviews, disposition findings, amend canonical contracts and the soil
parameterization ADR, and commit a standalone checkpoint ancestor before code.
No reviews or checkpoint commit have occurred during scaffolding. Final QA,
correctness and dedicated security review remain separate execution gates.
