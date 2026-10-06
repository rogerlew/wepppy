# Topanga seed recurrence tracker

Status: COMPLETE. Date: 2026-10-06 UTC. Owner: WEPPpy.

- [x] User approved execution of pilot and larger study.
- [x] Archived inputs and baseline/candidate ledgers verified on forest.
- [x] Isolated study workspace and seed list frozen.
- [x] Observer/replay recovery and acceptance fixtures pass.
- [x] Climate regeneration and spatial mapping validated.
- [x] Five-seed pilot and independent seed repeat pass.
- [x] 100 random seeds complete with event-level reconciliation.
- [x] Manual recurrence and mechanism review complete.
- [x] Scientific report authored and final cluster health checks complete.

Resolved constraint: historical observer path contained a later binary; an
isolated pinned-source rebuild passed acceptance. Existing
forest WEPPpy and WEPP-Forest checkouts have unrelated dirty files and will
remain untouched; use isolated export/work directories.

## 2026-10-06 execution evidence and decisions

Observer rebuilt in an isolated forest source export. Historical canonical
hashes, full-precision packets, replay, 1986 fixtures and inactive parameter
control passed. Rebuilt observer SHA-256:
36f3560395676e6a4f96d4eff87e3a860e8c6172efd76fdcb8985d817d8a9047.
Replay SHA-256:
3dcacd6c694ac4e233a18b79ffb0055a7e7a8cf12c94e72ac8dc8106129022b2.

Original-control cluster run and same-host repeat completed all five lanes;
every canonical output and trace was byte-identical between repetitions.
Forest/cluster differences were retained: at most 3.73e-9 m in one Ksat20
observer runoff value, 2.28e-13 m/s in one peak, 1e-5 mm in water output.
All event classifications were identical. HBP compressed files differ and
are retained but not consumed; routing is excluded. Cross-host acceptance
requires exact peak/erosion text output plus observer differences below 1e-8 m
or 1e-12 m/s and water differences below 2e-5 mm. These tolerances were recorded
before any seeded WEPP outputs, following the original-control comparison.

The unseeded raw CLIGEN storm fields, serialized to .1f as the historical writer
did, exactly reproduce all 16,437 archived daily records. Daily P/T spatial
corrections and observed radiation, wind and dew point are retained directly
from the immutable consumed climate. Only duration, tp and ip are varied.

Initial pilot climate attempts were rejected by the general CLIGEN quality
guard and retained under attempts/initial-quality-guard. Their warnings also
occur in the original climate regeneration, and identify Precip. Amt., Temp.
Dew Pt., Wind Vel. and Wind Dir. These generated daily fields are replaced by
independently frozen observations in this experiment. Before rerunning the
pilot, the study-only policy was refined to retain/label these warnings while
requiring exact observed-field parity. Unknown or storm-field warnings, runtime
errors, nonfinite values and date mismatch remain fatal. No production guard
or parameterization changed. Inference is conditional on the legacy generator,
not an endorsement of its meteorological sampling quality.

Cluster evidence root: /wc1/studies/topanga-seed-recurrence-20261006.
Worker: weppcloud-rq-batch-8454859648-48ks9 on worker-dell-01.
Concurrency: four seed tasks, each serially executes five hillslope lanes.
Seed manifest SHA-256:
87e5328d41faf5753d57c1081f2144bbd3dd97f1ae54e5662ace5c7df80ed005.

Pilot accepted: five distinct numerical storm series, fixed observations exact,
seed 0 reproduces the original numerical climate, and seed 12345 repeats all
five lanes byte-for-byte. Inference started only after this report existed.
All 100 random seeds run unchanged; no substitution or optional early stopping.
The trace-signature endpoint and deterministic manual selection were defined
before final inference analysis; these do not establish mechanism prevalence.

Focused script checks passed Wilson boundaries, screening thresholds, climate
dates and outer-join absence behavior. Documentation lint initially panicked
when given a path outside its current root; rerunning from the staged document
root passed without changing source-checkout files.

Inference seeds 53846 and 46045 failed the same study quality-name gate, now
for generated wet-day probability and (53846) maximum temperature. Direct raw
readback for 53846 showed exact dates, precipitation and both temperatures.
Before final analysis, the explicit allowed daily-variable names were completed
with Prob. of Precip, Max. Temp., Min. Temp. and Radiation. All are held fixed
at the model-consumed path; no storm-field warning is allowed. Preserve initial
attempts and rerun identical seeds with the same binary/inputs. Record this
post-start policy refinement, not a warning-free-generator acceptance claim.

## Completion, 2026-10-06

Inference finished at 17:17:35 UTC. All 100 frozen seeds completed; two initial
rejections were retained and rerun unchanged, with identical raw climate hashes.
The cluster completed 540 full-history hillslope runs including controls/pilot.
Independent readback verified 4,000 compressed inference outputs/traces, 100
distinct numerical storm series, exact daily fields and 66,910 event-pair rows.

Primary-date strict recurrence: Ksat 78/100, cover 0/100, dense 0/100.
Any-date recurrence: 100/100, 85/100, 77/100 respectively. Only 12/100 retain
the original Ksat solver/assignment signature. The report publishes pointwise
Wilson intervals and cautions against flood/defect-prevalence interpretation.

Twenty selected lane packets were manually reviewed. Historical replay passed
15; five failed because the storm-only branch replaces remax while the old
tool replays its recorded pre-surplus value. A separate source-checked branch
replay supplements, not overwrites, that evidence: all 20 match production
exactly. Its initial import error is retained in branch-replay.log; corrected
execution is branch-replay-v2.log. No model repair or new bracketing was done.

Final deployment inventory was fully available at desired replica counts;
all 15 RQ workers idle, all four queues zero queued/executing, failed registries
unchanged, public /health returned OK. No deployment, queue or source-run edits.
The scientific report and compact tables/packets live in
docs/investigations/2026-10-06-topanga-cligen-seed-recurrence. Bulk evidence and
all rejected attempts remain at the cluster root, indexed by SHA-256.
