# Execute Roads prepared-soil and hydraulic experiment

Completed 2026-10-29: all study runs and repository checks pass; no production
parameter candidate accepted. Native horizon-subdivision sensitivity retained
with a minimal reproducer.

## Purpose


Determine whether landuse-prepared generated soils and a distinct compacted road
layer can explain and resolve material Roads sediment disagreement with fswepp2.
Deliver reproducible native outputs and an explicit candidate disposition. This
is scaffold/surrogate scientific discovery; a successful script is not wired
production behavior. Promotion requires a separate actual Roads preparation and
execution gate with the exact modern binary and consumed artifacts.

## Progress


- [x] Record operator approval and scaffold the follow-up package.
- [x] Trace production conditioning and preparation; pin source inputs and bounds.
- [x] Execute and revalidate 140 diagnostic cases; none meets all five export comparisons.
- [x] Reject promotion and validate frozen roles/raw confirmation across five climates and the held-out soil: 1,440 successful native cases, all artifacts revalidated.
- [x] Validate all artifacts and two minimal replays; fresh repository coverage: 12,083 passed, 298 skipped, no failures. Report findings and close plan.

## Context and orientation


Repository root is `/workdir/wepppy`. Prior scratch results are in
`/wc1/runs/ro/roads-soil-benchmark-20261029/validation-v4`; the prior harness and
report are under `docs/work-packages/20261029_roads_soil_benchmark/artifacts/`.
Its common loss-report parser measures annual full-profile export and positive
spatial net loss, not road-only detachment. Its climate/calendar validator and
reference soil/geometry assembly can be reused with source hashes recorded.
Five climates are Birmingham, Denver, Flagstaff, Charleston and the 2000–2015
site fixture. Four source specimens are sand-class 1718465, clay-class 1718510
from addicted-reservist, and loam 2711184/silt 2711250 from clogging-starch.

Production conditioning is implemented by `WeppSoilUtil.to_over9000` in
`wepppy/wepp/soils/utils/wepp_soil_util.py`, selected by `Disturbed.modify_soil`
in `wepppy/nodb/mods/disturbed/disturbed.py` and its land-soil lookup CSV.
`wepppy/nodb/core/wepp.py::prep_soil` applies saturation, lower-boundary
conductivity and depth preparation. OFE means an overland-flow element: the road,
fill slope and forest buffer are three sequential elements here. Hold their
geometry, management, climate and duration fixed within paired soil comparisons.

## Plan of work


First retain the four base specimens, actual prepared examples and current
production lookup and source identities in a new scratch root
`/wc1/runs/ro/roads-prepared-soil-hydraulics-20261029`. Produce new soils through
owned conversion and preparation functions, read them back, and retain every
intermediate. Distinguish format conversion, landuse conditioning and project
preparation settings. Do not imply a function-level replay is a full-project run.
Reserve generated loam specimen 2711195 from clogging-starch as a new held-out
specimen before inspecting its modeled outputs.

Second run a small diagnostic panel: site sand unrutted gravel high traffic;
Birmingham clay unrutted paved low traffic; Denver loam rutted gravel low traffic;
Birmingham loam rutted gravel low traffic; and a prior agreeing silt case.
Compare prepared-only controls and isolated road/fill/buffer conditioning.
Hold erosion fixed while testing conductivity and treated-layer depth. Derive
bounds from retained input values and the production 200 mm treatment boundary;
label exploratory brackets as sensitivity tests, not measured road properties.
Then test erosion parameters independently. Use native modern readers for water
and sediment diagnostics without mixing their metrics with cross-binary ratios.

Third select at most two candidates using only diagnostic outcomes and physical
interpretability. Freeze identities before broader execution. Validate across all
five climates and original specimens plus held-out 2711195, with unchanged
reference texture-class controls. A new specimen probes within-class variability;
it is not an independent geographic or field validation. If no candidate survives
diagnostics, report the failure and retain a bounded confirmation panel rather
than claim calibration. If a candidate passes, perform actual Roads preparation
in a scratch project before any production proposal or parameter ADR.

## Validation and acceptance


Every admitted native case must consume pinned inputs and the exact
`wepp_runner/bin/wepp_261026`; verify successful native completion, finite
outputs, complete daily calendars, annual summaries, soil readback and hashes.
Missing/failed cases are retained and reported. Require factor-ten positive
reference export and net-loss agreement without hiding material subgroup
failures. Report zero cases separately and absolute errors in kg/year.
Regression tests must cover real risks in new layer splitting and assembly,
especially preservation of deeper soil horizons and non-target elements.
Use `wctl run-pytest` for tests and `wctl doc-lint` for package docs; retain the
full-suite gate or document a concrete blocker. Keep plan and tracker current.

## Concrete steps


Implemented `artifacts/experiment.py`, `artifacts/analyze.py`, and
`artifacts/diagnostic_evidence.py`. The final report provides reproduction commands.
Actual execution from `/workdir/wepppy` used:

    wctl exec weppcloud python docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py stage
    wctl exec weppcloud python docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py diagnostic --batch diagnostic-v1 --workers 12
    wctl exec weppcloud python docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py diagnostic --batch subdivision-v1 --variants split_all split_road split_fill split_buffer format_unsplit --workers 8
    wctl exec weppcloud python docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py validation --batch confirmation-v1 --variants roles raw --workers 16
    wctl exec weppcloud python docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/analyze.py --batch confirmation-v1 --destination /wc1/runs/ro/roads-prepared-soil-hydraulics-20261029/confirmation-analysis-v2 --workers 8
Run container work with `wctl exec weppcloud python ...`, from `/workdir/wepppy`.
Keep large raw native outputs in the scratch root; copy compact summaries,
comparisons, provenance and execution-source snapshots into this package.

## Idempotence and recovery


Staging and each batch refuse existing destinations. Retain failed batches and
use a new name for retries; never overwrite prior experiment evidence. Source
projects and previous study files are read-only. No branch switch, new service,
production setting or dependency is required. Candidate rejection ends conditional
promotion without leaving an implied production implementation outstanding.

## Surprises & Discoveries


The existing clogging-starch prepared soil is 9002, with forest conditioning,
saturation 0.75, lower-boundary conductivity 0.01 and clipping at 700 mm. These
are separate changes from the raw 7778 soil; isolate them rather than label all
of the difference a file-format effect. The current default forest lookup can
differ from the retained project's customized lookup; record both identities.

The equivalent subdivision changed sandy-loam export by roughly 41 times.
Exact-release input.for changes source-horizon conductivity while regridding;
the value can persist below 200 mm in an unsplit horizon. Native paired outputs
and the physical-profile equivalence audit establish the sensitivity; source
reasoning explains it without claiming internal-array instrumentation.

## Decision Log


2026-10-29: preserve the prior study and create an additive follow-up. Use owned
soil conversion/preparation functions, not hand-authored surrogate modern soils.
Reserve a new specimen before examining outputs. Production changes remain
conditional on scientific and generated-project acceptance, not pooled scores.

2026-10-29: freeze roles/raw for broad confirmation before seeing the held-out
soil outputs. Neither is accepted calibration. Retain the native subdivision
finding instead of compensating through erosion coefficients or removing horizon
boundaries to reduce sediment. A native repair is a separate fixed-binary boundary,
and may increase rather than decrease some predictions.

## Outcomes & Retrospective


Scientific execution is complete: 1,615 study cases and two minimal reproducer
replays. All native outputs passed artifact validation; repeated raw-soil results
match the original study. No production candidate is accepted. Roles improves
over raw but fails material unrutted cases, including the held-out matrix.
Equivalent horizon subdivision exposes a native conductivity mutation that must
be resolved before further calibration. The final report and reproducer are in
this package; repository validation passed across fresh disjoint groups (12,083 passed,
298 skipped, no failures). No required work remains in this study.

## Interfaces and dependencies


Reuse the prior strict parser and reference assembly, the owned soil utilities,
WEPP runner and native `wepppyo3` readers. No new external dependencies. New study
JSON/CSV files are isolated evidence and do not change project artifact schemas.

Initial plan: 2026-10-29, capturing the operator-approved follow-up experiment.

Execution update: diagnostic-v1 completed all 140 native cases. Seven new layer
splitting tests and four existing evidence tests pass. Primary preparation uses
9002 and saturation 0.75, preserves lower boundary and total depth; a separate
project control uses Kslast 0.01 and 700 mm clipping. Current default lookup is
pinned, while historical project-conditioned artifacts are retained separately.

No candidate survives the full diagnostic panel. Freeze roles and raw as broad
confirmation treatments, not accepted calibration: 600 profiles each, plus 240
fresh binary controls for the new loam specimen. Selection is recorded before
held-out execution in artifacts/selection.json. A separate 35-case diagnostic
will isolate 200 mm horizon subdivision because the sandy-loam format control
changes export sharply while three other specimen panels are unchanged.

Mechanism update: all 35 subdivision cases completed. In the sandy-loam site
case, original 7778 and unsplit 9002 give identical 109.099 kg/year export; adding
a redundant 200 mm boundary in 7778 gives 4473.288. Buffer-only subdivision gives
2547.390. Exact-release `input.for` mutates source-horizon Ksat while regridding
the top 200 mm, allowing that assignment to affect deeper material in an unsplit
horizon. Retain source-bound explanation and native evidence in artifacts/mechanism.md.
Do not expand into a native repair or compensate with erosion coefficients; this
study fixes the binary identity and can conclude with a documented native-input
sensitivity and rejected parameter candidates.

Scientific closeout: 1,615 total new native runs (140 diagnostics, 35 subdivision,
1,440 confirmation), no native failures. Roles export meets the band in 503/563
positive-reference cases (98/114 held-out), but only 58/113 unrutted cases and
material 22–68× errors remain. No production candidate is accepted. Original
480 raw-soil metrics and annual series reproduce exactly. An initial analyzer
failed on an additive field absent from old records; a strict shared-metric
comparison plus fresh parsing resolved the bookkeeping mismatch. All attempts
and execution-source snapshots remain retained. Repository tests passed: 12,083 passed, 298 skipped, no failures.

Final revision: 2026-10-29 22:36 UTC. Close the scientific work package with a
negative parameter-promotion decision, verified native sensitivity and completed
repository validation. No native repair, production integration or deployment
is implied by this completion.
