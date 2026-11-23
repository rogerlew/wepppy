# WEPP 261009: hourly surface-return peaks and channel integration

Historical release, never deployed. Superseded by
[wepp_261010](wepp_261010_release_notes.md) on 2026-10-10; its WEPPpy binary
pair and sidecars were removed at Roger's request. Evidence below retains
its original build identity and is not silently relabeled as 261010 results.

Release: 2026-10-09. Source commit
5a01758b7b998d54cccc47d7eea01847b04d866b on
wepp_260430_negmeltfix_comparator. General compatibility includes the paired
wepppyo3 reader and Roads/AgFields PASS composition. The
[released-build mutation study and Figures 1-3](../docs/work-packages/20261007-channel-discharge-closure/mutation-wepp-261009.md)
are complete. Deployment remains withheld pending Roger's review and the
separate disturbed-parameterization study.

## Why the Change Was Needed

The former peak calculation could place a day's returned soil water into a
short rainfall-excess duration. Two reproduced cases had roughly 34-40 mm of
runoff but calculated peaks near 240-275 mm/h. This peak also drives erosion
hydraulics, so changing a report alone would not correct the problem.

MIXPEAK calculates the non-return peak through the existing rainfall calculation
and adds the largest calculated hourly return rate. The two component peaks are
assumed to coincide; that timing is an approximation, not an observed hydrograph.
Both triggers fall to about 1.605 and 2.038 mm/h without changing runoff volume.
The physical peak and effective duration V/P feed existing erosion calculations.
There is no daily-average replacement of the hourly physical return estimator.
The targeted producer scope is single-OFE, non-contoured continuous-hourly runs;
other producer cases retain their existing calculation.

## Downstream Routing

PASS version 3 carries non-return volume and peak, return volume and 24 hourly
weights. The channel consumer reconstructs the non-return component separately.
It distributes return volume over a rectangle beginning at the computational
event origin, with support equal to the greater of existing storm support and
3600 times sum(weights)/max(weights). Thus the channel return rate cannot exceed
the hourly return ceiling. This scalar approximation preserves allocated volume
without claiming to recover true within-day timing or adding source carry.

The accepted channel-state repair retains the internal routed profile between
days, with linear transfer when the computational grid changes. Rainfall routing,
water balance, rrinit, soils and roughness are otherwise unchanged. The release
supersedes the earlier 261007 SURPEAK/channel-patch bundle; it does not layer those
experimental fixes back into the accepted candidate. Their source and tests
remain in history, with the superseded channel regression copied under the work
package's historical directory. Existing v3 regression gates remain active.

## Cedar Comparison

Complete 1980-2003 Cedar record against wepp_260803 at 10 cm, not field validation:

| Measure | Change |
| --- | --- |
| Totalwatsed streamflow | +0.393 m3 over the record |
| Daily channel water ledger | -0.17 m3 |
| Sampled outlet discharge volume | +0.05089% |
| Sum of absolute daily integral/ledger gaps | -9.19% |
| October peak | 50.5 to 46.4 m3/s |
| October centroid | 20.35 minutes later |
| October 28 recession volume | +0.566% |
| Hillslope sediment delivery | -7.12% |
| Gross channel erosion | -0.97% |
| Outlet sediment export | +0.73% |

The two previously introduced late pulses disappear without comparable earlier
replacement pulses. Some sediment windows increase by about one tonne and the
low-load year 2001 increases 76%; Roger accepted that tradeoff on 2026-10-09.
Neither aggregate agreement nor that judgment proves event-level sediment
accuracy. The independent 45-year watershed completes; sediment export changes
about +3.34% against baseline. Legacy accounting discrepancies remain documented.

See the [full results and figures](../docs/work-packages/20261007-channel-discharge-closure/return-support-results.md).
Historical daily-v2 mutation figures do not validate this release.

## Compatibility and Operations

Use the paired wepp_261009 and wepp_261009_hill binaries and regenerate all
hillslope passes. Do not combine passes across releases. Matching wepppyo3 source
c3d8481d1c7dcaf59dceb37d9ea2e860b89f4307 reads legacy and v3 outputs, rejects
experimental v1/v2, and preserves components through additive and area-weighted
composition. Existing public Parquet columns are unchanged. The WEPPpy startup
preflight pins the matching native extension. Roads climate-token normalization
and AgFields metadata reads preserve the leading version marker.

Combined source weights are normalized to represented return volume before
addition. Non-return peaks use the existing peak-combination procedure. This is
an explicit aggregate approximation, not exact superposition of independently
routed sources. Existing sediment and total-water combination rules are retained.

No runtime flags, calibration changes, release-banner change or capacity changes.
Historical executables and default selections are retained. No production
deployment is part of this release.

## Artifact Identity

| Artifact | SHA-256 |
| --- | --- |
| wepp_261009 | e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc |
| wepp_261009_hill | 37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228 |
| Matching interchange extension | 06319303a2337cc75a3c57eb594161565d8a2af1d58cee18c17abcfe6eea8cf8 |

Gate results and execution receipts are recorded in the
[release validation record](wepp_261009_validation.md). Build command: TARGET_TAG=261009
COMPILER=/usr/bin/gfortran tools/build_wepp_dated_release.sh, followed by
make prepare_watershed_includes in src. Both system ELF loaders were verified.
