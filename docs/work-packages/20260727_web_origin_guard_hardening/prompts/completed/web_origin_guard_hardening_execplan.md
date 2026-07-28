# Harden browser-origin guards and shared diagnostics boundaries

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. The `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`
sections must remain current.

## Purpose / Big Picture

WEPPcloud browser requests should be accepted or rejected consistently across
the Flask application, rq-engine, and query-engine, independent of where TLS
terminates. Resetting browser state must delete only WEPPcloud-owned cookies,
and copied diagnostics JSON must contain only known-safe fields and messages.

The observable restoration is a query-engine bandwidth upload with
`Sec-Fetch-Site: same-origin`, an HTTPS `Origin`, and an internally reconstructed
HTTP request scheme returning success instead of `403 cross_origin_blocked`.
Conflicting origins and cross-site requests remain rejected on every surface.

## Progress

- [x] (2026-07-27 23:40 UTC) Scoped the four implementation work packages.
- [x] (2026-07-28 00:00 UTC) Added this umbrella ExecPlan and a contract-first
  checkpoint phase to make the package executable.
- [x] (2026-07-28 00:50 UTC) Execute WP00: register the bounded remediation, finalize the contract
  decision and canonical contract amendments, obtain two independent reviews,
  disposition findings, and commit standalone checkpoint ancestor
  `736198ce8a4b68b83a9c77860a52da574f2cc98d`.
- [x] (2026-07-28) Execute WP01: conform all three same-origin guards and add focused tests.
- [x] (2026-07-28) Execute WP02: restrict reset cookie deletion to owned cookie tuples.
- [x] (2026-07-28) Execute WP03: make copied diagnostics reports allowlist-based.
- [x] (2026-07-28) Execute WP04: run the shared same-origin and CSRF matrix across all three
  surfaces.
- [x] (2026-07-28) Run focused and broad validation, complete independent final security and
  correctness reviews, disposition findings, and close the package.

## Surprises & Discoveries

- Observation: The original scaffold described a new normative browser-origin
  contract but omitted the mandatory pre-implementation checkpoint.
  Evidence: repository revision `4c574dcd6` contains no contract-decision
  artifact, governance registration, checkpoint reviews, or ancestor revision.
- Observation: query-engine treats a missing `Origin` as allowed while the
  Flask and rq-engine helpers require a valid `Referer` when `Origin` is absent.
  Evidence: `_is_same_origin_request` returns `True` for an empty origin in
  `wepppy/query_engine/app/server.py`; the other predicates return `False` when
  both browser signals are absent. WP00 must decide this divergence normatively.
- Observation: the monolithic Python suite has a pre-existing test-isolation
  defect: the Daymet client test replaces `cf_units.units` process-wide, causing
  a later GridMET test to fail because its fake object lacks `degC`.
  Evidence: the monolithic run stopped at 44% with 2450 passed and one failure;
  the GridMET test passes alone, and the suite passes when the Daymet file is
  run separately.

## Decision Log

- Decision: Add WP00 as a hard dependency of every implementation work package.
  Rationale: `docs/standards/contract-first-change-standard.md` forbids
  production edits until the reviewed contract checkpoint is a standalone
  ancestor commit.
  Date/Author: 2026-07-28, Codex.
- Decision: Treat the user's instruction to execute the package as approval of
  the package objective, but require WP00 to record the exact normative matrix
  and the operator's approval of any resolved ambiguity.
  Rationale: approval of a goal does not silently resolve the current missing-
  signal behavior divergence or establish bounded-remediation authority.
  Date/Author: 2026-07-28, Codex.

## Outcomes & Retrospective

The package is complete. All three guards implement the reviewed decision
matrix, browser-state reset deletes only configured WEPPcloud cookie tuples,
and copied diagnostics reports are constructed from a fixed allowlist. Shared
vectors and surface-specific security tests cover the restored and rejected
paths. The checkpoint is sealed by ancestor
`736198ce8a4b68b83a9c77860a52da574f2cc98d`; independent final correctness and
security rereviews both passed with zero remaining findings. Focused Python and
all JavaScript gates passed. Broad Python validation was split only to isolate
the unrelated Daymet process-pollution defect recorded above: the main
partition passed 5347 tests with 58 skipped, and the isolated Daymet partition
passed 2 tests.

## Context and Orientation

Three services independently decide whether a browser request is same-origin:
`wepppy/weppcloud/routes/weppcloud_site.py` protects Flask authentication
endpoints, `wepppy/microservices/rq_engine/session_routes.py` protects
cookie-authenticated rq-engine routes, and
`wepppy/query_engine/app/server.py` protects diagnostic bandwidth endpoints.
An origin is the normalized scheme, host, and port of a URL. A conflicting
`Origin` is one that does not exactly match an allowed normalized origin.

`wepppy/weppcloud/routes/weppcloud_site.py` also clears browser cookies during
reset. `wepppy/weppcloud/static/js/diagnostics/report.js` constructs JSON meant
to be safe to paste into public bug reports.

This is a UI-coupled, high-security remediation governed by
`docs/standards/contract-first-change-standard.md`. Before implementation, WP00
must register a new bounded-remediation ID and governance milestone in the Pure
UI child-package register, amend the canonical CSRF contract and diagnostics
specification, obtain two independent read-only reviews, resolve all findings,
and commit those documents alone as a standalone ancestor.

## Plan of Work

First execute `../completed/wp00_contract_checkpoint.prompt.md`. Do not edit production code
or implementation tests during WP00. Record the resulting ancestor revision in
this plan and the tracker.

Then execute WP01. Apply the reviewed decision order identically across all
three guards while using each framework's proxy-normalized request properties
and explicit configured public origin. Do not derive an allowed origin directly
from untrusted raw forwarded headers.

Execute WP02 and WP03 after WP01. WP02 enumerates only cookie names, paths, and
domains that WEPPcloud actually sets. WP03 maps known check identifiers and
statuses to fixed report text and treats raw evidence as untrusted.

Execute WP04 last so its matrix tests final behavior. Run focused gates after
each work package and the full Python and JavaScript gates before final review.
Obtain independent security and correctness reviews, resolve all medium/high
findings, then update outcomes and move completed prompts to `prompts/completed/`.

## Concrete Steps

Work from `/home/workdir/wepppy`.

During WP00:

    wctl doc-lint --path \
      docs/work-packages/20260727_web_origin_guard_hardening
    wctl doc-lint --path docs/schemas/weppcloud-csrf-contract.md
    wctl doc-lint --path docs/ui-docs/diagnostics-page.spec.md
    git diff --check

After WP00 reviews pass, create one documentation-only checkpoint commit and
record its full revision in the ExecPlan and tracker. Verify that no production
or test file is part of that commit.

During implementation:

    wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py \
      tests/weppcloud/routes/test_csrf_rollout.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_session_routes.py \
      tests/query_engine/test_server_routes.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py --maxfail=1
    python3 tools/check_broad_exceptions.py \
      --enforce-changed --base-ref origin/master
    wctl doc-lint --path \
      docs/work-packages/20260727_web_origin_guard_hardening
    git diff --check

Before closure:

    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

The shared matrix must prove on all three services that exact same-origin
browser signals pass, conflicting `Origin`, `Origin: null`, scheme mismatch,
port mismatch, subdomain mismatch, and `Sec-Fetch-Site: cross-site` fail, and
the reviewed missing-signal behavior is identical. The simulated upstream-TLS
case has `Origin: https://host`, `Sec-Fetch-Site: same-origin`, and an internal
HTTP request scheme; it must pass without trusting attacker-controlled
forwarded headers.

CSRF-enabled Flask tests must prove that same-origin evidence does not bypass a
missing or invalid CSRF token where CSRF applies. Cookie tests must compare the
complete deletion tuple set and prove no generic sibling-domain CSRF cookie is
targeted. JavaScript injection tests must prove arbitrary backend messages,
credentials, URLs, and WebSocket hostnames never appear in copied JSON.

Package closure requires focused and full gates, a dedicated final security
review, an independent correctness review, no unresolved medium/high findings,
and updated package, tracker, prompt outcomes, and ExecPlan outcomes.

## Idempotence and Recovery

All planned edits are source-controlled and validations are repeatable. If a
checkpoint review finds ambiguity, revise only checkpoint documents and repeat
both reviews before committing. If implementation begins before the recorded
checkpoint ancestor, stop, revert only this package's premature implementation
changes without disturbing unrelated work, and restart from WP00.

Rollback after implementation restores the prior helpers and report assembly
while retaining the security documentation as historical rationale. Because
rollback could reintroduce a cross-origin or disclosure defect, it requires a
security review and must not be used as an unreviewed operational workaround.

## Artifacts and Notes

WP00 owns `artifacts/2026-07-28_contract_decision.md`, two checkpoint review
artifacts, and a review disposition. Final review owns
`artifacts/2026-07-28_security_review.md` and an independent correctness review.
Use actual completion dates if execution occurs after 2026-07-28.

## Interfaces and Dependencies

Use the existing Flask, Starlette/FastAPI, Flask-WTF CSRF, and diagnostics
JavaScript interfaces. Add no external dependency. Preserve existing response
and error payload contracts. Queue wiring, Caddy configuration, authentication
policy, new endpoint coverage, and deployment are excluded.

Revision note: Created on 2026-07-28 to add the missing contract-first phase,
explicit sequencing, behavioral acceptance criteria, and closure gates.
