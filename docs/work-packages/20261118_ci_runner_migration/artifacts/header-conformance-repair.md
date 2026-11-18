# Theme Lab header conformance repair

Observed 2026-11-18 UTC in the actual isolated application: GET /ui/components/
returned HTTP 500 because header/_run_header_fixed.htm read ron.developer_mode,
but the gallery supplies current_ron, the same view model used throughout that
shared header. Existing tests provided both aliases and hid the defect.

Classification: implementation conformance defect, no normative behavior change.
Canonical authority: docs/schemas/project-developer-mode-contract.md, State and
lifecycle and UI sections. A false/missing legacy developer mode hides the
indicator; true shows it. No persistence, enablement, authorization, formulas or
other developer-mode behavior changes. Theme Lab's sample view remains valid.

Repair only that header expression to use current_ron. Add regression coverage
with ron absent, and missing/false/true mode on current_ron. Retest actual Theme Lab
HTTP/rendered browser output; a fixture-only template pass is insufficient.

## Browser runtime escalation evidence

The three-service CI runtime can render Theme Lab, but controller run pages require
CAP verification or an authenticated session. The actual controller run returned
CAP configuration errors and skipped all 18 controls; the new report guard rejected
that false success. Authentication must remain enabled. Add the existing owned CAP
service, built from its existing pinned production Dockerfile, to the isolated
browser project. Use job-local fixture credentials and data only, no published ports.
Proxy its existing /cap routes on the same loopback fixture origin. Provision a
controller session through actual CSRF/password/CAP login, not an auth bypass.
This is the smallest additional runtime component needed by the demonstrated path;
cleanup remains the same project-wide down/volumes operation.

Controller execution then reached real token requests at /rq-engine, which returned
404 because the initial fixture served Flask alone. Run the existing RQ API in the
same disposable container on a private loopback socket, proxying /rq-engine with
its normal prefix stripping. Preserve real session-token authorization. The existing
browser tests still intercept their own build requests; no RQ worker or model
execution service is introduced. Startup and shutdown are bounded and owned by the
fixture. This additional API is required by the observed controller authentication
path, not an attempt to replicate the full production stack.

The next run authenticated and passed the first four controller checks, but both
outlet checks timed out. Browser diagnostics confirmed ERR_NAME_NOT_RESOLVED for
the page's existing external scripts and “Outlet GL requires deck.gl GeoJsonLayer.”
Attach only the browser/application container to a job-local outbound bridge so
its existing public CDN assets can load. PostgreSQL, Redis and CAP remain on the
internal network; no host ports, host secrets, production targets or worker are
introduced. This preserves the existing page's dependencies rather than replacing
production script libraries with test stubs. Cleanup removes both job-local networks.
