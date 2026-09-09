# Compatibility and regression plan

2026-09-09, before runtime/schema implementation.

The proposed bundle is additive and belongs to a new caller-selected local
directory. Existing RUSLE, Soils, Climate, saved NoDb, `wepp/runs/*`, and legacy
debris-flow artifacts retain their paths, contents and schemas. No downstream
WEPP propagation is expected because this local adapter has no run publisher.
Verify that with source hashes before/after generated-output demonstrations.

Freeze bundle version, input types, required provenance, availability reasons
and completion marker in the canonical M1 contract before implementation.
P02/P03 were subsequently accepted in ADR-0059. Missing legacy provenance must remain visible;
file existence and newly computed hashes cannot establish upstream freshness.

Exercise real file preparation and the actual WBT executable, comparing samples,
masks and grids before/after conversion. Independently verify basin denominator,
T intersections and F/S means. Cover the plan's incomplete-source, invalid-value,
grid, palette, sentinel, source-mutation, process-failure and existing-output cases.
Retain incomplete failure evidence without a final success marker.

`source_inventory.json` identifies three read-only candidate runs. K and DEM
grids match in each; original disturbed SBS grids differ. Their RUSLE SBS copies
are separate candidates whose class mapping and provenance still need validation.
No normalized dNBR source was located by the initial filename search under
`/wc1/runs`; this is not proof that none exists under another name or location.
The inventory does not establish completed WEPP Soils or current source lineage.
No complete authentic T/F/S source set is established yet. Synthetic fixtures
must remain labeled and cannot satisfy that acceptance gate.
