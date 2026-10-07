# Validate the combined release on warming championship


Completed 2026-10-07 22:14 UTC. This plan follows
`docs/prompt_templates/codex_exec_plans.md`. The requested comparison is
complete, with yield preservation supported and routed-flow equivalence not
supported. See `results.md` and `validation-review.md` in this package.

## Purpose and context


Compare daily streamflow from three exact WEPP binary/roughness combinations
on forest. The reference is `wepp_260803` at 10 cm; comparisons are the recut
`wepp_261007` at 10 cm and `wepp_260803` at 17 cm. Random roughness (rrinit)
is an initial management value in metres. Only records originally at 0.10 m
may become 0.17 m. The 0.06 and 0.008 m records are negative controls.
The 864 hillslopes contain 1,904 OFEs (segments along hillslopes). All 8,766
daily values from 1980–2003 must be used, without warm-up exclusion.

The source is `/workdir/warming-rrinit-20261006/snapshot`; it contains native
model inputs retained by the earlier experiment. New output belongs solely
under `/workdir/warming-combined-release-20261007`. The WEPPpy environment is
`/workdir/wepppy/.venv/bin/python` on `forest.tail305ec9.ts.net`. Existing
runner utilities are in the immutable package
`docs/work-packages/20261006_warming_rrinit_legacy/artifacts/run_experiment.py`.
Reuse its manifest, management mutation and execution functions, not its
hard-coded run orchestration. Fresh same-build passes must feed each watershed.

## Progress


- [x] (2026-10-07 20:54 UTC) Verified combined release binary hashes and linkage.
- [x] (2026-10-07 20:54 UTC) Declared design and provisional screen in package.md.
- [x] Implement staging and metric logic; six metric/date tests pass on forest.
- [x] (2026-10-07 22:14 UTC) Complete all cases and observer control: 2,596 successful executions.
- [x] (2026-10-07 22:14 UTC) Convert all records, calculate metrics and produce six figures.
- [x] (2026-10-07 22:14 UTC) Inspect all figures, daily/event departures and outlet diagnostics.
- [x] (2026-10-07 22:14 UTC) Verify hashes and independent metrics, retain evidence and close research scope.

## Surprises and discoveries


The first same-name release lacked the estimator. The user recut it, and
hash checks now match the combined release. Never infer identity from the
release filename. The local checkouts contain prior unrelated changes; use
the clean, current forest checkout for execution without overwriting them.
The first fresh attempt stopped during staging because `p*.man` included
`pw0.man`. It is preserved at the root path with suffix
`-attempt1-staging-failure`; numeric hillslope ID filtering corrects the error.
All 6,056 raw legacy10 outputs reproduce their historical hashes exactly.
Native conversion accepts 7,573,824 PASS and 16,690,464 WAT records per
completed case. The old manifest includes three additional derived parquet
files; raw-binary reproduction excludes those and rebuilds them consistently.

## Decision log


On 7 October 2026, use fresh executions for all three cases, not cached
comparisons. Preserve the previous experiment's frozen inputs and channel
output mode 3 with 600-second sampling. This observer setting changes output
detail, not the physical routing step; retain a same-build mode-1 parity
check for the new release. The provisional aggregate screen is ≤0.1% absolute
yield bias and NSE/KGE/R² ≥0.999. It is not proof of instantaneous hydrograph
equivalence or a universal hydrological acceptance threshold.
Roger explicitly requested both totalwatsed and channel discharge. Report
NSE, KGE and R² for daily outlet means and the equally spaced 600-second
series as well as totalwatsed. Sparse single-record daily-average output is
expanded as a constant only for the labelled 600-second comparison; report
its frequency and do not invent subdaily timing for those days.

## Plan of work


First add `artifacts/run_validation.py`, stage isolated cases, validate rrinit
with the normal management reader and hash the exact consumed inputs. Freeze
binary copies and sidecars in the research root so a later vendoring change
cannot alter the running experiment. Run eight hillslopes concurrently per
case, then the matching watershed. Require 864 hill successes per case and
the watershed success marker; retain stderr and unsuccessful evidence.

Next add `artifacts/assess.py` and tests. Convert all PASS and WAT files using
native wepppyo3; require zero rejected records. Compute totalwatsed with
gwstorage=0, bfcoeff=0.04/day and dscoeff=0, matching the source project.
Streamflow is surface runoff plus lateral flow plus postprocessed baseflow.
Convert mm/day to mean m³/s using area/1000/86400. It is not routed outlet flow.

For baseline x and comparison y, NSE=1−sum((y−x)²)/sum((x−mean(x))²).
KGE2009=1−sqrt((r−1)²+(sd(y)/sd(x)−1)²+(mean(y)/mean(x)−1)²).
R² is squared Pearson r, not NSE. Report r and KGE components, volume bias,
RMSE and maximum daily departures as well. Do not fit or shift either series.
Reject missing/duplicate/nonfinite dates and test identity, scaling, offsets
and undefined constant-series metrics explicitly.

Produce a full-record hydrograph/residual figure, scatter/flow-duration
comparison and event-detail figure. Choose events reproducibly from baseline
peaks, including smaller events and the greatest departures, and retain the
selection. Read all images manually. Separately parse fresh outlet ledger
and 600-second printed discharge, documenting finite printing precision and
remaining conservation limitations rather than treating totalwatsed as an
outlet ledger.

## Concrete steps


Copy this package's scripts to the isolated forest research script directory,
then from `/workdir/wepppy` run:

    .venv/bin/python /workdir/warming-combined-release-scripts-20261007/run_validation.py

Run focused metric tests and the assessment script with the same interpreter.
Record exact commands, execution terminal records, identities and output
manifests. Retrieve compact evidence and figures into this package. Run
`git diff --check` and focused documentation checks before final handoff.

## Validation and acceptance


Completion requires verified fresh outputs, exact input isolation, complete
dates, correct area/units/components, tested metrics, saved data matching
plotted curves and manual visual assessment. A numerical failure of the
negligibility hypothesis is a valid completed research outcome; do not change
thresholds after seeing results. Full application tests are not required for
an offline research-only harness that changes no production code.

## Idempotence and recovery


Staging refuses an existing research root. Never delete or silently reuse
partially completed outputs. Retain failed attempts and choose a clearly
labelled new attempt if a rerun is necessary. No production inputs or defaults
are written. Raw evidence stays on forest; compact derived evidence is retained
locally. Later scientific fixes or deployment need separate authorisation.

## Artefacts and dependencies


Use the existing Python environment, native interchange, NumPy, pandas,
matplotlib and standard library only. Retain source manifests, sidecars,
binary hashes, parsed inventories, run summaries, paired daily parquet,
metrics JSON, figures and a results narrative within the package. Do not
commit multi-gigabyte raw model output. Full raw evidence paths must remain
documented for reproduction.

## Outcomes and retrospective


All execution and artefact checks pass. Totalwatsed agreement is effectively
exact, but daily outlet NSE/KGE/R² are 0.995419/0.970290/0.996189 and sampled
volume bias is −0.598043%. The routed-flow negligibility hypothesis fails the
unchanged provisional screen. Smaller-event peaks can more than double, and
the October 1994 integral/ledger deficit is 18.08%. This establishes
site-specific model agreement and departures, not validation against observed
flow or closure of HV-02/HV-05. Legacy output is not physical ground truth.

Interim result, 2026-10-07: combined-release totalwatsed scores are essentially
one, but routed daily NSE is 0.995419 and KGE 0.970290, with −0.598043%
sampled-volume bias against legacy10. The sampled-integral/ledger discrepancy
is −1.058113%. These contradict the provisional routed-flow negligibility
screen; preserve the result rather than altering the screen. Legacy output
is not physical ground truth, so a difference is not automatically proof of
a scientific regression. Final three-way figures and verification remain open.

Initial plan written 2026-10-07 before fresh model execution. Closed after
18,168 raw-output hash checks, seven-file observer parity, zero rejected native
records, six unit tests, independent daily metric recalculation and manual
review of all six figures. Conversion overlapped only already-completed cases.
The failed staging attempt and all raw model evidence remain on forest.
