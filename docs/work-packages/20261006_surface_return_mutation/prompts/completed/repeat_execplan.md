# Repeat the Topanga mutation plots with corrected surface-return peaks

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

Completed 2026-10-06: all 1,368 model runs reconcile and Figures 1–3 are delivered.

## Purpose / Big Picture

Roger requested Figures 1 (runoff), 2 (sediment), and 3 (peak) for the corrected
WEPP build on hand-to-mouth-drought. Small mutations test sensitivity around
each scenario baseline; they are not burn-versus-unburned causal comparisons.

## Progress

- [x] 2026-10-06 UTC: found original report, scripts and census adapters.
- [x] 2026-10-06 UTC: verified burned and undisturbed source directories.
- [x] 2026-10-06 UTC: freeze snapshot and validate observation/execution pilot.
- [x] 2026-10-06 20:11 UTC: all eligible mutations and baselines reconcile, no model failures.
- [x] 2026-10-06 UTC: generate and visually inspect three figures and numerical summaries.

## Context and Orientation

Local repository is /Users/roger/src/wepppy. Existing mutation adapters are
wepppy/wepp/peakflow_census/mutations.py. Original plotting scripts are under
docs/work-packages/20260809_peakflow_topanga_census_execution/artifacts/.
On forest.tail305ec9.ts.net, inputs are /wc1/runs/ha/hand-to-mouth-drought/wepp/runs
and /wc1/runs/ha/hand-to-mouth-drought/_pups/omni/scenarios/undisturbed/wepp/runs.
Corrected source/build is /workdir/wepp-forest-holdouts/20261006-surface-return.6SeF9A/candidate/src;
wepp_hill SHA256 is 440fcebbeb2c51c2da46e258a53dce7ad609b783551ee2f5a6b1e18b368b2307.
Python is /workdir/wepppy/.venv/bin/python. Preserve these sources read-only.

## Plan of Work and Milestones

First create a new forest holdout with copied input snapshots and exact hashes.
Reuse the existing soil/cover parsing, mutation and readback functions. Determine
eligibility before observing results. Validate matching hillslope populations,
shared climate and terrain, existing hourly mode, and 45-year decks.

Second obtain full-precision post-correction runoff/peak/surface-return values.
If needed, build an observational companion in a new source copy. It must only
write local diagnostics, never call extra solvers or mutate model variables.
Require byte-identical canonical outputs against the pinned corrected binary
with tracing active on burned and undisturbed H106 complete histories.

Third run all baseline histories and eligible mutations with bounded workers,
300-second per-process timeout, fresh isolated runs/output directories, and
explicit terminal records. Mutations may change exactly one input file and only
the intended parameter tokens. Preserve failed attempts; never reuse a partial
run as complete. Reconcile expected/completed/failed before analysis.

Finally outer-pair events by scenario, hillslope, OFE and calendar date. Preserve
presence fields; do not silently fill absent events. Figure 1 baseline runoff
floor is 0.01 mm; Figure 3 baseline peak floor is 0.36 mm/h, both require positive
mutant values. Figure 2 requires positive EBE sediment on both sides. Use original
log axes, 1:1, twofold/fivefold guides, markers and response-opacity conventions;
label figures as corrected-build, full-history, burned/undisturbed strata.
Record ties as incongruent for original-figure compatibility but enumerate ties
separately. Report plot clipping and one-sided events. Save PNG and statistics.

## Validation and Acceptance

Acceptance requires every eligible trial terminal to reconcile, real output
readback and unique finite paired records, semantic mutation readback, observer
parity, original plotting thresholds, and visual inspection of all three PNGs.
No watershed, release or observed-peak accuracy claim is authorized. Compare
August rates only with explicit input/build/grain limitations.

## Idempotence and Recovery

Use newly created holdout roots; refuse to overwrite artifacts. Preserve failures
and retry in separate attempts. No live project writes, deletion or deployment.
Artifacts and reproduction commands are retained in this package; large model
outputs remain external. A successor can resume from terminal manifests.

## Surprises & Discoveries

The named project is the original Topanga census source. The corrected binary
does not include the old peak_diag.csv observer, so it cannot be fed blindly
into the original observer parser.

All shared August input files are still byte-identical. Three extra shared
context files are included in the new snapshot. An initial diagnostic bug passed
the zero-based runoff/peak array from its index zero; report readback caught it.
V2 explicitly passes index one and adds preflight semantic report comparison.
Invalid initial outputs are retained but excluded. The old census test suite
has 17 passing tests and one stale executable-hash integration failure.

## Decision Log

2026-10-06: preserve original mutation design and visual thresholds, using a
freshly verified observation source for the fixed-build published peak. Do not
modify rrinit or fix rill width: full-history feedback belongs in this experiment.

## Outcomes & Retrospective

Completed 1,088 eligible mutations plus 280 baselines through 1980–2024.
There are 225,042 paired events and 617 one-sided rows. Figure 3 has 218
fivefold departures, versus 604 in the historical census, but 1,021 twofold
departures remain. Of the fivefold residuals, 184 lack surface return. The
results support a narrower severe tail, not elimination of all sensitivities.
Historical source/observer differences prevent a patch-only causal attribution.

All 1,368 diagnostics pass report readback; active observer parity passes seven
canonical files in both H106 strata. Eight new harness tests pass. Sixteen
nonintegration mutation tests pass; the historical executable-hash failure is
retained. Initial failed observer attempts remain separate, not removed.

The model worker pool finished before its per-future fsync progress callbacks
drained. After independent aggregation and verification that no child model
process remained, the coordinator was interrupted. finalize_evidence.py verifies
all expected terminal identities and hashes independently; execution-summary.json
is authoritative, not the preserved incomplete progress acknowledgment count.
This experience demonstrates why generated outputs and terminal evidence, not
coordinator progress alone, determine scientific completion.

## Concrete Steps / Current Evidence

Authoritative root on forest is /workdir/hand-to-mouth-fixed-census-20261006-v2.
Commands from /workdir/wepppy use .venv/bin/python and the campaign's
repeat_census.py: freeze --original-plan
docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json,
then build, parity, execute --workers 8, aggregate (each with --root followed by
the authoritative root). plot_figures.py --root ROOT --output ROOT/figures
produces three PNGs and figure-statistics.json. Inputs, builds, parity and
input-comparison JSON manifests are retained at ROOT. The execution stage is
complete. Original failed campaign remains separate, without deletion.
The final aggregator was retained as repeat_census_analysis.py on forest; it
matches the repository's repeat_census.py and adds all-terminal identity checks
and baseline report readback to the execution-time script. finalize_evidence.py
records terminal-inventory.csv, execution-summary.json, tail-context.json and
artifact-manifest.json. See artifacts/results.md for user-facing findings.

## Interfaces and Dependencies

Reuse Python standard library, existing pandas/numpy/matplotlib/pyarrow on forest,
the existing mutation adapter, SSH/SCP and gfortran. No new dependency required.
