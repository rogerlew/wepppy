# Verify the Pure UI README viewer and editor contract

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

An authorized project owner or administrator can view and safely edit the
current run's README, preview Markdown, survive ordinary save errors, and be
stopped when another tab owns the editor session. A readonly run remains
view-only. The behavior is observable through direct rendering, execution of
the actual inline script, route calls, persisted files, and reload.

## Progress

- [x] (2026-07-28 UTC) Scaffolded SURF-09 and ratified concise intent.
- [x] (2026-07-28 UTC) Traced the viewer/editor hosts, templates, CSRF transport, Redis session
  state, filesystem write, Markdown renderer, and existing tests.
- [x] (2026-07-28 UTC) Added direct render, inline-client, route, concurrency, persistence, and
  reload evidence.
- [x] (2026-07-28 UTC) Repaired only regressions that prove a contradiction of the ratified
  contract.
- [x] (2026-07-28 UTC) Completed security review, focused/broad validation, records, commit, and
  clean closeout.

## Surprises & Discoveries

- Observation: The editor currently has almost no direct behavioral coverage.
  Evidence: repository search finds only a static stale-bundle wiring assertion.

- Observation: A streamed output-size check does not bound the intermediate
  value created by a Jinja expression.
  Evidence: independent review reproduced multi-megabyte single chunks from
  `%`, `center`, and `join`; the renderer now rejects every expression node
  except variable/attribute/constant-key interpolation before evaluation.

- Observation: Route aliases and configuration aliases can address the same
  active root.
  Evidence: lock keys now derive from the resolved active-root path, while
  ownership resolves composite Omni run identifiers to the parent run.

## Decision Log

- Decision: The fixed `README.md` within `RunContext.active_root` is the entire
  writable filesystem boundary.
  Rationale: SURF-09 audits an existing project-note surface, not a general file
  editor.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: Owner/admin and readonly checks must protect mutation server-side.
  Rationale: UI visibility cannot establish authorization or data-integrity
  guarantees.
  Date/Author: 2026-07-28 / Codex with operator authority.

- Decision: README Jinja is an interpolation facility, not a programming
  surface.
  Rationale: literal Markdown plus run metadata satisfies the shipped template;
  operators, filters, calls, and control structures create unnecessary
  resource-exhaustion and behavior risk.
  Date/Author: 2026-07-28 / Codex after independent security review.

- Decision: A 1 MiB UTF-8 README and rendered-output limit, with 4 KiB of JSON
  envelope allowance, is the accepted parameter.
  Rationale: ADR-0030 records the operator decision, tradeoffs, and rollback.
  Date/Author: 2026-07-28 / Codex with operator authority.

## Outcomes & Retrospective

SURF-09 now has direct host rendering, execution of the real inline editor,
route/Redis/filesystem/reload regressions, and a passing independent security
review. Production repairs enforce owner/admin and readonly authority, bind
locks to the active root, serialize and revision-order saves, validate UUIDs
and bodies, confine atomic writes, avoid read-side file creation, bound source,
request, rendered Markdown, and HTML sizes, and restrict Jinja to bounded
interpolation. The client now handles non-success responses, invalidation, and
partial Ron updates. Focused validation passed 186 Python tests and 7 Jest
tests; all 93 frontend suites and 687 tests plus lint passed. The broad Python
gate reached 2,462 passes and 40 skips before the known unrelated GridMET
`_FakeUnits.degC` fixture failure. Documentation lint, broad-exception
enforcement, independent security review, and `git diff --check` passed.

## Context and Orientation

`readme_md.py` loads a run through `RunContext`, fixes the target name to
`README.md`, renders Markdown through a sandboxed Jinja environment and
`cmarkgfm`, stores editor ownership in the README Redis database, and exposes
viewer, editor, raw, preview, and save routes. `readme_editor.htm` contains the
actual debounce, preview, save, lock polling, title update, and invalidation
client. `readme_view.htm` presents rendered content and an Edit action.

## Plan of Work

Render both templates with hostile and ordinary values. Execute the production
inline editor script with deterministic DOM, fetch, timers, keyboard,
visibility, and reload doubles. Build a hermetic Flask route fixture around the
real blueprint and a temporary active run root. Prove authorization,
owner/admin and readonly decisions, fixed-path persistence, stale-tab rejection,
safe preview/view output, and reload. For each proven mismatch, retain the
failing regression and apply only the smallest compatible repair.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_readme_md.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm test -- readme_editor_inline
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260728_pure_ui_readme_editor_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Run a controller build only if controller source changes. Run the RQ graph gate
only if queue wiring changes.

## Validation and Acceptance

Acceptance requires rendered and executable proof of every risk-bearing
boundary, server-side owner/admin and readonly enforcement, a fixed and
confined file target, safe preview/view output, stale-tab denial before write,
successful persistence/reload, and no unresolved high or medium security
findings for an attack-surface patch. Focused, frontend, documentation, and
applicable broad gates pass except a proven unrelated baseline failure recorded
exactly.

## Idempotence and Recovery

Tests use temporary directories, fake Redis state, deterministic timers, and
local Flask clients. Repeated execution does not mutate a real run. A failed
edit is retried by rerunning the focused command; no destructive cleanup is
required.

## Artifacts and Notes

The field matrix is
`docs/work-packages/20260728_pure_ui_readme_editor_contract/artifacts/field_matrix.md`.
Record a security review artifact if production repairs change the authenticated
mutation, path, concurrency, or rendered-output surface.

## Interfaces and Dependencies

The package retains Flask, `RunContext`, the existing shared CSRF bootstrap,
Redis README state, `SandboxedEnvironment`, `cmarkgfm`, and fixed
`README_FILENAME`. It adds no dependency, endpoint family, queue edge, schema,
or arbitrary path input.
