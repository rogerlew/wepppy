# Local rainfall adapters and M1 results

Status: proposed contract, 2026-09-10 UTC; implementation pending. The
[work package](../../../../../docs/work-packages/20260909_staley_rainfall_results/package.md)
scopes local roadmap stage 4. Proposed policies are not approved production
UI, Climate-owner or persisted run schema changes.

## Inputs and ownership

Consume the accepted version-1 M1 predictor bundle and explicit Climate-owned
parquet/CSV snapshots with hashes and climate-mode/date provenance. The
[M1 contract](m1_predictors.md) and [scalar engine](staley2017_engine.md) remain
authoritative. Validate persisted bundles at the new read boundary; the existing
scenario helper accepts an in-memory dict and does not establish that boundary.
Do not follow arbitrary source paths embedded in manifests or rebuild inputs.

The CLI event artifact is `climate/wepp_cli.parquet`; peak_intensity_15/30/60
are mm/hour. Preserve actual climate mode, original year/month/day and source
row identity. Synthetic climate years are simulation labels, not observed dates.
Wet-event eligibility and per-duration validity must be finalized before code;
source dates alone must not be assumed unique. NOAA CSV is a frequency source
only and must never relabel the CLI event catalog.

## Proposed three result families

Event results evaluate each available 15/30/60-minute intensity with matching
coefficients and `rainfall_mm = intensity_mm_per_hour * duration_minutes / 60`.
Preserve event identity and valid other durations when one duration is missing.
Null/invalid rainfall is not zero rainfall. Fix the explicit valid-zero policy
separately from zero frequency placeholders. No intensity reconstruction,
storm-duration substitution, cross-duration average or joint probability.

Design results use explicit CLI-derived or NOAA source and the proposed
1/2/5/10-year × 15/30/60-minute matrix. Requested unsupported combinations remain
unavailable with reasons; never switch sources or treat placeholder zeros as
valid design rainfall. CLI full precision comes from event parquet and the
existing Climate rank method; CSV rounding is not the scientific input.
Before implementation, resolve insufficient duration samples, rank fallback and
full-recurrence-set parity against the Climate exporter. Do not silently alter
the Climate-owned estimator or extrapolate beyond its supported record length.

Inverse results use caller-specified target probabilities and all requested
supported durations. Preserve scalar available/unavailable/nonunique statuses.
They depend on predictors and coefficients, not CLI/NOAA frequency source.
Mapping inverse thresholds to return periods is separate and outside this
increment. No default target is required by the backend.

## Scientific identity and unavailable results

All scenarios refer to the selected fixed postfire predictor snapshot, not
recovery over simulated decades. Preserve independent predictor coverage,
T bounds/null, source-kind and assessment imagery identity. Missing point
predictors mean no single M1 probability; do not propagate probability bounds
or substitute another model. Preserve accepted area warning outside inclusive
0.2–8 km² on generated results and local queries. Do not call PDS average
recurrence intervals annual debris-flow probabilities.

Report canonical units, source and frequency method, represented record length,
wet-event years and positive sample counts by duration. Do not add an arbitrary
sample adequacy cutoff. Image/basin/climate identities remain separately visible.
A snapshot hash proves identity, not live controller freshness.

## Proposed artifacts and local queries

Create a fresh caller-owned bundle with final manifest and independently
identifiable event, design and inverse tables. Freeze filenames, schema version,
columns, null/reason vocabulary, sort order and event ID strategy before code.
Use existing parquet/tabular dependencies and bounded batches. Proposed local
queries list/filter/sort events with pagination and retrieve all durations for
one event; no HTTP endpoint, arbitrary SQL interface or new dashboard yet.
Measure representative catalog memory, build time and event-detail latency
before choosing materialization versus evaluation on demand.

Loading requires trusted regular local files, resource limits, explicit schemas
and expected hashes. Preserve source immutability, safe fresh-output behavior,
failed/incomplete artifacts and final completion marker semantics. No reading
untrusted URLs or enabling external database readers through query input.
Malformed files fail explicitly; scientific missing scenarios retain rows under
the accepted policy. Distinguish empty valid catalogs from malformed input.

Canonical output values are unitized only for later presentation; SI/English
switches must not recompute probabilities. No local source update triggers a
rebuild or changes active project results. Live publication and invalidation
are stage 5 contracts.

## Gates

Ratify the [decision register](../../../../../docs/work-packages/20260909_staley_rainfall_results/artifacts/decision_register.md)
and record new parameterization in an ADR before dependent code. Reuse existing
Climate/NOAA parsers where their actual contracts fit; do not add an unapproved
fallback parser or dependency. Validation includes genuine climate snapshots,
complete/partial predictor bundles, numerical parity, malformed/empty/short
records, stable identity, hash changes, failure preservation and bounded queries.
M3 local predictor integration and all production UI/RQ work remain separate.
