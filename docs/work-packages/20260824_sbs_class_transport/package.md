# SBS Display Class Decoding and Dashboard Tooltip Correction

**Status**: Proposed (2026-08-24) - scaffold cleanup / contract review
**Timezone**: UTC
**Package ID**: SBS-A11Y-02

## Overview

Two coupled defects. Both map clients render stored pixel colors when color
shift is off, so the ADR-0041 palette revision orphaned every earlier run -
confirmed on `strategic-eloquence/disturbed9002_wbt`, whose overlay and legend
disagree. Separately, the color-table classify branch omits unassigned palette
indices from the color table entirely, and because neither bake site disables
`gdaldem` interpolation, those pixels are baked a fabricated color that belongs
to no class while the model classifies them as unknown.

This package makes the color table total and exact, gives unassigned pixels a
first-class identifiable treatment, and moves display color into the clients so
palette revisions apply to every run on next load.

## Objectives

- Write a color-table entry for every palette index and disable interpolation,
  so no pixel is ever baked a fabricated color.
- Give unassigned pixels a distinct, identifiable display treatment, separate
  from both the severity classes and masked/NoData, so users can validate their
  classification on the deck.gl map.
- Decode display color to a class in both clients and recolor unconditionally,
  so no stored pixel color reaches the screen.
- Collapse palette and legend definitions to one per independent runtime
  boundary, with cross-client/Python parity proven by test.
- Report burn class and label in the GL Dashboard tooltip instead of raw RGBA.
- Correct known historical palette generations client-side without rewriting
  artifacts, while explicitly treating unrecoverable historical colors as a
  compatibility limitation.

## Scope

### Included

- Producer: total color table plus `-exact_color_entry` in
  `wepppy/nodb/mods/baer/sbs_map.py` and `wepppy/nodb/mods/baer/baer.py`,
  confined to the existing validate-time render path.
- Client decode table and class-keyed display palettes, defined once within each
  separate client boundary.
- Run-page recolor and legend in
  `wepppy/weppcloud/controllers_js/map_gl_shared.js`, `map_gl.js`, `baer.js`.
- GL Dashboard recolor, legend, unassigned count, and tooltip in
  `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js`,
  `layers/renderer.js`, `layers/detector.js`.
- Server-side legend consolidation in `disturbed.py` and `baer.py`.
- Generated-output regression evidence over real GDAL invocation for both
  classify branches and both controllers.
- Updates to current user/developer documentation and
  `wepppy/nodb/mods/baer/README.sbs_map.md` in the implementation change set.
- `docs/adrs/ADR-0045-sbs-class-coded-display-transport.md`, which must be
  accepted before implementation.
- `docs/ui-docs/contracts/sbs-display-transport-contract.md`, the promoted
  durable behavior contract.

### Explicitly Out of Scope

- **New request surface.** No route, payload key, artifact path, persisted
  field, request-time write, lazy regeneration, or subprocess from a request
  thread. Revision 1 proposed those and was rejected.
- **Regenerating existing artifacts.** Known endpoint colors can be decoded by
  the client, but historical interpolated and clamped colors cannot be fully
  recovered. Re-validation is the only complete correction.
- **Source color-table ingestion.** `sbs_color_map.json` and
  `_DEFAULT_COLOR_TO_SEVERITY` are unchanged and must not be merged with the
  display decode table.
- **A NoData option in the classify select.** Blank continues to mean
  unassigned; inferring masked from blank would assume intent.
- Class codes, thresholds, breaks, coverage formulas, or model behavior.
- `sbs_4class.tif` and its export palettes.
- **Unrelated remediation.** Authorization and default-opacity changes are not
  part of this transport package and must be handled independently if desired.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  `wepppy/nodb/mods/baer/sbs_map.py` (`_write_color_table`, `export_rgb_map`),
  `wepppy/weppcloud/controllers_js/map_gl_shared.js` (`mapSbsRgbForMode`),
  `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js`
  (`mapSbsRgbForDisplay`).
- **Cutover proof required**: a generation-A fixture must render canonical
  colors from the deployed clients with its stored raster byte-identical before
  and after.
- **Acceptance evidence type**: `generated-output`

## Stakeholders

- **Primary**: WEPPcloud run-page and GL Dashboard users; BAER/Disturbed
  operators.
- **Reviewers**: Roger Lew (decision owner); two independent read-only contract
  reviews per `docs/standards/contract-first-change-standard.md`.
- **Security Reviewer**: optional; the proposed delta adds no request or
  authorization surface.
- **Informed**: Codex (implementer).

## Success Criteria

- [ ] The produced color table has an entry for every palette index; unassigned
  indices carry the sentinel.
- [ ] A generated PNG's opaque RGB set is a subset of the decode domain, proven
  on an adversarial source with values between assigned breaks. Removing
  `-exact_color_entry` fails the test.
- [ ] No code path renders a stored SBS display RGB. The non-shifted passthrough
  and both `SBS_STANDARD_TO_SHIFTED_RGB` tables are deleted.
- [ ] Known endpoint colors from generation-0, generation-A, and generation-B
  rasters render canonical colors in both clients and both modes, with stored
  bytes unchanged; between-break generation-0 pixels exercise the approved
  Unassigned compatibility loss.
- [ ] Unassigned pixels render `#800098` at full alpha, are counted, and appear
  as a labeled legend entry in both clients.
- [ ] Unassigned is never rendered as a severity color nor as masked
  transparency.
- [ ] GL Dashboard SBS tooltip reports class code and label, or `Unassigned`.
- [ ] One server-side definition and one definition per separate client
  boundary; a cross-client/Python parity test fails if they disagree.
- [ ] The blueprint registers no new route and `query/baer_wgs_map` payload shape
  is unchanged from baseline.
- [ ] SBS-A11Y-01 ingestion recognition fixtures pass unchanged.

## Parameterization ADR Gate

- **Parameterization change present**: yes; the display transport encoding and
  the rule selecting display color both change.
- **ADR required**: yes,
  `docs/adrs/ADR-0045-sbs-class-coded-display-transport.md`.
- **ADR link(s)**: `docs/adrs/ADR-0045-sbs-class-coded-display-transport.md`
- **Decision provenance captured**: yes.

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites

- `SBS-A11Y-01` (`20260807_sbs_section508_palette`) accepted and deployed. This
  package supersedes its display-transport clause only.

### Blocks

- Any future SBS palette revision, per-user CVD palette preference, or third
  palette mode. Each becomes a client-constant change once this lands.

## Related Packages

- **Depends on**: `20260807_sbs_section508_palette`
- **Related**: `20260728_disturbed_baer_ui_contract` (DOM-23),
  `20260728_map_layers_feature_ui_contract` (DOM-04B)

## Timeline Estimate

- **Expected duration**: 3-5 days
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: no
- **Triage rationale**: the proposed delta changes an existing validate-time
  render path and client display logic. It adds no route, request-time write,
  request-thread subprocess, persisted state, or authorization surface.

## References

- `docs/adrs/ADR-0041-sbs-usgs-section508-palette.md` - superseded display transport
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- `wepppy/nodb/mods/baer/README.sbs_map.md`
- `docs/ui-docs/map-specification-and-behavior.md`
- `docs/ui-docs/gl-dashboard.md`
- `docs/ui-docs/contracts/sbs-display-transport-contract.md`
- `prompts/active/sbs_class_transport_execplan.md`

## Deliverables

_Fill at closure._

## Follow-up Work

_Fill at closure._
