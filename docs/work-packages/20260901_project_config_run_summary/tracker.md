# Tracker - Project Config Run Summary

> Living document tracking progress, decisions, risks, and communication for
> this work package.

## Quick Status

**Timezone**: UTC

**Started**: 2026-09-01 18:03 UTC

**Current phase**: Closed

**Last updated**: 2026-09-01 19:05 UTC

**Next milestone**: None

**Security impact**: `low`

**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Scaffolded package, tracker, ExecPlan, draft contract decision, and
  correctness artifact (2026-09-01 18:03 UTC).
- [x] Identified the fixed run header, run-page context builder, and focused
  template test module (2026-09-01 18:03 UTC).
- [x] Confirmed that locale pills use canonical locale IDs, including
  `locale: continental-us` (2026-09-01 18:07 UTC).
- [x] Recorded execution authorization, exact state behavior, and canonical
  section 7.8 amendment (2026-09-01 18:09 UTC).
- [x] Completed two independent reviews; both reported medium checkpoint
  findings requiring correction and renewed review (2026-09-01 18:14 UTC).
- [x] Corrected eligibility, per-field precedence, state/input separation,
  discrepancy classification, security triage, and canonical regression
  obligations (2026-09-01 18:18 UTC).
- [x] Operator explicitly approved the complete corrected edge-policy matrix
  (2026-09-01 18:24 UTC).
- [x] Both renewed independent reviews returned Ready with no medium/high
  findings (2026-09-01 18:31 UTC).
- [x] Committed standalone contract checkpoint `790f34207`
  (2026-09-01 18:32 UTC).
- [x] Implemented server summary model, locale pill, accessible modal, theme
  styling, tests, smoke coverage, and user guidance (2026-09-01 18:39 UTC).
- [x] Focused 10-test gate, 167-test rendering gate, frontend lint, and all 108
  frontend suites/833 tests passed (2026-09-01 18:42 UTC).
- [x] Independent implementation review passed after resolving two medium
  findings; no findings remain (2026-09-01 18:43 UTC).
- [x] Full Python suite passed: 7,313 passed and 63 skipped; documentation,
  smoke syntax, and diff gates also passed (2026-09-01 19:05 UTC).
- [x] Committed implementation and package closeout as `2887b74ec`
  (2026-09-01 19:07 UTC).

## Timeline

- **2026-09-01 18:03 UTC** - Package created and initial source/contract
  orientation completed.

## Decisions Log

### 2026-09-01 18:03 UTC: Use effective run authority and server rendering

**Context**: The summary describes the current run, not the current Builder
registry defaults, and all requested values are available while the run page is
being assembled.

**Decision**: Plan one server-side, read-only presentation model rendered into
the existing header/modal shell. Do not add an API or infer missing values from
current Builder defaults.

**Impact**: The pill and modal share one value source and remain truthful for
stored projects and supported legacy states.

### 2026-09-01 18:03 UTC: Treat locale example as an open wording correction

**Context**: The requested `us-contintental` text does not match the canonical
Config Builder locale ID `continental-us` and contains a spelling error.

**Decision**: Display the canonical locale ID, so the example becomes
`locale: continental-us`. The operator confirmed this choice.

**Impact**: No implementation may hard-code a new or misspelled locale alias;
all locale pills reflect the run's canonical locale ID.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Summary displays registry defaults instead of effective run values | Medium | Medium | Build from resolved run/config authority and test drift/legacy states | Mitigated |
| Shared header change leaks onto unintended pages | Medium | Medium | Gate the feature with explicit Config Builder run context and test absence | Mitigated |
| Missing values cause a 500 or misleading fallback | Medium | Low | Define honest unavailable behavior in the contract and state matrix | Mitigated |
| Long locale text harms narrow layouts | Low | Medium | Include reflow/axe smoke coverage | Mitigated; live smoke environment unavailable |

## Verification Checklist

### Code Quality

- [x] Focused Python template/route tests pass.
- [x] Frontend tests and lint pass.
- [x] `git diff --check` is clean.

### Security

- [x] Security impact reclassified as `low` for the new HTML disclosure sink.
- [x] Confirm authorization denial precedes rendering and hostile values are
  escaped.

### Documentation

- [x] Canonical UI contract approved and amended before implementation.
- [x] Affected user/developer documentation updated.
- [x] Work package and `PROJECT_TRACKER.md` kept current.
- [x] Scoped documentation lint passes.

### Testing

- [x] Populated Config Builder state is covered.
- [x] Absent/empty, supported legacy, and malformed states are covered or
  explicitly ruled out by contract.
- [x] Keyboard/modal and narrow-layout assertions are included in the
  authenticated Playwright smoke. Live execution was attempted but the local
  environment could neither provision nor locate a usable Config Builder run.
- [x] Correctness/UX review passes with no unresolved medium/high findings.

## Progress Notes

### 2026-09-01 18:03 UTC: Work package scaffolded

**Agent/Contributor**: Codex

**Work completed**:

- Read the repository work-package, ExecPlan, contract-first, and WEPPcloud
  guidance.
- Located the projection pill and More menu in
  `wepppy/weppcloud/templates/header/_run_header_fixed.htm`.
- Located effective run presentation assembly in
  `wepppy/weppcloud/routes/run_0/run_0_bp.py` and existing rendering tests in
  `tests/weppcloud/routes/test_pure_controls_render.py`.

**Blockers encountered**:

- The required contract-first checkpoint must precede implementation.

**Next steps**:

- Confirm wording, enumerate canonical contract delta/state behavior, obtain
  the required reviews and approval, and commit the checkpoint ancestor.

**Test results**: Initial package and tracker documentation lint passed.

### 2026-09-01 19:05 UTC: Validation and closeout

**Agent/Contributor**: Codex

**Work completed**:

- Passed the complete Python regression suite: 7,313 passed, 63 skipped.
- Passed focused route/rendering coverage, all frontend tests and lint, scoped
  documentation lint, smoke-file syntax validation, and `git diff --check`.
- Closed both independent-review findings and recorded a Ready verdict with no
  unresolved findings.

**Environmental limitation**:

- The authenticated Playwright test now opens and evaluates the modal at a
  640-pixel viewport, including focus return and Escape dismissal. Attempts to
  run that conditional branch could not obtain a usable Config Builder target:
  the test API lacked `configs/config.cfg`, scanned remote runs did not reach a
  map-bearing run page, and the direct local route remained CAP-gated. This is
  an environment-fixture limitation, not a detected product failure.

**Test results**: All executable code, frontend, documentation, and diff gates
passed; the live conditional browser branch remains unexecuted and is retained
as repeatable coverage for an environment with a Config Builder fixture.

## Watch List

- **Shared header reach**: `_run_header_fixed.htm` is reused; keep the new hints
  limited to the approved Config Builder run surface.
- **Authority drift**: stored run selections must not be replaced by live
  registry defaults for display.

## Communication Log

### 2026-09-01 18:03 UTC: Initial wording question

**Participants**: User and Codex

**Question/Topic**: Whether the locale pill should use the canonical ID
`continental-us` or the example spelling `us-contintental`.

**Outcome**: The user confirmed canonical locale IDs. The Continental US pill
is `locale: continental-us`; no display alias is introduced.

### 2026-09-01 18:07 UTC: Locale ID wording confirmed

**Participants**: User and Codex

**Question/Topic**: Locale pill value convention.

**Outcome**: Use the effective canonical locale ID for every locale.

### 2026-09-01 18:09 UTC: Work-package execution authorized

**Participants**: User and Codex

**Question/Topic**: Execute the prepared work package.

**Outcome**: Proceed milestone by milestone. The exact contract matrix uses
`Not available` for absent individual values and preserves all six rows.

### 2026-09-01 18:18 UTC: Initial contract reviews dispositioned

**Participants**: Independent correctness reviewer, independent governance
reviewer, and Codex

**Question/Topic**: Contract checkpoint readiness.

**Outcome**: Both reviews were Not Ready. All document-addressable findings
were corrected. Exact edge-policy approval and renewed reviewer confirmation
remain required before the standalone checkpoint commit.

### 2026-09-01 18:24 UTC: Corrected edge policy approved

**Participants**: User and Codex

**Question/Topic**: Exact target, nested/PUP, unavailable-value, locale-pill,
and non-target behavior.

**Outcome**: User explicitly approved the complete matrix without changes.
