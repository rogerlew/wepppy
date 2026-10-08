# PRISM-localized stochastic dewpoint study

Status: Closed 2026-10-08 (standalone research).

All 180 cases and 2,344,980 daily output rows passed validation. Forest precipitation rose from 22–37% to 90–102% of prior GridMET forcing. Clipping improved seasonal RMSE in 36/36 comparisons, but annual ET bias in only 6/36. See [results and figures](artifacts/results.md). Production and UI remain unchanged.

## Registered design and rationale

Use current PRISM 1991–2020 monthly 800 m normals at the nearest native cell to each of the same nine frozen hillslopes. Localize the three retained station parameter files with the existing `par_mod` precipitation, wet-day probability, and temperature algorithm. Keep its other parameters, including station dewpoint, unchanged; this isolates the established localization method rather than introducing a new humidity model. Compare native stochastic dewpoint against `max(Td, Tmin)` throughout spinup and assessment. Use seeds 1001–1010 and original 25–45-year histories, with 2016–2022 synthetic labels for assessment. Compare seasonal climatologies and distributions with the cached OpenET series, never individual observed and synthetic years. Check generated precipitation against both PRISM targets and the prior GridMET histories. Retain every seed and all CLIGEN quality diagnostics.

## Compatibility and evidence

Additive standalone research only. Reuse the frozen soils, vegetation, slopes, control files, and pinned model binaries from the two closed studies. Security impact: low; no dedicated security review required. Complexity budget: standalone scripts and existing executables, with no new infrastructure. No production behavior, defaults, schemas, or UI changes; no new dependencies or authenticated requests. Closed evidence and source projects remain immutable. Retain raw PRISM replies, cell identities, parameter files, exact input/output hashes, executable completion records, tables, and plots. Large model outputs live in `/home/workdir/wepppy-scratch/prism-stochastic-dewpoint-20261008`.

See [ExecPlan](prompts/completed/study_execplan.md) and [tracker](tracker.md).
