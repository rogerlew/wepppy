# Agent Prompt: WP-07 (Validation, Accessibility, Security, Closeout)

Execute **WP-07** from `docs/ui-docs/diagnostics-page.plan.md`.

## Objective

Run final diagnostics initiative closeout: full validation, accessibility and security disposition, and documentation/status finalization for the diagnostics page work.

## Inputs

- `docs/ui-docs/diagnostics-page.plan.md` (WP-07)
- `docs/ui-docs/diagnostics-page.spec.md`
- `docs/ui-docs/ui-style-guide.md`
- Diagnostics implementation files under:
  - `wepppy/weppcloud/templates/diagnostics/`
  - `wepppy/weppcloud/static/js/diagnostics/`
  - `wepppy/weppcloud/controllers_js/__tests__/diagnostics_*.test.js`
  - `tests/weppcloud/routes/test_diagnostics_page.py`

## Scope

1. Run final quality gates (targeted + broad).
2. Perform focused accessibility review of diagnostics UI behavior/semantics.
3. Perform focused security review of diagnostics checks and report redaction.
4. Finalize docs/status board for completed work-packages.

## Required Validation Commands

Run and report exact results:

- `wctl run-npm test -- diagnostics`
- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py --maxfail=1`
- `wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1 -k bandwidth`
- `wctl run-pytest tests/weppcloud --maxfail=1`
- `wctl run-pytest tests/query_engine --maxfail=1`
- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl doc-lint --path docs/ui-docs/diagnostics-page.spec.md --path docs/ui-docs/diagnostics-page.plan.md`

If any command is blocked (environment/dependency/runtime), document blocker details and run the closest viable fallback.

## Accessibility Review Checklist

Review `/diagnostics/` against `ui-style-guide.md` conventions:

- heading hierarchy and landmark structure
- `noscript` blocker clarity
- status messaging semantics (`aria-live`, alert usage)
- keyboard usability for `Copy JSON` and report preview interactions
- readable severity/status communication consistency with existing WC patterns

If issues are found, either:
- fix in scope and validate, or
- document explicit follow-up item with severity and rationale.

## Security Review Checklist

Confirm and document:

- redaction safety for copied JSON/report preview
- auth probe same-origin + CSRF behavior alignment
- realtime probe bounded timeout/retry behavior
- bandwidth probes are informational only and time-bounded
- no secret leakage in evidence/fix hints (tokens/cookies/auth headers/JWT)

## Documentation/Status Closeout

- Update `docs/ui-docs/diagnostics-page.plan.md` orchestration board statuses to final dispositions (`DONE`/`accepted-with-followup` as appropriate).
- If implementation behavior diverges from `docs/ui-docs/diagnostics-page.spec.md`, update the spec in the same change set with concise rationale.

## Hard Constraints

- Do not modify unrelated subsystems.
- Keep changes scoped to diagnostics and docs closeout.
- Preserve existing WEPPcloud UI conventions and contracts.

## Handoff Format

Return:

- files changed
- commands run with outcomes
- accessibility findings + disposition
- security findings + disposition
- final WP status table updates
- residual risks / accepted follow-ups

Do not commit or push.
