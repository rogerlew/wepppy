# Verify the saved Thomas Fire assessment


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Determine whether the owner's saved Thomas Fire assessment is numerically and
scientifically defensible, and name the smallest actionable improvements. A
successful audit produces reproducible evidence and bounded findings rather
than silently changing the run to obtain agreement with a reference.

## Progress


- [x] (2026-09-16 UTC) Located run on forest and established read-only scope.
- [x] (2026-09-16 UTC) Inventory and independently verify saved inputs and outputs.
- [x] (2026-09-16 UTC) Research and compare USGS basin/rainfall/predictor evidence.
- [x] (2026-09-16 UTC) Classify shortcomings, validate no-write boundary and close package.

## Surprises & Discoveries


Initial manifest is M1, 7.7669 km², NOAA scenarios, GridMetPRISM calendar-labeled
climate (1980–2025), and POLARIS nomograph soil erodibility. Independent checks
confirmed these facts. Official legacy USGS ZIPs remain publicly accessible;
bounded range reads avoid full 170/206 MB downloads. Maximum polygon overlap
matches basin 19384; nearest outlet would incorrectly select adjacent 19381.
Historical XML names STATSGO, correcting the initial SSURGO hypothesis.
USGS predictor rounding requires a derived tolerance, not binary64 equality.
The NOAA header requires whitespace stripping in the audit parser. Failed
intermediate evidence and explanations are retained in artifacts/findings.md.

## Decision Log


2026-09-16 / root: use a new audit package and preserve closed report packages.
No code fixes, model reruns, upstream communication or run-scoped writes are
authorized. Compare same rainfall, not nominal return periods. Distinguish a
synthetic storm catalog with calendar labels from actual subdaily observations.

2026-09-16 / root: retain accepted POLARIS behavior; recommend source disclosure
and benchmark comparisons, not restrictive soil rules. Do not change slopes or
coefficients merely to force agreement. A positive debris-flow occurrence does
not calibrate a probability. Recompute reference probabilities within a bound
derived from six-decimal source predictors.

## Outcomes & Retrospective


Completed audit: all 8,067 event-duration, 12 design and three inverse rows pass;
independent Horn/T/F/S checks pass. Source identities and report currentness pass;
53 monitored files unchanged. USGS basin 19384 overlap IoU 96.10%; run 85.63%
versus USGS 69.35% at I15=24 mm/hour. Soil accounts for 85.8% of net logit
difference, not a measured predictive error. Four prioritized recommendations
are in artifacts/findings.md; no remediation implemented. Exact historical SBS/
DEM replication, observed storm validation and multi-basin calibration remain
outside completed evidence. Existing root code-quality changes were preserved.

## Context and Orientation


Repository `/workdir/wepppy`; run `/wc1/runs/ne/nervous-mesquite`. Accepted
results live in `postfire_debris_flow/attempts/<id>/results/`, with convenience
copies at the module root. `postfire_debris_flow.nodb` identifies acceptance;
manifest records predictors, input provenance, coverage and rainfall request.
Read-only `report.open_assessment` validates accepted hashes and `report.view`
projects saved values. No production writer should be invoked.

M1 predictors are steep-and-moderate/high-burn fraction T, average dNBR divided
by 1000 F, and USLE customary soil erodibility S. Published logistic probabilities
use rainfall accumulation for the specified duration, not intensity directly.
The inverse gives rainfall at a chosen probability. Our code and canonical
specifications are under `wepppy/nodb/mods/postfire_debris_flow/`.

## Plan of Work


Milestone 1 inventories accepted state and hashes relevant files before reading.
Add a package-owned Python script using existing rasterio/numpy/pyarrow in the
weppcloud container to independently aggregate prepared rasters and inspect raw
upload encodings, masks and geography. Do not replace native model processing;
independent array arithmetic is diagnostic verification only.

Milestone 2 independently evaluates published coefficient rows and checks every
saved event/design probability and inverse. Check rainfall accumulation/intensity
units, source metadata, report projection and freshness. Retain scalar summaries,
not private NoDb dumps. Hash inspected files again after completion.

Milestone 3 obtains primary USGS data/publication evidence, prioritizing original
Thomas Fire basin tables. Match geometry/outlet/area before treating probability
differences as defects. If unavailable, retain retrieval limitations and compare
only the documented same-storm benchmark with explicit qualification.

Milestone 4 writes findings with severity, confidence, exact evidence, numerical
impact and smallest next action. Separate confirmed defects from accepted
method differences and scientific uncertainty. Close the audit even if proposed
remediation requires later authority; do not claim that remediation happened.

## Concrete Steps and Validation


Use `wctl run-python docs/work-packages/20260916_thomas_fire_verification/artifacts/audit_saved_run.py`
for retained checks. Read public USGS references with web/network tools and keep
URLs/access dates and hashes for downloaded reference data. Lint package docs
using `wctl doc-lint --path docs/work-packages/20260916_thomas_fire_verification`;
preview uk2us and run `git diff --check`. No broad application suite is needed
unless production code changes (which are outside this audit).

## Idempotence and Recovery


Scripts write only named files under this package's artifacts directory. All
run and scientific data access is read-only. Never construct missing NoDb state,
reconcile job state, alter credentials or overwrite source rasters. Repeat checks
only while accepted identity and source hashes remain stable; report concurrent
user changes rather than silently following a new assessment.

## Artifacts and Interfaces


Retain audit script, compact JSON evidence, reference inventory and findings.
Reuse installed dependencies; no source-acquisition service or new model is added.
No current scientific contract is changed by findings alone.

Revision: created 2026-09-16 UTC for the owner's read-only verification request.
