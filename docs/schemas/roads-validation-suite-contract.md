# Roads validation suite and current report

Status: operator-requested, implementation pending (2026-10-23).

## Purpose and scope

Provide a reproducible Roads parameter comparison based on the clogging-starch
site, a generated current report, and a vendored Usersum publication. Roger
requested a suite comparable to tests/disturbed and a report comparable to its
analysis_results_current.md. This is model verification and sensitivity evidence,
not calibration against measured erosion or proof of absolute field accuracy.
Production parameterization, formulas, route behavior and original site artifacts
are unchanged. Existing Roads accounting, segment-summary and lifecycle contracts
remain authoritative.

## Matrix and site fixtures

Keep canonical inputs, matrix definition, analyzer, tests and current report in
`tests/roads/`. Extract only scientific inputs and provenance from the site;
never vendor NoDb account metadata, credentials or entire working projects.
Commit finite daily climate, shared model inputs, and selected geometry metadata
so profile tests require neither a live project nor Redis/network access.
Pin actual climate dates and execution duration; do not trust the legacy CLI
header's advertised 100 years when the file contains 16 years.

Use three actual completed site segments selected deterministically by shortest,
lower median and longest positive road length (tie-break segment_id). Explain
that segmentation makes the median very short; these are geometry controls,
not three representative whole watersheds. The shortest observed segment is about
0.00861 m; preserve that extreme and disclose slope-file precision effects. Hold one pinned site climate common
across the matrix so parameter comparisons do not conflate different weather.

Cross these geometries with four soils (clay, loam, sand, silt), two surfaces
(gravel, paved), three traffic states (high, low, none), and seven supported
profile arrangements: inslope bare ditch and rocked ditch each with direct
single-OFE and routed road/buffer forms; outslope rutted road/fill/buffer;
outslope unrutted landuse/road/fill, with and without downslope landuse. This is
504 canonical combinations. OFEs are model overland-flow elements. Reuse the
production Roads input builders and model runner; do not reimplement parameter
formulas in the harness. Use production OFE orders (1)=road, (1,3)=road/buffer,
(1,2,3)=road/fill/buffer, (3,1,2)=landuse/road/fill, and
(3,1,2,3)=landuse/road/fill/landuse. Outslope-unrutted cases must call the existing
geometry parity/clamp helper before writing slopes and select legacy soil
templates with design=outslope_rutted, matching the production replacement path
(including paved templates). Retain requested and emitted
geometry (including rounded dimensions), flag clipping, and normalize by actual
WAT area. Isolated profile parity does not represent the full-project strip
allocation algorithm. Pin prescribed fill/buffer/landuse geometry separately
from measured road geometry and identify those assumptions in the report.

The reference uses actual selected road length/grade, width 4 m, fill 30 m at
10%, buffer/downstream landuse 30 m at 10%, upstream landuse 30 m at 10%, and
15% rock fragments. The 12 one-factor controls use median geometry, outslope
rutted, loam, gravel, low traffic: width_2/width_8 (m), grade_half/grade_double
(relative to the measured road grade), fill_length_10/fill_length_60 (m),
fill_grade_2/fill_grade_30 (%), buffer_length_5/buffer_length_60 (m), and
rock_0/rock_40 (%). Persist exact IDs and values in the case manifest before
execution. These experiment choices do not change production defaults.
Separately exercise full Roads controller preparation/execution for all four
designs on isolated site copies, including persisted settings, prepared inputs,
current receipt, summaries and aggregate accounting. Explicitly replace mapped
feature design attributes (defaults alone do not override them) and require
nonzero completed profiles of each requested design with its expected additive
or replacement routing/accounting mode. Record skipped features and reasons;
a no-op completed run is not acceptance. These project checks may
require an explicit local fixture path and must not run against the source site.
Profile tests alone do not certify geographic routing or watershed totals.

## Evidence and report semantics

Read generated slope, management and soil inputs to verify the selected values
reach the executable files. Require fresh model completion, finite required
outputs, complete native daily calendars, unique IDs and positive modeled area.
Use owned native PASS/WAT readers. Include all simulation years and zero-output
days. Preserve native signed detachment/deposition; do not clip values or invent
zero for missing output. Malformed or missing cases fail report generation.

Report mean annual native profile detachment, deposition, profile sediment export,
surface/lateral/baseflow volumes and modeled-area-normalized densities under the
existing segment-summary formulas. Detachment is the primary erosion comparison.
Mixed-profile detachment is not road-prism detachment; full-profile export is not
independently measured buffer delivery or watershed outlet yield. Separate the
whole-project accounting comparisons from the profile matrix.

Describe surface/traffic/texture/geometry contrasts, variability and exceptions.
Do not require universal monotonic rankings, a delivery ratio bounded by one,
or positive erosion in every case. Zero denominator ratios remain unavailable.
Any scientific anomaly remains visible and is assessed before publication.

Persist a machine-readable case summary and provenance sidecar with matrix,
fixture, builder, binary, native-library and analyzer identities plus generated
input/output hashes. Generate the report only from complete verified fresh cases.
Fast repository-only tests verify published source/report freshness without
requiring retained scratch output directories. A changed relevant source requires
rerun/review or explicit stale marking, never silently replacing identity hashes.

## Publication and compatibility

Canonical report: `tests/roads/analysis_results_current.md`. Vendor only its
Markdown through a scoped `wepppy-roads` entry in Usersum vendors.yaml, with
source repository `/workdir/wepppy`, into `vendor/wepppy-roads/tests/roads/`.
Register `usersum.source.roads_validation` as a user-readable vendor document,
link it in Workflows and Modules next to the disturbed results, and link it from
the Roads model guide. Preserve the existing Usersum role and URL contracts.
Do not add an endpoint or modify protected navigation sections. Use the existing
sync/index tooling; do not sync unrelated vendors or commit incidental index drift.
The current CLI syncs all vendors; scope the existing sync_vendor_docs call to
the wepppy-roads vendor mapping, then build-index with --skip-vendor-sync.
source_ref is descriptive metadata, not a checkout guarantee; report provenance
must bind the actual source bytes. Vendor content must equal the reviewed source,
render in Usersum, and have working
links. Keep the report self-contained so its vendor-relative location does not
break source-relative evidence links.

Old project outputs are neither migrated nor overwritten. Full-project tests use
fresh scratch copies; generated suite outputs remain in the selected test/artifact
root. Retain failed diagnostics and never publish a partial matrix as current.
