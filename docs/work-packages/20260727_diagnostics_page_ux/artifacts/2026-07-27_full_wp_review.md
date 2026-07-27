# Independent Post-Implementation WP Review — Diagnostics UX

**Reviewed**: implementation diff `280e7f9d5^..HEAD` (WP01 `1503e1ece`, WP02 `324169a37`, WP03 `cdf73f2aa`, docs WP04a/b)
**Reviewer**: Codex, fresh thread 019fa58a-ece1-71d0-8966-5909f97b0179, read-only, told not to trust the implementation or that its tests prove what they claim; security surface excluded (covered by the separate independent security pass)
**Verified & dispositioned by**: Claude Code, 2026-07-27 (code findings 1 and 9 verified against source before dispatching fixes)
**Reviewer verdict**: substantially meets visual/reset/nav/docs/live-feedback criteria; success criterion 2 (re-run/all-path lifecycle) only partially met as shipped due to finding 1 and its untested state.

## Dimensions reviewed

Correctness (lifecycle/progress/re-run state machine), spec 4.1/4.2 conformance, the 5 success criteria, test-coverage adequacy, quality/regressions. The reviewer explicitly confirmed clean: roster emitted first in registration order; core+extension checks each notify once; thrown/rejected extensions settle as failures; realtime retry yields one terminal result; skipped checks don't affect readiness; in-place card updates with polite live regions; pass/skipped omit fix hints; warn/fail translate taxonomy to impact language; profile reset hooks removed without orphaning shared styles; authenticated nav entries correctly nested; usersum manifest/nav/index/SHA-256 consistent.

## Findings and Dispositions

| # | Sev | Finding | Verified? | Disposition |
|---|-----|---------|-----------|-------------|
| 1 | Medium | `page.js` runDiagnostics(): `activeRun` latch not released if `runAllChecks()` throws synchronously (core checks + subscriber run synchronously, before the `.then/.catch` chain is attached) → Re-run permanently disabled, violating spec 4.2 recoverability. | **Confirmed at page.js:239-275.** Synchronous invocation at line 244; latch release only in the trailing `.then` which never runs on a synchronous throw. | **Fixed** — wrap invocation so a synchronous throw becomes a rejection flowing through `.catch()` and the latch-release `.then()`; regression test added. |
| 2 | Low | Lifecycle Jest test asserts only aggregate event counts; a duplicate/missing settlement pair would still pass. | Confirmed (diagnostics_core_page.test.js). | **Fixed** — assert full event sequence by check ID incl. throwing extension and realtime retry-then-failure. |
| 3 | Low | Card-state test omits queued→running→settled, teardown, skipped/warn rendering, and only catches capitalized "Blocker" (misses raw lowercase taxonomy). | Confirmed. | **Fixed** — exercise all four terminal statuses; reject `blocker`/`degraded`/`info` case-insensitively. |
| 4 | Low | Re-run test never completes one run and starts a second; rerun reset semantics unproven (success criterion 2's protection). | Confirmed. | **Fixed** — genuine two-run test asserting full reset + fresh report. |
| 5 | Low | No assertion that progress increments only on `settled` / finishes at total-of-total, nor that roster cards exist before the runner promise settles. | Confirmed. | **Fixed** — event-driven progress + pre-settle DOM assertions. |
| 6 | Low | WP03 density regression test greps bare `min-height: 0;` / `margin: 0;` anywhere in template; not tied to the check-row selector → a move reintroduces the `.wc-panel` regression while staying green. | Confirmed (test_diagnostics_page.py). | **Fixed** — assertion tied to `#diagnostics_page_root [data-diagnostics-check-list] > li` block. |
| 7 | Low | More→Diagnostics test doesn't assert authenticated role-specific entries (test user has no roles). | Confirmed (test_pure_controls_render.py). | **Fixed** — Admin/Root/Dev render cases for retained entries. |
| 8 | Low | Profile-removal and usersum-link checks are source-string greps, not rendered/resolved. | Confirmed. Note: manifest/nav/index contract already validated by `usersum_docs_tool.py validate`. | **Fixed** — rendered-template link-resolution assertions added; contract validation not duplicated. |
| 9 | Info | `core.js` `runCoreChecks()` (def ~350, exported ~492) is dead code — never called; duplicates the inline core runner and can drift. | **Confirmed** — grep found no call site in static/js or controllers_js. | **Fixed** — function and export removed. |

## Outcome

- **One real correctness fix (finding 1)**; the remaining eight are test-coverage/quality hardening. All nine accepted and dispatched to Codex as a single dispositioned change set. No finding was rejected (contrast the security pass, where finding 6's recommended fix was rejected on evidence).
- **Success criterion 2** ("re-run without reload, guards overlapping runs, re-gates Copy JSON") was **only partially met as shipped** — the guard could latch permanently and was untested. Finding 1's fix plus the finding-4/5 tests restore it to fully met. The package's closure record is updated accordingly.
- **Finding 1 fix** read and confirmed by Claude Code (page.js:244 — `runAllChecks` now invoked inside `Promise.resolve().then(...)`, so a synchronous subscriber throw becomes a rejection reaching `.catch()` and the latch-release `.then()` on every path).
- **Gates**: not re-run by Claude Code (per user request — CI is the verification of record). Codex's fix run reported `wctl run-npm lint` pass, `wctl run-npm test` 87 suites / 658 tests passed, `wctl run-pytest` (diagnostics + pure-controls + user-profile-token) 92 passed, `git diff --check` clean. These are Codex's reported results, to be confirmed by CI on push.
