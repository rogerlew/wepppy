# Independent implementation security and integration review

Date: 2026-10-22. Reviewer: integration_contract_review. Contract ancestor:
`1270c209fe978f59a067c88af0df9574d3459114`. Runtime changes were reviewed read-only
in the shared working tree. Final implementation review is bound to the source
hashes below; the final staged regression result was also inspected.

## Disposition

No unresolved high or medium implementation finding remains in this review.
The reviewed implementation passes the security/integration review. Canonical
archive, seven live HTTP reader transitions, separate-service D-Tale transitions,
and authenticated report/discovery checks have retained acceptance evidence.
EVID-01 is closed. The completed staged regression evidence is accepted with
the explicit process and source limitations below; it is not one clean full-suite
invocation. No remaining security/integration acceptance blocker is identified.

### Corrected finding SEC-09: existing D-Tale sessions

Severity: medium; resolved. Guarding the browse launch alone left subsequent
D-Tale session requests without Roads admission. Source hashes could admit
identical bytes recreated during an unpublished run; eager CSV sessions retained
old dataframes. These were new server reads, outside the bounded exception for
already-delivered browser responses.

The existing dataset authorization boundary now acquires shared admission after
authorization and keeps it through response close. Source metadata follows new
derived datasets, source fingerprints are checked, and canonical global cleanup
removes inherited source metadata. The independent
[D-Tale probe](20261022_dtale_security_probe.json) passed for original and derived
eager previews with identical bytes recreated after invalidation: both returned
409/roads_results_unavailable/no-store. A valid response blocked writers until
close, and canonical deletion removed the inherited metadata.

Regression recommendations: keep eager CSV and lazy Parquet cases, exercise
derived creation through an actual request, recreate identical bytes without a
receipt, verify cleanup through `global_state.cleanup`, and test lock release on
normal close and source-error responses. Private authorization must continue to
return 403 before lifecycle details. The existing new tests cover both input
formats and cleanup; the independent probe covers derivation and close lifetime.

## Findings corrected during review

| ID | Severity | Finding and current disposition |
| --- | --- | --- |
| SEC-01 | High | Copying private segment context could briefly expose it through permissive destination ancestry. Snapshot roots remain 0700 throughout staging; final modes preserve source restrictions. Independent copy-boundary observation passed. |
| SEC-02 | Medium | Marking invalidation before the first output rename let cleanup retry invalidate an untouched prior set after a rejected move. Invalidation is now recorded only after accepted mutation; failed preflight does not trigger retention cleanup. |
| SEC-03 | High | Rejecting every symlink broke normal Roads runs/output links to baseline files. Owned file links are materialized before moves, restricted target ancestry constrains snapshot permissions, and source bytes remain untouched. |
| SEC-04 | Medium | Direct return-period refresh lacked a lifecycle guard; loss-like report arguments failed new root inference. Public refresh is guarded and loss-like roots use the existing inference method. |
| SEC-05 | High | Cached query source aliases could bypass lexical-only classification. Execution now classifies lexical and resolved paths and holds guards through Arrow/DuckDB materialization. The independent non-current alias probe rejects access. |
| SEC-06 | Medium | Browse aliases and stale query catalogs advertised unavailable current outputs; MCP success/cache and missing-catalog errors differed from the contract. Inventories classify both paths, catalog visibility filters availability after authorization, and MCP now has no-store success and early current-prefix admission. |
| SEC-07 | High | Archive/restore checked whether a Roads directory existed before deciding to lock, allowing a race with the first Roads mutation. Guards are now unconditional, outside moved trees; restore preserves the lock inode. |
| SEC-08 | Medium | Run status/summary changed before retention succeeded, and stale read controllers could pair old summaries with a new receipt. Accepted run-state changes now follow retention; inspection rejects stale recorded NoDb signatures under the shared guard. |
| SEC-10 | Medium | Single-storm accounting writes a ledger, but publication initially omitted its required receipt path. The producer now includes the ledger in both modes; only equivalent WAT is continuous-only. Generated-set validation loads the single-storm ledger. |
| SEC-11 | Medium | The new internal D-Tale load guard checked currentness but admitted a current logical filename aliased into history. An independent internal-load probe returned 200 for that binding. Both loading and existing sessions now reject the alias; eager/lazy regressions pass while explicit historical loads remain available. |

Publication now reads every required Parquet batch, validates segment/profile
identity, checks produced optional resources, and validates accounting before
writing the receipt last. Restore uses the same generated-set validation. Full
producer evidence is retained separately from synthetic admission fixtures.
The final readonly preflight rejects mutations before retaining current outputs.
Files-route classification preserves existing malformed-path and symlink-loop
handling; the lifecycle guard does not replace those path-security responses.
Discovery no-store headers are conditional on Roads state/catalog sources,
including fully filtered results; baseline-only discovery keeps existing headers.

## Independent evidence

- `wctl run-pytest tests/wepp/interchange/test_roads_lifecycle.py --maxfail=1`:
  **9 passed**, including separate-process reader/writer contention, retained
  output/context/cache, duplicate geometry rejection, failed-restore receipt
  revocation and inode preservation, cached query rejection and streamed-response
  lock lifetime.
- After the D-Tale and restore corrections,
  `wctl run-pytest tests/microservices/test_dtale_freshness.py tests/wepp/interchange/test_roads_lifecycle.py --maxfail=1`:
  **34 passed** (18 D-Tale and 16 lifecycle cases).
- Final readonly and files-route review:
  `wctl run-pytest tests/wepp/interchange/test_roads_lifecycle.py tests/microservices/test_files_routes.py --maxfail=1`:
  **112 passed** (17 lifecycle and 95 files-route cases).
- After the internal-load alias correction,
  `wctl run-pytest tests/microservices/test_dtale_freshness.py -k roads --maxfail=1`:
  **4 passed**, covering eager/lazy existing-session invalidation, current-to-history
  alias rejection at load and grid boundaries, cleanup and explicit historical load.
- [Filesystem probe](20261022_security_probe.json), normal container identity
  uid 1000/gid 993: both observed copy boundaries had snapshot mode 0700;
  final restrictive ancestry remained 0700; retained links became regular files
  with the expected contents; the original source remained unchanged. A stale
  NoDb controller was rejected before its mutation body. Both alias query and
  inventory admission rejected a non-current physical Roads source.
- Earlier fault injection of the first output rename observed one failed rename,
  preserved the old receipt and created no retained receipt; no cleanup retry
  silently accepted invalidation.

The [real UM1 receipt](20261022_real_run_validation.json) and its validation
script were inspected: two full runs separated by
repreparation succeeded in 120.4 seconds, produced 34 summary rows, retained two
history snapshots, and preserved 911 baseline files and 46 original-project
Parquets. The successful receipt included all continuous resources and accounting
artifacts.

The [archive receipt](20261022_archive_validation.json) and `validate_archive.py`
exercise canonical filesystem archive/restore under uid 1000/gid 993, with isolated
RQ/status/cache callbacks. Fourteen required/context files match their source
hashes, historical receipts remain, the coordination inode is preserved, its file
is excluded from ZIP members, and the restored project is admitted as current.
This is real archive/restore evidence, not live RQ orchestration evidence; the
receipt asserts bytes and coordination behavior, not a separate mode comparison.

The [HTTP receipt](20261022_http_validation.json) and `validate_http.py` exercise
live authenticated download, CSV, schema, files metadata, browse, GL page and
query services: each returns 200 while current, 409 during a writer, 409 after
repreparation, then 200 after a fresh full run. The script checks stable error
codes and no-store, verifies 34 CSV/query rows, reads historical bytes successfully,
and checks prepared geometry. Real Chromium sees the final browse summary.
The token is issued through the ordinary scoped dev-agent authorization path;
no token or secret is retained in the receipt.

The [live D-Tale receipt](20261022_dtale_http_validation.json) and
`validate_dtale_http.py` exercise the actual browse and D-Tale containers on the
isolated public validation project. Launch/grid return 303/200 while current,
409/409 during an exclusive writer, 409/409 after repreparation, and 303/200 after
a fresh full Roads run. Existing grid requests return the stable unavailable code
and no-store; successful launches and grids also carry no-store. This closes
EVID-01 for the actual service, filesystem and lock boundary. The recorded
uid 1000/gid 993 belongs to the probe caller; successful HTTP reads exercise the
D-Tale service's own runtime identity and mounts rather than asserting its UID.

The [discovery receipt](20261022_discovery_validation.json) and
`validate_discovery.py` verify no-store on live schema, run-info and console
responses, with current Roads entries included and busy Roads entries omitted.
The actual HTTPS report uses the canonical smoke login and CAP flow with the
existing dev-agent account: the authenticated body contains the Loss summary
while current and returns 409 during a writer. Cookies remain in memory. This
checks report content rather than treating a CAP challenge's 200 as success.

## Review fingerprints

The complete [runtime source hash set](20261022_security_source_hashes.json)
binds this review to 28 task runtime files. Any later runtime edits need an
appropriate review refresh. Principal boundary hashes:

| File | SHA-256 |
| --- | --- |
| wepppy/wepp/interchange/_roads_lifecycle.py | `94b17afb10e8686afbcc9308e1893bc27e5dd924d87ebe9c5142aeca018e6836` |
| wepppy/nodb/mods/roads/roads.py | `55aa09763891340757755df228d2dcb8f2c0553e191b9233f304f3782480668e` |
| wepppy/query_engine/executor.py | `7f7aea9ede186da565167d64d53a31812e57d25300e04f2ec3f655ec700af83e` |
| wepppy/query_engine/app/feature_access.py | `eef7602809dc11f92cf7e9d5fa9a6be8510df60fe35854f8354b3caadc5580fe` |
| wepppy/microservices/browse/_roads.py | `a7c4d5d5517d199daaf2d03f21fdc2843a941adebe9330dc7977124ab6ffc75c` |
| wepppy/rq/project_rq_archive.py | `7fdda6b5669345ee63c41e0f3452c0b74b7c457644f4be39fa4342fcab61819e` |
| wepppy/webservices/dtale/dtale.py | `9678885cf5db77e6d5c3524941939acb823c702adaf73d6a17a9f88d20972278` |

## Remaining acceptance limits

The first broad pytest invocation stopped after 6,029 passed and 56 skipped:
`test_create_mcp_app` reloaded the edited router while its previously imported
`feature_access` module lacked the newly added `discovery_headers`. The reviewed
final clean-process logs show 75 query and 20 D-Tale tests passing. Runtime commit
`e4d28c9ad` is frozen and all 28 review fingerprints still match.

A second invocation performed ordinary full collection and resumed inclusively at
the failed MCP node using the retained `roads_resume.py` selector. It completed
4,774 passed and 71 skipped before an unrelated OpenET admission test reached a
real Redis client captured before autouse stubbing and returned 503. The reviewed
test-only correction binds the existing Redis client factory and a temporary
lifecycle lock directory through scoped monkeypatches. JWT verification, real SQL
membership changes, acknowledgment, scopes and revocation assertions remain
unchanged. No runtime correction was needed.

The final continuation includes that exact failed node and completed all 310
selected tests: 310 passed, one collection skip, and 10,930 deselected in 68.86
seconds. Collection counts reconcile across both
boundaries, including the two added pre-boundary D-Tale cases covered by the
final 20-test run. The completed staged evidence is acceptable; package closure
must retain the selector, collection/result counts and final focused coverage
of changes after the first collection. It must not be represented as one clean
full-suite invocation. Prefix execution used earlier sources, and a new process
does not test state accumulated across the split boundary. These are validation
limits, not evidence of another implementation defect. The implementation agent
also reports 990 frontend tests; final client sequencing regression disposition
is owned by the independent correctness review.

EVID-01 is closed by the retained live D-Tale workflow above. Its project is
public; private dataset authorization remains covered by existing authorization
regressions rather than a new live private-project probe. The live grid check
establishes successful service access and lifecycle admission, not independent
numerical validation of every displayed value.

Failure handling, single-storm accounting and first-creation contention have
targeted filesystem/regression coverage rather than a second live model or live
RQ failure injection. No production deployment or original-project repair is
certified by this review.
