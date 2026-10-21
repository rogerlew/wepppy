# Repair execution checkpoint

Status: active, not complete or release-ready. Native checkpoint: `22133f0c9`. No dated release, vendoring,
deployment, default change, push or original-project mutation occurred.

## Implemented and locally validated

- CONTIN initializes groundwater from total hillslope area and resets prior
  withdrawals only at simulation start. The existing recharge/withdrawal timing
  remains unchanged.
- WATBAL_HOURLY retains positive infiltration remainders and bounds negative
  allocation by represented liquid inventory, using binary64 working stores.
  Impossible withdrawals fail explicitly rather than silently dropping water.
- CHRQIN reconstructs flat source cells from volume and duration using binary64
  interval overlap; invalid positive-source durations fail explicitly. This
  establishes source-cell accounting, not every solver's input integral.
- WSHCHR executes its existing MC recurrence when retained interior discharge
  is nonzero even if boundary/lateral forcing is dry. No coefficient, Manning,
  storage-definition or clipping changes accompany this control-flow correction.

The operator's MC decision is recorded in ADR-0101, **MC continuity decision
(operator authorized)**, and the native physical-water contract. It supersedes
the previous recommendation to impose geometric-volume authority.

## Validation evidence

Current candidate source/build identities: `mc-guard-build-provenance.json`.
Both profile binaries use `/usr/bin/gfortran` and the compatible system loader.
The four changed native routines match the retained build tree byte for byte.

- Full native suite: 369 passed, four strict expected failures, two existing
  tarfile deprecation warnings; 567.32 seconds with other work running.
- Focused source/state/component controls: 165 passed, four expected failures.
- Permanent watchlist: all 12 complete 100-year cases pass.
- Both profile host smokes pass.
- All 29 fresh paired replay validations pass: ten two-year generated cases,
  eighteen 44-year audit configurations and one 400-year hourly 60/40 case.
  Date order, finiteness, all OFEs, PASS delivery and local/upstream transfers
  are checked; this is not whole-watershed physical closure.
- Six dry-boundary interior-pulse tests fail before the guard and pass after it;
  two all-zero controls pass both. MC4 and MC5 are included.
- Sixteen single-channel MC controls and eight actual WSHCQI/WSHCHR cascade
  controls retain full per-step/source/transfer observations. Independent
  observation parity and parser-corruption checks are retained.
- Earlier 44-year native hourly observations for one/two/three OFEs have zero
  unallocated remainders and unchanged scientific outputs with observation on.

The first 400-year fixture attempt failed at management EOF after 44 years;
explicit annual management expansion corrected the generator. The initial
MC-guard build attempt omitted `fpm-src` and stopped before compilation; the
complete isolated tree then built both profiles. Neither failed attempt is
counted as validation.

## Guard-only replay differences

Compare the new candidate to the three-fix v4 candidate, not to unrepaired 261021.
All files under `output/` are byte-identical in 28 of 29 cases. The daily-side
case changes three printed channel-waterbalance rows, with a largest affected
printed depth difference of 0.000001 mm; other fields are unchanged.

Native routed output also changes: daily-side has eight printed sample changes.
Hourly-cascade has nine affected channel-days; seven change from a compressed
near-zero daily record to 144 time samples. The largest shared-time discharge
change is 0.0000000234 m³/s. Keyed date/channel/time comparison is essential:
line-by-line comparison misleadingly reports millions of differences after
those additional records. Daily `chanwb.out` remains byte-identical in all cases.
These small retained-run effects do not limit the magnitude of the seeded defect
or establish natural-run incidence beyond the inspected cases.

## Remaining findings and next repair

`mc-continuity-findings.md` separates MC continuity increments, coefficient
revaluation, grid/boundary changes, clipping and publication. The fixed-grid
control balances against MC algebraic storage; geometric mismatch alone is not
water creation/loss. Variable K/X requires explicit revaluation terms when using
endpoint storage diagnostics.

The cascade audit proves two conflicting representations: upstream daily
publication transfers exactly into downstream daily intake, while upstream
rates transfer exactly into downstream rates. Their upstream discrepancy is
therefore inherited downstream. Correcting a copy operation cannot repair it.

Next work must reconcile source-cell/point integration, signed local exchange,
deferred baseflow and accepted outlet versus daily publication. Preserve MC
recurrences and distinguish numerical storage increments from geometric
inventory. Do not normalize the hydrograph or label a residual-derived store
as observed physical water. Four channel-local tests remain strict expected
failures and package closeout remains blocked on those scientific interfaces.

Impoundments, tile/contour/general geometry coverage and independent complete
initial/interception stores remain limits on broader certification. The original
Ayush decks were not supplied, so historical-case attribution is unavailable.

## Recovery

Keep paired 261021 binaries and historical outputs immutable. Local candidates
are under `/workdir/watershed-physical-water-repair-20261021`; select the prior
pair for comparison and regenerate contributing hillslopes, PASS and watershed
together. Revert individual source lanes if their invariants fail. The independent
MC guard is not a substitute for the unresolved source/publication repair.
