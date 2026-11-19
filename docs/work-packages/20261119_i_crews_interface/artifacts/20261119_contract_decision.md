# I-CREWS interface contract decision

## Authority and delta

The starting revision is `79ab5239d2391eca7a3028e1fe99c5acd691f6da`.
The operator requested an I-CREWS launch under Site Specific Resources,
specified the WBT and Multiple OFE source presets and a shared Idaho
intersection policy, then directed execution of the scaffold. Adopt the
proposed public Preview placement and standard creation policy. Preserve the
TOPAZ backend inherited by the requested MOFE source. Use the product
acknowledgment and the disclaimer published by Idaho EPSCoR. The exact copy and button
labels live in the package and interface contract.

## Canonical surfaces and rationale

- [I-CREWS interface contract](../../../ui-docs/contracts/i-crews-interface-contract.md)
  defines the new presentation, preset mapping and run attribution.
- [Feature registry specification](../../../../wepppy/weppcloud/feature_registry/specification.md)
  governs visibility, named preset identity and maturity.
- [Project creation policy](../../../schemas/project-creation-policy.md)
  governs authenticated and anonymous launches. The existing form and
  server policies apply to both choices.
- [Channel boundary contract](../../../schemas/channel-delineation-map-boundary-contract.md)
  governs extent selection, Upload DEM and disjoint rejections. The new
  presets reuse the existing rule.

This is an additive interface and named-preset change. It preserves the
catalog and existing runs, route and queue contracts, and geography behavior
of other presets. One shared polygon keeps display and enforcement consistent.
Security impact is high because creation applies the preset allowlists to
these two IDs even in legacy mode. The card uses public preset semantics and
the asset is owned by the application static tree. Persisted config snapshots
retain the original science settings. The preset corpus must include both
new IDs in the same change to keep ordinary project creation working.

The project-owned config and Flask run config contracts remain applicable.
The active run's saved preset identifies the run credit and Idaho outline.
The existing map bootstrap supplies a boundary URL but its deck.gl controller
does not draw an outline. Enable a line overlay for the two I-CREWS presets
using the existing static boundary URL and map layer registry.

## Evidence

Exercise both buttons, existing creation controls, preset snapshots and legacy allowed and denied overrides before allocation, asset
load and channel acceptance for inside, crossing and disjoint extents.
Read native WBT and TOPAZ artifacts as applicable and one prepared multi-OFE
hillslope input. Confirm attribution appears on the card and both direct run
pages and that an ordinary run has its existing presentation.

## Independent review disposition

Two read-only reviewers reviewed the checkpoint on 2026-11-19 UTC.

- Correctness review confirmed the requested source lineage and current
  creation conventions. The table now specifies default backends and the
  contract preserves the existing expert override and ordinary DEM checks.
- Security review found that legacy creation lacked the snapshot
  allowlists and the production run map did not draw configured boundaries.
  The revised checkpoint applies validation and canonical ID selection to
  both new presets in both modes, enables the shared outline on the same
  two run surfaces, and requires a dedicated security review. The reviewer
  approved the revision.
