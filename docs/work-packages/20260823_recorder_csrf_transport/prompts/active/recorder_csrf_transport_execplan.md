# Repair recorder CSRF transport end to end

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current while work proceeds.

## Purpose / Big Picture

WEPPcloud run pages record bounded browser request telemetry in the background.
Today those recorder submissions repeatedly fail with HTTP 400 because the
`sendBeacon`-first request can present a form CSRF token without the server-side
session value that Flask-WTF must compare it with. After this repair, run pages
will submit recorder batches through a credentialed same-origin fetch carrying
the canonical CSRF header, eliminating the console error while preserving CSRF
and run authorization.

## Progress

- [x] (2026-08-23 20:35Z) Reproduced and classified the live 400 response.
- [x] (2026-08-23 20:35Z) Scaffolded and registered the work package.
- [x] (2026-08-23 20:44Z) Added browser transport and real Flask CSRF middleware regressions.
- [x] (2026-08-23 20:44Z) Implemented credentialed, same-origin-only fetch and removed the broken Beacon preference.
- [x] (2026-08-23 20:44Z) Preserved singleton JSON arrays, rebuilt generated assets, and updated developer guidance.
- [x] (2026-08-23 20:59Z) Passed focused, full frontend, and full Python validation plus lint, documentation, and changed-file gates.
- [x] (2026-08-23 20:44Z) Completed correctness and security reviews and closed the package.

## Surprises & Discoveries

- Observation: The April 2026 hardening added a CSRF form field to beacon
  payloads, but the observed server response proves the corresponding session
  state is absent.
  Evidence: Bearhive returned `csrf_failed` with detail `The CSRF session token
  is missing.` rather than reporting a missing submitted token.

- Observation: `parse_request_payload` collapses a singleton list to its only
  dictionary value, which made one-event JSON recorder batches fail the route's
  array validation.
  Evidence: The real middleware test passed CSRF and then returned `events must
  be a non-empty array` until the route preserved native JSON.

- Observation: Host `python3` lacks Jinja even though the controller build
  script's documented invocation uses it.
  Evidence: host execution raised `ModuleNotFoundError: No module named
  'jinja2'`; `wctl exec weppcloud python ...` succeeded.

## Decision Log

- Decision: Treat this as a conformance repair to the unchanged browser-client
  section of `docs/schemas/weppcloud-csrf-contract.md`.
  Rationale: The contract already requires raw mutating fetch calls to carry
  `X-CSRFToken`; no exemption or CSRF policy change is necessary.
  Date/Author: 2026-08-23 / Codex.

- Decision: Prefer credentialed `fetch` with `keepalive` for every recorder
  flush, including unload-triggered flushes.
  Rationale: This transport can explicitly carry both same-origin credentials
  and the CSRF header. `sendBeacon` cannot set the required header and has
  produced the confirmed cross-deployment failure.
  Date/Author: 2026-08-23 / Codex.

- Decision: Validate the resolved endpoint before reading the CSRF token and
  constrain Fetch with `mode: "same-origin"`.
  Rationale: This prevents direct configured-endpoint and redirect-based CSRF
  token disclosure while preserving every repository-defined recorder target.
  Date/Author: 2026-08-23 / Codex.

- Decision: Bypass shared payload normalization only for native recorder JSON.
  Rationale: The shared parser's singleton-list behavior may be relied on by
  other routes; the smallest safe repair preserves recorder arrays locally and
  retains form compatibility.
  Date/Author: 2026-08-23 / Codex.

## Outcomes & Retrospective

The package achieved its purpose. Recorder mutations now retain session
credentials, carry the matching CSRF header, reject cross-origin targets, and
preserve singleton event arrays. Focused and full frontend gates passed, as did
independent correctness and high-impact security review. The remaining action
is a post-deployment Safari smoke check confirming the original console symptom
is absent.

## Context and Orientation

`wepppy/weppcloud/controllers_js/recorder_interceptor.js` wraps the shared
`WCHttp.request` function and batches request lifecycle events. Its private
`send` function currently prefers `navigator.sendBeacon`, sending a multipart
form containing `csrf_token` and serialized events. The protected Flask route
is `recorder_events` in `wepppy/weppcloud/routes/recorder_bp.py`. Global
Flask-WTF middleware rejects the request before that function runs when the
submitted token cannot be matched to session state. The generated production
bundle is `wepppy/weppcloud/static/js/controllers-gl.js`.

## Plan of Work

First extend `controllers_js/__tests__/recorder_interceptor.test.js` to prove
that recorder flushes use fetch even when `sendBeacon` exists, attach
`X-CSRFToken`, set `credentials: same-origin`, retain `keepalive: true`, and set
the internal recursion-suppression marker. Extend
`tests/weppcloud/routes/test_recorder_bp.py` with a minimal Flask application
using real `CSRFProtect` middleware so missing session/token state fails and a
client-generated token succeeds at the registered recorder endpoint.

Then change only the recorder transport. Remove the beacon payload machinery
and send JSON with credentialed fetch plus the discovered CSRF header. If fetch
or the token is unavailable, do not issue a predictably invalid mutation.
Preserve batching, endpoint resolution, event schemas, redaction, and recorder
recursion avoidance. Update `controllers_js/README.md` and rebuild the bundle.

Finally run focused Jest and pytest tests, lint, bundle build verification,
documentation lint, changed-file exception enforcement, and the proportionate
full pytest gate. Obtain independent correctness and security reviews, resolve
findings, and record evidence in package artifacts and trackers.

## Concrete Steps

Run commands from `/home/workdir/wepppy`:

    wctl run-npm test -- recorder_interceptor
    wctl run-pytest tests/weppcloud/routes/test_recorder_bp.py
    wctl run-npm lint
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260823_recorder_csrf_transport

## Validation and Acceptance

Focused Jest tests must show a recorder flush calling fetch with a JSON body,
same-origin credentials, keepalive enabled, and an `X-CSRFToken` value even
when a mocked beacon API exists. The Flask integration test must show that the
real middleware rejects an unprotected POST and accepts a POST using a token
generated in the same test-client session. The rebuilt bundle must contain the
same credentialed-fetch behavior. All relevant gates must pass or any unrelated
baseline failure must be recorded with evidence.

## Idempotence and Recovery

Tests, lint, and bundle generation are repeatable. The patch changes no run
data or deployment state. If validation fails, retain the first failing
regression, correct the smallest implementation seam, rebuild, and rerun the
focused gate before broad validation.

## Artifacts and Notes

The live failure was observed on 2026-08-23 at
`https://wc.bearhive.duckdns.org/weppcloud/runs/soft-boiled-copying/disturbed9002_wbt/`.
The response body identified `csrf_failed` and `The CSRF session token is
missing.`

## Interfaces and Dependencies

No new dependency is allowed. `WCRecorder` retains its public `emit`,
`setConfig`, `getConfig`, `isEnabled`, and test-only `_queueSize` surface. The
Flask route path and event JSON schema remain unchanged. The browser transport
uses the existing `WCHttp.getCsrfToken()` discovery interface and the native
Fetch API.
