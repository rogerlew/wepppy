# RRINIT Assessment Execution Plan

This is a living assessment plan under docs/prompt_templates/codex_exec_plans.md.

## Purpose

Give Roger a defensible inventory and decision about rrinit sensitivity before
any revision of WEPPpy forest/young-forest/shrub/tall-grass defaults. Scientific
acceptance and eventual parameter selection remain Roger's decision.

## Progress

- [x] Preserve the subsequent Rattlesnake and fresh Topanga return-period
  observations before any January 18, 1993 diagnosis. Separate investigation
  record contains eight frozen output series, two ranking settings, provenance
  and reproducible tables. No live-run mutation or new model execution.

- [x] Publish current canonical results for Usersum: select the 96 adopted-default
  cases from the validated 112 runs, verify their input/output identities, and
  generate the report at `tests/disturbed/analysis_results_current.md`. Keep
  `analysis_results.md` historical. Link the report from Disturbed ENDUSER and
  README, register it in Usersum, and document version/default refresh duties.
  Validate source-link rendering, publication contracts and documentation.

- [x] Adopt Roger-approved low-severity forest RRINIT 0.04 -> 0.06 m in the
  shared template and four packaged extended-lookup cells. Record ADR-0083;
  validate existing parser/readback and generated management propagation only.
  Preserve historical evidence, unrelated lookup differences and user overrides.

- [x] Follow-up: assess low-severity forest RRINIT 0.04 -> 0.06 m on the
  canonical profile. Generate 96 fresh current-default controls and 16 affected
  trials from canonical inputs, in one host runtime. Reuse unchanged controls
  when composing the proposed 96-cell matrix. Compare full-record, annual and
  event runoff/peak/sediment outputs, effective roughness and severity ranks.
  No production template changes; report recommendation separately from approval.

- [x] 2026-10-09 UTC: Roger authorized execution and canonical young-forest coverage.
  Extend the matrix to 96 cells, preserving historical IDs 1-80. Pin the study
  to wepp_261009 with explicit committed hourly context. Use current rrinit plus
  0.006/0.010/0.020/0.040 m on existing and 20% profiles: 896 planned runs.
  Repair the analysis reader for PASS v3 and retain one-sided events. Run
  sentinels before the population; do not retune other inputs to rescue failures.
  Defaults, model source and release binaries remain unchanged.
- [x] Correct invalid historical climate through a separately generated finite
  2000-2099 station fixture; preserve the old file and failed evidence.
- [x] Complete 896/896 runs and 99 canonical tests; archive source/output identities,
  report readbacks, rank comparisons, effective-state plots and runtime caveats.
- [x] Report findings for Roger; do not select or deploy replacement defaults.

- [x] 2026-10-09 UTC: inspect mappings, parser, override path and Fortran reads.
- [x] 2026-10-09 UTC: dispatch literature agent with no production write scope.
- [x] Generate reproducible static inventory: 275 entries, 25 template roundtrips.
- [x] Trace state evolution, guards and physical consumers in WEPP 261009.
- [x] Integrate literature and write bounded sensitivity/revision recommendation.
- [x] Documentation lint passes; independent inventory rerun is byte-identical,
  all input files are tracked, and the proposed 444-run count is verified.

## Context and Work

WEPPpy /home/workdir/wepppy is the management producer. Audit
wepppy/wepp/management/data/*disturbed*.json and their .man templates using
the repository parser, then follow generic ini.data overrides in
wepppy/nodb/core/management_overrides.py and Landuse preparation. Compare the
packaged extended lookup as a possible stale export, not assumed authority.
The unchanged WEPP 261009 source is in
/home/workdir/wepp-forest-release-20261009/src. Trace infile -> soil -> IRS,
GRNA/DEPSTO, FRCFAC/RDAT, PARAM, and thermal/snow consumers. Distinguish
initial rrinit from dynamic rrc, conditional decay, and unrelated roughnesses.

Parent owns inventory/static assessment; the hydrologist agent owns only
literature-review.md. Use primary sources, disclose missing measurements and
whether a value is an empirical measurement or a modeling assumption.

## Surprises & Discoveries

The 4-to-6 cm follow-up preserves canonical rankings and practically preserves
runoff but eliminates some small-event sediment delivery in sandy loam, where
6 cm remains above the PARAM interrill-delivery cutoff. Three other soils show
no compared runoff/peak/sediment changes. See ../../low-forest-4v6-results.md.

PARAM clips interrill roughness factor to zero near rrc=0.049565 m. Decay in
SOIL is nested inside a bulk-density guard, so eventual decay cannot be assumed.
The bundled extended table disagrees with some current parsed templates.

## Decision Log

2026-10-09 watershed documentation: Roger requested preservation of encouraging
Rattlesnake/Topanga comparisons before investigating the GridMET January 1993
undisturbed spike. Document only; do not start causal diagnosis or implementation.
See docs/investigations/2026-10-09-watershed-return-period-comparisons/report.md.

2026-10-09 publication: Roger requested a maintained report linked from the
Disturbed user guide to set expectations. Preserve the historical report;
publish `analysis_results_current.md` from the validated adopted-default cases.
Register the report in Usersum's Workflows and Modules section and link it
from ENDUSER and README. Source/context/report hashes provide a repository-only
freshness check; no external run folder becomes a required quality gate.

2026-10-09 rationale clarification: Roger rejects sediment-trade-off framing.
ADR-0083 records correction of a parameterization inconsistency, supported by
more sensible event-level sediment ordering. Same-date sandy-loam comparison
finds 17 low-over-moderate sediment inversions at 4 cm and none at 6 cm.
Full-record rankings are unchanged; do not conflate the two measurements.

2026-10-09 adoption: Roger explicitly approved the low-forest change and
extended-lookup synchronization with an ADR. ADR-0083 supersedes the earlier
no-default-change boundary only for these five RRINIT values. No deployment,
other parameter revision or new study is authorized.

2026-10-09 follow-up: Roger requested canonical-matrix impact assessment of
low-severity forest 4 -> 6 cm. Execute 96 fresh controls plus 16 affected
trials on the canonical profile, reusing the 80 unchanged controls to compose
the proposed matrix. Do not change templates or silently extend to other slopes.

2026-10-09 UTC execution: Roger authorized the study and canonical young-forest
addition, superseding the earlier assessment-only scope below. The old climate
contained six years and 22 NaN dewpoints despite a 100-year header. Generate
separate synthetic forcing from the same committed station, one fixed legal
seed, and a real-calendar 2000-2099 window. Do not fill observed gaps, adjust
roughness to avoid the failure or change WEPP physics. Failed/prototype evidence
is retained. See ../../sensitivity-results.md for results and limitations.

2026-10-09 UTC follow-up: Roger pointed to the existing Disturbed ranking
harness. Inspected tests/disturbed and confirmed it is the preferred scaffold.
Read ../../harness-assessment.md before implementation. The generic 444-run
proposal is superseded by reuse of its committed fixture matrix; no execution
or default changes are authorized by this read-only harness inspection.

2026-10-09 UTC, Roger request: inventory, static analysis and delegated
literature review precede default revision. No simulations or physical source
edits here; a sensitivity plan is a proposal, not an approved campaign.

## Validation

Run audit_rrinit.py with the WEPPpy venv and the stated Fortran source tree.
Verify serialization with the existing Management parser in temporary files.
Analytic equation tables are static illustrations, not simulated responses.
Document source hashes, class mapping aliases and any export differences.
Lint the package with wctl doc-lint. Required future gates use committed inputs;
external scientific studies are supplementary, not hidden dependencies.

## Outcomes & Retrospective

Current report publication: all 96 selected cases verified against current
serialized managements and retained input/output receipts. Analyzer emits the
reviewed user context plus all generated comparison tables. Eighty focused
matrix/Usersum checks pass, including strict-manifest report access. Usersum
contracts and scoped documentation lint pass. No new simulations or production
physics changes; the unrelated full WEPPpy suite was not rerun for this
documentation/report-publication scope. Local index rebuilt without vendor sync.

Adoption completed: template and four lookup cells now use 0.06 m. Structured
readback verifies no other production data changes; 16 canonical generated
managements match the accepted candidate using the existing parser. No tests
were added or rerun for this literal-only edit; prior study evidence remains
unchanged. Existing project artifacts and explicit overrides are not migrated.

Low-forest follow-up: 112/112 successful simulations, 14 harness checks passed.
Sandy-loam PASS sediment 819.45 -> 676.12 kg/100yr, runoff-volume change
-0.0000326%; other textures unchanged at compared output precision. No
full-record rank changes; same-date sediment ordering improves. The earlier
conditional sediment-trade-off interpretation is superseded by Roger's
parameterization-correction rationale. Defaults were unchanged during the
study and subsequently revised under ADR-0083.

Assessment, literature review and authorized study are complete. Maximum PASS
surface-volume response is about 17.89%; maximum peak response 109.35%, and
large persistent sediment effects occur in the sandy-loam fixture. Other
fixtures decay to the floor and show small transient sediment responses.
Weak runoff/sediment rank counts remain 47/48 at every tested level. Do not
tune roughness to force ranks or issue a blanket default change from this
matrix alone. Production defaults and model source remain unchanged.
