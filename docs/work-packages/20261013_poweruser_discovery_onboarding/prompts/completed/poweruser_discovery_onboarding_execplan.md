# Make PowerUser discovery and onboarding useful from Runs

Completed 2026-10-13: this is the PUUX-01 ExecPlan, maintained under docs/prompt_templates/codex_exec_plans.md. Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective are living sections. The operator authorized execution on 2026-10-13. Execute this package on master; no production deployment is included.

## Purpose / Big Picture

An ordinary signed-in user should discover advanced capabilities on Runs, understand whether they need them, enable PowerUser access with the existing two acknowledgments, and immediately reach a useful destination. Existing PowerUser/Admin/Root users should not see an acquisition notice. The PowerUser Panel remains restricted, including its report-page trigger. Internal feature approval stays separate from PowerUser status.

## Progress

- [x] (2026-10-13 17:42 UTC) Static source review and operator Runs-page decision captured in package and contract-decision artifact.
- [x] (2026-10-13 17:42 UTC) Scaffold and independent-review gates prepared; no runtime files changed.
- [x] PUUX-01A bounded GL Dashboard move implemented after checkpoint 5528224f6; 229 existing tests and 20 rendered cases pass. Before M0, no broader onboarding work had been executed.
- [x] M0: amend current contracts, complete two independent contract reviews and commit the standalone checkpoint.
- [x] M1: implement Runs discovery and complete Profile activation journey.
- [x] M2: improve internal-access presentation, panel orientation and documentation; align report trigger.
- [x] M3: focused checks, segmented broad coverage, real Forest evidence, cleanup and final independent reviews complete.

## Surprises & Discoveries

At initial inspection, the active Runs template was wepppy/weppcloud/templates/user/runs2.html, rendered by routes/user.py:runs. Main run navigation and panel markup require PowerUser, Admin or Root, but templates/reports/_base_report.htm emitted the panel trigger unconditionally. A Dev role alone does not permit the panel, even though Dev can use Config Builder and API tokens. Profile's feature_access.js also handles internal acknowledgment and membership administration; changing the common success branch carelessly would affect those workflows.

Live guide readback found that usersum requires both manifest and navigation registration, plus rebuilding its generated index. The guide is registered in Advanced and Operations; protected navigation is unchanged. Screenshot review found the generic panel minimum height made the discovery notice unnecessarily tall; the existing compact notice component resolves this without global CSS changes.

## Decision Log

2026-10-13 UTC, operator: GL Dashboard is a normal project-viewing destination. PUUX-01A moves its link from the restricted panel to More on run/report pages under its own reviewed checkpoint. Exclude it from PowerUser benefit copy. This bounded amendment may execute now while broader onboarding remains scaffolded.

2026-10-13 17:42 UTC, operator/Codex: use a compact notice on Runs, not a new global feature catalog or unrestricted panel. Hide acquisition messaging for the existing three-role panel audience. This resolves the discovery gap with a bounded presentation change. Show the notice for Dev-only users but describe benefits without implying they lack every advanced tool.

2026-10-13 17:42 UTC, Codex implementation proposal: use fixed server-generated completion links and normal Profile reload, not arbitrary return URLs, a new endpoint or persistent onboarding state. Preserve voluntary internal acknowledgment but make it secondary when there are no memberships. Preserve “PowerUser Panel” as the tool name, rather than introducing another synonym.

## Outcomes & Retrospective

Contract checkpoint 2f9f94443 and M0–M3 are complete. Reviewed candidate 3df2ec482 retains runtime ed80608fe. Forest activation, durable grant, guide/panel readback, served-asset parity and disposable-account cleanup pass. Broad coverage totals 10,723 distinct passes/126 skips across segments; frontend totals 980 passes. Two old viewer-context fixtures were corrected. Existing JWT order sensitivity, catalog latency variability and climate-test lint are documented rather than hidden. Delivery requires rebuilding the generated usersum catalog. Independent reviews approve the bounded change; panel desktop whitespace is a nonblocking layout follow-up. Production deployment has not occurred. Static evidence supports a report-trigger inconsistency but is not proof of an authorization bypass or measured user failure. Final human usability claims require observed users; browser conformance alone establishes the rendered interaction behavior.

## Context and Orientation

Work on the existing master branch in /home/workdir/wepppy; container path is /workdir/wepppy. Starting revision is a8de37a0db1e678e76eefb36a991514036fb9a9c. Read root and applicable nested AGENTS.md before editing. The intended authority is docs/schemas/feature-access-governance-contract.md plus shared UI contracts and feature-registry specifications. A work package records execution, not durable policy after closure.

The Runs template contains the page heading followed by a panel with table/map views and search. Put the informational notice between the header and panel so it survives empty data and view changes. Check current_user, not any admin-selected owner. Show only for authenticated viewers lacking PowerUser/Admin/Root. No new dismissal storage, toast, modal or role request on page load is needed.

Profile renders templates/user/_poweruser_access.html then _internal_access.html. routes/user.py:poweruser_onboarding delegates to utils/feature_access_web.py:approve_poweruser. The existing POST /profile/poweruser accepts needs_poweruser, accepts_training and statement_version; the account and role are server-owned. Keep this API and atomic role/acceptance semantics. static/js/feature_access.js presents pending, success and failure states. Replace only the PowerUser completion branch, preserving membership and internal acknowledgment behavior.

The panel lives in templates/controls/poweruser_panel.htm; run and report headers supply triggers. Its task presentation can change, but mutation handlers and backend authorization do not. User docs live under routes/usersum/weppcloud/. Add poweruser-getting-started.md, update user-guide.md and clearing-locks.md, and retain implementation-documentation links as secondary help. Read that directory's AGENTS before edits; do not modify generated docs_index.json.

## Plan of Work

M0 — Inspect current contracts and reconcile the package's exact intended presentation rules in docs/schemas/feature-access-governance-contract.md and an applicable contract under docs/ui-docs/contracts/. If no presentation contract covers this journey, create one in that canonical directory. Keep the training statement text/version unchanged unless an explicit versioning decision is recorded; explanatory copy around it is sufficient. Record base SHA, authority, normative changes, unchanged permissions, all valid states and input cases in artifacts/2026-10-13_contract_decision.md. Obtain two independent read-only correctness and security contract reviews as required by docs/standards/contract-first-change-standard.md. Disposition findings and commit the accepted contract checkpoint separately before runtime edits. Record its SHA in tracker.md. Do not treat pending artifact templates as approval.

M1 — Add the notice to runs2.html with a Profile section anchor and ordinary page semantics, not an alert that interrupts screen readers. Keep it visible on empty and populated accounts and table/map views. Add capability examples and immediate-activation wording above the unchanged two-answer form. Use Explore PowerUser access for discovery and Enable PowerUser access for submission. Successful activation must require a valid response confirming granted state and the presented statement version; use the current response contract and preserve retry/idempotence. Then refresh Profile at the PowerUser section so Roles, token availability and active state agree. The active view offers Config Builder, Runs and the guide. Loading an unavailable store, an expired session, or a malformed response must never claim success. Keep legacy role holders active without demanding a new acceptance. Add tests before changed controller behavior and prove the prior missing journey fails the new assertions.

M2 — Make the internal section concise for users with no memberships, with an explicit expandable route to its explanation and voluntary acknowledgment. Show pending acknowledgment clearly for users whose actual memberships require it; do not infer a grant from either statement. Reorganize panel presentation around inspecting inputs/outputs, analyzing results and troubleshooting, keeping raw state/logs under technical detail. Preserve resource-specific conditions, read-only behavior and all action handlers. Describe Clear Locks and link its safe-use guidance without introducing a new operational policy. Apply the existing role guard to the report header trigger. Keep dialog, trigger and documentation naming consistent. Write the getting-started guide with examples, access boundaries, project prerequisites, and a short first task. Update lock recovery to explain self-service instead of reflexively sending users to an administrator.

M3 — Run focused regression suites, frontend gates, required broad Python sanity and changed-doc lint. Rebuild actual generated controller assets if controller sources change; direct static/js/feature_access.js changes do not justify inventing a second build pipeline. Exercise the served Forest pages with a disposable ordinary account and a populated disposable project. Observe notice, keyboard interaction, actual authenticated grant, durable acceptance/role readback, Profile refresh, destination access, Runs notice disappearance and denied internal actions without membership. Also verify legacy PowerUser, Admin/Root and Dev-only states. Retain nonsecret receipts and screenshots bound to the candidate revision. Obtain final independent correctness/UX and security reviews, close medium/high findings and update package/tracker/plan. Record deployment separately; do not operate wepp.cloud under this scaffold.

## Concrete Steps

Run commands from /home/workdir/wepppy. Start with git status --short and read the scoped AGENTS files. The initial focused server set is:

    wctl run-pytest tests/weppcloud/routes/test_user_runs_admin_scope.py tests/weppcloud/routes/test_user_profile_contract.py tests/weppcloud/routes/test_feature_access_routes.py tests/weppcloud/routes/test_user_profile_token.py

Add or extend role-rendering tests for ordinary run and shared report headers in the nearest existing suite. Include negative tests for an unauthorized trigger and preserved API denial, and positive tests for legacy/empty states. Existing relevant JS suites are controllers_js/__tests__/feature_access.test.js, user_profile_inline.test.js and poweruser_panel_inline.test.js.

    wctl run-npm test -- --runInBand
    wctl run-npm lint
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20261013_poweruser_discovery_onboarding

Lint each amended canonical/user document too. If controllers_js files changed, run:

    wctl exec weppcloud python /workdir/wepppy/wepppy/weppcloud/controllers_js/build_controllers_js.py

Read static-src/tests/smoke/AGENTS.md and reuse the existing feature-access.spec.js flow for the Forest browser checks. Do not self-promote a production account or strip live permissions to create a test state. If a dedicated ordinary account is required, follow the existing fixture/account workflow and record cleanup. Use wctl wrappers for the dev stack and record a bounded refresh only if needed to load changes. Expected results are passing scoped checks and the observable journey below; record actual counts and unrelated failures rather than promising a clean gate without evidence.

## Validation and Acceptance

Assess runtime state separately from request combinations using the contract-decision matrices. Anonymous requests preserve authentication. An ordinary account with zero runs sees the notice without creating a project; populated accounts see it without losing table/map search and selection state. A Dev-only viewer remains correctly distinguished from panel-authorized roles. Existing PowerUser/Admin/Root viewers never see the notice. Other-user catalog selection never changes the viewer's access message.

A valid real POST with both answers true and current statement grants the current account once. Fresh Profile shows active status and useful destinations, and fresh Runs omits the notice. Duplicate submissions and lost-response retries do not manufacture a second acceptance or a different role. False/missing answers, stale version, invalid CSRF, expired session, store failure and malformed success cannot produce a false success. Existing PowerUsers without acceptance retain access and reassuring legacy text. Internal groups and private-resource protection remain unchanged. No ordinary user receives panel markup or a dead report trigger.

Keyboard focus must remain meaningful across submission and reload; success is announced or clearly reached, and links have meaningful names. Check narrow and desktop layouts without running an unsolicited full accessibility audit. If human participants are available, ask them to discover a concrete tool, explain the scope of access, activate and resume without coaching. Record completion, wrong turns and requests for help as observations, not invented metrics. Human study availability does not replace or block the required functional/browser gate.

## Idempotence and Recovery

Documentation and renders are reversible. Role grants use the existing idempotent transaction; do not undo legitimate grants during code rollback. Roll back paired presentation assets and templates if needed, retaining acceptance history. Do not add a schema migration, preference key or arbitrary navigation parameter. A refresh failure must allow safe retry and reveal current server state. Separate any later production rollout from Forest validation and inspect scripts/deploy-production.sh before proposing it.

## Artifacts and Notes

Retain contract decisions/reviews, final correctness/security artifacts, nonsecret test receipts and served-page evidence under this package's artifacts directory. Review stubs start pending. Native/model output evidence is not applicable because the task changes discovery and onboarding, not scientific artifacts. Durable account readback and rendered completion are applicable and must be real. Keep PROJECT_TRACKER.md, tracker.md and this plan synchronized. Initial scaffold revision: 2026-10-13 17:42 UTC, based on the operator's Runs-page proposal and the static usability findings.

## Interfaces and Dependencies

Reuse the existing Flask routes, server-generated url_for links, Pure UI macros and feature_access.js handler. Preserve POST /profile/poweruser payload and response contracts, statement versioning, current-user identity, CSRF and duplicate handling. No queue, dependency, public API or privilege expansion. Profile section anchors and presentation selectors may be added under the reviewed presentation contract; they do not become authorization checks.
