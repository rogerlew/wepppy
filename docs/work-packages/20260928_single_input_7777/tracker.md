# Tracker

Closed 2026-09-28: implementation and local acceptance complete; deployment separate.

Starting revision: `50495bfeebf5ccf3c8cf50753100803e35bb5382`.
Reviewed contract ancestor: `e3a12ba42`; implementation: `84caefd61`.

The canonical decision is in
[Upload interface and validation](../../schemas/single-user-defined-inputs-contract.md#upload-interface-and-validation)
and [ADR-0075 SUDI-03](../../adrs/ADR-0075-single-user-defined-inputs.md#sudi-03-7777-soil-format-amendment).
7777 retains eight header fields, ten layer fields, profile anisotropy and native
version. Generated inputs preserve supplied values; native reader limits remain.

Focused tests: 205 passed. Existing parser/WSU/Pure/transport regressions: 305 passed.
Full suite: 9892 passed, 99 skipped, 12 subtests passed in 2429.35 seconds, exit 0.
Frontend lint and 112 suites/919 tests passed. Stub completeness, exception gate
and documentation lint passed. Code-quality telemetry is retained and non-blocking.

Both independent final reviews approved with no unresolved findings. The exact
supplied CRLF fixture passes native execution at 1/2/12/32 OFEs; modifier cases
pass at 1/3 OFEs. Authenticated upload, real build, normal controller/service
preparation, native outputs, source download and archive/restore passed. See
[validation summary](artifacts/20260928_validation_summary.md) and linked JSON.

The disposable development run required a fresh-worker retry because long-lived
workers retained old imports. No shared restart, push or deployment performed.
Update web and workers together for rollout. The known test-generated management
JSON parser flags were inspected and restored before closeout.
