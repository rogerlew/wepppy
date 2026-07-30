# Verify the Command Bar contract

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

Run viewers can use one predictable keyboard palette for navigation and
diagnostics, while authenticated operators can perform only the mutations their
role permits. Token and agent features remain run-confined, secret-safe,
CSRF-protected, and resilient to hostile remote content.

## Progress

- [x] (2026-07-29 UTC) Scaffolded SHR-06 and ratified concise intent.
- [x] (2026-07-29 UTC) Traced template hosts, client commands, Project and agent
  consumers, Flask routes, shared transports, StatusStream, and current tests.
- [x] (2026-07-29 UTC) Added actual-render, direct-client, route, and
  hostile-content regressions.
- [x] (2026-07-29 UTC) Repaired only reproduced authority, request, lifecycle,
  and hostile-content contradictions.
- [x] (2026-07-29 UTC) Passed focused Python and JavaScript evidence, frontend
  lint and all 104 suites/739 tests, RQ graph, stub, isolation, exception,
  quality-observability, docs, and diff gates; completed security review.
- [x] (2026-07-29 UTC) Reconciled child and umbrella records and closed SHR-06.

## Surprises & Discoveries

- Observation: Runtime-directory lock clearing and NoDb-cache clearing are
  destructive GET routes available after ordinary run authorization.
  Evidence: `command_bar.py`, `project_bp.py`, and their client callers use GET
  without a privileged role decorator.

- Observation: Raw Command Bar mutations do not consistently attach CSRF.
  Evidence: MCP mint and Wojak POST/DELETE calls construct headers directly,
  while the shared CSRF contract requires a token for browser-session mutation.

- Observation: Remote Markdown sanitization removes elements and event
  handlers, but does not reject unsafe link URL schemes.
  Evidence: `AgentChat.sanitizeHtml` retains arbitrary `href` values.

- Observation: Route line movement changed the generated RQ graph artifact
  without changing an enqueue edge.
  Evidence: regeneration retained 144 edges and `wctl check-rq-graph` passed.

## Decision Log

- Decision: Ratify safe viewer commands separately from privileged mutations.
  Rationale: The Command Bar is included in viewer/report hosts, while recovery,
  token, and chat actions have independent security boundaries.
  Date/Author: 2026-07-29 / Codex with operator authority.

- Decision: Preserve the current command vocabulary and service protocols.
  Rationale: This is contract standardization, not a UX or agent redesign.
  Date/Author: 2026-07-29 / Codex.

- Decision: Return canonical JSON 403 errors for Command Bar authority
  failures.
  Rationale: The client expects JSON failures and must not receive an HTML
  login or role page for an in-palette operation.
  Date/Author: 2026-07-29 / Codex.

- Decision: Treat Project recovery and Wojak agent routes as finite consumers.
  Rationale: They complete Command Bar mutations without transferring package
  ownership of those subsystems.
  Date/Author: 2026-07-29 / Codex.

## Outcomes & Retrospective

SHR-06 closed with one initialized Command Bar owner, stable keyboard/history
behavior, exact CSRF-protected requests, privileged POST-only recovery,
authenticated run-confined MCP issuance, encoded agent lifecycle and stream
teardown, visible failures, and hostile Markdown confinement.

Direct production-JavaScript evidence exercises the complete command boundary.
Focused Python passed 198 tests and focused shared JavaScript passed 5 suites
and 40 tests. Frontend lint and all 104 suites/739 tests passed. Full repository
Python passed 5,570 tests and 12 subtests with 58 skips. RQ graph, stub,
isolation, exception, quality-observability, docs, and diff gates passed. The
security review passed with no unresolved high or medium finding.

## Context and Orientation

`wepppy/weppcloud/routes/command_bar/templates/command-bar.htm` renders the
palette and loads `static/command-bar.js`. The client derives run/config from
the URL, dispatches local and network commands, renders Query Engine tokens,
and manages Wojak chat through `StatusStream`. Command-specific Flask routes
live in `command_bar.py`; finite mutation consumers also live in
`nodb_api/project_bp.py` and `agent.py`.

## Plan of Work

Render actual run, report, Browse, and README hosts and prove one initialized
palette. Execute the production JavaScript in jsdom for keyboard/history,
navigation, exact request, error, token, agent, stream teardown, repeated-init,
and hostile Markdown cases. Add Flask tests for safe diagnostics, privileged
recovery, authenticated MCP minting, claims/redaction, and agent authorization.
Patch only failures against the ratified contract and update developer docs.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-npm test -- command_bar
    wctl run-pytest tests/weppcloud/routes/test_command_bar_mcp_token.py \
      tests/weppcloud/routes/test_project_bp.py \
      tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path \
      docs/work-packages/20260729_pure_ui_command_bar_contract
    wctl doc-lint --path \
      docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

## Validation and Acceptance

Acceptance requires executable evidence for one owner, keyboard/parser/history
behavior, exact safe and mutating requests, visible failures, privileged
recovery, authenticated and redacted MCP minting, agent lifecycle/teardown, and
hostile Markdown confinement. Focused and broad gates must pass.

## Idempotence and Recovery

Rendering and tests are safe to repeat. Direct-client tests isolate globals,
listeners, storage, fetch, clipboard, and StatusStream. Route repairs are
additive denials and retain authorized behavior.

## Interfaces and Dependencies

Preserve `[data-command-bar]`, `window.initializeCommandBar`,
`window.CommandBar`, existing command names, `/command_bar/*`, `/agent/chat`,
MCP `token_class`, scopes/audience/default TTL, Redis channel names, and
`StatusStream.attach/disconnect`.

## Revision Notes

2026-07-29: Created from explicit operator direction to scaffold and execute
SHR-06.
