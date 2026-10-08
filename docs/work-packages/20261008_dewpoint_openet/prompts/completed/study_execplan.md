# Evaluate dewpoint clipping using paired hillslopes and OpenET


Completed 2026-10-08: 18 successful paired runs and 36 complete OpenET series.
Existing clipping has lower monthly MAE/RMSE in every site–product comparison.
Results support retaining current behavior and deferring a general disable
switch. See `artifacts/results.md` within this work package for scope and limits.


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective at every handoff.

## Purpose / Big Picture


Produce an executable, auditable comparison of existing clipped dewpoint against
unclipped source-derived dewpoint. The result informs whether an advanced user
option merits implementation; it does not change the existing climate policy.
The user can inspect monthly ET plots and paired water-balance summaries across
multiple hillslopes and compare them with independently retrieved OpenET series.

## Progress


- [x] (2026-10-08) Audit WEPP and CLIGEN; locate historical forcing and OpenET API.
- [x] (2026-10-08) Record study contract and obtain credential location from user.
- [x] (2026-10-08) Verify exact reconstruction and official OpenET access.
- [x] (2026-10-08) Freeze nine hillslope fixtures and selection before execution.
- [x] (2026-10-08) Execute 18 cases and validate 234,498 daily rows and input isolation.
- [x] (2026-10-08) Retrieve 36 complete OpenET series and component/bias diagnostics.
- [x] (2026-10-08) Publish results, inspect figures and record bounded recommendation.

## Surprises & Discoveries


The CLI header can advertise 100 simulated years while the project uses a shorter
observed history; use actual daily dates and run control years. Existing spatial
GridMET climates adjust local Tmin/Tmax after source dewpoint clipping, so
`Td < local Tmin` alone does not identify whether the source rule was disabled.
Historical Topanga OpenET ET exceeds long-term precipitation substantially;
OpenET cannot be treated as an error-free calibration target.

The polygon API rejects a single GeoJSON Feature with HTTP 404 but accepts a
FeatureCollection containing the same geometry. Retained evidence includes the
failed request. Successful response times range from about 2 seconds to over two
minutes. `Ep` includes canopy interception evaporation after `swu`; the PMET
`Es` includes residue interception and `Er` is zero in all selected outputs.
The separate snow diagnostic `etm` is not written to the water-balance file.
Therefore use reported `Ep + Es + Er`, explicitly qualify snow-period comparison,
and separately compare months with both arms' maximum reported SWE <=1 mm.

Source humidity recovery matches archived clipping exactly, but hillslope
spatial adjustment produces occasional Td above local Tmax and a local Tmin/Tmax
inversion. The paired experiment preserves those inputs and records dates in
`artifacts/climate-quality-events.csv`; it does not silently repair them.
Higher annual ET can worsen monthly agreement: Topanga's additional winter ET
does not address the large modeled summer shortfall against OpenET.

## Decision Log


2026-10-08, Codex: retain Anurag's clipping policy and all production code. Compare
the effect of disabling the upstream floor while preserving subsequent spatial
adjustments. Reuse retained humidity rather than inventing dewpoint below the
clipped values. Choose sites before seeing ET responses, with common 2016–2022
assessment and available earlier years as spinup. Use standalone frozen hillslope
fixtures, not ad hoc cloned projects, following existing research matrix practice.

2026-10-08, Codex: use archived Topanga undisturbed inputs because post-fire
management is inappropriate for the historical comparison. Use the same vendored
`wepp_260803_hill` binary (source `f24c957e3633898e0fd4cbbea5ae08c781f29dba`,
SHA-256 `86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7`)
for all pairs. Select cover 52 shrubland or 42 forest, area >=27,000 m2, closest
to 20th/50th/80th elevation quantiles; report rather than optimize aspects.
No existing project or production executable was changed.

2026-10-08, Codex: add a secondary low-snow comparison after discovering the
unreported snow diagnostic. The <=1 mm SWE criterion is a declared research
screen, not a production parameter or proof of no intraday snow. Retain the
all-month comparison as primary; do not filter sites based on agreement.

2026-10-08, Codex: recommend retaining clipping and deferring a general disable
switch. All 36 site–product comparisons favor clipping for monthly MAE/RMSE,
including low-snow months. Forest ensemble scaling sensitivity at 1.20/1.25
also retains that ranking. Preserve raw source values for further scientific
testing; no claim is made that clipped humidity is inherently more physical.

## Outcomes & Retrospective


The bounded study is complete. Removing the floor increases reported annual ET
by 35–69 mm but worsens monthly agreement with all four OpenET products at every
site. All 63 ensemble site–year monthly MAE comparisons favor clipping. The
effect also changes soil water, lateral flow and snow duration. No numerical
failure occurred. Current production behavior remains unchanged.

The principal limits are three correlated watershed climates, GridMET-derived
humidity, prescribed vegetation, one executable and ET formulation, unreported
snow flux accounting, and OpenET uncertainty. Topanga's satellite ET/precipitation
discrepancy precludes using those ET totals as an unquestioned calibration target.
Daymet/PRISM and independent flux/snow observations are future research, not
unfinished acceptance requirements of this nine-hillslope screening study.

## Context and Orientation


The current GridMET client `wepppy/climates/gridmet/client.py` derives dewpoint
from average Tmin/Tmax and average minimum/maximum relative humidity using
MetPy, then floors it at source Tmin. The retained `climate/gridmet_*.parquet`
tables include those humidity inputs. Prepared files in `wepp/runs/pN.*` contain
the exact hillslope climate, management, slope, soil and run controls consumed by
WEPP. `watershed/hillslopes.parquet` maps WEPP integer IDs to TOPAZ spatial IDs,
centroids, area and elevation; subcatchment GeoJSON supplies geometry.

Candidate roots are `/wc1/runs/ha/hand-to-mouth-drought` (Topanga shrubland),
`/wc1/runs/ap/apostolic-saw` (Tiger-Mill) and
`/wc1/runs/cr/cryptic-beechnut` (Washington Cascade foothills). Verify land cover
from their actual management inputs, not inferred geography. Preserve source
projects. The shared evaluation years are 2016–2022 inclusive, with at least
16 preceding years at the shortest record. A hillslope is a modeled sloping land
unit; several such units sharing climate are spatial subsamples, not independent
watersheds.

## Plan of Work


Milestone one creates `artifacts/study.py`, a command-line research runner and
source manifest. Check exact daily calendars and source fields; reconstruct raw
dewpoint and quantify any MetPy-version rounding differences against archived
clipped values. Fail or explicitly resolve discrepancies before changing input.
Select three eligible units per watershed near lower, middle and upper elevation
quantiles, considering sufficiently large polygon support and distinct aspects.
Write selection and reasons before executing. Pin the WEPP binary and hash.

Milestone two freezes only required standalone model input files, including
ancillary parameter files. Both arms must use identical non-dewpoint tokens and
identical executable. Keep archived clipped climate as baseline; in the raw arm
replace daily dewpoint only where the original source floor acted, using verified
raw reconstruction. Save source and fixture hashes, stdout/stderr and failures.
Run complete historical periods, summarize common assessment years, and retain
all daily water output for evidence. Validate full date coverage, finite outputs,
successful terminal records, and exact paired input isolation.

Milestone three uses POST `https://openet-api.org/raster/timeseries/polygon`,
`Authorization` equal to the secret file contents, with monthly interval, version
2.1, model Ensemble, variable ET, units mm, reference_et gridMET and reducer mean.
Use GeoJSON polygon geometry in longitude/latitude; do not upload assets. Retain
request JSON without headers and full response. Start with one bounded probe,
then collect 2016–2022 ensemble and selected component models across sites.
Record coverage, model availability, units and retrieval dates. The API schema is
public at `https://openet-api.org/openapi.json`. Refuse redirects to other hosts.

Milestone four aggregates WEPP ET as plant transpiration plus soil and residue
evaporation from the daily water balance, explicitly checking canopy interception
and snow sublimation reporting before claiming comparability to total OpenET ET.
Compare monthly totals, seasonal bias and MAE/RMSE for both arms; report annual
water balance and snow diagnostics. Plot individual hillslope series and paired
ET effects. Describe OpenET model spread, spatial support and vegetation/history
limitations. Do not pool hundreds of months as independent watershed replicates.

## Concrete Steps


Work from `/home/workdir/wepppy`. Implement and retain the bounded commands in
`artifacts/study.py`, with separate prepare, run, openet, analyze and verify phases.
Use `.venv/bin/python` and installed requests, pandas, NumPy, MetPy and plotting
tools. Record exact commands and external execution root after preparation.
Read the secret only inside the authenticated request phase, never as a command
argument or log. Run `wctl doc-lint --path` for each changed Markdown file.

Executed from the repository root:

    .venv/bin/python docs/work-packages/20261008_dewpoint_openet/artifacts/study.py prepare
    .venv/bin/python docs/work-packages/20261008_dewpoint_openet/artifacts/study.py run
    .venv/bin/python docs/work-packages/20261008_dewpoint_openet/artifacts/study.py probe
    .venv/bin/python docs/work-packages/20261008_dewpoint_openet/artifacts/study.py verify

The `openet`, `analyze`, and final `verify` phases completed. Both PNG figures were
visually inspected and summary metrics reconciled. Execution evidence resides at
`/home/workdir/wepppy-scratch/dewpoint-openet-20261008`; source fixtures are also
retained in `artifacts/fixtures.tar.gz` with an archive hash. Authentication failure
or missing coverage must not be recoded as zero ET or successful completion.

## Validation and Acceptance


Require nine selected hillslopes across three watersheds, both arms completed and
daily dates reconciled, with identical non-dewpoint forcing and parameter hashes.
Explain every changed dewpoint day and all exclusions. Require archived OpenET
series with explicit coverage and spatial/model provenance and monthly overlap
checks. An inconclusive comparison is a valid scientific outcome if limitations
are supported by evidence; a failed extraction is not a completed comparison.
Review the rendered figures and reconcile their plotted totals with CSV tables.
Production tests are unnecessary unless production code changes; none are planned.

## Idempotence and Recovery


Never overwrite existing project inputs or successful evidence silently. Reuse
cached API responses only when request identity matches. Failed runs retain logs
and are not counted as complete. Use per-arm directories and bounded subprocess
timeouts. Any recovery must preserve failure evidence and document its cause.

## Artifacts and Notes


Package-relative `artifacts/` contains executable research code, input/API
manifests, summaries, figures and results. Large raw daily outputs may reside in
a named external study directory with a manifest path and hashes. Compact source
fixtures should be archived for reproducibility. The OpenET key is never an
artifact. This study is scientific screening, not a deployed workflow test.

## Interfaces and Dependencies


No added dependency, new service or production interface. The WEPP executable
reads an existing `pN.run` on stdin from its prepared directory. OpenET is called
only on its official HTTPS host. Reuse established WEPP water-output field
definitions and source-check ET accounting. A future option/default/formula
change requires its own reviewed contract, regression plan and ADR.

Revision 2026-10-08: initial registered study plan following the user's request
and credential provision; no scientific outcome or policy change claimed.

Revision 2026-10-08: record completed paired runs, precise site selection and
binary identity, API format discovery, and secondary snow-accounting screen.

Revision 2026-10-08: close the bounded research execution, record all comparison
outcomes and limits, and promote the conservative policy recommendation into
the current PRISM client design. No implementation or deployment is claimed.
