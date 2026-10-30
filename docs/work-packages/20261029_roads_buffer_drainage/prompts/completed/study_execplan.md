# Isolate buffer drainage and computational storage

## Purpose and context


Execute the operator-authorized follow-up to the Roads element-budget study.
Two site-climate unrutted profiles remain above factor ten under all surface
hydraulic combinations; their buffers add 733/942 kg/year net sediment and produce
large surface runoff while deep percolation is suppressed. Determine whether
buffer lower-boundary conductivity or computational storage explains the response.
An OFE is one slope element: road, fill and buffer, in that order.

Use `/workdir/wepppy`, prior frozen runs at
`/wc1/runs/ro/roads-ofe-budget-20261029-v2/factorial-v1`, and prior harnesses under
`docs/work-packages/20261029_roads_ofe_budget/artifacts/`. Reuse study.py for its
prior benchmark helpers and accounting.py for verified boundary-budget methods.
Keep these closed-package files unchanged. Exact modern binary SHA-256:
`a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48`.
Native source commit is `b73e93b19a724d1991d341d38a18d11e742231bd`.

## Progress


- [x] Audit exact native depth discretization and frozen drainage provenance.
- [x] Freeze four-profile, 24-run design and scaffold work package.
- [x] Implement isolated staging/run/accounting and focused invariant tests (15 + 2 passed).
- [x] Execute 24 cases; input invariance passes, exact upstream output invariance rejected in 14 cases.
- [x] Compare drainage, storage, sediment and late-year response; all budgets reconcile.
- [x] Complete regression coverage, report, review and documentation closeout.

## Milestones and concrete steps


First implement artifacts/experiment.py with stage, run and analyze commands.
Stage only the four prior all-on cases into a new scratch root, preserving exact
input/binary/native-source hashes and the executed code. Use the same management,
climate, run prompt and geometry. Change only buffer res_lyr.kslast and final
horizon solthk; preserve its 200 mm break and every material property. Keep initial
saturation at 0.75. Cross two drainage levels with depth offsets -1, 0 and +1 mm.
Source-based drainage is 1.512 mm/h for sand, 3.276 for clay and deepest emitted
Ksat for no-restrictive-layer loam. The last is a counterfactual, not a measured value.
Test these invariants and malformed-treatment rejection before executing.

Second run six native workers at most using the existing binary. Commands from
repo root are `python3 <artifact>/experiment.py stage --root <fresh-root>`, then
`wctl exec weppcloud python <artifact>/experiment.py run --root <fresh-root>` and
`wctl exec weppcloud python <artifact>/experiment.py analyze --root <fresh-root>`.
Here `<artifact>` is `docs/work-packages/20261029_roads_buffer_drainage/artifacts`;
use `/wc1/runs/ro/roads-buffer-drainage-20261029` as the initial fresh root.
Require native success and all consumed-input hashes unchanged. A zero-offset,
current-drainage control must reproduce the preceding native outputs exactly.

Third use existing Rust ELEMENT/WAT/EBE readers and audited prior accounting.
Require full WAT calendars, finite values, correctly scaled boundary transfers
and expected computational depths. Compare road/fill daily water fields exactly;
compare sparse sediment fluxes by date, treating absent checkpoint rows as zero
only for zero-load dates and documenting any event coverage difference. Preserve
all sediment report/ELEMENT/EBE discrepancies rather than relaxing bounds.
Compute annual and years 2–16 summaries to distinguish initial-storage transients.
Measure ProfilePorosityCap, SoilWaterTotal, deep percolation, lateral and surface
flows, and signed net sediment exchange. Never call net exchange gross detachment.
Use unchanged WEPP2010 reference reports for similarity, after rehashing their
retained artifacts. No epsilon denominator and no substitution of PASS export.

Finally write report.md, source audit, validation and self-review artifacts;
retain portable JSON/CSV and a standalone plot. Run focused tests with wctl and
full repository coverage using the established disjoint heavy-matrix groups plus
remainder. Run doc lint and whitespace checks. Update tracker and move the completed
plan with wctl doc-mv. No production candidate is accepted solely for closer agreement.

## Validation and acceptance


Twenty-four completed runs, audited consumed soils, complete daily calendars,
verified model depth, reproduced controls and checked upstream invariance constitute
execution acceptance. Scientific conclusions must distinguish diagnostic sensitivity
from physical validity. If native outputs disagree, report a bounded explanation
and its remaining uncertainty; do not silently force closure or alter the binary.

## Idempotence and recovery


Fresh run roots and analysis directories refuse overwrite. Retain failed attempts
and executed source snapshots; rerun into explicitly new directories if needed.
Existing uncommitted OFE-study work and unrelated generated Usersum index/Rust edits
remain untouched. No branch switch, new service, dependency or native compilation.

## Surprises & Discoveries


Exact-release input.for unconditionally adds 200 mm to the last input depth and
then rounds down to the 200 mm computational grid. A 1 mm perturbation can change
computational storage by a full layer. SSURGO /1000 reduction is an explicitly
recorded historical bedrock proxy, not newly diagnosed as a unit conversion error.

Exact upstream output equality fails despite unchanged inputs. IRS assigns effective
runoff duration and recalculates peak runoff across equivalent-plane member OFEs,
so upstream sediment is coupled. Upstream water/state differences also occur and
are retained without claiming every event mechanism has been traced.

## Decision Log


2026-10-30 UTC: use ±1 mm around current bottom depths rather than changing material
properties or removing the normalized boundary. This separates representation
sensitivity from erosion fitting and includes a same-grid +1 mm control.
Use provenance-derived conductivity endpoints, declared before results, and hold
initial saturation fixed.

2026-10-30 UTC: retain the frozen strict analysis failure and add reconcile.py to
quantify every upstream difference. Do not widen precision or call changed outputs
invariant. The experiment isolates buffer input interventions, not independent
buffer-only output behavior. All source/control/raw artifacts remain unchanged. No source tracing/rebuild is needed to test depth readback.

## Outcomes & Retrospective


All 24 native runs completed. Alternative buffer drainage brings both selected
outliers inside factor ten and turns their buffers into net sediment sinks. Effects
persist in years 2–16. Depth reduction crosses a 200 mm computational threshold
but does not resolve current-drainage excess. All 24 terminal budgets reconcile;
no EBE discrepancies. Four prior controls and eight same-grid pairs reproduce
native outputs exactly. Repository coverage: 12,168 passed, 298 skipped, including
two supplemental tests added after collection. Docs, stub and whitespace checks
pass. Self-review complete; no production behavior changed.

Revision: native/scientific execution complete; upstream coupling finding qualified
and source-audited. Physical policy and broad matrix evaluation remain future scope.

Closed 2026-10-30 01:29 UTC; all authorized experimental work complete. Physical policy
selection and broader candidate validation remain separate future work.
