# Validation and local backend handoff

Completed 2026-09-09 UTC. Starting revisions (both initially clean): WEPPpy
`68f4804e28560ca7da1cb9c55d57d3d3259d3f1d`; WBT
`01381f54c469564abc6776ff97d70b4966340726`. Changes remain local in both
repositories. No branch switch, live binary installation or deployment.

## Accepted decisions and compatibility

[ADR-0058, Execution disposition](../../../adrs/ADR-0058-staley-horn-slope.md#execution-disposition--2026-09-09-utc)
records raw-meter DEM and strict nine-valid-cell edges as engineering decisions
under the user's execution request. The
[canonical contract, Frozen local backend interface](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/slope_sbs.md#frozen-local-backend-interface-2026-09-09-execution)
fixes the dedicated tool, explicit class mapping, complete output schema,
resource/format bounds and fresh-directory completion marker.

Compatibility plan: additive local CLI and bindings; no project CSV/parquet/NoDb
schema, queued jobs, production callers or generated WEPP run artifacts changed.
Existing Slope/FVSlope stay unchanged. Normalized SBS values are 0–3 with 255
NoData; prepared grayscale Int16 is supported. Palettes, absent SampleFormat,
absent/nonfinite NoData and Float32-overflowing NoData are explicit rejections
because the legacy reader would reinterpret them. Preparation/resampling and
production publication remain successor work, with their own workflow gates.

## Gates and exact reproduction

Run from `/workdir/weppcloud-wbt`:

    cargo check -p whitebox-tools-app
    cargo test -p whitebox-tools-app
    cargo build --release -p whitebox-tools-app
    python -m py_compile whitebox_tools.py WBT/whitebox_tools.py tools/validate_staley_slope_sbs.py tools/validate_staley_slope_sbs_security.py tools/staley_slope_sbs_study.py
    python tools/validate_staley_slope_sbs.py --output /tmp/fresh-staley-analytical
    python tools/validate_staley_slope_sbs_security.py --binary target/release/whitebox_tools --output /tmp/fresh-staley-security
    python tools/staley_slope_sbs_study.py --output /tmp/fresh-staley-panel
    python test_fixtures/staley_m3_resolution/verify.py

Results: cargo check/build pass; 157 Rust tests pass. Existing compiler warnings
are outside this tool. The maintained analytical harness passes 60 CLI/binding
checks, including six-azimuth gradients, inclusive representable cutoff, ridges,
pits, missing neighbors/SBS, known false deductions, identical marginal fractions
with different overlap, malformed paths/units/classes/grids, output dtypes,
NoData/georeferencing, support/count/area identities and input preservation.
The 24-case security harness exercises actual malformed TIFFs, bounded resource
amplification and RLIMIT_FSIZE write failure; incomplete output has no summary.

[Analytical evidence](analytical_validation.json),
[security results](security_validation.json), and
[terrain provenance](terrain_provenance.json) pin the exact rebuilt binary,
commands and artifacts. Both actual wrappers execute analytical and Topanga
real-terrain inputs with that binary. Tool registration is exercised through
the public CLI; `--listtools` and `--toolparameters=StaleySlopeSbs` also succeed.
The terrain panel contains 48 method rows, 36 same-grid comparisons, six
conditioning contrasts, three native-basin contrasts and 432 explicit scalar
probability scenarios. All 66 source fixture files remain unchanged.

WEPPpy changes are documentation/evidence only; executable tests/helpers live
in WBT. Therefore the plan's conditional WEPPpy pytest gates are not applicable.
Scoped WEPPpy `wctl doc-lint` gates, spelling previews and both repository
`git diff --check` pass. For WBT docs, use the same underlying `markdown-doc
lint --path <file>` from the WBT root: the WEPPpy wrapper anchors its root
and rejects absolute paths outside WEPPpy. All three WBT Markdown files pass.
Spelling previews suggested only unrelated existing text; those were preserved. No installation/cross-container gate is claimed because
this package delivers a local trusted-path CLI; future production publication
must exercise real identities/mounts/orchestration before shipping that boundary.

## Reviews, discoveries and limits

[Correctness review](correctness_review.md) and
[security review](security_review.md) are independent artifacts; all medium/high
findings are closed. Correctness also independently evaluated 3,230 cells and
all probability scenarios. See [terrain report](terrain_report.md) for numeric
results and source citations. Actual generated output locations and binary hashes
are retained in the JSON artifacts, not inferred from an installed binary name.

Concrete interface friction: the legacy raster reader expands palette indices,
requires SampleFormat, silently defaults absent/malformed NoData, and normalizes
nonfinite sentinels to -32768. This tool explicitly restricts prepared inputs and
contains decoder errors. A future owned categorical read API that preserves raw
sample identity would reduce preparation burden; broad reader changes were not
required for this backend. The existing Python wrappers change cwd; reproduction
scripts restore it. Neither behavior is silently hidden as successful fallback.

The six-site panel has complete source support and synthetic SBS. Missing-data
behavior is established by dedicated analytical cases, not real partial-burn
observations. Native outlet/grid differences, GDAL float32 precision and fixed
scenario assumptions are explicit. No original 2017 calibration equivalence or
observed predictive validation is claimed. Stage 3 remains partial: K,
normalized dNBR composition, prepared input provenance/publication and production
predictor orchestration remain successor work.
