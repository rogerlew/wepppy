# Channel working-flux initialization checkpoint

The bounded repair clears `runoff(iplane)` and `chnrun(iplane)` immediately after
WSHCQI, before optional WSHIRS. Completed upstream element outputs can occupy
the next channel's soil-plane slots. Actual receiving-channel producers then
populate the cleared fields. Incoming transfers, soil stores, event decisions
and Muskingum–Cunge state and recurrence remain unchanged.

Native local source commit: `d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`.

## Evidence

The independent [scientific review](channel-plane-initialization-scientific-review.md)
and [control summary](channel-plane-initialization-control-summary.json) retain
four causal lanes: no reset, each reset alone, and both. All 96 two-year runs
complete, and 1,800 observer-on/off scientific file pairs match exactly.
The hourly dry witness recovers 1.54834 m³ of infiltration allocation denied by
inherited runoff. Wet controls remove 26.91–26.99 m³ of false local rainfall
runoff while preserving genuine local production. These incorrect local-input
and transmission terms can cancel in net routing; do not describe their entire
magnitude as water transported twice.

The [validation receipt](channel-plane-initialization-validation.json) pins
source, binaries, build logs, test logs and retained external evidence hashes.
Both profiles were built sequentially with `/usr/bin/gfortran` using
`make -B wepp FC=/usr/bin/gfortran LINKER=/usr/bin/gfortran` and the corresponding
`wepp_hill` target in an isolated src/fpm-src copy. Both use the system ELF loader.
Inherited binary sidecar metadata is not provenance for these experimental builds.

The explicit candidate passed the full native suite: **520 tests**, two existing
tarfile warnings, 618.33 seconds. The 100-year fixture reached year100/day365/
channel31 within its unchanged 900-second limit. All 29 paired replay validations
pass, including the 400-year / 146,097-day case. All 12 hillslope watchlist cases
and both profile host smokes pass. Seven new portable causal tests pass separately in 115.93 seconds; they were
added after the full-suite collection. All 527 final collected tests are covered.
The [QA review](channel-plane-initialization-qa-review.md) records exact-source
review and reproducible two-year native regressions.

## Acceptance boundary

This checkpoint fixes working-flux ownership only. Signed routing withdrawal
and soil credit remain unresolved. After the repair, the hourly dry control
still clips 11.423601 m³ between raw and accepted outlet discharge; the daily
control clips 38.351856 m³. No physical-volume authority, clipping limiter,
soil-credit adjustment or residual-derived store is introduced. The work package
remains active and is not release-ready. No release, vendoring or deployment.
