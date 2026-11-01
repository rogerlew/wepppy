# Native readback implementation review

Reviewer: `/root/rock_contract_impl`, 2026-11-01 UTC. Disposition: **APPROVE bounded invocation**, subject to the execution checks below. Reviewed declaration SHA256 `8940d6cb9a8618e894fa7e350e0f993d6ce85b3d81853dff59c24504626311bc`.

The fixture answers a finite source-to-consumer question: the real SoilGrids builder emits mass RFG and the pinned native observer consumes those tokens. It changes only the soil fixture in a disposable full-runtime copy, retains full configured16years and does not claim a parameter improvement, field validation or closure. Repeating the generated complete OFE block three times and updating its count is an appropriate explicit fixture adaptation.

Before invocation, bind the generated7778 source file, exact adapted p1.sol, full input/runtime bundle and pinned observer binary. Copy only input/runtime files or remove any copied native outputs before execution: neither a completion marker nor trace may be inherited. Hash the original bundle before/after and retain all new outputs/failures. No frozen file may be edited.

Validate actual emitted RFG33.8%, native mass fraction0.338 and all three OFEs. Compare CPM using actual observed density; do not assume native density or depth remains unchanged. Existing density rounding/clamp,85% mass cap and1800mm input-depth cap are interpretation limits. Require finite initialization trace and successful full-period execution before asserting propagation; otherwise retain the failure without weakening acceptance. This fixture cannot establish whole-system physical water or sediment closure.

## Implementation inspection

Current C change is bounded to fixed10 divisor plus additive source/normalized-unit metadata. Both C modes share the loader; priority, fallback and user override remain unchanged. Current ISRICHorizon calls the reviewed density-explicit converter before serialization and logs the source volume, density assumption and mass result. No unrelated soil source/native equation is changed. Converter arithmetic matches the approved contract and explicit domain checks.

The new regression tests exercise real input/output raster and manifest boundaries for both C modes/paths, including zero, low,100,101,800 and nodata; generated-soil test reads real stored-unit rasters and seven emitted horizons split at200mm. The standalone artifact generator repeats real writer/reader paths and binds production/test source hashes. The scalar native formula in the test is not treated as executed native evidence; this separately reviewed fixture closes that distinct boundary.

Final correctness review remains pending fresh native output, broad-test disposition and final evidence/readme readback. No production code was changed by this reviewer.
