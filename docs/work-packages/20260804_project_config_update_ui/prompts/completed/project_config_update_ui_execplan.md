# Deliver the accessible project config update UI

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a run page checks update availability without mutation, shows
an authenticated user any config digest warning, and lets an authorized owner
or administrator review every missing value before explicitly enqueueing the
WP08 merge-only job. Keyboard and assistive-technology users receive equivalent
notice, modal, focus, status, and error behavior.

## Progress

- [x] (2026-08-26) Read the canonical contract, roadmap, WP08 surface, UI/a11y
  standards, and subsystem instructions.
- [x] (2026-08-26) Scaffold the package and record compatibility/security plan.
- [x] (2026-08-26) Add complete read-only availability state and digest warning.
- [x] (2026-08-26) Add semantic header/modal markup and dedicated controller behavior.
- [x] (2026-08-26) Add regression and accessibility evidence.
- [x] (2026-08-26) Run gates, review, archive, close, and commit.

## Surprises & Discoveries

- WP08's availability route returned only `available`, while section 5.1 also
  requires the opaque preview identity and WP09 needs authenticated digest
  warning state. WP09 will add those read-only fields without changing mutation
  behavior.

## Decision Log

- Decision: use a dedicated `project_config_update.js` controller rather than
  expanding the already broad Project controller.
  Rationale: the new state machine has a narrow DOM/API boundary and can be
  tested independently while still sharing WCDom, WCHttp, ModalManager, and
  StatusStream/job polling primitives.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

Delivered the progressive, default-off run-header update experience over WP08.
The backend now returns complete read-only availability and digest state and
maps nested Omni identities to top-level config authority. The UI provides a
safe complete preview, explicit merge-only apply, canonical job/error state,
and accessible modal/live-region behavior. Focused, frontend, contract,
isolation, documentation, and full Python gates passed. The axe browser run had
three unrelated fixture/environment failures documented in validation evidence;
its five successful page groups reported zero violations.

## Context and Orientation

The shared run header is
`wepppy/weppcloud/templates/header/_run_header_fixed.htm`; run pages load the
generated controller bundle. WP08 exposes availability, preview, and apply
under `/rq-engine/api/runs/{runid}/{config}/project-config/`. The controller
will mint the normal run-scoped rq-engine bearer token through WCHttp.

## Plan of Work

First extend the availability response with the opaque preview identity and a
secret-safe digest warning derived from the actual project artifacts. Preserve
its read-only and run-read authorization contract. Then add declarative header
notice/warning and a labelled modal containing a complete additions table,
version-1 merge-only explanation, explicit apply, status, and refresh actions.

Implement one page-load check, preview retrieval only after the user opens the
panel, exact apply submission, canonical error-code mapping, job polling, and a
fresh availability/preview after completion or stale conflict. Ensure every
dynamic state is announced and focus moves predictably for errors and modal
transitions. Finish with JS/template/backend tests, bundle rebuild, accessibility
checks, documentation, security review, and full gates.

## Validation and Acceptance

Jest must prove one availability request, no automatic preview/apply, complete
safe text rendering, exact apply body, duplicate-submit prevention, job status,
and actionable canonical errors. Template tests must prove dialog naming,
descriptions, live regions, table headers, and hidden-by-default notices.
Backend tests must prove preview identity/warning fields and read-only behavior.

## Idempotence and Recovery

Repeated initialization is guarded per DOM root. Page load remains read-only.
Apply is disabled while pending and WP08 revalidates the opaque preview under
the project lock. A reload starts from server state; no browser persistence is
required.

## Artifacts and Notes

Record automated and focused keyboard/focus evidence under `artifacts/`.

## Interfaces and Dependencies

No new dependency. Reuse WCDom, WCHttp session-token requests, ModalManager,
the canonical rq-engine job-status endpoint, and existing UI foundation styles.

Plan revision note (2026-08-26): initial executable plan.
