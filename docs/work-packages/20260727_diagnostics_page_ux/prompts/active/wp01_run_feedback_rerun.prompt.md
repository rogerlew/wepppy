# WP01 — Diagnostics Run Feedback and Re-run Control

> **Purpose**: Make the 30+ second diagnostics run legible (live per-check states, overall progress) and repeatable in place (re-run button).
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active

## Context

`/weppcloud/diagnostics/` runs all registered checks once at DOMContentLoaded (`page.js` invokes the core runner). While checks run — bandwidth probes budget 4 s (RTT) and 12 s each (download, upload), and realtime probes hold 20-second windows with a reconnect retry, pushing total wall time past 30 seconds — the check list shows a single static "Running diagnostics..." placeholder that is only replaced when results settle. There is no progress indication and no way to re-run without reloading the page.

The settled cards are also confusing: `renderChecks` in `page.js` unconditionally appends a "Severity:" label and a fix hint to every card, so a passing check reads "pass Severity: Blocker" followed by remediation advice — users get hung up on "Blocker" on a check that passed, and fix hints on passing checks imply something needs fixing. The spec now has a Check Card Presentation Contract (section 4.1) ratified from this user feedback: one live card per check that updates in place through queued/running/settled states; severity taxonomy words never rendered verbatim (translated to plain-language impact statements on warn/fail only); fix hints and evidence rendered only on warn/fail.

- Current state: check list populates only after the run settles; every card shows raw severity labels and fix hints regardless of outcome; Copy JSON is disabled until settle; no re-run affordance.
- Goal state: each check has an active card conforming to spec section 4.1, an overall progress indicator, and a Re-run button that repeats the full run in place.
- Related work: `docs/work-packages/20260727_diagnostics_page_ux/package.md` (this package), `docs/ui-docs/diagnostics-page.spec.md` — section 4.1 is the card contract; implement to it, do not redesign it.

## Objective

Within one second of page load the user sees one card per check, all in queued state; each card updates in place through running to its settled state with content per spec section 4.1 (no severity labels or fix hints on passing checks; plain-language impact statements instead of raw taxonomy words on warn/fail); a completed-of-total progress indicator is visible during the run; a Re-run control repeats all checks without a page reload, guards against overlapping runs, and re-gates Copy JSON until the new run settles.

**Success looks like**: a user on a slow connection watches individual check cards flip from queued to running to pass/warn/fail over the 30+ second run, always knowing how many remain; a passing check reads simply as a pass with a one-line result; a failing check explains its impact in plain language with a fix hint; Re-run repeats the measurement in place.

## Working Set

### Files to Read (Inputs)
- `docs/ui-docs/diagnostics-page.spec.md` — page contract, check taxonomy, report semantics
- `wepppy/weppcloud/static/js/diagnostics/core.js` — check registry and runner; where lifecycle events must originate
- `wepppy/weppcloud/static/js/diagnostics/page.js` — DOM orchestration, list rendering, copy gating
- `wepppy/weppcloud/static/js/diagnostics/report.js` — report assembly and generated-at semantics
- `docs/ui-docs/ui-style-guide.md` — status chip and layout conventions

### Files to Modify (Outputs)
- `wepppy/weppcloud/static/js/diagnostics/core.js` — expose per-check lifecycle notifications (registered, started, settled) to a subscriber; keep the existing runner contract for check modules unchanged
- `wepppy/weppcloud/static/js/diagnostics/page.js` — render all checks immediately in registration order with live state chips; overall progress indicator; Re-run button wiring with a concurrency guard; reset overall-readiness chip, report preview, and Copy JSON gating at the start of each run
- `wepppy/weppcloud/static/js/diagnostics/report.js` — if needed so re-runs produce a fresh report with an updated generated timestamp
- `wepppy/weppcloud/static/js/diagnostics/bandwidth_checks.js`, `auth_checks.js`, `diagnostics-realtime.js` — add a plain-language `description` field to each check definition (spec section 4.1 requires it; `cloneCheckDefinition` in core.js currently exposes only id/title/severity/fix_hint, so core.js must also carry the new field through). No changes to probe logic or budgets.
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm` — Re-run button and progress indicator markup
- `docs/ui-docs/diagnostics-page.spec.md` — amend run-lifecycle and controls sections to match
- `wepppy/weppcloud/controllers_js/__tests__/` — extend the diagnostics Jest suites for lifecycle events, live list rendering, re-run reset behavior, and the concurrency guard

### Files to Reference (Dependencies)
- `wepppy/weppcloud/static-src/tests/smoke/diagnostics/` — NOT this page's test suite: it holds opt-in deck.gl/map-rendering diagnostics specs; do not touch it and do not treat it as verification for this page

### Files to Avoid (Exclusions)
- Probe sizes and timeout budgets in `bandwidth_checks.js` / `diagnostics-realtime.js` — the wait must become legible, not shorter; changing budgets changes measurement semantics
- `wepppy/weppcloud/controllers_js/bootstrap_observability.js` — separate subsystem
- `wepppy/weppcloud/routes/weppcloud_site.py` — no server-side change in this WP

## Instructions

1. Read the spec and the two orchestration modules; identify where the runner iterates checks and where the settled results reach `page.js`.
2. Add lifecycle observation to the core runner: a subscriber must learn the full ordered check roster before execution starts, and each check's transition to running and to settled with its result. Preserve the public registration API used by the check modules.
3. Rework the page module's card rendering to spec section 4.1: on run start, render one card per check in queued state with zero-of-total progress; update each card in place as notifications arrive; settled cards show state-dependent content — pass cards get a chip and concise result only, warn/fail cards get the severity translated to an impact statement plus fix hint and de-emphasized evidence, skipped cards get a one-line reason. Remove the unconditional "Severity:" line and unconditional fix-hint rendering. Check descriptions and impact statements need plain-language copy per check; derive titles/descriptions from the check definitions and keep them non-technical.
4. Add the Re-run button to the template and page module: disabled while a run is active; on click, clear prior states, reset the overall chip and report preview to their pre-run values, and start a fresh run through the same code path as the initial load.
5. Amend the spec: run lifecycle, progress indicator, re-run semantics, and copy gating during re-runs.
6. Extend the Jest suites, including assertions that pass cards omit severity/fix-hint text and that check definitions carry descriptions.

## Validation Gates

- `wctl run-npm lint`
- `wctl run-npm test`
- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py`
- Manual: load the page in the dev stack, confirm live states and progress during the run, then Re-run and confirm gating resets and a fresh report is produced.

## Deliverables

1. Live per-check cards conforming to spec section 4.1 (queued/running/settled states, no severity labels or fix hints on pass, impact-language on warn/fail) with overall progress during runs.
2. Working Re-run control with concurrency guard and gating reset.
3. Amended spec (run lifecycle, progress, re-run sections) and passing extended Jest coverage, including tests asserting pass cards omit severity/fix-hint text and warn/fail cards include impact statement and fix hint.

## Handoff Format

Report per the package tracker's Progress Notes convention: changes made, files modified, test output, deviations, and anything the spec amendment left ambiguous.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
