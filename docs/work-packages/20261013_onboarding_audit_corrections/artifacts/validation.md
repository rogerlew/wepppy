# Validation and handoff — 2026-10-13

Implementation follows reviewed ancestor checkpoint `b4be200b4` on master.

## Behavior and evidence

- D01: ConfigParser readback confirms `[ag_fields] bin = wepp_261010`; both vendored watershed and hillslope binaries exist. This was the operator's literal default edit; no new tests merely pin the config. Existing saved AgFields choices and parent fallback are unchanged. No new AgFields numerical-parity or corpus acceptance claim is made.
- D02 red-before: the new native-raster test failed for all-unknown and unburned-only palettes against the old admission rule; mixed recognized/unknown passed. Retained red log: `sbs-red.txt`.
- D02 final: actual GeoTIFF admission, native classification and four-class exports pass for all three cases. Unknown pixels retain 255 in model exports, explicit RGB mapping changes them to low 1, and original source NoData remains255. The generated display table retains opaque purple Unassigned and transparent nv. An initial added display assertion incorrectly expected an explicit numeric source-NoData entry; corrected to the existing absent entry plus transparent nv contract, without changing the producer.
- Final combined focused run: **182 passed, 1 skipped**, 8 warnings, 13.37s. Covers extended SBS, native-required boundaries, SBS fixtures, run/batch/HUC uploads and schema discovery. See `focused-tests.txt`. The skipped module requires unavailable optional large fixtures; no full-suite claim.
- Descriptive API metadata now says `optional_unknown_colors_unassigned`; integer and max256 schema constraints remain asserted. Native recognition diagnostics remain unchanged.
- Changed Markdown lint passed; usersum tree 46 files passes. Manifest/nav/vendor validation passes76 docs/76 leaves/2 vendors. Changed broad-exception enforcement passes, no added catches. Git whitespace check passes.
- D13: ORCID promotion indefinitely deferred in onboarding; runtime conditional support untouched. D14: Mariana Dobre contact documented, no permission change. D18: official FAQ title.

## Scope and limitations

No production deployment, account mutation, stack restart or generated usersum-index rebuild. No JavaScript or frontend behavior changed; the sole template change is literal executable help. Full Python/Jest sweeps were not repeated for this bounded branch/metadata/documentation change; focused tests directly exercise the modified validator and callers. No new browser or live authenticated-upload acceptance is claimed. Existing uncommitted model-list/FAQ updates and the audit report are retained in this change set. Other 13 audit dispositions remain open.

Publish through the existing delivery workflow; long-lived web/rq processes must load the revised code for the new upload behavior. Rebuild the usersum index when refreshing catalog/search content. Existing generated/docs_index.json dirtiness is deliberately excluded. No new infrastructure or schema migration is needed. Rollback restores the prior executable literal/admission branch for subsequent operations without rewriting existing saved selections.
