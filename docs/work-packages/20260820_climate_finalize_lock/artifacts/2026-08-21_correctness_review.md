# Correctness and User-Experience Review - Climate Multiple-Build Finalize Lock

## Metadata

- **Package**: `docs/work-packages/20260820_climate_finalize_lock/`
- **Reviewer**: Codex independent validation pass
- **Date**: 2026-08-21
- **Scope reviewed**: GridMET and Daymet multiple-interpolated build/finalize paths
- **Commit/branch context**: `codex/rehydrate-lfs-runtime` working tree
- **Canonical contract**: `docs/schemas/nodb-persistence-concurrency-contract.md`
- **Related QA/security artifacts**: `artifacts/2026-08-21_security_review.md`

## User Outcome

- **User goal**: Complete a multiple-interpolated climate build without losing
  work or overwriting newer climate settings.
- **Success presented to the user as**: RQ completion with current derived
  Climate state persisted.
- **Failures that may reach the user**: Explicit superseded/conflict result when
  relevant climate inputs changed; underlying collection failures.
- **Partial-state behavior**: Preserve existing artifact behavior; never report
  successful final persistence when the finalizer did not commit.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Climate file absent | no for build | explicit existing initialization failure | Existing Climate initialization/build contract; no new absent-file fallback added |
| Climate present, derived outputs empty | yes | collect and finalize | Focused service/facade tests; `ClimateMultipleBuildResult` carries all derived fields |
| Climate populated | yes | replace only derived output fields | `finalize_multiple_build()` allowlist at `wepppy/nodb/core/climate_multiple_build.py:148-156`; focused tests |
| Supported legacy payload | yes | preserve unrelated fields | `_parse_observed_year()` accepts persisted integer-like year strings; focused climate helper suite remains green |
| Malformed payload | no | bounded explicit decode/validation failure | Real NoDb test for malformed observed year proves `ClimateMultipleBuildSupersededError` and old derived state remains |
| Unrelated concurrent rewrite | yes | preserve rewrite and finalize | Real temporary Climate NoDb same-size atomic rewrite regression passes |
| Relevant concurrent rewrite | yes | supersede without mutation | Real station-input same-size rewrite regression passes and preserves prior derived fields |

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Concurrent finalization | None after implementation review | Shared fresh-state finalizer plus real temporary NoDb interleaving tests | None | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: proceed to final QA gate; deployment remains separately authorized
- **Reviewer sign-off**: Codex, 2026-08-21
