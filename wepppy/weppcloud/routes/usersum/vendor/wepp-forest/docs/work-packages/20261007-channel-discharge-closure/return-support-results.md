# Return-support v3 feasibility result

## 2026-10-09 decision: sediment trade-off accepted

Roger accepts the v3 sediment trade-off for this bounded feasibility test:
Cedar gross channel erosion changes -0.97% and outlet sediment export +0.73%.
He considers event departures above 1,000 kg potentially reasonable given the
channel routing changes and adjacent storms. This is an explicit scientific
judgment, not a new universal 1% acceptance threshold or proof of the mechanism.

The pending sediment-review hold is resolved. Retain the v3 candidate without
further sediment tuning. The measured event departures, +76% low-load 2001
result, independent-watershed differences and interface limitations remain
documented; no evidence is removed or reclassified as physically proven.
Earlier pending-review statements below are historical and superseded by this
decision. This does not authorize release, vendoring, deployment or new coding.

2026-10-08. One fixed-rule experiment authorized by Roger under the
[v3 contract](return-support-contract.md). No tuning, daily-mean physical
estimator, water-balance repair, release, vendoring or deployment.

## Decision

**Hydrologic feasibility is supported. Retain this candidate for scientific
review, not automatic acceptance.** It preserves the hourly physical peak
correction, removes both problematic late pulses without replacing them with
comparable earlier peaks, and substantially improves the October recession.
Water volumes remain close to wepp_260803 at 10 cm over the full record.

The remaining consequential uncertainty is event sediment delivery. Full-record
outlet export is only +0.73%, but some event windows gain approximately one tonne
and low-load year 2001 increases 76%. Those changes persist in wider windows;
they are not hidden by the favorable total. Whether that is an acceptable
accuracy cost requires Roger's judgment. No further patch or parameter adjustment
was made to reduce those differences.

## Implemented rule and identity

The physical producer remains exactly the hourly MIXPEAK implementation:
independently calculated rainfall Pr plus hourly return maximum Ps, followed by
the existing physical floor/cap and erosion V/P calculations. `mixpeak.for` is
byte-identical to the hourly state-repair parent, SHA-256
`a2122a517191cbd0159398fd3ed973fded794a8e282afa22a4894e410917827c`.

The only behavioral change from that parent is the return-source construction:

```text
Teq = 3600 * sum(hourly weights) / max(hourly weights)
Ts = max(existing storm support, Teq)
Return rate = caller-allocated return volume / Ts
Return source = rectangle on [0,Ts], using interval overlap
```

Rainfall reconstruction and its support remain unchanged. Ts is local to return
assembly, including pure-return cases; it is not written into storm duration,
erosion duration or tcs. Invalid or out-of-day support fails rather than being
clipped. Initial/subsequent-day boundary conventions and the isolated channel
state-repair implementation are retained. No new model parameter or runtime flag.

The delivered return rate may be below the hourly maximum. This is the explicitly
authorized source approximation, not a claim that the hourly peak was replaced
or that the computational event origin is observed return timing.

PASS uses `WEPP_PASS_COMPONENTS 3`, `SRC3`, and `SOURCES3`, with the same Vr, Qr,
Vs and 24-weight payload as v1. The version distinguishes the changed source
contract. V1/v2/unknown component versions fail explicitly; legacy reader tests
remain supported. An isolated matching Rust reader consumes v3 without changing
ordinary Parquet schemas. Installed extensions are unchanged.

Worktree: `/home/workdir/wepp-forest-return-support-20261008`, branch
`candidate/return-support-20261008`, based on f24c957e3 plus the archived hourly
and state-repair changes. Relative to the immediate state-repair parent, source
changes are limited to `chrqin.for`, `mixpass.for` and `wshpas.for`. Source and
binaries remain uncommitted and unpromoted.

| Artifact | SHA-256 |
| --- | --- |
| Watershed binary | `adcdbd4689e17e2e521b3b45f63f34f8204f4f2bd7168ba1d40acd8e026cb814` |
| Hillslope binary | `dc27010f36580b22b4116699a49040379009fc129a6f4eb126c03b77aa359235` |
| Isolated v3 reader | `498a171c4f4128211e571e57a82ecbb5aa35fa1930968c5ddc5fa20168c023d6` |

## Physical and interface verification

Fresh Ksat-35 runs retain the correction of both original triggers:
240.274/274.596 -> 1.605/2.038 mm/h, with 33.690/40.075 mm runoff unchanged.
All nine trigger/control summaries exactly match the hourly parent. Corresponding
physical output files match byte-for-byte; candidate PASS changes are limited
to version labels. Observer repeats preserve outputs. The Ksat-1 no-return case
retains its baseline runoff, peak and sediment results.

All 864 fresh Cedar hillslopes and 140 independent hillslopes complete. Their
5,184 and 840 non-PASS outputs are byte-identical to the hourly parent. All 1,004
PASS files preserve their numeric records exactly after mapping only version
labels for comparison. Actual simulations use the new files unchanged, with the
matching new executable; no cross-build PASS substitution occurred.

Validation completed:

- 67 focused native tests: mixed/pure return, vanishing components, the 43.484 mm
  rainfall control with 0.01 mm late return, caller scaling, partial endpoints,
  first-day/q0 behavior, invalid support and parser/version rejection.
- 154 full pytest tests, with two existing tarfile warnings. The historical
  dual-binary guard test remains historical coverage, not a substitute for the
  fresh candidate watershed runs.
- 101 Rust unit tests and 17 integration tests; formatting check passes.
- Both maintained host smokes, 12/12 permanent watchlist cases, correct system
  ELF loaders, and zero new candidate parse/runtime failures.
- Fresh conversion accepts 7,573,824 PASS and 16,690,464 WAT records without
  rejection. The independent master reader accepts 2,301,320 records.

The state-carry regression tests still inject a prescribed last-hour source so
the old restart failure remains active; they were not weakened by moving the
new return source earlier. Separate native source tests exercise the v3 rule.

## Cedar water comparison

Complete 1980-2003 warming-championship/Cedar Creek record: 8,766 days, 864 hills,
371 channels, unchanged inputs and 10 cm rrinit. This is engineering comparison
against a model baseline, not validation against observations.

| Full-record measure | wepp_260803 | V3 | Difference |
| --- | ---: | ---: | ---: |
| Totalwatsed hill streamflow, m3 | 1,267,735,665.289 | 1,267,735,665.682 | +0.393 m3 |
| Daily channel ledger, m3 | 1,272,337,716.46 | 1,272,337,716.29 | -0.17 m3 |
| Sampled routed integral, m3 | 1,266,448,890.30 | 1,267,093,408.92 | +0.05089% |
| Integral minus ledger, m3 | -5,888,826.16 | -5,244,307.37 | Smaller signed gap |
| Sum of absolute daily gaps, m3 | 6,441,305.44 | 5,849,097.91 | -9.19% |

The sampled-integral increase chiefly changes the existing accounting discrepancy;
it is not additional hillslope water production. Annual sampled-volume changes
range +0.01567% to +0.09485%. Daily/subdaily NSE is 0.999989/0.999339, descriptive
only. Across 322 baseline-selected seven-day windows, volume differences range
-0.0523% to +0.7828%; maximum centroid shift is about 20.3 minutes. These windows
are a consistent screen, not universal certification of isolated storm boundaries.

### Target late pulses and preceding events

| Time | Baseline m3/s | Hourly state parent m3/s | V3 m3/s |
| --- | ---: | ---: | ---: |
| 1990-10-22 01:10 | 0.530 | 1.260 | 0.530 |
| 1998-09-19 01:10 | 0.351 | 2.000 | 0.351 |

The full preceding-event windows were inspected, not just these two timestamps:

| Window | Volume change | Peak, baseline -> v3 m3/s | Peak-time change | Centroid change |
| --- | ---: | --- | --- | --- |
| 1990-10-18 to 24 | +0.404% | 1.42 -> 1.45 | None | -2.56 min |
| 1998-09-15 to 21 | +0.783% | 2.45 -> 2.50 | None | -1.05 min |
| 1991-10-22 to 28 | 0% | Unchanged | Unchanged | Unchanged |

The two large new secondary pulses are removed rather than simply moved to a
similarly large earlier crest. Primary peaks increase about 2% in these controls,
which remains a disclosed difference, not exact legacy parity.

### October event and recession

October 25-30 sampled volume changes +0.455% (+11,512.38 m3); peak changes
50.5 -> 46.4 m3/s with unchanged first-peak time. The centroid is 20.35 minutes
later, versus about 117 minutes under the literal-hourly parent.

October 28 volume changes +217.2 m3 (+0.566%), versus +72.3% under the hourly
parent. Its daily integral-ledger gap improves from -7,260.18 to -7,174.94 m3.
The full window's signed gap improves from -22,441.69 to -10,929.95 m3; the sum
of absolute daily gaps also decreases to 10,929.95 m3. The last differing printed
water sample is October 29 at 11:50, before the next storm. This does not prove
that every sediment consequence ends with the water difference.

![Cedar three-way comparison](../../ablation/20261007_channel_discharge_closure/artifacts/repro/return-support-v3/warming/three-way/windows.png)

### Remaining flow departures

The recession-turn screen finds 365 local maxima above a baseline nonrising on
one-hour flanks, versus 888 for the hourly state parent. Median added flow is
0.01 m3/s and the 90th percentile 0.10 m3/s. The largest added value is +0.54
m3/s on a baseline 3.03 m3/s recession, but its local prominence is only 0.01
m3/s: a raised recession with a small printed turn, not the earlier sharp pulse.
These counts include output-resolution effects and are not new-storm counts.

On 2,909 all-OFE dry-weather days, net sampled-volume change is +22.56 m3. The
single screened dry-day turn is 0.0001 m3/s above baseline. Large first-argmax
shifts were checked: the -24-hour case exchanges nearly equal 3.93 m3/s crests,
with centroid shift under a minute; February 1996 shifts the first maximum on a
24.4 m3/s plateau with a 12-second centroid difference. February 1982's +3h50m
maximum-time change accompanies peak 19.2 -> 18.7 m3/s and centroid +2.37 minutes.
These are not translations of whole floods by those argmax intervals.

## Sediment: small total difference, consequential individual cases

| Full-record measure | Baseline tonnes | V3 tonnes | Change |
| --- | ---: | ---: | ---: |
| Hillslope PASS sediment delivery | 62.3363 | 57.8978 | -7.12% |
| Reported gross channel erosion | 442.1907 | 437.9167 | -0.97% |
| Outlet sediment export | 202.6525 | 204.1309 | +0.73% |

Hillslope sediment is unchanged from the hourly parent; it was not reduced by
substituting a daily-mean erosion peak. October event outlet delivery changes
5,101.43 -> 5,030.05 kg (-1.40%). Daily EBE sums agree with rounded annual outlet
reports within their reporting precision, and EBE water agrees exactly with the
daily channel ledger.

However, 273 days increase and 195 decrease in outlet sediment. Gross positive
changes total 4,941.93 kg and negative changes -3,463.53 kg. Examples:

| Day | Baseline kg | V3 kg | Change kg |
| --- | ---: | ---: | ---: |
| 1997-01-30 | 24.77 | 1,132.36 | +1,107.59 |
| 2001-12-16 | 239.42 | 1,288.17 | +1,048.75 |
| 1996-12-30 | 226.44 | 1,094.81 | +868.37 |
| 1987-12-02 | 367.03 | 1,099.55 | +732.52 |
| 1983-02-17 | 5,496.82 | 5,033.69 | -463.13 |

The largest increases do not disappear when the comparison is extended to
15-day windows: January 1997 remains +1,105.08 kg and December 2001 +1,034.51 kg.
Those wider windows include adjacent events and are not certified isolated
storms, but they rule out an explanation confined to a simple one-day shift.
Annual 2001 delivery changes 1,356.49 -> 2,387.89 kg (+76.0%); 1987 increases
21.0%. Thus the +0.73% total must not be used to imply negligible sediment effects.

These changes arise despite small water differences, and some have unchanged
same-day hill sediment input. Existing channel sediment calculations and their
accounting inconsistencies preclude declaring this improved deposition or
erosion physics. No causal sediment ablation was conducted or new sediment
repair added. For storm-load applications, this is a substantive review item.

## Independent watershed

The unchanged 140-hill, 61-channel, 45-year case completes with all 16,437 daily
records present. Reported water volume is 92,405,525.26 m3 versus baseline
92,405,597.10 m3. Sediment export is 56,679,751.34 kg versus 54,849,478.10 kg,
about +3.34%; its maximum reported daily peak is 129.94968 versus 146.08635 m3/s.
Relative to the hourly state parent, sediment increases about 0.29% and water
volume changes -0.01 m3. This is independent execution/daily-output evidence,
not a new subdaily field-validation claim.

## Recommendation and limits

Retain this minimal, fixed candidate for Roger's review. The targeted source
peak correction remains physical, both late-pulse controls improve, complete
record water behavior is close to baseline, and the October recession/accounting
tradeoff is much smaller. No time-origin tuning, support multiplier, rainfall
threshold, new carry state or further physical patch was used to obtain that.

**Acceptance remains pending the event-sediment judgment.** The increases are
rare and much smaller than the prior candidate's largest changes, but are real
and important relative to the affected events/years. Baseline is not physical
truth, and neither sign alone settles accuracy. Bring that tradeoff to Roger
instead of reopening channel conservation or sediment reconstruction.

The approximation does not recover observed return timing. Scope remains
single-OFE, non-contoured continuous-hourly producer cases; broader peak methods
and modes are not universally validated here. PASS-combination workflows still
lack approved component composition, so this is not a general production-ready
release. Old daily-v2 mutation figures do not describe this candidate. Installed
reader SHA remains `c6b746bb77be39d38321a365df1762fd8d88ce0522f3a51215d5bb8bfdddf248`.

## Reproduction and evidence

Raw roots: `/wc1/holdouts/channel-discharge-return-support-20261008` and its
`-warming`, `-independent` and `-triggers` companions. The isolated reader source
and build are under the first root's `reader` directory. Large raw fixtures and
Parquet data remain outside git.

[Archived evidence](../../ablation/20261007_channel_discharge_closure/artifacts/repro/return-support-v3)
contains source/test/reader snapshots, build and input identities, receipts,
complete annual/daily/event tables, sediment comparisons and plots. Start with
`warming/three-way/summary.json`, `warming/deep-comparison/summary.json`, and
`warming/tradeoff/review.json` for the largest residual tradeoffs.

Executed build/test commands included:

```bash
make clean
make -j4 FC=/usr/bin/gfortran wepp
make -j4 FC=/usr/bin/gfortran wepp_hill
make prepare_watershed_includes
python -m pytest -q
PYO3_PYTHON=/home/workdir/wepppy/.venv/bin/python RUSTFLAGS='-C link-arg=-lpython3.12' cargo test --offline
PYO3_PYTHON=/home/workdir/wepppy/.venv/bin/python RUSTFLAGS='-C link-arg=-lpython3.12' cargo build --release --offline -j4
cargo fmt --check
```

The Python tests used `/home/workdir/wepppy/.venv/bin/python`. The package runner
`run_midnight_watershed.py` was invoked with the new `--source`, the hourly
state-repair `--parent`, and `--pass-version 3` for both watershed roots.
`run_component_triggers.py` regenerated the original controls. Fresh conversion,
full-record analysis and review used `convert_component_yield.py`,
`assess_return_support_watershed.py`, `finish_return_support.py`,
`deep_return_support.py` and `review_return_support.py`. Exact paths and binary
hashes are in the run receipts; no production executable was replaced.
