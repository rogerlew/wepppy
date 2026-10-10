# Same-Input WEPP 260803 Comparison

2026-10-10 UTC. Roger supplied
[eighty-five-synthetic](https://wc.bearhive.duckdns.org/weppcloud/runs/eighty-five-synthetic/disturbed9002_wbt/),
a fork of `scrawny-relay` rerun with `wepp_260803` and its undisturbed Omni
scenario. Existing results were inspected and preserved; no new simulations
or physical input changes were performed for this comparison.

## Provenance

All 284 hillslope execution logs in each old-version scenario identify successful
`wepp_260803_hill` runs, SHA256
`86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7`.
Both watershed execution logs identify successful `wepp_260803`, SHA256
`4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`.
This supplies the required same-build hillslope regeneration; `261009` PASS
files were not substituted under the older watershed executable.

The fork uses GridMET 1980-2024. Burned climate, slope, management, soil,
channel, structure and run files match `scrawny-relay` byte-for-byte. Undisturbed
files also match except 273 soil files with comment-only date/path differences;
all non-comment soil contents match. Shared `chan.inp`, `wepp_ui.txt`, PMET,
snow, groundwater and `tc.txt` files match, as do the impoundment files.
The undisturbed climate/slope references use the respective identical parent
inputs. New-version EBE files still match the frozen pre-investigation hashes.

This is a controlled comparison of the two released binary pairs with matching
effective inputs. It does not isolate a particular source patch or distinguish
hillslope-producer changes from routing changes within the combined release.

## January 18, 1993

| Scenario | 260803 peak, m3/s | 261009 peak, m3/s | 260803 volume, m3 | 261009 volume, m3 |
| --- | ---: | ---: | ---: | ---: |
| Burned | 106.42034 | 76.03957 | 213,215.02 | 213,282.16 |
| Undisturbed | 27.85154 | 707.63910 | 219,667.84 | 218,608.19 |

The undisturbed peak increases **25.41 times** while daily volume decreases
only **0.482%**. The burned peak decreases 28.55%. The old version does not
produce this large undisturbed outlet pulse on this date.

The contrast is event-specific rather than uniform peak amplification:

| Undisturbed date | 260803 peak, m3/s | 261009 peak, m3/s |
| --- | ---: | ---: |
| 1993-01-16 | 37.20665 | 18.11747 |
| 1993-01-17 | 139.82352 | 71.88370 |
| 1993-01-18 | 27.85154 | 707.63910 |
| 1993-01-19 | 1.97587 | 3.54204 |
| 1993-01-20 | 1.50862 | 2.25298 |

## Return-Period Context

Settings: all 45 years, CTA with Gringorten correction, independent rankings.
These use the same existing WEPPcloud `weibull_series` selection method as the
previous comparison. Runoff depths and selected dates are retained in the CSV.

| Interval | 260803 burned peak | 261009 burned peak | 260803 undisturbed peak | 261009 undisturbed peak |
| --- | ---: | ---: | ---: | ---: |
| 2 | 189.00145 | 168.93411 | 175.78200 | 118.84573 |
| 5 | 239.10179 | 218.13734 | 218.10080 | 170.68329 |
| 10 | 267.47964 | 243.79057 | 251.44600 | 211.63841 |
| 20 | 281.98358 | 259.95114 | 282.41470 | 249.90948 |
| 25 | 323.54831 | 293.55530 | 304.30307 | 707.63910 |

All peaks are m3/s. The newer build lowers most displayed return-period peak
estimates, but January 18 becomes its undisturbed record maximum and controls
the displayed 25-year row. Lower frequent-event peaks must not conceal this
large event-level departure. The old undisturbed record maximum is
304.30307 m3/s on February 15, 1980, not January 18, 1993.

## Investigation Consequence

The starting premise remains an outlier investigation, not a predetermined
defect finding. Evidence has now narrowed the question: this is a
**release-dependent outlier and regression candidate**, not a large peak
carried unchanged from the old model on the same inputs. It needs an
explanation before being accepted as improved physical behavior.

The new-version lower-network trace already places the pulse at WEPP element
406, with inputs from 402 and 403. The next useful comparison is the old and
new source/routing behavior at that boundary, using each release's own fresh
PASS files. Do not mix PASS formats or infer that any one patch is responsible
from this binary-pair comparison alone. No fix, timestep change, rollback or
release action is authorized by documenting these results.

## Retained Evidence

`artifacts/260803-comparison/` contains the two old-version watershed EBE
snapshots, January 16-20 comparison rows, both releases' return-period rows,
binary/log/input identities and checksums. The new-version reference remains
the previously frozen comparison snapshot. `capture_260803_comparison.py`
documents the read-only capture and input/log checks; it refuses to overwrite
an existing evidence directory. No required CI gate depends on the live runs.
