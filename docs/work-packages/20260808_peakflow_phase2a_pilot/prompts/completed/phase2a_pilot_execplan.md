# Execute the Topanga Phase 2A Multi-Hillslope Pilot

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Maintain `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` as work proceeds.

## Purpose / Big Picture

After this work, WEPP stakeholders can determine from generated evidence
whether the accepted observer and replay protocol is safe and complete enough
for the full Topanga candidate census. The pilot exercises a bounded but
hydrologically varied set of hillslopes, traces each mutation from local runoff
through downstream channels to the outlet, and produces an explicit pass/fail
decision for every automatic exit criterion.

## Progress

- [x] (2026-08-08 22:59 UTC) Record Phase 2A authorization and scaffold this
  execution package.
- [x] (2026-08-09 00:32 UTC) Freeze the two scenario manifests and baseline
  inventory after 280 successful full-history observer runs.
- [x] (2026-08-09 00:38 UTC) Select and preregister Hills 106, 84, 8, 35, 31,
  91, 85, and 62 under immutable selection ID `3b5778d7c9171311`.
- [x] (2026-08-09 00:41 UTC) Implement versioned mutation, outer-join,
  routing, hydrograph, replay, storage, and exit-report contracts.
- [x] (2026-08-09 00:43 UTC) Complete all 64 initial full-history mutation
  trials with exact one-file input isolation.
- [x] (2026-08-09 00:44 UTC) Validate a real Hill 31 no-surplus packet and
  observe both APPMTH and HDRIVE selections in the baseline census.
- [x] (2026-08-09 00:45 UTC) Adaptively bracket and frozen-replay the
  undisturbed Hill 106 1986 day-46 known-positive response.
- [x] (2026-08-09 00:49 UTC) Evaluate all ten exit criteria and publish a
  seven-pass, three-fail disposition that withholds the full census.
- [x] (2026-08-09 01:11 UTC) Hash and verify all 139 retained routing and
  hydrograph artifacts (18.23 GB), pass five focused tests, and record the
  container `/tmp` capacity blocker on the repository-wide sweep.

## Surprises & Discoveries

- Observation: the accepted `ea25ad79` observer writes the current `.hbp`
  hillslope-pass contract and deliberately rejects legacy `H*.pass.dat`
  output names. The authoritative scenario decks still name the legacy pass
  files.
  Evidence: the first smoke run stopped in year 1 with the explicit retirement
  message; the Phase 1 accepted fixture changes only the pass-output suffix to
  `.hbp`, and the adapted 45-year Hill 106 smoke run completed successfully in
  3.27 seconds with 6,816 observer records.
- Observation: authoritative burned and undisturbed inputs contain 140
  hillslopes and 61 channel elements; `pw0.str` provides a complete directed
  routing topology ending at element 201.
  Evidence: frozen source-tree inventory under
  `/wc1/runs/ha/hand-to-mouth-drought`.
- Observation: nine hillslopes have baseline `inrcov` or `rilcov` at a boundary
  that cannot support both requested `±0.01` probes without clipping. The
  initial selection included Hill 1 at `1.00`; its plus-cover job stopped
  before model execution.
  Evidence: `artifacts/preflight-aborted-selection.json` and the frozen
  baseline inventory. No aborted-run mutation outcomes were screened.
- Observation: the Hill 106 1986 day-46 peak changes by `84.95×` across a
  final Ksat bracket only `8.54e-5 mm/h` wide. APPMTH remains selected, while
  the surplus assignment changes from `positive_excess` to `storm` and the
  added rate drops from `1.0768e-4` to `9.8973e-7 m/s`.
  Evidence: `artifacts/candidate-adjudication.json` and the two frozen packets.
- Observation: two counterfactual HDRIVE replays routed only `0.531` of the
  input volume. Both were stopped and excluded from candidate statistics.
  Evidence: `artifacts/candidate-adjudication.json`.
- Observation: watershed routing is deterministic for identical input, but
  one-hillslope mutations changed 34,899 numerically distinct records on
  sibling channels outside the declared closure.
  Evidence: the burned baseline repeat is byte-identical, while
  `artifacts/routing-trial-validation.csv` records the off-path differences.
- Observation: 600-second `chan.out` timestamps are compatible and all flows
  are nonnegative, but none of the 20 known-positive channel/lane series
  integrates within `5%` or `0.1 m³` of `chanwb.out`; the largest discrepancy
  is `35.7%`.
  Evidence: `artifacts/hydrograph-validation-summary.json`.
- Observation: the repository-wide pytest sweep cannot complete in the current
  `weppcloud` container because its `/tmp` filesystem has no writable capacity;
  even after redirecting pytest's own temporary directory, a preexisting test
  writes directly to `/tmp/run` and fails with `ENOSPC`.
  Evidence: the focused Phase 2A suite passes five tests, while
  `test_run_ash_batch_multipart_returns_input_message_without_enqueue` stops
  the full sweep before exercising Phase 2A code.

## Decision Log

- Decision: use eight hillslopes and 64 initial mutation runs.
  Rationale: this is small enough to inspect completely while allowing seven
  non-control hillslopes to cover the required strata around Hill 106.
  Date/Author: 2026-08-08 / Codex.
- Decision: select from baseline covariates before mutation results exist.
  Rationale: selection should exercise mechanics without enriching every slot
  for known anomalies.
  Date/Author: 2026-08-08 / Codex.
- Decision: treat burned and undisturbed as separate strata.
  Rationale: the causal comparison is a frozen scenario versus the same
  scenario with one mutation, not burned versus unburned.
  Date/Author: 2026-08-08 / Codex.
- Decision: make Phase 2A data contracts additive and versioned; do not alter
  the Phase 1 `1.0.0` schemas or authoritative `/wc1` run trees. Generated
  Phase 2A records carry explicit lane-presence booleans, immutable input and
  executable hashes, and external-artifact locators. Regression validation
  covers Phase 1 schema validation, exact one-target input diffs, terminal
  ledger completeness, outer-join absence semantics, and propagation to the
  externally generated Parquet/JSON artifacts before compact summaries are
  committed.
  Rationale: this is an additive diagnostic data/schema change. It preserves
  existing consumers, makes absence distinguishable from numerical zero, and
  provides the compatibility and regression plan required before editing.
  Date/Author: 2026-08-09 / Codex.
- Decision: adapt copied execution decks from `H*.pass.dat` to `H*.hbp` in
  content-addressed work directories, while hashing and leaving the scenario
  authorities unchanged.
  Rationale: `.hbp` is the accepted observer contract established by Phase 1;
  the adaptation is execution plumbing, not a scenario parameter mutation.
  Date/Author: 2026-08-09 / Codex.
- Decision: require symmetric, unclipped cover-probe feasibility in both
  scenario strata as a baseline-only selection eligibility rule, and include
  the frozen selection hash in every mutation path.
  Rationale: requested versus realized mutations must agree; retaining the
  stopped preregistration while using a new content-addressed selection avoids
  clipping, overwrite, or outcome-informed replacement.
  Date/Author: 2026-08-09 / Codex.
- Decision: freeze the absolute screening and channel-volume tolerances in
  ADR-0042 before evaluating the mutation outcomes.
  Rationale: near-zero ratios and output-text precision require deterministic,
  outcome-independent floors.
  Date/Author: 2026-08-09 / Codex.
- Decision: retain all-channel daily peak and water-balance output for every
  mutation, plus 600-second interval series for the known-positive closure.
  Rationale: all-channel daily records prove off-path invariance, while the
  bounded interval pair proves timestamp and volume behavior without emitting
  interval data for every pilot lane.
  Date/Author: 2026-08-09 / Codex.
- Decision: withhold the full Topanga census because criteria 5, 6, and 7 fail.
  Rationale: capacity is acceptable, but sibling-channel changes and the
  incompatible interval/daily volume authorities violate automatic routing
  integrity gates.
  Date/Author: 2026-08-09 / Codex.
- Decision: after completing the pilot, cull watershed routing from the local
  census critical path and retire criteria 5–7 as authorization gates for that
  narrower census. Preserve the failed routing evidence and prohibit
  downstream-channel or outlet claims until a separate routing follow-up.
  Rationale: the local prevalence and mechanism questions do not require the
  projected 261.7 GB routing workflow or its unresolved output authorities.
  Date/Author: 2026-08-09 / requesting operator and Codex.

## Outcomes & Retrospective

Complete. The pilot executed 280 baseline observers, 64 full-history mutation
runs, 64 full-watershed mutation routes, two baseline routes, two interval
known-positive routes, a real no-surplus replay, and a 12-iteration adaptive
bracket. Seven of ten automatic criteria pass. Criteria 5–7 fail because
mutations alter sibling off-path channels and the interval discharge series do
not reproduce the daily authoritative outflow volumes. The full census is
therefore withheld. The smallest recovery is to remove the shared/event-global
transmission-loss effect and reconcile `chan.out` with the authoritative
`chanwb.out` volume, then rerun only routing criteria 5–7; immutable hillslope,
event-pair, packet, bracket, and cost evidence remains reusable.
All 139 retained routing and hydrograph artifacts have independently verified
byte counts and SHA-256 hashes. Focused tests and schema validation pass. The
broader repository sweep remains an environment-level validation exception
because the existing test container has no available `/tmp` capacity.

Post-completion amendment: the original seven-pass, three-fail exit report
remains immutable. The study now authorizes a hillslope-only local census and
defers routing consequences to a separate sampled follow-up, as recorded in
`artifacts/study-design-amendment-local-census.md`.

## Context and Orientation

The audit protocol is in
`docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md`.
Gate 2.1 accepted the observer and replay machinery at WEPP-Forest commit
`ea25ad79`. An event packet is an immutable record of one peak-solver call,
including its model state and forcing. A routing closure is the target
hillslope plus every downstream channel ending at the outlet. An outer join
retains an event even when it exists only in the baseline or mutation lane;
this prevents a missing event from being silently treated as zero runoff.

The accepted schemas and tools live under
`docs/work-packages/20260808_peakflow_phase1/artifacts/` and `tools/peakflow_*`.
Large generated tables do not belong in Git. Commit schemas, manifests,
summaries, compact diagnostic fixtures, hashes, and storage locators.

## Plan of Work

First freeze run and build provenance for the burned-base and
undisturbed-Omni scenarios. Execute observational baselines before mutations
and build a hillslope inventory containing soil and surface Ksat, cover,
topographic position, downstream path length, `surdra` frequency, solver
selection counts, and no-surplus event counts. Do not inspect mutation outcomes
during selection because none should exist yet.

Select Hill 106 plus seven hillslopes through a deterministic maximum-coverage
procedure. The resulting manifest must show which required categories each
hillslope covers and why no required category is absent. Freeze the selection,
input hashes, routing topology, and scenario manifests before running probes.

For each selected hillslope and scenario, create four one-hillslope mutations:
first-horizon Ksat at `0.99×` and `1.01×`, and paired `inrcov`/`rilcov` at
`-0.01` and `+0.01`. Record requested and realized values; reject clipping or
rounding that erases a perturbation. Every run uses a complete antecedent
history. Store only the target hillslope, its downstream closure, the outlet,
and checksums for unchanged elements unless a candidate requires full output.

Pair baseline and mutation events with an outer join on scenario, hillslope,
OFE, model day, and solver-call ordinal. Record `event_present` independently
for each lane. Apply candidate rules only after absolute floors prevent ratios
near zero from dominating. Preserve every applicable mechanism flag rather
than forcing an exclusive label.

Validate routing by proving that unmutated hillslopes and off-path channels are
unchanged. For changed records, verify downstream membership, monotonic and
compatible timestamps, nonnegative flow, and event-volume consistency from
local hillslope to outlet. Stop any HDRIVE replay whose routed fraction is
below `0.95` or which reports an array or iteration limit; create a terminal
disposition instead of including it in screening statistics.

Choose at least one Hill 106 known-positive response for adaptive local
bracketing. Replay its immutable event packet with antecedent state fixed, and
separate forcing-construction changes from solver-response changes. Record its
evidence state as screened, reproduced, locally bracketed, mechanism traced,
confirmed implementation defect, or physically unresolved.

Finally measure per-run runtime and retained bytes, project both to the full
Topanga matrix, and render a machine-readable exit report with evidence links
for all ten criteria. Passing every criterion authorizes the full census;
failure withholds execution and identifies the smallest remediation needed.

## Concrete Steps

Work from `/workdir/wepppy`. Before implementation, record `git status`, the
observer and replay hashes, scenario input-tree hashes, and routing topology
hash. Keep authoritative run inputs read-only and execute in temporary or
package-controlled work directories.

Use the canonical validation entry points as implementation develops:

    wctl run-pytest tests/investigations/<phase2a tests>
    .venv/bin/python tools/peakflow_phase1_protocol.py validate \
      docs/work-packages/20260808_peakflow_phase1/artifacts/schemas
    wctl doc-lint --path \
      docs/work-packages/20260808_peakflow_phase2a_pilot

The completed run produced:

    64/64 mutation terminals complete
    64/64 routing terminals complete
    697 screened event rows across 61 trials
    7 pass / 3 fail automatic exit criteria
    full_census_authorized: false

Update this plan and `tracker.md` after each milestone. Do not begin the full
census merely because mutation runs complete; the exit report is the gate.

## Validation and Acceptance

Acceptance requires generated evidence, not only unit tests. The pilot command
must exit nonzero when a mutation lacks a terminal disposition, an outer join
collapses absence into zero, an off-path element changes, a hydrograph violates
time or volume checks, an artifact fails its schema or hash, or an incomplete
HDRIVE replay reaches candidate statistics.

A passing run produces a Phase 2A exit report with ten named criteria, each
marked `pass` and linked to machine-readable evidence. It also reports the
eight selected hillslopes, 64 requested mutation trials, terminal counts,
candidate counts before and after adjudication, observed runtime/storage, and
the projected census cost.

## Idempotence and Recovery

All generated runs must be content-addressed or carry immutable run IDs so a
retry cannot overwrite evidence from a different input tree. Failed and
stopped runs retain their manifests and terminal disposition. A rerun may
reuse an artifact only after its input and executable hashes match exactly.
Never mutate `/wc1` fixture authorities in place.

## Artifacts and Notes

Commit compact manifests, selection tables, schemas, reports, figures, and
content hashes under this package's `artifacts/`. Store partitioned event and
hydrograph datasets externally and record their locator, format, byte size,
hash, producing run, schema version, and retention status.

## Interfaces and Dependencies

Reuse `tools/peakflow_phase1_protocol.py`, `tools/peakflow_phase1_replay.py`,
and `tools/peakflow_gate21_acceptance.py`; extend their typed contracts only
additively. Use Parquet for scalar ledgers and a separately compressed,
interval-oriented format for forcing and hydrograph series. The observational
process must call only the production-selected solver. Counterfactual solver
calls remain isolated in the standalone replay process.

## Revision Note

Initial Phase 2A plan authored 2026-08-08 from the accepted Gate 2.1 review
disposition. Revised 2026-08-09 after complete execution to record frozen
selection eligibility, additive schema compatibility, the known-positive
mechanism, measured cost, routing-integrity failures, and the automatic
withhold disposition.
