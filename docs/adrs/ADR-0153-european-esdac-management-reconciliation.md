# ADR-0153: Reconcile European ESDAC management scenarios

Status: Accepted and verified on forest
Date: 2026-11-20

## Context

The ESDAC land-use legend supplies source land cover classes. The plain and
Disturbed ESDAC catalogs use existing WEPP templates to model those classes.
Nine base rows differ. Forest and shrub moderate fire use the intended
templates in Disturbed ESDAC but carry low-severity classifications. Both
European catalogs direct three grass wildfire severities to a shrub template.

## Decision

Classify ESDAC key 22 as forest throughout the Disturbed workflow. Its
existing perennial forest management and ESDAC soil settings already use
that treatment. Reconcile the nine base rows of the Disturbed table by
their legend meaning and existing templates. The plain ESDAC table retains
its historical assignments.

| Key | Source class | Chosen Disturbed ESDAC management | Disturbed class | Rationale |
| --- | --- | --- | --- | --- |
| 1 | Pasture, grassland, grazing land | `GIS/Poor grass.man` | `tall grass` | Use the existing grass cover proxy and allow grass burn remapping when selected. |
| 2 | Poplars | `GeoWEPP/forest_perrenial.man` | `forest` | Use the established plain ESDAC perennial forest proxy. |
| 3 | Arable land, cereals | `GeoWEPP/winter wheat, Conventional till.man` | `short grass` | Match the plain ESDAC cereal rotation. |
| 4 | Wasteland, shrub | `Forest/DisturbedWEPPManagement/Shrub perennial.man` | `shrub` | Retain the existing Disturbed shrub proxy for the shrub label. |
| 5 | Forest, coppice | `GeoWEPP/forest_perrenial.man` | `forest` | Use the established plain ESDAC perennial forest proxy. |
| 9 | Bush, macchia | `GIS/Shrubs.man` | `shrub` | Use the matching plain ESDAC shrub proxy, also used by key 8 for garrigue. |
| 13 | Industrial crops | `Agriculture/corn,soybean,wheat,alfalfa(4yrs)- conv till.man` | `short grass` | Use the established plain ESDAC multi-crop proxy for a broad class. |
| 19 | Extensive pasture, grazing, rough pasture | `GIS/Poor grass.man` | `tall grass` | Match the plain ESDAC grass cover proxy and permit grass burn remapping when selected. |
| 20 | Dehesa, extensive pastoral system | `GIS/Shrubs.man` | `shrub` | Retain shrub as the existing modeled proxy for this mixed class and align its template with plain ESDAC. |

Set the Disturbed ESDAC classifications at keys 118 and 120 to forest and
shrub moderate-severity fire. Use the default Disturbed grass high,
moderate, and low wildfire classes and matching managements for keys
129–131 in both European Disturbed maps. For key 132, retain the distinct
`grass prescribed fire` class and use `UnDisturbed/Grass_Low_Severity_Fire.man`
in both maps. The default Disturbed map and the extended lookup use that
management. The base soil lookup already defines prescribed grass fire for
each of the four supported textures.

The exact `eu-esdac-disturbed` selector addresses the separate table.
Previously the substring resolver selected plain ESDAC for this spelling.
The exact option appears in Landuse Options for raster uploads. It is
excluded from Treatments because the catalog lacks treatment markers.
A new selection or rebuild uses the reconciled rows. Previously built
project artifacts and explicit run-owned maps retain their existing authority.

## Decision provenance

The WEPPcloud operator and Codex discussed the choices in the incident
conversation on 2026-11-20 UTC at approximately 16:14 UTC. The operator
selected forest for class 22, individual reconciliation of the nine
base rows, severity-specific grass wildfire, and consistency with default
Disturbed for prescribed grass fire. Codex selected the existing template
for each base row using the retained legend and catalog evidence.

## Rationale and alternatives

Copying all plain templates would give pasture a sagebrush proxy and the
shrub-labelled wasteland a grass template. Keeping all existing Disturbed
choices would retain shrub for grass pasture and a corn-soybean rotation for
the cereal class. Each choice uses an existing WEPP scenario. Source classes
still cover heterogeneous land use and the model choices are proxies.
Prescribed grass fire retains its distinct soil lookup key and the values in
the selected run lookup. In the bundled base lookup, its per-texture soil
coefficients match the grass wildfire rows. The severity-specific template
choices change management scenarios.

## Evidence and rollback

The [management audit](../work-packages/20261120_eu_run_recovery/artifacts/20261120_esdac_management_baseline.md)
contains descriptions and native cover readback. Validate effective
mapping, complete Disturbed wildfire destinations, native management
round trips, and representative soil and WEPP input propagation before
releasing. Revert changed table rows and exact selector routing if the
new mappings fail model preparation or numerical validation. Already
generated project decks remain available as run artifacts.
