# Precedent Crosswalk

## 20260425_p258-p1319_hillslope_sigfpe-watbal-log10
1. Status/signature: status=`closed`; Two hillslope seeds crash on current release hillslope binary with `SIGFPE` rooted at `log10f` in `watbal_hourly_`.
2. Overlap with current flagged set: none
3. Plausible D-family signature match: none
4. Recommendation: `hold`

## 20260426_taken-brainstem_p1408_hillslope_sigfpe-watbal-log10
1. Status/signature: status=`closed`; A production-origin hillslope seed (`taken-brainstem:p1408`) fails with `SIGFPE` in `wepp_260425_hill`. Reproduction on `forest` confirms the same signature on both
2. Overlap with current flagged set: none
3. Plausible D-family signature match: none
4. Recommendation: `hold`

## 20260427_intriguing-kingmaker_p980_hillslope_eof-stmget
1. Status/signature: status=`active`; Production run `intriguing-kingmaker` failed during hillslope execution on `p980` with a Fortran runtime EOF-read error in `stmget.for`.
2. Overlap with current flagged set: none
3. Plausible D-family signature match: none
4. Recommendation: `hold`

## 20260430_uncapped-spectacular_h2637_hillslope_closure-spike
1. Status/signature: status=`active`; failing run/config: `runid=uncapped-spectacular`, hillslope `H2637` (`p2637.run`). failure signature: large one-day closure spike on `year=1987`, `julian=44` in the legacy daily OFE closure diagnostic.
2. Overlap with current flagged set: none
3. Plausible D-family signature match: D4
4. Recommendation: `extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike`

## Family Coverage
- D0: no precedent found.
- D1: no precedent found.
- D2: no precedent found.
- D3: no precedent found.
- D4: precedent candidates -> 20260430_uncapped-spectacular_h2637_hillslope_closure-spike
- D5: no precedent found.
- D_UNCLASSIFIED: no precedent found.
