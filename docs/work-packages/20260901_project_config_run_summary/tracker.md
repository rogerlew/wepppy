# Tracker - Project Config Run Summary

> Living document tracking progress, decisions, risks, and communication for
> this work package.

## Quick Status

**Timezone**: UTC

**Started**: 2026-09-01 18:03 UTC

**Current phase**: Contract discovery

**Last updated**: 2026-09-01 18:31 UTC

**Next milestone**: Commit the standalone checkpoint ancestor

**Security impact**: `low`

**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Resolve the locale pill wording and the exact absent-state display.
- [ ] Inventory all applicable canonical contracts and create the required
  standalone contract-first checkpoint.
- [ ] Build one server-side summary presentation model from effective run
  authority.
- [ ] Add the locale pill, More-menu action, and accessible modal.
- [ ] Add focused regression and accessibility coverage.
- [ ] Update affected user/developer documentation and complete correctness
  review.

### In Progress

- [ ] Selectively commit the approved standalone contract checkpoint.

### Blocked

- [ ] Implementation is blocked until the contract-first checkpoint is
  approved, independently reviewed, and committed as a standalone ancestor.

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
| Summary displays registry defaults instead of effective run values | Medium | Medium | Build from resolved run/config authority and test drift/legacy states | Open |
| Shared header change leaks onto unintended pages | Medium | Medium | Gate the feature with explicit Config Builder run context and test absence | Open |
| Missing values cause a 500 or misleading fallback | Medium | Low | Define honest unavailable behavior in the contract and state matrix | Open |
| Long locale text harms narrow layouts | Low | Medium | Include reflow/axe smoke evidence | Open |

## Verification Checklist

### Code Quality

- [ ] Focused Python template/route tests pass.
- [ ] Frontend tests and lint pass.
- [ ] `git diff --check` is clean.

### Security

- [x] Security impact reclassified as `low` for the new HTML disclosure sink.
- [ ] Confirm authorization denial precedes rendering and hostile values are
  escaped.

### Documentation

- [ ] Canonical UI contract approved and amended before implementation.
- [ ] Affected user/developer documentation updated.
- [ ] Work package and `PROJECT_TRACKER.md` kept current.
- [ ] Scoped documentation lint passes.

### Testing

- [ ] Populated Config Builder state is covered.
- [ ] Absent/empty, supported legacy, and malformed states are covered or
  explicitly ruled out by contract.
- [ ] Keyboard/modal and narrow-layout behavior is manually verified.
- [ ] Correctness/UX review passes with no unresolved medium/high findings.

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
