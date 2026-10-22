# Cedar Creek comparison: independent scientific review

## Disposition

No blocking correctness finding in the final runner, analyzer, or reported comparison. This is a valid descriptive comparison of `wepp_261010` with unreleased native commit `d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`. The operator's `wepp_2601010` spelling is explicitly interpreted as the available `wepp_261010` release.

This evidence does not establish physical water-budget closure, calibration accuracy, or attribution to individual repairs. Signed soil/channel exchange and negative-discharge clipping remain open package boundaries.

## Identity and independent checks

- Frozen Cedar Creek inputs: 864 hillslopes, 371 channels, 10 cm RRINIT, January 1980 through December 2003, MC4 and 600-second outlet samples. Each build generated and consumed its own fresh hillslope PASS files. The runner checks the frozen input manifest and successful completion of all 24 years for every execution.
- All 242 candidate Fortran compilation units independently match the committed native source. Both executable identities and the candidate's earlier validation receipt are retained under `/workdir/cedar-physical-water-comparison-20261021/`.
- Both empty `wepp_ui.txt` markers select hourly soil water balance: native `src/main.for:163`, `src/watbal.for:252`, and `src/watbal_hourly.for:436`. Both fresh H1 WAT headers independently confirm the hourly seepage mode.
- Independent streaming parsing verified 1,262,304 finite, nonnegative outlet samples and 8,766 exact calendar days per build, including every year/day/channel/time field. Native daily publication agrees with EBE. Every daily and annual comparison value, and all 356 descriptive event windows, match independent calculations using `math.fsum`.
- Fresh aggregate-yield arithmetic independently matches every daily CSV value and total; surface runoff, lateral flow, and baseflow sum to streamflow. The final plotting revision leaves all seven metric CSV/JSON files byte-identical to analysis v1.

The retained [independent audit](cedar-comparison-independent-audit.json) pins raw-output hashes, review scripts, source/mode evidence, and the reviewed runner/analyzer. [Comparison metrics and definitions](cedar-comparison/summary.json) retain the complete results.

## Verified results

| Quantity | `wepp_261010` | Repair candidate | Change |
| --- | ---: | ---: | ---: |
| Mean sampled outlet discharge, m³/s | 1.67215618 | 1.68079341 | +0.516533% |
| Sampled outlet volume, million m³ | 1266.461660 | 1273.003350 | +0.516533% |
| Published outlet volume, million m³ | 1272.337712 | 1273.001266 | +0.052152% |
| Maximum reported peak, m³/s | 46.19911 | 46.31255 | +0.245546% |
| Maximum printed sampled peak, m³/s | 46.2 | 46.3 | +0.216450% |
| Aggregated hillslope streamflow, million m³ | 1267.735666 | 1268.205085 | +0.037028% |

All 24 reported annual maximum peaks increase, by 0.222857–2.461208%. Annual sampled volumes increase by 0.458629–0.653537%. Both builds' largest sampled peak first occurs at **1994-10-27 04:40**, at the available ten-minute resolution and printed precision.

The small full-record changes do not describe every event. Across the symmetric 356-window screen, the largest peak increase is **19.066%**, from 0.257 to 0.306 m³/s during November 2–8, 1999. The largest sampled-volume increase is **13.552%** during October 22–28, 1991. The final figures retain these small-flow exceptions alongside the major events.

## Interpretation limits and residual risks

1. **Build comparison includes hillslope changes.** Both lanes use hourly soil balance, and fresh PASS/WAT artifacts differ. The measured +0.037028% aggregate hillslope yield establishes an upstream contribution. Subtracting that percentage from the outlet change would not isolate routing: the yield aggregation is not the complete admitted channel-source ledger, and the channel response is coupled. Individual-repair attribution requires ablations.
2. **Volume definitions must remain separate.** The sampled metric is the right-endpoint sum of printed discharge, whereas publication changes from the release's balance-derived volume to the candidate's accepted outlet integral. For days 2 onward, the candidate's reconstructed trapezoid agrees with publication within the direct half-weight printing bound on all 8,765 days. The release exceeds that bound on 3,455 days. The analyzer uses a slightly looser conservative bound and reports 3,446 release exceedances; this is consistent. Neither check is a physical water budget. First-day `q0` is absent from the printed series and remains unknown.
3. **Timing is descriptive.** Seven-day windows can contain multiple peaks and overlap; they are not independent storms. The first rounded maximum shifts by −2,680 to +4,680 minutes across these windows as the winning maximum changes. For example, the April 6–12, 1983 window has 16 tied release peak samples and two candidate peak samples. These differences cannot establish transit-time or date-label shifts. Centroids also respond to amplitude and baseflow. The common largest-peak timestamp is a narrower, supported observation.
4. **Precision and coverage are bounded.** `chan.out` prints three significant figures; reported peaks include the initial endpoint differently between builds. Annual reported peaks therefore give the more precise magnitude comparison, while timing comes from the printed series. The frequency figure is an empirical plotting-position comparison of 24 annual maxima, with no fitted extrapolation. This calendar contains no non-leap century and does not test the 100-year defect. This one basin/forcing/method/soil-mode comparison does not close daily-mode, MC5, or remaining signed-coupling acceptance.

Reviewed code: [runner](../run_cedar_comparison.py), [analyzer](../analyze_cedar_comparison.py). Production source and simulation inputs were not edited by this review.
