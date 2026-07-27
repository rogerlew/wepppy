# Codex Scaffold Review — 2026-07-27

**Reviewed**: commit 783095311 (work-package scaffold + spec section 4.1)
**Reviewer**: Codex (via MCP, read-only sandbox, thread 019fa553-347e-76b0-8445-5934e806eb76)
**Dispositioned by**: Claude Code, 2026-07-27 20:55 UTC
**Codex verdict as delivered**: "not fully executable as written" — WP01's description source, WP02's canonical-contract/test scope, and the WP03→WP04 documentation dependency needed correction.
**Post-disposition status**: all findings fixed in commit following this artifact; scaffold executable.

## Findings and Dispositions

| # | Sev | Finding (Codex) | Disposition |
|---|-----|-----------------|-------------|
| 1 | Med | Spec 4.1 requires a plain-language description per check, but check definitions expose only id/title/severity/fix_hint (`cloneCheckDefinition`, core.js), and WP01 treated the check modules (`auth_checks.js`, `bandwidth_checks.js`, `diagnostics-realtime.js`) as reference-only. | **Accepted.** Spec 4.1 now requires a `description` field on check definitions with title-only fallback; WP01's working set moves the three check modules into outputs (descriptions only, no probe-logic changes) and notes core.js must carry the field through. |
| 2 | Med | Spec 4.1 `info` impact statement ("advisory only; no action required") contradicts the rule that every warn/fail renders a `fix_hint`; informational checks (localStorage, AbortController) can warn with actionable remediation. | **Accepted.** `info` impact language reworded to "advisory; WEPPcloud will still run" with an explicit note that the fix-hint rule still applies on warn. |
| 3 | Med | WP02 changes anonymous authorization but only amends the diagnostics UI spec; the canonical `docs/schemas/weppcloud-csrf-contract.md` and `weppcloud-session-contract.md` require route-classification amendments (or an explicit no-amendment disposition) under the contract-first rule. | **Accepted.** Both contracts added to WP02's read set and outputs (amend or record "no normative amendment required" in the tracker with rationale). |
| 4 | Med | WP02's test working set named the wrong suites: reset endpoint tests live in `tests/weppcloud/routes/test_rq_engine_token_api.py` (~line 947, including `test_reset_browser_state_requires_auth`, which asserts the 401 WP02 removes); profile context assertions live in `tests/weppcloud/routes/test_user_profile_token.py` (~line 380). | **Accepted, independently verified.** Both suites named in WP02 outputs and validation gates; package.md test inventory updated. |
| 5 | Med | Serial WP03-before-WP04 sequencing has WP03 wiring a usersum link to a doc that doesn't exist yet, with no canonical filename recorded. | **Accepted.** Canonical path ratified in the tracker: `wepppy/weppcloud/routes/usersum/weppcloud/diagnostics.md`. WP04 split: WP04a (registered stub, Claude Code) lands before WP03; WP04b (full doc) lands last. Sequencing now WP01 → WP02 → WP04a → WP03 → WP04b. |
| 6 | Low | "10-second default timeouts" for bandwidth checks is stale: registered checks pass explicit budgets of 4 s (RTT) and 12 s each (download, upload); the 10 s value is only a low-level helper fallback. | **Accepted, independently verified** (`bandwidth_checks.js:11-13`). Corrected in package.md and WP01; realtime probe windows (20 s + reconnect retry) stated alongside. |
| 7 | Low | `static-src/tests/smoke/diagnostics/` is opt-in deck.gl/map-rendering diagnostics, unrelated to `/weppcloud/diagnostics/`; treating it as this page's smoke suite gives a false verification signal. | **Accepted.** References corrected in package.md, WP01, and WP03 with explicit do-not-touch notes. |
| 8 | Low | Tracker "Last updated: 20:20 UTC" predates its own 20:40 UTC decision entry. | **Accepted.** Timestamp corrected; decision log kept newest-first. |

## Notes
- No high-severity findings; nothing invalidated the package's core scoping (reset relocation rationale, security triage, card contract direction all stood).
- Finding 3's CSRF-token concern for anonymous sessions was also folded into WP02 step 2 and the risk register: WP02 must verify anonymous pages receive a usable CSRF token before shipping, else resolve per the CSRF contract's classification scheme.
