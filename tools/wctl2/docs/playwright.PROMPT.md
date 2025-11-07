# Follow-Up Agent Instructions — `wctl2 run-playwright`

## Required References
1. **Specification:** `tools/wctl2/docs/playwright.SPEC.md` (authoritative command design)
2. **Existing CLI context:** `tools/wctl2/docs/SPEC.md`, `tools/wctl2/context.py`, `tools/wctl2/commands/__init__.py`
3. **Playwright tests doc:** `tests/README.smoke_tests.md`
4. **Playwright config & suite:** `wepppy/weppcloud/static-src/playwright.config.mjs`, plus the smoke specs under `wepppy/weppcloud/static-src/tests/smoke/`

Review these before writing code. Keep the spec open; do not diverge without approval.

## Deliverable
Implement `wctl2 run-playwright` so that:
- The Typer command exists under `tools/wctl2/commands/playwright.py`
- `tools/wctl2/commands/__init__.py` registers it
- All behaviors in `playwright.SPEC.md` are functional (suite presets, ping check, overrides, headed clamp, report handling, etc.)
- `wctl2 run-playwright` actually runs Playwright with the correct env/CLI wiring before handing back the workspace

## Implementation Outline
1. **Create command module** per spec (import sections, helper functions, Typer command). Follow naming and control flow exactly.
2. **Environment & suite handling**
   - `_resolve_base_url` and `_ping_test_support`
   - Suite → grep mapping + user override precedence
   - `--run-path` auto-disables provisioning
   - `--overrides` builder → JSON stored in `SMOKE_RUN_OVERRIDES`
3. **Execution logic**
   - Build env vars (`SMOKE_*`)
   - Construct Playwright CLI args (respecting `--headed`, `--report`, `--report-path`, `--playwright-args`)
   - `npm run test:playwright -- …` from `wepppy/weppcloud/static-src`
   - When `--report`, always call `npx playwright show-report <path>` after the run (even on failure, per spec)
4. **Docs/tests updates**
   - If needed, add unit coverage or update README snippets referenced by the spec

## Validation Before Handback
1. `pytest tools/wctl2` (or targeted tests) if new helpers require coverage
2. `npm run lint` inside `wepppy/weppcloud/static-src` (the spec assumes lint-clean tree)
3. Run `wctl2 run-playwright --env dev --suite smoke --workers 1 --no-create-run --run-path <existing-run>` (or equivalent) to prove the command is functional. Capture the command output for reviewers.

Do **not** hand back until `wctl2 run-playwright` works end-to-end. Document all commands run and their outcomes in the final summary for Claude’s acceptance testing.

Good luck!***
