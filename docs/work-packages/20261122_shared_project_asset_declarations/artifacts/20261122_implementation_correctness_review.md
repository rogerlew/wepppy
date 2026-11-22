# Two-asset implementation correctness review

Reviewed on 2026-11-22 UTC by the independent correctness reviewer. Candidate `f17ec6ca3681efd5f93207a8b825b1059c94c177`, baseline `a957440abbc00b51ddb356e74d84b50382edae3f`, reviewed contract ancestor `1b51ac142`. The [contract](../../../schemas/shared-project-asset-declarations-contract.md#identity-and-compatibility) requires a faithful extraction for two asset families across producers, query and Feature Export.

## Findings

| Severity | Finding | Disposition |
| --- | --- | --- |
| Medium | The initial extraction left the NoDb interchange-completeness check and Roads publication requirements using their own hill-loss filename. A future naming change could make valid outputs unavailable. | Corrected in the reviewed candidate. `wepp_nodb_post_utils._watershed_interchange_complete`, `_roads_lifecycle.CONTINUOUS`, the Roads report requirements and the equivalent legacy migration predicates now consume the declaration. |
| High during development | An invalid expression in the amended export catalog loader prevented import. | Corrected before the candidate commit. Inspected the final scope guard, which still rejects unsupported scope classes. |
| Evidence | An absent retained Roads key proves a catalog omission. It cannot establish the currentness outcome of an explicit Roads request or successful query/export from a current Roads project. | Track absence, explicit unavailability and positive current Roads readback independently in the actual-project results. |

## User states and artifact checks

| State and request | Required outcome | Reviewed implementation and checks |
| --- | --- | --- |
| Normal project, two published Parquets | Users can query the original public keys and export the same layers and values. | Peridot, native LOSS and the two legacy migration entry points publish or check the historical destinations. The managed [cross-owner test](../../../../tests/nodb/test_shared_asset_publication.py) checks receipts, reloaded listing, value-bearing queries and SHA-256 of selected export inputs. |
| Valid scenario or contrast | The child can inherit or override a source. A named child key in the parent requires existing membership. | Query selection reads one published view. The [query tests](../../../../tests/query_engine/test_activate.py) compare literal expected keys, listing multiplicity and lookup, then execute queries against distinguishable physical Parquets. |
| Optional artifact absent, duplicate key, invalid selector or ambiguous declaration | Preserve the missing marker or absence for valid optional state. Reject invalid declarations or ambiguities explicitly. | The registry detects collisions before consumer use. The metadata observer rejects duplicate retained entries for the selected key. Export rejects invalid declaration references before planning. The native scanner and legacy persisted catalog format retain their existing contracts. |
| Roads selected, unavailable or current | Honor the selected scope and its normal lifecycle checks. A baseline value cannot satisfy a Roads request. | Checked the shared scope roots, report path binding and native publication requirements. Production positive evidence depends on a genuine current Roads cohort. |
| Existing export products and equivalent legacy catalog inputs | Preserve user-visible metadata, resolved roles, dependency fingerprint and cache reuse. | The loader normalizes declaration syntax before consumers inspect raw locators. The [export parity test](../../../../tests/nodb/mods/test_features_export_dependency_tracker.py) restores independently pinned legacy locators and compares catalog, plan, dependency snapshot, fingerprint and cache key under both digest modes. |

The paired native writers retain independent output-name ABIs. A physical rename requires coordinated native changes, regeneration and readback. This slice introduces shared Python naming and published-catalog lookup. The retained catalog comparison cannot measure refresh throughput or prove that a declaration-only inventory would discover missing files.

## Disposition

The two code findings are closed for the specified candidate. Contract acceptance also requires paired reads on original production NFS projects and a fresh private export of the same generation. Partial or missing real cases keep that gate open. [Actual-project protocol](production_validation.md)
