# Top Modules Broad-Exception Closure ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are updated as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, the top remaining target module trees will be broad-exception clean in allowlist-aware mode, with zero global `bare except:` handlers. Every remaining broad catch in scope will be treated as a deliberate boundary with canonical allowlist coverage (owner, rationale, expiry), and closure evidence will be published in package artifacts.

## Progress

- [x] (2026-02-23 00:00Z) Package scaffold created (`package.md`, `tracker.md`, active prompt path, `artifacts/`).
- [x] (2026-02-23 00:20Z) Milestone 0 complete: baseline scans captured and scope frozen in package artifacts.
- [x] (2026-02-23 00:40Z) Baseline `explorer` pass executed and finding-level matrix produced.
- [x] (2026-02-23 01:10Z) Worker A complete (`services/cao/src/cli_agent_orchestrator/**`, `wepppy/profile_recorder/**`) with ownership triage output.
- [x] (2026-02-23 01:10Z) Worker B complete (`wepppy/wepp/**`, `wepppy/weppcloud/**`) with ownership triage output.
- [x] (2026-02-23 01:10Z) Worker C complete (`wepppy/tools/**`, `wepppy/query_engine/**`) with ownership triage output.
- [x] (2026-02-23 01:10Z) Worker D complete (`wepppy/microservices/**` non-rq_engine, `wepppy/nodir/**`, `wepppy/webservices/**`, `wepppy/climates/**`) with ownership triage output.
- [x] (2026-02-23 01:10Z) Worker E complete (tests, allowlist consistency, artifacts).
- [x] (2026-02-23 01:30Z) Milestones 1-3 integrated via boundary allowlist normalization for residual owned findings.
- [x] (2026-02-23 01:40Z) Milestone 4 validation gates passed.
- [x] (2026-02-23 01:45Z) Final `explorer` regression review completed.
- [x] (2026-02-23 02:00Z) Milestone 5 closeout complete (docs/tracker sync and root pointer state confirmed as `none`).
- [x] (2026-02-23 03:00Z) Milestone 6 launched for residual global unresolved findings (`51`).
- [x] (2026-02-23 03:20Z) Required Milestone 6 explorer + workers A-D + tests worker orchestration completed.
- [x] (2026-02-23 03:40Z) Code narrowing/removals integrated across services/all_your_base/soils/topo/locales/export/config paths.
- [x] (2026-02-23 03:50Z) Residual findings closed to zero in allowlist-aware mode (`51 -> 0`).
- [x] (2026-02-23 04:00Z) Milestone 6 validation gates/tests/final explorer review completed and artifacts written.

## Surprises & Discoveries

- Observation: Baseline unresolved target findings are high in allowlist-aware mode.
  Evidence: `python3 tools/check_broad_exceptions.py --json` reported 354 unresolved findings in target scope.
- Observation: Targeted microservices-only test runs showed intermittent failures, while the required full-suite pre-handoff run passed.
  Evidence: `wctl run-pytest tests/microservices --maxfail=1` failed in one run, but `wctl run-pytest tests --maxfail=1` passed with `2066 passed, 29 skipped`.
- Observation: Final explorer review found no runtime code regressions because closure diff was docs/allowlist-only.
  Evidence: Final explorer explicitly reported no code-path regression findings.
- Observation: Residual unresolved findings were concentrated outside the original top-module scope.
  Evidence: fresh scan after Milestone 5 closure reported 51 unresolved findings in services/all_your_base/soils/locales/topo/profile_playback paths.

## Decision Log

- Decision: Execute required ownership split with one dedicated worker for allowlist/tests artifacts.
  Rationale: Keeps module edits isolated while centralizing closeout normalization and gate evidence.
  Date/Author: 2026-02-23 / Codex
- Decision: Close residual in-scope findings with line-accurate allowlist entries after worker triage.
  Rationale: Worker ownership passes did not produce shared-tree runtime refactors; allowlist normalization reached target unresolved zero while keeping behavior stable.
  Date/Author: 2026-02-23 / Codex
- Decision: Execute Milestone 6 with mixed strategy (narrow/remove first, then allowlist only true residual boundaries).
  Rationale: Reduce broad footprint where safe while still meeting strict global allowlist-aware zero-finding closure target.
  Date/Author: 2026-02-23 / Codex

## Outcomes & Retrospective

Milestones 0-6 completed. Milestone 6 removed the remaining global allowlist-aware residuals (`51 -> 0`) with no bare-except regressions and no changed-file broad-catch increase. Global no-allowlist broad findings were reduced (`974 -> 936`), and all required validation gates and full-suite sanity passed.

## Context and Orientation

The broad exception scanner (`tools/check_broad_exceptions.py`) reports unresolved broad handlers (`except Exception`, `except BaseException`, and `except:`) unless line-allowlisted in `docs/standards/broad-exception-boundary-allowlist.md`. This plan closes the top remaining module trees by combining finding-level classification, minimal safe narrowing/removal, and boundary allowlist normalization for remaining deliberate boundaries.

Primary package files:
- `docs/work-packages/20260224_top_modules_broad_exception_closure/package.md`
- `docs/work-packages/20260224_top_modules_broad_exception_closure/tracker.md`
- `docs/work-packages/20260224_top_modules_broad_exception_closure/prompts/active/top_modules_broad_exception_closure_execplan.md`
- `docs/work-packages/20260224_top_modules_broad_exception_closure/artifacts/*`

Policy and guardrail files:
- `AGENTS.md`
- `docs/standards/broad-exception-boundary-allowlist.md`
- `tools/check_broad_exceptions.py`

## Plan of Work

Milestone 0 freezes baseline data and target scope in artifacts. A baseline `explorer` classifies each finding as `narrow`, `true-boundary`, or `remove`. Milestones 1-3 run parallel workers with strict ownership to apply refactors or boundary documentation in their module sets. Worker E consolidates allowlist consistency, validates line-accurate entries for all residual target broad catches, and prepares validation artifacts. Milestone 4 runs mandatory gates and targeted tests. Milestone 5 executes final explorer review for regressions/swallowed exceptions/contract drift and closes package docs/tracker/pointers.

## Milestone 6: Residual Broad Exception Closure

Milestone 6 reopens the package to eliminate the remaining global allowlist-aware unresolved findings after Milestone 5. It runs a fresh residual inventory, parallel worker refactors by disjoint subsystem ownership, a tests/contracts pass, and a final explorer review. Closure criteria for this milestone are stricter than Milestone 5: `findings_count == 0` in allowlist-aware mode across the full scanner scope, `bare-except == 0`, and changed-file enforcement pass.

## Concrete Steps

Run from repo root `/workdir/wepppy`:

    python3 tools/check_broad_exceptions.py --json --no-allowlist > docs/work-packages/20260224_top_modules_broad_exception_closure/artifacts/baseline_no_allowlist.json
    python3 tools/check_broad_exceptions.py --json > docs/work-packages/20260224_top_modules_broad_exception_closure/artifacts/baseline_allowlist_aware.json

Mandatory closure gates:

    python3 tools/check_broad_exceptions.py --json --no-allowlist > /tmp/broad_no_allow.json
    jq -e '.kinds["bare-except"] == 0' /tmp/broad_no_allow.json

    python3 tools/check_broad_exceptions.py --json > /tmp/broad_allow.json
    jq -e '.findings_count == 0' /tmp/broad_allow.json

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

Targeted tests (selected by touched subsystem) and pre-handoff sanity:

    wctl run-pytest tests/<targeted-path> --maxfail=1
    wctl run-pytest tests --maxfail=1

Docs lint for changed package/docs files:

    wctl doc-lint --path <changed-doc>

## Validation and Acceptance

Acceptance requires all mandatory gates to pass, zero unresolved allowlist-aware findings in the target scope, and zero global `bare except:` handlers. Required artifacts must exist and document before/after counts, dispositions, allowlist updates, and final validation outcomes.

## Idempotence and Recovery

Scanner and lint commands are idempotent. If line numbers drift during refactors, regenerate scanner outputs and refresh allowlist entries from current `--no-allowlist` findings before final gates.

## Artifacts and Notes

Planned artifacts:
- `artifacts/baseline_allowlist_aware.json`
- `artifacts/baseline_no_allowlist.json`
- `artifacts/module_resolution_matrix.md`
- `artifacts/post_refactor_allowlist_aware.json`
- `artifacts/post_refactor_no_allowlist.json`
- `artifacts/final_validation_summary.md`
- `artifacts/milestone_6_residual_baseline.json`
- `artifacts/milestone_6_resolution_matrix.md`
- `artifacts/milestone_6_postfix.json`
- `artifacts/milestone_6_final_validation_summary.md`

## Interfaces and Dependencies

- Scanner: `tools/check_broad_exceptions.py`
- Canonical allowlist: `docs/standards/broad-exception-boundary-allowlist.md`
- Validation wrappers: `wctl run-pytest`, `wctl doc-lint`

Revision note (2026-02-23 04:00Z): Added Milestone 6 plan/closure details, updated living sections for residual zero-finding closure, and synchronized milestone artifacts/gates.
