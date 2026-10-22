# Roads lateral-flow investigation tracker

**Started / updated**: 2026-10-22 20:05 UTC  
**Phase**: Diagnosis complete; implementation deferred  
**Security impact**: none; dedicated security review not required

## Progress

- [x] Locate forest copy and reproduce all-zero roads lateral flow.
- [x] Retain source hashes, ID populations, area ranges, and annual totals.
- [x] Open package and active investigation plan; register on project board.
- [x] Trace raw-file assembly and native aggregation to the first divergence.
- [x] Replay the suspected boundary on isolated inputs.
- [x] Record causal conclusions, affected scope, and minimal repair proposal.

## Decisions

2026-10-22 20:05 UTC: Scope is diagnosis and repair recommendation. Preserve
synced source artifacts; compare WAT and PASS populations before considering
native model changes. This implements Roger's request to open an investigation.
The authoritative scope and rationale are in package.md, “Investigation contract
and rationale”.

## Findings and remaining risks

Roads WAT has 34 segment IDs; roads PASS has 100 IDs. Road-only area is used in
roads totalwatsed. Confirm whether the assembly boundary omits baseline WAT,
whether native aggregation sums all PASS IDs, and whether segment PASS is
counted again after incorporation into target hillslope PASS. Baseflow needs its
own percolation/storage trace. No root-cause closure or repair claim yet.

## Validation

Read-only inspection succeeded on forest at repository revision
`38df23fbf5696b9cc5b5cdbbd6f15fa297a5286e`. This identifies inspected source,
not the production revision that originally generated the synced outputs.
Evidence: `artifacts/initial-inputs.json`; reproduction: `artifacts/inspect_inputs.py`.
No production code or run data changed; runtime test suites are not applicable.

## Next action

Execute milestone 2 of the active plan. Keep original artifacts immutable and
record native package/binary provenance before any scratch replay. No external
blocker is known.

## Completed investigation — 2026-10-22 UTC

[Diagnosis](diagnosis.md) confirms omitted baseline WAT, wrong runoff denominator,
and duplicate segment PASS contributions. Four unmocked native replays cover
all 5,844 days. Original roads water metrics reproduce exactly; all six source
hashes remain unchanged. Next action is a contract decision on additive and
replacement report hydrology, followed by a separately scoped repair. No runtime
change or production repair was performed. Earlier next-action notes are superseded.
