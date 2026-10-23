# Independent Roads lifecycle implementation correctness review

## Disposition

**Approved: no unresolved high or medium correctness finding remains.** The producer,
read admission, restore and client corrections below have targeted evidence.
Real-project, authenticated HTTP and canonical archive evidence support the
approved replacement lifecycle. Query discovery now prevents cached availability
with a bounded no-store rule, and its 75-case gate passes. Broad Python coverage
is complete through the explicitly documented segmented validation below;
this is not a claim that one full-suite invocation passed.

Reviewer: independent `accounting_contract_review`, 2026-10-22.
Contract ancestor: `1270c209fe978f59a067c88af0df9574d3459114`.
Reviewed runtime is frozen at `e4d28c9adc6c86948ba2383fdc172686c0d4d67c`.
Runtime and tests were reviewed read only. This artifact is the reviewer's only
implementation-review edit. Scope includes producer retention/publication,
report/query/browse consumers, module mutations, archive/restore and client state.

## Coverage limits

The inspected full frontend log records 119 suites/990 tests, including the new
nonempty summary regressions. Source inspection confirms the generated
`static/js/controllers-gl.js` also contains the corrected invalidation epoch and
panel sequence. The final lifecycle log records 17 passing cases; this
review independently ran the earlier 15-case suite and the three module cases.

The module fixture initially failed because its registry stub did not cover the
new direct `Roads.getInstance` call. That seam is corrected; the same independent
Roads module subset now passes, including explicit HTTP contention behavior.

The [security review](20261022_security_review.md) separately owns D-Tale existing
session admission and final security closure. The live HTTP evidence covers seven
readers and a Chromium browse page, not every dashboard interaction or actual RQ
enqueue/status sequence. Archive validation uses canonical filesystem functions
with isolated RQ/status/cache callbacks. Single-storm publication and failure
branches have targeted tests rather than a second full single-storm project run.
Broad coverage closes with the continuation evidence below. No production
deployment or original-project repair is certified.

## Findings corrected during review

| ID | Severity | Finding and disposition |
| --- | --- | --- |
| A1 | Medium | Single-storm execution creates an accounting ledger, but its resource list originally omitted that required path. Producer now includes the ledger in both modes; only equivalent WAT is continuous-only. The single-storm test validates ledger provenance after restore. |
| A2 | High | Restore checked receipt/file presence without prepared geometry, manifest or artifact readback. Shared generated-set validation now checks those relationships and applicable accounting before releasing restoration. Independent missing-context/footer probes reject and revoke. |
| A3 | Medium | Direct files metadata/listing and D-Tale launch bypassed result admission. Their current guards enclose existence/metadata construction and the remote load operation. Live files metadata and browse transitions passed; D-Tale evidence is retained in the independent security review. |
| A4 | Medium | An instance loaded before acquiring the shared guard could pair stale NoDb summary/parameters with a newer receipt. Inspection now compares the persisted signature under the guard and rejects stale instances. |
| A5 | High | Footer-only Parquet validation admitted unreadable data pages at publication and restore. Required Parquets now stream through bounded batches with validation. The independent corrupted-page publication probe now rejects without a receipt. |
| A6 | High | Module enable did not synchronize the new controller's enabled state; disable bypassed lifecycle locking and invalidation. Current module helpers hold the operation guard and call set_enabled before completing module mutation. Module tests and a real-controller disable probe passed. |
| A7 | High | Failed restoration could leave a current receipt when output ancestry was readonly. Revocation now temporarily restores owner access, removes the receipt and restores modes before releasing the guard. Independent uid-1000 probe confirms unavailable state and exact 0555 mode restoration. |
| A8 | Medium | The set_mod broad catch converted lifecycle contention to HTTP 500 before outer error translation. It now re-raises lifecycle exceptions; the independent module test confirms HTTP 409, roads_operation_busy and no-store. |
| A9 | Medium | Panel refresh incremented the summary request version and discarded fresh bootstrap/completion summaries. Separate panel sequencing now preserves fresh summaries. Both trigger regressions supply nonempty summaries and assert rendered content, while another case rejects an older panel response after preparation. |

Attribution correction for A6: inspection of `git show 1270c209f:.../roads_bp.py`
confirms `_sync_roads_enabled_state` was already read only at the checkpoint.
The first-enable mismatch is a preexisting integration defect exposed by this
review, not a regression introduced by the lifecycle patch. The authorized
mutation hooks are the appropriate place to repair it; reads need not mutate.

## Independent validation

- `wctl run-pytest tests/wepp/interchange/test_roads_lifecycle.py --maxfail=1 -q`:
  **15 passed**, 17.23 seconds, six dependency deprecation warnings. Coverage
  includes retention/context/cache, separate-process contention, cached query
  rejection, streaming lifetime, single-storm ledger, restore corruption,
  failed-run diagnostics and first-creation locking.
- `wctl run-pytest tests/weppcloud/routes/test_project_bp.py -k roads --maxfail=1 -q`:
  **3 passed**, 9.03 seconds after the fixture correction. Covers backend
  rejection, synchronization on enable and HTTP lock-conflict behavior.
- Actual container probes used `wctl exec -T weppcloud python -` with temporary
  directories. Missing geometry/manifest and a corrupt Parquet footer initially
  restored as current; after correction each raises and removes the receipt.
- A valid three-row Parquet with bytes 4 through 15 overwritten retained a valid
  footer but failed full reading. Initially publication and restore admitted it;
  after bounded batch validation publication raises OSError with no receipt.
- Under uid 1000, a simulated failed restore with output mode 0555 initially
  raised PermissionError and left readiness admitted. After correction it
  preserves the original failure, removes readiness and restores mode 0555.
- A temporary-directory probe using the real `Roads` controller confirmed that
  `set_enabled(False)` revokes current availability and retains one historical
  receipt. This complements the module synchronization test without modifying
  either the validation project or original UM1.

These probes establish failure behavior at the shared boundary; they do not
replace actual controller, transport or archive workflows. Synthetic admission
fixtures remain separate from evidence that the full model producer succeeded.

## Broad-gate continuation assessment

The original full-suite process collected 11229 tests before the final discovery
and preview edits. It stopped after **6029 passed, 56 skipped and one failure** at
`tests/query_engine/test_mcp_router.py::test_create_mcp_app`. The inspected traceback
shows `reload(router)` importing the newly added `discovery_headers` symbol from
an older, already-loaded `feature_access` module. This matches the documented
mid-run edit sequence. A clean process passes all 75 query cases, and the restarted
live query service passes the discovery checks. No runtime workaround is warranted
for this mixed-source test process.

The continuation uses the same full `tests` collection and an inspected temporary
pytest hook at `/tmp/roads_resume.py`. It finds the exact failing node, reports all
earlier nodes as deselected, and retains that node and every subsequent node. It
does not filter by marker or by changed file. Final D-Tale validation separately
passes 20 cases, covering the two alias regressions added before that boundary;
new discovery cases are after the boundary and also pass in the focused query run.

The fresh collection reports **11240 collected, 6086 deselected, 5154 selected and
one collection skip**. The deselected prefix is the original 6084 executed nodes
(6029 passed plus 55 runtime skips), plus the two new D-Tale cases covered by the
focused rerun; the original total of 56 skips includes the collection skip.

The first continuation stopped after **4774 passed, 71 skipped and one failure**
at `tests/weppcloud/test_feature_access.py::test_openet_signed_token_live_membership_admission`.
The inspected traceback shows the lifecycle middleware's import-captured real
Redis constructor reaching an authentication-required Redis server, yielding 503
before the test's first expected 403. This is a test isolation defect; the
isolated feature-access file already passed without it.

The reviewed six-line test-only correction binds that captured constructor to
`tests.factories.redis.make_redis_client()` and places lifecycle filesystem locks
under `tmp_path`. It does not change JWT verification, feature policy evaluation,
SQL membership state or the response assertions. The test still checks Root and
nonmember denial, acknowledgment and scope requirements, grant success and live
revocation of the same token. Production runtime remains frozen.

The final continuation accepts `ROADS_RESUME_NODE` and includes the exact failed
feature-access node plus every later node. Its fresh collection is **11240
collected, 10930 deselected, 310 selected and one collection skip**. The boundary
reconciles: 6086 earlier deselections plus 4774 passes and 70 runtime skips equals
10930; the first continuation's 71 skips include its collection skip.

The inspected final log records **310 passed, one collection skip, 10930
deselected in 68.86 seconds**. It includes the corrected feature-access test and
every remaining node. Combined distinct coverage is **11115 passed**
(6029 + 4774 + 310 + two added pre-boundary D-Tale cases), **125 runtime skips**
(55 + 70), and **one collection skip**. This accounts for all 11240 collected
nodes plus the collection-level skip without counting focused reruns twice.

These bounded continuations close the broad coverage requirement with the
runtime frozen. Report the original prefix, focused reruns, intermediate
continuation and final suffix separately. Do not claim a single all-green
full-suite invocation. Restarting processes does not prove absence of test-order
interactions across either continuation boundary; that remains an evidence limit.

## Real-project evidence inspected

Read the retained [validation script](validate_lifecycle.py) and
[real-run receipt](20261022_real_run_validation.json). The implementation agent exercised
`/wc1/runs/ro/roads-segment-summary-validation` under uid 1000/gid 993:

- Two full Roads runs with preparation between them; current output was removed
  after preparation, retained receipt/context existed in history, and only the
  second full run restored current admission.
- Both successful outputs contained 34 profile rows; final summary SHA-256 was
  `96acc980474f2800bcd8fa652ef3d40cad6898f04e8e6f80b1b78ed1fd858a5f`.
- Hash checks preserved 911 baseline input/output files and 46 Parquets from
  original `/wc1/runs/cl/clogging-starch`.

This is inspected implementation-agent evidence, not a second independent model
rerun. The script verifies row counts, receipts, retention and protected bytes;
it does not itself prove every HTTP consumer or failed attempt.

Independent readback of the resulting Parquets additionally confirmed annual
profile sediment export 4810.81837972126 kg, runoff 1008.0648908316253 m3 and
modeled area 4127.150000000001 m2. The water table has 5844 days and represented
area 441820.2900000002 m2; 2001 surface runoff, lateral flow and baseflow sum to
183.26310493761835, 1011.5502449533644 and 71.4562594052902 mm respectively.
These agree with the prior accounting/segment investigation evidence.

The [archive script](validate_archive.py) and
[receipt](20261022_archive_validation.json) exercise canonical `archive_rq` and
`restore_archive_rq` under uid 1000/gid 993. They verify 14 resources byte for byte,
retained historical receipts, restored current admission, exclusion of the lock
from ZIP members and preservation of the destination lock inode. RQ/status/cache
callbacks are explicitly isolated; this is not evidence of queued job execution.

The [live HTTP script](validate_http.py) and
[receipt](20261022_http_validation.json) use actual authorization with an existing
scoped dev-agent identity against the isolated restored project. Binary download,
CSV, schema, files metadata, browse, dashboard and query each pass current 200,
writer-conflict 409, post-preparation 409 and fresh-full-run 200. The script checks
no-store on every response, the canonical error code on 409, 34 CSV/query rows,
historical download byte equality and prepared geometry availability. Chromium
loads the real browse page and finds the summary filename. The browser probe does
not automate the entire Roads controller workflow; that client behavior is covered
by focused JavaScript tests.

The final query-discovery patch sets no-store on run information, schema, query
UI and MCP catalog responses only when local Roads state or raw catalog sources
communicate Roads availability. Eight route cases check both Roads and ordinary
baseline discovery; the retained final query log records 75 passing tests. The
D-Tale loader now shares source classification with existing sessions and rejects
a current path aliased into history while allowing explicit historical requests.
The independent security reviewer owns the corresponding eager/lazy regression
and private-authorization evidence.

## Review fingerprints

These identify the source inspection recorded below; later task-scoped runtime
changes require a bounded follow-up review. Paths are repository-relative.

| File | SHA-256 |
| --- | --- |
| wepppy/wepp/interchange/_roads_lifecycle.py | `94b17afb10e8686afbcc9308e1893bc27e5dd924d87ebe9c5142aeca018e6836` |
| wepppy/nodb/mods/roads/roads.py | `55aa09763891340757755df228d2dcb8f2c0553e191b9233f304f3782480668e` |
| wepppy/weppcloud/routes/nodb_api/project_bp.py | `13b2fd46850d2ddab0242ac121343356cfeb7bd74ad35ceae014729591cda7ac` |
| wepppy/weppcloud/routes/nodb_api/roads_bp.py | `68945de8b0096610592716d380d46fdefadfbe8295a16607a944e620dc2f9546` |
| wepppy/query_engine/executor.py | `7f7aea9ede186da565167d64d53a31812e57d25300e04f2ec3f655ec700af83e` |
| wepppy/query_engine/app/feature_access.py | `eef7602809dc11f92cf7e9d5fa9a6be8510df60fe35854f8354b3caadc5580fe` |
| wepppy/query_engine/app/server.py | `1bd1e889219b9ae707cb8a2569e3c9754271f62930504074ec06a834e1168f9d` |
| wepppy/query_engine/app/mcp/router.py | `16a17b0f572e07699bb567a86c0ae38815fda9a40abb4e5edd79fbd819bcb21d` |
| wepppy/rq/project_rq_archive.py | `7fdda6b5669345ee63c41e0f3452c0b74b7c457644f4be39fa4342fcab61819e` |
| wepppy/microservices/browse/_roads.py | `a7c4d5d5517d199daaf2d03f21fdc2843a941adebe9330dc7977124ab6ffc75c` |
| wepppy/webservices/dtale/dtale.py | `9678885cf5db77e6d5c3524941939acb823c702adaf73d6a17a9f88d20972278` |
| wepppy/weppcloud/controllers_js/roads.js | `9768d78296264d8557384b1e8acbf5f0044d5abaeac4b2e94497d87c63908631` |
| wepppy/weppcloud/controllers_js/__tests__/roads.test.js | `73feb674a67d33b8c8fc282f49591a785dac9f5127350afb73add6c63795ba84` |
| wepppy/weppcloud/static/js/controllers-gl.js (generated, ignored) | `7540fe59ebda882cf695e5faad415418f428726b064f10c6ed538e96c3133efc` |
| tests/wepp/interchange/test_roads_lifecycle.py | `96a9cf5d2010f586e0402b046a3d8c42e077e29fd31c8161d151c638faba5186` |
| tests/microservices/test_dtale_freshness.py | `903ed9ab4d4244948458e4e22f7676150c14a451f3299f18b2300122894cec09` |
| tests/query_engine/test_mcp_router.py | `8f3b75f94892946eb1732f1812baf48f82e2ce070203dcfbb926ad3bb41ac4b1` |
| tests/weppcloud/test_feature_access.py (test isolation follow-up) | `d889f8ceec6db66e2531e0d683d2784ddc7074acd2c407e44ce3bf355ae65e45` |
