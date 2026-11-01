# Comparator outcome scientific review

Disposition: failed experiment admission. The twelve declared comparator processes produced eleven accepted complete histories and one native failure. Deferring all twelve proposed consumer-observer histories is scientifically appropriate. No native repair, replacement invocation or tolerance change is warranted by these observations alone.

## Actual outcome and contrasts

The aggregate receipt is explicitly unsuccessful. The failed cell is source 84543461, candidate retention, KSFLAG1; return code 1 and no completion marker. Stdout locates HOURLY_WATER_UNMET at simulation year 9/day 355/OFE3/hour 1. Baseline retention with KSFLAG1 and candidate retention with KSFLAG0 both complete. All eleven accepted histories retain 17,532 daily records and complete daily-gate support. The zero-rock baseline/candidate ordinary-output hashes are identical under each KSFLAG setting.

Actual FROST_CALL counts in the three baseline KSFLAG1 histories are 106,774, 111,786 and 243,109. Their selected windows are year1/day9, year1/day9 and year1/day2. This establishes actual frost exposure in the experiment, but not a frost-specific cause for the failure: KSFLAG also changes conductivity. The incomplete cell cannot enter a complete-history output contrast as though its truncated output were an ordinary numerical difference.

## Source-bound failure interpretation

Pinned hourly water balance assigns hrfin=xfin before the observed diagnostic and tests -dble(xfin)>sum(max(0,ST)) for a negative hourly request. Stdout prints hrfin=-2.42531928e-12 m and available=0. This is a rounded diagnostic, not an exact retained binary32 bit pattern or a demonstrated arithmetic cancellation chain. It is approximately 2.4253e-9 mm in magnitude. The exact strict comparison rejects a negative request when the allocatable relative storage is zero.

I independently inspected the last complete OFE3 snapshot, IRS_WB_PRE sequence976157 at year9/day355. Its four layers have ST=FRZW=FROZEN=0. Summing ST+dry*(DG-FROZEN) from these retained values gives 43.19526128750084 mm of dry-reference liquid over approximately600 mm native support. This snapshot precedes the failed hourly call; it is not a replacement for exact guard-site operand observations. Positive absolute liquid does not imply positive allocatable ST under the current withdrawal contract.

The evidence therefore does not establish zero absolute water, negative absolute water, or currently frozen water at the retained boundary. The request's tiny magnitude makes numerical cancellation a plausible hypothesis, not a proven origin. Earlier frost history and a successful KSFLAG0 contrast do not isolate frost causality or validate a retention replacement. The guard failure is a reproducible admission blocker in this configuration, not proof that the source water limits are physically invalid.

## Next bounded experiment

First declare a targeted replay of the failing cell with the existing BP_WBH_SOURCE, BP_WBH_ALLOC and BP_WBH_BEFORE observations at year9/day355, including the preceding day if supplied by the existing marker. Retain the expected stop. Establish parity of the completed FH/output prefix against this failed comparator rather than require a completion marker or terminal FH footer. Determine which routed-return, FIN, area-scaling and temporal-allocation operands are already recoverable before adding instrumentation.

Reconstruct the signed request with source-owned precision and operation order, distinguishing the original demand from its allocation. Do not spend dry-reference liquid, drop a tiny residual, or insert a floor merely to make the process finish. Any subsequent behavioral proposal needs its own justified contract and controls. The planned consumer-domain/selected-flux campaign remains deferred; its unbuilt/unexecuted helper controls provide no native coverage or physical closure evidence.

## Findings review and bindings

The reviewed findings correctly distinguish failure, compound configuration effects, last-state water coordinates, selected exposure and missing consumer evidence. Their proposed next experiment is appropriately narrower than a native repair. No scientific wording correction is required. Helper-control and archive verification claims are separately owned by their implementation/packaging receipts.

- `docs/work-packages/20261101_retention_frost_consumers/artifacts/findings.md`: `08530365d3100cbe97de3e8fbb644adeaeaca9b4775cb0820063559fe64e75ad`
- `out/retention-frost-consumers-20261101/comparators-v1/receipt.json`: `edf610a1757bbb03a87a72ab9e9a6e42ab4eca7cd95c230206a02e6da492ad9b`
- `out/retention-frost-consumers-20261101/comparators-v1/selected-windows.json`: `2e87c755f9e94558952b8a7c865306e8c22e84a7c0a2f9ab66e90ce5dc3fd018`
- `out/retention-frost-consumers-20261101/comparators-v1/84543461-candidate-ks1/receipt.json`: `ff272759bddcc490af23d878913c1da65f63843d664efd13b3c833e19bd81fb8`
- `out/retention-frost-consumers-20261101/comparators-v1/84543461-candidate-ks1/runs/stdout`: `262351a5d14c193d0e7c7a4c7f2a6626d5dadd66f8b2770597b3e0cc8e086c76`
- `out/retention-frost-consumers-20261101/comparators-v1/84543461-candidate-ks1/runs/frwatc-history.txt`: `b0666f3c0882c96266789e279220c36f4b9699418315b033cd8e0eee2a5d8bcd`
- `out/frozen-water-flux-20261101/campaign-v2/build/src/watbal_hourly.for`: `b9405810a972dfbaefdd2996aec0c02612fd99dcd9a70e516edaf9dba62ad611`

Review complete. No raw evidence was modified; reviewer writers are clear.

## Final findings addendum

The expanded findings are accepted. Their added calendar paragraph and frost-call table agree with the compact summary and the already reviewed comparator receipts. Independent read-only parsing confirms 9,830 failed-cell daily rows, ending at OFE2/year9/day355; this remains a partial prefix, not full-history admission. All eleven accepted histories have 17,532 rows. Accepted KSFLAG1 FROST_CALL and FROST_DONE totals match, and all six KSFLAG0 histories have zero actual frost calls.

Independent comparison of summary output hashes confirms zero changed ordinary files for either zero-rock retention pair, four changes for moderate-rock KSFLAG0, and seven for each high-rock pair. The failed moderate-rock KSFLAG1 cell remains excluded. These additions do not alter the failed-admission decision or imply physical improvement.

This addendum binds the current public files and preserves the historical findings hash above:

- `findings.md`: `49c4a0949b862314e570b48482e8b501d5d4d1ab6baba4c23fd70c0eb3df5e23`
- `summary.json`: `502385143ca85d3116ad67c514427d69bd4a3237b5d4e39124442ab33eb1a663`

No frozen raw files were written. Public review writers are clear.
