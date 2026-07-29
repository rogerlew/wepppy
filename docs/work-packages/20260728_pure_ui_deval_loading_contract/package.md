# SURF-18 Pure UI DEVAL Loading Contract

**Status**: Verified
**Package ID**: SURF-18
**Security impact**: `high`
**Dedicated security review**: required for any production patch

## Purpose

Verify the complete “Deval in the Details” report handoff: authorized run
access, CAP challenge, cached-report reuse, bounded enqueue decisions, job
tracking and polling, worker rendering, explicit failures, and final HTML
delivery.

## Concise Intent Contract

The DEVAL report route is run-scoped. It enforces the canonical run/config
authorization boundary and additionally requires CAP verification for anonymous
traffic. CAP proves that a visitor passed the abuse-control challenge; it never
grants access to a private run. The resolved `RunContext.active_root` owns the
fixed report artifact and tracked job identity.

Without `no-cache`, a completed cached report is served directly with no-store
headers. With no cached report, or with `no-cache`, the route reuses an already
active tracked job or enqueues one render job and returns the loading page with
HTTP 202. PUP requests preserve the active root and `pup` refresh target.
Enqueue arguments fix run ID, config, active root, cache choice, container
override, and timeout. The worker rejects retired root resources, invokes the
owned weppcloudR renderer, writes diagnostic logs, requires the expected output,
publishes status, and returns the generated artifact path.

The loading client polls the canonical same-origin jobstatus endpoint without
overlapping requests. `queued`, `started`, `deferred`, and `scheduled` remain
active; `finished` alone is success and refreshes the report route; `failed`,
`stopped`, and `canceled` show an escaped failure; missing, malformed, or unknown
statuses are failures rather than success. HTTP 429 uses bounded exponential
backoff. Other transient failures retry up to the fixed error limit, after which
the client stops and shows a generic failure. Canonical nested error messages
may be displayed as text, never HTML.

The route and worker retain existing RQ response, run authorization, CAP,
filesystem, and error contracts. The package does not add polling endpoints,
queue dependencies, renderer parameters, report schemas, or public access.

## Scope

- `wepppy/weppcloud/templates/reports/deval_loading.htm`;
- `wepppy/weppcloud/routes/weppcloudr.py::{deval_details,_determine_job,_enqueue_deval_job}`;
- `wepppy/rq/weppcloudr_rq.py::render_deval_details_rq`;
- existing CAP, RQ jobstatus, RunContext, RedisPrep, and artifact boundaries;
- direct render, executable inline-client, route, enqueue, worker, cache, and
  reload evidence; and
- parent register/tracker reconciliation.

## Exclusions

No report-content redesign, R script change, new endpoint, queue edge, Redis
schema, polling policy shared abstraction, public-access rule, timeout/default
parameter change, or artifact filename change is authorized.

## Acceptance

Actual rendering and the real inline script prove safe bootstrap, exact status
classification, bounded retry/backoff, terminal behavior, error text, and
refresh. Route tests prove run authorization plus CAP, cache/no-cache decisions,
active job reuse, enqueue arguments, PUP identity, response headers, and
generated handoff. Worker tests prove command, path, log, success, and failure
behavior. Focused, frontend, documentation, applicable RQ/security, and broad
gates are recorded before closeout.
