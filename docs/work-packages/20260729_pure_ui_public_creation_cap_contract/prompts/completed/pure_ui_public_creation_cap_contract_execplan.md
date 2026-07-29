# Verify public creation and CAPTCHA contracts

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` current.

## Purpose / Big Picture

Anonymous users see only permitted interfaces, complete one section-owned CAP
challenge, and submit the exact chosen configuration once. Authenticated users
retain permitted launch identity without anonymous CAP gating. Regional and
authenticated creation pages preserve their exact producer-owned payloads,
while failures remain visible and fail closed.

## Progress

- [x] (2026-07-29 UTC) Scaffolded SURF-01 and ratified concise intent.
- [x] (2026-07-29 UTC) Traced canonical registry/CSRF contracts, templates,
  CAP client, route producers, verification helper, and existing tests.
- [x] (2026-07-29 UTC) Added actual-render and executable production-client
  regressions.
- [x] (2026-07-29 UTC) Ran focused registry, CAP, route, and
  creation-handoff evidence.
- [x] (2026-07-29 UTC) Confirmed no production contradiction required a patch
  or generated-bundle rebuild.
- [x] (2026-07-29 UTC) Completed broad gates, security review, records, and
  closure.

## Surprises & Discoveries

- Observation: JOH is registered in the host family but has no creation form.
  Evidence: Its template is presentation/iframe content; Portland, Seattle, and
  SPU contain the fixed regional POST forms.

- Observation: Existing interfaces rendering is strong for registry maturity
  and visibility but the production `interfaces_captcha.js` has no direct
  executable suite.
  Evidence: The audit register names a direct CAPTCHA gap; current Jest covers
  the separate Flask-Security CAP script.

- Observation: The authenticated create-index route is login-required, so its
  template's anonymous CAP branch is defensive rather than a reachable public
  surface.
  Evidence: Route decoration and actual authenticated rendering.

- Observation: Repeated interfaces-client execution replaces each launch
  button's `onclick` owner; repeated widget callbacks only repeat the same
  token assignment.
  Evidence: The direct repeated-execution Jest regression performs one native
  form submission.

## Decision Log

- Decision: Preserve the existing registry-informed launch and CAP behavior
  without changing metadata, minimum roles, payloads, or defaults.
  Rationale: SURF-01 is a conformance audit; the feature registry and CSRF
  schema are already canonical.
  Date/Author: 2026-07-29 / Codex with operator authority.

- Decision: Use direct tests to determine whether repeated client execution is
  safe before considering any production patch.
  Rationale: The registered package explicitly owns duplicate-handler
  safeguards, and implementation inspection alone cannot prove event behavior.
  Date/Author: 2026-07-29 / Codex.

## Outcomes & Retrospective

SURF-01 closed without a production repair. Exact renders now cover anonymous
registry launch forms, the authenticated catalog, Portland, Seattle, SPU, JOH,
and hostile CAP-gate values. Seven direct Jest tests execute section-owned
solve/block/submit/repeat/failure behavior. Existing route, CAP/session,
logging, and rq-engine creation tests remain green. The dedicated high-impact
security review passed with no unresolved finding. Frontend lint and all 101
suites/714 tests passed; repository Python passed 5,548 tests with 58 skips.

## Context and Orientation

`interfaces.htm` renders registry-filtered cards and anonymous CAP sections.
`interfaces_captcha.js` copies a solved widget token only to forms in its
section and owns launch clicks. `weppcloud_site.py` supplies registry/CAP
context and verifies CAP tokens. `create_index.htm` is an authenticated
configuration catalog. `locations.py` supplies shared regional CAP context to
four location templates; only Portland, Seattle, and SPU create runs.

## Plan of Work

Render all producer templates with anonymous, authenticated, registry-filtered,
and hostile values. Assert exact risk-bearing form fields and asset URLs.
Execute the production CAP client under Jest/jsdom for section isolation,
blocked and allowed submission, repeated load, absent DOM, empty solve, and
missing-prompt cases. Retain inspected route tests for registry filtering, CAP
verification, create-index rows, regional context, and rq-engine creation
handoff. If a regression exposes a mismatch, patch the smallest existing
function and rebuild the generated bundle.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py \
      tests/weppcloud/routes/test_weppcloud_site_interfaces_route.py \
      tests/weppcloud/routes/test_cap_verify.py \
      tests/weppcloud/test_auth_cap_captcha.py --maxfail=1
    wctl run-npm test -- interfaces_captcha
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260729_pure_ui_public_creation_cap_contract
    wctl doc-lint --path docs/work-packages/20260716_pure_ui_contract_standardization_c
    git diff --check

Build only if controller source changes. No RQ graph, stub, dependency, or ADR
gate applies unless implementation scope changes.

## Validation and Acceptance

Acceptance requires actual-render evidence across every registered host,
executable production-client evidence for solve/block/submit/repeat/failure
behavior, and retained downstream evidence for registry visibility, CAP
verification/session, exact creation payload, and safe errors. Focused and
broad applicable gates pass, or a proven unrelated failure is recorded.

## Idempotence and Recovery

All render, Jest, pytest, build, and lint commands are safe to rerun. Tests use
controlled browser globals and Flask clients. A missing or rejected CAP token
does not submit or create a run; retry requires a fresh valid widget result.

## Interfaces and Dependencies

Preserve `data-cap-section`, `data-cap-required`, `data-cap-token`,
`data-run-action`, CAP asset/site-key configuration, exact registry config ids,
override JSON, POST action, verification response, and native form submission.
Add no dependency, route, compatibility alias, fallback, or parameter default.

## Revision Notes

2026-07-29: Created from explicit operator direction to scaffold and execute
SURF-01.

2026-07-29: Completed with regression-only changes, a contract evidence
matrix, and a passing dedicated security review.
