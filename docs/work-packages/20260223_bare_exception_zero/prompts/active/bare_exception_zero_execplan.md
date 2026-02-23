# Bare Exception Zero - Phase 2 Broad-Exception Boundary Closure

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are maintained through closure.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Phase 1 removed all production `bare except:` handlers. Phase 2 closes broad-exception boundary debt for `wepppy/weppcloud/routes/**`, `wepppy/microservices/rq_engine/**`, and `wepppy/rq/**` so unresolved broad findings in those trees are zero in allowlist-aware scans, while preserving runtime contracts and adding explicit boundary telemetry.

## Progress

- [x] (2026-02-23 05:19Z) Phase 1 closure already complete (`bare except: 82 -> 0`).
- [x] (2026-02-23 05:32Z) Reopened package and activated this ExecPlan for Phase 2.
- [x] (2026-02-23 05:33Z) Captured baseline artifact `artifacts/baseline_broad_exceptions.json` (`523` in-scope broad catches).
- [x] (2026-02-23 05:36Z) Milestone 0 complete: generated `artifacts/target_module_classification.md` line-by-line classification artifact.
- [x] (2026-02-23 05:44Z) Milestones 1-3 complete: subsystem normalization across routes, rq-engine, and rq modules with boundary logging normalization and targeted narrowing/removals.
- [x] (2026-02-23 05:49Z) Milestone 4 complete: tests/contracts worker outputs integrated; regression tests added in `tests/weppcloud/routes/test_user_meta_boundaries.py`, `tests/microservices/test_rq_engine_fork_archive_routes.py`, and `tests/rq/test_project_rq_readonly.py`.
- [x] (2026-02-23 05:58Z) Milestone 5 complete: closure gates passed, postfix/final artifacts written, docs synchronized, root pointer reset.

## Surprises & Discoveries

- Observation: Sub-agent edits introduced two rq-engine regressions in Redis connection close helpers.
  Evidence: `tests/microservices/test_rq_engine_admin_job_routes.py::test_recently_completed_returns_payload` and `tests/microservices/test_rq_engine_run_sync_routes.py::test_run_sync_status_returns_payload` failed with `AttributeError: 'RecordingRedis' object has no attribute 'close'` until `_redis_conn()` guarded `close()` existence.

- Observation: Allowlist line drift occurred repeatedly during late-stage code/test fixes.
  Evidence: target unresolved gate temporarily rose above zero until allowlist was regenerated from current `--no-allowlist` findings.

- Observation: Broad-count reduction occurred but did not eliminate broad boundaries; closure relies on explicit boundary allowlisting.
  Evidence: in-scope broad counts changed from `523` baseline to `475` final (`--no-allowlist`) while allowlist-aware unresolved in scope reached `0`.

## Decision Log

- Decision: Reopen existing package rather than creating a second package.
  Rationale: explicit user requirement and single audit trail for bare + broad closure.
  Date/Author: 2026-02-23 / Codex.

- Decision: Use mandatory orchestration model (explorer + parallel subsystem workers + tests worker + final reviewer).
  Rationale: initial in-scope inventory (`523` findings) required disjoint parallel coverage and an independent review pass.
  Date/Author: 2026-02-23 / Codex.

- Decision: Keep payload parse boundaries broad in rq-engine after reviewer flagged potential contract drift from over-narrowing.
  Rationale: preserve canonical API fallback behavior and avoid new uncaught parse failures.
  Date/Author: 2026-02-23 / Codex.

- Decision: Regenerate target allowlist from current no-allowlist scan at closeout.
  Rationale: deterministic line alignment after regression fixes and final test-driven edits.
  Date/Author: 2026-02-23 / Codex.

## Outcomes & Retrospective

Phase 2 closed successfully against required gates:
- Global `bare except` remained `0`.
- Target-module unresolved broad findings (allowlist-aware) reached `0`.
- Changed-file enforcement passed.
- Targeted subsystem suites and final `wctl run-pytest tests --maxfail=1` passed on final state (`2060 passed, 29 skipped`).

Net scanner deltas:
- In-scope broad (`--no-allowlist`): `523 -> 475`.
- Global broad (`--no-allowlist`): `1066 -> 1018`.

The largest residual tradeoff is allowlist surface area (per-handler, line-precise) rather than full broad-catch elimination; revisit is explicitly bounded by expiry dates in the allowlist.

## Context and Orientation

Phase 2 scope is confined to:
- `wepppy/weppcloud/routes/**`
- `wepppy/microservices/rq_engine/**`
- `wepppy/rq/**`

Canonical interfaces and artifacts:
- Checker: `tools/check_broad_exceptions.py`
- Contract: `docs/schemas/rq-response-contract.md`
- Allowlist: `docs/standards/broad-exception-boundary-allowlist.md`
- Required artifacts:
  - `docs/work-packages/20260223_bare_exception_zero/artifacts/baseline_broad_exceptions.json`
  - `docs/work-packages/20260223_bare_exception_zero/artifacts/postfix_broad_exceptions.json`
  - `docs/work-packages/20260223_bare_exception_zero/artifacts/target_module_classification.md`
  - `docs/work-packages/20260223_bare_exception_zero/artifacts/final_validation_summary.md`

## Plan of Work

Completed milestone sequence:
- Milestone 0: baseline + classification artifact.
- Milestones 1-3: subsystem normalization via parallel workers.
- Milestone 4: tests/contracts additions and allowlist consolidation.
- Milestone 5: closure audit, gate runs, artifact publication, tracker/project sync, and root pointer reset.

## Concrete Steps

Executed from `/workdir/wepppy`:

    python3 tools/check_broad_exceptions.py --json --no-allowlist > docs/work-packages/20260223_bare_exception_zero/artifacts/baseline_broad_exceptions.json
    python3 tools/check_broad_exceptions.py --json --no-allowlist > /tmp/broad_no_allow_current.json
    jq -e '.kinds["bare-except"] == 0' /tmp/broad_no_allow_current.json

    python3 tools/check_broad_exceptions.py --json > /tmp/broad_allow_current.json
    jq -e '[.findings[] | select((.path|startswith("wepppy/weppcloud/routes/")) or (.path|startswith("wepppy/microservices/rq_engine/")) or (.path|startswith("wepppy/rq/")))] | length == 0' /tmp/broad_allow_current.json

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

    wctl run-pytest tests/weppcloud/routes --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine* --maxfail=1
    wctl run-pytest tests/rq --maxfail=1
    wctl run-pytest tests --maxfail=1

    cp /tmp/broad_allow_current.json docs/work-packages/20260223_bare_exception_zero/artifacts/postfix_broad_exceptions.json

## Validation and Acceptance

Acceptance criteria were met:
- Global `bare except` stayed at zero.
- Target unresolved allowlist-aware findings are zero.
- Remaining in-scope broad catches are boundary-classified and allowlisted per handler.
- Required targeted and full-suite tests passed.
- Package docs, tracker, project tracker, and root AGENTS pointer were synchronized at close.

## Idempotence and Recovery

Scanner/doc-lint commands are idempotent. Final allowlist generation is reproducible from current `--no-allowlist` scanner output to correct line drift after code edits.

## Artifacts and Notes

- `docs/work-packages/20260223_bare_exception_zero/artifacts/baseline_broad_exceptions.json`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/postfix_broad_exceptions.json`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/target_module_classification.md`
- `docs/work-packages/20260223_bare_exception_zero/artifacts/final_validation_summary.md`

## Interfaces and Dependencies

- `tools/check_broad_exceptions.py` (`--json`, `--no-allowlist`, `--enforce-changed`)
- `docs/standards/broad-exception-boundary-allowlist.md`
- `docs/schemas/rq-response-contract.md`
- `wepppy/weppcloud/AGENTS.md`, `wepppy/microservices/rq_engine/AGENTS.md`, root `AGENTS.md`, `tests/AGENTS.md`

---

Revision note (2026-02-23 05:59Z): Marked all milestones complete, captured final gate/test outcomes, documented regression fixes and allowlist drift handling, and closed Phase 2.
