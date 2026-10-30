# Attribute Roads sediment and hydraulic responses by element

## Purpose and context


Execute a bounded scientific experiment, not a production parameter change.
The preceding prepared-soil study had 60 factor-ten export failures, 55 in
unrutted profiles. Normalization now consistently emits the 200 mm boundary,
but does not calibrate erosion. Determine whether road, fill or buffer is a net
sediment source/sink and which element's hydraulic conditioning changes export.

Work in `/workdir/wepppy`. Reuse immutable staged data at
`/wc1/runs/ro/roads-prepared-soil-hydraulics-20261029/inputs` and its reference
folder. Owned historical harnesses are under
`docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py`
and `20261029_roads_soil_benchmark/artifacts/benchmark.py`. Do not edit them.
The exact binary SHA is a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48.

## Progress


- [x] Inspect prior evidence and identify native ELEMENT/WAT output candidates.
- [x] Scaffold scope, immutable-input policy and frozen diagnostic panel.
- [x] Audit source semantics and verify per-element accounting on a retained run.
- [x] Implement and test the isolated harness and fail-closed accounting.
- [x] Execute 66 native cases; all completed.
- [x] Validate consumed inputs, calendars and budgets.
- [x] Report source/sink attribution, factorial effects and next scientific target.
- [x] Complete checks, evidence review and documentation closeout.

## Plan of work


First inspect exact-release native source for ELEMENT SedLeave and WAT terms.
Use existing Rust-backed interchange readers for native files. ELEMENT output
is event/sparse-day data; do not pretend it is a full daily calendar. WAT must
cover all three OFEs for every day in 16 complete years. Verify the meaning of
runoff denominators and boundary sediment flux before calculating differences.
If gross detachment/deposition is absent, report net exchange and its limits.

Second stage frozen soils, prepared 9002 components, lookup and reference assets
in a fresh scratch root. Verify source hashes against the preceding manifest.
Freeze six profiles as listed in package.md. For each, construct eight factorial
cases: each OFE independently uses conditioned or format-only hydraulic fields.
Hold Ki, Kr, critical shear, landuse identity, lower horizons, boundaries,
management and geometry fixed across those eight cases. Retain a separate full
format-only 9002 anchor. Run legacy inputs with both binaries separately; never
mix legacy and modern formats inside one file.

Third run 66 cases using at most six workers and the existing runner. Retain
exact inputs, binary/source identities, stdout, output hashes, report metrics,
ELEMENT, WAT and modern PASS diagnostics. No branch switch, native rebuild or
production source mutation. Fail explicitly on native or accounting errors.

Fourth aggregate boundary sediment exports and net OFE exchanges, water terms,
and paired factorial effects. Compare report export to fresh WEPP2010 controls
using ratios only for positive references, keeping zero cases explicit. Keep
native PASS/report accounting differences visible. Attribute net source/sink
behavior, not origin of every sediment particle. Preserve interactions instead
of assuming additive effects. Use absolute quantities alongside ratios.

## Validation and acceptance


Meaningful tests reject malformed, missing, duplicate or nonfinite accounting
records and wrong calendar/OFE coverage. Validate final model-input horizon
boundaries, unchanged deeper material and fixed erosion coefficients across the
factorial. Bound report/ELEMENT reconciliation by documented printed precision,
not arbitrary fit tolerance. Tests use `wctl run-pytest`; inspect actual native
outputs and reproduce aggregate metrics from retained records before closure.
No physical field validation or production candidate acceptance is claimed.

## Concrete steps


Create artifacts/study.py and artifacts/accounting.py with CLI stage/run/analyze
commands, plus focused tests under tests/tools. Execute through `wctl exec
weppcloud python` using `/wc1/runs/ro/roads-ofe-budget-20261029`. Commands and
outcomes are retained in artifacts/validation.md. Report findings in report.md.
Use canonical doc lint, spelling previews and whitespace checks at closeout.

## Idempotence and recovery


New roots and batch directories refuse existing destinations. Analyses may be
rerun into new analysis directories; do not overwrite executed sources or raw
artifacts. Failed attempts remain recorded and do not count as successful cases.
Preserve the unrelated generated Usersum index and dirty wepppyo3 source files.

## Surprises & Discoveries


ELEMENT already emits SedLeave per OFE but has sparse dates. WAT has cumulative
runoff and local areas; multiplying every Q by local area would misstate fluxes.
Source semantics and reconciliation are a required first milestone.

EBE and ELEMENT are not always equivalent: exact-release source separately gates
report export with qout/iroute. Retain discrepancies rather than widen precision.
All modern WAT boundary transfers pass. SSURGO kslast uses a documented historical
bedrock-proxy reduction; low drainage alone does not establish a unit bug.

## Decision Log


2026-10-30 00:07 UTC: freeze erosion coefficients at existing role-conditioned
values and toggle hydraulic fields only. This implements the requested diagnostic
without conflating erodibility changes with hydraulic effects. Retain a separate
format-only anchor to locate the older raw/prepared contrast. No coefficients
will be selected or fitted based on these results.

2026-10-30: Preserve native accounting failures as scientific findings. Diagnostic
mode records the original bounds, boolean reconciliation outcome and all dated
event mismatches; it still rejects malformed/duplicate/missing/nonfinite records.
Only five of six all-on terminal budgets support precision-reconciled attribution.

2026-10-30: Audit drainage/storage next because surface hydraulic toggles fail
the two selected site cases and their buffers show large water-partition changes.
Do not infer an erroneous kslast conversion from the historical /1000 heuristic.

## Outcomes & Retrospective


All 66 native cases completed. Six factorials preserve fixed fields and deeper
material; all six all-on endpoints reproduce the preceding study byte-for-byte.
The two selected site-climate unrutted failures remain outside factor ten under
every hydraulic combination. Their buffers are large net sediment sources and
generate substantial net surface flow with suppressed deep percolation.
Recommend isolating lower-boundary drainage/storage before erosion fitting.
No production candidate accepted. Seven terminal budgets and 22 EBE events remain
unreconciled, explicitly limiting attribution; see report.md and output semantics.
Repository checks complete: 12,151 passed, 298 skipped. Documentation lint,
spelling previews and whitespace checks pass. Primary-agent self-review completed.

## Interfaces and dependencies


Use existing WEPPpy soil utilities, runner and wepppyo3 ELEMENT/WAT/PASS readers,
with PyArrow for tables. The study modules are isolated orchestration/accounting,
not replacements for native geospatial or model kernels. No new dependency.

Initial revision: authorized study scaffold, 2026-10-30 00:07 UTC.

2026-10-30: Initial container staging could not access the native-source Git checkout.
Retained the failed root and staged on the host into `roads-ofe-budget-20261029-v2`.
All 66 runs completed in `factorial-v1`. Analysis v1 rejected ISO date strings
passed as reader start years; v2 exposed a native EBE/ELEMENT disagreement.
Analysis v3 retains explicit reconciliation status and every discrepancy instead
of widening numerical bounds. See artifacts/output-semantics.md for audited branches.
Final revision: scientific execution and evidence review complete. Full regression
coverage 12,151 passed, 298 skipped; no failures. Doc lint passes.
No production defaults, binary or source projects changed.
