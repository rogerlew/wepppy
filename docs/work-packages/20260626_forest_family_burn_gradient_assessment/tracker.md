# Tracker - Forest-Family Burn Gradient Assessment

> Living document tracking the expanded disturbed matrix assessment for
> deciduous/mixed unburned forests versus existing burned forest managements.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-26 17:19 UTC
**Current phase**: Complete
**Last updated**: 2026-06-26 17:32 UTC
**Next milestone**: None
**Security impact**: none
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Package scaffolded with scope, parameterization guardrail, and security
  triage (2026-06-26 17:19 UTC).
- [x] Extended disturbed matrix and analysis report for forest-family burn
  comparisons (2026-06-26 17:24 UTC).
- [x] Focused 80-run disturbed matrix passed (2026-06-26 17:28 UTC).
- [x] Regenerated `tests/disturbed/analysis_results.md` from expanded outputs
  (2026-06-26 17:29 UTC).
- [x] Added analyzer guard for stale/incomplete output trees
  (2026-06-26 17:32 UTC).
- [x] Updated disturbed README, package, tracker, and project tracker with the
  decision (2026-06-26 17:29 UTC).

## Timeline

- **2026-06-26 17:19 UTC** - Package created and execution started.
- **2026-06-26 17:24 UTC** - Disturbed matrix expanded to `80` simulations
  (`4` textures x `5` vegetation types x `4` severities).
- **2026-06-26 17:28 UTC** - Focused matrix test passed (`83 passed`,
  `2 warnings`, `232.70s`).
- **2026-06-26 17:29 UTC** - Report regenerated from container pytest outputs
  at `/tmp/pytest-of-unknown/pytest-10/disturbed_matrix0/output`.
- **2026-06-26 17:32 UTC** - Analyzer guard verified against the old local
  48-run artifact path; it exits before report writing.

## Decisions Log

### 2026-06-26 17:19 UTC: Use Existing Burned Forest Classes For Assessment

**Context**: The user asked whether existing burned forest managements remain
directionally correct against the new unburned deciduous and mixed forest
managements.

**Options considered**:

1. Add new production deciduous/mixed burned managements immediately.
2. Reuse existing generic forest low/moderate/high severity managements in the
   test harness and assess output direction.
3. Compare only management file parameters without running WEPP.

**Decision**: Use option 2 for this package.

**Impact**: This package remains an assessment and test/report expansion. Any
production parameterization change is deferred until the generated-output
evidence indicates it is needed.

### 2026-06-26 17:29 UTC: No Deciduous/Mixed Burn Classes Indicated

**Context**: The regenerated 80-run matrix showed every evergreen, deciduous,
and mixed forest low/moderate/high burn row was directionally correct for
matched runoff total, sediment-delivery total, and peakflow total.

**Decision**: Do not add low/moderate/high burned deciduous or mixed forest
management classes from this evidence.

**Impact**: The shipped `.man` files and disturbed lookup rows remain unchanged.
Future vegetation-family-specific burned classes require a new parameterization
package with broader evidence or source calibration requirements.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Expanded 80-run matrix is slower than existing 48-run matrix | Medium | Medium | Run focused disturbed suite only; record runtime and failures | Closed |
| Existing report assumptions hard-code 48 runs | Medium | High | Derive run counts from shared matrix constants | Closed |

## Outcome

The regenerated forest-family assessment shows all evergreen, deciduous, and
mixed forest low/moderate/high burn rows are directionally correct by matched
runoff total, sediment-delivery total, and peakflow total. The existing generic
forest burn severity managements remain adequate for this matrix.

Decision: no low/moderate/high burned deciduous or mixed forest managements are
indicated by this test. Open a new parameterization package only if a broader
calibration/evidence matrix shows a directional failure or documents a source
requirement for vegetation-family-specific burned classes.

## Verification Checklist

### Code Quality

- [x] Focused disturbed matrix run passed.
- [x] Report regenerated from expanded outputs.
- [x] `wctl doc-lint` passed for package/docs.
- [x] `git diff --check` passed for changed files.

### Documentation

- [x] Work package closure notes complete.
- [x] Disturbed README validation summary updated.
- [x] PROJECT_TRACKER updated.

## Progress Notes

### 2026-06-26 17:19 UTC: Package Scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Created package and tracker.
- Locked scope to generated-output assessment without parameterization changes.

**Blockers encountered**:

- None.

**Next steps**:

- Extend `tests/disturbed/test_disturbed_matrix.py`.
- Extend and run `tests/disturbed/analyze_matrix.py`.
- Regenerate and assess `tests/disturbed/analysis_results.md`.

**Test results**: Not yet run.

### 2026-06-26 17:29 UTC: Expanded Matrix Complete

**Agent/Contributor**: Codex

**Work completed**:

- Added `deciduous forest` and `mixed forest` to the disturbed matrix.
- Reused existing generic forest burn managements for deciduous/mixed burned
  assessment rows.
- Regenerated `tests/disturbed/analysis_results.md` from the expanded pytest
  output tree.
- Added a full-matrix guard so the analyzer rejects stale/incomplete output
  trees before writing a report.
- Updated the disturbed README and package outcome with the assessment result.

**Blockers encountered**:

- None.

**Next steps**:

- Run documentation lint and whitespace validation.
- Update `PROJECT_TRACKER.md`.

**Test results**:

- `wctl run-pytest tests/disturbed/test_disturbed_matrix.py -q` (`83 passed`,
  `2 warnings`, `232.70s`)
- Report generation loaded `80` simulations from
  `/tmp/pytest-of-unknown/pytest-10/disturbed_matrix0/output`.
- Stale local output guard rejected `tests/disturbed/disturbed_matrix0/output`
  because it has only the old `48`-run layout.
