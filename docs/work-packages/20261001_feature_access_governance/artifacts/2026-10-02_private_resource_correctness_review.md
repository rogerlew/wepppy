# Private-resource remediation correctness review

## Metadata and authority

- Reviewer: `/root/contract_correctness`, independent review, 2026-10-02 UTC.
- Base: `5d4f199e6`; uncommitted S04/S08 remediation in the shared working tree.
- Scope: query planning/execution and source adapters; browse-to-D-Tale handoff; D-Tale private launch, viewer identity, cached/derived data, enumeration, maps and cleanup; affected tests/contracts.
- Canonical intent: [FA-02 authorization composition and mixed delivery](../../../schemas/feature-access-governance-contract.md), [query-engine contract](../../../../wepppy/query_engine/README.md), and [D-Tale generation contract](../../../schemas/file-dependency-freshness-contract.md).
- Related evidence: [runtime validation](2026-10-02_fa02_runtime_validation.md) and [bounded FA-02 reconciliation review](2026-10-02_fa02_runtime_correctness_review.md).
- This review changes only this artifact. No production data, credentials, services or implementation were changed by the reviewer.

## Findings and disposition

Line numbers refer to review snapshots; named functions identify the stable seams. Changes arrived during review, so closed findings describe earlier inspected content rather than current defects.

| ID | Severity | Evidence and consequence | Disposition |
| --- | --- | --- | --- |
| PRC01 | High | `dtale.load_into_dtale` initially assigned private scope before `_discard_dataset`; source refresh removed that scope and could publish the replacement as public | Closed on readback: desired scope is restored after registration/reuse, with refresh denial regression |
| PRC02 | High | `_request_private_scopes` initially ignored JSON-encoded IDs, then used substring matching; encoded merge references could evade admission/provenance | Closed: string and Unicode-escaped JSON references recursively decoded; integer references also closed under PRC07 |
| PRC03 | High | Initial scope-only cookies and mutable last-loader claims did not establish each viewer's current authority | Closed on readback: per-viewer capability records bind the signed ticket/cookie to that viewer's verified claims; request checks include current expiry/revocation and resource/group admission. Test covers removed member A after active member B reloads the same dataset |
| PRC04 | Medium | Substring ID scanning treated ordinary grid range `0-1` as private derived dataset `1`, denying an unrelated public table | Closed on readback: arbitrary substring scanning removed. Independent real grid probe reproduced 200 before private ID creation, then 403 for `0-1` while `0-0` stayed 200; regression now covers the collision |
| PRC05 | Medium | Upstream `global_state.cleanup` bypassed owned cleanup and left private scope on a reusable numeric ID | Closed: actual upstream boundary clears dataset sidecars. Independent startup/cleanup/startup probe confirms reused ID `1` has no stale scope; map cleanup also closed under PRC09 |
| PRC06 | High | Public-to-private transitions were initially ignored by cached table/overlay reads | Closed: current table visibility and guarded overlay lookup/list recheck resource visibility. Authorized private maps restored; direct-list remainder closed under PRC08 |
| PRC07 | High | `wepppy/webservices/dtale/dtale.py:_request_private_scopes` ignored integers, while upstream merge accepted numeric `dataId` and cast it to a string during lookup. Independent reproduction returned a private canary through an anonymous derivative | Closed: supported numeric references normalize under dataset-ID fields. Real endpoint regression denies anonymous integer-ID merge, permits authorized merge, propagates its scope and denies anonymous derivative grid access without returning the canary |
| PRC08 | Medium | `_build_geojson_upload_with_defaults` built options from raw `CUSTOM_GEOJSON`; absent relevant choices included private overlay names | Closed on source readback: both fallback discovery and final dropdown options use guarded `get_custom_geojson()`. Guarded map list/key visibility is covered by regressions; browser dropdown rendering remains acceptance work |
| PRC09 | High | `_guarded_global_cleanup` removed metadata/scope but left map references, allowing `_geojson_resource_is_visible` to treat an absent dataset as public | Closed: cleanup removes choices/defaults and unreferenced overlays; missing associated metadata fails closed. Regression removes a private table and verifies its overlay is no longer available |
| PRC10 | High | Initial uploaded-overlay cleanup weakened a multi-source conjunction by removing deleted scope A from `{A, B}`, admitting B-only viewers to previously protected content | Closed on source readback: deleting any required private scope discards the dependent uploaded overlay entirely. Regression checks multi-scope removal; no confidentiality requirement is subtracted |

The initial proposal to skip private map registration has been withdrawn. Private map support remains part of the expected valid workflow; no operator exception is needed if the final guarded implementation preserves it.

## Valid-state and compatibility assessment

| State | Required outcome | Reviewed evidence / remaining limit |
| --- | --- | --- |
| Ordinary declared Parquet data, joins, aggregation and scalar expressions | Preserve records and schemas while preventing undeclared files | Existing query core tests pass using registered Arrow datasets |
| Declared vector geometry joined to tabular data | Preserve geometry values and aliases | Real GeoJSON/Parquet join checks exact names and point GeoJSON output through Arrow/WKB adapter |
| SQL expression reads another private file | Explicit denial before returning source data | Real DuckDB `read_parquet` canary denied after external access is disabled |
| Direct or dynamically hidden PROJ transformation | Exclude external-grid reads | Direct `ST_Transform` and dynamic `query` are rejected; these restrictions are documented |
| Public D-Tale eager/lazy table | Anonymous downstream data remains readable | Real CSV/Parquet loader/grid tests; existing lazy-export 501 and generation conflict envelopes retained |
| Private table, absent viewer proof | Deny direct, name, enumeration, export and derived reads | Direct denial, key filtering and real integer-ID merge/derivative denial tested; no unresolved concrete bypass identified in reviewed paths |
| Private table, authorized viewer | Launch/cookie, grid and maps work with current authority | Viewer binding regression uses real loader/cookie/grid with identity-adapter stubs; full deployed identity/proxy acceptance still required |
| Viewer expires/is revoked/loses group; another member reloads | Old viewer stays denied; current member remains allowed | Per-viewer immutable binding and current-claims tests; no last-loader identity substitution |
| Source changes and cache refreshes | Preserve private classification, generation checks and explicit reload behavior | Refresh regression and existing freshness tests |
| Public source becomes private | Stop anonymous cached table/map access | Live table marker and guarded map tests; private maps remain usable with current viewer authority |
| Derived dataset deletion and ID reuse | No inherited stale permission or loss of private provenance | Actual reused-ID probe passes for table scopes; cleanup removes dependent overlays without weakening multi-source requirements |
| Missing/empty optional map state | Keep valid table use and explain absent maps | Existing freshness/map tests; no permission to hide available private maps from entitled users |

## Error policy and evidence

Expected authorization failure must precede data access and keep private contents out of responses. Private launch expiry uses an explicit relaunch outcome; existing lazy source-change behavior remains HTTP 200 with `success=false` because the upstream grid discards non-2xx error bodies. Missing/malformed sources retain their explicit reader failures. Dependency outages must not grant access; current D-Tale reauthorization fails closed, but service/browser acceptance must verify useful recovery guidance.

Independent final focused command:

```text
wctl run-pytest tests/query_engine/test_core.py tests/microservices/test_browse_dtale.py tests/microservices/test_dtale_freshness.py tests/microservices/test_rq_engine_auth.py -q --maxfail=3
```

Final result after cleanup correction: **91 passed**, 5.43 seconds. An earlier concurrent-edit run failed on a then-changing session-revocation fixture; the final run includes the corrected fixture and both revocation checks. This is bounded regression evidence, not a full-suite or deployment acceptance claim.

Additional independent disposable-process probes use real upstream D-Tale startup, CSV loading, grid/merge routes and cleanup. Temporary synthetic canaries are created inside isolated Python processes; no real private data or shared account state is used. Source discovery and optional map discovery are replaced only where needed to select the disposable fixture root. These probes do not substitute for production-equivalent browser credentials, Redis/PostgreSQL state or proxy cookie handling.

## Artifact observability and coverage limits

| Evidence stage | Status |
| --- | --- |
| Approved user outcome | Preserve broad public result sharing and legitimate private workflows while denying unauthorized private-resource reads |
| Reloaded source state | Real temporary CSV/Parquet and PUBLIC marker changes exercised |
| Prepared/executable query input | Catalog paths registered into DuckDB as Arrow sources; generated SQL no longer opens declared files itself |
| Consumed output | Exact spatial records and synthetic grid canaries checked; not inferred from status codes alone |
| Browser/download/derived artifacts | HTTP test-client grid/merge probes; full live proxy/browser, map rendering and exported-file readback remain acceptance work |
| Deployment/recovery | No deployment or affected-resource repair performed; old in-memory instances require coordinated service rollout after acceptance |

No scientific formula or persisted project artifact schema changes were identified. Query source registration preserves Parquet lazy scanning; representative large-vector memory/performance behavior was not benchmarked by this review. Changes to the installed upstream D-Tale route/store behavior require the retained regressions to remain part of upgrade validation.

## Verdict

- **S04 bounded correctness:** no unresolved concrete finding in the reviewed query delta; existing query and spatial regression passed.
- **S08 bounded correctness:** **pass** for the reviewed remediation paths after PRC01–PRC10 corrections.
- Current unresolved findings: High **0**, Medium **0**, Low **0**.
- **M3 remains incomplete and undeployed.** A bounded review pass after corrections would not replace independent security review, stable focused/full-suite results or production-equivalent service/browser acceptance.
