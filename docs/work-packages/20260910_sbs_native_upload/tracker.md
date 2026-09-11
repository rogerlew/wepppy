# Tracker

## Progress

Contract checkpoint prepared; review pending. Starting revision f59d18942.
Existing uncommitted work includes Builder setup, capability timeout correction,
and an experimental source/display NoData union for the existing native exporter.
No native-required/UI changes precede this checkpoint. Preserve unrelated work.

## Decisions

2026-09-10 UTC: operator requires Python fallback removal and HTML gateway errors
in Details, not hints. Keep Summary for results. No full suite.

## Evidence

Prior Wallow profile: init 0.05 s, WGS 0.56 s, RGB 0.98 s, Python four-class
55.55 s; native union-mask experiment 0.35 s. Pixel parity and final transport
verification pending. Builder package remains separately tracked.

Checkpoint ancestor: 328db92dd. Independent contracts passed before native-only
and UI edits. Removed native catch-and-fallback wrappers and duplicate raster
summary/reclassification/export loops. Added SBS-only inert Details rendering;
JSON diagnostics retain escaped text and Summary targets are excluded.

## Final implementation and evidence

Removed five catch/fallback boundaries and 339 lines of duplicate raster code.
Required corrected companion native artifact; source/configured masks stay
separate from WGS display masks. Fixed native metadata truncation. Final Wallow
export parity passed in 0.57 s versus 54.09 s for the frozen Python baseline.

78 focused Python, 4 Rust, 852 JavaScript and 2 template tests passed; stubtest,
test-stub completeness, ESLint, broad-exception gate and bundle build passed.
Authenticated proxy upload, filename/table/map, HTML504 Details, prior Summary,
retry and reload passed (`artifacts/validation.md`). No full Python suite.
First-upload filename target is now present even without an accepted map, and
filenames are assigned with textContent. Independent reviews closed code findings.

Repeated proxy attempts also exposed a stale inherited lifecycle context. The
captured stack showed a new request checking a previous request's released lease.
Fixed explicit HTTP request isolation; current nested lease/lost-owner behavior
is preserved. Ten admission tests passed; the final proxy gate passed failure/recovery/reload
and three additional consecutive uploads. Both independent reviews cover this
admission correction.

## Outcome

Completed; plan archived in prompts/completed/. Independent correctness and
security gates passed, including real Redis/file-lock and browser probes.
Runtime changes remain uncommitted in WEPPpy and wepppyo3; no push or fleet deployment.
