# R05 Birmingham observed mechanism review

Decision: the retained observations establish a snowmelt-support and routing-branch chain preceding the day 10 lateral-flow difference. This is an evidence interpretation, not scientific admission or an isolated counterfactual experiment.

## Evidence and method

Adapted the original Flagstaff selective extractor into a fresh `R05-birmingham-mechanism-v1` analysis directory. Each raw trace was streamed once and its full hash matched both the passed process receipt and observation readback. Only year 11 days 5–17 were decoded: baseline 53,264 records, candidate 53,025, with 39 daily ledgers per lane. No native run, full canonical reader replay, shared helper edit or earlier evidence write occurred.

`mechanism.json` retains 364 baseline and 362 candidate exact-bit witnesses, selected exact rational daily deltas, and source/input bindings. Its source bindings cover both lanes' MELT, SNOWD, WINTER, DISAG, IDAT, IRS, ROCHEK and WATBAL. Values below are decoded native REAL observations; daily changes are candidate minus baseline on the local OFE2 depth basis.

## Actual forcing, support and branch chain

Day 7 external precipitation is identical at 0.0074000004678964615 m and rain is zero. OFE1 hourly melt support is identical. OFE2's MELT cap at hour 17 returns 0.0001646911259740591 m in the baseline; SNOWD leaves 2.9103830456733704e-11 m snow depth, producing another positive melt hour at 18 (about 1.018634e-11 m water). Candidate hour 17 instead clears the snow; hour 18 is zero.

This follows the actual source path: MELT caps water to snow depth times density/1000; SNOWD converts water back to snow depth and subtracts it, recalculating melt when remaining depth is nonpositive. WINTER publishes hourly melt. DISAG counts every strictly positive connected-segment melt hour, including an arbitrarily small positive tail. For OFE2 the upstream hours 13–15 combine with local hours 14–18 in the baseline, versus 14–17 in the candidate. The observed IDAT duration is therefore 21,600 versus 18,000 seconds; both use a 300-second timestep, with NF 76 versus 64.

Baseline GRNA returns zero runoff, after which IRS executes ROCHEK and returns 0.0017708019586279988 m runoff. Candidate GRNA returns 0.0003131976700387895 m and does not execute ROCHEK for this OFE/day. Final routed runoff is 0.0017708019586279988 versus 0.00008109713235171512 m on the 65.53 m effective-length basis. The ledger converts this to a 24.228960841 mm reduction on the 4.57 m local OFE2 basis. This scale distinction is essential.

Day 9 shows the opposite support-tail direction. Baseline clears snow at hour 18. Candidate leaves 2.3283064365386963e-10 m snow depth and supplies hour 19 melt of about 8.149074e-11 m. Upstream/local combined wet-hour support grows from six to seven hours. IDAT duration becomes 25,200 rather than 21,600 seconds and crosses the source timestep threshold: 600 rather than 300 seconds, NF 51 rather than 79. GRNA returns 0.0027412790805101395 versus 0.0017939013196155429 m; final routed runoff becomes 0.0024821918923407793 versus 0.0015441055875271559 m. The local-depth surface reduction is 13.451376827 mm.

IDAT interception, accepted FIN and infiltration-state operands also differ slightly; day 9 has material antecedent storage differences. Consequently this proves the executed support/branch chain, but does not numerically isolate the effect of duration from other changed operands. Nor does this window identify the first historical cause of the small snow-state divergence. No claim that the interception helper directly changes MELT arithmetic is made.

## Subsequent storage and lateral transfer

| Day | Surface delta (mm) | Lateral delta (mm) | Closing liquid-stock delta (mm) |
| --- | ---: | ---: | ---: |
| 7 | -24.228960841 | 0.308460090 | 23.920476437 |
| 8 | 0 | 4.658563063 | 19.261933863 |
| 9 | -13.451376827 | 13.141063973 | 19.572198391 |
| 10 | 0 | 17.644926906 | 1.927221194 |

Day 10 has zero paired input delta and zero surface/deep/tile delta. Its 17.644926906 mm extra lateral discharge accompanies the decrease in excess liquid stock from 19.572198391 to 1.927221194 mm. Small ET/canopy differences and an exact ledger residual of about 0.000050233 mm remain explicitly retained. This explains the later stock redistribution while locating the earlier support-sensitive routing mechanism. It is not a complete energy, snow or watershed conservation certificate, and no numerical threshold repair is authorized.

## Bound artifacts

- `extract.py` SHA-256 `779c84a7077609c384f1ce30217fdaab71b579c2a2d16130ad449d0ff324e787`.
- `extraction-receipt.json` SHA-256 `d5ad6cde78ec96d70f33ffe623660de387f20f07d4776972e4b075963c35b717`.
- `summarize.py` SHA-256 `3a167c3b15a1901e664a76f5d6ce8f9139c9725ec14a3d2c2af3f90dda0247d6`.
- `mechanism.json` SHA-256 `0130768fb4d23424e86cdab92f34fb48093668d40627b0a4386064447a0b3ebe`.

Documentation lint passed. Review writer clear.
