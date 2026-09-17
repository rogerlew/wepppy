# Preserve Daymet source parquet

Status: closed, 2026-09-17 UTC.

Fix the confirmed overwrite of retained Daymet source data by CLI preparation. User explicitly requested source parquet be read-only after initial acquisition and approved the fix. Scope: single-location and interpolated Daymet builders, source isolation during PRN conversion, tests and documentation. Radiation formulas, CLI conversions, quality-guard policy and job wiring remain unchanged. Complexity budget: existing functions and sidecars; no new infrastructure.

Security impact: low; no permissions or interfaces change. Two contract reviews are required by the contract-first standard. Dedicated security implementation review is not required. Production correctness review retained before closeout.

Compatibility plan: new acquisitions retain physical units under existing column names; derived radiation provenance stays in the existing CSV. Existing source files are not migrated or guessed from magnitude. Interpolated CLI preparation must leave preexisting source bytes unchanged, including legacy provenance columns. Normal explicit climate rebuild may acquire a new source; read-only means downstream preparation does not rewrite acquisition artifacts, not chmod enforcement. Validate real parquet/PRN/CLI files together and rerun affected climate suites plus broad sanity. Live accepted project is not rebuilt by this repair.

Exit criteria: accepted contract ancestor; single/interpolated source preservation tests; unchanged CLI radiation and PRN conversion; isolated real CLIGEN build evidence; test and documentation results; completed plan/tracker.

## Outcome

Implemented source preservation in both Daymet builders. Contract checkpoint aa4fbc502 precedes implementation. Three before-fix regression failures now pass; focused suite: 42 passed. Full suite: 8,983 passed, 99 skipped, 3,155 warnings in 1,405.18 seconds. Real CLIGEN replay preserves PRN, CLI and radiation CSV bytes exactly while correcting source equality. Canonical archive/restore and authenticated existing-source/CSV browse/download checks pass. No live climate rebuild or automatic historical artifact repair was performed.

Evidence: [correctness review](artifacts/20260917_correctness_review.md), [real build](artifacts/real_after.json), [radiation parity](artifacts/radiation_parity.json), [archive receipt](artifacts/archive_verification.json), and [full suite](artifacts/full_tests.log).
