# Recorder CSRF Transport Repair

**Status**: Complete (2026-08-23)

## Overview

Repair the run-page profile recorder so its background `recorder/events` POSTs
retain the browser session and carry the CSRF header required by the canonical
WEPPcloud CSRF contract. The current `sendBeacon`-first transport submits a form
token but can arrive without the matching session state, producing persistent
HTTP 400 `csrf_failed` responses across deployments.

## Scope

Included work is limited to the recorder browser transport, focused Flask CSRF
boundary coverage, generated controller bundle, developer documentation, and
validation/review evidence. Recorder schemas, run authorization, CSRF policy,
session configuration, and the recorder persistence format are unchanged.

## Contract Classification

This is a conformance fix against
`docs/schemas/weppcloud-csrf-contract.md#browser-client-requirements`. That
contract already requires raw mutating `fetch` calls to attach `X-CSRFToken`
and recommends the shared credential-aware browser transport. No normative
contract behavior changes.

## Success Criteria

- Recorder batches use credentialed same-origin `fetch` with `keepalive` and a
  discovered `X-CSRFToken` header.
- The recorder never prefers `sendBeacon` for a CSRF-protected Flask route.
- Focused browser tests prove credentials, token propagation, batching, and
  recorder recursion avoidance.
- Flask tests exercise the real CSRF middleware accept/reject boundary.
- The generated `controllers-gl.js` bundle is rebuilt and matches its sources.
- Required correctness and security reviews are dispositioned.

## Outcome

The recorder now uses a fail-closed, same-origin-only Fetch transport with
session credentials, `keepalive`, and `X-CSRFToken`. The Flask route preserves
singleton JSON arrays instead of passing them through the shared singleton-list
normalizer. Focused, full frontend, correctness, and security gates passed; see
`artifacts/final_validation_summary.md`.

## Deliverables

- `prompts/active/recorder_csrf_transport_execplan.md`
- `artifacts/final_validation_summary.md`
- `artifacts/correctness_review.md`
- `artifacts/security_review.md`
- `tracker.md`
