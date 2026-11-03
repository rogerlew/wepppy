# MIPA-02 independent QA review

Reviewer: `mipa_qa`, 2026-11-02. Native implementation: `b581352b6`;
contract ancestors: native `0a8727057`, WEPPpy `a42b9d640`.
Reviewed the native test, observer/campaign tools, committed fixtures and retained
campaign artifacts. No shared native source or build was modified by this reviewer.

## Disposition

**PASS for the bounded source/test quality and verified ownership evidence.**
The concrete QA findings below are resolved. This is not release approval:
remaining artifact binding, application/release gates and declared compatibility
limits must be dispositioned in the final validation inventory. In particular,
9005 and RAP cover compatibility do not follow from these 9002 histories.

## Findings and resolutions

| ID | Finding | Resolution |
| --- | --- | --- |
| QA-N01 | Medium: the initial observer builder archived only `src`; its makefile depends on committed `fpm-src/wepp_calendar.f90`, so the retained v1 builds failed. | Fixed in `f0ab62935`; the builder includes that source. Fresh v2 build directories contain it and successful build logs. Failed v1 evidence remains retained. |
| QA-N02 | Medium: the initial comparison loop accepted whichever cases occurred in the candidate receipt, so an empty/incomplete case set could produce a passing result. | `5fce84e93` requires the exact four policy/mode cases in every receipt and rehashes actual binaries, inputs and outputs. Independent QA accepted the complete retained campaign and rejected eight empty/missing-case mutations in temporary copies. |
| QA-N03 | Low test robustness: the first HK-zero guard assertion could pass from zero-initialized COMMON storage even if the assignment were missing. | The revised fixture seeds HK with a nonzero sentinel, verifies zero at the target OFE and unchanged neighboring OFEs. The final 26-test selection passes. |

## Meaningful coverage

The native patch retains the existing arithmetic and control flow while carrying
FC/HK's OFE index. The test suite compiles actual initialization blocks and real
PURK/PERC, varying initialization order, distinct/repeated materials, unequal
layer counts and frozen/unfrozen state. It requires positive percolation rather
than allowing an inactive branch to pass. Private include copies are overwritten
with the complete hillslope role includes, avoiding shared build-capacity races.

Capacity tests execute the real PMET reader through all 32 hillslope and 15,000
watershed plant entries for named and fallback rows, with bounds checks and a
COMMON sentinel. The EVAPPM test compiles its actual mapping/adjustment expressions
with six distinct OFE/rotation selections. Eight drain/lateral source expressions
are compiled against distinct owners. That is expression-level coverage, not a
claim that every full drainage/tile branch executed in a model history. New guard
cases cover both zero UL and zero FC through daily/hourly initializers.

Independent commands from the native repository, with system compiler PATH:

```sh
PATH=/usr/bin:/bin:$PATH pytest tests/test_mofe_coefficient_ownership.py -q
```

Initial reviewed selection: **22 passed**. Final selection including discriminating
guard cases: **26 passed**, retained in `mipa02_qa_native_final.log`. The test
snapshot SHA256 is
`c80475995f3987d1f1492ef38577927610fd21866b3a210aa1baeb3e0824d521`.
QA inspected the retained four before failures; they concern distinct-material
cross-OFE interference, while repeated-material controls passed.

All 24 committed heterogeneous fixture files match their manifest. The full
2000–2015 climate and both material policies are repository resources; required
reproduction does not require the original private projects. These are controlled
material reassignments, not field validation.

## Independent artifact readback

Evidence root: `/wc1/holdouts/mipa-native-r6-20261102`.

For all four default/optional and daily/hourly histories, QA rehashed ordinary
output files and independently compared plain/observer inputs and outputs for
both revisions. Every pair has exact equality of all seven ordinary outputs;
the observation marker is the sole extra input. Recomputing the trace comparison
gives **20 wrong-owner stage/OFE/layer samples out of 30 before**, and **zero out
of 30 after**, per history. Every history contains 15 actual sub-0.95 PERC power
samples. The observer records the first initialization/PURK/PERC-power visit per
slot, not continuous ownership at every timestep. The comparison receipt states
this limit and retains before/after runoff, ET, drainage and terminal-state
deltas over the full histories.

QA also exercised the current comparison helper against real artifacts through
a temporary receipt tree: the complete cases pass and all eight empty/missing-case
mutations fail. Retained result: `mipa02_qa_comparison.log`.

The separate PMET v3 case uses the actual WEPPpy producer, runner and native
observer. QA independently reparsed staged management, followed every year's
OFE-to-crop references, and matched all **48 native records** to their table
coefficients across **three distinct pairs**. All seven ordinary outputs match
plain/observer execution exactly; binary/input/output hashes also match receipts.
Command/output is retained in `mipa02_qa_pmet_readback.log`. Earlier fixture-mount
and calendar-assertion failures remain separate evidence, not successful runs.

## Remaining evidence gates and residual debt

- The original producer contract's reversed-PMET-row-order acceptance is not
  established by the current transition script. Retain a separate reversed-table
  run and native/output comparison before claiming that item complete.
- Single/equal/three material controls use committed
  `tools/physical_water_case.py` and `tests/fixtures/physical_water`. Their initial
  list receipts contain output hashes but no binary/input binding; retain the
  explicit replay invocation and binary/input manifests in final provenance.
- Later tillage/density refresh behavior and missing-density cases are not proven
  by these forest histories. Preserve the unchanged initialization-policy scope.
  Passing a bounded ownership repair does not waive remaining native release,
  paired-binary, application-reader, security or disclosure gates.

The observer builder uses explicit text anchors and hardcoded hill dimensions
for observation arrays. They match this release and fail loudly on incompatible
builds, but future capacity/source-layout edits must revisit them. The campaign
runner deliberately retains bad-baseline observations; the comparison helper is
the acceptance gate. Keep both roles explicit and preserve the negative cases
when extending these tools.
