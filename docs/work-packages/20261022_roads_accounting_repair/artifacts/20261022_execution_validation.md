# Roads accounting execution evidence

## Scope and revisions

Confirmed local implementation of full modeled MOFE accounting, without geographic
overlap inputs. Contract checkpoint: `83f7410e8`; native implementation: `c941cb6`.
The exact native artifact and source hashes are in
[the release receipt](20261022_native_release.json). The local binary includes
preexisting calendar/HBP source edits, explicitly disclosed there and excluded
from this task's source commit. It is not a clean task-only rebuild or production
deployment. Baseline and original UM1 files were not repaired in place.

## Generated and consumed artifact chain

[The UM1 script](validate_um1.py) reconstructed 66 canonical target PASS files
from 100 original sources in an isolated full project copy. Fresh `pw0.run`
contains exactly those 66 canonical paths. All consumed PASS hashes match the
ledger. WEPP `wepp_260409` completed fresh watershed routing; PASS interchange,
water products and the actual average hillslope report were then regenerated.
[Full-record results](20261022_um1_validation.json) cover 5,844 days and 16 years.
All 44 retained original baseline/Roads Parquet files remained byte-identical.

For 2001, corrected runoff is 183.263105 mm, lateral flow 1011.550245 mm and
baseflow 71.456259 mm. The old Roads report had runoff 20082.365246 mm, lateral
flow zero and baseflow 1273.251164 mm. The corrected hillslope area is
441820.29 m² and the actual average report agrees.

The routed outlet summary reports 44.33 ha. Directly summing the 66 serialized
canonical PASS headers gives 441819.27 m²; channel width × length from `pw0.slp`
adds 1481.2595 m², giving 44.33005295 ha, which rounds to the reported value.
The small PASS/WAT difference is explicit serialization reconciliation. Channel
area belongs to routed outlet accounting, not the hillslope TotalWatSed denominator.

After fresh routing, the actual `Roads._regenerate_roads_report_resources()`
controller ran under the final native artifact SHA-256
`4ae01a243bebb596e6bf719626804a04e8ebdced7d9134e170f2af2a1bd31b6e`.
It returned `ready`, policy `roads_modeled_area_v1`, required ledger/accounting
WAT resources present, and no missing resources. Fresh watershed execution used
an earlier native candidate; final changes tighten invalid-input validation, and
all consumed canonical PASS hashes remain identical under the final ledger.

## Persistence and runtime boundary

[Archive validation](20261022_archive_validation.json) used the existing
`project_rq_archive` archive/restore filesystem implementation. Only job/status,
lock and cache callbacks were isolated. All 176 retained lineage files remained
byte-identical after restore; the restored average report rebuilt and admitted
441820.29 m². The local web and worker identities are uid 1000/gid 993.
The pre-fix scratch ledger's mode 0600 was preserved through restore. Separate
unmocked tests prove new ledgers honor umask 007 (0660), and replacement preserves
an existing mode 0640. No production host identity or deployment claim is made.

## Verification

- Final native Rust suite: 110 unit and 17 integration tests passed.
- Independent native Python review: 61 tests passed, including 16 Roads tests,
  43 frozen TotalWatSed tests and two weighted PASS tests. Eight additional
  invalid/overflow probes preserved existing products. Optional absent/empty/
  partial source weighting and independent UM1 terminal lateral recomputation passed.
- Final focused WEPPpy suite: 105 passed, covering accounting, Roads controller,
  water reports, output scope, return periods and native startup preflight.
- `wctl check-test-stubs`: passed. New `roads_accounting` stubtest: passed.
  `output_scope` stubtest retains one preexisting `OutputScope is not a Union`
  Literal-alias diagnostic; the new function/export surface passes.
- Broad-exception changed-file gate: passed, zero net added broad handlers.
- Full WEPPpy sanity first stopped at the startup test's old literal native hash
  after 506 passes and 28 skips. Updated its existing expected release hash to
  match the paired artifact; the full-suite rerun is pending.

The [native correctness review](20261022_correctness_review_native.md) and
[security review](20261022_security_review.md) pass with no unresolved high or
medium findings. Scope-specific evidence does not claim exhaustive scenario
coverage or performance benchmarking.
