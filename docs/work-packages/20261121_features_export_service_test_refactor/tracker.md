# Feature export service test refactor tracker

**Started** 2026-11-22 05:23 UTC
**Phase** Closed locally
**Last updated** 2026-11-22 05:26 UTC
**Security impact** None. Dedicated security review is unnecessary for the test-only change.

## Progress

- [x] Record the starting modules, test results and quality measurements.
- [x] Move test groups and keep the local helpers with their callers.
- [x] Check case and assertion parity, run the focused selection and lint documentation.

## Decision log

Keep execution, cache and publication together so their helper functions stay local. Name each extracted module with the shared `test_features_export_service_` prefix so the complete service selection is easy to run from a shell.

## Verification

The [validation record](artifacts/validation.md) contains the focused results, case and definition parity, and measurements. The task worktree is ready for review.
