# Download error observability

## Purpose / Big Picture

A failed project download must explain the server failure and stop, rather than
show a bare HTTP 500 followed by an apparent successful empty download. This plan
covers browse manifests, file downloads, dedicated archive downloads and the
three bootstrap download entry points in `/home/workdir/wepppy-win-bootstrap`.
Preserve authentication, successful bytes, concurrency and existing CLI arguments.

## Progress

- [x] 2026-10-27 UTC: traced browse error suppression, missing dedicated-download
  exception handlers, and client manifest error continuation.
- [x] Add safe classified server errors with log-correlated request IDs.
- [x] Make bootstrap clients display errors and propagate failed exits.
- [x] Validate response-to-terminal behavior, success, auth and failure cases.
- [x] Independent correctness, security and QA reviews; 190 focused server tests, 14 Windows tests and 12 Linux tests pass (two Windows-only skips).
- [x] Complete full-collection coverage in recorded segments and reconcile final evidence: 11,923 passed, 198 skipped, one unrelated Roads provenance blocker.
- [x] Prepare scoped publication in both repositories; bootstrap commit `d765507`. Deployment remains held.

## Context and Orientation

`wepppy/config/secrets.py` raises untyped RuntimeError on required missing, empty
or unreadable configuration. Lazy owner lookup loads Flask and can raise this
inside a browse request. `browse/browse.py` suppresses unexpected failures;
`download/app.py` has no application error handlers. The bootstrap batch and
shell wrappers run aria2c even when the manifest fetch fails. The legacy Python
archive downloader does not read urllib HTTPError bodies.

## Plan of Work

First add a RuntimeError-compatible secret configuration exception carrying a
safe public description (configuration names and reason, never secret values or
filesystem paths). Reuse a small browse/download error response helper to attach
request IDs and log full exceptions. Preserve browser pages and machine-readable
error contracts. Then share standard-library HTTP diagnostics in bootstrap
clients; retain existing Python prerequisite and aria2c transfer implementation.
Exercise errors with real local HTTP responses and inspect terminal output and
exit codes. Successful downloads must preserve exact bytes.

## Validation and Acceptance

Run `wctl run-pytest tests/config/test_secrets.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_dedicated_download_service.py` and focused new tests, then
`wctl run-pytest tests --maxfail=1`. Run bootstrap unittest discovery. Confirm a
missing SECRET_KEY produces a useful safe message, stable code and request ID;
the same ID appears in server logs. No traceback, token, secret value or secret
file path may reach default responses. Manifest failure must not invoke aria2c;
file transfer failure must be nonzero. Check docs with `wctl doc-lint`.

## Surprises & Discoveries

The bootstrap README already recorded false success after manifest failure.
Prior configuration repair fixed provisioning but did not test error delivery. Real aria2c saved sessions add trailing TABs and percent-encode spaces/Unicode; mock-only fixtures initially missed these details. An initial broad run was invalidated by source edits during collection; repeat only against stable code. Reviews also caught loss of legacy NoDir codes and upstream raw exception disclosure; both are fixed and retained in tests.

## Decision Log

On 2026-10-27 the user required meaningful server errors and client reporting.
Use typed known failures and a diagnostic reference for unknown ones; publishing
arbitrary exception text would expose secrets and private paths. No new runtime
dependency, service, queue, configuration fallback or authorization change. Python is already a documented bootstrap prerequisite. Preserve external manifest origins and resume behavior; do not add a blanket same-origin manifest restriction. Cross-origin HTTP redirects strip Authorization. Preserve authored legacy NoDir codes with safe descriptions, and preserve explicit BROWSE_DEBUG_ERRORS operator behavior.

## Outcomes & Retrospective

Implementation, native Windows/Linux validation and independent reviews pass. Broad assessment is complete with one unrelated Roads provenance blocker; scoped source changes are ready for publication. No production deployment of this repair yet.

## Idempotence and Recovery

Changes are source-only and reversible. Use disposable local fixtures; do not
inject failures into production. Preserve unrelated dirty bootstrap files.

## Artifacts and Notes

Precedents: artifact-observability and hardening-lifecycle standards; dedicated
download service package and existing browse/files error envelope. This repair
extends failure visibility rather than changing access or artifact eligibility.

## Interfaces and Dependencies

Use existing Starlette, urllib and aria2c. No schema migration or project mutation.
The bounded assessment excludes unrelated HTTP services and third-party clients.

Revision 2026-10-27: created from the observed server/client observability gap.

Revision 2026-10-27: recorded completed implementation, independently found regressions and exact platform evidence; broad validation remains a distinct gate.

Validation execution decision: after 21m39s without a failure (2,630 passed/48 skipped), interrupt the serial run inside the isolated soil matrix. The collected matrix has 230 cases, distributed without overlap across eight processes; all pass. Preserve the already completed 2,530-item prefix and execute the 9,354-item suffix from its exact 580-file inventory. Deduplicate the 147 matrix cases already passed in the serial attempt. Seven late GDAL/D-Tale and exception-pickle regressions extend the original 12,114-item collection and are validated with the final focused suite. This is segmented coverage, not a claimed monolithic pass.

Final validation decision: preserve the unrelated Roads working-tree edit and document its provenance failure. Correct only the browser-cache path for the individual test invocation; it passes with the existing installed browser. All remaining cases complete. Publish the bounded repair with this explicit limitation; do not claim a globally green suite or deploy.
