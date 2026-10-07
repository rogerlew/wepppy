# Compare original and corrected WEPP roughness sensitivity

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

Completed research 2026-10-07 00:37 UTC: all requested original runs, comparisons, figures and artifact checks complete. The candidate's hydrograph-volume consistency remains unresolved; this is not a release-approval record.

## Purpose and context

Roger requests original `wepp_260803` runs at 10/17/60 cm and a comparison of the original and corrected 10 cm runs. Roughness can change rainfall excess and the legacy duration used to assign surface-return peaks. The corrected estimator separates those peaks without intentionally changing water accounting. A matched experiment must test that expectation rather than assume it.

Forest is reachable by `ssh -o BatchMode=yes forest.tail305ec9.ts.net`; Python is `/workdir/wepppy/.venv/bin/python`. The immutable reference root is `/workdir/warming-rrinit-20261006`; its snapshot contains executable inputs for 864 hillslopes, 1,904 overland-flow elements (OFE means one hillslope segment), and a 371-channel watershed for 1980–2003. The outlet element is 1235. Only 1,885 initial roughness records at 0.1 m change, to 0.17 or 0.6 m. Fourteen hillslopes are unchanged controls. All lanes retain full hydrograph output at 600-second intervals and the same hourly water balance.

## Progress

- [x] (2026-10-06 23:45 UTC) Locate and hash original release binaries; read existing runner and validation.
- [x] (2026-10-06 23:52 UTC) Verify all matched inputs; complete 864 original 10 cm hillslopes and source audit.
- [x] (2026-10-07 00:11 UTC) Complete original 10/17 cm lanes and their native flow summaries.
- [x] (2026-10-07 00:37 UTC) Stage, execute and validate original lanes.
- [x] (2026-10-07 00:37 UTC) Generate fresh totalwatsed and within-build analyses.
- [x] (2026-10-07 00:37 UTC) Compare matched inputs, water outputs and peaks across builds.
- [x] (2026-10-07 00:37 UTC) Review four figures and publish bounded conclusions.

## Surprises and discoveries

The existing reference has a printed hydrograph integral below its outlet volume ledger; preserve both measures separately. The build system swaps four root sizing includes when compiling hillslopes. Comparing the saved `includes_watershed` versions resolves apparent release-source differences: all 485 source/include/build files match. Only `irs.for`, `surpeak.for` and `makefile` differ from retained baseline to corrected candidate.

## Decision log

Use the original release binary pair with verified hashes, not a newly compiled surrogate. Reuse frozen inputs and require complete input hash equality across builds. Run at most eight hillslopes concurrently on the lightly loaded 48-logical-CPU host; watershed lanes remain sequential. Keep all outputs isolated and retain failure evidence.

## Milestones and concrete steps

First stage the new package runner at `/workdir/warming-rrinit-legacy-run-20261006.py`. From the local repository copy `artifacts/run_experiment.py` by scp, run it with `--test`, then execute using forest Python. It creates `/workdir/warming-rrinit-legacy-20261006` with fail-if-present semantics. Its management parser and hashes must prove each lane matches the corrected experiment before any model executes. Progress is recorded every twenty hillslopes; final authority is `execution-summary.json`, not the last progress checkpoint.

Second run the package `validate.py` and `analyze.py`, each with the remote experiment root as its argument. Require all successful terminal records, unchanged input hashes, exact roughness mutations, unchanged negative-control outputs across roughness, and canonical output parity between channel output modes 1 and 3. Read channel and event outputs for all 8,766 days. Preserve printed timing ambiguity and water-balance residuals.

Third use the existing native hillslope PASS and WAT converters and `run_totalwatsed3` to build fresh daily water yield (runoff plus bottom-OFE lateral flow plus calculated baseflow). Use initial groundwater storage zero, baseflow coefficient 0.04/day and seepage coefficient zero, matching the run. Compare all three original lanes with one another and all matched lanes with the corrected outputs at `/workdir/warming-rrinit-totalwatsed-20261006`. Check daily and total water accounting separately from peak rates. Inspect original release commit `f24c957e3633898e0fd4cbbea5ae08c781f29dba` against corrected source provenance before attributing every difference to the patch.

Finally generate within-build roughness plots and paired 10 cm peak/hydrograph plots, including smaller events and the largest build departures. Record selection rules before interpretation. Retain summaries, hashes, raw paths and executable analysis. Review images visually, compare semantic outputs and write concise results. Update package, tracker and root PROJECT_TRACKER; move this plan to completed only after the requested comparison is delivered.

## Validation and acceptance

Expect 2,596 successful model executions, exact matched input hashes, and no unresolved missing output. Water outputs are expected to agree closely across builds, but differences must be measured, not erased or forced. If differences appear, localize hillslope versus channel effects and qualify conclusions. This experiment supports site-specific validation, not a claim of full physical correctness or authorization to deploy. The original source run and closed reference package must remain unchanged.

## Idempotence and recovery

The runner refuses an existing output root. Do not rerun into partial results or overwrite them. Inspect terminal records on failure, retain the attempt, and use a new explicitly named root for any required retry. Existing binaries and inputs are read-only. No branch changes, commits, deployment or production repairs are required.

## Artifacts and dependencies

Use only the existing Python environment, WEPP release binary pair, native interchange tools, pandas, NumPy and matplotlib. Local records belong in `docs/work-packages/20261006_warming_rrinit_legacy`; raw output remains in the named forest directory. Reuse prior scripts by copying, never editing the closed package.

## Outcomes and retrospective

Execution and comparison completed. Initial plan created 2026-10-06 23:45 UTC to preserve scope, evidence requirements and recovery instructions.

The completed 10 cm comparison preserves total outlet volume to 4.25 m³ over 1.272 billion m³, while 2,356 daily peaks differ by more than 1%. The printed hydrograph integral/ledger deficit grows from 0.4628% to 1.3212%, beyond printing-rounding bounds in both builds. In the October 25–29, 1994 window it grows from 0.83% to 18.30%. Preserve this as an unresolved validation concern; do not claim unqualified fix validation or silently normalize the hydrographs. All three main lanes and the output-mode control completed. All input, negative-control, terminal and 18,177 output-hash checks passed. Four figures and machine-readable comparisons are retained under artifacts. No production changes were made.

Updated 2026-10-06 23:52 UTC with matched-input, first hillslope lane and normalized source audit evidence. Native postprocessing is overlapped with watershed computation without changing model execution.

Updated 2026-10-07 00:11 UTC with completed 10/17 cm runs and emerging peak/volume evidence. Added explicit hydrograph-integral rounding checks to avoid attributing the discrepancy to output precision without testing it.

Closed 2026-10-07 00:37 UTC after the final output hash audit. Added smaller-event comparisons and event-window volume checks to expose effects hidden by whole-record totals. The latter reveals an unresolved candidate validation concern; further diagnosis is a separate scope, not a reason to suppress the experimental result.
