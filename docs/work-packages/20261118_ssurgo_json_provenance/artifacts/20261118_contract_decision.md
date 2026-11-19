# Contract decision checkpoint

Starting implementation: 96555f2f95326350d2d7007c19327378ea831ab0.
Operator explicitly authorized JSON integration and tracking the queried soil-data
server; session commit/push authority persists. New canonical contract:
docs/schemas/soil-data-source-provenance-contract.md. Existing NoDb persistence and
200 mm soil-boundary contracts are preserved, not amended scientifically.

Normative delta: explicit per-project endpoint/profile/release, isolated JSON cache
identity, strict JSON validation, transactionally linked retrieval provenance,
honest unknown-origin legacy metadata, and base-soil provenance sidecars. All six
collection consumers share the same selection. JSON transport identity failures
must escape candidate fallback handling. Rationale: a filename or hardcoded USDA
metadata cannot establish the origin of reused data; silent failover/mixing would
make scientific lineage ambiguous. No automatic endpoint rollout is authorized.

Compatibility/regression plan and valid-state matrix are in the canonical contract.
Default XML remains; historical caches and .sol bytes remain intact. Additive SQLite
metadata and locked NoDb configuration are the only persistence extensions. Explicit
schema/data mutation scope is authorized by requested provenance tracking. No formulas,
thresholds, unit conversions or fallback heuristics change, so no parameterization
ADR is needed. Security impact is medium: outbound operator-configured HTTP and cache
identity enforcement; URL credentials/redirects and mixed-release writes are rejected.

Discrepancy: current .meta.md attributes all data to the hardcoded USDA endpoint;
this is insufficient provenance, not evidence of actual historical requests. Runtime
and official import evidence remain separate. Planned validation: direct HTTP/SQLite
boundary tests, settings reload and selected-cache clearing, frozen legacy-extraction
cases, and real Compose fresh-cache generated output comparison.

Independent read-only reviews: contract_correctness and contract_security, 2026-11-18.
Both confirmed authorized scope and core design; their findings are retained in
contract-reviews.md. All findings accepted and addressed in the canonical contract:
sidecar invalidation before overwrite plus atomic publication/hash verification;
exact identifier/non-finite validation; negative-only and malformed metadata states;
configured XML endpoint versus observed response origin; absolute network deadline
and identity-only bounded streaming. No findings waived. No new dependency is added:
JSON uses stdlib HTTP with an absolute-deadline socket reader, while XML retains
requests behavior. Validation includes slow headers/body and sidecar failure with
identical soil bytes/different source. Implementation remains pending.
