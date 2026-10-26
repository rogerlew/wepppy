# Final independent science and QA review

Date: 2026-10-26. Reviewer: `/root/science_review`.

**PASS for the implemented correction, isolated project acceptance and final
regression gate.** No scientific blocker found. This is not
production deployment approval or evidence of original-project regeneration.

Inspected the native implementation: the appended keyword-only `wbt=False`
preserves existing TOPAZ callers; only true invokes the existing Peridot
conversion on the loaded buffer. Roads explicitly passes true. The current
Roads source delta is that keyword alone. Selected-binary forwarding is the
preceding commit, not an undisclosed part of this adapter change. Neither change
is a calibration or physical routing formula adjustment.

Independent checks against actual candidate flovec, relief, subcatchment and
channel rasters verified every step of all five recovered paths against the
Whitebox neighbor directions, distances against raster geometry, and slopes
against elevations. Paths are loop-free and terminate in the expected channel
cells. Segment 000001 reaches 204 over 102.627417 m; 000020–000023 reach 154 over
103.941125, 102.627417, 96.970563 and 97.798990 m respectively. These lengths agree
with the generated execution records and buffer lengths. Every recovered segment
has a two-OFE slope file, nonempty PASS file and a row in the fresh 35-row segment
report. Retained script and results: `independent_science_check.py` and
`independent-science-check.json`.

Recomputed all 20 retained Parquet hashes and row counts against validation.json.
They match the actual artifacts. The project receipt records 35 executed segments
and the four prescribed NoData exclusions, current report resources and completed
watershed execution. The parent replay additionally checks daily area/water
reconciliation, unchanged source/baseline inventories, and current lifecycle
receipt. Native 23-test and focused 108-test results are reported by the executing
agent; this review did not rerun those suites.

Publication disclosure is appropriate: analysis_staleness_current.json explicitly
marks historical full-project routing evidence stale, including the earlier
selected-binary correction. Historical 516-profile results retain their original
provenance and metrics. The publication test compares exact acknowledged source
deltas, preserves the original report hash after removing only the notice, and
retains original results hashes. It does not silently relabel historical evidence
as validating corrected coverage. The isolated replay supplies distinct evidence.

## Limits and final gate

The replay's generic numeric scan rejects infinity, not every NaN/null. Describe
it as an infinity scan plus domain accounting checks, rather than claiming all
fields in every Parquet are finite. Optional/null fields may be valid; any stronger
completeness claim needs column-specific checks. This does not undermine the
independently checked routing geometry and artifact propagation.

The five recovered paths establish encoding correctness and integration for this
fixture; they are not independent field validation of DEM hydrology. The final broad gate is closed by the evidence below; source/binary provenance
remains part of the retained release evidence.
No new production actions are authorized by this review.

## Final gate closure

Reviewed `broad-coverage-summary.json`: all 11,947 collected nodes are covered,
with 11,795 unique passes, 152 test skips and one separately identified collection
module skip. Missing nodes and unresolved failures are empty. The two observed
failures remain disclosed and have later passing executions: the isolated SWAT
run reports eight passes, and the browser-dependent resumed group reports 36.
This is a completed segmented gate, not a claim that the interrupted first run
passed uninterrupted. Native source commit is `71ec98a`.

Also reviewed `profile-readback.json` and `segment-query-readback.json`: all five
recovered profiles expose completed/channel-reaching query results without
profile errors, and have 5,844 daily PASS records and 11,688 two-OFE water rows.
Serialized buffer lengths agree with the independent geometric lengths to the
profile's printed precision. Existing fixed buffer slope 0.4 is preserved; trace
terrain slopes were independently checked as geometry, not claimed to replace
that established profile parameterization. Finite-output claims are now scoped
to required fields rather than every nullable table column, resolving the
wording limitation above. No remaining science/QA condition blocks local closeout.
Production deployment and original-project regeneration remain outside this review.
