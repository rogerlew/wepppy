# Correctness and user-experience review

Reviewer: `/root/defaults_correctness`; independent read-only, 2026-09-19 UTC.
Base `1b4f9af72`; accepted contract ancestor `acc192323`; implementation
`b1e857765`. Authority: MOFE artifact contract, Configured cover defaults;
WEPP run-input contract, kslast omission; NoDb persistence contract unchanged.
Scope: two NoDb methods, associated regressions and retained acceptance evidence.
Security: low, no changed auth/access/filesystem boundary; dedicated artifact N/A.

## User outcome and state matrix

| State | Expected outcome | Direct evidence |
| --- | --- | --- |
| Defaults absent/empty/unmatched | No regeneration, even without assignments | Three no-op regressions |
| Applicable defaults and populated assignments | Saved covers reach assigned combined/prepared segments | Real parser tests and normal build/modify tests |
| Applicable defaults, assignments absent/empty | Build-first error before mutation | Two pre-mutation regressions |
| Single-OFE | Existing summary application, no MOFE build | Explicit single-OFE regression |
| Writer failure with intent saved | Error remains visible; retry regenerates unchanged values | Real filesystem failure and retry |
| Saved kslast absent/None/zero/value | Omission preserves state through locked facade and reload | Four durable readback cases |
| Explicit kslast values/clears/collections | Existing conversion/clearing semantics | Parser matrix and JSON/form route tests |
| Malformed values/assignments | Existing errors or ignored parser values; no new fallback | Existing assignment regression and explicit malformed parser cases |

## Error policy and findings

Missing assignments with applicable defaults is expected unbuilt state: existing
actionable build-first error. Writer failure is exceptional and remains an
error, not successful artifact completion. Optional default absence remains
valid. No new exception translation, broad catch, access surface or fallback.
Configured-default precedence and RAP canopy precedence are unchanged.

Source gate: pass, no High/Medium/Low findings. Reviewer verified one regeneration
after all applicable covers, saved-assignment guard before mutation, and narrow
key-presence parser change. Checkpoint ancestry precedes production edits.

## Artifact acceptance and verdict

See [validation evidence](20260919_validation.md) and reusable validators.
Generated/prepared boundary regressions, actual-project execution/output,
normal browser/download, archive/restore and broad-suite gates pass.
Reviewer independently reran the current post-restore validator: all 455 hills,
1,065 segments, saved kslast, prepared covers, output and archive checks pass.
The initial inventory omitted generated soil intermediates; all 455 files and
`soils.nodb` are now included. Before/after 2,734 non-log records match exactly;
source-management manifest is unchanged. Observation resolved; no source change.
Final findings: High 0, Medium 0, Low 0. Broad suite completed after reviewer
approval: 9,079 passed, 99 skipped; 286 focused cases cover late additions.
Release recommendation: ship for the validated Forest scope.
No production deployment, source-project repair or compiler work is claimed.
