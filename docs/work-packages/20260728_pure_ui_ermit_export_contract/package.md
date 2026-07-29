# SURF-16 Pure UI ERMiT Export Contract

**Status**: Closed
**Package ID**: SURF-16
**Security impact**: `high`
**Dedicated security review**: required only if an actual production patch
changes the authenticated export surface

## Purpose

Verify the authenticated ERMiT/Disturbed WEPP export page from its run-results
link through session-token minting, queue submission, status polling, protected
artifact download, retry/error behavior, and return navigation.

## Concise Intent Contract

For an authorized, CAP-verified non-RHEM run, the results page links to a
run-scoped launcher. The launcher safely embeds run-scoped submit, token, and
return URLs; submits exactly one export; polls the canonical job-status URL;
downloads only the finished job artifact with the minted bearer token; and
shows explicit queued, active, finished, failure, retry, and no-JavaScript
states.

Retry starts a fresh recoverable attempt after token, submit, poll, or download
failure. The rq-engine submit route retains `rq:export` scope and run-access
authorization, canonical `202` keys, existing queue wiring, pup scoping, and
worker artifact metadata. Protected download retains run/job association and
finished-state checks.

## Scope

- `templates/controls/wepp_reports.htm` export discoverability;
- `templates/reports/ermit_export_download.htm` launcher and inline client;
- `routes/nodb_api/wepp_bp.py::download_ermit_export`;
- rq-engine ERMiT submit/status/download and session-token boundaries;
- `rq/ermit_export_rq.py` artifact generation metadata; and
- direct render, inline Jest, route, worker, and existing security tests.

## Exclusions

This package does not change ERMiT CSV formulas or columns, WEPP inputs,
queue topology, token claims/scopes, authorization policy, CAP policy, public
download policy, NoDir behavior, or shared transport/status producers. DOM-14A
owns WEPP execution; SURF-12 owns the generic report shell.

## Acceptance

Actual rendering proves exact links, run URLs, lifecycle/action targets,
accessibility state, safe JSON embedding, and initial state. Inline client tests
prove bearer-token submission, canonical polling, finished download, failure
presentation, and genuine retry recovery. Existing route/RQ/worker/session
evidence must pass. A confirmed mismatch receives only the smallest compatible
repair and the proportional independent review required by the audit protocol.

## Outcome

The audit confirmed one production mismatch: a rejected session-token promise
remained cached, so the visible Retry action could never recover from an
initial token failure. The launcher now clears that cache at the start of each
explicit export attempt. It still shares one token across submit, poll, and
download within an attempt and preserves all scopes, claims, routes, queue
wiring, and protected-download checks.

Direct rendering, real inline-client execution, route/session/RQ tests, and a
new worker artifact-metadata regression cover the complete bounded lifecycle.
Final review and broad-gate evidence are recorded in `tracker.md`.
