# Independent contract correctness review

Review date: 2026-10-13. Reviewer: selected_correctness subagent. Status: PASS for the preimplementation contract checkpoint, after correction of the empty-mapping statement. Implementation and generated-artifact validation remain pending.

Reviewed the package, active ExecPlan, contract decision checkpoint, SBS raster contract, upload-endpoint contract, ADR-0089 and ADR-0090 against the current Python classifier/validator and native color-table summary source.

The proposed change is bounded and consistent with the operator's request. Current sanity checking rejects a readable palette when native `color_table_valid` is false. Native recognition requires at least one low/moderate/high palette entry; this flag is not a raster-corruption check. Existing Python color-table classification already supports unknown entries and explicit RGB overrides. Removing recognition as an admission requirement does not require a new classifier or guessed severity values.

One contract precision issue was found and resolved before approval: `None` selects default recognition, whereas an explicit empty mapping leaves entries unassigned. The checkpoint now preserves that distinction. The schema-discovery amendment retains the existing key and updates its descriptive value to match admission.

Existing unknown classification uses sentinel `255`; `class_map` labels it `No Data`. Existing source/configured NoData behavior must remain independently preserved, including the mask union passed to native four-class export. Do not assert a newly invented class label. Explicit RGB mapping in `get_sbs_color_table` provides the existing correction path.

Acceptance requires real native raster artifacts for all-unknown and mixed palettes, original NoData, unknown output pixels, and explicit remapping. Numeric rasters and recognized palettes must retain behavior; native failures, invalid projection, noninteger pixels and excessive classes must still fail. A palette containing only recognized unburned colors also currently has a false recognition flag and becomes admissible under the proposed policy; this is consistent with the new contract.

The requested AgFields default is a new-project literal change. Existing persisted selections and historical fallback remain unchanged. Config parser/readback evidence is appropriate; no claim of scientific parity between executables is authorized or established.

No unresolved correctness findings block the contract checkpoint. This approval is not an implementation or production rollout approval.

## Final implementation review

Reviewed the working-tree implementation after checkpoint `b4be200b4`, excluding the generated usersum index. Runtime changes remain bounded: admission changes only the readable/unrecognized-palette return path; native summary calls and structural validation remain in place. Schema discovery now describes the accepted state. AgFields changes only the requested default literal and associated help/documentation, preserving existing saved state.

The real GeoTIFF regression covers all-unknown, mixed high/unknown and unburned/unknown palettes, native four-class output, source NoData preservation and explicit RGB remapping. The display-table assertions preserve ADR-0045: unknown pixels use opaque purple Unassigned, whereas source NoData is transparent. Model sentinel `255` and four-class NoData do not replace the distinct display state.

Review follow-ups were resolved: the large-fixture native-summary oracle was restored because native diagnostic semantics did not change, the remaining outdated AgFields capacity description was corrected, and new prose now separates map Unassigned from export NoData. ORCID deferral remains documentation-only, access requests name Mariana Dobre without implying automatic approval, and the FAQ is no longer labeled a draft.

Observed validation receipts: the initial targeted raster/upload set passed 103 tests with one skip, and schema discovery passed 79 tests. The combined final run passed 182 tests with one skip and eight warnings in 13.37 seconds (`/tmp/onboarding-final-tests.log`). This includes native raster artifacts, generated display-table assertions, native failure cases, upload routes and schema discovery. An intermediate new display assertion incorrectly expected a numeric source-NoData entry; it was corrected to assert the actual established representation (numeric entry absent, `nv` transparent). The producer was unchanged. This test-assumption failure is distinct from the initial expected red admission failures.

Final implementation correctness: PASS, with no unresolved findings. The optional large-fixture suite remains skipped; no full-repository or live-production workflow validation is claimed.
