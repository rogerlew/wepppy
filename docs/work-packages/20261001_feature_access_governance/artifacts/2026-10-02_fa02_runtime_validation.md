# FA-02 runtime reconciliation and validation

Contract ancestor: `102c81066`. Implementation checkpoint being reconciled:
`458557219`. This evidence covers result sharing, not M3 completion or deployment.

## Implemented behavior

Removed feature-derived file classification, catalog/listing filtering, copied
output restrictions and recursive job-result redaction. Public retained contrast
and PATH-CE results use existing endpoint/resource authorization. Ordinary jobs
on contrast children do not inherit a feature action gate. PATH-CE consumes
already-computed contrasts and requires only its own action entitlement.

Restricted actions retain current identity, group/role, acknowledgment, readonly
and capability checks. Cancellation now checks named restricted operations across
the retained job tree before stopping anything; batch dispatch/finalizer IDs do
not masquerade as Ron project IDs. Private grouped-resource, sensitive-path,
JWT/scope and CSRF checks remain. The existing cancellation snapshot/dispatch
concurrency boundary is recorded in the independent correctness review.

The account UI describes actual contrast execution as the dependency boundary.
Missing optional Omni report state returns `404 results_unavailable` without
creating state. Anonymous creation and ordinary operation remain supported.

## Regression evidence

- Evaluator/PATH/query plus initial route run: 219 passed, 2 skipped before an
  obsolete export authorization stub signature stopped the run. Updated the
  stub to accept the existing `operation` keyword; no runtime auth relaxation.
- Delivery/export/fork/browse/D-Tale launch/jobinfo/Omni report suite: 275 passed.
- Jobinfo after grouped-root cancellation correction: 59 passed.
- Independent correctness verification (artifact/data, jobinfo, Omni report):
  84 passed. All three bounded review findings closed.
- First full-suite attempts reached 857 and 900 passed (28 skipped) before old
  authorization test doubles rejected the existing `operation` keyword. After
  correcting those fixtures, the complete affected microservice/WEPPcloud scope
  passed 3,325 of 3,326 tests. The sole failure was the preexisting run-catalog
  latency threshold (`68.6 ms` observed versus `50 ms`); both parameterizations
  passed when rerun in isolation. The authorization corrections also prove that
  Admin alone does not bypass the Batch group and that public Batch inspection
  remains available.
- Control-rendering follow-up: 326 passed. Frontend lint passed and 112 suites /
  919 tests passed.
- Isolated full-app browser acceptance passed the real-session group grant,
  acknowledgment, removal and decision flow, including accessibility checks:
  1 Playwright test passed. The disposable schema/session artifacts were cleaned.
- A public ZIP containing retained contrast bytes, PATH-CE JSON and a query
  catalog was downloaded byte-for-byte: 15 dedicated-download tests passed.

These runs overlap; counts are not additive. A complete Python-suite pass is
still pending, and the unrelated timing test remains flaky under suite load. No
production deployment or shared account mutation occurred.

## Private-resource remediation

Both reproductions use disposable synthetic files inside the existing container,
not real user data. The [reproduction script](2026-10-02_private_resource_reproduction.py)
retains the exact paths through production code.

- **S04:** query plans now bind resolved catalog sources as opaque Arrow
  relations. DuckDB extension auto-loading and external access are disabled
  before caller expressions execute. Vector inputs use a trusted Arrow/WKB
  adapter; `ST_Transform` is rejected because PROJ can read external grid paths.
  The retained scalar-subquery canary now reports
  `private_canary_read=false, external_read=blocked`.
- **S08:** trusted browse admission labels every D-Tale load with current
  resource visibility. Public cached tables keep anonymous downstream reads.
  Private tables return a 60-second launch ticket that establishes a scoped,
  HttpOnly viewer cookie bound to that viewer's verified claims; direct anonymous
  data/export/name/enumeration paths are denied or filtered, and derived IDs
  inherit scope. Every private request rechecks token/session expiry and
  revocation plus current run or feature-group authorization. Capability state is
  pruned on expiry and dataset discard. Private overlays remain available to an
  authorized viewer, while D-Tale's global GeoJSON lookup/list boundary applies
  the same capability and observes public-to-private marker changes. D-Tale
  receives the existing Postgres secret for live membership reads and already
  had the Redis secret used for revocation/session checks. The retained anonymous
  canary now receives HTTP 403 and reports `private_canary_read=false`.

The combined focused query/browse/D-Tale/files/auth regression passed 387 cases
with 2 benchmark skips. Compose rendering for development, HPC development and
production configurations passes. The retained exploit harness passes against
actual production code. Independent [correctness](2026-10-02_private_resource_correctness_review.md)
and [security](2026-10-02_private_resource_security_review.md) reviews pass with
zero unresolved findings. Broader M3 regression/service-browser acceptance
remains open. The final stable affected microservice/query/WEPPcloud suite passed
**3,468 cases with 2 skipped**; this is not a full-repository or deployed-browser
acceptance claim.

FA-02 did not waive either private-resource defect. M3 acceptance, dependent
self-promotion and rollout remain on hold until independent remediation review
and service/browser acceptance establish the private-resource contract.
