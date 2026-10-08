# Historic PRISM bulk client and cache

Status: Closed 2026-10-08 UTC (code/local; not deployed).

Implement a callable 800 m daily PRISM bulk client with nearest-native-cell identity and a persistent cache configured by `PRISM_CACHE_DIR` in Docker `.env`. This delivery stops at extraction/cache; climate catalog, UI, model input conversion and WEPP execution are separate integration work. Preserve existing clients and climate modes.

## Scope and compatibility

Additive Python API and versioned cache schema only. No project schemas, model defaults, humidity preprocessing, or source clients change. Preserve raw source units/dewpoint. Cache entries are per cell and exact date interval split at calendar-year boundaries; ordinary full-year requests share entries across projects. Partial overlapping intervals are independent in v1. Use immutable attempt directories and atomically replaced entry references. Returned provenance identifies raw evidence and revisions; future project consumers must retain their own source/provenance copy for archives. Shared cache files alone are not project records.

Complexity budget: existing Requests/Pandas/NumPy/PyProj and standard-library file locking/atomic writes. No new dependency, service, Redis state, queue or mount. Security impact: low; public-provider HTTP and operator-owned local cache, no user-facing endpoint. Retain a correctness review; a dedicated security review is not required.

## Acceptance

Cold extraction and warm reuse must produce identical parsed series at the same cells. Changed release metadata invalidates cache; malformed/missing manifests cannot certify freshness. Masked cells, missing dates, duplicates, nonfinite/missing values and invalid units fail explicitly. Retain failed attempts. Verify actual cache files, concurrency, interrupted publication, and live extraction/reuse under the Compose worker identity and persistent mount. Run focused and full tests via `wctl` and document the remaining deployment boundary.

See [ExecPlan](prompts/completed/prism_bulk_client_execplan.md), [tracker](tracker.md), and [client contract](../../dev-notes/prism-800m-client-design.md).

## Outcome

Delivered extraction/cache and Docker configuration with 39 focused tests, live worker artifact validation and retained source evidence. Broad-suite timing failure and successful 207-test tail rerun are recorded in the tracker. Climate/WEPP integration remains follow-up work. Changes are uncommitted at this handoff.
