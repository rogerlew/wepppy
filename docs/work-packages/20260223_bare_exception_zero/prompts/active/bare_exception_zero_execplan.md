# Bare Exception Zero Across Production Scan Scope

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package closes, production scan scope (`wepppy`, `services`) will contain zero `bare except:` handlers, verified by the scanner with allowlist disabled. Runtime contracts are preserved by replacing bare handlers with narrow expected exceptions where possible and explicit boundary `except Exception` only where needed with logging/contract-safe handling.

## Progress

- [x] (2026-02-23 04:29Z) Created package scaffold at `docs/work-packages/20260223_bare_exception_zero/`.
- [x] (2026-02-23 04:29Z) Captured mandatory baseline artifacts (`baseline.json`, `baseline_no_allowlist.json`).
- [x] (2026-02-23 04:39Z) Completed inventory/risk ranking via required `explorer` and defined 4 disjoint worker slices.
- [x] (2026-02-23 04:41Z) Spawned 4 parallel `worker` agents for disjoint slice cleanup.
- [x] (2026-02-23 04:58Z) Milestone A complete: deferred files integrated first (`user.py`, `inbox_service.py`) and slice outputs merged.
- [x] (2026-02-23 05:03Z) Milestone B complete: all slices re-scanned with zero `bare-except`; allowlist drift corrected.
- [x] (2026-02-23 05:15Z) Milestone C complete: hard gate, changed-file enforcement, targeted suites, and full-suite sanity passed on final code state.
- [x] (2026-02-23 05:18Z) Milestone D complete: closeout artifacts written, trackers synchronized, and root `AGENTS.md` ad hoc pointer reset to `none`.

## Surprises & Discoveries

- Observation: Baseline already includes an existing boundary allowlist, but hard bare-exception closure is independent because closure gate uses `--no-allowlist`.
  Evidence: `artifacts/baseline_no_allowlist.json` reports `"bare-except": 82`.

- Observation: Deferred hotspots (`user.py`, `inbox_service.py`) are broad-catch quality issues, not bare-except inventory items.
  Evidence: Inventory report excludes those paths for `bare-except`, but user requirement explicitly prioritizes them.

- Observation: Changed-file enforcement can fail from allowlist line drift even when broad-catch logic is not expanded.
  Evidence: Initial enforcement failed on `user.py` and `nodb/base.py` until allowlist line targets were re-aligned.

- Observation: `mint_profile_token` contract depended on returning the exact JWT configuration error string.
  Evidence: `tests/weppcloud/routes/test_user_profile_token.py::test_profile_token_mint_errors_without_jwt_secret` failed until `str(exc)` response was restored for `JWTConfigurationError`.

## Decision Log

- Decision: Execute four parallel worker slices (WEPPcloud, NoDb, remaining wepppy, CAO services).
  Rationale: Disjoint ownership reduces merge conflicts and covers all 82 bare findings quickly.
  Date/Author: 2026-02-23 / Codex.

- Decision: Enforce strict rule that no `bare except:` can be allowlisted.
  Rationale: Matches hard closure gate and avoids masking `BaseException` swallowing.
  Date/Author: 2026-02-23 / Codex.

- Decision: Re-point allowlist entries `BEA-20260223-010/011` to `_build_meta` and `_build_map_meta` boundaries.
  Rationale: Keeps allowlist rationale aligned to true per-run metadata skip boundaries and avoids ambiguous route-level suppression.
  Date/Author: 2026-02-23 / Codex.

- Decision: Add debug breadcrumbs to allowlisted NoDb mirror boundaries in `NoDbBase.dump`.
  Rationale: Preserve best-effort boundary behavior while removing silent swallow behavior in touched code.
  Date/Author: 2026-02-23 / Codex.

## Outcomes & Retrospective

Package objective was met end-to-end: production scan scope now reports zero `bare except:` handlers under `--no-allowlist` (`82 -> 0`), changed-file enforcement passes, and required targeted/full validation suites pass on final code state.

The most important mid-flight corrections were (1) a route contract regression in `mint_profile_token` response text and (2) allowlist line drift after refactors. Both were fixed in-package and revalidated, then documented in `artifacts/final_validation_summary.md`.

Residual debt remains in non-bare broad catches, but touched-file boundaries are now explicit, logged, and allowlisted where deliberate.

## Context and Orientation

The scanner (`tools/check_broad_exceptions.py`) walks tracked Python files under `wepppy` and `services` by default and reports three broad kinds: `bare-except`, `except-Exception`, and `except-BaseException`. For this package, success is hard-gated on `bare-except == 0` in `--no-allowlist` mode, plus changed-file enforcement (`--enforce-changed`) and subsystem tests.

Key files:
- Work package docs: `docs/work-packages/20260223_bare_exception_zero/package.md`, `docs/work-packages/20260223_bare_exception_zero/tracker.md`.
- Active plan: `docs/work-packages/20260223_bare_exception_zero/prompts/active/bare_exception_zero_execplan.md`.
- Baselines: `docs/work-packages/20260223_bare_exception_zero/artifacts/baseline.json`, `docs/work-packages/20260223_bare_exception_zero/artifacts/baseline_no_allowlist.json`.
- Canonical broad-boundary allowlist: `docs/standards/broad-exception-boundary-allowlist.md`.

Risk-first cleanup order:
1. Deferred files first (`wepppy/weppcloud/routes/user.py`, `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`).
2. Concentrated runtime modules (`wepppy/weppcloud/routes/*`, `wepppy/nodb/*`, and any remaining scanner hits under `wepppy` and `services`).
3. Final gate and documentation closure.

## Plan of Work

Milestone A (deferred-first):
- Apply minimal contract-safe refactors in `user.py` and `inbox_service.py` for broad boundary quality and logging context.
- Merge parallel worker results for WEPPcloud/NoDb/other slices, ensuring every `bare except:` is removed.

Milestone B (slice closure):
- Re-scan each touched slice to confirm local bare count is zero.
- Resolve any line drift against allowlist entries where broad boundaries are intentionally retained.

Milestone C (global validation):
- Run hard bare gate with `--no-allowlist` and `jq` assertion.
- Run changed-file enforcement against `origin/master`.
- Run targeted tests for touched subsystems, then full pre-handoff suite.

Milestone D (closeout):
- Capture after snapshots in `artifacts/`.
- Update tracker and project board states.
- Reset root `AGENTS.md` active ad hoc ExecPlan pointer to `none`.

## Concrete Steps

Run from `/workdir/wepppy`.

Baseline (already captured):
    python3 tools/check_broad_exceptions.py --json > docs/work-packages/20260223_bare_exception_zero/artifacts/baseline.json
    python3 tools/check_broad_exceptions.py --json --no-allowlist > docs/work-packages/20260223_bare_exception_zero/artifacts/baseline_no_allowlist.json

Hard gate (required):
    python3 tools/check_broad_exceptions.py --json --no-allowlist > /tmp/broad_no_allow.json
    jq -e '.kinds["bare-except"] == 0' /tmp/broad_no_allow.json

Changed-file enforcement:
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

Tests:
    wctl run-pytest tests/<relevant module path>
    wctl run-pytest tests --maxfail=1

Docs lint:
    wctl doc-lint --path AGENTS.md --path PROJECT_TRACKER.md --path docs/work-packages/20260223_bare_exception_zero/package.md --path docs/work-packages/20260223_bare_exception_zero/tracker.md --path docs/work-packages/20260223_bare_exception_zero/prompts/active/bare_exception_zero_execplan.md

## Validation and Acceptance

Acceptance conditions:
- Scanner reports exactly zero `bare-except` findings under `--no-allowlist`.
- Changed-file enforcement passes with no per-file broad-catch increase.
- Deferred files are refactored and tested first.
- Targeted subsystem tests and full-suite pre-handoff test pass.
- Work-package docs, project tracker, and root AGENTS pointers are consistent at closure.

## Idempotence and Recovery

- Scanner commands are read-only and can be re-run safely.
- If a slice edit introduces regressions, revert only the affected hunk/file and re-run slice-level checks before global gates.
- Keep boundary try/except blocks minimal to reduce rollback scope.

## Artifacts and Notes

- `docs/work-packages/20260223_bare_exception_zero/artifacts/baseline.json`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/baseline_no_allowlist.json`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/after.json`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/after_no_allowlist.json`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/final_validation_summary.md`

## Interfaces and Dependencies

- Scanner interface: `tools/check_broad_exceptions.py` (`--json`, `--no-allowlist`, `--enforce-changed`, `--base-ref`).
- Allowlist interface: `docs/standards/broad-exception-boundary-allowlist.md` markdown table entries (owner, rationale, expiry required).
- Runtime contract dependency: route/worker error envelopes must remain canonical and telemetry/logging must be preserved.

---

Revision note (2026-02-23 04:41Z): Initialized active ExecPlan after baseline capture and worker orchestration launch so milestone tracking is live before code integration.
Revision note (2026-02-23 05:19Z): Marked Milestones A-D complete, recorded enforcement/test discoveries, and finalized outcomes/closeout artifacts after passing all required gates.
