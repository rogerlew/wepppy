# RRINIT Review Tracker

## Progress

Supplemental watershed evidence is preserved separately in the
[Rattlesnake/Topanga comparison record](../../investigations/2026-10-09-watershed-return-period-comparisons/report.md).
It includes both Rattlesnake versions, synthetic and GridMET Topanga, and their
undisturbed scenarios. These are not the canonical hillslope ranking metric.
January 18, 1993 is an open finding only; diagnosis has not begun.

Publication complete: the [current canonical report](../../../tests/disturbed/analysis_results_current.md)
is linked from Disturbed ENDUSER and README and registered in Usersum.
It represents all 96 adopted-default cases, with verified input/output identities,
reviewed expectations and explicit limitations. Eighty focused checks pass,
including report freshness and link rendering; documentation and Usersum
contract validation pass. Historical reports remain preserved. No deployment.

Adoption, 2026-10-09: Roger approved low-severity forest RRINIT 4 -> 6 cm
with [ADR-0083](../../adrs/ADR-0083-low-severity-forest-initial-random-roughness.md).
Updated the shared template and all four corresponding extended-lookup rows.
Existing parser/CSV readback confirms exactly five RRINIT-only changes; all
16 generated low-forest managements match the previously validated candidate.
No other parameter values, model code or binaries changed. Study results below
describe the pre-adoption assessment; no deployment was performed.

Follow-up complete: [low-severity forest 4 -> 6 cm](low-forest-4v6-results.md).
All 96 fresh canonical controls and 16 affected trials completed. Runoff and
full-record rankings are effectively unchanged; sandy-loam PASS sediment falls 17.49%,
including 24 positive-to-zero sediment dates. Other soils show no changes in
compared runoff/peak/sediment outputs at reporting precision. Subsequent
same-date analysis finds low-over-moderate sediment inversions reduced from
17 to zero. Roger clarified adoption as a parameterization inconsistency
correction with more sensible event ordering, superseding the earlier
sediment-trade-off framing. Defaults were unchanged during the experiment;
the approved revision is now implemented as recorded above.

Current: [sensitivity complete](sensitivity-results.md). All 896 final-grid cases
completed, with 192 controls and 704 non-reference trials. Canonical matrix is
96 cases including young forest; 99 integration tests and 14 fast checks pass.
Original invalid climate and year-1 prototype are preserved; final forcing is
a reproducible 100-year synthetic McKenzie Bridge record for 2000-2099.
The sandy-loam fixture retains RR and has large persistent responses; the
other three fixtures decay to the floor. Lower RR does not eliminate the
remaining runoff/sediment rank inversions. No production defaults changed.

- [x] Identify canonical Disturbed templates and current initial values.
- [x] Dispatch a hydrologist agent for the requested literature review.
- [x] Complete map/override/export inventory: 275 records, 25 templates, all roundtrips pass.
- [x] Complete static Fortran trace and illustrative equation evaluations.
- [x] Integrate literature, sensitivity recommendation and evidence gaps.

- [x] Add young forest, explicit hourly context, PASS-v3 and one-sided-event handling.
- [x] Replace invalid default climate with a separately generated finite fixture.
- [x] Complete the 896-run grid, audits, rankings and plots.
- [x] Preserve failures/prototypes and document runtime differences.

The original [assessment](assessment.md) preceded the authorized study. Results
are now ready for Roger's default-revision decision; no production values changed.

## Decisions

Validation: documentation lint passes. An independent inventory rerun is
byte-identical; all inventoried input files are tracked; 25 management
serialization roundtrips pass. The original 444-run proposal was superseded by
the existing matrix scaffold and completed 896-run design.

Historical assessment decision, 2026-10-09 UTC: assess before revising. Keep rrinit distinct from ridge height,
Manning roughness, litter thickness and routing roughness-element height. Do
not change model defaults or launch simulations during that initial assessment.
Roger subsequently authorized the harness changes and sensitivity execution;
this supersedes the assessment-only restriction, not the default-change boundary.

## Findings

Historical scaffold inspection, 2026-10-09 UTC: found tests/disturbed/test_disturbed_matrix.py and
analyze_matrix.py. Prefer this existing scaffold; see
[inspection and required adaptations](harness-assessment.md). Young forest,
release pinning, explicit hourly context and v3 peak parsing were missing;
those omissions are now addressed.
The committed slope is 87.9 m at approximately 38.56%, not the documented
200 m/43%; retain it and add a gentler contrast for storage sensitivity.
That inspection itself did not change code or run models; subsequent authorized
execution is recorded above.

Current disturbed-map templates: forest 0.10 m, young forest 0.08 m, shrub
0.06 m, tall grass 0.02 m. Burned young forest maps to forest burn templates.
The packaged extended lookup disagrees for several unburned classes; a parsed
management inventory and override audit are necessary before naming defaults.
All selected templates use lanuse=1; rrinit affects interrill delivery as well
as depression storage. Those effects cannot be inferred from a routing-only
roughness interpretation.
