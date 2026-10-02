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
  passed 3,325 of 3,326 tests. The sole failure was the pre-existing run-catalog
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

## Confirmed remaining private-resource defects

Both reproductions use disposable synthetic files inside the existing container,
not real user data. The [reproduction script](2026-10-02_private_resource_reproduction.py)
retains the exact paths through production code.

- **S04, High:** public declared-dataset admission succeeds, then a computed SQL
  scalar subquery reads a private Batch Parquet file omitted from the catalog.
  Observed `private_canary_read=true`. Actual DuckDB 1.1.1 supports SQL JSON
  serialization, but an AST-based containment strategy still needs a complete
  compatibility/security design. `allowed_paths` is unavailable; blanket
  external-access disable breaks supported Parquet scans. No upgrade or query
  language change has been made.
- **S08, High:** an internal authorized load registers a private Batch CSV, then a
  fresh anonymous Flask client gets `/dtale/data/<id>` with HTTP 200 and the
  synthetic value. Observed `private_canary_read=true`. Launch admission alone
  cannot protect cached tables. A fix must cover downstream data, exports,
  metadata, global dataset discovery and map assets while retaining ordinary
  public anonymous D-Tale. No global login requirement or credential change has
  been introduced.

FA-02 does not waive either private-resource defect. M3 acceptance, dependent
self-promotion and rollout remain on hold until remediation and service/browser
acceptance establish the existing private-resource contract.
