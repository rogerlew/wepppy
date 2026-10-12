# SA-01 contract decision checkpoint

Starting revisions: WEPPpy 298e434d3; wepppyo3 bd63094. Operator's current request authorizes upper 1–100/lower 1–10 anisotropy controls at 50 cm for MOFE/hourly deep seepage, warning above 10, Rust implementation and read/write review. Existing session local commit authority is retained; this package does not authorize push or production deployment.

Normative additions: docs/schemas/soil-anisotropy-contract.md and ADR-0088. Reconciled owners: wepp-run-input-contract.md and single-user-defined-inputs-contract.md. Unchanged applicable contracts: NoDb persistence/concurrency, rq-response, WEPPcloud CSRF, controller-contract shared fields/serialization/read-only/error invariants, output-scope, and MOFE management artifacts. No authority conflict identified; native7777 preservation explicitly excludes an active per-horizon override. The source-owned Rust module follows wepppyo3 architecture/release contracts.

Exact source boundary: WEPP input parser/facade and prep service (effective hourly state), soil util, paired WEPP template/controller/tests; sibling interchange crate export/kernel and its rebuilt release object. No route, queue, auth, model binary or original soil migration is planned. Discrepancy classification: intended additive feature, plus confirmed redundant source reads. No native-performance claim is made.

Compatibility plan: legacy absent/new omitted fields preserve None/saved values; explicit blank/null clears. Disabled/ineligible saved values remain inactive. Existing soil formulas, rounding, defaults and relative order remain unchanged. Optional format incompatibility fails clearly rather than altering native layout. New values apply to every OFE after depth modifications and only on prepared copies. Proposed bottom-depth classification was presented to the operator; no horizon split is assumed.

State matrix: absent, explicit empty, populated, stored inactive, uploaded-native, symbolic, malformed numeric, incompatible format. Input matrix: MOFE on/off, hourly on/off and preparation override, upper/lower unset/set, clipping on/off, exact depth/range boundaries, read-only UI and failed routine-save requests. Evidence must include real Rust imports, locked persistence/reload, actual generated soils, full non-target-field and source hash parity, source-open/write counts and ordinary browse access. Tests mocking a changed boundary are insufficient.

Security impact low: finite numeric validation through existing run grants; two new numeric fields on existing transport; no new endpoint, upload/path input, or privilege. Two independent read-only contract reviews must close findings before standalone ancestor commit. Final correctness review remains required. Implementation is pending.

Correctness review disposition: include existing 9001 per-horizon format; require nondecreasing (not strictly increasing) native depths to preserve existing exact-boundary clipping outputs; preserve admitted original zero ratios in unset classes. Add regression cases for each.

Both independent reviews approve the checkpoint; all findings are closed. Reviewed bottom-depth behavior remains a stated implementation assumption, not a claim of a separate operator ratification. Runtime conformance remains pending.
