# WEPP 261021 revision-2 validation

## Identity and release boundary

The owner authorized reissuing the undeployed same-name binary pair. Build:
`TARGET_TAG=261021 COMPILER=/usr/bin/gfortran tools/build_wepp_dated_release.sh`,
source `d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`, canonical branch
`wepp_260430_negmeltfix_comparator`. Compiler GNU Fortran 13.3.0; the two
capacity profiles were built sequentially and original watershed includes
restored afterward. No source formula changed during release packaging.

| Profile | SHA256 |
| --- | --- |
| Watershed | `e2c83b1a691fad3ffe29acf1588dadbecfeec9b027391df8b7fddcf4908d2971` |
| Hillslope | `81591bf0301604aa25002d641e3c8e5d22e15c747b179f1613e7c329233f4965` |

Both sidecars declare artifact revision 2, exact source/branch, unchanged
ASCII PASS v3/MOFE/single-input interfaces, Gregorian validation, existing
paired interchange and the superseded binary identity. HBP remains disabled.
Regenerate the complete contributing hillslope/PASS/watershed/interchange chain.
No selected default changes or production deployment were performed.

## Fresh native gates

- Full `pytest -q` with `WEPP_GUARDED_BINARY` pointing to this release:
  **527 passed**, two existing tarfile deprecation warnings, **718.13 seconds**.
- The required 100-year watershed fixture passes within its unchanged 900-second
  timeout; it reaches year 100/day 365/channel 31. No test timeout was raised.
- Both profile host smokes pass; hillslope watchlist **12/12** passes.
- Ablation artifact policy and system ELF/runtime provenance pass.
- All mandatory resources are committed inputs or reproducibly generated data.
  Private watershed/Cedar inputs are supplementary, not required release gates.

An independent ELF64 reader verified all 26 allocated sections (including BSS
layout) against the previously validated d354 candidate, excluding GNU build ID.
Contents, addresses, offsets, sizes, flags and alignments match. Independently
stripping debug sections/build ID also produces identical complete files. The
retained 29 paired replays, 146097-day 400-year run, 96 causal channel-plane runs,
1800 observer-neutral file pairs and24-year Cedar study therefore apply to the
same executable code. This evidence does not replace the fresh 527-test gate.

## Post-vendor validation

Both installed profiles pass host and running-container smoke tests and ELF
provenance checks. Runner/output/binary-policy selection passes **21 tests**
with two existing deprecation warnings.

Broad WEPPpy validation covers all 11173 collected nodes, with **11052 unique
passes and 122 skips** including one collection skip. This is segmented coverage:
the original full command was intentionally interrupted during the 230-case soil
block; all four soil shards pass, and completed-module/per-node ledgers prevent
gaps or double counting. The combined remainder stopped at the previously
observed feature-access Redis authentication failure (HTTP 503 instead of 403).
That module passes 52/52 in isolation. The final 258 tests pass with the existing
browser cache selected for that process. No application auth/configuration or
test timeout changed. The combined-run failure remains an isolation limitation,
not a clean uninterrupted full-suite pass. Detailed receipts are retained in
the WEPPpy reissue package.

## Technical report and scientific limits

The [technical report](../docs/release-notes/wepp_261021/README.md) has 21 mapped
change dispositions and nine original figures. A separate numerical/scientific
review verifies implementation, all Cedar annual integrals/maxima and all 6048
plotted samples against raw outputs; independent primary-reference checks,
source disclosure and PDF layout checks are retained with the report.

MC dynamics and numerical storage authority are preserved. Signed soil/routing
withdrawal acceptance and raw negative-rate clipping remain open. Reported
outlet volume consistency is not universal physical closure. Cedar comparison
is not observational calibration or routing-only attribution; adverse small
flow changes and unvalidated sediment/nutrient consequences are disclosed.
Roger Lew approved the completed 24-page/nine-figure report for publication on
2026-10-21. The PDF/public manifest are vendored in WEPPpy; local Caddy download
and existing Usersum navigation checks pass with exact approved PDF hash
`b4e894d013e4858e410ff8e2d265095ebebcde04fe68e3c25a665e3a9027f82c`.
Earlier 261010 report revisions remain unchanged.

## Superseded original edition

Source `a87925df9ffe6ebb928e126395dd159d484285fa`, calendar-only 261021:

| Profile | Superseded SHA256 |
| --- | --- |
| Watershed | `fe7a8d7b93deb2329536b9cc937b9f51a5c747b19fd3b95584347639046fa385` |
| Hillslope | `6e4ec397551175ffd71337eeea04f5b3150a544f247382c863956fb50d7e59d1` |

Its 232-test validation, original binaries, sidecars and notes remain in Git
history and a hashed local reissue archive. The closed initial WEPPpy release
package remains unchanged. Rollback requires restoring the whole paired
binary/sidecar identity and regenerating outputs, never mixing generations.

Internal evidence root: `/workdir/wepp-261021-rerelease-20261021`;
compact receipts and final gate logs are retained in the WEPPpy reissue package.
