# Final implementation review

Disposition: **PASS for this source-investigation and scalar-observation checkpoint.** No production correction, full-model acceptance or field validation follows. The pre-execution review remains unchanged.

The reviewer inspected actual retained results in `out/rock-sources-water-accounting-20261101/native-scalars-v1`, verified the public scalar receipt is byte-identical, and checked all 17 wrapper/binary hashes and per-process receipts. Compiler, source, declarations and runner match their bound identities. Every selected source slice occurs unchanged in its corresponding private wrapper. All compilations succeeded; 16 finite observations satisfy independent arithmetic checks and the seventeenth retains the predeclared synthetic SIGFPE. No native probe was rebuilt or rerun during this final review.

Independent checks reconstructed initialized absolute water and native UL, stock ordering and all six overflow transfers with float32 operation boundaries. Maximum absolute signed stock-plus-surface-flux residual is 1.881935995928785e-9 m, below the declared 2e-8 m bound. Daily/hourly small-excess behavior differs as reported. The positive native drainage denominator succeeds and the diagnostic zero denominator traps. The results certify these extracted expressions only; intervening dynamics, routing and frost transitions remain outside the executed scope.

Both public source readers were replayed to fresh private `implementation-review/surface-replay` and `implementation-review/bc-replay` directories. Their results exactly reproduce the published receipts; all four surface-reader outputs also match the retained accepted readback. Surface XML supports 15 rows, nine unique components and eight fragment records, including two zero representative records. Component weighting counts each component once. Material 2711184 retains 90 percent reported support and 10 percent unallocated support. The reader preserves missing rows, does not renormalize components and does not aggregate cover. These are bounded retained-input readers, not certification of every possible future source schema or partial interval.

Acquisition payload hashes match the published source identities. All 260 extracted BC dictionary files match the acquired ZIP members. The actual metadata readback identifies COFRAG entry160/BCSLF13 as volume percentage and BD entry191/BCSLF44 as fine-earth bulk density; KP33/KP1500 use total-soil volume. SIFT consumes the BCSLF layer table and directly emits validated COFRAG as its RFG field. Fresh actual SiftHorizon serialization reproduces 20.0; independent mass arithmetic, 100*(0.2*2.65)/(0.2*2.65+0.8*1.3), gives 33.75796178343949 percent. The synthetic adapter observation is correctly distinguished from a deployed dataset audit. The mineral density assumption is a convention, not a measured fragment density.

Reviewed findings and additions to the rock-fragment representation contract preserve those distinctions. They add downstream expression-domain and frozen-reference prerequisites without installing a new formula or default. Missing survey support is not zero cover, observed synthetic singularity is not a historical model failure, and the source-confirmed BC mismatch remains pending its separate ADR and generated/native artifact validation. No unresolved blocking implementation findings remain.

Reviewed public SHA-256 identities:

- `scalar-readback.json`: `12d86705140c699895d58cd21f5ea7a074b7087fb158963b59e293d14ee70f98`
- `read_surface_records.py`: `fb720dfd952b38807a3fc10738ffa059482eb0c22e81a4fd845edd225ac246d4`
- `read_bc_basis.py`: `c91da2e9462038099d24d71dca5a9e49df27ad9af317327444fe2a2b3fec81f9`
- `findings.md`: `968f9d34b397e957292ef039845be4a997161501330b4f80fe8e4d5ee8cb8537`
- `surface-readback.json`: `123f5ca6c685a003536cdeb503eeea182d35f0ae04bc96546bc45ab10bdcf4ad`
- `bc-basis-readback.json`: `3059e9381cd2aaac881817021d3543b55549887bc5b525e64665cf114450c7b1`
- `source-acquisition.json`: `7e3a64fd0acb3a590cf5b87b19822e8decf9c6d93987cae57461ba4e5c341d6f`

Private independent verification: `out/rock-sources-water-accounting-20261101/implementation-review/verification.json`. All reviewer writers are finished after this review and scoped documentation lint; the raw root may then be archived by the parent agent.
