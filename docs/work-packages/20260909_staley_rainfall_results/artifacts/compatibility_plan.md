# Compatibility and regression plan

Execution authorized 2026-09-09 Pacific. Changes add local rainfall/result Python
interfaces and fresh caller-owned bundles only. Existing Climate CSV/parquet,
predictor bundles, NoDb, RQ, UI and generated `wepp/runs/*` stay unchanged.
There is no migration or propagation into those artifacts. Validate source
hashes before/after composition and inspect all three newly generated tables.

Use explicit source, durations, return intervals and inverse targets. Adopt the
proposed 1/2/5/10-year support and stable snapshot-hash/original-ordinal event IDs.
No browser defaults are established. The owner explicitly approved R02:
unsupported positive ranks return unavailable/insufficient_positive_samples.
Climate's exporter is unchanged; its clamped CSV remains parity evidence.

Exercise real Wallow Climate snapshots with the matched complete predictor
bundle, controlled unavailable predictors, malformed/direct-file boundaries,
scalar parity, deterministic queries, output preservation and source mutation.
Run focused/full wctl tests and independent correctness/security reviews.
