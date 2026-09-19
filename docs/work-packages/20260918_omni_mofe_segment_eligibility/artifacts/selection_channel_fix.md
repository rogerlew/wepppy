# Modify Landuse channel-selection conformance fix

The user reported that Enable selection mode captures channel TOPAZ IDs and
requested their exclusion. This restores the unchanged selected-hillslope scope
of `docs/schemas/landuse-modification-contract.md` (Required outcome and State,
compatibility, and errors), plus the shared controller contract. No new payload,
endpoint, model parameter, authorization or server mutation behavior is added.

Scope: Modify Landuse selection only. Filter channel IDs (TOPAZ suffix 4) at the
selection-set boundary and omit their features from the selectable overlay.
Keep other map layers and the shared intersection endpoint unchanged.

Regression matrix: absent/empty selection remains empty; hillslope-only values
retain toggle/sort/deduplication; mixed numeric/string hillslope/channel inputs
keep only hillslopes; channel-only input clears selection; legacy prefilled or
pasted channel IDs cannot enter the submitted payload. Existing input
normalization and server validation remain unchanged. Check click, box-select,
textarea and submission, including GeoJSON without features. Channels are an
expected nonselectable feature, not a user-facing exception.

Validation: four regression assertions failed before the patch. Afterward all
five focused tests pass; full frontend suite 112 suites / 906 tests pass, ESLint
passes, and template rendering passes 193 tests. Rebuilt `controllers-gl.js`
through `wctl run-python` (host Python lacks Jinja2). No live browser interaction
was performed; no production deployment was requested. Full repository pytest
was not rerun for this client-only filter/help-text change; focused template and
complete frontend coverage are the gates used here.

Independent correctness review `selection_fix_review`: no blocking findings;
minor wording correction about existing normalization applied above.
