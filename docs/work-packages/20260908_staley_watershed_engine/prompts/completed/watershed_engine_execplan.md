# Implement the single-watershed Staley numerical foundation


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective at every handoff. Completed 2026-09-09 UTC: watershed artifact contract and scalar engine
validated; N01–N04 are owner-approved. Production integration remains outside
this completed scope.

## Purpose / Big Picture


A developer will be able to supply prepared terrain, burn, and soil predictors
for the existing WEPPcloud project watershed and evaluate M1 or M3 probabilities
and rainfall thresholds through a tested local Python interface. A reproducible
example will show results for 15-, 30-, and 60-minute rainfall scenarios. The
package also establishes which existing WBT artifacts identify the project
assessment area and outlet, avoiding redundant delineation work.

This delivers an offline scientific engine. Browser controls, real-project
predictor production, climate ingestion, saved run state and RQ execution are
successor work. Do not describe engine completion as a functioning WEPPcloud
assessment or deployment.

## Progress


- [x] (2026-09-09 04:18 UTC) Scaffold package and record owner-selected scope.
- [x] (2026-09-09 UTC) Owner approved N01–N04; accepted detailed contract and ADR-0056 before code.
- [x] (2026-09-09 04:33 UTC) Verify coefficient table and watershed artifact mapping; reproduce audit in container.
- [x] (2026-09-09 04:33 UTC) Draft proposed detailed numerical contract and request N01–N04 owner resolution.
- [x] (2026-09-09 UTC) Implement scalar engine and focused tests; independent review identified adjacent-target and underflow fixes, now covered.
- [x] (2026-09-09 UTC) Generate examples; independent review passes after two numerical fixes.
- [x] (2026-09-09 UTC) Full suite: 7,959 passed, 72 skipped; final focused suite: 145 passed; API/stub/docs checks pass.
- [x] (2026-09-09 UTC) Update roadmap/specification, record outcomes, archive plan and move board entry to Done.

## Surprises & Discoveries


The earlier roadmap treated per-channel nested assessments as a foundation.
The owner clarified that the existing project watershed/outlet is sufficient
and selected it as the sole initial assessment scope. Multiple-mask offline
soil/dNBR helpers and nested terrain study fixtures do not impose a UI need.
The Topanga routed mask includes the outlet despite selection metadata
reporting `outlet_in_mask=false`; that field describes the optional selection
mask. The 49,917-cell mask matches the polygon and subcatchment support.
PDF text extraction omits equations; rendered pages were checked. The manuscript
area range differs from current guidance, as noted in the coefficient audit.

## Decision Log


2026-09-09 UTC, owner: explicitly approved N01–N04 in the drafted detailed
contract. ADR-0056 records accepted scalar/equality policies and provenance.
Independent review found cancellation near the intercept and inverse underflow;
exact reachability and stable centered log-odds preserve those policies, with
explicit underflow unavailability rather than a false zero result.

2026-09-09 04:18 UTC, owner decision: reuse the project watershed and existing
outlet; users should manually isolate burned basins they suspect may be at risk.
Rationale: WEPPcloud already provides the needed assessment domain. ADR-0055
records this choice; nested assessments require separate future approval.

2026-09-09 04:18 UTC, Codex scaffolding scope: deliver the watershed artifact
contract and pure numerical engine together, without raster aggregation or
production wiring. This lets M1 proceed without waiting for M3 soil policy.
Numerical recommendations in the package decision register are not accepted
parameterization and must be resolved before executable implementation.

## Outcomes & Retrospective


All four milestones are complete within the offline scope. The accepted
contract and ADR-0056 precede the pure scalar engine; final focused tests pass
145 cases. Generated examples cover both models/all durations, independent
Decimal arithmetic, and explicit inverse availability. Independent correctness
review resolved adjacent-baseline cancellation and nonzero inverse underflow;
no findings remain. Full repository suite passed 7,959 tests with 72 skips in
791.10 seconds. Container fixture audit preserves hashes and verifies 49,917
watershed cells, matching grid/support and the existing resolved outlet.

No real-project predictor aggregation, climate adapter, saved results,
UI/NoDb/RQ wiring or deployed assessment is delivered. Stages 3–7 remain
successor work. Numerical tests establish arithmetic, not model calibration.
The source-version area-range discrepancy is retained in current scientific
guidance for later reconciliation without introducing an area gate.

## Context and Orientation


Work from repository root `/workdir/wepppy` (also `/home/workdir/wepppy`). Read
root AGENTS, `wepppy/nodb/AGENTS.md`, module AGENTS and `tests/AGENTS.md` before
editing their respective files. Current scientific authority is
`wepppy/nodb/mods/postfire_debris_flow/specification.md` and its linked contracts.
Delivery tracking is `implementation_roadmap.md` in that directory.

`dnbr.py` already normalizes explicitly encoded rasters and reports observed
means. Its normalized mean is M1 F directly; never divide it by 1000 again.
`soil_thickness.py` is an offline SSURGO derivation helper; production fallback
is not implemented. The owned WBT tool computes M3 H as maximum upstream raw
elevation minus raw elevation at the outlet, including the outlet; A is full
upstream area in square meters. M3 T is H/sqrt(A), dimensionless. This package
accepts T as supplied input and does not invoke the tool.

M1 T is the fraction of the full watershed both moderately/highly burned and
at least 23 degrees in slope; it is not the product of two separate fractions.
M1 S is mean K in the calibrated convention, whose RUSLE mapping is successor
work. M3 F is moderately/highly burned fraction; M3 S is mean thickness in cm
divided by 254. The pure engine accepts already prepared T, F and S; no display
unit conversion or raster normalization belongs inside that evaluator.

`wepppy/nodb/core/watershed.py` owns project watershed/outlet behavior. Trace
its WBT integration and existing committed terrain-study fixtures to identify
authoritative masks, grid and resolved outlet cell. Study evidence is under
`docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/`; inspect its
inventory/harness to locate frozen sources rather than assuming their paths.
Closed packages are immutable history. Do not modify their files.

## Plan of Work


Milestone 1 establishes the contract. Read the package decision register and
settle N01–N04 with the owner before coding dependent behavior. Perform the
coefficient check and trusted read-only watershed artifact inventory while
those decisions are pending. Amend the module specification and create
`wepppy/nodb/mods/postfire_debris_flow/docs/staley2017_engine.md` for accepted
signatures, ranges, outputs, units, reason codes and numerical policies. Write
a numerical parameterization ADR using the next available number; do not
repurpose ADR-0055, which governs assessment scope only. Record provenance and
explicitly separate caller errors from unavailable scientific results.

Verify equations 4–6 and Table 4 from the local Staley 2017 paper, expected at
`wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf`. It is ignored
for redistribution reasons. If absent, follow `docs/pdfs/README.md` in that
module to obtain a lawful reading copy; do not commit it without established
rights. Do not inspect, copy, or translate GPL pfdf source or tests to implement
this engine. Record an independent coefficient check in package artifacts.

The current specification transcribes rows (B, Ct, Cf, Cs) as M1/15:
(-3.63, .41, .67, .70); M1/30: (-3.61, .26, .39, .50); M1/60:
(-3.21, .17, .20, .220); M3/15: (-3.71, .32, .33, .47); M3/30:
(-3.79, .21, .19, .36); M3/60: (-3.46, .14, .10, .18). These are check targets,
not permission to omit the publication verification.

Document full-watershed mask semantics, existing outlet identity and square-
meter area in the canonical assessment section. Verify at least one existing
fixture's mask cell count, boundary/grid relationship and outlet inclusion.
Distinguish a drawn boundary polygon from the raster cells actually routed to
the resolved outlet. If artifacts disagree, document the mismatch and reuse
canonical authority; do not silently re-snap or re-delineate. Identify slope,
SBS and missing-data decisions as stage 3 prerequisites without resolving them
through an incidental test implementation.

Milestone 2 implements the numerical library in
`wepppy/nodb/mods/postfire_debris_flow/staley2017.py` with explicit `__all__`.
Use existing numerical dependencies (NumPy where array behavior is justified)
and no new external packages. Define q = Ct*T + Cf*F + Cs*S; x = B + R*q;
p = sigmoid(x); R is accumulation in mm for the selected duration. For an
inverse equality solution use R = (logit(target)-B)/q when defined. Intensity
is R divided by duration in hours. Evaluate sigmoid/logit stably and follow
the accepted policies for finite inputs, response sign and arithmetic overflow.
Never confuse rainfall R with RUSLE annual erosivity R.

Milestone 3 demonstrates behavior. Add independently authored tests in
`tests/nodb/mods/test_postfire_debris_flow_staley2017.py`. Generate a small
reviewable CSV or JSON example under this package's artifacts for both models
and all durations using explicitly synthetic supplied predictors and rainfall.
Include an independent hand calculation, intermediate q/x, probability, and
inverse reconstruction, plus unavailable/nonunique examples under accepted
policy. Label synthetic inputs and canonical units. Do not call these outputs
a real-project scientific validation. Separately preserve the read-only
watershed artifact audit and its hashes/counts.

Milestone 4 closes the bounded package. Obtain an independent read-only
correctness review using the repository template and resolve findings. Run
focused and full tests; update user/developer notes and canonical contracts.
Update roadmap stages 1–2 only to the extent actually satisfied; production
aggregation and all UI/RQ work remain pending. Archive this plan with outcomes
and move the package board entry to Done only after exit evidence exists.

## Concrete Steps


At repository root start with `git status --short` and `git rev-parse HEAD`.
Record the current revision in the tracker; do not change branches or overwrite
unrelated changes. Inspect the canonical contracts and accepted numerical ADR
before editing executable files. During iteration run:

    wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_staley2017.py --maxfail=1

Before handoff run:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow
    wctl doc-lint --path docs/work-packages/20260908_staley_watershed_engine
    git diff --check

Use the applicable stub checks if package exports/stubs change. Record exact
commands, counts and generated artifact locations in `artifacts/validation.md`.
Run Python checks in the container via `wctl run-python` and numerical tests
via `wctl run-pytest`; WBT is `/workdir/weppcloud-wbt`. Until N01–N04 are resolved,
validate the audit and docs only; after implementation run the full gates above.

## Validation and Acceptance


A developer can call the documented pure API with explicit model, duration,
prepared predictors and rainfall and reproduce a hand-checked probability.
Inverse results reconstruct the target through the forward function when a
unique nonnegative finite solution exists. Tests cover both models/all six
coefficient rows, zero rainfall, extreme logits, negative finite dNBR, q of
both signs and zero, invalid duration/model, nonfinite inputs, target endpoints,
negative inverse solutions, and overflow. Accepted input-shape semantics must
be tested; do not invent broad broadcasting behavior solely for hypothetical use.

No invalid result becomes numeric zero or an unlabeled infinity/NaN. The
canonical contract governs whether a case raises or returns an unavailable
reason. Production integration will later preserve valid events when one input
is unavailable. The artifact audit must demonstrate reuse of one existing
project outlet/domain with no nested enumeration or live mutation. Test
coverage does not establish model calibration or deployed readiness.

## Idempotence and Recovery


Changes are additive: new pure helper, tests, current docs and package evidence.
No run-scoped NoDb, parquet or CSV schema is mutated. Generated demonstration
files are package-local and reproducible from documented commands; use fresh
scratch directories for any raster audit products and preserve source fixtures.
If runtime scope expands to file handling, UI, NoDb or RQ, reassess security and
obtain the applicable contract-first checkpoint before implementation. No live
Soils rebuild, deployment, implicit external download or push is authorized by
this package. Do not introduce fallback dependencies to hide missing tools.

## Artifacts and Notes


Delivered evidence: `artifacts/coefficient_check.md`,
`artifacts/watershed_artifact_audit.md`, reproducible example output and its
invocation, `artifacts/validation.md`, and a dated independent correctness
review. See `artifacts/synthetic_examples.json` and `generate_examples.py` for
reproducible six-row arithmetic evidence; `20260909_correctness_review.md`
records independent review and both resolved findings. The decision register
records explicit owner acceptance; the engine contract and ADR-0056 carry
durable numerical authority.

## Interfaces and Dependencies


Implemented Python interface names are `probability(model, duration_minutes, *,
T, F, S, rainfall_mm)` and `rainfall_threshold(model, duration_minutes, *, T, F,
S, target_probability)`. The accepted detailed contract fixes scalar-only
inputs, return types, reasons and units. The probability
interface returns a 0–1 value; inverse results must distinguish a unique finite
solution from unavailable or nonunique cases. These are local library names,
not HTTP payloads or persisted schemas. Production defaults remain external.

Use the owned WBT/project delineation as artifact authority and existing
compiled geospatial tools for any read-only audit; no Python raster traversal
replacement or new dependency is justified by this package. This engine adds
no filesystem or network interface. A separate source inventory is evidence,
not an unreviewed production loader.

Revision note: initial scaffold records the owner's single-watershed decision
and limits delivery to the assessment contract and numerical foundation.


Revision note (2026-09-09 04:33 UTC): execution requested; source/fixture checks
completed and draft numerical contract prepared. Owner directed container use
with WBT at `/workdir/weppcloud-wbt`; audit rerun reproduced all measurements
and hashes. This direction does not resolve N01–N04. Implementation remains
pending their explicit owner resolution as required by milestone 1.


Completion revision (2026-09-09 UTC): owner approved N01–N04 after the initial
pause. Implemented and reviewed the accepted API; recorded both numerical
review refinements in the contract/ADR. All focused/full and documentation
checks passed. Archived this plan with stage 1–2 outcomes; stages 3–7 remain
unimplemented. Evidence is in `artifacts/validation.md` and the dated review.
